更新时间（带时区）: 2026-10-24T10:02:28+0000

# stage3_adapt_place_can_basket_r1_from_fam2

- 阶段: 3 / 类型: adapt / 重复种子 r=1
- 源族: 2 / 目标任务: place_can_basket
- 数据: pi05_30_aloha_target_place_can_basket_n5 / 示范编号 [17, 27, 37, 44, 48]
- 初始权重: stage3_source_fam2_r1
- 步数上限: 2001；训练种子: 1
- 学习率: 2.5e-05；chunk_size(action_horizon): 10
- 回测任务: place_can_basket；回测种子: [500100, 500101, 500102, 500103, 500104]
- 状态: completed

| 步数 | loss(500步均值) | 各任务成功数/回合 | 平均成功率 | 检查点 | 早停判断 |
|---:|---:|---|---:|---|---|
| 500 | 0.03993089176248759 | place_can_basket:4/5 | 0.8 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_place_can_basket_from_fam2/500 | 未提升0/3 loss未达标 |
| 1000 | 0.017172094239853324 | place_can_basket:4/5 | 0.8 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_place_can_basket_from_fam2/1000 | 未提升0/3 loss未达标 |
| 1500 | 0.017748471627011896 | place_can_basket:2/5 | 0.4 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_place_can_basket_from_fam2/1500 | 未提升0/3 loss未达标 |
| 2000 | 0.015655783304944635 | place_can_basket:1/5 | 0.2 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_place_can_basket_from_fam2/2000 | 未提升0/3 loss未达标 |

最终检查点: {"step": 2000, "params_only": {"path": "/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_place_can_basket_from_fam2_final_step2000", "bytes": 12440732418, "files": 44, "restored_leaves": 51, "verified": true, "source_files": 44}}
