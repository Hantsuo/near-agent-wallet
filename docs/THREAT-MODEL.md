# Threat model

Written before the code, because a security demo that cannot name its own gaps is
a liability.

## Assets

| asset | why it matters |
|---|---|
| the wallet balance | the obvious one |
| the signing key | whoever holds it can bypass every rule below |
| ledger integrity | the budget and velocity checks read it; forged history defeats them |
| human attention | approvals are the last line, and they are exhaustible |

## Adversaries

1. **A manipulated agent.** Prompt injection through a web page, a file, an API
   response, or another agent's message. It still runs as the agent: it can call
   `propose` as fast as it likes, with whatever arguments it likes.
2. **A buggy agent.** No adversary at all — a retry loop, a unit confusion
   (NEAR vs yoctoNEAR), a stale plan. This is the more common cause of loss.
3. **A malicious counterparty.** Gets paid once, then keeps the invoice open and
   asks again; or asks from a lookalike address.
4. **An observer with the ledger.** Can read every payment; must not be able to
   re-submit one.

## Boundaries

| boundary | what crosses it | enforced by |
|---|---|---|
| agent → engine | an `Intent`: id, token, amount, recipient, memo | `policy.py`, pure function |
| engine → ledger | a settled intent, exactly once | idempotency key in `ledger.py` |
| engine → signer | a canonical envelope + digest | `signer.py`, which has no key |
| human → engine | an approval with a timestamp | TTL check on re-evaluation |

The agent never holds the key, never writes the ledger, and never approves
anything. Every one of those is a separate call it cannot make.

## What each check buys

| check | stops | does not stop |
|---|---|---|
| `per_tx_max` | one catastrophic call | a thousand small ones |
| `daily_max` | a day of damage | the next day |
| `hourly_count_max` | a fast drip | a slow one over days |
| `allowlist` | a lookalike recipient | a compromised allowlisted one |
| `require_approval_over` | large payments without a human | a tired human clicking yes |
| `approval_ttl_s` | a stale yes being reused | a fresh yes |
| `spike_multiple` | a sudden change in size | a gradual ramp — by design |
| `kill_switch` | everything, immediately | an attacker who already moved funds |

The design assumes each check fails eventually; the point is that they fail at
different times and sizes.

## Residual risks, named

1. **Whoever runs `policy.py` is trusted.** In this demo the engine, the agent and
   the ledger are one process. A production deployment must put the engine behind
   its own socket and give the agent no filesystem access to the ledger.
2. **The signer is a stub.** `signer.py` produces a digest, not a signature. Until
   a real signer exists on a separate host, the "key never enters the agent"
   claim is architectural intent, not a verified property.
3. **The ledger is a file.** Anyone with write access can rewrite history. In
   production the ledger is the chain, or an append-only log with an external
   anchor.
4. **Approval fatigue.** A policy that asks too often trains the human to click
   yes. The thresholds in `policy.json` are a starting point, not a recommendation.

## The three changes that would make this real

1. Move the engine to its own process, reachable only through a signed request
   from the agent, and give the ledger file 0400 permissions for the agent user.
2. Put the signer behind a separate host or an HSM, and require a second factor
   for `execute`.
3. Anchor the ledger root hash on-chain daily, so a rewrite is detectable without
   trusting the file.
