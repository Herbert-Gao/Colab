#!/usr/bin/env bash
# Final chain of the round:
#
#   1. refill the episodes that were lost to the websocket keepalive - the
#      cells run in parallel, one policy server each, the simulators on the
#      remaining cards (eight cards busy at once);
#   2. draw the charts, write the report, render the PDF;
#   3. train the third family with the longer budget on all eight cards.
set -uo pipefail

ROOT=${PI05_30_ROOT:-/data/szgx/gaohang/pi05_30}
CAMPAIGN="$ROOT/campaign"
PY=${PI05_PYTHON:-/data/szgx/xworld-gzh/third_party/external/openpi/.venv/bin/python}
REPORT_PY="$ROOT/envs/report-tools/bin/python"
LOG="$ROOT/logs/eval_report.log"
JOB=stage3_source_fam3_r1_long

say() { echo "[$(date -Is)] $*" | tee -a "$LOG"; }

say "refilling the lost episodes (parallel over the cells)"
echo -n "" > "$ROOT/state/phase.txt"
printf 'evaluation' > "$ROOT/state/phase.txt"
"$PY" -u "$CAMPAIGN/refill_missing_eval.py" >> "$LOG" 2>&1

say "drawing the charts"
"$PY" -u "$CAMPAIGN/eval_charts.py" >> "$LOG" 2>&1
say "writing the report"
"$PY" -u "$CAMPAIGN/eval_report.py" >> "$LOG" 2>&1
if [[ -x "$REPORT_PY" ]]; then
  "$REPORT_PY" "$CAMPAIGN/md2pdf.py" "$ROOT/docs/eval_report.md" >> "$LOG" 2>&1
fi
say "report and PDF written"

say "starting $JOB (the longer budget for the third family, eight cards)"
bash "$CAMPAIGN/run_job.sh" "$JOB" >> "$LOG" 2>&1
say "$JOB finished (status=$($PY "$CAMPAIGN/jobctl.py" field "$JOB" status))"

# The longer run supersedes the 15,000-step weights of the third family.
"$PY" - <<'PYEOF' >> "$LOG" 2>&1
import json, pathlib
root = pathlib.Path("/data/szgx/gaohang/pi05_30/state/jobs")
long_job = json.loads((root / "stage3_source_fam3_r1_long.json").read_text())
delivered = ((long_job.get("final_checkpoint") or {}).get("params_only") or {}).get("path")
if delivered:
    base = root / "stage3_source_fam3_r1.json"
    job = json.loads(base.read_text())
    job["superseded_by"] = "stage3_source_fam3_r1_long"
    job["delivered_weights_note"] = (
        "15,000 步的权重已交付；族③ 的最终交付权重改为 stage3_source_fam3_r1_long "
        "(同族续训 15,000 步，共 30,000 步)")
    base.write_text(json.dumps(job, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"stage3_source_fam3_r1: superseded by {delivered}")
PYEOF

"$PY" -u "$CAMPAIGN/manifest.py" >> "$LOG" 2>&1
"$PY" -u "$CAMPAIGN/write_docs.py" >> "$LOG" 2>&1

say "scoring the third family on the ten target tasks (all eight cards)"
# A last refill before the evaluation: one cell of the first round is still a
# single episode short.
"$PY" -u "$CAMPAIGN/refill_missing_eval.py" >> "$LOG" 2>&1
PI05_FINAL_SIMS=6 "$PY" -u "$CAMPAIGN/eval_sources.py" --models stage3_source_fam3_r1_long \
    >> "$LOG" 2>&1
say "drawing the charts and rewriting the report with the third family"
"$PY" -u "$CAMPAIGN/eval_charts.py" >> "$LOG" 2>&1
"$PY" -u "$CAMPAIGN/eval_report.py" >> "$LOG" 2>&1
if [[ -x "$REPORT_PY" ]]; then
  "$REPORT_PY" "$CAMPAIGN/md2pdf.py" "$ROOT/docs/eval_report.md" >> "$LOG" 2>&1
fi
say "the third family is scored and the report is final"

# The fine-tuning matrix (30 jobs, 8,000-step cap) starts now: the evaluation
# has the priority, the matrix takes the machine from here.
printf 'matrix' > "$ROOT/state/phase.txt"
say "starting the fine-tuning matrix (30 jobs, 8,000 steps each, two at a time)"
setsid nohup bash "$CAMPAIGN/cotrain_matrix.sh" >> "$ROOT/logs/driver_stdout.log" 2>&1 < /dev/null &
say "the fine-tuning matrix driver is up"
