更新时间（带时区）: 2026-10-22T17:20:00+0000
# 阶段0 前置检查结果（服务器 A）


机体: aloha-agilex（ALOHA 双臂）；训练、仿真评估、归一化使用同一套关节/相机/夹爪映射。

| 序号 | 项目 | 结果 | 证据 |
|---:|---|---|---|
| 1 | 复用现有 RoboTwin 环境并创建 ALOHA 任务 | 通过 | task_config/demo_clean.yml embodiment=['aloha-agilex']（唯一机体），相机 D435+D435×2；30/30 个任务实例化成功 |
| 2 | 训练环境（openpi/JAX 版本锁定） | 通过 | python=3.11.16 jax=0.5.3 devices=8 driver=580.65.06 freeze=/data/szgx/gaohang/pi05_30/snapshots/openpi_venv_pip_freeze.txt |
| 3 | 评测环境（渲染/物理/相机） | 通过 | sapien=3.0.0b1 torch=2.4.1+cu121 cuda=True; 无头渲染使用 EGL/sapien，训练与评测环境分离 |
| 4 | π0.5 预训练权重校验与离线可加载 | 通过 | params=11.6 GiB，离线 restore 叶子 51 个 / 3353433872 参数，工作目录软链 /data/szgx/gaohang/pi05_30/weights/pi05_base_params |
| 5 | 20源+10目标数据（ALOHA）与统一归一化统计量 | 通过 | datasets=44 全部 aloha_agilex，统计量 1000 条示范 / 217680 帧，sha256=2b66b3e6840d6b4a…，示范编号与校验和见 state/norm_stats_manifest.json；本轮重建的 10 个目标子集另经 `prepare_data.py verify` 复检（robot_type=aloha_agilex、各 5 回合、state/action 形状 (14,)） |
| 6 | 8 卡 NCCL 通信与小批量前反向 | 通过 | 8 卡 FSDP 实际训练完成：`stage3_source_fam1_r1` 在 8 卡上从 step 6001 连续跑到 25825（检查点 7500 / 15000 / 25000 均落盘），2026-10-22 的日志中 NCCL/CUDA 错误计数为 0（`grep 'NCCL error\|ncclInternalError\|CUDA error'` 在 10-21 之后无命中）；原预检记录的 OOM 发生在机器同时跑训练时，非配置问题。另本轮 co-train 的两组 4 卡 FSDP（GPU0-3 / GPU4-7）亦全程无通信错误 |
| 7 | 训练冒烟（20 步保存 + 恢复续训） | 通过 | state/smoke_validation.json：train.ok=true，训练 41 步、checkpoint 20/40 已保存、从 step 20 恢复续训到 40，loss 全精度轨迹 41 行（logs/smoke_validation_loss_trace.csv）。按运营 2026-10-22 指示本轮不再重跑 smoke，该次记录即为证据 |
| 8 | 评测冒烟（2 回合全链路） | 通过 | eval/smoke/move_pillbottle_pad/episodes.json：2 个有效回合（种子 500000 / 500001，该次冒烟早于回测种子口径调整），逐回合结果与指令已写入；state/smoke_validation.json 的 eval.ok=true |
| 9 | 训练与评测并行（10 分钟无冲突） | 通过 | state/smoke_validation.json 的 parallel 段：ok=true，训练进程存活、并行窗口 10.1 分钟、评测完成 5 回合、无冲突（该次冒烟早于证据落盘改造，证据保存在 smoke_validation.json 内） |
| 10 | 磁盘与权限 | 通过 | 剩余 3130 GiB，单作业峰值估算 258 GiB；工作目录可写=True docs=True |
| 11 | 飞书通知通道（lark-bot-bridge → OMP → lark-im） | 通过 | status=sent receipt={"ok": true, "identity": "bot", "data": {"chat_id": "oc_59380a2551cfa7641dc64b4982dd0405", "create_time": "2026-10-21 02:30:28", "message_id": "om_x100b62b67286 |
| 12 | 环境/配置冻结快照 | 通过 | /data/szgx/gaohang/pi05_30/snapshots/campaign_freeze.json（openpi@215abfb217，18 个脚本摘要 8e29449b0718f41d…） |

## 本轮实际使用的训练参数（运营 2026-10-22 改为 openpi 官方口径）

- **学习率**：`peak_lr 2.5e-05`（openpi 官方 `CosineDecaySchedule` 默认值，`openpi/training/config.py`），
  warmup 1000，cosine decay 30000 → 2.5e-06
- **chunk_size**：`action_horizon 10`（官方 `pi05_aloha_robotwin_h10` 模型配置）
- 全局 batch 32，AdamW(b1 0.9 / b2 0.95 / eps 1e-8 / wd 1e-10 / clip 1.0)，ema_decay 0.99，训练种子 1
- **步数**：15000（阶段1/2/2b 预实验与 30 个微调作业的预实验轮次已按运营指示延后）
- **保存与回测**：每 500 步保存（同时整除 2000 步回测节奏与 7500/15000 里程碑），每 2000 步回测 5 回合
  （场景种子 500100+i），最终步权重另回测一次
- **GPU**：训练 8 卡 FSDP（S2: GPU0-3、S3: GPU4-7 两两共训，显存配额 0.72），回测只用本作业的卡组
- **归一化统计量**：20 源任务 × 50 示范，目标任务不参与
