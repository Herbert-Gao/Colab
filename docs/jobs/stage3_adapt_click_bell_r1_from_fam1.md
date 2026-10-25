更新时间（带时区）: 2026-10-24T23:05:56+0000

# stage3_adapt_click_bell_r1_from_fam1

- 阶段: 3 / 类型: adapt / 重复种子 r=1
- 源族: 1 / 目标任务: click_bell
- 数据: pi05_30_aloha_target_click_bell_n5 / 示范编号 [7, 16, 23, 27, 39]
- 初始权重: stage3_source_fam1_r1
- 步数上限: 2001；训练种子: 1
- 学习率: 2.5e-05；chunk_size(action_horizon): 10
- 回测任务: click_bell；回测种子: [500100, 500101, 500102, 500103, 500104]
- 状态: completed

| 步数 | loss(500步均值) | 各任务成功数/回合 | 平均成功率 | 检查点 | 早停判断 |
|---:|---:|---|---:|---|---|
| 500 | 0.014279646734707057 | click_bell:4/5 | 0.8 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_click_bell_from_fam1/500 | 未提升0/3 loss未达标 |
| 1000 | 0.007374540417920798 | click_bell:3/5 | 0.6 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_click_bell_from_fam1/1000 | 未提升0/3 loss未达标 |
| 1500 | 0.007704788466915489 | click_bell:2/5 | 0.4 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_click_bell_from_fam1/1500 | 未提升0/3 loss未达标 |
| 2000 | 0.005985452296677977 | click_bell:2/5 | 0.4 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_click_bell_from_fam1/2000 | 未提升0/3 loss未达标 |

最终检查点: {"step": 2000, "params_only": {"path": "/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_click_bell_from_fam1_final_step2000", "bytes": 12440592993, "files": 25, "restored_leaves": 51, "verified": true, "source_files": 25}}
