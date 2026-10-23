更新时间（带时区）: 2026-10-21T06:16:06+0000
# stage1_lr2x_h10


- 阶段: 1 / 类型: pilot / 重复种子 r=0
- 源族: None / 目标任务: move_pillbottle_pad
- 数据: pi05_30_pilot_move_pillbottle_pad
- 初始权重: /data/szgx/xworld-gzh/cache/openpi/openpi-assets/checkpoints/pi05_base/params
- 步数上限: 2001；训练种子: 0
- 学习率: 5e-05；chunk_size(action_horizon): 10
- 回测任务: move_pillbottle_pad；回测种子: [500000, 500001, 500002, 500003, 500004]
- 状态: completed

| 步数 | loss(500步均值) | 各任务成功数/回合 | 平均成功率 | 检查点 | 早停判断 |
|---:|---:|---|---:|---|---|
| 2000 | 0.03861285316385329 | move_pillbottle_pad:5/5 | 1.0 | /data/szgx/gaohang/pi05_30/runs/stage1/pi05_aloha_robotwin_30/aloha_pilot_stage1_lr2x_h10/2000 | 未提升0/3 loss未达标 |

最终检查点: {"step": 2000, "params_only": {"path": "/data/szgx/gaohang/pi05_30/runs/stage1/pi05_aloha_robotwin_30/aloha_pilot_stage1_lr2x_h10_final_step2000", "bytes": 12441731323, "files": 50, "restored_leaves": 51, "verified": true, "source_files": 50}}

里程碑（仅权重）: {"2000": {"path": "/data/szgx/gaohang/pi05_30/runs/stage1/pi05_aloha_robotwin_30/aloha_pilot_stage1_lr2x_h10_step2000", "bytes": 12441731323, "files": 50, "restored_leaves": 51, "verified": true, "source_files": 50}}
