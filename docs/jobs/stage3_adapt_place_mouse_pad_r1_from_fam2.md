更新时间（带时区）: 2026-10-23T10:03:29+0000

# stage3_adapt_place_mouse_pad_r1_from_fam2

- 阶段: 3 / 类型: adapt / 重复种子 r=1
- 源族: 2 / 目标任务: place_mouse_pad
- 数据: pi05_30_aloha_target_place_mouse_pad_n5 / 示范编号 [9, 24, 29, 40, 49]
- 初始权重: stage3_source_fam2_r1
- 步数上限: 8001；训练种子: 1
- 学习率: 2.5e-05；chunk_size(action_horizon): 10
- 回测任务: place_mouse_pad；回测种子: [500100, 500101, 500102, 500103, 500104]
- 状态: stopped

| 步数 | loss(500步均值) | 各任务成功数/回合 | 平均成功率 | 检查点 | 早停判断 |
|---:|---:|---|---:|---|---|
| 2000 | 0.010253044991288334 | place_mouse_pad:0/5 | 0.0 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_place_mouse_pad_from_fam2/2000 | 未提升0/3 loss未达标 |
| 4000 | 0.006396480431314557 | place_mouse_pad:0/5 | 0.0 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_place_mouse_pad_from_fam2/4000 | 未提升0/3 loss未达标 |
| 6000 | 0.005063593065366149 | place_mouse_pad:0/5 | 0.0 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_place_mouse_pad_from_fam2/6000 | 未提升0/3 loss未达标 |

最终检查点: {"step": 7500, "params_only": {"path": "/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_place_mouse_pad_from_fam2_final_step7500", "bytes": 12440597119, "files": 36, "restored_leaves": 51, "verified": true, "source_files": 36}}

里程碑（仅权重）: {"7500": {"path": "/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_place_mouse_pad_from_fam2_step7500", "bytes": 12440597119, "files": 36, "restored_leaves": 51, "verified": true, "source_files": 36}}
