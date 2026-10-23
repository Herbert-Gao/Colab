#!/usr/bin/env bash
# Wait until every source model of this round reached a terminal state, then
# write the deliverables: the model manifest (with the verified checkpoint
# paths), the machine-readable job table, the Chinese summary and the progress
# document.
#
# It runs independently of the training driver, so the round is complete even
# if the driver has to be restarted in between.
set -uo pipefail

ROOT=${PI05_30_ROOT:-/data/szgx/gaohang/pi05_30}
CAMPAIGN="$ROOT/campaign"
PY=${PI05_PYTHON:-/data/szgx/xworld-gzh/third_party/external/openpi/.venv/bin/python}
LOG="$ROOT/logs/finalize.log"
mkdir -p "$ROOT/logs"
say() { echo "[$(date -Is)] $*" | tee -a "$LOG"; }

pending_sources() {
  "$PY" - <<'PYEOF'
import json, pathlib
root = pathlib.Path("/data/szgx/gaohang/pi05_30/state/jobs")
terminal = ("completed", "early_stopped", "failed", "stopped", "deferred")
count = 0
for path in root.glob("*.json"):
    job = json.loads(path.read_text())
    if job.get("kind") == "source" and job.get("status") not in terminal:
        count += 1
print(count)
PYEOF
}

say "finalizer waiting for the source models to reach a terminal state"
while true; do
  LEFT=$(pending_sources)
  [[ "$LEFT" == "0" ]] && break
  sleep 120
done
say "all source models are terminal -> writing the deliverables"
"$PY" -u "$CAMPAIGN/manifest.py" >> "$LOG" 2>&1
"$PY" -u "$CAMPAIGN/deliverables.py" >> "$LOG" 2>&1
"$PY" -u "$CAMPAIGN/write_docs.py" >> "$LOG" 2>&1
say "deliverables written"
