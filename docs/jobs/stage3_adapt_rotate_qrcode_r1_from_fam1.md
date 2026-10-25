更新时间（带时区）: 2026-10-24T07:26:56+0000

# stage3_adapt_rotate_qrcode_r1_from_fam1

- 阶段: 3 / 类型: adapt / 重复种子 r=1
- 源族: 1 / 目标任务: rotate_qrcode
- 数据: pi05_30_aloha_target_rotate_qrcode_n5 / 示范编号 [0, 25, 28, 39, 41]
- 初始权重: stage3_source_fam1_r1
- 步数上限: 2001；训练种子: 1
- 学习率: 2.5e-05；chunk_size(action_horizon): 10
- 回测任务: rotate_qrcode；回测种子: [500100, 500101, 500102, 500103, 500104]
- 状态: completed

| 步数 | loss(500步均值) | 各任务成功数/回合 | 平均成功率 | 检查点 | 早停判断 |
|---:|---:|---|---:|---|---|
| 500 | 0.07348313186503946 | rotate_qrcode:1/5 | 0.2 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_rotate_qrcode_from_fam1/500 | 未提升0/3 loss未达标 |
| 1000 | 0.02027121982164681 | rotate_qrcode:2/5 | 0.4 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_rotate_qrcode_from_fam1/1000 | 未提升0/3 loss未达标 |
| 1500 | 0.018855629589408635 | rotate_qrcode:1/5 | 0.2 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_rotate_qrcode_from_fam1/1500 | 未提升0/3 loss未达标 |
| 2000 | 0.015308767864480615 | rotate_qrcode:3/5 | 0.6 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_rotate_qrcode_from_fam1/2000 | 未提升0/3 loss未达标 |

最终检查点: {"step": 2000, "params_only": {"path": "/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_rotate_qrcode_from_fam1_final_step2000", "bytes": 12440885050, "files": 46, "restored_leaves": 51, "verified": true, "source_files": 46}}
