"""Canonical envelope + digest for an approved intent.

This module does NOT hold a key and does NOT broadcast. It turns a decision the
engine already made into the exact bytes a wallet would sign, so the payload can
be audited, diffed and replayed. Real signing happens in `near-cli` /
`near-api-js` on the ops box, never inside the agent process.

Keeping the key out of the agent is the whole point: the agent can propose, the
policy can approve, only a separate signer can spend.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone


def envelope(intent, decision, *, network: str = "testnet", signer_id: str = "agent.policy.testnet") -> dict:
    body = {
        "network": network,
        "signer_id": signer_id,
        "receiver_id": intent.to,
        "actions": [{
            "type": "Transfer" if intent.kind == "transfer" else "FunctionCall",
            "token": intent.token,
            "amount": str(intent.amount),
            "memo": intent.memo,
        }],
        "intent_id": intent.id,
        "policy": {"level": decision.level, "checks": decision.checks},
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {
        "body": body,
        "canonical": canonical,
        "digest": "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "signed": False,
        "note": "dry-run envelope: sign with near-cli on the ops box, never in the agent",
    }
