"""Write the generalization report of the source models.

Reads the evaluation results (``eval/final/source_models_eval.json``) and the
source models' own-family backtests, and writes ``docs/eval_report.md``:

* the 2 models x 10 target tasks table (100 episodes each),
* the in-family versus cross-family comparison per model,
* the family-to-family transfer matrix,
* the generalization gap against the models' own-family performance.

    python eval_report.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
import jobctl  # noqa: E402

RESULTS = C.EVAL / "final" / "source_models_eval.json"
DOC = C.DOCS / "eval_report.md"
MODEL_NAMES = {
    "stage3_source_fam1_r1": "S1（族群① 搬运定位）",
    "stage3_source_fam2_r1": "S2（族群② 容器复合）",
    "stage3_source_fam3_r1": "S3（族群③ 排列堆叠）",
}


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def own_family_score(job_id: str) -> tuple[float, str]:
    """The model's score on its own four source tasks (the delivered weights)."""
    job = jobctl.load(job_id)
    final = (job.get("final_checkpoint") or {}).get("step")
    history = job.get("history") or []
    scored = [h for h in history if final is not None and h.get("step") == final]
    if not scored:
        scored = history[-1:] if history else []
    if not scored:
        return 0.0, "-"
    per = "，".join(f"{task} {info['successes']}/{info['episodes']}"
                    for task, info in scored[0]["per_task"].items())
    return scored[0]["mean_success_rate"], per


def main() -> int:
    if not RESULTS.is_file():
        print(f"{RESULTS} missing - run campaign/eval_sources.py first")
        return 2
    payload = json.loads(RESULTS.read_text())
    results = payload.get("results") or {}
    if not results:
        print("no results in the evaluation file")
        return 2

    models = list(results)
    lines = [
        f"更新时间（带时区）: {now()}", "",
        "# 源模型跨任务泛化测试报告（服务器 A）", "",
        "## 测试设置", "",
        f"- 模型: {', '.join(MODEL_NAMES.get(m, m) for m in models)}（各自训练于 4 个源任务 × 50 条示范，官方超参、15000 步）",
        f"- 任务: 10 个目标测试任务（族群①–⑤ 各 2 个）",
        f"- 回合: 每模型每任务 {payload.get('episodes_per_task', C.FINAL_EPISODES)} 回合，共 "
        f"{len(models)} × {len(C.TARGET_TASKS)} × {payload.get('episodes_per_task', C.FINAL_EPISODES)} = "
        f"{len(models) * len(C.TARGET_TASKS) * payload.get('episodes_per_task', C.FINAL_EPISODES)} 回合",
        f"- 场景种子: `{payload.get('seeds')}`（同一目标对所有模型使用同一组种子，构成配对比较）",
        "- 评测配置: RoboTwin aloha-agilex 仿真环境，与训练一致的相机/动作定义与控制频率；每回合独立重置",
        "- 说明: 本轮不做最终评估的 0 步裸测；微调矩阵已按运营指示在保存权重后停止", "",
    ]

    # --- per task table -----------------------------------------------------
    lines += ["## 逐任务成功率", "",
              "| 目标任务 | 所属族群 | " + " | ".join(MODEL_NAMES.get(m, m) for m in models) + " |",
              "|---|---|" + "---|" * len(models)]
    per_task_rows = []
    for t, task in enumerate(C.TARGET_TASKS):
        cells = []
        for model in models:
            row = next((r for r in results[model] if r.get("target_index") == t), None)
            cells.append(f"{row['successes']}/{row['episodes']}（{row['success_rate'] * 100:.0f}%）" if row else "-")
        per_task_rows.append((task, C.TARGET_FAMILY[t], cells))
        lines.append(f"| `{task}` | 族群{C.TARGET_FAMILY[t]} | " + " | ".join(cells) + " |")
    totals = []
    for model in models:
        episodes = sum(r["episodes"] for r in results[model])
        wins = sum(r["successes"] for r in results[model])
        totals.append((wins, episodes, wins / episodes if episodes else 0.0))
    lines.append("| **全部 10 个任务** | - | " + " | ".join(
        f"**{w}/{e}（{r * 100:.1f}%）**" for w, e, r in totals) + " |")
    lines += ["", "![逐任务成功率](eval_task_bars.png)", ""]

    # --- in-family versus cross-family -------------------------------------
    lines += ["", "## 族内泛化 vs 族间泛化", "",
              "「族内」= 测试任务与模型训练用的族群相同；「族间」= 测试任务属于其它族群（未见过的任务）。", "",
              "| 模型 | 训练族群 | 族内任务 | 族内成功率 | 族间任务 | 族间成功率 | 族内-族间差 | 本族训练任务成功率 |",
              "|---|---|---|---:|---|---:|---:|---:|"]
    for model in models:
        family = jobctl.load(model).get("family")
        inside = [(t, r) for t, r in enumerate(results[model])
                   if C.TARGET_FAMILY[t] == family]
        outside = [(t, r) for t, r in enumerate(results[model])
                   if C.TARGET_FAMILY[t] != family]
        def agg(rows):
            episodes = sum(r["episodes"] for _, r in rows)
            wins = sum(r["successes"] for _, r in rows)
            return wins, episodes, (wins / episodes if episodes else 0.0)
        wi, ei, ri = agg(inside)
        wo, eo, ro = agg(outside)
        own_score, own_detail = own_family_score(model)
        lines.append(
            f"| {MODEL_NAMES.get(model, model)} | 族群{family} | "
            f"{', '.join(f'`{C.TARGET_TASKS[t]}`' for t, _ in inside)} | {ri * 100:.1f}%（{wi}/{ei}） | "
            f"{len(outside)} 个任务 | {ro * 100:.1f}%（{wo}/{eo}） | {(ri - ro) * 100:+.1f} pt | "
            f"{own_score * 100:.1f}%（{own_detail}） |")

    # --- family to family matrix -------------------------------------------
    lines += ["", "![族内 vs 族间](eval_in_vs_cross.png)", "",
              "## 族群 × 族群 转移矩阵（目标任务所属族群 → 成功率）", ""]
    header = "| 模型 | " + " | ".join(f"族群{f}（{len([t for t in range(10) if C.TARGET_FAMILY[t] == f])} 个任务）"
                                     for f in ("1", "2", "3", "4", "5")) + " |"
    lines += [header, "|---|" + "---|" * 5]
    for model in models:
        cells = []
        for family in ("1", "2", "3", "4", "5"):
            rows = [r for t, r in enumerate(results[model]) if C.TARGET_FAMILY[t] == family]
            episodes = sum(r["episodes"] for r in rows)
            wins = sum(r["successes"] for r in rows)
            cells.append(f"{wins / episodes * 100:.1f}%（{wins}/{episodes}）" if episodes else "-")
        lines.append(f"| {MODEL_NAMES.get(model, model)} | " + " | ".join(cells) + " |")

    lines += ["", "![族群 × 族群 转移矩阵](eval_family_matrix.png)", "",
              "## 源模型训练过程（周期回测）", "",
              "![源模型训练曲线](eval_training_curves.png)", "",
              "## 结论要点", ""]
    for model in models:
        family = jobctl.load(model).get("family")
        inside = [r for t, r in enumerate(results[model]) if C.TARGET_FAMILY[t] == family]
        outside = [r for t, r in enumerate(results[model]) if C.TARGET_FAMILY[t] != family]
        def agg(rows):
            episodes = sum(r["episodes"] for r in rows)
            wins = sum(r["successes"] for r in rows)
            return (wins / episodes if episodes else 0.0), wins, episodes
        ri, wi, ei = agg(inside)
        ro, wo, eo = agg(outside)
        own, _ = own_family_score(model)
        lines.append(
            f"- **{MODEL_NAMES.get(model, model)}**：本族训练任务 {own * 100:.1f}% → 族内目标任务 {ri * 100:.1f}%"
            f" → 族间目标任务 {ro * 100:.1f}%；族内相对族间 {(ri - ro) * 100:+.1f} pt，"
            f"相对本族训练任务 {(ri - own) * 100:+.1f} pt。")
    lines += [
        "- 族内与族间之差即「同族技能迁移」的幅度；相对本族训练任务的下降即「同族任务之间的分布差」幅度。",
        "- 样本口径: 每格 100 回合（族内格为 200 回合，族间格为 800 回合）；"
        "同一目标在两个模型上使用同一组场景种子，可直接配对比较。",
        "",
    ]
    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"report -> {DOC}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
