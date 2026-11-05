"""Live demo server: propose, judge, approve, settle — in a browser.

Stdlib only, on purpose. A judge should be able to clone the repo, run one
command, and click the attacks themselves without installing anything.

    python demo/server.py         # http://127.0.0.1:8770
"""
from __future__ import annotations

import json
import os
import sys
import threading
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ledger import Ledger          # noqa: E402
from policy import Intent, Policy, PolicyEngine   # noqa: E402
import signer                       # noqa: E402

STATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state")
os.makedirs(STATE_DIR, exist_ok=True)
LEDGER_PATH = os.path.join(STATE_DIR, "ledger.jsonl")
INDEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

START_BALANCE = Decimal("100")
LOCK = threading.Lock()


class Demo:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        if os.path.exists(LEDGER_PATH):
            os.remove(LEDGER_PATH)
        self.policy = Policy.from_json(os.path.join(ROOT, "policy.json"))
        self.ledger = Ledger(LEDGER_PATH)
        self.engine = PolicyEngine(self.policy, self.ledger)
        self.balance = START_BALANCE
        self.feed: list[dict] = []
        self.pending: dict[str, dict] = {}
        self.counter = 0
        self.log("system", "demo reset", "allow", "policy loaded from policy.json")

    # ------------------------------------------------------------------ helpers
    def log(self, source: str, label: str, level: str, detail: str) -> dict:
        entry = {
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": source,
            "label": label,
            "level": level,
            "detail": detail,
        }
        self.feed.insert(0, entry)
        del self.feed[60:]
        return entry

    def new_intent(self, to: str, amount: str, memo: str = "", id: str | None = None) -> Intent:
        self.counter += 1
        return Intent(
            id=id or f"intent-{self.counter:03d}",
            kind="transfer",
            token="NEAR",
            amount=Decimal(amount),
            to=to,
            memo=memo,
        )

    def decide(self, intent: Intent) -> dict:
        d = self.engine.evaluate(intent)
        detail = "; ".join(d.reasons) if d.reasons else f"{intent.amount} NEAR to {intent.to}"
        self.log("agent", intent.memo or f"transfer {intent.amount} NEAR to {intent.to}",
                 d.level, detail)
        if d.level == "allow":
            self.ledger.settle(intent, d)
            self.balance -= intent.amount
        elif d.level == "approval":
            self.pending[intent.id] = {
                "id": intent.id,
                "to": intent.to,
                "amount": str(intent.amount),
                "memo": intent.memo,
                "reasons": d.reasons,
            }
        return d.as_dict()

    def approve(self, pid: str) -> dict:
        p = self.pending.get(pid)
        if not p:
            return {"error": "no such pending payment"}
        intent = self.new_intent(p["to"], p["amount"], p["memo"], id=pid)
        intent.approved_at = datetime.now(timezone.utc)
        d = self.engine.evaluate(intent)
        self.log("human", f"approved {pid}", d.level, "; ".join(d.reasons) or "re-checked and paid")
        if d.level == "allow":
            self.ledger.settle(intent, d)
            self.balance -= intent.amount
            del self.pending[pid]
        return d.as_dict()

    # ----------------------------------------------------------------- attacks
    def attack(self, name: str) -> list[dict]:
        """Attacks run on a throwaway wallet, so one attack cannot colour the next.

        The real balance, ledger and pending list stay untouched — that is what
        makes the demo legible: every button shows the same rule meeting the same
        attack from a clean state.
        """
        tmp_path = os.path.join(STATE_DIR, "_attack.jsonl")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        ledger = Ledger(tmp_path)
        policy = Policy(**{**self.policy.__dict__})
        engine = PolicyEngine(policy, ledger)
        base = datetime.now(timezone.utc)
        seq = 0

        def intent(to: str, amount: str, memo: str, id: str | None = None,
                   approved: datetime | None = None) -> Intent:
            nonlocal seq
            seq += 1
            return Intent(id=id or f"sim-{seq}", kind="transfer", token="NEAR",
                          amount=Decimal(amount), to=to, memo=memo,
                          created_at=base, approved_at=approved)

        def run(i: Intent) -> dict:
            d = engine.evaluate(i, now=base + timedelta(seconds=seq))
            if d.level != "deny":
                ledger.settle(i, d, at=base + timedelta(seconds=seq))
            detail = "; ".join(d.reasons) if d.reasons else f"{i.amount} NEAR to {i.to} settled"
            self.log(f"attack:{name}", i.memo, d.level, detail)
            return d.as_dict()

        out: list[dict] = []
        if name == "drain":
            out.append(run(intent("alice.near", "1000", "drain: 1000 NEAR at once")))
        elif name == "split":
            for _ in range(6):
                out.append(run(intent("alice.near", "0.9", "split: 0.9 NEAR, one of six")))
                if out[-1]["level"] == "deny":
                    break
        elif name == "stranger":
            out.append(run(intent("mallory.near", "0.5", "stranger: unknown recipient")))
        elif name == "over":
            out.append(run(intent("alice.near", "2", "over: 2 NEAR, above the 1 NEAR threshold")))
        elif name == "replay":
            i = intent("alice.near", "0.5", "replay: same intent, twice", id="fixed-intent")
            out.append(run(i))
            out.append(run(i))
        elif name == "stale":
            out.append(run(intent("mallory.near", "2", "stale: approval 20 minutes old",
                                  approved=base - timedelta(minutes=20))))
        elif name == "spike":
            for _ in range(3):
                out.append(run(intent("alice.near", "0.5", "spike: normal 0.5 NEAR")))
            out.append(run(intent("alice.near", "4.5", "spike: 4.5 NEAR after a 0.5 median")))
        elif name == "kill":
            policy = replace(policy, kill_switch=True)
            engine = PolicyEngine(policy, ledger)
            self.log("human", "kill switch flipped", "deny", "whole agent frozen")
            out.append(run(intent("alice.near", "0.1", "kill: 0.1 NEAR after the switch")))
        else:
            return [{"error": f"unknown attack {name}"}]

        os.remove(tmp_path) if os.path.exists(tmp_path) else None
        return out

    def snapshot(self) -> dict:
        return {
            "balance": str(self.balance),
            "policy": {
                "per_tx_max": str(self.policy.per_tx_max),
                "daily_max": str(self.policy.daily_max),
                "hourly_count_max": self.policy.hourly_count_max,
                "require_approval_over": str(self.policy.require_approval_over),
                "allowlist": list(self.policy.allowlist),
                "approval_ttl_s": self.policy.approval_ttl_s,
                "kill_switch": self.policy.kill_switch,
            },
            "spent_today": str(self.ledger.total_since(
                datetime.now(timezone.utc) - timedelta(days=1), "NEAR")),
            "feed": self.feed[:40],
            "pending": list(self.pending.values()),
            "ledger": self.ledger.entries()[-12:],
        }


DEMO = Demo()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args) -> None:  # keep the console readable
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload, code: int = 200) -> None:
        self._send(code, json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            with open(INDEX, "rb") as fh:
                self._send(200, fh.read(), "text/html; charset=utf-8")
        elif self.path == "/api/state":
            with LOCK:
                self._json(DEMO.snapshot())
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return self._json({"error": "bad json"}, 400)

        path = self.path.rstrip("/")
        with LOCK:
            if path == "/api/propose":
                intent = DEMO.new_intent(
                    body.get("to", "alice.near"),
                    str(body.get("amount", "0.5")),
                    body.get("memo", "manual"),
                )
                return self._json(DEMO.decide(intent))
            if path.startswith("/api/attack/"):
                return self._json({"decisions": DEMO.attack(path.rsplit("/", 1)[-1])})
            if path.startswith("/api/approve/"):
                return self._json(DEMO.approve(path.rsplit("/", 1)[-1]))
            if path == "/api/kill":
                kill = bool(body.get("on", True))
                DEMO.policy = Policy(**{**DEMO.policy.__dict__, "kill_switch": kill})
                DEMO.engine = PolicyEngine(DEMO.policy, DEMO.ledger)
                DEMO.log("human", f"kill switch {'on' if kill else 'off'}", "allow" if not kill else "deny",
                         "policy updated")
                return self._json({"ok": True, "kill_switch": kill})
            if path == "/api/reset":
                DEMO.reset()
                return self._json({"ok": True})
        return self._json({"error": "not found"}, 404)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8770"))
    print(f"policy demo on http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
