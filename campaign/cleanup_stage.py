"""Stage cleanup (section 4.1).

* ``--stage 1``  keep only the final weights of the selected hyper-parameter
  group; every other group is deleted once the selection is recorded.
* ``--stage 2 --all``  the trial run is not a deliverable: delete everything it
  produced once the stage is finished.

Safety: nothing outside the campaign work directory is ever touched, the work
directory itself is never a delete target, and empty paths are ignored.  Every
deletion is appended to ``docs/cleanup_log.md``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
import jobctl  # noqa: E402


def size_of(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) if path.is_dir() else 0


def safe_target(raw: str) -> Path | None:
    """Resolve a deletion target, refusing anything outside the work dir."""
    if not raw or not raw.strip():
        return None
    target = Path(raw).expanduser().resolve()
    work = C.WORK.resolve()
    if target == work or work not in target.parents:
        print(f"refusing to delete {target} (outside {work})")
        return None
    return target


def delete(target: Path, step: int, reason: str) -> None:
    size = size_of(target)
    shutil.rmtree(target, ignore_errors=True)
    jobctl.log_cleanup(target, step, reason, size)
    print(f"deleted {target} ({size / 1024 ** 3:.1f} GiB)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=int, required=True)
    parser.add_argument("--all", action="store_true", help="delete every artifact of the stage")
    args = parser.parse_args()

    if args.stage == 1:
        frozen_path = C.STATE / "hparams.json"
        if not frozen_path.is_file():
            print("state/hparams.json missing; keep every group until the selection exists")
            return 1
        frozen = json.loads(frozen_path.read_text())
        keep_lr, keep_horizon = frozen.get("peak_lr"), frozen.get("action_horizon")
        for path in sorted((C.STATE / "jobs").glob("stage1_*.json")):
            job = json.loads(path.read_text())
            if job.get("peak_lr") == keep_lr and job.get("action_horizon") == keep_horizon:
                print(f"keep {job['job_id']} (selected: lr={keep_lr}, action_horizon={keep_horizon})")
                continue
            entry = job.get("final_checkpoint") or {}
            target = safe_target((entry.get("params_only") or {}).get("path", ""))
            if target is not None and target.is_dir():
                delete(target, entry.get("step", -1), "阶段1未选中的组，选定后删除")
            job["milestones"] = {}
            job["final_checkpoint"] = None
            C.json_dump(path, job)
        return 0

    if args.stage == 4:
        # The stage 2b pilot is not a deliverable: only the weights of the
        # selected group survive until the adaptation jobs are done.
        frozen_path = C.STATE / "hparams_adapt.json"
        if not frozen_path.is_file():
            print("state/hparams_adapt.json missing; keep the stage 2b artifacts")
            return 1
        frozen = json.loads(frozen_path.read_text())
        keep_lr, keep_horizon = frozen.get("peak_lr"), frozen.get("action_horizon")
        for path in sorted((C.STATE / "jobs").glob("stage2b_*.json")):
            job = json.loads(path.read_text())
            if job.get("peak_lr") == keep_lr and job.get("action_horizon") == keep_horizon:
                print(f"keep {job['job_id']} (selected: lr={keep_lr}, action_horizon={keep_horizon})")
                continue
            entry = job.get("final_checkpoint") or {}
            target = safe_target((entry.get("params_only") or {}).get("path", ""))
            if target is not None and target.is_dir():
                delete(target, entry.get("step", -1), "阶段2b未选中的组，选定后删除")
            job["milestones"] = {}
            job["final_checkpoint"] = None
            C.json_dump(path, job)
        root = C.RUNS / "stage2b"
        if root.is_dir():
            for child in sorted(root.iterdir()):
                if child.is_dir():
                    delete(child, -1, "阶段2b预实验检查点，选定后删除")
        return 0

    if args.stage == 2 and args.all:
        root = C.RUNS / "stage2"
        if root.is_dir():
            for child in sorted(root.rglob("*_step*")):
                if child.is_dir():
                    delete(child, -1, "阶段2试运行产物不保留")
            for child in sorted(root.iterdir()):
                if child.is_dir():
                    delete(child, -1, "阶段2试运行产物不保留")
            for path in sorted((C.STATE / "jobs").glob("stage2_*.json")):
                job = json.loads(path.read_text())
                job["final_checkpoint"] = None
                job["milestones"] = {}
                C.json_dump(path, job)
        return 0

    print(f"nothing to clean for stage {args.stage}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
