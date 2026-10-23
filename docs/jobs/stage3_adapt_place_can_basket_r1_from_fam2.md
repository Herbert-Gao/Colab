更新时间（带时区）: 2026-10-23T10:03:29+0000

# stage3_adapt_place_can_basket_r1_from_fam2

- 阶段: 3 / 类型: adapt / 重复种子 r=1
- 源族: 2 / 目标任务: place_can_basket
- 数据: pi05_30_aloha_target_place_can_basket_n5 / 示范编号 [17, 27, 37, 44, 48]
- 初始权重: stage3_source_fam2_r1
- 步数上限: 8001；训练种子: 1
- 学习率: 2.5e-05；chunk_size(action_horizon): 10
- 回测任务: place_can_basket；回测种子: [500100, 500101, 500102, 500103, 500104]
- 状态: deferred

| 步数 | loss(500步均值) | 各任务成功数/回合 | 平均成功率 | 检查点 | 早停判断 |
|---:|---:|---|---:|---|---|
