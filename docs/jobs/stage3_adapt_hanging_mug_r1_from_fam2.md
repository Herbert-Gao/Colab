更新时间（带时区）: 2026-10-24T13:05:52+0000

# stage3_adapt_hanging_mug_r1_from_fam2

- 阶段: 3 / 类型: adapt / 重复种子 r=1
- 源族: 2 / 目标任务: hanging_mug
- 数据: pi05_30_aloha_target_hanging_mug_n5 / 示范编号 [8, 12, 13, 14, 27]
- 初始权重: stage3_source_fam2_r1
- 步数上限: 2001；训练种子: 1
- 学习率: 2.5e-05；chunk_size(action_horizon): 10
- 回测任务: hanging_mug；回测种子: [500100, 500101, 500102, 500103, 500104]
- 状态: completed

| 步数 | loss(500步均值) | 各任务成功数/回合 | 平均成功率 | 检查点 | 早停判断 |
|---:|---:|---|---:|---|---|
| 500 | 0.19189288749365147 | hanging_mug:0/5 | 0.0 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_hanging_mug_from_fam2/500 | 未提升0/3 loss未达标 |
| 1000 | 0.036684135431423785 | hanging_mug:0/5 | 0.0 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_hanging_mug_from_fam2/1000 | 未提升0/3 loss未达标 |
| 1500 | 0.02882726634480059 | hanging_mug:0/5 | 0.0 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_hanging_mug_from_fam2/1500 | 未提升0/3 loss未达标 |
| 2000 | 0.02520696119219065 | hanging_mug:0/5 | 0.0 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_hanging_mug_from_fam2/2000 | 未提升0/3 loss未达标 |

最终检查点: {"step": 2000, "params_only": {"path": "/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_hanging_mug_from_fam2_final_step2000", "bytes": 12440418316, "files": 24, "restored_leaves": 51, "verified": true, "source_files": 24}}
