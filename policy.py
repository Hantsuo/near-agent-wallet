"""Policy engine for an AI agent that holds a wallet.

Every intent the agent proposes passes through `PolicyEngine.evaluate` before it
can be signed. The engine is deliberately boring: small, pure, and replayable.
No network, no randomness, no clock of its own -- `now` is injected so the same
intent can be re-judged against the same ledger years later.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation


def _d(value) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"not a decimal: {value!r}") from exc


@dataclass(frozen=True)
class Policy:
    per_tx_max: Decimal
    daily_max: Decimal
    hourly_count_max: int
    require_approval_over: Decimal
    allowlist: tuple[str, ...]
    token_allowlist: tuple[str, ...] = ("NEAR",)
    approval_ttl_s: int = 900
    kill_switch: bool = False
    spike_multiple: Decimal = Decimal("5")

    @classmethod
    def from_json(cls, path: str) -> "Policy":
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
        return cls(
            per_tx_max=_d(raw["per_tx_max"]),
            daily_max=_d(raw["daily_max"]),
            hourly_count_max=int(raw["hourly_count_max"]),
            require_approval_over=_d(raw["require_approval_over"]),
            allowlist=tuple(a.lower() for a in raw["allowlist"]),
            token_allowlist=tuple(t.upper() for t in raw.get("token_allowlist", ["NEAR"])),
            approval_ttl_s=int(raw.get("approval_ttl_s", 900)),
            kill_switch=bool(raw.get("kill_switch", False)),
            spike_multiple=_d(raw.get("spike_multiple", 5)),
        )


@dataclass
class Intent:
    id: str
    kind: str                 # "transfer" | "call"
    token: str
    amount: Decimal
    to: str
    memo: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    approved_at: datetime | None = None

    @property
    def idempotency_key(self) -> str:
        return f"{self.id}:{self.kind}:{self.token}:{self.amount}:{self.to.lower()}"


@dataclass
class Decision:
    level: str                       # "allow" | "approval" | "deny"
    reasons: list[str]
    checks: dict[str, str]

    @property
    def allowed(self) -> bool:
        return self.level == "allow"

    def as_dict(self) -> dict:
        return {"level": self.level, "allowed": self.allowed,
                "reasons": self.reasons, "checks": self.checks}


class PolicyEngine:
    def __init__(self, policy: Policy, ledger):
        self.policy = policy
        self.ledger = ledger

    # ---------------------------------------------------------------- evaluate
    def evaluate(self, intent: Intent, now: datetime | None = None) -> Decision:
        now = now or datetime.now(timezone.utc)
        checks: dict[str, str] = {}
        deny: list[str] = []
        review: list[str] = []

        # 1. kill switch: the whole agent is frozen, not just this intent
        if self.policy.kill_switch:
            return Decision("deny", ["kill_switch is on"], {"kill_switch": "deny"})
        checks["kill_switch"] = "pass"

        # 2. replay: the same intent must not be paid twice
        if self.ledger.has_key(intent.idempotency_key):
            return Decision("deny", ["duplicate intent (idempotency key already settled)"],
                            {"replay": "deny"})
        checks["replay"] = "pass"

        # 3. token allowlist
        if intent.token.upper() not in self.policy.token_allowlist:
            deny.append(f"token {intent.token} not in allowlist")
        checks["token"] = "deny" if deny else "pass"

        # 4. amount sanity
        if intent.amount <= 0:
            deny.append("amount must be positive")
        if intent.amount > self.policy.per_tx_max:
            deny.append(f"amount {intent.amount} > per_tx_max {self.policy.per_tx_max}")
        checks["per_tx_cap"] = "deny" if any("per_tx_max" in r for r in deny) else "pass"

        # 5. daily budget, counting only what was actually settled
        spent = self.ledger.total_since(now - timedelta(days=1), intent.token)
        if spent + intent.amount > self.policy.daily_max:
            deny.append(f"daily budget: spent {spent} + {intent.amount} > {self.policy.daily_max}")
        checks["daily_budget"] = "deny" if any("daily budget" in r for r in deny) else "pass"

        # 6. velocity: many small intents are how you drain a wallet slowly
        recent = self.ledger.count_since(now - timedelta(hours=1))
        if recent >= self.policy.hourly_count_max:
            deny.append(f"velocity: {recent} intents in the last hour >= {self.policy.hourly_count_max}")
        checks["velocity"] = "deny" if any("velocity" in r for r in deny) else "pass"

        # 7. recipient allowlist
        allowed_to = intent.to.lower() in self.policy.allowlist
        if not allowed_to:
            review.append(f"recipient {intent.to} is not on the allowlist")
        checks["recipient"] = "pass" if allowed_to else "review"

        # 8. size that needs a human, even when every other check passes
        if intent.amount > self.policy.require_approval_over:
            review.append(f"amount {intent.amount} > approval threshold "
                          f"{self.policy.require_approval_over}")
            checks["approval_threshold"] = "review"

        # 9. spike against this wallet's own history
        typical = self.ledger.median_amount(intent.token, limit=20)
        if typical and intent.amount > typical * self.policy.spike_multiple:
            review.append(f"spike: {intent.amount} > {self.policy.spike_multiple}x median {typical}")
            checks["spike"] = "review"

        # 10. approvals expire; an approval from yesterday is not consent today
        if intent.approved_at is not None:
            age = (now - intent.approved_at).total_seconds()
            if age > self.policy.approval_ttl_s:
                deny.append(f"approval expired ({int(age)}s > {self.policy.approval_ttl_s}s)")
                checks["approval_ttl"] = "deny"
            else:
                review = [r for r in review if not r.startswith(("recipient", "amount", "spike"))]
                checks["approval_ttl"] = "pass"

        if deny:
            return Decision("deny", deny + review, checks)
        if review:
            return Decision("approval", review, checks)
        return Decision("allow", [], checks)
