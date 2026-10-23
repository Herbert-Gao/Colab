"""Write the job document and refresh the overall progress document."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def write_job_doc(job: dict) -> None:
    lines = [
        f"更新时间（带时区）: {now()}", "",
        f"# {job['job_id']}", "",
        f"- 阶段: {job.get('stage')} / 类型: {job.get('kind')} / 重复种子 r={job.get('repeat')}",
        f"- 源族: {job.get('family')} / 目标任务: {job.get('task')}",
        f"- 数据: {job.get('repo_id')}" + (f" / 示范编号 {job.get('demo_ids')}" if job.get("demo_ids") else ""),
        f"- 初始权重: {job.get('init_params') or job.get('init_from_job')}",
        f"- 步数上限: {job.get('max_steps')}；训练种子: {job.get('seed')}",
        f"- 学习率: {job.get('peak_lr')}；chunk_size(action_horizon): {job.get('action_horizon')}",
        f"- 回测任务: {', '.join(job.get('backtest_tasks', []))}；回测种子: {job.get('backtest_seeds')}",
        f"- 状态: {job.get('status')}", "",
        "| 步数 | loss(500步均值) | 各任务成功数/回合 | 平均成功率 | 检查点 | 早停判断 |",
        "|---:|---:|---|---:|---|---|",
    ]
    for entry in job.get("history", []):
        per_task = " ".join(f"{task}:{info['successes']}/{info['episodes']}"
                            for task, info in entry["per_task"].items())
        verdict = entry.get("early_stop", {})
        decision = "停止" if verdict.get("stop") else (
            f"未提升{job.get('no_improve_count', 0)}/{C.EARLY_STOP_PATIENCE} "
            f"loss{'达标' if verdict.get('loss_condition_met') else '未达标'}")
        loss = (entry.get("loss") or {}).get("loss_mean")
        lines.append(f"| {entry['step']} | {loss} | {per_task} | {entry['mean_success_rate']} | "
                     f"{entry.get('checkpoint', '')} | {decision} |")
    if job.get("early_stop"):
        lines += ["", f"早停: {json.dumps(job['early_stop'], ensure_ascii=False)}"]
    if job.get("final_checkpoint"):
        lines += ["", f"最终检查点: {json.dumps(job['final_checkpoint'], ensure_ascii=False)}"]
    if job.get("milestones"):
        lines += ["", f"里程碑（仅权重）: {json.dumps(job['milestones'], ensure_ascii=False)}"]
    (C.JOBS_DOCS / f"{job['job_id']}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_progress_doc() -> None:
    jobs = []
    for path in sorted((C.STATE / "jobs").glob("*.json")):
        try:
            job = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        if job.get("legacy"):
            continue
        jobs.append(job)

    def frozen(name: str) -> str:
        path = C.STATE / name
        if not path.is_file():
            return "未冻结"
        data = json.loads(path.read_text())
        return f"学习率 {data.get('peak_lr')}，chunk_size(action_horizon) {data.get('action_horizon')}"

    frozen_source = frozen("hparams.json")
    frozen_adapt = frozen("hparams_adapt.json")
    lines = [
        f"更新时间（带时区）: {now()}", "",
        "# pi0.5 / RoboTwin ALOHA 训练总览（服务器 A）", "",
        "- 机体: aloha-agilex（ALOHA 双臂；训练、仿真评估、归一化一致）",
        f"- 训练卡 {C.TRAIN_GPUS}（{C.FSDP_DEVICES} 卡 FSDP），仿真卡 {C.SIM_GPU}，策略服务卡 {C.POLICY_GPUS}",
        f"- 作业总数: {len(jobs)}",
        "- 状态分布: " + ", ".join(
            f"{status}={sum(1 for j in jobs if j.get('status') == status)}"
            for status in sorted({j.get('status') for j in jobs})), "",
        f"- 本轮范围: 阶段0/1/2/2b/3，源模型 {len(C.SOURCE_FAMILIES)} 个（族群 "
        f"{'、'.join(C.SOURCE_FAMILIES)}），目标适应 {len(C.TARGET_TASKS) * len(C.ADAPT_SOURCE_FAMILIES)} 个"
        f"（{len(C.TARGET_TASKS)} 目标 × {len(C.ADAPT_SOURCE_FAMILIES)} 起点），本轮不执行最终评估与 0 步裸测",
        f"- 冻结参数: 源训练 {frozen_source}；目标适应 {frozen_adapt}",
        f"- 种子: 训练 {C.FORMAL_REPEAT}（试运行 {C.TRIAL_REPEAT}）／阶段1 回测 {C.PILOT_BACKTEST_SEED_BASE}+i／"
        f"阶段2b 回测 {C.ADAPT_PILOT_BACKTEST_SEED_BASE}+i／周期回测 {C.PERIODIC_BACKTEST_SEED_BASE}+i／"
        f"最终评估（本轮不用）{C.final_eval_seeds(0)[0]}+1000*t+i",
        "- 微调模型清单: `docs/models_manifest.md`",
        "| 作业ID | 状态 | 当前步数 | 最新成功率 | 最新loss | 开始 | 结束 |",
        "|---|---|---:|---:|---:|---|---|",
        "",
        "## 检查点保留与清理（4.1）",
        "",
        "- 滚动恢复点: 每 1000 步存一个，只保留最近 2 个已回测恢复点 + 最新恢复点；回测结果校验落盘后立即删除更旧的恢复点",
        "- 周期回测: 每 2000 步 5 回合（§5/§6 的 2000 步区间口径），回测与训练并行（策略服务与仿真占用训练器未预留的显存）",
        "- 里程碑: 7500 / 15000 / 30000 步与早停最终步，存 params-only 副本并长期保留",
        "- 源模型最终权重: 每族一份 params-only 副本，本服务器所有适应作业结束后仍保留",
        "- 失败/暂停作业: 保留最后一个有效恢复点，禁止清理",
        "- 每次保存前检查磁盘余量；不足「一个检查点 × 3」时暂停作业并飞书反馈，不删保留类检查点",
        "- 每条删除记入 `docs/cleanup_log.md`（路径、步数、原因、释放大小）",
        "",
    ]
    for job in jobs:
        history = job.get("history") or []
        latest = history[-1] if history else {}
        loss = (latest.get("loss") or {}).get("loss_mean")
        lines.append(f"| {job.get('job_id')} | {job.get('status')} | "
                     f"{latest.get('step', job.get('current_step', 0))} | "
                     f"{latest.get('mean_success_rate', '-')} | {loss if loss is not None else '-'} | "
                     f"{job.get('started', '-')} | {job.get('finished', '-')} |")
    usage = shutil.disk_usage(C.WORK)
    sources = [j for j in jobs if j.get("kind") == "source"]
    adapts = [j for j in jobs if j.get("kind") == "adapt"]
    delivered = [j for j in jobs if j.get("status") in ("completed", "early_stopped")]
    lines += [
        "", "## 总汇总", "",
        f"- 源模型: {len(sources)} 个（完成 {sum(1 for j in sources if j.get('status') in ('completed', 'early_stopped'))}）",
        f"- 微调模型（目标适应）: {len(adapts)} 个（完成 {sum(1 for j in adapts if j.get('status') in ('completed', 'early_stopped'))}，"
        f"延后 {sum(1 for j in adapts if j.get('status') == 'deferred')}）",
        f"- 延后作业（预实验与微调）: {sum(1 for j in jobs if j.get('status') == 'deferred')}",
        f"- 终态作业合计: {len(delivered)} / {len(jobs)}",
        f"- 微调模型清单: `docs/models_manifest.md`（模型ID／起点模型／目标任务／实际步数／早停／检查点路径／最近回测成功率）",
        f"- 磁盘：卷剩余 {usage.free / 1024 ** 3:.0f} GiB", "",
    ]
    (C.DOCS / "00_progress.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-id", default="")
    args = parser.parse_args()
    if args.job_id:
        job = json.loads((C.STATE / "jobs" / f"{args.job_id}.json").read_text())
        write_job_doc(job)
    write_progress_doc()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
