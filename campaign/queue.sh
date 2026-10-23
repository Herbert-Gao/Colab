#!/usr/bin/env bash
# Stage queue: run every job of a stage, one at a time, in order.
#
#   queue.sh <stage>
#
# Each job is a separate process (campaign/run_job.sh), so a crash, a kill or a
# reboot never takes the queue with it: the next run simply skips the jobs that
# already reached a terminal state.  A job whose source model failed is marked
# "skipped" - it never blocks the other jobs of the stage.
set -uo pipefail

STAGE=${1:?usage: queue.sh <stage>}
ROOT=${PI05_30_ROOT:-/data/szgx/gaohang/pi05_30}
CAMPAIGN="$ROOT/campaign"
PY=${PI05_PYTHON:-/data/szgx/xworld-gzh/third_party/external/openpi/.venv/bin/python}
QUEUE_LOG="$ROOT/logs/queue_stage${STAGE}.log"
mkdir -p "$ROOT/logs"

say() { echo "[$(date -Is)] $*" | tee -a "$QUEUE_LOG"; }

# Job ids of this stage, in plan order: source jobs first, because an
# adaptation job needs its source model to be finished.
JOB_IDS=$("$PY" - "$STAGE" <<'PYEOF'
import json, sys, pathlib
root = pathlib.Path("/data/szgx/gaohang/pi05_30")
stage = int(sys.argv[1])
rows = []
for path in (root / "state" / "jobs").glob("*.json"):
    job = json.loads(path.read_text())
    if job.get("stage") == stage:
        rows.append(job)
rows.sort(key=lambda job: (bool(job.get("init_from_job")), job["job_id"]))
print(" ".join(job["job_id"] for job in rows))
PYEOF
)

say "stage $STAGE queue: $(echo "$JOB_IDS" | wc -w) jobs"

for JOB_ID in $JOB_IDS; do
  if [[ ! -f "$ROOT/state/jobs/$JOB_ID.json" ]]; then
    say "skip $JOB_ID (no job record)"
    continue
  fi
  STATUS=$($PY "$CAMPAIGN/jobctl.py" field "$JOB_ID" status 2>/dev/null)
  case "$STATUS" in
    completed|early_stopped|failed|skipped|deferred|stopped)
      say "skip $JOB_ID ($STATUS)"
      continue
      ;;
  esac
  # A job that needs a source model waits for that source to finish.
  PARENT=$($PY "$CAMPAIGN/jobctl.py" field "$JOB_ID" init_from_job 2>/dev/null)
  if [[ -n "$PARENT" && "$PARENT" != "None" ]]; then
    PARENT_STATUS=$($PY "$CAMPAIGN/jobctl.py" field "$PARENT" status 2>/dev/null)
    if [[ "$PARENT_STATUS" == "failed" || "$PARENT_STATUS" == "skipped" ]]; then
      say "skip $JOB_ID: source $PARENT is $PARENT_STATUS"
      $PY "$CAMPAIGN/jobctl.py" set "$JOB_ID" "status=skipped" \
        "skip_reason=起点作业 $PARENT 状态为 $PARENT_STATUS" >> "$QUEUE_LOG" 2>&1
      $PY "$CAMPAIGN/write_docs.py" >> "$QUEUE_LOG" 2>&1
      continue
    fi
    if [[ "$PARENT_STATUS" != "completed" && "$PARENT_STATUS" != "early_stopped" ]]; then
      say "wait $JOB_ID: parent $PARENT is $PARENT_STATUS"
      continue
    fi
  fi
  say "start $JOB_ID"
  bash "$CAMPAIGN/run_job.sh" "$JOB_ID" >> "$QUEUE_LOG" 2>&1
  say "done $JOB_ID (status=$($PY "$CAMPAIGN/jobctl.py" field "$JOB_ID" status 2>/dev/null))"
  $PY "$CAMPAIGN/write_docs.py" >> "$QUEUE_LOG" 2>&1
done

say "stage $STAGE queue finished"
