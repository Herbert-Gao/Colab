"""Thin state helpers for the shell job runner (``run_job.sh`` / ``queue.sh``).

Every heavy operation (training, backtest, snapshot) already lives in its own
tested module; this file only reads and updates the job record so the shell
scripts stay declarative.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402


def job_path(job_id: str) -> Path:
    return C.STATE / "jobs" / f"{job_id}.json"


def load(job_id: str) -> dict:
    return json.loads(job_path(job_id).read_text())


def save(job: dict) -> None:
    import time
    job["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    C.json_dump(job_path(job["job_id"]), job)


def checkpoint_root(job: dict) -> Path:
    return Path(job["checkpoint_base_dir"]) / C.CONFIG_NAME / job["exp_name"]


def complete(step_dir: Path) -> bool:
    if not step_dir.is_dir() or not (step_dir / "_CHECKPOINT_METADATA").is_file():
        return False
    if not (step_dir / "params" / "_METADATA").is_file():
        return False
    return not any(step_dir.parent.glob(f"{step_dir.name}.orbax-checkpoint-tmp-*"))


def cmd_field(args) -> int:
    job = load(args.job_id)
    value = job
    for part in args.key.split("."):
        value = value[part] if isinstance(value, dict) else value[int(part)]
    if isinstance(value, (list, tuple)):
        print(" ".join(str(v) for v in value))
    else:
        print(value)
    return 0


def cmd_new_checkpoints(args) -> int:
    """Print complete checkpoint steps that are not recorded yet."""
    job = load(args.job_id)
    root = checkpoint_root(job)
    done = set(job.get("processed_checkpoints", []))
    steps = []
    if root.is_dir():
        for child in sorted(root.iterdir()):
            if child.is_dir() and child.name.isdigit() and int(child.name) not in done:
                if complete(child):
                    steps.append(int(child.name))
    print(" ".join(str(s) for s in steps))
    return 0


def cmd_mark_processed(args) -> int:
    job = load(args.job_id)
    for step in args.steps:
        if int(step) not in job.setdefault("processed_checkpoints", []):
            job["processed_checkpoints"].append(int(step))
    save(job)
    return 0


def cmd_record(args) -> int:
    """Append one backtest row, update the early-stop bookkeeping, print the verdict."""
    job = load(args.job_id)
    payload = json.loads(Path(args.backtest_json).read_text())
    step = int(args.step)
    trace = C.LOGS / f"{args.job_id}_loss_trace.csv"
    loss_info = None
    if trace.is_file():
        values = []
        with open(trace, encoding="utf-8") as handle:
            for line in handle:
                parts = line.strip().split(",")
                if len(parts) < 2:
                    continue
                try:
                    at, loss = int(parts[0]), float(parts[1])
                except ValueError:
                    continue
                if at > step:
                    break
                if loss == loss and abs(loss) != float("inf"):
                    values.append(loss)
        if values:
            tail = values[-C.LOSS_WINDOW:]
            loss_info = {"loss_mean": sum(tail) / len(tail), "n": len(tail),
                         "sufficient": len(tail) >= C.LOSS_WINDOW,
                         "total_updates": len(values)}

    per_task = {task: {"successes": payload.get("successes", 0),
                        "episodes": payload.get("episodes", 0),
                        "success_rate": payload.get("success_rate", 0.0),
                        "per_episode": payload.get("per_episode", [])}
                for task, payload in payload.get("tasks", {}).items()}
    mean_rate = payload.get("mean_success_rate", 0.0)
    entry = {
        "step": step,
        "mean_success_rate": mean_rate,
        "per_task": per_task,
        "loss": loss_info,
        "checkpoint": str(checkpoint_root(job) / str(step)),
        "backtest": args.backtest_json,
        "seeds": payload.get("seeds"),
        "time": payload.get("recorded"),
    }
    verdict = judge(job, step, mean_rate, loss_info)
    entry["early_stop"] = verdict
    job.setdefault("history", []).append(entry)
    if step not in job.setdefault("processed_checkpoints", []):
        job["processed_checkpoints"].append(step)
    save(job)
    print("stop" if verdict["stop"] else "continue")
    return 0


def judge(job: dict, step: int, success_rate: float, loss_info: dict | None) -> dict:
    """Section 6 early-stop rule."""
    verdict = {"step": step, "success_rate": success_rate, "loss": loss_info,
               "stop": False, "reasons": []}
    # The loss window of every scored checkpoint is kept: section 6 compares
    # the last three 2,000-step intervals, which reach back before 12,000.
    windows = job.setdefault("loss_windows", [])
    windows.append({"step": step, "loss": (loss_info or {}).get("loss_mean")})
    windows.sort(key=lambda entry: entry["step"])
    if step < C.EARLY_STOP_MIN_STEP:
        # Section 6: the 10,000-step checkpoint is the baseline; the judgement
        # only starts at 12,000 steps.  Earlier backtests must not raise the
        # baseline, otherwise a lucky early checkpoint would mask the real one.
        if step >= C.EARLY_STOP_BASELINE_STEP:
            job["best_success"] = success_rate
            job["no_improve_count"] = 0
            verdict["reasons"].append("baseline success rate recorded")
        else:
            verdict["reasons"].append(f"step {step} < {C.EARLY_STOP_BASELINE_STEP}: baseline not set yet")
        return verdict
    if job.get("best_success") is None or success_rate > job["best_success"]:
        job["best_success"] = success_rate
        job["no_improve_count"] = 0
        verdict["reasons"].append("new best success rate")
    else:
        job["no_improve_count"] = int(job.get("no_improve_count", 0)) + 1
    windows = job.setdefault("loss_windows", [])
    recent = windows[-4:]
    changes = []
    loss_ok = False
    if len(recent) >= 4:
        loss_ok = True
        for previous, current in zip(recent[-4:-1], recent[-3:]):
            a, b = previous["loss"], current["loss"]
            if a is None or b is None:
                loss_ok = False
                break
            change = abs(b - a) / max(abs(a), 1e-12)
            changes.append(round(change, 6))
            if change > C.EARLY_STOP_LOSS_TOL:
                loss_ok = False
    verdict["loss_relative_changes"] = changes
    verdict["loss_condition_met"] = loss_ok
    verdict["success_condition_met"] = int(job.get("no_improve_count", 0)) >= C.EARLY_STOP_PATIENCE
    # Section 6 asks for both conditions; the operator relaxed the rule to the
    # success condition alone, because the loss of this recipe keeps moving by
    # more than 1% per interval and would therefore never allow an early stop.
    verdict["stop"] = bool(verdict["success_condition_met"]
                            and (loss_ok or not C.EARLY_STOP_REQUIRE_LOSS_CONDITION))
    return verdict


def cmd_snapshot(args) -> int:
    """Copy a checkpoint's weights only (params + assets) to a delivery path."""
    import snapshot as S

    job = load(args.job_id)
    step = int(args.step)
    source = checkpoint_root(job) / str(step)
    if not source.is_dir():
        print(f"missing checkpoint {source}", file=sys.stderr)
        return 1
    base = checkpoint_root(job).parent
    dest = base / (f"{job['exp_name']}_step{step}" if args.kind == "milestone"
                   else f"{job['exp_name']}_final_step{step}")
    try:
        info = S.copy_weights(source, dest)
    except Exception as error:
        print(f"snapshot failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    job.setdefault("milestones" if args.kind == "milestone" else "final_checkpoints", {})[str(step)] = info
    if args.kind == "final":
        job["final_checkpoint"] = {"step": step, "params_only": info}
    save(job)
    print(json.dumps(info, ensure_ascii=False))
    return 0


def cmd_cleanup(args) -> int:
    """Keep the newest N full checkpoints; drop the rest and log it.

    ``--keep-backtested N`` keeps the N newest checkpoints that already carry a
    backtest result (section 4.1 wants the recovery points on the backtest
    cadence) plus the newest checkpoint on disk, which is the resume point.
    """
    job = load(args.job_id)
    root = checkpoint_root(job)
    if not root.is_dir():
        return 0
    steps = sorted(int(p.name) for p in root.iterdir() if p.is_dir() and p.name.isdigit())
    if args.keep_backtested:
        scored = sorted(int(h["step"]) for h in job.get("history", []) if h.get("step") is not None)
        keep = set(scored[-args.keep_backtested:]) if scored else set()
        if steps:
            keep.add(steps[-1])
    else:
        keep = set(steps[-args.keep:]) if args.keep else set()
    freed = 0
    for step in steps:
        if step in keep:
            continue
        path = root / str(step)
        size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        shutil.rmtree(path, ignore_errors=True)
        freed += size
        log_cleanup(path, step, args.reason, size)
    print(f"freed_gib={freed / 1024 ** 3:.1f}")
    return 0


def log_cleanup(path: Path, step: int, reason: str, size: int = 0) -> None:
    import time
    doc = C.DOCS / "cleanup_log.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    if not doc.is_file():
        doc.write_text("更新时间（带时区）: "
                       + time.strftime("%Y-%m-%dT%H:%M:%S%z")
                       + "\n\n# 检查点清理日志\n\n| 时间 | 路径 | 步数 | 原因 | 释放 (GiB) |\n|---|---|---:|---|---:|\n",
                       encoding="utf-8")
    with open(doc, "a", encoding="utf-8") as handle:
        handle.write(f"| {time.strftime('%Y-%m-%dT%H:%M:%S%z')} | {path} | {step} | {reason} | "
                     f"{(size / 1024 ** 3):.1f} |\n")


def cmd_set_hparams(args) -> int:
    """Apply the frozen learning rate and action horizon to the later jobs.

    Source models use the stage-1 selection, adaptation jobs the stage-2b
    selection; the grid jobs themselves keep their own values.
    """
    def load(name):
        path = C.STATE / name
        return json.loads(path.read_text()) if path.is_file() else {}

    source = load("hparams.json")
    adapt = load("hparams_adapt.json")
    changed = 0
    for path in sorted((C.STATE / "jobs").glob("*.json")):
        job = json.loads(path.read_text())
        if job.get("kind") in ("pilot", "adapt_pilot"):
            continue
        frozen = adapt if job.get("kind") == "adapt" else source
        if not frozen:
            continue
        dirty = False
        for key in ("peak_lr", "action_horizon"):
            if frozen.get(key) and job.get(key) != frozen[key]:
                job[key] = frozen[key]
                dirty = True
        if dirty:
            save(job)
            changed += 1
    print(json.dumps({"source": source, "adapt": adapt, "jobs_updated": changed},
                     ensure_ascii=False))
    return 0


def cmd_status(args) -> int:
    job = load(args.job_id)
    print(json.dumps({k: job.get(k) for k in
                      ("job_id", "status", "current_step", "no_improve_count", "best_success",
                       "early_stop", "final_checkpoint")}, ensure_ascii=False))
    return 0


def cmd_set(args) -> int:
    job = load(args.job_id)
    for pair in args.pairs:
        key, _, raw = pair.partition("=")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = raw
        job[key] = value
    save(job)
    return 0


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("field"); p.add_argument("job_id"); p.add_argument("key")
    p.set_defaults(func=cmd_field)

    p = sub.add_parser("new-checkpoints"); p.add_argument("job_id")
    p.set_defaults(func=cmd_new_checkpoints)

    p = sub.add_parser("mark-processed"); p.add_argument("job_id"); p.add_argument("steps", nargs="+")
    p.set_defaults(func=cmd_mark_processed)

    p = sub.add_parser("record"); p.add_argument("job_id"); p.add_argument("step")
    p.add_argument("backtest_json")
    p.set_defaults(func=cmd_record)

    p = sub.add_parser("snapshot"); p.add_argument("job_id"); p.add_argument("step")
    p.add_argument("kind", choices=["milestone", "final"])
    p.set_defaults(func=cmd_snapshot)

    p = sub.add_parser("cleanup"); p.add_argument("job_id")
    p.add_argument("--keep", type=int, default=C.ROLLING_KEEP)
    p.add_argument("--keep-backtested", type=int, default=0,
                   help="keep the N newest checkpoints that already have a backtest result")
    p.add_argument("--reason", default="回测完成，仅保留最近恢复点")
    p.set_defaults(func=cmd_cleanup)

    p = sub.add_parser("set-hparams"); p.set_defaults(func=cmd_set_hparams)

    p = sub.add_parser("status"); p.add_argument("job_id")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("set"); p.add_argument("job_id"); p.add_argument("pairs", nargs="+")
    p.set_defaults(func=cmd_set)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
