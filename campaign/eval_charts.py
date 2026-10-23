"""Draw the charts of the generalization test.

Three figures (PNG) plus the training curves of the source models:

* ``docs/eval_task_bars.png``   - the per-task success rate of both models,
                                  the in-family tasks marked;
* ``docs/eval_family_matrix.png`` - the family-to-family transfer matrix;
* ``docs/eval_in_vs_cross.png`` - in-family versus cross-family success rate;
* ``docs/eval_training_curves.png`` - the backtest success rate and the loss of
  the three source models over their training steps.

The Chinese glyphs come from the Droid Sans Fallback font in
``assets/fonts/cjk.ttf``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
import jobctl  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
FONT = ROOT / "assets" / "fonts" / "cjk.ttf"
RESULTS = ROOT / "eval" / "final" / "source_models_eval.json"
MODELS = ["stage3_source_fam1_r1", "stage3_source_fam2_r1"]
NAMES = {"stage3_source_fam1_r1": "S1（族群①）", "stage3_source_fam2_r1": "S2（族群②）",
         "stage3_source_fam3_r1": "S3（族群③）"}
COLORS = ["#2f6fd0", "#e08b2f", "#3f9d5b"]


def models_with_results(results: dict) -> list[str]:
    """The models that were scored, in the order they should appear."""
    ordered = [m for m in ("stage3_source_fam1_r1", "stage3_source_fam2_r1",
                            "stage3_source_fam3_r1") if results.get(m)]
    return ordered or MODELS


def setup() -> None:
    if FONT.is_file():
        font_manager.fontManager.addfont(str(FONT))
        family = font_manager.FontProperties(fname=str(FONT)).get_name()
        plt.rcParams["font.family"] = family
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 140
    plt.rcParams["savefig.bbox"] = "tight"


def load() -> dict:
    """The per-model rows of the evaluation (the file holds a wrapper)."""
    if not RESULTS.is_file():
        raise FileNotFoundError(RESULTS)
    return json.loads(RESULTS.read_text()).get("results", {})


def task_bars(results: dict) -> Path:
    tasks = [C.TARGET_TASKS[t] for t in range(len(C.TARGET_TASKS))]
    families = [C.TARGET_FAMILY[t] for t in range(len(C.TARGET_TASKS))]
    models = models_with_results(results)
    fig, ax = plt.subplots(figsize=(9.5, 4.2))
    width = 0.8 / max(len(models), 1)
    for index, model in enumerate(models):
        rows = {r["target_index"]: r for r in results.get(model, [])}
        values = [rows.get(t, {}).get("success_rate", 0.0) * 100 for t in range(len(tasks))]
        offsets = [i + (index - (len(models) - 1) / 2) * width for i in range(len(tasks))]
        bars = ax.bar(offsets, values, width, label=NAMES.get(model, model), color=COLORS[index])
        for bar, value in zip(bars, values):
            if value > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, value + 1.2, f"{value:.0f}",
                        ha="center", fontsize=7.5)
    for index, family in enumerate(families):
        if family == families[0] or family == "2":
            continue
        ax.axvline(index - 0.5 + 0.5, color="#c8ced6", lw=0.8)
    ax.set_xticks(range(len(tasks)))
    ax.set_xticklabels([f"{task}  (族{family})" for task, family in zip(tasks, families)],
                       fontsize=7.2, rotation=32, ha="right")
    ax.set_ylabel("成功率 (%)")
    ax.set_title("S1 / S2 在 10 个目标任务上的成功率（每任务 100 回合）", fontsize=11)
    ax.set_ylim(0, 108)
    ax.legend(fontsize=8.5, loc="upper right")
    ax.grid(axis="y", color="#e6e9ee", lw=0.7)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    out = DOCS / "eval_task_bars.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def family_matrix(results: dict) -> Path:
    families = ["1", "2", "3", "4", "5"]
    models = models_with_results(results)
    fig, axes = plt.subplots(1, len(models), figsize=(5.2 * len(models), 3.6), squeeze=False)
    axes = axes[0]
    for index, model in enumerate(models):
        ax = axes[index]
        matrix = []
        for family in families:
            rows = [r for t, r in enumerate(results.get(model, [])) if C.TARGET_FAMILY[t] == family]
            episodes = sum(r["episodes"] for r in rows)
            wins = sum(r["successes"] for r in rows)
            matrix.append(wins / episodes * 100 if episodes else 0.0)
        image = ax.imshow([matrix], cmap="Blues", vmin=0, vmax=100, aspect="auto")
        ax.set_xticks(range(len(families)))
        ax.set_xticklabels([f"族群{f}" for f in families], fontsize=8.5)
        ax.set_yticks([0])
        ax.set_yticklabels([NAMES.get(model, model)], fontsize=9)
        for column, value in enumerate(matrix):
            ax.text(column, 0, f"{value:.0f}%", ha="center", va="center", fontsize=9,
                    color="white" if value > 55 else "#1c2530")
        ax.set_title(f"目标所属族群 → 成功率（{NAMES.get(model, model)}）", fontsize=9.5)
    fig.colorbar(image, ax=axes, fraction=0.02, pad=0.02).set_label("成功率 (%)", fontsize=8)
    out = DOCS / "eval_family_matrix.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def in_vs_cross(results: dict) -> Path:
    models = models_with_results(results)
    fig, ax = plt.subplots(figsize=(3.7 * len(models) + 1.2, 3.9))
    labels, inside, outside, baseline = [], [], [], []
    for model in models:
        job = jobctl.load(model)
        family = job.get("family")
        rows = [(t, r) for t, r in enumerate(results.get(model, []))]
        in_rows = [r for t, r in rows if C.TARGET_FAMILY[t] == family]
        out_rows = [r for t, r in rows if C.TARGET_FAMILY[t] != family]

        def rate(items):
            episodes = sum(r["episodes"] for r in items)
            wins = sum(r["successes"] for r in items)
            return wins / episodes * 100 if episodes else 0.0

        # The model's score on its own four training tasks (the delivered
        # weights, the periodic backtest of the last checkpoint).
        history = job.get("history") or []
        final_step = (job.get("final_checkpoint") or {}).get("step")
        scored = [h for h in history if final_step is not None and h.get("step") == final_step]
        own = scored[0]["mean_success_rate"] * 100 if scored else 0.0
        labels.append(NAMES.get(model, model))
        inside.append(rate(in_rows))
        outside.append(rate(out_rows))
        baseline.append(own)
    positions = range(len(labels))
    ax.bar([p - 0.28 for p in positions], inside, 0.26, label="族内目标任务（2 个）", color="#2f6fd0")
    ax.bar([p for p in positions], outside, 0.26, label="族间目标任务（8 个）", color="#b9c3cf")
    ax.bar([p + 0.28 for p in positions], baseline, 0.26, label="本族训练任务（基线，20 回合）",
           color="#3f9d5b")
    for p, value in zip(positions, inside):
        ax.text(p - 0.28, value + 1.5, f"{value:.1f}%", ha="center", fontsize=8)
    for p, value in zip(positions, outside):
        ax.text(p, value + 1.5, f"{value:.1f}%", ha="center", fontsize=8)
    for p, value in zip(positions, baseline):
        ax.text(p + 0.28, value + 1.5, f"{value:.1f}%", ha="center", fontsize=8)
    ax.set_xticks(list(positions))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("成功率 (%)")
    ax.set_title("族内 vs 族间泛化（与本族训练任务基线对照）", fontsize=11)
    ax.legend(fontsize=8)
    ax.grid(axis="y", color="#e6e9ee", lw=0.7)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    out = DOCS / "eval_in_vs_cross.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def training_curves() -> Path:
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.5))
    palette = {"stage3_source_fam1_r1": "#2f6fd0", "stage3_source_fam2_r1": "#e08b2f",
               "stage3_source_fam3_r1": "#3f9d5b", "stage3_source_fam3_r1_long": "#8b5cf6"}
    for model, color in palette.items():
        job = jobctl.load(model)
        history = job.get("history") or []
        if not history:
            continue
        steps = [h["step"] for h in history]
        success = [h["mean_success_rate"] * 100 for h in history]
        loss = [(h.get("loss") or {}).get("loss_mean") for h in history]
        axes[0].plot(steps, success, marker="o", ms=3, color=color, label=NAMES.get(model, model))
        axes[1].plot(steps, loss, marker="o", ms=3, color=color, label=NAMES.get(model, model))
        per_task = history[-1].get("per_task", {})
        labels = list(per_task)
        block = list(palette).index(model) * len(labels)
        positions = [i + block for i in range(len(labels))]
        axes[2].barh(positions, [info["success_rate"] * 100 for info in per_task.values()],
                     height=0.62, color=color, alpha=0.9)
        for position, task in zip(positions, labels):
            axes[2].text(-3, position, task, ha="right", va="center", fontsize=7.4)
    axes[2].set_yticks([])
    axes[0].set_title("周期回测成功率", fontsize=10)
    axes[1].set_title("训练 loss（最后 500 步均值）", fontsize=10)
    axes[2].set_title("各源任务成功率（末次回测）", fontsize=10)
    for ax in axes[:2]:
        ax.set_xlabel("训练步数", fontsize=8.5)
        ax.set_ylabel("百分比 / loss", fontsize=8.5)
        ax.grid(color="#e6e9ee", lw=0.7)
        ax.set_axisbelow(True)
        ax.legend(fontsize=7.5)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
    axes[2].set_xlabel("成功率 (%)", fontsize=8.5)
    axes[2].set_xlim(-42, 108)
    axes[2].set_ylim(-0.8, 11.8)
    axes[2].grid(axis="x", color="#e6e9ee", lw=0.7)
    axes[2].set_axisbelow(True)
    for spine in ("top", "right"):
        axes[2].spines[spine].set_visible(False)
    out = DOCS / "eval_training_curves.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def main() -> int:
    setup()
    results = load()
    for path in (task_bars(results), family_matrix(results), in_vs_cross(results),
                 training_curves()):
        print(f"chart -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
