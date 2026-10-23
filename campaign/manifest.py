"""Write ``docs/models_manifest.md``: the models this server delivers.

The manifest lists the source models of this round with the weights that are
kept on disk and their last periodic backtest, plus the fine-tuning jobs that
the operator deferred.  Every listed path is verified against the file system,
so the manifest cannot claim a checkpoint that is not there.

    python manifest.py            # write the manifest and verify the paths
    python manifest.py --notify   # additionally send the "all done" lark message
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def load_jobs() -> list[dict]:
    jobs = []
    for path in sorted((C.STATE / "jobs").glob("*.json")):
        try:
            job = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        if job.get("legacy"):
            continue
        jobs.append(job)
    return jobs


def last_success(job: dict):
    history = job.get("history") or []
    if not history:
        return None
    return history[-1].get("mean_success_rate")


def kept_paths(job: dict) -> list[str]:
    paths = []
    final = job.get("final_checkpoint") or {}
    info = final.get("params_only") or {}
    if info.get("path"):
        paths.append(f"{info['path']}（最终权重，step {final.get('step')}）")
    for step, entry in sorted((job.get("milestones") or {}).items(), key=lambda kv: int(kv[0])):
        if entry.get("path"):
            paths.append(f"{entry['path']}（里程碑 step {step}）")
    return paths


def path_exists(path: str) -> bool:
    return Path(path).exists()


def row(job: dict, kind: str) -> tuple[str, list[str]]:
    missing = []
    paths = kept_paths(job)
    for entry in paths:
        path = entry.split("（")[0]
        if not path_exists(path):
            missing.append(path)
    early = "是 @%s" % job["early_stop"]["step"] if job.get("early_stop") else "否"
    step = (job.get("final_checkpoint") or {}).get("step") or job.get("current_step") or 0
    status = job.get("status") or "unknown"
    if kind == "source":
        cells = [job["job_id"], job.get("family", "-"), step, early, status,
                 "<br>".join(paths) if paths else "（无）", last_success(job)]
    else:
        cells = [job["job_id"], job.get("init_from_job", "-"), job.get("task", "-"), step, early, status,
                 "<br>".join(paths) if paths else "（无）", last_success(job)]
    return "| " + " | ".join("-" if cell is None else str(cell) for cell in cells) + " |", missing


def build(jobs: list[dict]) -> tuple[list[str], list[str]]:
    sources = [job for job in jobs if job.get("kind") == "source"]
    adapts = [job for job in jobs if job.get("kind") == "adapt"]
    header = [
        "| 模型ID | 起点模型 | 目标任务 | 实际步数 | 是否早停 | 状态 | 保留的检查点路径 | 最近一次回测成功率 |",
        "|---|---|---|---:|---|---|---|---|",
    ]
    lines = ["| 源模型ID | 族群 | 实际步数 | 是否早停 | 状态 | 保留的检查点路径 | 最近一次回测成功率 |",
             "|---|---|---:|---|---|---|---|"]
    missing: list[str] = []
    for job in sorted(sources, key=lambda j: j["job_id"]):
        text, gone = row(job, "source")
        missing += gone
        lines.append(text)
    deferred = [job for job in adapts if job.get("status") == "deferred"]
    done = [job for job in adapts if job.get("status") in ("completed", "early_stopped")]
    lines += ["", f"## 微调模型（目标适应，本轮延后：{len(deferred)} 个作业状态为 deferred）", ""] + header
    for job in sorted(adapts, key=lambda j: (j.get("t", 0), j.get("family", ""))):
        text, gone = row(job, "adapt")
        missing += gone
        lines.append(text)
    lines += ["", f"- 已交付微调模型: {len(done)} / {len(adapts)}", ""]
    return lines, missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notify", action="store_true",
                        help="send the 'all done' message through lark-im")
    args = parser.parse_args()

    jobs = load_jobs()
    lines, missing = build(jobs)
    sources = [job for job in jobs if job.get("kind") == "source"]
    adapts = [job for job in jobs if job.get("kind") == "adapt"]
    delivered = [job for job in sources
                 if job.get("status") in ("completed", "early_stopped")]
    trained = [job for job in sources if job.get("status") in ("completed", "early_stopped", "stopped")]

    doc = [
        f"更新时间（带时区）: {now()}", "",
        "# 模型清单（服务器 A，aloha-agilex）", "",
        f"本轮范围（运营 2026-10-22 决定）：只训练源模型，用 openpi 官方超参"
        f"（peak_lr {C.OFFICIAL_PEAK_LR}、action_horizon {C.OFFICIAL_ACTION_HORIZON}、batch {C.BATCH_SIZE}）"
        f"训 {C.SOURCE_MAX_STEPS} 步；微调矩阵（{len(C.TARGET_TASKS)} 目标 × "
        f"{len(C.ADAPT_SOURCE_FAMILIES)} 起点 = {len(adapts)} 个）**延后**，作业状态为 `deferred`。",
        f"本轮不含最终评估（100 回合）与 0 步裸测。",
        "",
    ] + lines + [
        "",
        f"- 源模型: {len(sources)} 个（有交付权重 {len(trained)}，训练完成 {len(delivered)}）",
        f"- 微调模型: {len(adapts)} 个（完成 {sum(1 for j in adapts if j.get('status') in ('completed', 'early_stopped'))}，"
        f"延后 {sum(1 for j in adapts if j.get('status') == 'deferred')}）",
        f"- 检查点路径校验: {'全部存在' if not missing else '缺失 ' + str(missing)}",
        "",
    ]
    (C.DOCS / "models_manifest.md").write_text("\n".join(doc) + "\n", encoding="utf-8")
    print(f"manifest -> {C.DOCS / 'models_manifest.md'} "
          f"({len(delivered)} source models completed, missing={len(missing)})")

    if args.notify:
        import notify_channel
        message = (f"服务器A/A800×8｜阶段3：全部完成。"
                   f"本轮交付 {len(delivered)}/{len(sources)} 个源模型"
                   f"（微调矩阵已按运营指示延后），清单见 docs/models_manifest.md。")
        record = notify_channel.send(message)
        C.json_dump(C.STATE / "final_notify.json", {
            "sent_at": now(), "message": message, "record": record})
        print(json.dumps({"status": record.get("status")}, ensure_ascii=False))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
