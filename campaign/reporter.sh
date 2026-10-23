#!/usr/bin/env bash
# Append a one-line campaign status every 5 minutes (so long gaps can be
# reconstructed from a single file instead of live polling).
set -uo pipefail
ROOT=${PI05_30_ROOT:-/data/szgx/gaohang/pi05_30}
PY=${PI05_PYTHON:-/data/szgx/xworld-gzh/third_party/external/openpi/.venv/bin/python}
OUT="$ROOT/logs/status_history.log"
while true; do
  sleep 300
  "$PY" - >> "$OUT" <<'PYEOF'
import json, pathlib, time, subprocess
root = pathlib.Path("/data/szgx/gaohang/pi05_30")
counts, results = {}, []
for path in (root / "state" / "jobs").glob("*.json"):
    try:
        job = json.loads(path.read_text())
    except Exception:
        continue
    status = job.get("status", "?")
    counts[status] = counts.get(status, 0) + 1
    history = job.get("history") or []
    if history:
        results.append((job["job_id"], history[-1]["mean_success_rate"]))
trainer = subprocess.run(["pgrep", "-fc", "campaign/train_job.py"], capture_output=True, text=True).stdout.strip()
stage1 = [r for r in results if r[0].startswith("stage1_")]
print(time.strftime("%Y-%m-%dT%H:%M:%S%z"),
      "jobs=" + json.dumps(counts, ensure_ascii=False),
      "trainers=" + (trainer or "0"),
      "stage1=" + ",".join(f"{j}:{r}" for j, r in sorted(stage1)))
PYEOF
done
