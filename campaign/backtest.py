"""Backtest one checkpoint on its tasks (5 episodes each, fixed seeds).

Policy servers and simulators are allocated from a global pool: at most one
policy server per GPU and one simulator per server.  The training job keeps
most of the GPU memory while this runs, so several servers on one card would
exceed it and the evaluation would fall back to (much slower) CPU inference.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
import evaluator as E  # noqa: E402


def build_items(tasks: list[str], seeds: list[int], workers: int) -> list[list[tuple[str, list[int]]]]:
    """Split the episodes over the workers, one simulator process per (task, chunk)."""
    buckets: list[list[tuple[str, list[int]]]] = [[] for _ in range(workers)]
    for index, task in enumerate(tasks):
        for slot in range(workers):
            chunk = seeds[slot::workers]
            if chunk:
                buckets[index % workers].append((task, chunk))
    return buckets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--step", required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--policy-gpus", default="",
                        help="comma separated cards for the policy servers")
    parser.add_argument("--sim-gpus", default="",
                        help="comma separated cards for the simulators")
    args = parser.parse_args()

    job = json.loads((C.STATE / "jobs" / f"{args.job_id}.json").read_text())
    tasks = job["backtest_tasks"]
    seeds = job["backtest_seeds"]
    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    gpus = [g.strip() for g in args.policy_gpus.split(",") if g.strip()] or list(C.POLICY_GPUS) or ["6"]
    buckets = build_items(tasks, seeds, len(gpus))
    results: dict[str, list[dict]] = {task: [] for task in tasks}
    lock = threading.Lock()
    # The simulators use the GPUs that do not host a policy server, one client
    # each: the evaluation then spreads over the whole machine instead of
    # stacking every client on one card.
    sim_pool = [g.strip() for g in args.sim_gpus.split(",") if g.strip()]
    if not sim_pool:
        sim_pool = [g for g in C.TRAIN_GPUS.split(",") if g not in gpus] or [C.SIM_GPU]

    def worker(index: int) -> None:
        items = buckets[index]
        if not items:
            return
        gpu = gpus[index]
        with E.policy_server(args.checkpoint, repo_id=job["repo_id"],
                             action_horizon=job["action_horizon"], gpu=gpu,
                             log_path=out / f"policy_server_gpu{gpu}.log") as port:
            # One simulator client per policy server, each on its own GPU.
            # Measured: the simulation is rendering-bound, so several clients
            # on one card slow each other down - sixteen clients took longer
            # than four (13.7 min vs 12.4 min for the same four tasks).
            for slot, (task, chunk) in enumerate(items):
                payload = E.run_task_eval(task, chunk, out_dir=out / f"{task}_gpu{gpu}_s{slot}",
                                          sim_gpu=sim_pool[(index + slot) % len(sim_pool)], port=port)
                with lock:
                    results[task].append(payload)

    threads = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(len(gpus))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    summary_tasks: dict[str, dict] = {}
    for task in tasks:
        payloads = [p for p in results[task] if p]
        episodes = sum(p.get("episodes", 0) for p in payloads)
        successes = sum(p.get("successes", 0) for p in payloads)
        summary_tasks[task] = {
            "task": task,
            "episodes": episodes,
            "successes": successes,
            "success_rate": round(successes / episodes, 4) if episodes else 0.0,
            "per_episode": [e for p in payloads for e in p.get("per_episode", [])],
            "per_group": payloads,
            "skipped": [e for p in payloads for e in p.get("skipped", [])],
        }
    rates = [payload.get("success_rate", 0.0) for payload in summary_tasks.values()]
    summary = {
        "job_id": args.job_id,
        "step": int(args.step),
        "checkpoint": str(args.checkpoint),
        "seeds": seeds,
        "policy_gpus": gpus,
        "sim_gpu": C.SIM_GPU,
        "tasks": summary_tasks,
        "mean_success_rate": round(sum(rates) / len(rates), 4) if rates else 0.0,
        "recorded": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    C.json_dump(out / "backtest.json", summary)
    print(json.dumps({t: {"successes": p["successes"], "episodes": p["episodes"],
                          "success_rate": p["success_rate"]} for t, p in summary_tasks.items()},
                     ensure_ascii=False))
    if not summary_tasks or any(not payload.get("episodes") for payload in summary_tasks.values()):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
