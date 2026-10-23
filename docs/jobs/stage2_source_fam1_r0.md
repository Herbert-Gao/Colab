更新时间（带时区）: 2026-10-21T09:49:32+0000
# stage2_source_fam1_r0


- 阶段: 2 / 类型: trial_source / 重复种子 r=0
- 源族: 1 / 目标任务: None
- 数据: pi05_30_aloha_fam1_move_pillbottle_pad_move_stapler_pad_place_a2b_left_place_fan_src50
- 初始权重: /data/szgx/xworld-gzh/cache/openpi/openpi-assets/checkpoints/pi05_base/params
- 步数上限: 2001；训练种子: 0
- 学习率: 1.25e-05；chunk_size(action_horizon): 10
- 回测任务: move_pillbottle_pad, move_stapler_pad, place_a2b_left, place_fan；回测种子: [500000, 500001, 500002, 500003, 500004]
- 状态: completed

| 步数 | loss(500步均值) | 各任务成功数/回合 | 平均成功率 | 检查点 | 早停判断 |
|---:|---:|---|---:|---|---|
| 2000 | 0.05349346573464572 | place_a2b_left:5/5 move_stapler_pad:0/5 move_pillbottle_pad:3/5 place_fan:1/5 | 0.45 | /data/szgx/gaohang/pi05_30/runs/stage2/pi05_aloha_robotwin_30/aloha_trial_fam1_r0/2000 | 未提升0/3 loss未达标 |

最终检查点: {"step": 2000, "params_only": {"path": "/data/szgx/gaohang/pi05_30/runs/stage2/pi05_aloha_robotwin_30/aloha_trial_fam1_r0_final_step2000", "bytes": 12441306730, "files": 40, "restored_leaves": 51, "verified": true, "source_files": 40}}

里程碑（仅权重）: {"2000": {"path": "/data/szgx/gaohang/pi05_30/runs/stage2/pi05_aloha_robotwin_30/aloha_trial_fam1_r0_step2000", "bytes": 12441306730, "files": 40, "restored_leaves": 51, "verified": true, "source_files": 40}}
