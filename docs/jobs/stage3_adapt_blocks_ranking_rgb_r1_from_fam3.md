更新时间（带时区）: 2026-10-24T17:44:20+0000

# stage3_adapt_blocks_ranking_rgb_r1_from_fam3

- 阶段: 3 / 类型: adapt / 重复种子 r=1
- 源族: 3 / 目标任务: blocks_ranking_rgb
- 数据: pi05_30_aloha_target_blocks_ranking_rgb_n5 / 示范编号 [3, 19, 25, 45, 48]
- 初始权重: stage3_source_fam3_r1
- 步数上限: 2001；训练种子: 1
- 学习率: 2.5e-05；chunk_size(action_horizon): 10
- 回测任务: blocks_ranking_rgb；回测种子: [500100, 500101, 500102, 500103, 500104]
- 状态: completed

| 步数 | loss(500步均值) | 各任务成功数/回合 | 平均成功率 | 检查点 | 早停判断 |
|---:|---:|---|---:|---|---|
| 500 | 0.031199581938831208 | blocks_ranking_rgb:0/5 | 0.0 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_blocks_ranking_rgb_from_fam3/500 | 未提升0/3 loss未达标 |
| 1000 | 0.01643032269785181 | blocks_ranking_rgb:0/5 | 0.0 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_blocks_ranking_rgb_from_fam3/1000 | 未提升0/3 loss未达标 |
| 1500 | 0.017131813107058406 | blocks_ranking_rgb:0/5 | 0.0 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_blocks_ranking_rgb_from_fam3/1500 | 未提升0/3 loss未达标 |
| 2000 | 0.015441426320932806 | blocks_ranking_rgb:0/5 | 0.0 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_blocks_ranking_rgb_from_fam3/2000 | 未提升0/3 loss未达标 |

最终检查点: {"step": 2000, "params_only": {"path": "/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_blocks_ranking_rgb_from_fam3_final_step2000", "bytes": 12440602690, "files": 38, "restored_leaves": 51, "verified": true, "source_files": 38}}
