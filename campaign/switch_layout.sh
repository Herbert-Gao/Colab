#!/usr/bin/env bash
# One-off device-layout switch (e.g. 4 -> 8 FSDP devices).
#
#   bash campaign/switch_layout.sh <new_devices>
#
# Checkpoints saved with a different device count cannot be restored, so the
# affected job restarts from the base weights.  This is deliberately NOT part
# of the restart path: campaign/resume.sh must never delete checkpoints or job
# history.
set -uo pipefail

ROOT=${PI05_30_ROOT:-/data/szgx/gaohang/pi05_30}
PY=${PI05_PYTHON:-/data/szgx/xworld-gzh/third_party/external/openpi/.venv/bin/python}
NEW_DEVICES=${1:?usage: switch_layout.sh <new_devices>}

"$PY" - "$NEW_DEVICES" <<'PYEOF'
import json, pathlib, shutil, sys, time

new_devices = int(sys.argv[1])
root = pathlib.Path("/data/szgx/gaohang/pi05_30")
log = root / "docs/cleanup_log.md"
stamp = time.strftime('%Y-%m-%dT%H:%M:%S%z')

for path in sorted((root / "state/jobs").glob("stage3_*.json")):
    job = json.loads(path.read_text())
    if job.get("history") or job.get("processed_checkpoints"):
        job["status"] = "pending"
        job["history"] = []
        job["processed_checkpoints"] = []
        job["current_step"] = 0
        job.pop("pid", None)
        path.write_text(json.dumps(job, indent=2, ensure_ascii=False) + "\n")
        print("reset (old layout cannot be restored):", job["job_id"])

for run in sorted((root / "runs/stage3").glob("*/*")):
    if not run.is_dir():
        continue
    for ckpt in sorted(run.iterdir()):
        if not (ckpt.is_dir() and ckpt.name.isdigit()):
            continue
        size = sum(f.stat().st_size for f in ckpt.rglob("*") if f.is_file())
        shutil.rmtree(ckpt, ignore_errors=True)
        with log.open("a", encoding="utf-8") as handle:
            handle.write(f"| {stamp} | {ckpt} | {ckpt.name} | "
                         f"切换到 {new_devices} 设备 FSDP 布局，旧布局检查点无法恢复，作业从头重跑 | "
                         f"{size / 1024 ** 3:.1f} |\n")
        print("dropped:", ckpt)
PYEOF
