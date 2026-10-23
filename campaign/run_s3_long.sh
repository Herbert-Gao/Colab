#!/usr/bin/env bash
# Longer budget for the third family.
#
# The operator gave the third source family more steps: its 15,000-step run left
# stack_blocks_three at 0/5 while the loss was still falling.  This script runs
# the continuation (another 15,000 steps from the delivered weights) after the
# running adaptation pair and before the rest of the fine-tuning matrix, so the
# ten adaptations that start from the third family use the improved model.
set -uo pipefail

ROOT=${PI05_30_ROOT:-/data/szgx/gaohang/pi05_30}
CAMPAIGN="$ROOT/campaign"
PY=${PI05_PYTHON:-/data/szgx/xworld-gzh/third_party/external/openpi/.venv/bin/python}
LOG="$ROOT/logs/s3_long.log"
JOB=stage3_source_fam3_r1_long
mkdir -p "$ROOT/logs"
say() { echo "[$(date -Is)] $*" | tee -a "$LOG"; }

running_adaptations() {
  "$PY" - <<'PYEOF'
import json, pathlib
root = pathlib.Path("/data/szgx/gaohang/pi05_30/state/jobs")
count = 0
for path in root.glob("stage3_adapt_*.json"):
    job = json.loads(path.read_text())
    if job.get("status") == "running":
        count += 1
print(count)
PYEOF
}

evaluation_running() {
  pgrep -fc "campaign/eval_sources.py" 2>/dev/null | head -1
}

# The generalization test owns the whole machine (two policy servers plus
# twelve simulators), so the longer run waits for it.  The fine-tuning matrix
# stays stopped: the operator ended it once the weights were saved.
say "waiting for the generalization test to finish"
while true; do
  LEFT=$(evaluation_running)
  [[ -z "$LEFT" || "$LEFT" == "0" ]] && break
  sleep 120
done
say "the evaluation is done -> starting $JOB"
bash "$CAMPAIGN/run_job.sh" "$JOB" >> "$LOG" 2>&1
say "$JOB finished (status=$($PY "$CAMPAIGN/jobctl.py" field "$JOB" status))"

# The longer run supersedes the 15,000-step weights of the third family: the
# adaptation jobs that start from that family use the improved model.
"$PY" - <<'PYEOF' >> "$LOG" 2>&1
import json, pathlib
root = pathlib.Path("/data/szgx/gaohang/pi05_30/state/jobs")
long_job = json.loads((root / "stage3_source_fam3_r1_long.json").read_text())
delivered = ((long_job.get("final_checkpoint") or {}).get("params_only") or {}).get("path")
if delivered:
    base = root / "stage3_source_fam3_r1.json"
    job = json.loads(base.read_text())
    job["superseded_by"] = "stage3_source_fam3_r1_long"
    job["delivered_weights_note"] = (
        "15,000 步的权重已交付；族③ 的最终交付权重改为 stage3_source_fam3_r1_long "
        "(同族续训 15,000 步，共 30,000 步)")
    base.write_text(json.dumps(job, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"stage3_source_fam3_r1: superseded by {delivered}")
PYEOF

"$PY" -u "$CAMPAIGN/manifest.py" >> "$LOG" 2>&1
"$PY" -u "$CAMPAIGN/write_docs.py" >> "$LOG" 2>&1
say "the longer run is delivered; the fine-tuning matrix stays stopped (operator decision)"
