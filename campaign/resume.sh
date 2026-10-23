#!/usr/bin/env bash
# Resume the campaign after a pause (e.g. while GPU7 is being reset).
#
#   bash campaign/resume.sh                 # 4-GPU layout, resumes the running job
#   PI05_TRAIN_GPUS=0,1,2,3,4,5,6,7 bash campaign/resume.sh   # back to 8 GPUs
#
# With 8 GPUs the step-1500 checkpoint (saved with a 4-device FSDP layout) can
# no longer be restored, so the current job restarts from the base weights.
set -uo pipefail

ROOT=${PI05_30_ROOT:-/data/szgx/gaohang/pi05_30}
CAMPAIGN="$ROOT/campaign"
PY=${PI05_PYTHON:-/data/szgx/xworld-gzh/third_party/external/openpi/.venv/bin/python}
LOG="$ROOT/logs/campaign_driver.log"

export PI05_TRAIN_GPUS=${PI05_TRAIN_GPUS:-0,1,2,3,4,5,6,7}
export PI05_FSDP_DEVICES=${PI05_FSDP_DEVICES:-8}
export PI05_SIM_GPU=${PI05_SIM_GPU:-1}
export PI05_POLICY_GPUS=${PI05_POLICY_GPUS:-0,2,4,6}

# A resume must never touch checkpoints or job history: the layout switch
# (4 -> 8 devices) that invalidated the old checkpoints is a one-off action and
# lives in campaign/switch_layout.sh, never in the restart path.
setsid nohup bash "$CAMPAIGN/run_stage.sh" 1 2 3 >> "$LOG" 2>&1 < /dev/null &
disown
sleep 2
setsid nohup bash "$CAMPAIGN/watchdog.sh" >> "$ROOT/logs/watchdog_stdout.log" 2>&1 < /dev/null &
disown
sleep 5
echo "resumed: train_gpus=$PI05_TRAIN_GPUS fsdp=$PI05_FSDP_DEVICES sim=$PI05_SIM_GPU policy=$PI05_POLICY_GPUS"
