更新时间（带时区）: 2026-10-25T01:26:32+0000

# 模型清单（服务器 A，aloha-agilex）

本轮范围：30 个微调模型（10 目标 × 3 起点，每作业 ≤2000 步、每 500 步存一次 .ckpt 并回测 5 回合）+ 4 个源模型（openpi 官方超参 peak_lr 2.5e-05、action_horizon 10、batch 32，15000 步）。
按运营指示本轮不做 0 步裸测；源模型在 10 个目标任务上的 100 回合泛化测试为运营追加的评测，结果见 `docs/eval_report.md`。

| 源模型ID | 族群 | 实际步数 | 是否早停 | 状态 | 保留的检查点路径 | 最近一次回测成功率 |
|---|---|---:|---|---|---|---|
| stage3_source_fam1_r1 | 1 | 15000 | 否 | stopped | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam1_step15000（最终权重，step 15000）<br>/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam1_step7500（里程碑 step 7500）<br>/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam1_step15000（里程碑 step 15000） | 0.8 |
| stage3_source_fam2_r1 | 2 | 15000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam2_final_step15000（最终权重，step 15000）<br>/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam2_step15000（里程碑 step 15000） | 0.8 |
| stage3_source_fam3_r1 | 3 | 15000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam3_final_step15000（最终权重，step 15000）<br>/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam3_step7500（里程碑 step 7500）<br>/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam3_step15000（里程碑 step 15000） | 0.55 |
| stage3_source_fam3_r1_long | 3 | 2000 | 否 | stopped | （无） | - |

## 微调模型（目标适应，本轮延后：0 个作业状态为 deferred）

| 模型ID | 起点模型 | 目标任务 | 实际步数 | 是否早停 | 状态 | 保留的检查点路径 | 最近一次回测成功率 |
|---|---|---|---:|---|---|---|---|
| stage3_adapt_place_mouse_pad_r1_from_fam1 | stage3_source_fam1_r1 | place_mouse_pad | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_place_mouse_pad_from_fam1_final_step2000（最终权重，step 2000） | 0.2 |
| stage3_adapt_place_mouse_pad_r1_from_fam2 | stage3_source_fam2_r1 | place_mouse_pad | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_place_mouse_pad_from_fam2_final_step2000（最终权重，step 2000） | 0.0 |
| stage3_adapt_place_mouse_pad_r1_from_fam3 | stage3_source_fam3_r1 | place_mouse_pad | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_place_mouse_pad_from_fam3_final_step2000（最终权重，step 2000） | 0.0 |
| stage3_adapt_rotate_qrcode_r1_from_fam1 | stage3_source_fam1_r1 | rotate_qrcode | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_rotate_qrcode_from_fam1_final_step2000（最终权重，step 2000） | 0.6 |
| stage3_adapt_rotate_qrcode_r1_from_fam2 | stage3_source_fam2_r1 | rotate_qrcode | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_rotate_qrcode_from_fam2_final_step2000（最终权重，step 2000） | 0.2 |
| stage3_adapt_rotate_qrcode_r1_from_fam3 | stage3_source_fam3_r1 | rotate_qrcode | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_rotate_qrcode_from_fam3_final_step2000（最终权重，step 2000） | 0.4 |
| stage3_adapt_place_can_basket_r1_from_fam1 | stage3_source_fam1_r1 | place_can_basket | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_place_can_basket_from_fam1_final_step2000（最终权重，step 2000） | 0.4 |
| stage3_adapt_place_can_basket_r1_from_fam2 | stage3_source_fam2_r1 | place_can_basket | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_place_can_basket_from_fam2_final_step2000（最终权重，step 2000） | 0.2 |
| stage3_adapt_place_can_basket_r1_from_fam3 | stage3_source_fam3_r1 | place_can_basket | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_place_can_basket_from_fam3_final_step2000（最终权重，step 2000） | 0.8 |
| stage3_adapt_hanging_mug_r1_from_fam1 | stage3_source_fam1_r1 | hanging_mug | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_hanging_mug_from_fam1_final_step2000（最终权重，step 2000） | 0.0 |
| stage3_adapt_hanging_mug_r1_from_fam2 | stage3_source_fam2_r1 | hanging_mug | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_hanging_mug_from_fam2_final_step2000（最终权重，step 2000） | 0.0 |
| stage3_adapt_hanging_mug_r1_from_fam3 | stage3_source_fam3_r1 | hanging_mug | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_hanging_mug_from_fam3_final_step2000（最终权重，step 2000） | 0.2 |
| stage3_adapt_stack_blocks_two_r1_from_fam1 | stage3_source_fam1_r1 | stack_blocks_two | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_stack_blocks_two_from_fam1_final_step2000（最终权重，step 2000） | 0.2 |
| stage3_adapt_stack_blocks_two_r1_from_fam2 | stage3_source_fam2_r1 | stack_blocks_two | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_stack_blocks_two_from_fam2_final_step2000（最终权重，step 2000） | 0.0 |
| stage3_adapt_stack_blocks_two_r1_from_fam3 | stage3_source_fam3_r1 | stack_blocks_two | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_stack_blocks_two_from_fam3_final_step2000（最终权重，step 2000） | 0.0 |
| stage3_adapt_blocks_ranking_rgb_r1_from_fam1 | stage3_source_fam1_r1 | blocks_ranking_rgb | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_blocks_ranking_rgb_from_fam1_final_step2000（最终权重，step 2000） | 0.0 |
| stage3_adapt_blocks_ranking_rgb_r1_from_fam2 | stage3_source_fam2_r1 | blocks_ranking_rgb | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_blocks_ranking_rgb_from_fam2_final_step2000（最终权重，step 2000） | 0.0 |
| stage3_adapt_blocks_ranking_rgb_r1_from_fam3 | stage3_source_fam3_r1 | blocks_ranking_rgb | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_blocks_ranking_rgb_from_fam3_final_step2000（最终权重，step 2000） | 0.0 |
| stage3_adapt_pick_dual_bottles_r1_from_fam1 | stage3_source_fam1_r1 | pick_dual_bottles | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_pick_dual_bottles_from_fam1_final_step2000（最终权重，step 2000） | 0.2 |
| stage3_adapt_pick_dual_bottles_r1_from_fam2 | stage3_source_fam2_r1 | pick_dual_bottles | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_pick_dual_bottles_from_fam2_final_step2000（最终权重，step 2000） | 0.0 |
| stage3_adapt_pick_dual_bottles_r1_from_fam3 | stage3_source_fam3_r1 | pick_dual_bottles | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_pick_dual_bottles_from_fam3_final_step2000（最终权重，step 2000） | 0.0 |
| stage3_adapt_scan_object_r1_from_fam1 | stage3_source_fam1_r1 | scan_object | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_scan_object_from_fam1_final_step2000（最终权重，step 2000） | 0.0 |
| stage3_adapt_scan_object_r1_from_fam2 | stage3_source_fam2_r1 | scan_object | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_scan_object_from_fam2_final_step2000（最终权重，step 2000） | 0.0 |
| stage3_adapt_scan_object_r1_from_fam3 | stage3_source_fam3_r1 | scan_object | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_scan_object_from_fam3_final_step2000（最终权重，step 2000） | 0.0 |
| stage3_adapt_click_bell_r1_from_fam1 | stage3_source_fam1_r1 | click_bell | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_click_bell_from_fam1_final_step2000（最终权重，step 2000） | 0.4 |
| stage3_adapt_click_bell_r1_from_fam2 | stage3_source_fam2_r1 | click_bell | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_click_bell_from_fam2_final_step2000（最终权重，step 2000） | 1.0 |
| stage3_adapt_click_bell_r1_from_fam3 | stage3_source_fam3_r1 | click_bell | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_click_bell_from_fam3_final_step2000（最终权重，step 2000） | 0.8 |
| stage3_adapt_beat_block_hammer_r1_from_fam1 | stage3_source_fam1_r1 | beat_block_hammer | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_beat_block_hammer_from_fam1_final_step2000（最终权重，step 2000） | 0.4 |
| stage3_adapt_beat_block_hammer_r1_from_fam2 | stage3_source_fam2_r1 | beat_block_hammer | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_beat_block_hammer_from_fam2_final_step2000（最终权重，step 2000） | 0.4 |
| stage3_adapt_beat_block_hammer_r1_from_fam3 | stage3_source_fam3_r1 | beat_block_hammer | 2000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_adapt_beat_block_hammer_from_fam3_final_step2000（最终权重，step 2000） | 0.6 |

- 已交付微调模型: 30 / 30


- 源模型: 4 个（有交付权重 4，训练完成 3）
- 微调模型: 30 个（完成 30，延后 0）
- 检查点路径校验: 全部存在

