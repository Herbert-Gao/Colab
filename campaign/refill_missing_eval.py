"""Fill the episodes that the evaluation lost to the websocket keepalive.

The RoboTwin policy client uses a websocket keepalive; when the policy server
is busy (the first request of a fresh server includes the JAX compilation),
the ping can time out and the simulator chunk dies with
``ConnectionClosedError: 1011 keepalive ping timeout``.  The affected task
then holds fewer episodes than planned, which would make the report's sample
sizes uneven.

This script finds the seeds that were never played and runs only those, with
a relaxed keepalive, then merges the new result into the task's summary.

    python refill_missing_eval.py
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# A relaxed keepalive: the ping must not fire while the policy server
# compiles or serves several simulator clients at once.
os.environ.setdefault("WEBSOCKET_PING_INTERVAL", "60")
os.environ.setdefault("WEBSOCKET_PING_TIMEOUT", "300")
os.environ.setdefault("PI05_FINAL_SIMS", "6")

import config as C  # noqa: E402
import eval_sources as E  # noqa: E402
import jobctl  # noqa: E402

RESULTS = C.EVAL / "final"

# One policy server per parallel cell, the simulators on the other cards (two
# per card): eight cards, no idling.
POLICY_GPU = ["0", "1"]
SIM_POOLS = [["2", "2", "3", "3", "4", "4"], ["5", "5", "6", "6", "7", "7"]]


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def played_seeds(payload: dict) -> set[int]:
    """The seeds of the episodes that were really played.

    Only the per-episode records count: a chunk can carry a seed list that is
    one longer than the episodes it managed to play.
    """
    seeds: set[int] = set()
    for chunk in payload.get("per_chunk") or []:
        for entry in chunk.get("per_episode") or []:
            if entry.get("seed") is not None:
                seeds.add(int(entry["seed"]))
    return seeds


def incomplete() -> list[tuple[str, int, Path]]:
    """The tasks with fewer episodes than planned.

    Both result layouts are scanned: ``<model>/<task>/final_eval.json`` and
    ``<model>/target<i>/<task>/final_eval.json``.
    """
    out = []
    seen = set()
    for path in sorted(RESULTS.glob("**/final_eval.json")):
        payload = json.loads(path.read_text())
        if payload.get("episodes", 0) >= C.FINAL_EPISODES:
            continue
        parts = path.parts
        task = parts[-2]
        if task not in C.TARGET_TASKS:
            continue
        model = payload.get("model") or parts[-3]
        index = payload.get("target_index")
        if index is None:
            index = C.TARGET_TASKS.index(task)
        if (model, index) in seen:
            continue
        seen.add((model, index))
        out.append((model, int(index), path))
    return out


def refill(model: str, index: int, path: Path, slot: int = 0) -> None:
    task = C.TARGET_TASKS[index]
    old = json.loads(path.read_text())
    planned = C.final_eval_seeds(index)
    done = played_seeds(old)
    missing = [seed for seed in planned if seed not in done]
    print(f"[{now()}] {model} -> {task}: {old['episodes']}/{C.FINAL_EPISODES} episodes, "
          f"refilling {len(missing)} seeds", flush=True)
    if not missing:
        return
    job = jobctl.load(model)
    checkpoint = E.delivered_weights(job)
    extra = E.F.evaluate_checkpoint(
        task, missing, checkpoint,
        repo_id=job["repo_id"], action_horizon=job["action_horizon"],
        out_dir=path.parent / "refill", policy_gpu=POLICY_GPU[slot % len(POLICY_GPU)],
        sim_gpus=SIM_POOLS[slot % len(SIM_POOLS)])
    episodes = old["episodes"] + extra["episodes"]
    successes = old["successes"] + extra["successes"]
    merged = dict(old)
    merged.update({
        "episodes": episodes,
        "successes": successes,
        "success_rate": round(successes / episodes, 4) if episodes else 0.0,
        "per_chunk": (old.get("per_chunk") or []) + (extra.get("per_chunk") or []),
        "refilled_at": now(),
        "refilled_seeds": missing,
    })
    path.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[{now()}] {model} -> {task}: {successes}/{episodes} = "
          f"{merged['success_rate']:.3f}", flush=True)


def main() -> int:
    todo = incomplete()
    if not todo:
        print("every task has the planned number of episodes")
        return 0
    # The cells run in parallel: every cell gets its own policy server and its
    # own simulators, so the whole machine is busy.
    threads = []
    for slot, (model, index, path) in enumerate(todo):
        thread = threading.Thread(target=refill, args=(model, index, path, slot), daemon=True)
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
