更新时间（带时区）: 2026-10-23T09:58:32+0000

# stage3_source_fam3_r1_long

- 阶段: 3 / 类型: source / 重复种子 r=1
- 源族: 3 / 目标任务: None
- 数据: pi05_30_aloha_fam3_blocks_ranking_size_stack_blocks_three_stack_bowls_two_stack_bowls_three_src50
- 初始权重: /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam3_final_step15000/params
- 步数上限: 15001；训练种子: 1
- 学习率: 2.5e-05；chunk_size(action_horizon): 10
- 回测任务: blocks_ranking_size, stack_blocks_three, stack_bowls_two, stack_bowls_three；回测种子: [500100, 500101, 500102, 500103, 500104]
- 状态: running

| 步数 | loss(500步均值) | 各任务成功数/回合 | 平均成功率 | 检查点 | 早停判断 |
|---:|---:|---|---:|---|---|
