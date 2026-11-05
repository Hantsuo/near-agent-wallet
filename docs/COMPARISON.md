# How this differs from the products that already exist

Being honest about the neighbourhood is part of the submission. All of these are
more complete than this demo; none of them ship the four checks below as a
default.

| | this demo | Coinbase Agentic Wallets | Openfort | Turnkey |
|---|---|---|---|---|
| where policy is enforced | before signing, in a reference engine | MPC policy layer, then enclave | on-chain in the smart account (ERC-7715) | inside the enclave at signing |
| per-transaction cap | ✓ | ✓ | ✓ | ✓ |
| rolling / session budget | ✓ | ✓ | ✓ | ✓ |
| recipient allowlist | ✓ | ✓ | ✓ | ✓ |
| velocity limit (calls per hour) | ✓ | — | ✓ | — |
| median-spike anomaly check | ✓ | — | — | — |
| approval that expires | ✓ | ✓ | ✓ | ✓ |
| replay ledger | ✓ | ✓ | ✓ | ✓ |
| custody of real funds | — | ✓ | ✓ | ✓ |
| verifiable by a third party | — | — | ✓ | — |

## Where each one wins

**Coinbase Agentic Wallets** is the closest product comparison: session caps,
per-transaction limits, allowlists, x402 payments, MPC signing. It is a wallet,
not a policy library — you adopt their custody to get their limits.

**Openfort** is the strongest design in the table: the limits are enforced by the
smart account, so a bug in the agent cannot bypass them, and anyone can verify the
grant on-chain. That is the property this demo only argues for.

**Turnkey** enforces at the enclave, which is the best answer to "what if the
policy service is compromised" — the key material never leaves the enclave.

## What is actually new here

Two things, and neither is a moat:

1. **Anomaly detection as a first-class check.** Everyone ships caps. Almost
   nobody ships "this wallet has only ever spent 0.5, and now it wants 4.5" — the
   baseline is the wallet's own history, which is free to compute and catches the
   compromise that stays under every static limit.
2. **The decision is a first-class object.** `Decision` carries `checks` per rule,
   so the demo, the ledger and the test suite all read the same structure. A
   reviewer can see *which* rule fired, not just that something was refused.

## What a judge should conclude

This is a decision layer, not a custody product. Its natural home is inside one of
the products above — as the anomaly and velocity component that turns a spending
cap into something that notices.
