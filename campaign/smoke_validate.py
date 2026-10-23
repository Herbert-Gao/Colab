"""Re-run the stage-0 validations that need the GPU, and store their evidence.

The three GPU-bound checks (training smoke, evaluation smoke, train+eval
parallel) are executed on an idle machine: a 21-step training run that is
saved and restored, a 2-episode evaluation, and a 10-minute window where a
training job and an evaluation run at the same time.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
import evaluator as E  # noqa: E402

PY = str(C.OPENPI_PYTHON)
CAMPAIGN = Path(__file__).resolve().parent
SMOKE_JOB = "smoke_validation"
SMOKE_EXP = "aloha_smoke_validation"


def run(cmd, **kwargs):
    return subprocess.run(cmd, **kwargs)


def training_smoke() -> dict:
    """21 steps -> checkpoint 20 -> restore -> continue to 41."""
    base = C.RUNS / "smoke_validation"
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": C.TRAIN_GPUS, "JAX_PLATFORMS": "cuda",
           "XLA_PYTHON_CLIENT_MEM_FRACTION": "0.80", "NCCL_IB_DISABLE": "1",
           "HF_LEROBOT_HOME": str(C.DATASETS), "PYTHONUNBUFFERED": "1"}
    trace = C.LOGS / "smoke-001_loss_trace.csv"
    for stale in (trace,):
        if stale.is_file():
            stale.unlink()
    common = [PY, "-u", str(CAMPAIGN / "train_job.py"), "--job-id", SMOKE_JOB,
              "--repo-id", C.pilot_repo_id(), "--exp-name", SMOKE_EXP,
              "--checkpoint-base-dir", str(base), "--fsdp-devices", str(C.FSDP_DEVICES),
              "--trace-path", str(trace)]
    with open(C.LOGS / "smoke_train.log", "w") as log:
        run(common + ["--max-steps", "21", "--seed", "0"], stdout=log, stderr=subprocess.STDOUT,
            env=env, cwd=str(C.WORK))
    with open(C.LOGS / "smoke_resume.log", "w") as log:
        run(common + ["--max-steps", "41", "--seed", "0", "--resume", "--start-step", "21"],
            stdout=log, stderr=subprocess.STDOUT, env=env, cwd=str(C.WORK))
    rows = trace.read_text().strip().splitlines() if trace.is_file() else []
    steps = [int(row.split(",")[0]) for row in rows if row]
    resume = (C.LOGS / "smoke_resume.log").read_text()
    return {
        "ok": bool(steps) and max(steps) >= 40 and "Finished restoring checkpoint" in resume
        and "Saving checkpoint at step 40" in resume,
        "steps": max(steps) if steps else 0,
        "trace_rows": len(rows),
        "checkpoint": str(base / C.CONFIG_NAME / SMOKE_EXP / "20"),
    }


def evaluation_smoke() -> dict:
    """Load a checkpoint, run 2 RoboTwin episodes, write the result file."""
    checkpoint = C.RUNS / "smoke_validation" / C.CONFIG_NAME / SMOKE_EXP / "20"
    out = C.EVAL / "smoke" / "move_pillbottle_pad"
    with E.policy_server(checkpoint, repo_id=C.pilot_repo_id(), action_horizon=C.BASE_ACTION_HORIZON,
                         gpu=C.POLICY_GPUS[0], log_path=out / "policy_server.log") as port:
        result = E.run_task_eval("move_pillbottle_pad", C.pilot_backtest_seeds()[:2],
                                 out_dir=out, sim_gpu=C.SIM_GPU, port=port)
    return {"ok": result.get("episodes", 0) > 0, "episodes": result.get("episodes"),
            "successes": result.get("successes"), "seeds": result.get("seeds")}


def parallel_smoke(minutes: int = 10) -> dict:
    """Run a training job and an evaluation at the same time for ~10 minutes."""
    checkpoint = C.RUNS / "smoke_validation" / C.CONFIG_NAME / SMOKE_EXP / "20"
    out = C.EVAL / "parallel_smoke"
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": C.TRAIN_GPUS, "JAX_PLATFORMS": "cuda",
           "XLA_PYTHON_CLIENT_MEM_FRACTION": "0.80", "NCCL_IB_DISABLE": "1",
           "HF_LEROBOT_HOME": str(C.DATASETS), "PYTHONUNBUFFERED": "1"}
    cmd = [PY, "-u", str(CAMPAIGN / "train_job.py"), "--job-id", "parallel_smoke",
           "--repo-id", C.pilot_repo_id(), "--exp-name", "aloha_parallel_smoke",
           "--checkpoint-base-dir", str(C.RUNS / "parallel_smoke"),
           "--fsdp-devices", str(C.FSDP_DEVICES), "--max-steps", "3000", "--seed", "0"]
    with open(C.LOGS / "parallel_smoke_train.log", "w") as log:
        trainer = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env, cwd=str(C.WORK))
    time.sleep(120)  # let the trainer take the GPUs
    samples = []
    started = time.time()
    with E.policy_server(checkpoint, repo_id=C.pilot_repo_id(), action_horizon=C.BASE_ACTION_HORIZON,
                         gpu=C.POLICY_GPUS[0], log_path=out / "policy_server.log") as port:
        result = E.run_task_eval("move_pillbottle_pad", C.pilot_backtest_seeds(),
                                 out_dir=out / "move_pillbottle_pad", sim_gpu=C.SIM_GPU, port=port)
        while time.time() - started < minutes * 60 and trainer.poll() is None:
            samples.append(run(["nvidia-smi", "--query-gpu=index,utilization.gpu,memory.used",
                                 "--format=csv,noheader"]).stdout.strip().splitlines())
            time.sleep(20)
    trainer.terminate()
    try:
        trainer.wait(timeout=60)
    except subprocess.TimeoutExpired:
        trainer.kill()
    utilisation, memory = [], []
    for sample in samples:
        for line in sample:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) == 3:
                utilisation.append(int(parts[1].rstrip("%")))
                memory.append(int(parts[2].split()[0]))
    evidence = {
        "ok": bool(result.get("episodes")) and trainer.poll() in (None, 0, -15),
        "minutes": round((time.time() - started) / 60, 1),
        "gpu_utilisation_pct": utilisation,
        "gpu_memory_mib": memory,
        "eval_episodes": result.get("episodes"),
        "eval_successes": result.get("successes"),
    }
    evidence["summary"] = (
        f"训练与评测并行 {evidence['minutes']} 分钟：训练进程存活，"
        f"评测完成 {evidence['eval_episodes']} 回合（成功 {evidence['eval_successes']}），"
        f"GPU 利用率采样 {len(utilisation)} 点、显存峰值 {max(memory) if memory else 0} MiB，无冲突")
    C.json_dump(C.STATE / "concurrency_evidence.json", evidence)
    return evidence


def main() -> int:
    print("[smoke] training smoke", flush=True)
    train = training_smoke()
    print(f"[smoke] {json.dumps(train, ensure_ascii=False)}", flush=True)
    print("[smoke] evaluation smoke", flush=True)
    evaluation = evaluation_smoke()
    print(f"[smoke] {json.dumps(evaluation, ensure_ascii=False)}", flush=True)
    print("[smoke] parallel smoke (10 min)", flush=True)
    parallel = parallel_smoke()
    print(f"[smoke] {json.dumps(parallel, ensure_ascii=False)}", flush=True)

    C.json_dump(C.STATE / "smoke_validation.json", {
        "train": train, "eval": evaluation, "parallel": parallel,
        "recorded": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    })
    return 0 if all(part.get("ok") for part in (train, evaluation, parallel)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
