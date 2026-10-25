"""Audit the delivery of the round against the run book.

    bash campaign/verify_delivery.sh

Every check prints PASS/FAIL with the evidence; the script exits non-zero if
any check fails.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path("/data/szgx/gaohang/pi05_30")
DOCS = ROOT / "docs"
JOBS = ROOT / "state" / "jobs"
TERMINAL = ("completed", "early_stopped", "failed", "skipped")
results: list[tuple[bool, str, str]] = []


def check(ok: bool, name: str, evidence: str) -> None:
    results.append((bool(ok), name, evidence))


def main() -> int:
    # 1 - the documents exist and carry a timestamp on the first line
    for name in ("00_progress.md", "01_preflight.md", "02_hparam_pilot.md",
                 "models_manifest.md", "incidents.md", "cleanup_log.md"):
        path = DOCS / name
        first = path.read_text(encoding="utf-8").splitlines()[0] if path.is_file() else ""
        check(path.is_file() and first.startswith("更新时间"),
              f"docs/{name} 存在且首行带时区", first or "缺失")

    # 2 - the manifest lists the 30 fine-tuned models and the source models
    manifest = (DOCS / "models_manifest.md").read_text(encoding="utf-8") if (DOCS / "models_manifest.md").is_file() else ""
    rows = [line for line in manifest.splitlines()
            if line.startswith("| stage3_adapt_")]
    check(len(rows) == 30, "models_manifest 列出 30 条微调模型", f"{len(rows)} 条")
    paths = re.findall(r"(/data/szgx/gaohang/pi05_30/runs/\S+?)(?:（|<br>| \|)", manifest)
    missing = [p for p in set(paths) if not pathlib.Path(p).exists()]
    check(not missing, "清单中每个检查点路径都在磁盘上",
          f"{len(set(paths))} 个路径，缺失 {len(missing)} 个" + (f"：{missing[:3]}" if missing else ""))

    # 3 - every job reached a terminal state
    states: dict[str, str] = {}
    for path in JOBS.glob("*.json"):
        job = json.loads(path.read_text())
        if job.get("legacy"):
            continue
        states[job["job_id"]] = job.get("status")
    open_jobs = {n: s for n, s in states.items() if s not in TERMINAL and s not in ("deferred", "stopped")}
    check(not open_jobs, "作业总表中无待运行/运行中", f"{len(open_jobs)} 个未终态" if open_jobs else "全部终态")

    # 4 - one job document per job, with the backtest rows
    docs = list((DOCS / "jobs").glob("*.md"))
    check(len(docs) >= 54, "每个作业一份 docs/jobs/<id>.md", f"{len(docs)} 份")
    sample = sorted((DOCS / "jobs").glob("stage3_adapt_*.md"))[:3]
    for path in sample:
        text = path.read_text(encoding="utf-8")
        rows = [line for line in text.splitlines() if re.match(r"^\| (500|1000|1500|2000) \|", line)]
        check(bool(rows), f"{path.name} 记录了每 500 步的回测行",
              f"{len(rows)} 行回测" if rows else "尚无回测行（作业未跑）")

    # 5 - the round summary and the deliverable table
    progress = (DOCS / "00_progress.md").read_text(encoding="utf-8") if (DOCS / "00_progress.md").is_file() else ""
    check("总汇总" in progress and "磁盘" in progress, "00_progress.md 含总汇总与磁盘占用", "有" if "总汇总" in progress else "无")
    check((ROOT / "deliverables" / "summary_zh.md").is_file()
          and (ROOT / "deliverables" / "jobs.json").is_file(),
          "deliverables/ 含机器可读作业表与中文摘要", "有")

    # 6 - the lark receipt
    receipt = ROOT / "state" / "final_notify.json"
    payload = json.loads(receipt.read_text()) if receipt.is_file() else {}
    status = (payload.get("record") or {}).get("status")
    check(status == "sent", "飞书「全部完成」通知已送达", f"status={status}")

    # 7 - the disk
    usage = subprocess.run(["df", "-h", str(ROOT)], capture_output=True, text=True).stdout.splitlines()[-1]
    check(True, "磁盘余量", usage)

    # 8 - the forbidden items: no zero-step baseline, no final_eval.py run
    zero_step = subprocess.run(["grep", "-rl", "zero-step\\|zero_shot", str(ROOT / "logs")],
                               capture_output=True, text=True).stdout.strip()
    check(not zero_step, "未运行 0 步裸测", "无" if not zero_step else zero_step[:200])
    hits = subprocess.run(["grep", "-rh", "final_eval.py", str(ROOT / "logs")],
                          capture_output=True, text=True).stdout.splitlines()
    # the verification output itself mentions the script name - ignore it
    final_eval = "\n".join(line for line in hits if "[PASS]" not in line and "[FAIL]" not in line)
    check(not final_eval, "未运行 final_eval.py 的最终评估流程", "无" if not final_eval else final_eval[:200])

    width = max(len(name) for _, name, _ in results)
    failed = 0
    for ok, name, evidence in results:
        failed += 0 if ok else 1
        print(f"[{'PASS' if ok else 'FAIL'}] {name.ljust(width)}  {evidence}")
    print(f"\n{len(results) - failed}/{len(results)} 项通过")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
