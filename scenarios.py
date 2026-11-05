"""Nine ways an agent tries to spend money it should not, and what the policy says.

Each scenario gets a fresh ledger and a fresh clock, so the result is a claim
about the policy, not about whatever else happened that day. `demo.py` prints
them; `tests/test_policy.py` asserts them.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ledger import Ledger
from policy import Intent, Policy, PolicyEngine

T0 = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)


@dataclass
class Result:
    name: str
    expected: str
    actual: str
    detail: str
    passed: bool


def _engine(overrides: dict | None = None):
    raw = {
        "per_tx_max": "5", "daily_max": "20", "hourly_count_max": 5,
        "require_approval_over": "1",
        "allowlist": ["alice.near", "bob.near", "treasury.near"],
        "token_allowlist": ["NEAR", "USDC"], "approval_ttl_s": 900,
        "kill_switch": False, "spike_multiple": "5",
    }
    raw.update(overrides or {})
    policy = Policy(
        per_tx_max=Decimal(raw["per_tx_max"]),
        daily_max=Decimal(raw["daily_max"]),
        hourly_count_max=int(raw["hourly_count_max"]),
        require_approval_over=Decimal(raw["require_approval_over"]),
        allowlist=tuple(raw["allowlist"]),
        token_allowlist=tuple(raw["token_allowlist"]),
        approval_ttl_s=int(raw["approval_ttl_s"]),
        kill_switch=bool(raw["kill_switch"]),
        spike_multiple=Decimal(raw["spike_multiple"]),
    )
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.unlink(path)
    ledger = Ledger(path)
    return PolicyEngine(policy, ledger), ledger, path


def _intent(i: int, amount: str, to: str = "alice.near", when: datetime = T0,
            approved: datetime | None = None, token: str = "NEAR") -> Intent:
    return Intent(id=f"intent-{i}", kind="transfer", token=token,
                  amount=Decimal(amount), to=to, memo="scenario",
                  created_at=when, approved_at=approved)


def _settle(engine, ledger, intent, when):
    decision = engine.evaluate(intent, now=when)
    if decision.level != "deny":
        ledger.settle(intent, decision, at=when)
    return decision


def sane_transfer():
    engine, ledger, path = _engine()
    try:
        d = engine.evaluate(_intent(1, "0.5"), now=T0)
        return d.level, f"0.5 NEAR to allowlisted alice.near, reasons={d.reasons}"
    finally:
        os.unlink(path) if os.path.exists(path) else None


def drain_attempt():
    engine, ledger, path = _engine()
    try:
        d = engine.evaluate(_intent(1, "1000"), now=T0)
        return d.level, "; ".join(d.reasons)
    finally:
        os.unlink(path) if os.path.exists(path) else None


def split_attack():
    """Ten sub-cap transfers in one minute: the classic slow drain."""
    engine, ledger, path = _engine()
    try:
        levels = []
        for i in range(1, 7):
            d = _settle(engine, ledger, _intent(i, "0.9"), T0 + timedelta(seconds=i * 5))
            levels.append(d.level)
        return levels[-1], f"levels={levels} (first five allowed, sixth must die)"
    finally:
        os.unlink(path) if os.path.exists(path) else None


def new_recipient():
    engine, ledger, path = _engine()
    try:
        d = engine.evaluate(_intent(1, "0.5", to="mallory.near"), now=T0)
        return d.level, "; ".join(d.reasons)
    finally:
        os.unlink(path) if os.path.exists(path) else None


def over_threshold():
    engine, ledger, path = _engine()
    try:
        d = engine.evaluate(_intent(1, "2"), now=T0)
        return d.level, "; ".join(d.reasons)
    finally:
        os.unlink(path) if os.path.exists(path) else None


def replay():
    engine, ledger, path = _engine()
    try:
        intent = _intent(1, "0.5")
        first = _settle(engine, ledger, intent, T0)
        second = engine.evaluate(intent, now=T0 + timedelta(seconds=2))
        return second.level, f"first={first.level}, second={second.level}: {'; '.join(second.reasons)}"
    finally:
        os.unlink(path) if os.path.exists(path) else None


def stale_approval():
    engine, ledger, path = _engine()
    try:
        intent = _intent(1, "2", to="mallory.near", approved=T0 - timedelta(minutes=20))
        d = engine.evaluate(intent, now=T0)
        return d.level, "; ".join(d.reasons)
    finally:
        os.unlink(path) if os.path.exists(path) else None


def kill_switch():
    engine, ledger, path = _engine({"kill_switch": True})
    try:
        d = engine.evaluate(_intent(1, "0.1"), now=T0)
        return d.level, "; ".join(d.reasons)
    finally:
        os.unlink(path) if os.path.exists(path) else None


def spike():
    engine, ledger, path = _engine()
    try:
        for i in range(1, 4):
            _settle(engine, ledger, _intent(i, "0.5"), T0 + timedelta(minutes=i))
        d = engine.evaluate(_intent(9, "4.5"), now=T0 + timedelta(minutes=10))
        return d.level, "; ".join(d.reasons)
    finally:
        os.unlink(path) if os.path.exists(path) else None


SCENARIOS = [
    ("sane transfer 0.5 NEAR", "allow", sane_transfer),
    ("drain: 1000 NEAR in one go", "deny", drain_attempt),
    ("split: 6 x 0.9 NEAR in a minute", "deny", split_attack),
    ("new recipient mallory.near", "approval", new_recipient),
    ("2 NEAR, above 1 NEAR threshold", "approval", over_threshold),
    ("replay the same intent", "deny", replay),
    ("approval 20 minutes old", "deny", stale_approval),
    ("kill switch on", "deny", kill_switch),
    ("4.5 NEAR after a 0.5 median", "approval", spike),
]


def run_all() -> list[Result]:
    out = []
    for name, expected, fn in SCENARIOS:
        actual, detail = fn()
        out.append(Result(name, expected, actual, detail, actual == expected))
    return out


if __name__ == "__main__":
    for r in run_all():
        print(f"{'PASS' if r.passed else 'FAIL'}  {r.name:38s} {r.actual:9s} {r.detail}")
