更新时间（带时区）: 2026-10-25T01:26:32+0000

# pi0.5 / RoboTwin ALOHA 训练总览（服务器 A）

- 机体: aloha-agilex（ALOHA 双臂；训练、仿真评估、归一化一致）
- 训练卡 0,1,2,3,4,5,6,7（8 卡 FSDP），仿真卡 1，策略服务卡 ['0', '2', '4', '6']
- 作业总数: 54
- 状态分布: completed=32, deferred=20, stopped=2

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
| stage3_adapt_beat_block_hammer_r1_from_fam1 | completed | 2000 | 0.4 | 0.009235127956140786 | 2026-10-24T23:08:03+00:00 | 2026-10-25T00:05:47+00:00 |
| stage3_adapt_beat_block_hammer_r1_from_fam2 | completed | 2000 | 0.4 | 0.008414353688247502 | 2026-10-25T00:07:12+00:00 | 2026-10-25T01:11:32+00:00 |
| stage3_adapt_beat_block_hammer_r1_from_fam3 | completed | 2000 | 0.6 | 0.00842808397905901 | 2026-10-25T00:07:43+00:00 | 2026-10-25T01:23:08+00:00 |
| stage3_adapt_blocks_ranking_rgb_r1_from_fam1 | completed | 2000 | 0.0 | 0.022580788500607015 | 2026-10-24T14:30:32+00:00 | 2026-10-24T16:06:33+00:00 |
| stage3_adapt_blocks_ranking_rgb_r1_from_fam2 | completed | 2000 | 0.0 | 0.018091016869992017 | 2026-10-24T16:07:05+00:00 | 2026-10-24T17:41:34+00:00 |
| stage3_adapt_blocks_ranking_rgb_r1_from_fam3 | completed | 2000 | 0.0 | 0.015441426320932806 | 2026-10-24T16:07:35+00:00 | 2026-10-24T17:44:13+00:00 |
| stage3_adapt_click_bell_r1_from_fam1 | completed | 2000 | 0.4 | 0.005985452296677977 | 2026-10-24T22:08:01+00:00 | 2026-10-24T23:05:50+00:00 |
| stage3_adapt_click_bell_r1_from_fam2 | completed | 2000 | 1.0 | 0.005330442176666111 | 2026-10-24T22:08:32+00:00 | 2026-10-24T23:07:01+00:00 |
| stage3_adapt_click_bell_r1_from_fam3 | completed | 2000 | 0.8 | 0.005123536184662953 | 2026-10-24T23:07:32+00:00 | 2026-10-25T00:06:41+00:00 |
| stage3_adapt_hanging_mug_r1_from_fam1 | completed | 2000 | 0.0 | 0.03234991986118257 | 2026-10-24T10:03:23+00:00 | 2026-10-24T11:34:07+00:00 |
| stage3_adapt_hanging_mug_r1_from_fam2 | completed | 2000 | 0.0 | 0.02520696119219065 | 2026-10-24T11:34:38+00:00 | 2026-10-24T13:05:45+00:00 |
| stage3_adapt_hanging_mug_r1_from_fam3 | completed | 2000 | 0.2 | 0.027325438669882716 | 2026-10-24T11:35:09+00:00 | 2026-10-24T13:05:02+00:00 |
| stage3_adapt_pick_dual_bottles_r1_from_fam1 | completed | 2000 | 0.2 | 0.019417443138547243 | 2026-10-24T17:44:44+00:00 | 2026-10-24T18:58:32+00:00 |
| stage3_adapt_pick_dual_bottles_r1_from_fam2 | completed | 2000 | 0.0 | 0.01586780836060643 | 2026-10-24T17:45:15+00:00 | 2026-10-24T18:59:29+00:00 |
| stage3_adapt_pick_dual_bottles_r1_from_fam3 | completed | 2000 | 0.0 | 0.018683595077134667 | 2026-10-24T18:59:59+00:00 | 2026-10-24T20:17:23+00:00 |
| stage3_adapt_place_can_basket_r1_from_fam1 | completed | 2000 | 0.4 | 0.022878102600574494 | 2026-10-24T08:37:09+00:00 | 2026-10-24T09:53:46+00:00 |
| stage3_adapt_place_can_basket_r1_from_fam2 | completed | 2000 | 0.2 | 0.015655783304944635 | 2026-10-24T08:37:40+00:00 | 2026-10-24T10:02:22+00:00 |
| stage3_adapt_place_can_basket_r1_from_fam3 | completed | 2000 | 0.8 | 0.018755971987731754 | 2026-10-24T10:02:52+00:00 | 2026-10-24T11:33:18+00:00 |
| stage3_adapt_place_mouse_pad_r1_from_fam1 | completed | 2000 | 0.2 | 0.011346869803965091 | 2026-10-24T05:11:52+00:00 | 2026-10-24T06:16:21+00:00 |
| stage3_adapt_place_mouse_pad_r1_from_fam2 | completed | 2000 | 0.0 | 0.010282026106026024 | 2026-10-24T05:12:22+00:00 | 2026-10-24T06:23:19+00:00 |
| stage3_adapt_place_mouse_pad_r1_from_fam3 | completed | 2000 | 0.0 | 0.010346955521497876 | 2026-10-24T06:23:51+00:00 | 2026-10-24T07:29:15+00:00 |
| stage3_adapt_rotate_qrcode_r1_from_fam1 | completed | 2000 | 0.6 | 0.015308767864480615 | 2026-10-24T06:24:21+00:00 | 2026-10-24T07:26:49+00:00 |
| stage3_adapt_rotate_qrcode_r1_from_fam2 | completed | 2000 | 0.2 | 0.012871586731635035 | 2026-10-24T07:29:46+00:00 | 2026-10-24T08:36:38+00:00 |
| stage3_adapt_rotate_qrcode_r1_from_fam3 | completed | 2000 | 0.4 | 0.013392703893594444 | 2026-10-24T07:30:17+00:00 | 2026-10-24T08:31:02+00:00 |
| stage3_adapt_scan_object_r1_from_fam1 | completed | 2000 | 0.0 | 0.038049945606850086 | 2026-10-24T19:00:30+00:00 | 2026-10-24T20:33:02+00:00 |
| stage3_adapt_scan_object_r1_from_fam2 | completed | 2000 | 0.0 | 0.027192694705910982 | 2026-10-24T20:33:33+00:00 | 2026-10-24T22:07:12+00:00 |
| stage3_adapt_scan_object_r1_from_fam3 | completed | 2000 | 0.0 | 0.032976289808750156 | 2026-10-24T20:34:04+00:00 | 2026-10-24T22:07:30+00:00 |
| stage3_adapt_stack_blocks_two_r1_from_fam1 | completed | 2000 | 0.2 | 0.01840924019459635 | 2026-10-24T13:06:16+00:00 | 2026-10-24T14:19:27+00:00 |
| stage3_adapt_stack_blocks_two_r1_from_fam2 | completed | 2000 | 0.0 | 0.014890197185799479 | 2026-10-24T13:06:47+00:00 | 2026-10-24T14:29:31+00:00 |
| stage3_adapt_stack_blocks_two_r1_from_fam3 | completed | 2000 | 0.0 | 0.011996836350765079 | 2026-10-24T14:30:02+00:00 | 2026-10-24T15:47:25+00:00 |
| stage3_source_fam1_r1 | stopped | 15000 | 0.8 | 0.013236459823325277 | 2026-10-22T06:36:43+00:00 | - |
| stage3_source_fam2_r1 | completed | 15000 | 0.8 | 0.017694183138199152 | 2026-10-22T12:04:25+00:00 | 2026-10-22T23:07:06+00:00 |
| stage3_source_fam3_r1 | completed | 15000 | 0.55 | 0.015705752642825244 | 2026-10-22T12:04:56+00:00 | 2026-10-22T20:24:22+00:00 |
| stage3_source_fam3_r1_long | stopped | 2000 | - | - | 2026-10-23T09:53:31+00:00 | - |

## 总汇总

- 源模型: 4 个（完成 2）
- 微调模型（目标适应）: 30 个（完成 30，延后 0）
- 延后作业（预实验与微调）: 20
- 终态作业合计: 32 / 54
- 微调模型清单: `docs/models_manifest.md`（模型ID／起点模型／目标任务／实际步数／早停／检查点路径／最近回测成功率）
- 磁盘：卷剩余 985 GiB

