更新时间（带时区）: 2026-10-21T10:20:27+0000
# stage2_target_place_mouse_pad_r0


- 阶段: 2 / 类型: trial_adapt / 重复种子 r=0
- 源族: 1 / 目标任务: place_mouse_pad
- 数据: pi05_30_aloha_target_place_mouse_pad_r0_n5
- 初始权重: stage2_source_fam1_r0
- 步数上限: 2001；训练种子: 0
- 学习率: 1.25e-05；chunk_size(action_horizon): 10
- 回测任务: place_mouse_pad；回测种子: [500000, 500001, 500002, 500003, 500004]
- 状态: completed

| 步数 | loss(500步均值) | 各任务成功数/回合 | 平均成功率 | 检查点 | 早停判断 |
|---:|---:|---|---:|---|---|
| 2000 | 0.013225813659839332 | place_mouse_pad:1/5 | 0.2 | /data/szgx/gaohang/pi05_30/runs/stage2/pi05_aloha_robotwin_30/aloha_trial_adapt_place_mouse_pad_r0/2000 | 未提升0/3 loss未达标 |

最终检查点: {"step": 2000, "params_only": {"path": "/data/szgx/gaohang/pi05_30/runs/stage2/pi05_aloha_robotwin_30/aloha_trial_adapt_place_mouse_pad_r0_final_step2000", "bytes": 12441338983, "files": 42, "restored_leaves": 51, "verified": true, "source_files": 42}}

里程碑（仅权重）: {"2000": {"path": "/data/szgx/gaohang/pi05_30/runs/stage2/pi05_aloha_robotwin_30/aloha_trial_adapt_place_mouse_pad_r0_step2000", "bytes": 12441338983, "files": 42, "restored_leaves": 51, "verified": true, "source_files": 42}}
