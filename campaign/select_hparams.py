"""Hyper-parameter selection for the source pilot (stage 1) and the
adaptation pilot (stage 2b).

Rule (section 4.2): the highest 5-episode success rate wins; ties break on the
lower 2000-step loss (mean of the last 500 updates); a remaining tie goes to
the setting closest to the configuration baseline.

    python select_hparams.py --stage 1     # -> state/hparams.json
    python select_hparams.py --stage 2b    # -> state/hparams_adapt.json

Both selections are appended to ``docs/02_hparam_pilot.md``; the document
keeps the earlier tables.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

DOC = C.DOCS / "02_hparam_pilot.md"


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def collect_rows(pattern: str) -> tuple[list[dict], list[str]]:
    """One row per finished group: its best backtest and its 2000-step loss."""
    rows = []
    missing = []
    for path in sorted((C.STATE / "jobs").glob(pattern)):
        job = json.loads(path.read_text())
        history = job.get("history") or []
        if not history:
            missing.append(job["job_id"])
            continue
        best = max(history, key=lambda entry: entry["mean_success_rate"])
        loss = (best.get("loss") or {}).get("loss_mean")
        rows.append({
            "job_id": job["job_id"],
            "lr": job["peak_lr"],
            "action_horizon": job["action_horizon"],
            "success_rate": best["mean_success_rate"],
            "loss_2000": loss,
            "step": best["step"],
            "per_task": {task: info["success_rate"] for task, info in best["per_task"].items()},
            "status": job.get("status"),
        })
    return rows, missing


def choose(rows: list[dict]) -> dict:
    """Section 4.2 selection rule."""
    rows.sort(key=lambda row: (-row["success_rate"],
                               row["loss_2000"] if row["loss_2000"] is not None else 1e9))
    best = rows[0]
    ties = [row for row in rows if row["success_rate"] == best["success_rate"]]
    if len(ties) > 1:
        best_losses = [row["loss_2000"] for row in ties if row["loss_2000"] is not None]
        if best_losses:
            lowest = min(best_losses)
            ties = [row for row in ties
                    if row["loss_2000"] is not None and row["loss_2000"] <= lowest + 1e-12]
        if len(ties) > 1:
            best = sorted(ties, key=lambda row: (abs(math.log(row["lr"]) - math.log(C.BASE_LR))
                                                 + abs(row["action_horizon"] - C.BASE_ACTION_HORIZON)))[0]
    return best


def append_doc(section_lines: list[str]) -> None:
    """Keep the history: the header is refreshed, the tables are appended."""
    DOC.parent.mkdir(parents=True, exist_ok=True)
    existing = DOC.read_text(encoding="utf-8").splitlines() if DOC.is_file() else []
    body = [line for line in existing if not line.startswith("更新时间（带时区）")]
    header = [f"更新时间（带时区）: {now()}", ""]
    if body and body[0].startswith("# "):
        body = body[1:]
    DOC.write_text("\n".join(header + body + section_lines) + "\n", encoding="utf-8")


def table(rows: list[dict]) -> list[str]:
    lines = ["| 组 | 学习率 | action_horizon | 5 回合成功率 | 2000 步 loss（最后 500 步均值） | 状态 |",
             "|---|---:|---:|---:|---:|---|"]
    for row in rows:
        lines.append(f"| {row['job_id']} | {row['lr']} | {row['action_horizon']} | "
                     f"{row['success_rate']} | {row['loss_2000']} | {row.get('status')} |")
    return lines


def select_stage1() -> int:
    rows, missing = collect_rows("stage1_*.json")
    if missing:
        print(f"stage 1 incomplete, no result yet: {missing}", file=sys.stderr)
        return 2
    if len(rows) < 9:
        print(f"stage 1 incomplete: {len(rows)}/9 groups", file=sys.stderr)
        return 2
    best = choose(rows)
    choice = {
        "selected": best,
        "rule": "5 回合成功率最高 → 2000 步 loss（最后 500 次更新均值）更低 → 最接近配置基准值",
        "decided": now(),
        "rows": rows,
    }
    C.json_dump(C.STATE / "hparams.json", {
        "peak_lr": best["lr"],
        "action_horizon": best["action_horizon"],
        "decided": choice["decided"],
    })
    C.json_dump(C.STATE / "hparams_selection.json", choice)

    lines = [
        f"## 阶段1 源训练超参数预实验（{now()}）", "",
        "任务: `move_pillbottle_pad`（50 条示范，训练种子 0）；每组 2000 步后回测 5 回合。",
        f"学习率基准 {C.BASE_LR}（候选 0.5×/1×/2× = {tuple(round(C.BASE_LR * f, 12) for f in C.LR_FACTORS)}）；",
        f"chunk_size = `action_horizon`，基准 {C.BASE_ACTION_HORIZON}，候选 {C.ACTION_HORIZONS}"
        "（5：代码中 `Pi0Config.action_horizon` 为任意整数；15：`training/config.py` 的 `pi05_droid` 配置使用 15）。",
        "回测种子: " + ", ".join(str(s) for s in C.pilot_backtest_seeds()), "",
    ] + table(rows) + [
        "",
        f"**选定：学习率 {best['lr']}，chunk_size(action_horizon) {best['action_horizon']}**"
        f"（{choice['rule']}）",
        "",
        "选定后阶段2 / 阶段3 源训练的全部作业使用该组合，已写入 `state/hparams.json`。",
        "",
    ]
    append_doc(lines)
    print(json.dumps(choice["selected"], ensure_ascii=False))
    return 0


def select_stage2b() -> int:
    rows, missing = collect_rows("stage2b_*.json")
    if missing:
        print(f"stage 2b incomplete, no result yet: {missing}", file=sys.stderr)
        return 2
    if len(rows) < 3:
        print(f"stage 2b incomplete: {len(rows)}/3 groups", file=sys.stderr)
        return 2
    best = choose(rows)
    choice = {
        "selected": best,
        "rule": "5 回合成功率最高 → 2000 步 loss（最后 500 次更新均值）更低 → 最接近配置基准值",
        "decided": now(),
        "rows": rows,
    }
    C.json_dump(C.STATE / "hparams_adapt.json", {
        "peak_lr": best["lr"],
        "action_horizon": best["action_horizon"],
        "decided": choice["decided"],
    })
    C.json_dump(C.STATE / "hparams_adapt_selection.json", choice)

    horizons = sorted({row["action_horizon"] for row in rows})
    lrs = sorted({row["lr"] for row in rows})
    compatible = len(horizons) > 1 and all(row["status"] in ("completed", "early_stopped")
                                           for row in rows)
    code_note = ("（依据：openpi 中 `action_horizon` 只影响数据加载的动作块长度、损失形状与注意力掩码，"
                 "不改变参数树形状——`openpi/models/pi0.py` 的 `action_time_mlp_in` 对时间嵌入做 repeat 而非可学习参数，"
                 "`action_out_proj` 输出维度由 `action_dim=32` 决定）")
    lines = [
        f"## 阶段2b 目标适应超参数预实验（{now()}）", "",
        f"固定目标: `{C.TARGET_TASKS[C.ADAPT_PILOT_TARGET_T]}`（t={C.ADAPT_PILOT_TARGET_T}，"
        f"5 条示范按 4.2 抽取）；起点: 阶段2 试运行源模型 `stage2_source_fam1_r0`；每组 2000 步后回测 5 回合。",
        f"学习率候选 {lrs}；chunk_size(action_horizon) 候选 {horizons}。",
        "回测种子: " + ", ".join(str(s) for s in C.adapt_pilot_backtest_seeds())
        + "（独立于周期回测 500100+ 与最终评估 100000+1000*t+i）。", "",
    ] + table(rows) + [
        "",
        f"**选定：学习率 {best['lr']}，chunk_size(action_horizon) {best['action_horizon']}**"
        f"（{choice['rule']}）",
        "",
        "### chunk_size 兼容性说明", "",
        ("全部 9 组均以不同的 action_horizon 从同一份源模型检查点继续训练并完成回测，"
         "说明源模型检查点与不同 chunk_size 兼容，因此适应阶段同时搜索学习率与 chunk_size。" + code_note
         if compatible else
         "存在 action_horizon 与源模型不一致而未完成的组：框架要求适应阶段沿用源训练的 chunk_size，"
         "此时仅按学习率维度选择（见上表学习率列）。" + code_note),
        "",
        "选定后全部 30 个目标适应作业使用该组合，已写入 `state/hparams_adapt.json`。",
        "",
    ]
    append_doc(lines)
    print(json.dumps(choice["selected"], ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["1", "2b"], default="1")
    args = parser.parse_args()
    return select_stage1() if args.stage == "1" else select_stage2b()


if __name__ == "__main__":
    raise SystemExit(main())
