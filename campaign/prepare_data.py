"""Build every LeRobot dataset and the shared normalization stats for the campaign.

Raw source: RoboTwin 2 ``demo_clean`` HDF5 demos (``aloha_agilex`` layout), the
same input the canonical converter ``scripts/convert_robotwin_pi05_multi.py`` on
this box reads.  Two things the existing converter cannot express are needed
here, so this module implements them explicitly:

* arbitrary per-task episode-id selection (4.2 draws the 5 target demos with
  ``numpy.random.default_rng(1000*r + t)``, not the first N episodes);
* the unified 20-source-task normalization stats, which must not be recomputed
  per job and must never see a target task.

Usage:
    python prepare_data.py datasets      # convert / link all datasets
    python prepare_data.py stats          # unified norm stats + manifest
    python prepare_data.py verify         # embodiment / episode-count audit
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

import cv2
import h5py
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

IMAGE_KEYS = {
    "observation.images.top": "vision/cam_head/colors",
    "observation.images.left_wrist": "vision/cam_left_wrist/colors",
    "observation.images.right_wrist": "vision/cam_right_wrist/colors",
}
STATE_KEY = "state/joint_states"
ACTION_KEY = "action/joint_states"
ROBOT_TYPE = "aloha_agilex"
DELTA_MASK = np.ones(14, dtype=bool)
DELTA_MASK[[6, 13]] = False  # grippers stay absolute (openpi DeltaActions mask)


def decode_jpeg(value) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(bytes(value), dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("RoboTwin camera sample is not a decodable JPEG")
    return image[:, :, ::-1].copy()


def episode_path(task: str, episode_id: int) -> Path:
    return C.RAW_ROOT / task / "aloha_agilex" / "data" / f"episode_{episode_id:07d}.hdf5"


def sha256_file(path: Path, chunk: int = 1 << 22) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def lerobot_api():
    try:
        from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
    except ModuleNotFoundError:
        from lerobot.datasets.lerobot_dataset import LeRobotDataset
    return LeRobotDataset


def convert(repo_id: str, selection: dict[str, list[int]], *, overwrite: bool = False) -> dict:
    """Convert {task: [episode ids]} into one LeRobot dataset under C.DATASETS."""
    output = C.DATASETS / repo_id
    if output.is_dir() and not overwrite:
        meta_path = output / "meta" / "info.json"
        if meta_path.is_file():
            info = json.loads(meta_path.read_text())
            print(f"[skip] {repo_id}: {info['total_episodes']} episodes already present", flush=True)
            manifest = read_json(C.STATE / "dataset_manifests" / f"{repo_id}.json", {})
            if manifest:
                return manifest
            return {"repo_id": repo_id, "episodes_total": info["total_episodes"]}

    LeRobotDataset = lerobot_api()
    sources: list[tuple[str, int, Path]] = []
    for task, ids in selection.items():
        for episode_id in ids:
            path = episode_path(task, episode_id)
            if not path.is_file():
                raise FileNotFoundError(f"missing RoboTwin demo: {path}")
            sources.append((task, episode_id, path))
    if not sources:
        raise ValueError(f"empty selection for {repo_id}")

    started = time.time()
    with h5py.File(sources[0][2], "r") as hdf:
        frequency = int(hdf["additional_info/frequency"][()])
        shapes = {key: decode_jpeg(hdf[path][0]).shape for key, path in IMAGE_KEYS.items()}
    if len({tuple(s) for s in shapes.values()}) != 1:
        raise ValueError(f"camera shapes differ: {shapes}")
    height, width, channels = shapes["observation.images.top"]
    if channels != 3:
        raise ValueError(f"expected RGB, got {shapes}")

    dataset = LeRobotDataset.create(
        repo_id=repo_id,
        robot_type=ROBOT_TYPE,
        fps=frequency,
        features={
            **{
                key: {"dtype": "image", "shape": (height, width, 3),
                      "names": ["height", "width", "channel"]}
                for key in IMAGE_KEYS
            },
            "observation.state": {"dtype": "float32", "shape": (14,), "names": ["state"]},
            "action": {"dtype": "float32", "shape": (14,), "names": ["action"]},
        },
        use_videos=False,
        # The asynchronous image writer (processes=1, threads=4) deadlocks in
        # this LeRobot build: the writer process stops draining its queue while
        # the main process waits for the episode to be finalized.  The images
        # are written synchronously instead - same result, no hang.
        image_writer_threads=0,
        image_writer_processes=0,
        root=str(output),
    )

    frames = 0
    instructions: set[str] = set()
    episode_map: list[dict] = []
    for episode_index, (task, episode_id, path) in enumerate(sources):
        with h5py.File(path, "r") as hdf:
            state = np.asarray(hdf[STATE_KEY], dtype=np.float32)
            action = np.asarray(hdf[ACTION_KEY], dtype=np.float32)
            prompt = bytes(hdf["instruction"][()]).decode()
            if int(hdf["additional_info/frequency"][()]) != frequency:
                raise ValueError(f"frequency mismatch in {path}")
            n = min(len(state), len(action), *(len(hdf[p]) for p in IMAGE_KEYS.values()))
            if n < 2:
                raise ValueError(f"episode too short: {path} ({n})")
            instructions.add(prompt)
            for index in range(n):
                dataset.add_frame({
                    **{key: decode_jpeg(hdf[path_key][index]) for key, path_key in IMAGE_KEYS.items()},
                    "observation.state": state[index],
                    "action": action[index],
                    "task": prompt,
                })
            dataset.save_episode()
            frames += n
        episode_map.append({
            "episode_index": episode_index,
            "task": task,
            "source_episode_id": episode_id,
            "source_file": str(path),
            "frames": n,
            "instruction": prompt,
        })
        print(f"[{repo_id}] {episode_index + 1}/{len(sources)} {task}#{episode_id} frames={frames}", flush=True)

    manifest = {
        "repo_id": repo_id,
        "robot_type": ROBOT_TYPE,
        "embodiment": "aloha-agilex",
        "source_root": str(C.RAW_ROOT),
        "episodes_total": len(sources),
        "frames_total": frames,
        "fps": frequency,
        "image_shape": [height, width, channels],
        "episodes_per_task": {
            task: sum(1 for e in episode_map if e["task"] == task) for task in selection
        },
        "task_instructions": sorted(instructions),
        "selection": selection,
        "episode_map": episode_map,
        "conversion_seconds": round(time.time() - started, 1),
    }
    C.json_dump(output / "campaign_conversion.json", manifest)
    C.json_dump(C.STATE / "dataset_manifests" / f"{repo_id}.json", manifest)
    print(f"[done] {repo_id}: {frames} frames in {manifest['conversion_seconds']}s", flush=True)
    return manifest


def link_existing(repo_id_link: str, repo_id_source: str) -> dict:
    """Expose a previously converted single-task dataset inside the work dir."""
    target = C.DATASETS / repo_id_link
    source = C.XWORLD_LEROBOT / repo_id_source
    if not source.is_dir():
        raise FileNotFoundError(source)
    if target.exists() or target.is_symlink():
        if target.is_symlink():
            target.unlink()
        else:
            shutil.rmtree(target)
    target.symlink_to(source)
    info = json.loads((source / "meta" / "info.json").read_text())
    manifest = {
        "repo_id": repo_id_link,
        "link_to": str(source),
        "robot_type": info["robot_type"],
        "embodiment": "aloha-agilex",
        "episodes_total": info["total_episodes"],
        "frames_total": info["total_frames"],
        "fps": info["fps"],
        "selection": {C.PILOT_TASK: list(range(C.DEMOS_PER_TASK))},
    }
    linked_path = C.STATE / "linked_datasets.json"
    linked = read_json(linked_path, {})
    linked[repo_id_link] = manifest
    C.json_dump(linked_path, linked)
    C.json_dump(C.STATE / "dataset_manifests" / f"{repo_id_link}.json", manifest)
    print(f"[link] {repo_id_link} -> {source}", flush=True)
    return manifest


def read_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def stats(values: list[np.ndarray]) -> dict:
    value = np.concatenate(values, axis=0)
    return {
        "mean": value.mean(0).tolist(),
        "std": np.maximum(value.std(0), 1e-6).tolist(),
        "q01": np.quantile(value, 0.01, axis=0).tolist(),
        "q99": np.quantile(value, 0.99, axis=0).tolist(),
    }


def build_stats() -> dict:
    """Unified stats over the 20 source tasks x 50 demos; no target task data."""
    selection = {task: list(range(C.DEMOS_PER_TASK)) for task in C.STATS_TASKS}
    state_parts: list[np.ndarray] = []
    action_parts: list[np.ndarray] = []
    episode_records: list[dict] = []
    for task in C.STATS_TASKS:
        for episode_id in selection[task]:
            path = episode_path(task, episode_id)
            if not path.is_file():
                raise FileNotFoundError(f"missing RoboTwin demo for stats: {path}")
            with h5py.File(path, "r") as hdf:
                state = np.asarray(hdf[STATE_KEY], dtype=np.float32)
                action = np.asarray(hdf[ACTION_KEY], dtype=np.float32).copy()
            n = min(len(state), len(action))
            action = action[:n]
            action[:, DELTA_MASK] -= state[:n][:, DELTA_MASK]
            state_parts.append(state[:n])
            action_parts.append(action)
            episode_records.append({
                "task": task,
                "episode_id": episode_id,
                "file": str(path),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            })
            print(f"[stats] {task}#{episode_id} ({len(episode_records)}/1000)", flush=True)

    payload = {"norm_stats": {"state": stats(state_parts), "actions": stats(action_parts)}}
    out = C.ASSETS / "RoboTwin_lerobot_v30" / "norm_stats.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, out)
    manifest = {
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "scope": "20 source tasks x 50 demos (section 4.2)",
        "tasks": C.STATS_TASKS,
        "episodes": len(episode_records),
        "frames": int(sum(len(part) for part in state_parts)),
        "embodiment": "aloha-agilex",
        "action_space": "delta on 12 arm joints, absolute on 2 grippers",
        "norm_stats_file": str(out),
        "norm_stats_sha256": sha256_file(out),
        "episode_records": episode_records,
    }
    C.json_dump(C.STATE / "norm_stats_manifest.json", manifest)
    print(f"[done] stats -> {out} ({manifest['frames']} frames, {manifest['episodes']} episodes)", flush=True)
    return manifest


def build_datasets(*, overwrite: bool = False) -> None:
    C.DATASETS.mkdir(parents=True, exist_ok=True)
    os.environ["HF_LEROBOT_HOME"] = str(C.DATASETS)

    link_existing(C.pilot_repo_id(), f"robotwin_{C.PILOT_TASK}_demo_clean")

    for family, tasks in C.FAMILIES.items():
        convert(
            C.family_repo_id(family),
            {task: list(range(C.DEMOS_PER_TASK)) for task in tasks},
            overwrite=overwrite,
        )

    for t, task in enumerate(C.TARGET_TASKS):
        ids = C.target_demo_ids(t)
        convert(C.target_repo_id(t), {task: ids}, overwrite=overwrite)
    C.json_dump(C.STATE / "target_demo_ids.json", {
        f"t{t}:{task}": C.target_demo_ids(t)
        for t, task in enumerate(C.TARGET_TASKS)
    })


def verify() -> dict:
    """Embodiment + episode-count audit of everything the campaign will read."""
    os.environ["HF_LEROBOT_HOME"] = str(C.DATASETS)
    expected: dict[str, dict] = {C.pilot_repo_id(): {C.PILOT_TASK: C.DEMOS_PER_TASK}}
    for family, tasks in C.FAMILIES.items():
        expected[C.family_repo_id(family)] = {task: C.DEMOS_PER_TASK for task in tasks}
    for t, task in enumerate(C.TARGET_TASKS):
        expected[C.target_repo_id(t)] = {task: C.TARGET_DEMOS}

    audit: list[dict] = []
    failures: list[str] = []
    for repo_id, want in expected.items():
        root = C.DATASETS / repo_id
        info_path = root / "meta" / "info.json"
        entry = {"repo_id": repo_id, "path": str(root.resolve()), "ok": False}
        if not info_path.is_file():
            entry["error"] = "meta/info.json missing"
            failures.append(f"{repo_id}: meta/info.json missing")
            audit.append(entry)
            continue
        info = json.loads(info_path.read_text())
        entry.update({
            "robot_type": info.get("robot_type"),
            "total_episodes": info.get("total_episodes"),
            "fps": info.get("fps"),
            "state_shape": info["features"]["observation.state"]["shape"],
            "action_shape": info["features"]["action"]["shape"],
            "cameras": sorted(k for k in info["features"] if k.startswith("observation.images")),
        })
        if info.get("robot_type") != ROBOT_TYPE:
            failures.append(f"{repo_id}: robot_type={info.get('robot_type')} (expected {ROBOT_TYPE})")
        if info.get("total_episodes") != sum(want.values()):
            failures.append(f"{repo_id}: {info.get('total_episodes')} episodes (expected {sum(want.values())})")
        for key, shape in (("observation.state", (14,)), ("action", (14,))):
            if tuple(info["features"][key]["shape"]) != shape:
                failures.append(f"{repo_id}: {key} shape {info['features'][key]['shape']} != {shape}")
        entry["expected_episodes"] = sum(want.values())
        entry["ok"] = entry["robot_type"] == ROBOT_TYPE and entry["total_episodes"] == entry["expected_episodes"]
        audit.append(entry)

    raw_missing = [
        f"{task}#{i}"
        for task in set(C.STATS_TASKS) | set(C.TARGET_TASKS)
        for i in range(C.DEMOS_PER_TASK)
        if not episode_path(task, i).is_file()
    ]
    result = {
        "datasets": audit,
        "raw_demo_missing": raw_missing,
        "embodiment_required": "aloha-agilex",
        "embodiment_violations": [f for f in failures if "robot_type" in f],
        "failures": failures,
        "ok": not failures and not raw_missing,
    }
    C.json_dump(C.STATE / "data_audit.json", result)
    print(json.dumps({"ok": result["ok"], "failures": failures[:10],
                      "raw_demo_missing": raw_missing[:10]}, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["datasets", "stats", "verify"])
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    for directory in C.ALL_DIRS + [C.STATE / "jobs", C.STATE / "dataset_manifests"]:
        directory.mkdir(parents=True, exist_ok=True)
    if args.command == "datasets":
        build_datasets(overwrite=args.overwrite)
    elif args.command == "stats":
        build_stats()
    else:
        result = verify()
        if not result["ok"]:
            raise SystemExit(2)


if __name__ == "__main__":
    main()
