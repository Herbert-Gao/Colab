更新时间（带时区）: 2026-10-23T10:03:29+0000

# stage3_adapt_pick_dual_bottles_r1_from_fam3

- 阶段: 3 / 类型: adapt / 重复种子 r=1
- 源族: 3 / 目标任务: pick_dual_bottles
- 数据: pi05_30_aloha_target_pick_dual_bottles_n5 / 示范编号 [9, 15, 23, 29, 34]
- 初始权重: stage3_source_fam3_r1
- 步数上限: 8001；训练种子: 1
- 学习率: 2.5e-05；chunk_size(action_horizon): 10
- 回测任务: pick_dual_bottles；回测种子: [500100, 500101, 500102, 500103, 500104]
- 状态: deferred

| 步数 | loss(500步均值) | 各任务成功数/回合 | 平均成功率 | 检查点 | 早停判断 |
|---:|---:|---|---:|---|---|
