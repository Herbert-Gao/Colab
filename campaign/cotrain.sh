#!/usr/bin/env bash
# Train several jobs side by side, each on its own set of cards.
#
#   cotrain.sh <job_id> [<job_id> ...]
#
# Every job runs as its own process (campaign/run_job.sh) with the GPU layout
# from its job record, so two source models share the eight cards: one on
# 0-3, the other on 4-7.  A job that fails is restarted from its last recovery
# point (the run book allows two retries); the other job keeps running.
#
# The driver waits until the machine is idle before it starts, writes the
# progress documents afterwards and sends the round summary through lark-im.
set -uo pipefail

ROOT=${PI05_30_ROOT:-/data/szgx/gaohang/pi05_30}
CAMPAIGN="$ROOT/campaign"
PY=${PI05_PYTHON:-/data/szgx/xworld-gzh/third_party/external/openpi/.venv/bin/python}
LOG="$ROOT/logs/cotrain.log"
mkdir -p "$ROOT/logs"
say() { echo "[$(date -Is)] $*" | tee -a "$LOG"; }

JOBS=("$@")
if [[ ${#JOBS[@]} -eq 0 ]]; then
  say "usage: cotrain.sh <job_id> [<job_id> ...]"
  exit 2
fi

status_of() { $PY "$CAMPAIGN/jobctl.py" field "$1" status 2>/dev/null; }

wait_for_idle() {
  local WORKERS
  while true; do
    WORKERS=$(pgrep -fc "campaign/(run_job.sh|train_job.py|backtest.py|policy_server.py|robotwin_eval.py)" 2>/dev/null | head -1)
    WORKERS=${WORKERS:-0}
    if [[ "$WORKERS" -eq 0 ]]; then
      sleep 20
      WORKERS=$(pgrep -fc "campaign/(run_job.sh|train_job.py|backtest.py|policy_server.py|robotwin_eval.py)" 2>/dev/null | head -1)
      WORKERS=${WORKERS:-0}
      [[ "$WORKERS" -eq 0 ]] && return
    fi
    say "waiting for the machine to be idle (workers=$WORKERS)"
    sleep 60
  done
}

terminal() {
  case "$1" in
    completed|early_stopped|failed|skipped|deferred|stopped) return 0 ;;
    *) return 1 ;;
  esac
}

say "cotrain driver starting: ${JOBS[*]}"
wait_for_idle

for ATTEMPT in 1 2 3; do
  RUNNING=()
  for JOB in "${JOBS[@]}"; do
    STATE=$(status_of "$JOB")
    if terminal "$STATE"; then
      say "skip $JOB ($STATE)"
      continue
    fi
    bash "$CAMPAIGN/run_job.sh" "$JOB" >> "$LOG" 2>&1 &
    RUNNING+=("$!")
    say "started $JOB (attempt $ATTEMPT, pid ${RUNNING[-1]})"
    # Give the first trainer time to claim its cards before the next job
    # starts, so the two jobs never fight over the same device.
    sleep 30
  done
  if [[ ${#RUNNING[@]} -eq 0 ]]; then
    break
  fi
  wait "${RUNNING[@]}"
  PENDING=0
  for JOB in "${JOBS[@]}"; do
    STATE=$(status_of "$JOB")
    say "$JOB -> $STATE"
    terminal "$STATE" || PENDING=1
  done
  [[ "$PENDING" == "0" ]] && break
  [[ "$ATTEMPT" == "3" ]] && break
  say "retrying the jobs that did not finish"
  sleep 60
done

"$PY" -u "$CAMPAIGN/write_docs.py" >> "$LOG" 2>&1
"$PY" -u "$CAMPAIGN/manifest.py" >> "$LOG" 2>&1
SUMMARY=$("$PY" - <<'PYEOF'
import json, pathlib
root = pathlib.Path("/data/szgx/gaohang/pi05_30/state/jobs")
rows = []
for path in sorted(root.glob("stage3_source_*.json")):
    job = json.loads(path.read_text())
    history = job.get("history") or []
    last = history[-1] if history else {}
    rows.append(f"{job['job_id']}={job.get('status')}"
                f"(step {last.get('step', job.get('current_step', 0))},"
                f"成功率 {last.get('mean_success_rate', '-')})")
print("; ".join(rows))
PYEOF
)
say "cotrain finished: $SUMMARY"
if [[ "${PI05_COTRAIN_NOTIFY:-1}" == "1" ]]; then
  "$PY" -u -c "
import sys; sys.path.insert(0, '$CAMPAIGN')
import notify_channel
record = notify_channel.send('服务器A/A800×8｜阶段3：co-train 源模型完成（$SUMMARY）。')
print('notify status:', record.get('status'))
" >> "$LOG" 2>&1
fi
say "cotrain driver finished"
