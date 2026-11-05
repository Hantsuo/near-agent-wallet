# NEAR Hackathon submission pack

Track: **06 AI Security & Defense**. Deadline: **14 Nov 2026, 23:59 UTC**.
Rules require three things: a public repo, a public demo post on X tagging
`@NEARProtocol` with `#NEARHackathon`, and the submission form with both links.

## Form fields

| field | value |
|---|---|
| Project name | Blast Radius Zero — Agent Wallet Edition |
| Team size | Solo builder |
| Tracks | 06 AI Security & Defense |
| Repository | https://github.com/Hantsuo/near-agent-wallet |
| Demo post | https://x.com/3rsona/status/2118345921692127594 |
| NEAR wallet | `6594532b2ab4a31d4a11cc7c0f0bfe0f26ac6284621a23ec3a6e375d983f60ae` (implicit account, mainnet) |

## What did you build (20–2000 chars)

Blast Radius Zero is the decision layer between an AI agent and a wallet. The
agent can only propose an `Intent`; a pure, clock-injected policy engine decides
allow / approval / deny against a per-transaction cap, a rolling 24-hour budget, a
velocity limit, a recipient allowlist, an approval TTL and a median-spike anomaly
check computed from the wallet's own history. Approved intents are written to an
append-only ledger that doubles as the replay guard, so a restarted agent cannot
pay the same intent twice. The signing key lives outside the agent process: the
repo emits a canonical envelope and its SHA-256 digest, and a separate signer pays.

Eight attacks are one click each in a zero-dependency browser demo: drain, split
transfer, unknown recipient, above-threshold payment, replay, stale approval,
value spike, kill switch. Four of them — velocity, spike, TTL, replay — are the
ones a plain spending cap does not catch. The whole demo runs on the standard
library: `python demo/server.py`, no install.

## Demo post draft (X)

> Built for @NEARProtocol #NEARHackathon — track 06, AI Security & Defense.
>
> An agent that holds a NEAR wallet and still cannot drain it.
>
> 8 attacks, one click each: drain, split transfer, unknown recipient, replay,
> stale approval, 4.5 NEAR after a 0.5 median, kill switch. Each one is stopped
> or sent to a human.
>
> No pip install. python demo/server.py
> https://github.com/Hantsuo/near-agent-wallet

## Before submitting

- [x] repo is public and the README renders
- [x] `python -m unittest discover -s tests` passes on a clean clone
- [x] demo runs with no dependencies and is screenshot in the README
- [ ] demo post published and public
- [ ] wallet address filled in (done above)
