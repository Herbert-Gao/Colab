更新时间（带时区）: 2026-10-22T17:25:00+0000
# 超参数预实验记录（服务器 A）

## 本轮口径（运营 2026-10-22 决定）

阶段1（源训练超参预实验）与阶段2b（目标适应超参预实验）**本轮延后**：运营指示「直接使用 openpi 官方的参数、
全量 15000 步直接进行训练」，不再跑预实验网格。因此本轮**全部源模型与微调作业统一使用 openpi 官方超参**
（`peak_lr 2.5e-05`、`action_horizon 10`、batch 32、warmup 1000、cosine decay 30000→2.5e-06、ema_decay 0.99，
见 `openpi/training/config.py` 的 `CosineDecaySchedule` 默认值与 `pi05_aloha_robotwin_h10` 模型配置）。

两个预实验作业组（阶段1 九组、阶段2b 九组）的记录保留在 `state/jobs/`，状态为 `deferred`，随时可恢复：
- 恢复方式：把 `state/jobs/stage1_*.json` / `state/jobs/stage2b_*.json` 的 `status` 改回 `pending`，
  再用 `bash campaign/queue.sh 1` / `bash campaign/queue.sh 4` 续跑；选参由
  `python campaign/select_hparams.py --stage 1|2b` 完成（写入 `state/hparams.json` / `state/hparams_adapt.json`）。
- 恢复后的选择规则不变：5 回合成功率最高 → 2000 步 loss（最后 500 次更新均值）更低 → 最接近配置基准值；
  阶段2b 若出现 action_horizon 与源模型不兼容而未完成的组，则按规范只按学习率维度选择并写明依据。

## 阶段1 旧种子轮次对照（已作废，仅作历史）

第一次阶段1 预实验按旧口径使用回测种子 500000+i（与试运行阶段 r=0 的周期回测种子重叠）。
本轮该组结果作废，不参与任何选参。下表的学习率取自各组训练日志的启动行（权威证据）——
作业记录里的 `peak_lr` 曾在选参冻结后被一次计划重写覆盖成同一值，学习率以日志为准：

| 组 | 学习率（日志） | action_horizon | 5 回合成功率 | 2000 步 loss（最后 500 步均值） |
|---|---:|---:|---:|---:|
| stage1legacy_lr0.5x_h10 | 1.25e-05 | 10 | 1.0 | 0.028099135780707003 |
| stage1legacy_lr0.5x_h15 | 1.25e-05 | 15 | 0.8 | 0.034478461315855385 |
| stage1legacy_lr0.5x_h5 | 1.25e-05 | 5 | 0.8 | 0.017602493797428904 |
| stage1legacy_lr1x_h10 | 2.5e-05 | 10 | 1.0 | 0.03159422889351845 |
| stage1legacy_lr1x_h15 | 2.5e-05 | 15 | 0.8 | 0.03914982818253338 |
| stage1legacy_lr1x_h5 | 2.5e-05 | 5 | 0.4 | 0.019694991181604563 |
| stage1legacy_lr2x_h10 | 5e-05 | 10 | 1.0 | 0.03861285316385329 |
| stage1legacy_lr2x_h15 | 5e-05 | 15 | 0.8 | 0.04872591815516353 |
| stage1legacy_lr2x_h5 | 5e-05 | 5 | 0.6 | 0.024560658968985082 |

对照结论（仅供理解配方）：三个 `action_horizon=10` 的组成功率并列 1.0，并列时按 2000 步 loss 最低者胜出
（1.25e-05 组 loss 0.0281 最低）。这与本轮直接采用官方 `action_horizon 10`、官方 `peak_lr 2.5e-05` 的选择方向一致。
