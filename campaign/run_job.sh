#!/usr/bin/env bash
# Run one campaign job end to end: train -> backtest every 2000 steps -> keep
# the section 4.1 checkpoint set -> write the job document.
#
#   run_job.sh <job_id>
#
# The job record (state/jobs/<job_id>.json) holds every parameter; this script
# only sequences the steps so that progress is visible in the job log.
#
# The GPU layout of a job comes from the record as well: ``train_gpus`` (the
# cards the trainer uses), ``fsdp_devices`` (how many of them take part in the
# FSDP mesh), ``policy_gpus`` (the policy servers of the backtest) and
# ``sim_gpus`` (the simulators).  Two jobs can therefore run side by side, each
# on its own four cards.
set -uo pipefail

JOB_ID=${1:?usage: run_job.sh <job_id>}
ROOT=${PI05_30_ROOT:-/data/szgx/gaohang/pi05_30}
CAMPAIGN="$ROOT/campaign"
PY=${PI05_PYTHON:-/data/szgx/xworld-gzh/third_party/external/openpi/.venv/bin/python}
CTL="$PY $CAMPAIGN/jobctl.py"
LOG_DIR="$ROOT/logs"
JOB_LOG="$LOG_DIR/$JOB_ID.log"
mkdir -p "$LOG_DIR"

field() { $CTL field "$JOB_ID" "$1" 2>/dev/null; }
say()  { echo "[$(date -Is)] $*" | tee -a "$JOB_LOG"; }

# One runner per job: a second queue must not pick the same job up again.
mkdir -p "$ROOT/state/locks"
exec 8>"$ROOT/state/locks/$JOB_ID.lock"
if ! flock -n 8; then
  echo "[$(date -Is)] job $JOB_ID is already running elsewhere; skipping" | tee -a "$JOB_LOG"
  exit 0
fi

REPO_ID=$(field repo_id)
EXP_NAME=$(field exp_name)
CKPT_BASE=$(field checkpoint_base_dir)
INIT_PARAMS=$(field init_params)
LR=$(field peak_lr)
HORIZON=$(field action_horizon)
MAX_STEPS=$(field max_steps)
SEED=$(field seed)
MILESTONES=$(field milestone_steps)
BACKTEST_TASKS=$(field backtest_tasks)
BACKTEST_SEEDS=$(field backtest_seeds)
NUM_WORKERS=${PI05_NUM_WORKERS:-4}
SAVE_INTERVAL=$(field save_interval)
BACKTEST_INTERVAL=$(field backtest_interval)
[[ -z "$BACKTEST_INTERVAL" || "$BACKTEST_INTERVAL" == "None" ]] && BACKTEST_INTERVAL=${PI05_BACKTEST_INTERVAL:-2000}
FINAL_STEP=$(field final_backtest_step)

# --- GPU layout of this job ------------------------------------------------
TRAIN_GPUS=$(field train_gpus)
[[ -z "$TRAIN_GPUS" || "$TRAIN_GPUS" == "None" ]] && TRAIN_GPUS=${PI05_TRAIN_GPUS:-0,1,2,3,4,5,6,7}
FSDP_DEVICES=$(field fsdp_devices)
[[ -z "$FSDP_DEVICES" || "$FSDP_DEVICES" == "None" ]] && FSDP_DEVICES=${PI05_FSDP_DEVICES:-8}
POLICY_GPUS=$(field policy_gpus)
[[ -z "$POLICY_GPUS" || "$POLICY_GPUS" == "None" ]] && POLICY_GPUS=${PI05_POLICY_GPUS:-0,2,4,6}
SIM_GPUS=$(field sim_gpus)
[[ -z "$SIM_GPUS" || "$SIM_GPUS" == "None" ]] && SIM_GPUS=${PI05_SIM_GPUS:-1,3,5,7}
MEM_FRACTION=$(field mem_fraction)
[[ -z "$MEM_FRACTION" || "$MEM_FRACTION" == "None" ]] && MEM_FRACTION=${PI05_TRAIN_MEM_FRACTION:-0.75}
TRAIN_GPU0=${TRAIN_GPUS%%,*}
say "gpu layout: train=$TRAIN_GPUS fsdp=$FSDP_DEVICES policy=$POLICY_GPUS sim=$SIM_GPUS"

# An adaptation job starts from the source model's delivered weights.
if [[ -z "$INIT_PARAMS" || "$INIT_PARAMS" == "None" ]]; then
  SOURCE_JOB=$(field init_from_job)
  SNAPSHOT=$($CTL field "$SOURCE_JOB" final_checkpoint.params_only.path)
  # CheckpointWeightLoader expects the params tree root, i.e. <snapshot>/params.
  INIT_PARAMS="$SNAPSHOT/params"
  if [[ ! -d "$INIT_PARAMS" ]]; then
    say "ERROR: source $SOURCE_JOB has no usable weights ($INIT_PARAMS)"
    exit 3
  fi
  say "init weights from $SOURCE_JOB: $INIT_PARAMS"
fi

ATTEMPTS_RAW=$(field attempts)
ATTEMPTS=0
[[ "$ATTEMPTS_RAW" =~ ^[0-9]+$ ]] && ATTEMPTS=$ATTEMPTS_RAW
ATTEMPTS=$((ATTEMPTS + 1))
say "=== job $JOB_ID start (attempt $ATTEMPTS): repo=$REPO_ID lr=$LR horizon=$HORIZON steps=$MAX_STEPS seed=$SEED ==="
$CTL set "$JOB_ID" "status=running" "attempts=$ATTEMPTS" "started=$(date -Is)" >> "$JOB_LOG" 2>&1

TRAIN_ARGS=(
  --job-id "$JOB_ID" --repo-id "$REPO_ID" --exp-name "$EXP_NAME"
  --checkpoint-base-dir "$CKPT_BASE" --peak-lr "$LR" --action-horizon "$HORIZON"
  --max-steps "$MAX_STEPS" --seed "$SEED" --num-workers "$NUM_WORKERS"
  --save-interval "$SAVE_INTERVAL" --fsdp-devices "$FSDP_DEVICES"
)
if [[ -n "$INIT_PARAMS" && "$INIT_PARAMS" != "None" ]]; then
  TRAIN_ARGS+=(--init-params "$INIT_PARAMS")
fi
CONFIG_NAME=pi05_aloha_robotwin_30
CKPT_ROOT="$CKPT_BASE/$CONFIG_NAME/$EXP_NAME"
if [[ -d "$CKPT_ROOT" ]] && compgen -G "$CKPT_ROOT/[0-9]*" > /dev/null; then
  TRAIN_ARGS+=(--resume)
  START_STEP=$(( $(ls -1 "$CKPT_ROOT" | grep -E '^[0-9]+$' | sort -n | tail -1) + 1 ))
  TRAIN_ARGS+=(--start-step "$START_STEP")
  say "resuming from step $START_STEP"
fi

export CUDA_VISIBLE_DEVICES="$TRAIN_GPUS"
export HF_LEROBOT_HOME="$ROOT/datasets/lerobot"
export JAX_PLATFORMS=cuda
# The memory fraction leaves room on every card for the policy server (~9 GiB)
# and the simulator (~11 GiB), which run on the same GPUs while the trainer is
# stopped.
export XLA_PYTHON_CLIENT_MEM_FRACTION="$MEM_FRACTION"
export NCCL_IB_DISABLE=1
export PYTHONUNBUFFERED=1
export TRAIN_GPU0="$TRAIN_GPU0"
export TRAIN_GPUS="$TRAIN_GPUS"

# Wait until the training GPUs are actually free: a leftover CUDA context from
# a previous policy server makes the trainer see fewer devices and die.  If the
# cards stay busy for an hour the job gives up and stays pending instead of
# starting on top of another workload.
GPUS_READY=0
# The machine can carry another workload for hours; a job waits for the
# cards instead of giving up (48 h by default).
GPU_WAIT_ITER=${PI05_GPU_WAIT_ITER:-8640}
for _ in $(seq 1 $GPU_WAIT_ITER); do
  BUSY=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits \
         -i "$TRAIN_GPUS" 2>/dev/null | awk -F', ' '{s+=$1} END {print s+0}')
  if [[ -n "$BUSY" && "$BUSY" -lt 2000 ]]; then GPUS_READY=1; break; fi
  say "waiting for the GPUs to be released (busy=${BUSY} MiB)"
  sleep 20
done
if [[ "$GPUS_READY" != "1" ]]; then
  say "ERROR: the GPUs are still busy after the wait window - the job stays pending"
  exit 4
fi

"$PY" -u "$CAMPAIGN/train_job.py" "${TRAIN_ARGS[@]}" >> "$JOB_LOG" 2>&1 &
TRAIN_PID=$!
say "trainer pid=$TRAIN_PID"

# If this script dies while the trainer is stopped, the trainer must be resumed
# or it would stay SIGSTOPped forever and block the machine.
cleanup_trainer() {
  if kill -0 "$TRAIN_PID" 2>/dev/null; then
    kill -CONT "$TRAIN_PID" 2>/dev/null
  fi
}
trap cleanup_trainer EXIT

STOP_REQUESTED=0
TICK=0

# Backtest every finished checkpoint (section 5).  Runs both while the trainer
# is alive and once more after it exits, so a job that is resumed after its
# training already finished still gets its checkpoint scored.
process_checkpoints() {
  for STEP in $($CTL new-checkpoints "$JOB_ID"); do
    CKPT="$CKPT_ROOT/$STEP"
    if [[ ! -f "$CKPT/_CHECKPOINT_METADATA" ]]; then continue; fi
    # Section 4.1: a milestone checkpoint (7500 / 15000 / 30000, and the final
    # step of an early-stopped job) is delivered as a weights-only copy.  It is
    # captured as soon as the checkpoint is complete, independently of the
    # backtest cadence.
    for M in $MILESTONES; do
      if [[ "$M" == "$STEP" ]]; then
        $CTL snapshot "$JOB_ID" "$STEP" milestone >> "$JOB_LOG" 2>&1 && say "milestone snapshot $STEP"
      fi
    done
    # Section 5: the periodic backtest runs every 2000 steps (the cadence the
    # early-stop loss window of section 6 is defined on).  Checkpoints saved in
    # between are recorded as processed without being scored.  The delivered
    # final checkpoint is scored as well, even when it is not on the cadence.
    if (( STEP % BACKTEST_INTERVAL != 0 )) && [[ "$STEP" != "$FINAL_STEP" ]]; then
      $CTL mark-processed "$JOB_ID" "$STEP" >> "$JOB_LOG" 2>&1
      continue
    fi
    # The policy servers must not grab a GPU while the trainer is still
    # initialising its memory pool, otherwise the trainer sees fewer devices
    # and dies with "Batch size 32 must be divisible by the number of devices".
    # Once the trainer is gone its memory pool is released and the evaluation
    # may use the cards right away - that is the case for the final checkpoint,
    # which is scored after the trainer exited.
    TRAINER_READY=0
    if ! kill -0 "$TRAIN_PID" 2>/dev/null; then
      TRAINER_READY=1
    else
      for _ in $(seq 1 20); do
        USED=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -i "$TRAIN_GPU0" 2>/dev/null | head -1)
        if [[ -n "$USED" && "$USED" -gt 40000 ]]; then TRAINER_READY=1; break; fi
        sleep 30
      done
    fi
    if [[ "$TRAINER_READY" != "1" ]]; then
      say "trainer has not reserved its GPU memory yet; skipping backtest for $STEP (will retry)"
      continue
    fi
    say "checkpoint $STEP ready -> pause trainer, backtest (tasks: $BACKTEST_TASKS), then resume"
    OUT="$ROOT/eval/backtest/$JOB_ID/$STEP"
    # The backtest is exclusive with the training.  Measured: with the trainer
    # running, the policy inference latency grows by an order of magnitude
    # (a failed episode needs all 400 steps), which turned a 13 minute
    # evaluation into 18.5 minutes and made its cost unpredictable.  Stopping
    # the trainer keeps the evaluation fast and its timing bounded.
    kill -STOP "$TRAIN_PID" 2>/dev/null
    if "$PY" -u "$CAMPAIGN/backtest.py" --job-id "$JOB_ID" --step "$STEP" \
        --checkpoint "$CKPT" --out "$OUT" --policy-gpus "$POLICY_GPUS" --sim-gpus "$SIM_GPUS" >> "$JOB_LOG" 2>&1; then
      VERDICT=$($CTL record "$JOB_ID" "$STEP" "$OUT/backtest.json" | tail -1)
      say "backtest $STEP recorded (early-stop: $VERDICT)"
      $CTL cleanup "$JOB_ID" --keep-backtested 2 --reason "回测完成，仅保留最近 2 个已回测恢复点与最新恢复点" >> "$JOB_LOG"
      if [[ "$VERDICT" == "stop" ]]; then
        say "early stop at $STEP -> terminate trainer"
        kill -CONT "$TRAIN_PID" 2>/dev/null
        kill -TERM "$TRAIN_PID" 2>/dev/null
        STOP_REQUESTED=1
        sleep 60
        kill -KILL "$TRAIN_PID" 2>/dev/null
        return
      fi
    else
      say "backtest $STEP FAILED (see $JOB_LOG)"
    fi
    say "backtest $STEP done -> resume training"
    kill -CONT "$TRAIN_PID" 2>/dev/null
  done
}

# Section 4.1 rule 4: before every save the volume must still hold three
# checkpoints.  The trainer saves on its own schedule, so the free space is
# checked every cycle; when it drops below the threshold the trainer is
# stopped (no further checkpoint can be written) and the user is notified.
# Retained checkpoints are never deleted to make room.
CHECKPOINT_BYTES=${PI05_CHECKPOINT_BYTES:-$((42 * 1024 * 1024 * 1024))}
DISK_TRIP=0
disk_guard() {
  [[ "$DISK_TRIP" == "1" ]] && return 0
  local avail
  avail=$(df -B1 --output=avail "$(dirname "$CKPT_BASE")" 2>/dev/null | tail -1 | tr -d ' ')
  [[ -z "$avail" ]] && return 0
  if [[ "$avail" -lt $((CHECKPOINT_BYTES * 3)) ]]; then
    DISK_TRIP=1
    say "disk free ${avail}B < 3x checkpoint (${CHECKPOINT_BYTES}B) -> pause job, no checkpoint is deleted"
    $CTL set "$JOB_ID" "status=paused" "pause_reason=磁盘空间不足" "paused_at=$(date -Is)" >> "$JOB_LOG" 2>&1
    kill -STOP "$TRAIN_PID" 2>/dev/null
    "$PY" -u -c "
import sys; sys.path.insert(0, '$CAMPAIGN')
import notify_channel
record = notify_channel.send('服务器A/A800×8｜阶段3：磁盘空间不足，作业已暂停；需清理空间后恢复（不删除保留类检查点）。')
print('notify status:', record.get('status'))
" >> "$JOB_LOG" 2>&1
  fi
}

while kill -0 "$TRAIN_PID" 2>/dev/null; do
  sleep 60
  disk_guard
  process_checkpoints
  # keep the progress document current
  LAST_LOGGED_STEP=$(grep -oE "Step [0-9]+:" "$JOB_LOG" | tail -1 | tr -dc '0-9')
  if [[ -n "$LAST_LOGGED_STEP" ]]; then
    $CTL set "$JOB_ID" "current_step=$LAST_LOGGED_STEP" >> "$JOB_LOG" 2>&1
  fi
  TICK=$((TICK + 1))
  if [[ $((TICK % 5)) -eq 0 ]]; then
    "$PY" -u "$CAMPAIGN/write_docs.py" --job-id "$JOB_ID" >> "$JOB_LOG" 2>&1
  fi
  if [[ "$STOP_REQUESTED" == "1" ]]; then break; fi
done
wait "$TRAIN_PID" 2>/dev/null
TRAIN_RC=$?
# the trainer may have exited right after writing its last checkpoint
process_checkpoints

ALL_STEPS=$(ls -1 "$CKPT_ROOT" 2>/dev/null | grep -E '^[0-9]+$' | sort -n | tail -1)
if [[ -z "$ALL_STEPS" ]]; then
  ALL_STEPS=$($CTL new-checkpoints "$JOB_ID" | tr ' ' '\n' | tail -1)
fi

if [[ "$STOP_REQUESTED" == "1" ]]; then
  $CTL snapshot "$JOB_ID" "$ALL_STEPS" final >> "$JOB_LOG" 2>&1
  $CTL set "$JOB_ID" "status=early_stopped" "early_stop={\"step\": $ALL_STEPS}" "finished=$(date -Is)" >> "$JOB_LOG"
  say "job $JOB_ID early stopped at $ALL_STEPS"
else
  if [[ "$TRAIN_RC" == "0" && -n "$ALL_STEPS" ]]; then
    $CTL snapshot "$JOB_ID" "$ALL_STEPS" final >> "$JOB_LOG" 2>&1
    $CTL set "$JOB_ID" "status=completed" "finished=$(date -Is)" >> "$JOB_LOG"
    say "job $JOB_ID completed at $ALL_STEPS (train rc=$TRAIN_RC)"
  else
    # The run book allows two retries from the last recovery point; after the
    # third attempt the job is failed for good and the other jobs keep going.
    if [[ "$ATTEMPTS" -ge 3 ]]; then
      $CTL set "$JOB_ID" "status=failed" "train_rc=$TRAIN_RC" "finished=$(date -Is)" >> "$JOB_LOG"
    else
      $CTL set "$JOB_ID" "status=failed_retry" "train_rc=$TRAIN_RC" "finished=$(date -Is)" >> "$JOB_LOG"
    fi
    say "job $JOB_ID FAILED (train rc=$TRAIN_RC, attempt $ATTEMPTS); last recovery point kept"
    "$PY" -u "$CAMPAIGN/failures.py" record "$JOB_ID" "$ATTEMPTS" "train_rc=$TRAIN_RC" >> "$JOB_LOG" 2>&1
    "$PY" -u -c "
import sys; sys.path.insert(0, '$CAMPAIGN')
import notify_channel
record = notify_channel.send('服务器A/A800×8｜阶段3：作业 ${JOB_ID} 失败（训练退出码 $TRAIN_RC，第 $ATTEMPTS 次尝试）；已暂停；需协助。')
print('notify status:', record.get('status'))
" >> "$JOB_LOG" 2>&1
    # Section 4.1: a failed or paused job keeps its last valid recovery point.
    $CTL cleanup "$JOB_ID" --keep 1 --reason "作业失败/暂停，保留最后有效恢复点" >> "$JOB_LOG" 2>&1
  fi
fi

# The delivered weights are weights-only; the full checkpoints are no longer
# needed once the job is finished.  Failed and paused jobs keep their last
# recovery point (section 4.1).
JOB_STATUS=$(field status)
if [[ "$JOB_STATUS" != "failed" && "$JOB_STATUS" != "failed_retry" && "$JOB_STATUS" != "paused" ]]; then
  $CTL cleanup "$JOB_ID" --keep 0 --reason "作业结束，最终权重已另存为 params-only" >> "$JOB_LOG"
fi
"$PY" -u "$CAMPAIGN/write_docs.py" --job-id "$JOB_ID" >> "$JOB_LOG" 2>&1
say "=== job $JOB_ID end ==="
