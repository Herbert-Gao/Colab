#!/usr/bin/env bash
# Watchdog for the unattended campaign.
#
# Every cycle it checks that
#   * a driver is alive (the training driver, the matrix driver or the
#     finalizer),
#   * no job is stuck in "running" without a live trainer,
#   * the machine is not oversubscribed (two trainings at once),
# and repairs what it can, notifying through lark-im when it acts.
set -uo pipefail

ROOT=${PI05_30_ROOT:-/data/szgx/gaohang/pi05_30}
CAMPAIGN="$ROOT/campaign"
PY=${PI05_PYTHON:-/data/szgx/xworld-gzh/third_party/external/openpi/.venv/bin/python}
LOG="$ROOT/logs/watchdog.log"
CYCLE=${PI05_WATCHDOG_CYCLE:-300}
mkdir -p "$ROOT/logs"

say() { echo "[$(date -Is)] $*" | tee -a "$LOG"; }

pending_jobs() {
  "$PY" - <<'PYEOF'
import json, pathlib
root = pathlib.Path("/data/szgx/gaohang/pi05_30")
count = 0
for path in (root / "state" / "jobs").glob("*.json"):
    job = json.loads(path.read_text())
    # "deferred" is work that the matrix driver still has to pick up, so it
    # counts as pending here - otherwise the watchdog would idle exactly when
    # the fine-tuning matrix has to start.
    if job.get("status") not in ("completed", "early_stopped", "failed", "skipped", "stopped"):
        count += 1
print(count)
PYEOF
}

stuck_jobs() {
  "$PY" - <<'PYEOF'
import json, pathlib
root = pathlib.Path("/data/szgx/gaohang/pi05_30")
out = []
for path in (root / "state" / "jobs").glob("*.json"):
    job = json.loads(path.read_text())
    if job.get("status") == "running":
        out.append(job["job_id"])
print(" ".join(out))
PYEOF
}

# Which driver belongs to the current phase: the source models first, then the
# fine-tuning matrix, then the finalizer.
phase_driver() {
  "$PY" - <<'PYEOF'
import json, pathlib
root = pathlib.Path("/data/szgx/gaohang/pi05_30")
# The phase file has priority: while the evaluation runs, the fine-tuning
# matrix must not be started on the same cards.
phase_file = root / "state" / "phase.txt"
if phase_file.is_file():
    phase = phase_file.read_text().strip()
    if phase in ("evaluation", "matrix", "source", "finalize"):
        print(phase)
        raise SystemExit(0)
jobs = root / "state" / "jobs"
terminal = ("completed", "early_stopped", "failed", "skipped", "stopped")
sources = adapts = 0
for path in jobs.glob("*.json"):
    job = json.loads(path.read_text())
    if job.get("kind") == "source" and job.get("status") not in terminal:
        sources += 1
    if job.get("kind") == "adapt" and job.get("status") not in terminal:
        adapts += 1
if sources:
    print("source")
elif adapts:
    print("matrix")
else:
    print("finalize")
PYEOF
}

notify() {
  local CHAT
  CHAT=$(cat "$ROOT/state/notify_chat_id" 2>/dev/null)
  [[ -z "$CHAT" ]] && return 0
  LARK_CHANNEL_HOME=/home/szgx/.lark-bot-bridge timeout 120 lark-cli im +messages-send \
    --chat-id "$CHAT" --text "$1" >> "$LOG" 2>&1
}

# remember the chat this session was started from
if [[ ! -f "$ROOT/state/notify_chat_id" ]]; then
  "$PY" - > "$ROOT/state/notify_chat_id" <<'PYEOF'
import json, pathlib
sessions = json.loads((pathlib.Path.home() / ".lark-bot-bridge/profiles/omp/sessions.json").read_text())
print(max(sessions.items(), key=lambda kv: kv[1].get("updatedAt", 0))[0])
PYEOF
fi

while true; do
  sleep "$CYCLE"
  PENDING=$(pending_jobs)
  [[ "$PENDING" == "0" ]] && { say "no pending jobs; watchdog idles"; continue; }

  # Cumulative failures: the user is informed once the threshold is reached.
  "$PY" -u "$CAMPAIGN/failures.py" check >> "$LOG" 2>&1

  DRIVERS=$(pgrep -fc "campaign/(run_stage.sh|cotrain.sh|cotrain_matrix.sh|finalize_round.sh)" 2>/dev/null | head -1); DRIVERS=${DRIVERS:-0}
  TRAINERS=$(pgrep -fc "campaign/train_job.py" 2>/dev/null | head -1); TRAINERS=${TRAINERS:-0}

  if [[ "$DRIVERS" -eq 0 ]]; then
    PHASE=$(phase_driver)
    say "driver is not running ($PENDING pending jobs, phase=$PHASE) -> restarting it"
    case "$PHASE" in
      source) setsid nohup bash "$CAMPAIGN/cotrain.sh" stage3_source_fam2_r1 stage3_source_fam3_r1 \
               >> "$ROOT/logs/driver_stdout.log" 2>&1 < /dev/null & ;;
      matrix) setsid nohup bash "$CAMPAIGN/cotrain_matrix.sh" \
               >> "$ROOT/logs/driver_stdout.log" 2>&1 < /dev/null & ;;
      *)      setsid nohup bash "$CAMPAIGN/finalize_round.sh" \
               >> "$ROOT/logs/driver_stdout.log" 2>&1 < /dev/null & ;;
    esac
    sleep 10
    notify "服务器A/A800×8｜阶段：看门狗检测到驱动进程缺失，已自动重启（$PENDING 个作业待跑）。"
    continue
  fi

  if [[ "$TRAINERS" -eq 0 ]]; then
    STUCK=$(stuck_jobs)
    if [[ -n "${STUCK// /}" ]]; then
      say "jobs marked running without a live trainer: $STUCK -> releasing them"
      for JOB in $STUCK; do
        "$PY" "$CAMPAIGN/jobctl.py" set "$JOB" "status=pending" "released_by=watchdog" >> "$LOG" 2>&1
      done
      notify "服务器A/A800×8｜阶段：作业 ${STUCK} 无训练进程，已释放为待运行并通知。"
    fi
    continue
  fi

  if [[ "$TRAINERS" -gt 1 ]]; then
    say "note: $TRAINERS trainers running at once (expected during co-training)"
  fi
done
