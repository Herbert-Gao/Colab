#!/usr/bin/env bash
# After the 2,000-episode test: refill the episodes that were lost to the
# websocket keepalive, draw the charts, write the generalization report and
# render it as PDF.
set -uo pipefail

ROOT=${PI05_30_ROOT:-/data/szgx/gaohang/pi05_30}
CAMPAIGN="$ROOT/campaign"
PY=${PI05_PYTHON:-/data/szgx/xworld-gzh/third_party/external/openpi/.venv/bin/python}
REPORT_PY="$ROOT/envs/report-tools/bin/python"
LOG="$ROOT/logs/eval_report.log"

while true; do
  LEFT=$(pgrep -fc "campaign/eval_sources.py" 2>/dev/null | head -1)
  [[ -z "$LEFT" || "$LEFT" == "0" ]] && break
  sleep 120
done
sleep 30
echo "[$(date -Is)] evaluation finished -> refilling the lost episodes" >> "$LOG"
"$PY" -u "$CAMPAIGN/refill_missing_eval.py" >> "$LOG" 2>&1
echo "[$(date -Is)] refill done -> drawing the charts" >> "$LOG"
"$PY" -u "$CAMPAIGN/eval_charts.py" >> "$LOG" 2>&1
echo "[$(date -Is)] charts done -> writing the report" >> "$LOG"
"$PY" -u "$CAMPAIGN/eval_report.py" >> "$LOG" 2>&1
if [[ -x "$REPORT_PY" ]]; then
  "$REPORT_PY" "$CAMPAIGN/md2pdf.py" "$ROOT/docs/eval_report.md" >> "$LOG" 2>&1
fi
echo "[$(date -Is)] report and PDF written" >> "$LOG"
