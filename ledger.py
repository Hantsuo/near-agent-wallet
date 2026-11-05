"""Append-only ledger of settled intents.

JSONL on disk, one line per settlement, fsync-free but replayed on startup. The
policy engine reads it; nothing else writes it. `has_key` is the replay guard,
so a crashed agent that retries the same intent cannot pay twice.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from statistics import median


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class Ledger:
    def __init__(self, path: str):
        self.path = path
        self._entries: list[dict] = []
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        self._entries.append(json.loads(line))

    # ------------------------------------------------------------------ writes
    def settle(self, intent, decision, *, tx_hash: str = "", at: datetime | None = None) -> dict:
        stamp = at or datetime.now(timezone.utc)
        entry = {
            "id": intent.id,
            "key": intent.idempotency_key,
            "kind": intent.kind,
            "token": intent.token,
            "amount": str(intent.amount),
            "to": intent.to,
            "memo": intent.memo,
            "level": decision.level,
            "settled_at": stamp.isoformat().replace("+00:00", "Z"),
            "tx_hash": tx_hash,
        }
        self._entries.append(entry)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    # ------------------------------------------------------------------- reads
    def entries(self) -> list[dict]:
        return list(self._entries)

    def has_key(self, key: str) -> bool:
        return any(e["key"] == key and e["level"] in ("allow", "approval") for e in self._entries)

    def total_since(self, since: datetime, token: str) -> Decimal:
        total = Decimal("0")
        for e in self._entries:
            if e["level"] not in ("allow", "approval"):
                continue
            if e["token"].upper() != token.upper():
                continue
            if _parse_ts(e["settled_at"]) >= since:
                total += Decimal(e["amount"])
        return total

    def count_since(self, since: datetime) -> int:
        return sum(1 for e in self._entries
                   if e["level"] in ("allow", "approval")
                   and _parse_ts(e["settled_at"]) >= since)

    def median_amount(self, token: str, limit: int = 20) -> Decimal | None:
        amounts = [Decimal(e["amount"]) for e in self._entries
                   if e["level"] in ("allow", "approval") and e["token"].upper() == token.upper()]
        if len(amounts) < 3:
            return None
        return Decimal(str(median(amounts[-limit:])))
