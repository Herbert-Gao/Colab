更新时间（带时区）: 2026-10-23T10:03:29+0000

# stage2_source_fam1_r0

- 阶段: 2 / 类型: trial_source / 重复种子 r=0
- 源族: 1 / 目标任务: None
- 数据: pi05_30_aloha_fam1_move_pillbottle_pad_move_stapler_pad_place_a2b_left_place_fan_src50
- 初始权重: /data/szgx/xworld-gzh/cache/openpi/openpi-assets/checkpoints/pi05_base/params
- 步数上限: 2001；训练种子: 0
- 学习率: 2.5e-05；chunk_size(action_horizon): 10
- 回测任务: move_pillbottle_pad, move_stapler_pad, place_a2b_left, place_fan；回测种子: [500100, 500101, 500102, 500103, 500104]
- 状态: deferred

| 步数 | loss(500步均值) | 各任务成功数/回合 | 平均成功率 | 检查点 | 早停判断 |
|---:|---:|---|---:|---|---|
