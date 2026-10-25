更新时间（带时区）: 2026-10-24T22:07:37+0000

# stage3_adapt_scan_object_r1_from_fam3

- 阶段: 3 / 类型: adapt / 重复种子 r=1
- 源族: 3 / 目标任务: scan_object
- 数据: pi05_30_aloha_target_scan_object_n5 / 示范编号 [2, 3, 32, 34, 39]
- 初始权重: stage3_source_fam3_r1
- 步数上限: 2001；训练种子: 1
- 学习率: 2.5e-05；chunk_size(action_horizon): 10
- 回测任务: scan_object；回测种子: [500100, 500101, 500102, 500103, 500104]
- 状态: completed

| 步数 | loss(500步均值) | 各任务成功数/回合 | 平均成功率 | 检查点 | 早停判断 |
|---:|---:|---|---:|---|---|
| 500 | 0.43907439954206345 | scan_object:1/5 | 0.2 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_scan_object_from_fam3/500 | 未提升0/3 loss未达标 |
| 1000 | 0.05240794853493571 | scan_object:1/5 | 0.2 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_scan_object_from_fam3/1000 | 未提升0/3 loss未达标 |
| 1500 | 0.04294134075194597 | scan_object:0/5 | 0.0 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_scan_object_from_fam3/1500 | 未提升0/3 loss未达标 |
| 2000 | 0.032976289808750156 | scan_object:0/5 | 0.0 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_scan_object_from_fam3/2000 | 未提升0/3 loss未达标 |

最终检查点: {"step": 2000, "params_only": {"path": "/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_scan_object_from_fam3_final_step2000", "bytes": 12440606661, "files": 35, "restored_leaves": 51, "verified": true, "source_files": 35}}
