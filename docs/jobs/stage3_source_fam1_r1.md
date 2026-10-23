更新时间（带时区）: 2026-10-22T11:55:49+0000

# stage3_source_fam1_r1

- 阶段: 3 / 类型: source / 重复种子 r=1
- 源族: 1 / 目标任务: None
- 数据: pi05_30_aloha_fam1_move_pillbottle_pad_move_stapler_pad_place_a2b_left_place_fan_src50
- 初始权重: /data/szgx/xworld-gzh/cache/openpi/openpi-assets/checkpoints/pi05_base/params
- 步数上限: 30001；训练种子: 1
- 学习率: 1.25e-05；chunk_size(action_horizon): 10
- 回测任务: move_pillbottle_pad, move_stapler_pad, place_a2b_left, place_fan；回测种子: [500100, 500101, 500102, 500103, 500104]
- 状态: running

| 步数 | loss(500步均值) | 各任务成功数/回合 | 平均成功率 | 检查点 | 早停判断 |
|---:|---:|---|---:|---|---|
| 2000 | 0.05206353756412864 | move_pillbottle_pad:3/5 move_stapler_pad:2/5 place_a2b_left:4/5 place_fan:4/5 | 0.65 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam1/2000 | 未提升7/3 loss未达标 |
| 4000 | 0.03303324254788458 | move_pillbottle_pad:4/5 move_stapler_pad:2/5 place_a2b_left:4/5 place_fan:4/5 | 0.7 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam1/4000 | 未提升7/3 loss未达标 |
| 6000 | 0.02685892701521516 | move_pillbottle_pad:4/5 move_stapler_pad:2/5 place_a2b_left:4/5 place_fan:5/5 | 0.75 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam1/6000 | 未提升7/3 loss未达标 |
| 8000 | 0.022583777824416756 | move_pillbottle_pad:5/5 move_stapler_pad:2/5 place_a2b_left:5/5 place_fan:5/5 | 0.85 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam1/8000 | 未提升7/3 loss未达标 |
| 10000 | 0.019495024666190148 | move_pillbottle_pad:5/5 move_stapler_pad:3/5 place_a2b_left:4/5 place_fan:5/5 | 0.85 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam1/10000 | 未提升7/3 loss未达标 |
| 12000 | 0.016245361688546837 | move_pillbottle_pad:3/5 move_stapler_pad:2/5 place_a2b_left:4/5 place_fan:5/5 | 0.7 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam1/12000 | 未提升7/3 loss未达标 |
| 14000 | 0.014131724438630044 | move_pillbottle_pad:4/5 move_stapler_pad:2/5 place_a2b_left:4/5 place_fan:5/5 | 0.75 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam1/14000 | 未提升7/3 loss未达标 |
| 16000 | 0.012356308342888951 | move_pillbottle_pad:4/5 move_stapler_pad:3/5 place_a2b_left:4/5 place_fan:5/5 | 0.8 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam1/16000 | 未提升7/3 loss未达标 |
| 18000 | 0.011044540681410581 | move_pillbottle_pad:5/5 move_stapler_pad:4/5 place_a2b_left:4/5 place_fan:4/5 | 0.85 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam1/18000 | 未提升7/3 loss未达标 |
| 20000 | 0.009229171324521303 | move_pillbottle_pad:4/5 move_stapler_pad:4/5 place_a2b_left:5/5 place_fan:4/5 | 0.85 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam1/20000 | 未提升7/3 loss未达标 |
| 22000 | 0.008029490782413632 | move_pillbottle_pad:5/5 move_stapler_pad:3/5 place_a2b_left:4/5 place_fan:4/5 | 0.8 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam1/22000 | 未提升7/3 loss未达标 |
| 24000 | 0.0069738988648168744 | move_pillbottle_pad:5/5 move_stapler_pad:3/5 place_a2b_left:4/5 place_fan:5/5 | 0.85 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam1/24000 | 未提升7/3 loss未达标 |

里程碑（仅权重）: {"7500": {"path": "/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam1_step7500", "bytes": 12440706821, "files": 28, "restored_leaves": 51, "verified": true, "source_files": 28}, "15000": {"path": "/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam1_step15000", "bytes": 12440585249, "files": 24, "restored_leaves": 51, "verified": true, "source_files": 24}}
