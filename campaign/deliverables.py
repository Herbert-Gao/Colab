"""Assemble the section 8 delivery table: machine-readable table + Chinese summary."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
import final_eval as F  # noqa: E402

OUT = C.WORK / "deliverables"


def collect() -> dict:
    jobs = []
    for path in sorted((C.STATE / "jobs").glob("*.json")):
        job = json.loads(path.read_text())
        if job.get("legacy"):
            continue
        history = job.get("history", [])
        evals = sorted(C.EVAL.glob(f"final/{job['job_id']}/*/*/final_eval.json"))
        jobs.append({
            "job_id": job["job_id"],
            "stage": job.get("stage"),
            "kind": job.get("kind"),
            "repeat": job.get("repeat"),
            "family": job.get("family"),
            "task": job.get("task"),
            "repo_id": job.get("repo_id"),
            "demo_ids": job.get("demo_ids"),
            "init_params": job.get("init_params") or job.get("init_from_job"),
            "peak_lr": job.get("peak_lr"),
            "action_horizon": job.get("action_horizon"),
            "seed": job.get("seed"),
            "max_steps": job.get("max_steps"),
            "status": job.get("status"),
            "current_step": job.get("current_step", 0),
            "early_stop": job.get("early_stop"),
            "backtests": [
                {"step": entry["step"], "mean_success_rate": entry["mean_success_rate"],
                 "per_task": {task: info["success_rate"] for task, info in entry["per_task"].items()},
                 "loss_500": (entry.get("loss") or {}).get("loss_mean"),
                 "seeds": job.get("backtest_seeds")}
                for entry in history if entry
            ],
            "milestones": job.get("milestones", {}),
            "final_checkpoint": job.get("final_checkpoint"),
            "final_evals": [str(path) for path in evals],
            "incidents": job.get("incidents", []),
        })
    return {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "embodiment": "aloha-agilex",
        "campaign_root": str(C.WORK),
        "seeds": {
            "pilot_train": C.PILOT_TRAIN_SEED,
            "formal_train": C.FORMAL_REPEAT,
            "pilot_backtest": "900000 + i",
            "adapt_pilot_backtest": "910000 + i",
            "periodic_backtest": "500100 + i",
            "final_eval": "100000 + 1000*t + i",
            "target_demo_selection": "numpy.random.default_rng(1000 + t).choice(50, 5, replace=False)",
            "target_demo_ids": {f"t{t}:{task}": C.target_demo_ids(t)
                                for t, task in enumerate(C.TARGET_TASKS)},
        },
        "hparams": json.loads((C.STATE / "hparams.json").read_text())
        if (C.STATE / "hparams.json").is_file() else {},
        "hparams_adapt": json.loads((C.STATE / "hparams_adapt.json").read_text())
        if (C.STATE / "hparams_adapt.json").is_file() else {},
        "norm_stats_manifest": str(C.STATE / "norm_stats_manifest.json"),
        "jobs": jobs,
    }


def write_summary(payload: dict) -> None:
    jobs = payload["jobs"]
    by_status: dict[str, list[str]] = {}
    for job in jobs:
        by_status.setdefault(job["status"] or "unknown", []).append(job["job_id"])
    lines = [
        f"更新时间（带时区）: {payload['generated']}", "",
        "# 交付摘要（服务器 A）", "",
        f"机体 aloha-agilex；工作目录 `{payload['campaign_root']}`。", "",
        "## 作业统计", "",
        "| 状态 | 数量 | 作业 |", "|---|---:|---|",
    ]
    for status, ids in sorted(by_status.items()):
        lines.append(f"| {status} | {len(ids)} | {', '.join(ids[:6])}{' …' if len(ids) > 6 else ''} |")
    done = [job for job in jobs if job["status"] in ("completed", "early_stopped")]
    lines += ["", "## 已完成作业关键指标", "",
              "| 作业 | 实际步数 | 早停 | 最后回测成功率 | 最终评估 |", "|---|---:|---|---:|---|"]
    for job in done:
        last = job["backtests"][-1] if job["backtests"] else {}
        lines.append(f"| {job['job_id']} | {(job.get('final_checkpoint') or {}).get('step', job.get('current_step', 0))} | "
                     f"{'是 @' + str(job['early_stop']['step']) if job.get('early_stop') else '否'} | "
                     f"{last.get('mean_success_rate', '-')} | {len(job['final_evals'])} 个检查点 |")
    not_run = by_status.get("pending", [])
    lines += ["", "## 未运行作业", "", ", ".join(not_run) if not_run else "无", ""]
    (OUT / "summary_zh.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    payload = collect()
    C.json_dump(OUT / "jobs.json", payload)
    write_summary(payload)
    F.write_eval_doc()
    print(f"deliverables -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
