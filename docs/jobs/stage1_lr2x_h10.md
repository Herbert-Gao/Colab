更新时间（带时区）: 2026-10-23T10:03:29+0000

# stage1_lr2x_h10

- 阶段: 1 / 类型: pilot / 重复种子 r=0
- 源族: None / 目标任务: move_pillbottle_pad
- 数据: pi05_30_pilot_move_pillbottle_pad
- 初始权重: /data/szgx/xworld-gzh/cache/openpi/openpi-assets/checkpoints/pi05_base/params
- 步数上限: 2001；训练种子: 0
- 学习率: 5e-05；chunk_size(action_horizon): 10
- 回测任务: move_pillbottle_pad；回测种子: [900000, 900001, 900002, 900003, 900004]
- 状态: deferred

| 步数 | loss(500步均值) | 各任务成功数/回合 | 平均成功率 | 检查点 | 早停判断 |
|---:|---:|---|---:|---|---|
