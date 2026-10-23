更新时间（带时区）: 2026-10-22T23:07:28+0000

# 模型清单（服务器 A，aloha-agilex）

本轮范围（运营 2026-10-22 决定）：只训练源模型，用 openpi 官方超参（peak_lr 2.5e-05、action_horizon 10、batch 32）训 15000 步；微调矩阵（10 目标 × 3 起点 = 30 个）**延后**，作业状态为 `deferred`。
本轮不含最终评估（100 回合）与 0 步裸测。

| 源模型ID | 族群 | 实际步数 | 是否早停 | 状态 | 保留的检查点路径 | 最近一次回测成功率 |
|---|---|---:|---|---|---|---|
| stage3_source_fam1_r1 | 1 | 15000 | 否 | stopped | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam1_step15000（最终权重，step 15000）<br>/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam1_step7500（里程碑 step 7500）<br>/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam1_step15000（里程碑 step 15000） | 0.85 |
| stage3_source_fam2_r1 | 2 | 15000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam2_final_step15000（最终权重，step 15000）<br>/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam2_step15000（里程碑 step 15000） | 0.7 |
| stage3_source_fam3_r1 | 3 | 15000 | 否 | completed | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam3_final_step15000（最终权重，step 15000）<br>/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam3_step7500（里程碑 step 7500）<br>/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam3_step15000（里程碑 step 15000） | 0.55 |

## 微调模型（目标适应，本轮延后：30 个作业状态为 deferred）

| 模型ID | 起点模型 | 目标任务 | 实际步数 | 是否早停 | 状态 | 保留的检查点路径 | 最近一次回测成功率 |
|---|---|---|---:|---|---|---|---|
| stage3_adapt_place_mouse_pad_r1_from_fam1 | stage3_source_fam1_r1 | place_mouse_pad | 0 | 否 | deferred | （无） | - |
| stage3_adapt_place_mouse_pad_r1_from_fam2 | stage3_source_fam2_r1 | place_mouse_pad | 0 | 否 | deferred | （无） | - |
| stage3_adapt_place_mouse_pad_r1_from_fam3 | stage3_source_fam3_r1 | place_mouse_pad | 0 | 否 | deferred | （无） | - |
| stage3_adapt_rotate_qrcode_r1_from_fam1 | stage3_source_fam1_r1 | rotate_qrcode | 0 | 否 | deferred | （无） | - |
| stage3_adapt_rotate_qrcode_r1_from_fam2 | stage3_source_fam2_r1 | rotate_qrcode | 0 | 否 | deferred | （无） | - |
| stage3_adapt_rotate_qrcode_r1_from_fam3 | stage3_source_fam3_r1 | rotate_qrcode | 0 | 否 | deferred | （无） | - |
| stage3_adapt_place_can_basket_r1_from_fam1 | stage3_source_fam1_r1 | place_can_basket | 0 | 否 | deferred | （无） | - |
| stage3_adapt_place_can_basket_r1_from_fam2 | stage3_source_fam2_r1 | place_can_basket | 0 | 否 | deferred | （无） | - |
| stage3_adapt_place_can_basket_r1_from_fam3 | stage3_source_fam3_r1 | place_can_basket | 0 | 否 | deferred | （无） | - |
| stage3_adapt_hanging_mug_r1_from_fam1 | stage3_source_fam1_r1 | hanging_mug | 0 | 否 | deferred | （无） | - |
| stage3_adapt_hanging_mug_r1_from_fam2 | stage3_source_fam2_r1 | hanging_mug | 0 | 否 | deferred | （无） | - |
| stage3_adapt_hanging_mug_r1_from_fam3 | stage3_source_fam3_r1 | hanging_mug | 0 | 否 | deferred | （无） | - |
| stage3_adapt_stack_blocks_two_r1_from_fam1 | stage3_source_fam1_r1 | stack_blocks_two | 0 | 否 | deferred | （无） | - |
| stage3_adapt_stack_blocks_two_r1_from_fam2 | stage3_source_fam2_r1 | stack_blocks_two | 0 | 否 | deferred | （无） | - |
| stage3_adapt_stack_blocks_two_r1_from_fam3 | stage3_source_fam3_r1 | stack_blocks_two | 0 | 否 | deferred | （无） | - |
| stage3_adapt_blocks_ranking_rgb_r1_from_fam1 | stage3_source_fam1_r1 | blocks_ranking_rgb | 0 | 否 | deferred | （无） | - |
| stage3_adapt_blocks_ranking_rgb_r1_from_fam2 | stage3_source_fam2_r1 | blocks_ranking_rgb | 0 | 否 | deferred | （无） | - |
| stage3_adapt_blocks_ranking_rgb_r1_from_fam3 | stage3_source_fam3_r1 | blocks_ranking_rgb | 0 | 否 | deferred | （无） | - |
| stage3_adapt_pick_dual_bottles_r1_from_fam1 | stage3_source_fam1_r1 | pick_dual_bottles | 0 | 否 | deferred | （无） | - |
| stage3_adapt_pick_dual_bottles_r1_from_fam2 | stage3_source_fam2_r1 | pick_dual_bottles | 0 | 否 | deferred | （无） | - |
| stage3_adapt_pick_dual_bottles_r1_from_fam3 | stage3_source_fam3_r1 | pick_dual_bottles | 0 | 否 | deferred | （无） | - |
| stage3_adapt_scan_object_r1_from_fam1 | stage3_source_fam1_r1 | scan_object | 0 | 否 | deferred | （无） | - |
| stage3_adapt_scan_object_r1_from_fam2 | stage3_source_fam2_r1 | scan_object | 0 | 否 | deferred | （无） | - |
| stage3_adapt_scan_object_r1_from_fam3 | stage3_source_fam3_r1 | scan_object | 0 | 否 | deferred | （无） | - |
| stage3_adapt_click_bell_r1_from_fam1 | stage3_source_fam1_r1 | click_bell | 0 | 否 | deferred | （无） | - |
| stage3_adapt_click_bell_r1_from_fam2 | stage3_source_fam2_r1 | click_bell | 0 | 否 | deferred | （无） | - |
| stage3_adapt_click_bell_r1_from_fam3 | stage3_source_fam3_r1 | click_bell | 0 | 否 | deferred | （无） | - |
| stage3_adapt_beat_block_hammer_r1_from_fam1 | stage3_source_fam1_r1 | beat_block_hammer | 0 | 否 | deferred | （无） | - |
| stage3_adapt_beat_block_hammer_r1_from_fam2 | stage3_source_fam2_r1 | beat_block_hammer | 0 | 否 | deferred | （无） | - |
| stage3_adapt_beat_block_hammer_r1_from_fam3 | stage3_source_fam3_r1 | beat_block_hammer | 0 | 否 | deferred | （无） | - |

- 已交付微调模型: 0 / 30


- 源模型: 3 个（有交付权重 3，训练完成 2）
- 微调模型: 30 个（完成 0，延后 30）
- 检查点路径校验: 全部存在

