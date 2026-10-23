更新时间（带时区）: 2026-10-23T10:03:29+0000

# stage3_source_fam2_r1

- 阶段: 3 / 类型: source / 重复种子 r=1
- 源族: 2 / 目标任务: None
- 数据: pi05_30_aloha_fam2_place_object_basket_place_cans_plasticbox_place_bread_skillet_put_object_cabinet_src50
- 初始权重: /data/szgx/xworld-gzh/cache/openpi/openpi-assets/checkpoints/pi05_base/params
- 步数上限: 15001；训练种子: 1
- 学习率: 2.5e-05；chunk_size(action_horizon): 10
- 回测任务: place_object_basket, place_cans_plasticbox, place_bread_skillet, put_object_cabinet；回测种子: [500100, 500101, 500102, 500103, 500104]
- 状态: completed

| 步数 | loss(500步均值) | 各任务成功数/回合 | 平均成功率 | 检查点 | 早停判断 |
|---:|---:|---|---:|---|---|
| 2000 | 0.07230158156901598 | place_object_basket:0/5 place_cans_plasticbox:2/5 place_bread_skillet:3/5 put_object_cabinet:0/5 | 0.25 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam2/2000 | 未提升3/3 loss未达标 |
| 4000 | 0.04609180500358343 | place_object_basket:4/5 place_cans_plasticbox:3/5 place_bread_skillet:3/5 put_object_cabinet:2/5 | 0.6 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam2/4000 | 未提升3/3 loss未达标 |
| 6000 | 0.0366828464102 | place_object_basket:4/5 place_cans_plasticbox:5/5 place_bread_skillet:2/5 put_object_cabinet:1/5 | 0.6 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam2/6000 | 未提升3/3 loss未达标 |
| 8000 | 0.02888466195203364 | place_object_basket:4/5 place_cans_plasticbox:5/5 place_bread_skillet:4/5 put_object_cabinet:4/5 | 0.85 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam2/8000 | 未提升3/3 loss未达标 |
| 10000 | 0.025182031098753214 | place_object_basket:4/5 place_cans_plasticbox:5/5 place_bread_skillet:5/5 put_object_cabinet:4/5 | 0.9 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam2/10000 | 未提升3/3 loss未达标 |
| 12000 | 0.020745974758639932 | place_object_basket:4/5 place_cans_plasticbox:5/5 place_bread_skillet:5/5 put_object_cabinet:3/5 | 0.85 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam2/12000 | 未提升3/3 loss未达标 |
| 14000 | 0.019136248860508204 | place_object_basket:4/5 place_cans_plasticbox:4/5 place_bread_skillet:3/5 put_object_cabinet:3/5 | 0.7 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam2/14000 | 未提升3/3 loss未达标 |
| 15000 | 0.017694183138199152 | place_object_basket:2/5 place_cans_plasticbox:5/5 place_bread_skillet:5/5 put_object_cabinet:4/5 | 0.8 | /data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam2/15000 | 停止 |

最终检查点: {"step": 15000, "params_only": {"path": "/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam2_final_step15000", "bytes": 12440713157, "files": 42, "restored_leaves": 51, "verified": true, "source_files": 42}}

里程碑（仅权重）: {"15000": {"path": "/data/szgx/gaohang/pi05_30/runs/stage3/pi05_aloha_robotwin_30/aloha_r1_source_fam2_step15000", "bytes": 12440713157, "files": 42, "restored_leaves": 51, "verified": true, "source_files": 42}}
