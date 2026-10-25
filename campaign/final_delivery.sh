#!/usr/bin/env bash
# Final delivery of the round: runs when the fine-tuning matrix is done.
#
#   1. fill the single episode that the first evaluation round is still short
#      (one simulator plus a policy server, the machine is free by then),
#   2. redraw the charts and rewrite the report and its PDF,
#   3. write the model manifest (30 fine-tuned models + the source models) with
#      a path check on every delivered checkpoint,
#   4. write the progress summary and the deliverable table,
#   5. send the "all done" notice through lark-im and record the receipt.
set -uo pipefail

ROOT=${PI05_30_ROOT:-/data/szgx/gaohang/pi05_30}
CAMPAIGN="$ROOT/campaign"
PY=${PI05_PYTHON:-/data/szgx/xworld-gzh/third_party/external/openpi/.venv/bin/python}
REPORT_PY="$ROOT/envs/report-tools/bin/python"
LOG="$ROOT/logs/final_delivery.log"
say() { echo "[$(date -Is)] $*" | tee -a "$LOG"; }

matrix_running() {
  pgrep -fc "campaign/cotrain_matrix.sh" 2>/dev/null | head -1
}

say "waiting for the fine-tuning matrix to finish"
while true; do
  LEFT=$(matrix_running)
  [[ -z "$LEFT" || "$LEFT" == "0" ]] && break
  sleep 120
done
say "the matrix is done -> final delivery"

say "filling the episodes the first evaluation round is short"
"$PY" -u "$CAMPAIGN/refill_missing_eval.py" >> "$LOG" 2>&1

say "redrawing the charts and rewriting the report"
"$PY" -u "$CAMPAIGN/eval_charts.py" >> "$LOG" 2>&1
"$PY" -u "$CAMPAIGN/eval_report.py" >> "$LOG" 2>&1
if [[ -x "$REPORT_PY" ]]; then
  "$REPORT_PY" "$CAMPAIGN/md2pdf.py" "$ROOT/docs/eval_report.md" >> "$LOG" 2>&1
fi

say "writing the model manifest, the progress summary and the deliverable table"
"$PY" -u "$CAMPAIGN/manifest.py" >> "$LOG" 2>&1
"$PY" -u "$CAMPAIGN/deliverables.py" >> "$LOG" 2>&1
"$PY" -u "$CAMPAIGN/write_docs.py" >> "$LOG" 2>&1

say "auditing the delivery against the run book"
"$PY" -u "$CAMPAIGN/verify_delivery.py" >> "$LOG" 2>&1

say "sending the completion notice"
"$PY" -u - <<'PYEOF' >> "$LOG" 2>&1
import json, pathlib, sys
sys.path.insert(0, "/data/szgx/gaohang/pi05_30/campaign")
import notify_channel
root = pathlib.Path("/data/szgx/gaohang/pi05_30/state/jobs")
adapt = done = 0
for path in root.glob("stage3_adapt_*.json"):
    job = json.loads(path.read_text())
    adapt += 1
    if job.get("status") in ("completed", "early_stopped"):
        done += 1
message = (f"服务器A/A800×8｜阶段3：全部完成。"
           f"微调模型 {done}/{adapt} 个（每作业 ≤2000 步，每 500 步回测打分），"
           f"源模型 3 个，清单见 docs/models_manifest.md。")
record = notify_channel.send(message)
pathlib.Path("/data/szgx/gaohang/pi05_30/state/final_notify.json").write_text(
    json.dumps({"message": message, "record": record}, ensure_ascii=False, indent=2))
print("notify status:", record.get("status"))
PYEOF

say "final delivery done"
