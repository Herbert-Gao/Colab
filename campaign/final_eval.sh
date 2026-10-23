#!/usr/bin/env bash
# Final evaluation (section 3): every delivered checkpoint of every job, plus
# the zero-step baseline of each source model on each target task.
#
#   final_eval.sh <job_id>          # one job's checkpoints
#   final_eval.sh --zero-shot <source_job_id> <target_index>
#   final_eval.sh --all             # everything that is ready
set -uo pipefail

ROOT=${PI05_30_ROOT:-/data/szgx/gaohang/pi05_30}
CAMPAIGN="$ROOT/campaign"
PY=${PI05_PYTHON:-/data/szgx/xworld-gzh/third_party/external/openpi/.venv/bin/python}
LOG="$ROOT/logs/final_eval.log"
mkdir -p "$ROOT/logs"
say() { echo "[$(date -Is)] $*" | tee -a "$LOG"; }

case "${1:-}" in
  --zero-shot)
    "$PY" -u "$CAMPAIGN/final_eval.py" zero-shot --job-id "$2" --target-index "$3" >> "$LOG" 2>&1
    say "zero-shot $2 target#$3 done"
    ;;
  --all)
    for JOB_FILE in "$ROOT"/state/jobs/*.json; do
      JOB_ID=$(basename "$JOB_FILE" .json)
      case "$JOB_ID" in
        stage1_*) continue ;;
      esac
      "$PY" -u "$CAMPAIGN/final_eval.py" job --job-id "$JOB_ID" >> "$LOG" 2>&1
      say "final eval $JOB_ID done"
    done
    "$PY" -u "$CAMPAIGN/final_eval.py" doc >> "$LOG" 2>&1
    ;;
  *)
    "$PY" -u "$CAMPAIGN/final_eval.py" job --job-id "${1:?usage: final_eval.sh <job_id>}" >> "$LOG" 2>&1
    say "final eval ${1} done"
    ;;
esac
