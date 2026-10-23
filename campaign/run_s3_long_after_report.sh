#!/usr/bin/env bash
# Start the longer third-family run after the generalization test and its
# refill are done.
#
# The test owns the whole machine (two policy servers plus twelve simulators),
# so the longer run has to wait: running both at once would put the trainer and
# the evaluation on the same cards.
set -uo pipefail

ROOT=${PI05_30_ROOT:-/data/szgx/gaohang/pi05_30}
CAMPAIGN="$ROOT/campaign"
PY=${PI05_PYTHON:-/data/szgx/xworld-gzh/third_party/external/openpi/.venv/bin/python}
LOG="$ROOT/logs/s3_long.log"
JOB=stage3_source_fam3_r1_long
mkdir -p "$ROOT/logs"
say() { echo "[$(date -Is)] $*" | tee -a "$LOG"; }

busy() {
  pgrep -fc "campaign/(eval_sources.py|refill_missing_eval.py|eval_report.py|report_watch.sh)" 2>/dev/null | head -1
}

say "waiting for the evaluation, its refill and the report to finish"
while true; do
  LEFT=$(busy)
  [[ -z "$LEFT" || "$LEFT" == "0" ]] && break
  sleep 120
done
say "the machine is free -> starting $JOB"
bash "$CAMPAIGN/run_job.sh" "$JOB" >> "$LOG" 2>&1
say "$JOB finished (status=$($PY "$CAMPAIGN/jobctl.py" field "$JOB" status))"

# The longer run supersedes the 15,000-step weights of the third family.
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
