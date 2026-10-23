更新时间（带时区）: 2026-10-23T10:03:29+0000

# stage2b_lr1x_h5

- 阶段: 4 / 类型: adapt_pilot / 重复种子 r=0
- 源族: 1 / 目标任务: place_mouse_pad
- 数据: pi05_30_aloha_target_place_mouse_pad_n5 / 示范编号 [9, 24, 29, 40, 49]
- 初始权重: stage2_source_fam1_r0
- 步数上限: 2001；训练种子: 0
- 学习率: 2.5e-05；chunk_size(action_horizon): 5
- 回测任务: place_mouse_pad；回测种子: [910000, 910001, 910002, 910003, 910004]
- 状态: deferred

| 步数 | loss(500步均值) | 各任务成功数/回合 | 平均成功率 | 检查点 | 早停判断 |
|---:|---:|---|---:|---|---|
