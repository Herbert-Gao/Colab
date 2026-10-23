# 服务器 A：π0.5 / RoboTwin ALOHA 训练工作区

工作目录 `/data/szgx/gaohang/pi05_30`，机体唯一为 RoboTwin **aloha-agilex**（ALOHA 双臂）。
训练、仿真评估、归一化统计使用同一套关节/相机/夹爪映射。

## 目录

| 路径 | 内容 |
|---|---|
| `campaign/` | 执行脚本（见下） |
| `datasets/lerobot/` | 本次实验用 LeRobot 数据集（3 族源模型 + 10 个目标子集 + 1 个预实验） |
| `assets/RoboTwin_lerobot_v30/norm_stats.json` | 20 个源任务 × 50 条示范的**统一**归一化统计量（目标任务不参与） |
| `runs/` | 检查点（`stage1/`、`stage2/`、`stage2b/`、`stage3/`），里程碑与最终权重为 params-only |
| `eval/` | 回测与最终评估结果 |
| `logs/` | 每个作业的训练日志、全精度 loss 轨迹、队列日志 |
| `state/` | 作业记录（`state/jobs/<作业ID>.json`）、计划、冻结超参、种子与示范清单 |
| `docs/` | 进度与交付文档 |
| `snapshots/` | 环境/配置冻结快照（pip freeze、权重清单、脚本摘要） |
| `deliverables/` | 机器可读作业表 + 中文摘要 |

## 脚本

| 脚本 | 作用 |
|---|---|
| `campaign/prepare_data.py` | 构建/校验 LeRobot 数据集（`datasets`/`stats`/`verify`） |
| `campaign/plan.py` | 生成全部作业记录（`state/jobs/*.json`） |
| `campaign/train_job.py` | 单个训练作业（调用 openpi `scripts/train.py`，附全精度 loss 轨迹） |
| `campaign/run_job.sh` | **单作业全流程**：训练 → 每 2000 步回测 → 里程碑/最终权重快照 → 检查点清理 → 写文档 |
| `campaign/queue.sh` | 阶段队列：依次执行该阶段所有作业（源模型优先于适应作业） |
| `campaign/run_stage.sh` | 无人值守驱动：阶段 1→2→2b→3（队列阶段号 1/2/4/3）；本轮已停用，预实验与微调作业延后 |
| `campaign/cotrain.sh` | **本轮驱动**：并行训练多个作业，每个作业用作业记录里的卡组（S2: GPU0-3，S3: GPU4-7），失败自动重试，完成后写文档并发飞书汇总 |
| `campaign/watchdog.sh` | 看门狗：驱动缺失自动重启、卡住的作业自动释放、动作飞书通知 |
| `campaign/backtest.py` | 对一个检查点跑指定任务的 5 回合回测 |
| `campaign/final_eval.sh` / `campaign/final_eval.py` | 最终评估：每个交付检查点 100 回合 + 源模型 0 步裸测（**本轮不执行**） |
| `campaign/select_hparams.py` | 选参：`--stage 1` 写 `state/hparams.json`（源训练），`--stage 2b` 写 `state/hparams_adapt.json`（目标适应）；结果追加到 `docs/02_hparam_pilot.md` |
| `campaign/manifest.py` | 写 `docs/models_manifest.md`（30 个微调模型 + 3 个源模型）并校验检查点路径；`--notify` 发「全部完成」飞书通知 |
| `campaign/failures.py` | 累计失败计数与飞书升级（≥10 次失败通知用户，不中断循环） |
| `campaign/snapshot.py` | params-only 权重快照：等源目录稳定 + 逐文件清单比对 + Orbax restore 校验 |
| `campaign/cleanup_stage.py` | 阶段清理：阶段 1 只留选中的组；阶段 2/2b 产物不保留（带删除保护） |
| `campaign/jobctl.py` | 作业记录读写（`field`/`new-checkpoints`/`record`/`snapshot`/`cleanup`/`set-hparams`） |
| `campaign/write_docs.py` | 写 `docs/00_progress.md` 与 `docs/jobs/<作业ID>.md` |
| `campaign/preflight.py` | 阶段 0 的 12 项检查，产出 `docs/01_preflight.md` |
| `campaign/smoke_validate.py` | 重跑需要 GPU 的阶段 0 验证（训练冒烟 / 评测冒烟 / 并行 10 分钟） |
| `campaign/notify_channel.py` | 飞书通知（lark-im bot 身份，带回执） |
| `campaign/deliverables.py` | 生成 `deliverables/jobs.json` 与 `deliverables/summary_zh.md` |

## 常用命令

```bash
# 看总览
cat docs/00_progress.md

# 看某个作业
cat docs/jobs/<作业ID>.md

# 队列状态 / 继续推进
tail -f logs/queue_stage1.log
bash campaign/queue.sh 1          # 续跑阶段 1（跳过已完成作业）
bash campaign/queue.sh 2          # 阶段2 端到端试运行
bash campaign/queue.sh 4          # 阶段2b 目标适应超参预实验
bash campaign/queue.sh 3          # 阶段3 正式训练
bash campaign/run_stage.sh 1 2 4 3  # 无人值守跑完四个阶段

# 单作业状态
python campaign/jobctl.py status <作业ID>
python campaign/jobctl.py new-checkpoints <作业ID>   # 尚未回测的检查点
```

## 关键约定

- **步数**：检查点目录名即步数；`save_interval` 阶段1/2/2b 为 2000，阶段3 为 500
  （为精确产出 4.1 节的 7500/15000/30000 里程碑），**回测每 2000 步一次**（§5/§6 口径）。
- **种子**（4.2 固定口径）：训练种子 = 1（试运行 0）；阶段1 回测 = `900000+i`；阶段2b 回测 = `910000+i`；
  周期回测 = `500100+i`；最终评估 = `100000+1000*t+i`（本轮不执行）；
  目标 5 条示范 = `numpy.random.default_rng(1000+t)` 无放回抽 5 条（清单在 `state/target_demo_ids.json`）。
- **本轮范围（运营 2026-10-22 / 10-23 两次改方案）**：源模型用 openpi 官方超参
  （peak_lr 2.5e-05、action_horizon 10、batch 32、warmup 1000、cosine decay 30000→2.5e-06、ema 0.99）
  训 **15000 步**；**co-train 两个模型**（S2 用 GPU0-3、S3 用 GPU4-7，各 4 卡 FSDP）；
  阶段1/2/2b 预实验、阶段0 的 GPU 冒烟复核与最终评估**本轮全部延后**（作业记录状态 `deferred`）；
  **微调矩阵按运营指示恢复：30 个适应作业（3 起点 × 10 目标）两两共训，步长 500→2000、每 500 步存一次 .ckpt**
  （上限 2000 步，无里程碑副本，交付权重=最终权重；2000 步上限下规范的早停不会触发）。
  S1（族群①）沿用改方案前已开跑的一次训练（学习率 1.25e-05），按运营指示在 25825 步停止（状态 `stopped`），
  交付其 7500 / 15000 两个里程碑权重；本轮实际训练的是 S2（族群②）与 S3（族群③），族③ 另有一段 15000 步续训
  （`stage3_source_fam3_r1_long`，等效 30000 步）。
- **检查点**：滚动恢复点只保留最近 2 个已回测点 + 最新点；里程碑/最终权重仅存 params（12 GB）并经 Orbax 校验；
  其余检查点回测完成即删，全部动作记入 `docs/cleanup_log.md`。
- **GPU**：每个作业的卡组来自作业记录（`train_gpus`/`fsdp_devices`/`policy_gpus`/`sim_gpus`）；
  回测与本作业的训练互斥（训练 SIGSTOP，回测只用本作业的卡组）；策略服务显存不足时自动回退到 CPU 推理。
- **早停**：只看成功率——基线取 10000 步检查点，12000 步起连续 3 个检查点未严格提升即停（loss 指标仍全程记录）。
- **失败处理**：单作业失败从最近恢复点重试最多 2 次；仍失败则标记 failed 并继续其他作业，依赖它的适应作业标记 skipped；
  累计失败 ≥10 次时飞书通知用户（不中断循环）。
- **凭据**：不写入任何日志、产物或消息。

## 已发生的事故（详见 `docs/incidents.md`）

- Orbax 快照竞态导致权重缺 `ocdbt.process_0` → 快照必须等源目录稳定 + 逐文件比对 + restore 校验。
- `cleanup_stage.py` 曾把空路径当成 `'.'` 递归删掉整个工作目录 → 已加 `safe_target()` 保护
  （空路径、工作目录本身、工作目录之外一律拒绝删除）。
