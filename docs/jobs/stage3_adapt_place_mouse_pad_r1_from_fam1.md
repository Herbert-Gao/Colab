更新时间（带时区）: 2026-10-23T02:27:00+0000

# stage3_adapt_place_mouse_pad_r1_from_fam1

- 阶段: 3 / 类型: adapt / 重复种子 r=1
- 源族: 1 / 目标任务: place_mouse_pad
- 数据: pi05_30_aloha_target_place_mouse_pad_n5 / 示范编号 [9, 24, 29, 40, 49]
- 初始权重: stage3_source_fam1_r1
- 步数上限: 15001；训练种子: 1
- 学习率: 2.5e-05；chunk_size(action_horizon): 10
- 回测任务: place_mouse_pad；回测种子: [500100, 500101, 500102, 500103, 500104]
- 状态: running

| 步数 | loss(500步均值) | 各任务成功数/回合 | 平均成功率 | 检查点 | 早停判断 |
|---:|---:|---|---:|---|---|
| 2000 | 0.01139001308893785 | place_mouse_pad:0/5 | 0.0 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_place_mouse_pad_from_fam1/2000 | 未提升0/3 loss未达标 |
| 4000 | 0.006744863002095372 | place_mouse_pad:0/5 | 0.0 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_place_mouse_pad_from_fam1/4000 | 未提升0/3 loss未达标 |
