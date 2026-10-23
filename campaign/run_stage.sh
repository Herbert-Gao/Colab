#!/usr/bin/env bash
# Unattended campaign driver.
#
#   run_stage.sh [stage ...]      # default: 1 2 4 3
#
# Queue stage numbers: 1 = 阶段1 (source hyper-parameter pilot), 2 = 阶段2
# (end-to-end trial), 4 = 阶段2b (adaptation hyper-parameter pilot), 3 = 阶段3
# (formal training).  The final evaluation (100 episodes per delivered
# checkpoint plus the 0-step baseline) is NOT part of this round.
#
# Each job runs as its own process, so a crash, a kill or a reboot never takes
# the driver with it: the next pass skips the jobs that already reached a
# terminal state.
set -uo pipefail

ROOT=${PI05_30_ROOT:-/data/szgx/gaohang/pi05_30}
CAMPAIGN="$ROOT/campaign"
PY=${PI05_PYTHON:-/data/szgx/xworld-gzh/third_party/external/openpi/.venv/bin/python}
DRIVER_LOG="$ROOT/logs/campaign_driver.log"
mkdir -p "$ROOT/logs"
say() { echo "[$(date -Is)] $*" | tee -a "$DRIVER_LOG"; }

TERMINAL='("completed", "early_stopped", "failed", "skipped")'

pending_count() {
  "$PY" - "$1" <<'PYEOF'
import json, sys, pathlib
root = pathlib.Path("/data/szgx/gaohang/pi05_30")
stage = int(sys.argv[1])
terminal = ("completed", "early_stopped", "failed", "skipped", "stopped", "deferred")
count = 0
for path in (root / "state" / "jobs").glob("*.json"):
    job = json.loads(path.read_text())
    if job.get("stage") == stage and job.get("status") not in terminal:
        count += 1
print(count)
PYEOF
}

wait_for_idle() {
  # Never run two campaigns on this machine at the same time: any queue, job
  # runner, trainer, backtest or policy server counts as busy.
  local WORKERS
  while true; do
    WORKERS=$(pgrep -fc "campaign/(queue.sh|run_job.sh|train_job.py|backtest.py|policy_server.py|robotwin_eval.py)" 2>/dev/null | head -1)
    WORKERS=${WORKERS:-0}
    if [[ "$WORKERS" -eq 0 ]]; then
      sleep 20
      WORKERS=$(pgrep -fc "campaign/(queue.sh|run_job.sh|train_job.py|backtest.py|policy_server.py|robotwin_eval.py)" 2>/dev/null | head -1)
      WORKERS=${WORKERS:-0}
      [[ "$WORKERS" -eq 0 ]] && return
    fi
    say "waiting for the machine to be idle (workers=$WORKERS)"
    sleep 60
  done
}

run_stage() {
  local STAGE=$1
  for PASS in $(seq 1 30); do
    local LEFT
    LEFT=$(pending_count "$STAGE")
    [[ "$LEFT" == "0" ]] && break
    say "stage $STAGE: $LEFT job(s) pending (pass $PASS)"
    wait_for_idle
    bash "$CAMPAIGN/queue.sh" "$STAGE" >> "$DRIVER_LOG" 2>&1
  done
  say "stage $STAGE finished with $(pending_count "$STAGE") job(s) not in a terminal state"
}

stage0_gpu_validations() {
  # Section 1.2 items 6-9 need an idle machine: the 8-card NCCL check, the
  # training smoke, the evaluation smoke and the 10-minute parallel window.
  local NEED
  NEED=$("$PY" - <<'PYEOF'
import json, pathlib
state = pathlib.Path("/data/szgx/gaohang/pi05_30/state")
smoke_ok = False
smoke = state / "smoke_validation.json"
if smoke.is_file():
    data = json.loads(smoke.read_text())
    smoke_ok = all(data.get(part, {}).get("ok") for part in ("train", "eval", "parallel"))
gpu_ok = False
preflight = state / "preflight.json"
if preflight.is_file():
    for entry in json.loads(preflight.read_text()):
        if entry.get("no") == 6:
            gpu_ok = bool(entry.get("passed"))
print("0" if (smoke_ok and gpu_ok) else "1")
PYEOF
)
  [[ "$NEED" == "0" ]] && return 0
  say "stage 0: re-running the GPU-bound validations (8-card NCCL, training smoke, evaluation smoke, 10-minute parallel window)"
  wait_for_idle
  "$PY" -u "$CAMPAIGN/smoke_validate.py" >> "$DRIVER_LOG" 2>&1
  "$PY" -u "$CAMPAIGN/preflight.py" >> "$DRIVER_LOG" 2>&1
}

STAGES="${*:-1 2 4 3}"
say "campaign driver starting (stages: $STAGES)"
stage0_gpu_validations

for STAGE in $STAGES; do
  run_stage "$STAGE"
  case "$STAGE" in
    1)
      say "stage 1: selecting the source hyper-parameters"
      if "$PY" -u "$CAMPAIGN/select_hparams.py" --stage 1 >> "$DRIVER_LOG" 2>&1; then
        say "stage 1 selection frozen: $(cat "$ROOT/state/hparams.json")"
      else
        say "stage 1 selection FAILED (see $DRIVER_LOG)"
      fi
      "$PY" "$CAMPAIGN/jobctl.py" set-hparams >> "$DRIVER_LOG" 2>&1
      "$PY" -u "$CAMPAIGN/plan.py" >> "$DRIVER_LOG" 2>&1
      "$PY" -u "$CAMPAIGN/cleanup_stage.py" --stage 1 >> "$DRIVER_LOG" 2>&1
      ;;
    2)
      say "stage 2 done; the trial artifacts stay until stage 2b has selected the adaptation hyper-parameters"
      ;;
    4)
      say "stage 2b: selecting the adaptation hyper-parameters"
      if "$PY" -u "$CAMPAIGN/select_hparams.py" --stage 2b >> "$DRIVER_LOG" 2>&1; then
        say "stage 2b selection frozen: $(cat "$ROOT/state/hparams_adapt.json")"
      else
        say "stage 2b selection FAILED (see $DRIVER_LOG)"
      fi
      "$PY" "$CAMPAIGN/jobctl.py" set-hparams >> "$DRIVER_LOG" 2>&1
      "$PY" -u "$CAMPAIGN/plan.py" >> "$DRIVER_LOG" 2>&1
      "$PY" -u "$CAMPAIGN/cleanup_stage.py" --stage 2 --all >> "$DRIVER_LOG" 2>&1
      "$PY" -u "$CAMPAIGN/cleanup_stage.py" --stage 4 >> "$DRIVER_LOG" 2>&1
      ;;
    3)
      say "stage 3: writing the model manifest, the round summary and the deliverables"
      "$PY" -u "$CAMPAIGN/manifest.py" >> "$DRIVER_LOG" 2>&1
      "$PY" -u "$CAMPAIGN/deliverables.py" >> "$DRIVER_LOG" 2>&1
      "$PY" -u "$CAMPAIGN/write_docs.py" >> "$DRIVER_LOG" 2>&1
      if [[ "$(pending_count 3)" == "0" ]]; then
        say "stage 3: every job reached a terminal state - sending the completion notice"
        "$PY" -u "$CAMPAIGN/manifest.py" --notify >> "$DRIVER_LOG" 2>&1
      fi
      ;;
  esac
done
say "campaign driver finished"
