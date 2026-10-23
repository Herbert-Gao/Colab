"""Score the delivered source models on the ten target tasks.

Every model is scored on every target task with 100 episodes (the seeds of
section 4.2: ``100000 + 1000*t + i``), the same seeds for every model so the
comparison is paired.  The two models run at the same time: one policy server
per model on its own card, the RoboTwin simulators on the remaining cards.

    python eval_sources.py [--models stage3_source_fam1_r1 stage3_source_fam2_r1]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("PI05_FINAL_SIMS", "6")

import config as C  # noqa: E402
import jobctl  # noqa: E402
import final_eval as F  # noqa: E402

# One policy server per model, the simulators on the other cards.  With a
# single model every remaining card carries a simulator (seven clients, one per
# card - the rendering is the bottleneck, so one client per card is fastest);
# with two models each of them gets three cards with two simulators.
SERVER_GPU = {"stage3_source_fam1_r1": "0", "stage3_source_fam2_r1": "1",
              "stage3_source_fam3_r1": "0", "stage3_source_fam3_r1_long": "0"}
SIM_POOL = {
    "stage3_source_fam1_r1": ["2", "2", "3", "3", "4", "4"],
    "stage3_source_fam2_r1": ["5", "5", "6", "6", "7", "7"],
    "stage3_source_fam3_r1": ["1", "2", "3", "4", "5", "6", "7"],
    # A single model (the third family on its own) puts one simulator on every
    # card but the policy server's.
    "stage3_source_fam3_r1_long": ["1", "2", "3", "4", "5", "6", "7"],
}


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def delivered_weights(job: dict) -> Path:
    final = job.get("final_checkpoint") or {}
    path = (final.get("params_only") or {}).get("path")
    if not path:
        raise FileNotFoundError(f"{job['job_id']}: no delivered weights")
    return Path(path)


def score_model(job_id: str, out_root: Path) -> list[dict]:
    job = jobctl.load(job_id)
    checkpoint = delivered_weights(job)
    server_gpu = SERVER_GPU.get(job_id, "0")
    pool = SIM_POOL.get(job_id, ["2", "3", "4", "5", "6", "7"])
    rows = []
    for index, task in enumerate(C.TARGET_TASKS):
        seeds = C.final_eval_seeds(index)
        family = C.TARGET_FAMILY[index]
        out_dir = out_root / job_id / f"target{index}" / task
        print(f"[{now()}] {job_id} -> {task}: {len(seeds)} episodes", flush=True)
        summary = F.evaluate_checkpoint(
            task, seeds, checkpoint,
            repo_id=job["repo_id"], action_horizon=job["action_horizon"],
            out_dir=out_dir, policy_gpu=server_gpu, sim_gpus=pool)
        summary["model"] = job_id
        summary["target_index"] = index
        summary["family"] = family
        rows.append(summary)
        print(f"[{now()}] {job_id} -> {task}: {summary['successes']}/{summary['episodes']} "
              f"= {summary['success_rate']:.2f} ({summary['seconds']} s)", flush=True)
        C.json_dump(out_root / f"{job_id}_summary.json", rows)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="*", default=["stage3_source_fam1_r1",
                                                        "stage3_source_fam2_r1"])
    parser.add_argument("--out", type=Path, default=C.EVAL / "final")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    results: dict[str, list[dict]] = {}
    errors: dict[str, str] = {}

    def worker(job_id: str) -> None:
        try:
            results[job_id] = score_model(job_id, args.out)
        except Exception as error:  # noqa: BLE001 - one model must not kill the other
            errors[job_id] = f"{type(error).__name__}: {error}"
            print(f"[{now()}] {job_id} FAILED: {errors[job_id]}", flush=True)

    threads = [threading.Thread(target=worker, args=(job_id,), daemon=True)
               for job_id in args.models]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # The aggregate keeps the models that were scored earlier, so a second run
    # (for example the third family after its longer training) adds to it.
    aggregate = args.out / "source_models_eval.json"
    merged: dict = {}
    if aggregate.is_file():
        try:
            merged = json.loads(aggregate.read_text()).get("results", {})
        except json.JSONDecodeError:
            merged = {}
    merged.update(results)
    payload = {"recorded": now(), "results": merged, "errors": errors,
               "kind": "target_tasks",
               "episodes_per_task": C.FINAL_EPISODES,
               "seeds": "100000 + 1000*t + i"}
    C.json_dump(aggregate, payload)
    for job_id, rows in results.items():
        total = sum(row["episodes"] for row in rows)
        wins = sum(row["successes"] for row in rows)
        print(f"{job_id}: {wins}/{total} = {wins / total:.3f} over {len(rows)} tasks", flush=True)
    print(f"-> {args.out / name}", flush=True)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
