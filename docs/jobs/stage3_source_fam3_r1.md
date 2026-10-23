更新时间（带时区）: 2026-10-23T10:03:29+0000

# stage3_source_fam3_r1

- 阶段: 3 / 类型: source / 重复种子 r=1
- 源族: 3 / 目标任务: None
- 数据: pi05_30_aloha_fam3_blocks_ranking_size_stack_blocks_three_stack_bowls_two_stack_bowls_three_src50
- 初始权重: /data/szgx/xworld-gzh/cache/openpi/openpi-assets/checkpoints/pi05_base/params
- 步数上限: 15001；训练种子: 1
- 学习率: 2.5e-05；chunk_size(action_horizon): 10
- 回测任务: blocks_ranking_size, stack_blocks_three, stack_bowls_two, stack_bowls_three；回测种子: [500100, 500101, 500102, 500103, 500104]
- 状态: completed

| 步数 | loss(500步均值) | 各任务成功数/回合 | 平均成功率 | 检查点 | 早停判断 |
|---:|---:|---|---:|---|---|
| 2000 | 0.05733372044190765 | blocks_ranking_size:0/5 stack_blocks_three:0/5 stack_bowls_two:5/5 stack_bowls_three:1/5 | 0.3 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam3/2000 | 未提升0/3 loss未达标 |
| 4000 | 0.039175801822915676 | blocks_ranking_size:3/5 stack_blocks_three:0/5 stack_bowls_two:4/5 stack_bowls_three:1/5 | 0.4 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam3/4000 | 未提升0/3 loss未达标 |
| 6000 | 0.031823407201096415 | blocks_ranking_size:2/5 stack_blocks_three:0/5 stack_bowls_two:5/5 stack_bowls_three:3/5 | 0.5 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam3/6000 | 未提升0/3 loss未达标 |
| 8000 | 0.02570020477473736 | blocks_ranking_size:0/5 stack_blocks_three:0/5 stack_bowls_two:5/5 stack_bowls_three:2/5 | 0.35 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam3/8000 | 未提升0/3 loss未达标 |
| 10000 | 0.021895512186922133 | blocks_ranking_size:0/5 stack_blocks_three:0/5 stack_bowls_two:5/5 stack_bowls_three:5/5 | 0.5 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam3/10000 | 未提升0/3 loss未达标 |
| 12000 | 0.01971115292608738 | blocks_ranking_size:1/5 stack_blocks_three:0/5 stack_bowls_two:5/5 stack_bowls_three:3/5 | 0.45 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam3/12000 | 未提升0/3 loss未达标 |
| 14000 | 0.016669407282955944 | blocks_ranking_size:2/5 stack_blocks_three:0/5 stack_bowls_two:5/5 stack_bowls_three:3/5 | 0.5 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam3/14000 | 未提升0/3 loss未达标 |
| 15000 | 0.015705752642825244 | blocks_ranking_size:3/5 stack_blocks_three:0/5 stack_bowls_two:5/5 stack_bowls_three:3/5 | 0.55 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam3/15000 | 未提升0/3 loss未达标 |

最终检查点: {"step": 15000, "params_only": {"path": "/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam3_final_step15000", "bytes": 12440639618, "files": 36, "restored_leaves": 51, "verified": true, "source_files": 36}}

里程碑（仅权重）: {"7500": {"path": "/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam3_step7500", "bytes": 12440449399, "files": 23, "restored_leaves": 51, "verified": true, "source_files": 23}, "15000": {"path": "/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam3_step15000", "bytes": 12440639618, "files": 36, "restored_leaves": 51, "verified": true, "source_files": 36}}
