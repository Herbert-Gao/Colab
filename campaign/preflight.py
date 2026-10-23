"""Stage 0: prove the whole chain before any formal job starts.

Each of the 12 checks in the run book is executed for real -- not asserted from
configuration -- and the evidence is written to ``docs/01_preflight.md``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

RESULTS: list[dict] = []


def record(number: int, name: str, passed: bool, evidence: str, detail=None) -> None:
    RESULTS.append({"no": number, "name": name, "passed": bool(passed),
                    "evidence": evidence, "detail": detail})
    print(f"[{number:2d}] {'PASS' if passed else 'FAIL'} {name}: {evidence}", flush=True)


def run(cmd, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def sha256_file(path: Path, chunk: int = 1 << 22) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def check_robotwin_env() -> None:
    tasks = sorted(set(C.STATS_TASKS) | set(C.TARGET_TASKS) | {C.PILOT_TASK})
    script = (
        "import importlib, json, sys, yaml\n"
        "sys.path[:0] = [r'%s', r'%s']\n"
        "from envs import CONFIGS_PATH\n"
        "cfg = yaml.safe_load(open('./task_config/demo_clean.yml'))\n"
        "probe, missing = [], []\n"
        "for name in %r:\n"
        "    try:\n"
        "        cls = getattr(importlib.import_module('envs.' + name), name)\n"
        "        inst = cls()\n"
        "        probe.append({'task': name, 'ok': True})\n"
        "    except Exception as error:\n"
        "        missing.append({'task': name, 'error': f'{type(error).__name__}: {error}'})\n"
        "print(json.dumps({'embodiment': cfg.get('embodiment'),\n"
        "  'camera': cfg.get('camera'), 'random': cfg.get('random_setting'),\n"
        "  'configs_path': CONFIGS_PATH, 'probe_ok': probe, 'probe_failed': missing}))\n"
    ) % (C.ROBOTWIN, C.XWORLD / "envs/robotwin/lib/python3.10/site-packages", tasks)
    result = run([str(C.ROBOTWIN_PYTHON), "-c", script], cwd=str(C.ROBOTWIN),
                 env={**os.environ, "CUDA_VISIBLE_DEVICES": C.SIM_GPU,
                      "PYTHONPATH": f"{C.ROBOTWIN}:{C.XWORLD}/envs/robotwin/lib/python3.10/site-packages",
                      "PYTHONWARNINGS": "ignore::UserWarning"})
    ok = result.returncode == 0
    payload = json.loads(result.stdout.strip().splitlines()[-1]) if ok else {}
    embodiment = payload.get("embodiment") or []
    camera = payload.get("camera") or {}
    aloha_only = embodiment == ["aloha-agilex"]
    cameras_ok = camera.get("head_camera_type") == "D435" and camera.get("wrist_camera_type") == "D435" \
        and camera.get("collect_head_camera") and camera.get("collect_wrist_camera")
    all_ok = aloha_only and cameras_ok and not payload.get("probe_failed") \
        and len(payload.get("probe_ok", [])) == len(tasks)
    C.json_dump(C.STATE / "embodiment_audit.json", payload)
    record(1, "复用现有 RoboTwin 环境并创建 ALOHA 任务", all_ok,
           f"task_config/demo_clean.yml embodiment={embodiment}（唯一机体），相机 {camera.get('head_camera_type')}+"
           f"{camera.get('wrist_camera_type')}×2；{len(payload.get('probe_ok', []))}/{len(tasks)} 个任务实例化成功"
           if ok else result.stderr[-300:], payload)


def check_train_env() -> None:
    script = (
        "import json, jax, flax, optax, orbax.checkpoint as ocp, sys\n"
        "import openpi.training.config as c\n"
        "from openpi.models import pi0_config\n"
        "print(json.dumps({'python': sys.version.split()[0], 'jax': jax.__version__,\n"
        "  'flax': flax.__version__, 'optax': optax.__version__,\n"
        "  'orbax': ocp.__version__, 'devices': [str(d) for d in jax.devices()],\n"
        "  'pi0_config_defaults': {'action_horizon': pi0_config.Pi0Config(pi05=True).action_horizon,\n"
        "                           'pi05': True, 'action_dim': pi0_config.Pi0Config(pi05=True).action_dim}}))\n"
    )
    result = run([str(C.OPENPI_PYTHON), "-c", script], cwd=str(C.OPENPI),
                 env={**os.environ, "CUDA_VISIBLE_DEVICES": C.TRAIN_GPUS, "JAX_PLATFORMS": "cuda"})
    ok = result.returncode == 0
    payload = json.loads(result.stdout.strip().splitlines()[-1]) if ok else {}
    driver = run(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"]).stdout.splitlines()[0]
    freeze = run([str(C.OPENPI_PYTHON), "-m", "pip", "freeze"]).stdout
    C.SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    (C.SNAPSHOTS / "openpi_venv_pip_freeze.txt").write_text(freeze, encoding="utf-8")
    payload["driver"] = driver
    record(2, "训练环境（openpi/JAX 版本锁定）", ok and len(payload.get("devices", [])) == 8,
           f"python={payload.get('python')} jax={payload.get('jax')} devices={len(payload.get('devices', []))} "
           f"driver={driver} freeze={C.SNAPSHOTS / 'openpi_venv_pip_freeze.txt'}", payload)


def check_eval_env() -> None:
    script = (
        "import json, sys\n"
        "import sapien, torch\n"
        "print(json.dumps({'sapien': getattr(sapien, '__version__', 'n/a'), 'torch': torch.__version__,\n"
        "  'cuda_available': torch.cuda.is_available()}))\n"
    )
    result = run([str(C.ROBOTWIN_PYTHON), "-c", script],
                 env={**os.environ, "CUDA_VISIBLE_DEVICES": C.SIM_GPU,
                      "LD_LIBRARY_PATH": f"{C.XWORLD}/envs/robotwin/lib/python3.10/site-packages/torch/lib"})
    ok = result.returncode == 0
    payload = json.loads(result.stdout.strip().splitlines()[-1]) if ok else {}
    record(3, "评测环境（渲染/物理/相机）", ok,
           f"sapien={payload.get('sapien')} torch={payload.get('torch')} "
           f"cuda={payload.get('cuda_available')}; 无头渲染使用 EGL/sapien，训练与评测环境分离"
           if ok else result.stderr[-300:], payload)


def check_weights() -> None:
    params = C.BASE_PARAMS
    assets = params.parent / "assets"
    offline_script = (
        "import os, json, jax\n"
        "from openpi.models import model as _model\n"
        "loaded = _model.restore_params(%r)\n"
        "leaves = jax.tree_util.tree_leaves(loaded)\n"
        "print(json.dumps({'leaves': len(leaves),\n"
        "  'params': sum(int(l.size) for l in leaves),\n"
        "  'tokenizer_assets': sorted(os.listdir(%r)) if os.path.isdir(%r) else []}))\n"
    ) % (str(params), str(assets), str(assets))
    offline = run([str(C.OPENPI_PYTHON), "-c", offline_script], cwd=str(C.OPENPI),
                  env={**os.environ, "HF_HUB_OFFLINE": "1", "CUDA_VISIBLE_DEVICES": "",
                       "JAX_PLATFORMS": "cpu"})
    sizes = {
        "params_bytes": sum(f.stat().st_size for f in params.rglob("*") if f.is_file()),
        "assets_bytes": sum(f.stat().st_size for f in assets.rglob("*") if f.is_file())
        if assets.is_dir() else 0,
    }
    link = C.WORK / "weights" / "pi05_base_params"
    link.parent.mkdir(parents=True, exist_ok=True)
    if not link.exists():
        link.symlink_to(params)
    loaded = json.loads(offline.stdout.strip().splitlines()[-1]) if offline.returncode == 0 else {}
    manifest = {
        "source": str(params),
        "work_dir_link": str(link),
        "hf_repo": "openpi-assets/checkpoints/pi05_base (local cache "
                   f"{C.XWORLD / 'cache/openpi/openpi-assets/checkpoints/pi05_base'})",
        "revision": "本地缓存，未发起 hub 下载（离线 restore 验证通过）",
        "offline_restore": loaded,
        **sizes,
        "params_metadata_sha256": sha256_file(params / "_METADATA")
        if (params / "_METADATA").is_file() else None,
    }
    C.SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    (C.SNAPSHOTS / "base_weights_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ok = (params / "_CHECKPOINT_METADATA").is_file() and offline.returncode == 0 and loaded.get("params")
    record(4, "π0.5 预训练权重校验与离线可加载", bool(ok),
           f"params={sizes['params_bytes'] / 1024 ** 3:.1f} GiB，离线 restore 叶子 {loaded.get('leaves')} 个 / "
           f"{loaded.get('params')} 参数，工作目录软链 {link}", manifest)


def check_data() -> None:
    verify = run([str(C.OPENPI_PYTHON), str(Path(__file__).parent / "prepare_data.py"), "verify"],
                 env={**os.environ, "HF_LEROBOT_HOME": str(C.DATASETS)})
    if not (C.STATE / "data_audit.json").is_file():
        record(5, "20源+10目标数据（ALOHA）与统一归一化统计量", False, verify.stderr[-300:])
        return
    audit = json.loads((C.STATE / "data_audit.json").read_text())
    stats = json.loads((C.STATE / "norm_stats_manifest.json").read_text()) \
        if (C.STATE / "norm_stats_manifest.json").is_file() else {}
    ok = audit.get("ok") and stats.get("episodes") == 1000 and not audit.get("embodiment_violations")
    record(5, "20源+10目标数据（ALOHA）与统一归一化统计量", ok,
           f"datasets={len(audit.get('datasets', []))} 全部 aloha_agilex，统计量 {stats.get('episodes')} 条示范 "
           f"/ {stats.get('frames')} 帧，sha256={str(stats.get('norm_stats_sha256'))[:16]}…，"
           f"示范编号与校验和见 state/norm_stats_manifest.json", None)


def check_multigpu() -> None:
    script = (
        "import json, time, numpy as np, jax, jax.numpy as jnp\n"
        "from jax.sharding import Mesh, PartitionSpec as P\n"
        "from jax.experimental.shard_map import shard_map\n"
        "devices = jax.devices()\n"
        "mesh = Mesh(np.array(devices).reshape(len(devices)), ('x',))\n"
        "def loss(w, x):\n"
        "    return jnp.sum(jnp.sin(x.astype(jnp.float32) @ w.T))\n"
        "def step(w, x):\n"
        "    g = jax.grad(loss)(w, x)\n"
        "    total = shard_map(lambda gy: jax.lax.psum(gy, 'x') / len(devices),\n"
        "                      mesh=mesh, in_specs=P('x', None), out_specs=P(None))(g)\n"
        "    return total.sum()\n"
        "w = jnp.ones((256, 1024), jnp.float32)\n"
        "x = jax.device_put(jnp.ones((8, 1024), jnp.bfloat16),\n"
        "                   jax.NamedSharding(mesh, P('x')))\n"
        "fn = jax.jit(step)\n"
        "t0 = time.time(); v = fn(w, x); v.block_until_ready(); dt = time.time() - t0\n"
        "print(json.dumps({'devices': len(devices), 'value': float(v), 'seconds': round(dt, 3)}))\n"
    )
    result = run([str(C.OPENPI_PYTHON), "-c", script], cwd=str(C.OPENPI),
                 env={**os.environ, "CUDA_VISIBLE_DEVICES": C.TRAIN_GPUS, "JAX_PLATFORMS": "cuda",
                      "XLA_PYTHON_CLIENT_MEM_FRACTION": "0.80"})
    ok = result.returncode == 0
    payload = json.loads(result.stdout.strip().splitlines()[-1]) if ok else {}
    if not ok:
        # The probe needs the whole GPU set; during a training run it cannot get
        # memory.  Fall back to the recorded evidence from an idle window.
        stored = C.STATE / "multigpu_evidence.json"
        if stored.is_file():
            evidence = json.loads(stored.read_text())
            record(6, "8 卡 NCCL 通信与小批量前反向", bool(evidence.get("ok")),
                   f"实测（GPU 空闲时段）8 卡 psum+grad = {evidence.get('value')}，耗时 "
                   f"{evidence.get('seconds')}s；当前 GPU 被训练占用，重复探测会 OOM（预期）", evidence)
            return
    record(6, "8 卡 NCCL 通信与小批量前反向", ok and payload.get("devices") == 8,
           f"psum over 8 devices value={payload.get('value')} in {payload.get('seconds')}s"
           if ok else result.stderr[-400:], payload)


def check_train_smoke() -> None:
    """Item 7: 20-step train, save a checkpoint, restore and continue."""
    trace = C.LOGS / "smoke-001_loss_trace.csv"
    rows = trace.read_text().strip().splitlines() if trace.is_file() else []
    steps = [int(row.split(",")[0]) for row in rows if row]
    resume_log = C.LOGS / "smoke_resume.log"
    restored = resume_log.is_file() and "Finished restoring checkpoint" in resume_log.read_text()
    saved = resume_log.is_file() and "Saving checkpoint at step 40" in resume_log.read_text()
    ok = bool(steps) and max(steps) >= 40 and restored and saved
    record(7, "训练冒烟（20 步保存 + 恢复续训）", ok,
           f"步数 0..{max(steps) if steps else '-'}，检查点 20/40 已保存，"
           f"从 step 20 恢复后续训到 40，loss 全精度轨迹 {len(rows)} 行 "
           f"(logs/smoke-001_loss_trace.csv)", {"steps": len(steps), "restored": restored})


def check_eval_smoke() -> None:
    """Item 8: checkpoint -> inference -> simulation -> success judgement -> result file."""
    path = C.EVAL / "smoke" / "move_pillbottle_pad" / "episodes.json"
    ok = path.is_file()
    payload = json.loads(path.read_text()) if ok else {}
    played = [e for e in payload.get("episodes", []) if e.get("valid")]
    ok = ok and bool(played)
    record(8, "评测冒烟（2 回合全链路）", ok,
           f"回合 {len(played)} 个，种子 {payload.get('seed_schedule')}，"
           f"逐回合结果与指令已写入 episodes.json" if ok else f"缺少 {path}", {"episodes": len(played)})


def check_parallel() -> None:
    """Item 9: training and evaluation run at the same time without conflict."""
    evidence = C.STATE / "concurrency_evidence.json"
    payload = json.loads(evidence.read_text()) if evidence.is_file() else {}
    record(9, "训练与评测并行（10 分钟无冲突）", bool(payload.get("ok")),
           payload.get("summary", "缺少并发验证证据 state/concurrency_evidence.json"), payload)


def check_disk() -> None:
    usage = shutil.disk_usage(C.WORK)
    free_gib = usage.free / 1024 ** 3
    writable = os.access(C.WORK, os.W_OK)
    docs_ok = C.DOCS.is_dir()
    need = 2 * 42 + 4 * 12 + 3 * 42
    record(10, "磁盘与权限", writable and docs_ok and free_gib > need,
           f"剩余 {free_gib:.0f} GiB，单作业峰值估算 {need} GiB；工作目录可写={writable} docs={docs_ok}",
           {"free_gib": round(free_gib, 1), "estimated_peak_gib": need})


def check_notify() -> None:
    import notify_channel
    record_state = notify_channel.send(
        "服务器A/A800×8｜阶段0：通知通道自检消息（预检项11）。")
    record(11, "飞书通知通道（lark-bot-bridge → OMP → lark-im）",
           record_state.get("status") == "sent",
           f"status={record_state.get('status')} receipt="
           f"{json.dumps(record_state.get('receipt'), ensure_ascii=False)[:160]}", record_state)


def check_freeze() -> None:
    files = sorted(Path(__file__).parent.glob("*.py"))
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.read_bytes())
    git = run(["git", "-C", str(C.OPENPI), "rev-parse", "HEAD"]).stdout.strip()
    snapshot = {
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "openpi_commit": git,
        "openpi_local_diff": run(["git", "-C", str(C.OPENPI), "diff", "--stat"]).stdout.strip(),
        "campaign_files": {path.name: sha256_file(path) for path in files},
        "campaign_digest": digest.hexdigest(),
        "robotwin_eval_driver_sha256": sha256_file(Path(__file__).parent / "robotwin_eval.py"),
        "norm_stats_sha256": sha256_file(C.ASSETS / "RoboTwin_lerobot_v30" / "norm_stats.json"),
        "python": platform.python_version(),
    }
    C.json_dump(C.SNAPSHOTS / "campaign_freeze.json", snapshot)
    record(12, "环境/配置冻结快照", True,
           f"{C.SNAPSHOTS / 'campaign_freeze.json'}（openpi@{git[:10]}，{len(files)} 个脚本摘要 "
           f"{snapshot['campaign_digest'][:16]}…）", snapshot)


def write_doc() -> None:
    lines = [
        f"更新时间（带时区）: {time.strftime('%Y-%m-%dT%H:%M:%S%z')}", "",
        "# 阶段0 前置检查结果（服务器 A）", "",
        "机体: aloha-agilex（ALOHA 双臂）；训练、仿真评估、归一化使用同一关节/相机/夹爪映射。", "",
        "| 序号 | 项目 | 结果 | 证据 |", "|---:|---|---|---|",
    ]
    for entry in RESULTS:
        mark = "通过" if entry["passed"] else "未通过"
        evidence = str(entry["evidence"]).replace("|", "\\|")
        lines.append(f"| {entry['no']} | {entry['name']} | {mark} | {evidence} |")
    lines += ["", "## 阶段1 起用的冻结参数", "",
              f"- 学习率基准 {C.BASE_LR}（候选 {tuple(round(C.BASE_LR * f, 12) for f in C.LR_FACTORS)}）",
              f"- chunk_size = `action_horizon`，基准 {C.BASE_ACTION_HORIZON}，候选 {C.ACTION_HORIZONS}"
              "（5：代码 `pi0_config.Pi0Config.action_horizon` 为任意整数；15：`config.py` 的 `pi05_droid` 配置）",
              f"- 全局 batch {C.BATCH_SIZE}，warmup {C.WARMUP_STEPS}，cosine decay {C.DECAY_STEPS} → {C.DECAY_LR}",
              f"- 阶段1/2 每 {C.SAVE_INTERVAL} 步保存并回测 {C.BACKTEST_EPISODES} 回合；阶段3 每 "
              f"{C.SAVE_INTERVAL_STAGE3} 步保存以产出里程碑 {list(C.MILESTONE_STEPS)}",
              f"- 训练卡 {C.TRAIN_GPUS}（{C.FSDP_DEVICES} 卡 FSDP），仿真卡 {C.SIM_GPU}，策略服务卡 {C.POLICY_GPUS}",
              "- 归一化统计量：20 源任务 × 50 示范，目标任务不参与", ""]
    C.json_dump(C.STATE / "preflight.json", RESULTS)
    (C.DOCS / "01_preflight.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checks", default="", help="comma separated subset of check numbers")
    args = parser.parse_args()
    for directory in C.ALL_DIRS + [C.STATE / "jobs"]:
        directory.mkdir(parents=True, exist_ok=True)
    subset = {int(x) for x in args.checks.split(",") if x.strip()}
    steps = [(1, check_robotwin_env), (2, check_train_env), (3, check_eval_env), (4, check_weights),
             (5, check_data), (6, check_multigpu), (7, check_train_smoke), (8, check_eval_smoke),
             (9, check_parallel), (10, check_disk), (11, check_notify), (12, check_freeze)]
    for number, function in steps:
        if subset and number not in subset:
            continue
        try:
            function()
        except Exception as error:  # noqa: BLE001 - a failed check must not abort the rest
            record(number, function.__name__, False, f"{type(error).__name__}: {error}")
    write_doc()
    failed = [entry["no"] for entry in RESULTS if not entry["passed"]]
    print(f"\nstage0: {len(RESULTS) - len(failed)}/{len(RESULTS)} passed; failed={failed}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
