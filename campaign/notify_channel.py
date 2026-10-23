"""Feishu notifications for the campaign (section 7).

The lark-bot-bridge profile is bound to lark-cli as a bot; messages go to the
chat the current OMP session was started from.  Delivery receipts are stored in
``logs/notify.jsonl`` and the return value carries the message id so the caller
can record whether the alert actually arrived.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

import config as C

LOG = C.LOGS / "notify.jsonl"
CHAT_ID_FILE = C.STATE / "notify_chat_id"


def current_chat_id() -> str | None:
    """The chat this OMP session was started from (lark-bot-bridge session map)."""
    if CHAT_ID_FILE.is_file():
        value = CHAT_ID_FILE.read_text().strip()
        if value:
            return value
    sessions_file = Path.home() / ".lark-bot-bridge/profiles/omp/sessions.json"
    try:
        sessions = json.loads(sessions_file.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    if not sessions:
        return None
    chat = max(sessions.items(), key=lambda kv: kv[1].get("updatedAt", 0))[0]
    CHAT_ID_FILE.parent.mkdir(parents=True, exist_ok=True)
    CHAT_ID_FILE.write_text(chat)
    return chat


def send(message: str, *, log: Path | None = None) -> dict:
    """Send one short line through lark-im; keep the receipt."""
    record = {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "message": message}
    try:
        chat = current_chat_id()
        if not chat:
            record.update(status="no_chat_binding")
            return record
        key = "srvA" + hashlib.sha1(message.encode()).hexdigest()[:9]
        result = subprocess.run(
            ["lark-cli", "im", "+messages-send", "--chat-id", chat, "--text", message,
             "--idempotency-key", key],
            capture_output=True, text=True, timeout=120, check=False,
            env={**os.environ, "LARK_CHANNEL_HOME": "/home/szgx/.lark-bot-bridge"},
        )
        receipt = None
        if result.stdout.strip().startswith("{"):
            try:
                receipt = json.loads(result.stdout)
            except json.JSONDecodeError:
                receipt = None
        record.update(returncode=result.returncode, receipt=receipt,
                      stderr=result.stderr[-400:] if result.returncode else "")
        record["status"] = "sent" if result.returncode == 0 else "failed"
    except Exception as error:  # noqa: BLE001 - notification must never kill the run
        record.update(status="error", error=f"{type(error).__name__}: {error}")
    path = log or LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record
