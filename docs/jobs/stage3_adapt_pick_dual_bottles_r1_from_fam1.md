更新时间（带时区）: 2026-10-24T18:58:39+0000

# stage3_adapt_pick_dual_bottles_r1_from_fam1

- 阶段: 3 / 类型: adapt / 重复种子 r=1
- 源族: 1 / 目标任务: pick_dual_bottles
- 数据: pi05_30_aloha_target_pick_dual_bottles_n5 / 示范编号 [9, 15, 23, 29, 34]
- 初始权重: stage3_source_fam1_r1
- 步数上限: 2001；训练种子: 1
- 学习率: 2.5e-05；chunk_size(action_horizon): 10
- 回测任务: pick_dual_bottles；回测种子: [500100, 500101, 500102, 500103, 500104]
- 状态: completed

| 步数 | loss(500步均值) | 各任务成功数/回合 | 平均成功率 | 检查点 | 早停判断 |
|---:|---:|---|---:|---|---|
| 500 | 0.28869475876912476 | pick_dual_bottles:2/5 | 0.4 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_pick_dual_bottles_from_fam1/500 | 未提升0/3 loss未达标 |
| 1000 | 0.03447928484529257 | pick_dual_bottles:2/5 | 0.4 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_pick_dual_bottles_from_fam1/1000 | 未提升0/3 loss未达标 |
| 1500 | 0.027143997186794878 | pick_dual_bottles:1/5 | 0.2 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_pick_dual_bottles_from_fam1/1500 | 未提升0/3 loss未达标 |
| 2000 | 0.019417443138547243 | pick_dual_bottles:1/5 | 0.2 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_pick_dual_bottles_from_fam1/2000 | 未提升0/3 loss未达标 |

最终检查点: {"step": 2000, "params_only": {"path": "/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_pick_dual_bottles_from_fam1_final_step2000", "bytes": 12440858748, "files": 43, "restored_leaves": 51, "verified": true, "source_files": 43}}
