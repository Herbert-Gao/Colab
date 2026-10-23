#!/usr/bin/env bash
# Fine-tuning matrix: the 30 adaptation jobs of this round, two at a time, four
# cards each.
#
#   cotrain_matrix.sh
#
# The driver waits until the source models are finished, gives every adaptation
# job its training specification and its card group, and then walks the jobs in
# pairs.  Every pair is run by campaign/cotrain.sh, which owns the per-job
# retry, the checkpoint bookkeeping and the job document.
#
# The round summary (model manifest, job table, Chinese summary and the lark
# notification) is written when the last pair is done.
set -uo pipefail

ROOT=${PI05_30_ROOT:-/data/szgx/gaohang/pi05_30}
CAMPAIGN="$ROOT/campaign"
PY=${PI05_PYTHON:-/data/szgx/xworld-gzh/third_party/external/openpi/.venv/bin/python}
LOG="$ROOT/logs/cotrain_matrix.log"
mkdir -p "$ROOT/logs"
say() { echo "[$(date -Is)] $*" | tee -a "$LOG"; }

# One matrix driver at a time: the watchdog and the sequencer may both want to
# start one, and two of them would fight over the same adaptation jobs.
mkdir -p "$ROOT/state/locks"
exec 9>"$ROOT/state/locks/cotrain_matrix.lock"
if ! flock -n 9; then
  say "another matrix driver is already running; exiting"
  exit 0
fi

GROUP_A_TRAIN="0,1,2,3"; GROUP_A_POLICY="0,2"; GROUP_A_SIM="1,3"
GROUP_B_TRAIN="4,5,6,7"; GROUP_B_POLICY="4,6"; GROUP_B_SIM="5,7"
MEM_FRACTION=${PI05_MEM_FRACTION:-0.72}

source_models_pending() {
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

say "matrix driver waiting for the source models to reach a terminal state"
while true; do
  LEFT=$(source_models_pending)
  [[ "$LEFT" == "0" ]] && break
  sleep 120
done
say "all source models are terminal"

# The machine can carry another workload (an unrelated training job may hold
# the cards).  The matrix waits for them instead of failing the pairs.
wait_for_free_cards() {
  local BUSY
  while true; do
    BUSY=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null \
           | awk '{s+=$1} END {print s+0}')
    [[ -n "$BUSY" && "$BUSY" -lt 4000 ]] && break
    say "waiting for the cards to be free (busy=${BUSY} MiB)"
    sleep 15
  done
}

# Every source model needs a delivered weight tree that the adaptation jobs
# can start from.  S1 was stopped by the operator, so its 15,000-step
# milestone is used as its delivered weights.
"$PY" - <<'PYEOF'
import json, pathlib
root = pathlib.Path("/data/szgx/gaohang/pi05_30/state/jobs")
for path in sorted(root.glob("stage3_source_*.json")):
    job = json.loads(path.read_text())
    if job.get("status") == "running":
        # A job that is still training will write its own delivered weights.
        print(f"{job['job_id']}: still running, delivered weights come from the job itself")
        continue
    final = job.get("final_checkpoint") or {}
    if final.get("params_only", {}).get("path"):
        continue
    milestones = job.get("milestones") or {}
    if not milestones:
        print(f"{job['job_id']}: no delivered weights")
        continue
    step = sorted(milestones, key=lambda s: int(s))[-1]
    info = milestones[step]
    job["final_checkpoint"] = {"step": int(step), "params_only": info}
    path.write_text(json.dumps(job, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{job['job_id']}: delivered weights = step {step} ({info['path']})")
PYEOF

# The delivered weights of every source model are scored on their own
# benchmark: the periodic backtests measured the rolling checkpoints, and the
# delivered tree is the final (or the last milestone) one.
"$PY" -u - <<'PYEOF' 2>&1 | tee -a "$LOG"
import json, pathlib, subprocess
root = pathlib.Path("/data/szgx/gaohang/pi05_30")
PY = "/data/szgx/xworld-gzh/third_party/external/openpi/.venv/bin/python"
for path in sorted((root / "state" / "jobs").glob("stage3_source_*.json")):
    job = json.loads(path.read_text())
    if job.get("status") == "running":
        continue
    final = job.get("final_checkpoint") or {}
    step = final.get("step")
    ckpt = (final.get("params_only") or {}).get("path")
    if not step or not ckpt:
        print(f"{job['job_id']}: no delivered weights to score")
        continue
    if any(entry.get("step") == step for entry in job.get("history") or []):
        print(f"{job['job_id']}: step {step} is already scored")
        continue
    out = root / "eval" / "backtest" / job["job_id"] / str(step)
    print(f"{job['job_id']}: scoring the delivered weights (step {step})", flush=True)
    result = subprocess.run([PY, "-u", str(root / "campaign" / "backtest.py"),
                             "--job-id", job["job_id"], "--step", str(step),
                             "--checkpoint", ckpt, "--out", str(out),
                             "--policy-gpus", "0,2", "--sim-gpus", "1,3"],
                            capture_output=True, text=True)
    payload = out / "backtest.json"
    if payload.is_file():
        subprocess.run([PY, str(root / "campaign" / "jobctl.py"), "record",
                        job["job_id"], str(step), str(payload)], check=False)
        print(f"{job['job_id']}: delivered weights scored", flush=True)
    else:
        print(f"{job['job_id']}: scoring failed rc={result.returncode}: {result.stderr[-300:]}", flush=True)
PYEOF

# The adaptation jobs, in plan order, that are not finished yet.
ADAPT_JOBS=$("$PY" - <<'PYEOF'
import json, pathlib
root = pathlib.Path("/data/szgx/gaohang/pi05_30/state/jobs")
terminal = ("completed", "early_stopped", "failed", "skipped")
rows = []
for path in root.glob("*.json"):
    job = json.loads(path.read_text())
    if job.get("kind") != "adapt":
        continue
    if job.get("status") in terminal:
        continue
    rows.append((job.get("t", 0), job.get("family", ""), job["job_id"]))
rows.sort()
print(" ".join(job_id for _, _, job_id in rows))
PYEOF
)
say "adaptation jobs to run: $(echo "$ADAPT_JOBS" | wc -w)"

INDEX=0
QUEUE=($ADAPT_JOBS)
while [[ ${#QUEUE[@]} -gt 0 ]]; do
  JOB_A="${QUEUE[0]}"
  JOB_B=""
  if [[ ${#QUEUE[@]} -gt 1 ]]; then
    JOB_B="${QUEUE[1]}"
  fi
  # The two jobs of a pair share the eight cards; the groups alternate so
  # that no card is used twice.
  if (( INDEX % 2 == 0 )); then
    TRAIN_A=$GROUP_A_TRAIN; POLICY_A=$GROUP_A_POLICY; SIM_A=$GROUP_A_SIM
    TRAIN_B=$GROUP_B_TRAIN; POLICY_B=$GROUP_B_POLICY; SIM_B=$GROUP_B_SIM
  else
    TRAIN_A=$GROUP_B_TRAIN; POLICY_A=$GROUP_B_POLICY; SIM_A=$GROUP_B_SIM
    TRAIN_B=$GROUP_A_TRAIN; POLICY_B=$GROUP_A_POLICY; SIM_B=$GROUP_A_SIM
  fi

  $PY "$CAMPAIGN/jobctl.py" set "$JOB_A" \
    "status=pending" "peak_lr=2.5e-05" "action_horizon=10" "max_steps=2001" \
    "milestone_steps=[]" "save_interval=500" "final_backtest_step=2000" \
    "backtest_interval=500" \
    "train_gpus=$TRAIN_A" "fsdp_devices=4" "policy_gpus=$POLICY_A" "sim_gpus=$SIM_A" \
    "mem_fraction=$MEM_FRACTION" >> "$LOG" 2>&1
  if [[ -n "$JOB_B" ]]; then
    $PY "$CAMPAIGN/jobctl.py" set "$JOB_B" \
      "status=pending" "peak_lr=2.5e-05" "action_horizon=10" "max_steps=2001" \
      "milestone_steps=[]" "save_interval=500" "final_backtest_step=2000" \
      "backtest_interval=500" \
      "train_gpus=$TRAIN_B" "fsdp_devices=4" "policy_gpus=$POLICY_B" "sim_gpus=$SIM_B" \
      "mem_fraction=$MEM_FRACTION" >> "$LOG" 2>&1
  fi
  say "pair $((INDEX / 2 + 1)): $JOB_A (${TRAIN_A}) ${JOB_B:+and $JOB_B (${TRAIN_B})}"
  wait_for_free_cards

  if [[ -n "$JOB_B" ]]; then
    PI05_COTRAIN_NOTIFY=0 bash "$CAMPAIGN/cotrain.sh" "$JOB_A" "$JOB_B" >> "$LOG" 2>&1
    QUEUE=("${QUEUE[@]:2}")
  else
    PI05_COTRAIN_NOTIFY=0 bash "$CAMPAIGN/cotrain.sh" "$JOB_A" >> "$LOG" 2>&1
    QUEUE=("${QUEUE[@]:1}")
  fi
  INDEX=$((INDEX + 2))
done

say "all adaptation jobs are terminal -> writing the round deliverables"
"$PY" -u "$CAMPAIGN/manifest.py" >> "$LOG" 2>&1
"$PY" -u "$CAMPAIGN/deliverables.py" >> "$LOG" 2>&1
"$PY" -u "$CAMPAIGN/write_docs.py" >> "$LOG" 2>&1
"$PY" -u "$CAMPAIGN/manifest.py" --notify >> "$LOG" 2>&1
say "matrix driver finished"
