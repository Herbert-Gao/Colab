更新时间（带时区）: 2026-10-23T02:29:35+0000

# pi0.5 / RoboTwin ALOHA 训练总览（服务器 A）

- 机体: aloha-agilex（ALOHA 双臂；训练、仿真评估、归一化一致）
- 训练卡 0,1,2,3,4,5,6,7（8 卡 FSDP），仿真卡 1，策略服务卡 ['0', '2', '4', '6']
- 作业总数: 54
- 状态分布: completed=2, deferred=48, pending=1, running=2, stopped=1

- 本轮范围: 阶段0/1/2/2b/3，源模型 3 个（族群 1、2、3），目标适应 30 个（10 目标 × 3 起点），本轮不执行最终评估与 0 步裸测
- 冻结参数: 源训练 学习率 1.25e-05，chunk_size(action_horizon) 10；目标适应 未冻结
- 种子: 训练 1（试运行 0）／阶段1 回测 900000+i／阶段2b 回测 910000+i／周期回测 500100+i／最终评估（本轮不用）100000+1000*t+i
- 微调模型清单: `docs/models_manifest.md`
| 作业ID | 状态 | 当前步数 | 最新成功率 | 最新loss | 开始 | 结束 |
|---|---|---:|---:|---:|---|---|

## 检查点保留与清理（4.1）

- 滚动恢复点: 每 1000 步存一个，只保留最近 2 个已回测恢复点 + 最新恢复点；回测结果校验落盘后立即删除更旧的恢复点
- 周期回测: 每 2000 步 5 回合（§5/§6 的 2000 步区间口径），回测与训练并行（策略服务与仿真占用训练器未预留的显存）
- 里程碑: 7500 / 15000 / 30000 步与早停最终步，存 params-only 副本并长期保留
- 源模型最终权重: 每族一份 params-only 副本，本服务器所有适应作业结束后仍保留
- 失败/暂停作业: 保留最后一个有效恢复点，禁止清理
- 每次保存前检查磁盘余量；不足「一个检查点 × 3」时暂停作业并飞书反馈，不删保留类检查点
- 每条删除记入 `docs/cleanup_log.md`（路径、步数、原因、释放大小）

| stage1_lr0.5x_h10 | deferred | 0 | - | - | - | - |
| stage1_lr0.5x_h15 | deferred | 0 | - | - | - | - |
| stage1_lr0.5x_h5 | deferred | 0 | - | - | - | - |
| stage1_lr1x_h10 | deferred | 0 | - | - | - | - |
| stage1_lr1x_h15 | deferred | 0 | - | - | - | - |
| stage1_lr1x_h5 | deferred | 0 | - | - | - | - |
| stage1_lr2x_h10 | deferred | 0 | - | - | - | - |
| stage1_lr2x_h15 | deferred | 0 | - | - | - | - |
| stage1_lr2x_h5 | deferred | 0 | - | - | - | - |
| stage2_source_fam1_r0 | deferred | 0 | - | - | - | - |
| stage2_target_place_mouse_pad_r0 | deferred | 0 | - | - | - | - |
| stage2b_lr0.5x_h10 | deferred | 0 | - | - | - | - |
| stage2b_lr0.5x_h15 | deferred | 0 | - | - | - | - |
| stage2b_lr0.5x_h5 | deferred | 0 | - | - | - | - |
| stage2b_lr1x_h10 | deferred | 0 | - | - | - | - |
| stage2b_lr1x_h15 | deferred | 0 | - | - | - | - |
| stage2b_lr1x_h5 | deferred | 0 | - | - | - | - |
| stage2b_lr2x_h10 | deferred | 0 | - | - | - | - |
| stage2b_lr2x_h15 | deferred | 0 | - | - | - | - |
| stage2b_lr2x_h5 | deferred | 0 | - | - | - | - |
| stage3_adapt_beat_block_hammer_r1_from_fam1 | deferred | 0 | - | - | - | - |
| stage3_adapt_beat_block_hammer_r1_from_fam2 | deferred | 0 | - | - | - | - |
| stage3_adapt_beat_block_hammer_r1_from_fam3 | deferred | 0 | - | - | - | - |
| stage3_adapt_blocks_ranking_rgb_r1_from_fam1 | deferred | 0 | - | - | - | - |
| stage3_adapt_blocks_ranking_rgb_r1_from_fam2 | deferred | 0 | - | - | - | - |
| stage3_adapt_blocks_ranking_rgb_r1_from_fam3 | deferred | 0 | - | - | - | - |
| stage3_adapt_click_bell_r1_from_fam1 | deferred | 0 | - | - | - | - |
| stage3_adapt_click_bell_r1_from_fam2 | deferred | 0 | - | - | - | - |
| stage3_adapt_click_bell_r1_from_fam3 | deferred | 0 | - | - | - | - |
| stage3_adapt_hanging_mug_r1_from_fam1 | deferred | 0 | - | - | - | - |
| stage3_adapt_hanging_mug_r1_from_fam2 | deferred | 0 | - | - | - | - |
| stage3_adapt_hanging_mug_r1_from_fam3 | deferred | 0 | - | - | - | - |
| stage3_adapt_pick_dual_bottles_r1_from_fam1 | deferred | 0 | - | - | - | - |
| stage3_adapt_pick_dual_bottles_r1_from_fam2 | deferred | 0 | - | - | - | - |
| stage3_adapt_pick_dual_bottles_r1_from_fam3 | deferred | 0 | - | - | - | - |
| stage3_adapt_place_can_basket_r1_from_fam1 | deferred | 0 | - | - | - | - |
| stage3_adapt_place_can_basket_r1_from_fam2 | deferred | 0 | - | - | - | - |
| stage3_adapt_place_can_basket_r1_from_fam3 | deferred | 0 | - | - | - | - |
| stage3_adapt_place_mouse_pad_r1_from_fam1 | running | 4000 | 0.0 | 0.006744863002095372 | 2026-10-22T23:44:07+00:00 | - |
| stage3_adapt_place_mouse_pad_r1_from_fam2 | running | 6000 | 0.0 | 0.005063593065366149 | 2026-10-22T23:44:37+00:00 | - |
| stage3_adapt_place_mouse_pad_r1_from_fam3 | deferred | 0 | - | - | - | - |
| stage3_adapt_rotate_qrcode_r1_from_fam1 | deferred | 0 | - | - | - | - |
| stage3_adapt_rotate_qrcode_r1_from_fam2 | deferred | 0 | - | - | - | - |
| stage3_adapt_rotate_qrcode_r1_from_fam3 | deferred | 0 | - | - | - | - |
| stage3_adapt_scan_object_r1_from_fam1 | deferred | 0 | - | - | - | - |
| stage3_adapt_scan_object_r1_from_fam2 | deferred | 0 | - | - | - | - |
| stage3_adapt_scan_object_r1_from_fam3 | deferred | 0 | - | - | - | - |
| stage3_adapt_stack_blocks_two_r1_from_fam1 | deferred | 0 | - | - | - | - |
| stage3_adapt_stack_blocks_two_r1_from_fam2 | deferred | 0 | - | - | - | - |
| stage3_adapt_stack_blocks_two_r1_from_fam3 | deferred | 0 | - | - | - | - |
| stage3_source_fam1_r1 | stopped | 15000 | 0.8 | 0.013236459823325277 | 2026-10-22T06:36:43+00:00 | - |
| stage3_source_fam2_r1 | completed | 15000 | 0.8 | 0.017694183138199152 | 2026-10-22T12:04:25+00:00 | 2026-10-22T23:07:06+00:00 |
| stage3_source_fam3_r1 | completed | 15000 | 0.55 | 0.015705752642825244 | 2026-10-22T12:04:56+00:00 | 2026-10-22T20:24:22+00:00 |
| stage3_source_fam3_r1_long | pending | 0 | - | - | - | - |

## 总汇总

- 源模型: 4 个（完成 2）
- 微调模型（目标适应）: 30 个（完成 0，延后 28）
- 延后作业（预实验与微调）: 48
- 终态作业合计: 2 / 54
- 微调模型清单: `docs/models_manifest.md`（模型ID／起点模型／目标任务／实际步数／早停／检查点路径／最近回测成功率）
- 磁盘：卷剩余 2590 GiB

