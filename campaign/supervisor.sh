#!/usr/bin/env bash
# Supervisor of the supervisor: keeps the watchdog alive.
#
# The watchdog restarts the training driver when it dies; this script restarts
# the watchdog when it dies.  Together they make the round unattended: nobody
# has to look at the machine for the training to continue.
set -uo pipefail

ROOT=${PI05_30_ROOT:-/data/szgx/gaohang/pi05_30}
CAMPAIGN="$ROOT/campaign"
CYCLE=${PI05_SUPERVISOR_CYCLE:-120}
LOG="$ROOT/logs/supervisor.log"
mkdir -p "$ROOT/logs"

while true; do
  sleep "$CYCLE"
  if ! pgrep -f "campaign/watchdog.sh" > /dev/null; then
    echo "[$(date -Is)] supervisor: watchdog is gone -> restarting it" >> "$LOG"
    setsid nohup bash "$CAMPAIGN/watchdog.sh" >> "$ROOT/logs/watchdog_stdout.log" 2>&1 < /dev/null &
  fi
  if ! pgrep -f "campaign/cotrain.sh" > /dev/null && ! pgrep -f "campaign/train_job.py" > /dev/null; then
    # No driver and no trainer: the round is over or the driver died between
    # jobs.  The watchdog restarts the driver; nothing to do here.
    echo "[$(date -Is)] supervisor: no driver and no trainer (round finished or driver down)" >> "$LOG"
  fi
done
