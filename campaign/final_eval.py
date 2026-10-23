"""Final evaluation: every delivered checkpoint over 100 fixed episodes.

Section 3 requires, per adaptation job, the 7500 / 15000 / 30000 checkpoints
(whichever were reached) plus the early-stop final checkpoint, each scored on
100 independent RoboTwin episodes with the seeds fixed in section 4.2, plus the
source model's zero-step baseline on the same target task.

Checkpoints are scored in parallel: one websocket policy server per checkpoint
and several RoboTwin simulators against it.
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
import config as C  # noqa: E402
import evaluator as E  # noqa: E402
import jobctl  # noqa: E402

SIMS_PER_SERVER = int(os.environ.get("PI05_FINAL_SIMS", "3"))


def training_running() -> bool:
    """A live trainer owns most of the GPU memory; keep the eval footprint small."""
    import subprocess
    out = subprocess.run(["pgrep", "-fc", "campaign/train_job.py"], capture_output=True, text=True).stdout
    try:
        return int(out.strip().splitlines()[0]) > 0
    except (ValueError, IndexError):
        return False


def eval_placement() -> tuple[list[str], int, list[str]]:
    """Policy-service GPUs, simulators per server, and the pool for simulators.

    The simulators must not all land on one GPU: with eight concurrent policy
    servers that would put ~40 simulator clients on a single card.
    """
    if training_running():
        servers = list(C.POLICY_GPUS)
        pool = [g for g in C.TRAIN_GPUS.split(",") if g not in servers] or [C.SIM_GPU]
        return servers, SIMS_PER_SERVER, pool
    # No training: every GPU can host a policy server.
    pool = list(C.TRAIN_GPUS.split(","))
    return pool, SIMS_PER_SERVER + 2, pool


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def evaluate_checkpoint(task: str, seeds: list[int], checkpoint: Path, *, repo_id: str,
                        action_horizon: int, out_dir: Path, policy_gpu: str,
                        sim_gpus: list[str] | None = None) -> dict:
    """Score one checkpoint on one task; splits the episode list across sims."""
    started = time.time()
    chunks = [seeds[i::SIMS_PER_SERVER] for i in range(SIMS_PER_SERVER)]
    merged: list[dict] = [{} for _ in chunks]
    pool = list(sim_gpus) if sim_gpus else [C.SIM_GPU]

    with E.policy_server(checkpoint, repo_id=repo_id, action_horizon=action_horizon,
                         gpu=policy_gpu, log_path=out_dir / "policy_server.log") as port:
        def worker(index: int) -> None:
            if not chunks[index]:
                return
            merged[index] = E.run_task_eval(task, chunks[index], out_dir=out_dir / f"sim{index}",
                                            sim_gpu=pool[index % len(pool)], port=port)

        threads = [threading.Thread(target=worker, args=(i,), daemon=True)
                   for i in range(len(chunks)) if chunks[i]]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    merged = [payload for payload in merged if payload]
    episodes = sum(payload.get("episodes", 0) for payload in merged)
    successes = sum(payload.get("successes", 0) for payload in merged)
    summary = {
        "task": task,
        "checkpoint": str(checkpoint),
        "episodes": episodes,
        "successes": successes,
        "success_rate": round(successes / episodes, 4) if episodes else 0.0,
        "seeds": seeds,
        "sims": SIMS_PER_SERVER,
        "per_chunk": merged,
        "seconds": round(time.time() - started, 1),
        "recorded": now(),
    }
    C.json_dump(out_dir / "final_eval.json", summary)
    return summary


def checkpoints_of(job: dict) -> list[tuple[int, Path]]:
    """Milestones that exist plus the early-stop / final weights."""
    found: list[tuple[int, Path]] = []
    base = Path(job["checkpoint_base_dir"]) / C.CONFIG_NAME
    for step in job.get("milestone_steps", []):
        path = base / f"{job['exp_name']}_step{step}"
        if path.is_dir() and (path / "params" / "_METADATA").is_file():
            found.append((step, path))
    final = job.get("final_checkpoint") or {}
    if final.get("params_only") and Path(final["params_only"]).is_dir():
        step = final.get("step")
        if not any(step == existing for existing, _ in found):
            found.append((step, Path(final["params_only"])))
    return sorted(found, key=lambda item: (item[0] is None, item[0]))


def run_job_final_eval(job: dict) -> list[dict]:
    job = jobctl.load(job["job_id"]) or job
    if job["kind"] in ("source", "trial_source"):
        # Section 3: source models are scored on the target tasks as the
        # zero-step baseline (see run_zero_shot), not on their own tasks.
        return []
    targets = [job["task"]]
    t = job.get("t", 0)
    summaries: list[dict] = []
    for index, (step, checkpoint) in enumerate(checkpoints_of(job)):
        for task in targets:
            gpu = C.POLICY_GPUS[index % len(C.POLICY_GPUS)]
            out_dir = C.EVAL / "final" / job["job_id"] / f"step{step}" / task
            if (out_dir / "final_eval.json").is_file():
                summaries.append(json.loads((out_dir / "final_eval.json").read_text()))
                continue
            print(f"[final] {job['job_id']} step={step} task={task}", flush=True)
            servers, sims, pool = eval_placement()
            summary = evaluate_checkpoint(
                task, C.final_eval_seeds(t), checkpoint,
                repo_id=job["repo_id"], action_horizon=job["action_horizon"],
                out_dir=out_dir, policy_gpu=gpu,
                sim_gpus=[g for g in pool if g != gpu] or pool)
            summaries.append(summary)
            write_eval_doc()
    job["final_evals"] = summaries
    jobctl.save(job)
    write_eval_doc()
    return summaries


def run_zero_shot(source_job_id: str, t: int, *, sim_gpus: list[str] | None = None) -> dict:
    """Source model evaluated directly on the target task: the 0-step baseline."""
    source = jobctl.load(source_job_id)
    final = source.get("final_checkpoint") or {}
    if not final.get("params_only"):
        raise RuntimeError(f"source job {source_job_id} has no final weights")
    task = C.TARGET_TASKS[t]
    out_dir = C.EVAL / "final" / source_job_id / "step0_zero_shot" / task
    if (out_dir / "final_eval.json").is_file():
        return json.loads((out_dir / "final_eval.json").read_text())
    servers, sims, pool = eval_placement()
    summary = evaluate_checkpoint(
        task, C.final_eval_seeds(t), Path(final["params_only"]),
        repo_id=source["repo_id"], action_horizon=source["action_horizon"],
        out_dir=out_dir, policy_gpu=servers[0],
        sim_gpus=sim_gpus if sim_gpus else pool)
    summary["note"] = f"0 步裸测：{source_job_id} 的最终权重直接用于目标任务，未使用目标示范"
    C.json_dump(out_dir / "final_eval.json", summary)
    write_eval_doc()
    return summary


def write_eval_doc() -> None:
    rows = sorted(C.EVAL.glob("final/*/*/*/final_eval.json"))
    lines = [
        f"更新时间（带时区）: {now()}", "",
        "# 最终评估汇总（服务器 A）", "",
        "评估种子：目标 t 的第 i 回合（0..99）= 100000 + 1000*t + i；",
        "任务指令、相机、控制频率、最大执行步数与周期回测一致；不同模型来源使用同一组种子。", "",
        "| 作业/基线 | 检查点步数 | 任务 | 回合 | 成功 | 成功率 | 结果文件 |",
        "|---|---:|---|---:|---:|---:|---|",
    ]
    for path in rows:
        payload = json.loads(path.read_text())
        parts = path.parts
        lines.append(
            f"| {parts[-4]} | {parts[-3]} | {payload['task']} | {payload['episodes']} | "
            f"{payload['successes']} | {payload['success_rate']} | `{path}` |")
    (C.DOCS / "eval_final.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_worklist() -> list[dict]:
    """Every checkpoint that has to be scored, plus the zero-step baselines."""
    work: list[dict] = []
    for path in sorted((C.STATE / "jobs").glob("stage3_*.json")):
        job = json.loads(path.read_text())
        if job.get("kind") in ("source", "trial_source"):
            for t in range(len(C.TARGET_TASKS)):
                work.append({"kind": "zero_shot", "job_id": job["job_id"], "target_index": t,
                             "task": C.TARGET_TASKS[t]})
        else:
            for step, checkpoint in checkpoints_of(job):
                work.append({"kind": "adapt", "job_id": job["job_id"], "step": step,
                             "task": job["task"], "target_index": job.get("t", 0),
                             "checkpoint": str(checkpoint)})
    return work


def run_all(parallel: int = 0) -> int:
    """Score every checkpoint, several evaluations at a time (one per policy GPU)."""
    work = build_worklist()
    available, sims, pool = eval_placement()
    gpus = available if parallel <= 0 else available[:parallel]
    global SIMS_PER_SERVER
    SIMS_PER_SERVER = sims
    print(f"[final] {len(work)} evaluations, {len(gpus)} policy servers x {sims} sims, "
          f"simulator pool {pool}", flush=True)
    queue: list[dict] = []
    lock = threading.Lock()

    def worker(gpu: str) -> None:
        # The simulators of this server avoid the server's own GPU.
        sim_pool = [g for g in pool if g != gpu] or pool
        while True:
            with lock:
                if not queue:
                    return
                item = queue.pop(0)
            if item["kind"] == "zero_shot":
                print(f"[final] zero-shot {item['job_id']} -> {item['task']}", flush=True)
                run_zero_shot(item["job_id"], item["target_index"], sim_gpus=sim_pool)
            else:
                job = jobctl.load(item["job_id"])
                out_dir = C.EVAL / "final" / item["job_id"] / f"step{item['step']}" / item["task"]
                print(f"[final] {item['job_id']} step={item['step']} task={item['task']}", flush=True)
                evaluate_checkpoint(
                    item["task"], C.final_eval_seeds(item["target_index"]),
                    Path(item["checkpoint"]), repo_id=job["repo_id"],
                    action_horizon=job["action_horizon"], out_dir=out_dir, policy_gpu=gpu,
                    sim_gpus=sim_pool)
            write_eval_doc()

    threads = [threading.Thread(target=worker, args=(gpu,), daemon=True) for gpu in gpus]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    write_eval_doc()
    print(f"[final] {len(work)} evaluations done", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["job", "zero-shot", "doc", "all"])
    parser.add_argument("--job-id", default="")
    parser.add_argument("--target-index", type=int, default=0)
    parser.add_argument("--parallel", type=int, default=0)
    args = parser.parse_args()
    if args.command == "doc":
        write_eval_doc()
    elif args.command == "job":
        run_job_final_eval(jobctl.load(args.job_id))
    elif args.command == "all":
        run_all(args.parallel)
    else:
        print(json.dumps(run_zero_shot(args.job_id, args.target_index), ensure_ascii=False)[:400])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
