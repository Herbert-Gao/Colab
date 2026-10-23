"""Failure counter and the lark escalation of the run book.

Every failed job attempt is counted across the whole campaign.  As soon as the
cumulative count reaches ten, the user is informed through lark-im; the
escalation repeats every ten further failures.  The loop itself is not
stopped by this - the run book keeps going with the remaining jobs.

    python failures.py record <job_id> <attempts> <reason>
    python failures.py check
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

THRESHOLD = 10
COUNTER = C.STATE / "failure_counter.json"


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def load() -> dict:
    if COUNTER.is_file():
        try:
            return json.loads(COUNTER.read_text())
        except json.JSONDecodeError:
            pass
    return {"count": 0, "notified_count": 0, "events": []}


def save(data: dict) -> None:
    C.json_dump(COUNTER, data)


def record(job_id: str, attempts: str, reason: str) -> dict:
    data = load()
    data["count"] = int(data.get("count", 0)) + 1
    data.setdefault("events", []).append({
        "time": now(), "job": job_id, "attempts": int(attempts or 0), "reason": reason,
    })
    save(data)
    return data


def check() -> dict:
    """Notify the user when the cumulative failures reach the threshold."""
    data = load()
    count = int(data.get("count", 0))
    notified = int(data.get("notified_count", 0))
    if count < THRESHOLD or count - notified < THRESHOLD:
        return data
    import notify_channel
    jobs = sorted({event["job"] for event in data.get("events", [])})
    message = (f"服务器A/A800×8｜阶段3：累计失败 {count} 次（阈值 {THRESHOLD}）；"
               f"相关作业已暂停/跳过，其余作业继续；需协助。失败作业：{', '.join(jobs[-6:])}")
    record_state = notify_channel.send(message)
    data["notified_count"] = count
    data["notified_at"] = now()
    data["notify"] = record_state
    save(data)
    print(json.dumps({"status": record_state.get("status"), "count": count}, ensure_ascii=False))
    return data


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "record":
        data = record(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "0",
                      sys.argv[4] if len(sys.argv) > 4 else "")
        check()
        print(json.dumps({"count": data["count"]}, ensure_ascii=False))
        return 0
    data = check()
    print(json.dumps({"count": data.get("count", 0),
                      "notified_count": data.get("notified_count", 0)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
