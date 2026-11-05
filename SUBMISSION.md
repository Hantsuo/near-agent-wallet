# NEAR Hackathon submission pack

Track: **06 AI Security & Defense**. Deadline: **14 Nov 2026, 23:59 UTC**.
Rules require three things: a public repo, a public demo post on X tagging
`@NEARProtocol` with `#NEARHackathon`, and the submission form with both links.

## Form fields

| field | value |
|---|---|
| Project name | Blast Radius Zero — Agent Wallet Edition |
| Team size | Solo builder |
| Tracks | 06 AI Security & Defense (optionally 07 Agent Economy) |
| Repository | https://github.com/Hantsuo/near-agent-wallet |
| Demo post | _X post URL_ |
| NEAR wallet | `6594532b2ab4a31d4a11cc7c0f0bfe0f26ac6284621a23ec3a6e375d983f60ae` (implicit account, mainnet) |

## What did you build (20–2000 chars)

Blast Radius Zero is a policy engine that lets an AI agent hold and spend NEAR
without giving it the keys. The agent may only propose an `Intent`; a pure,
clock-injected policy engine decides allow / approval / deny against per-tx
caps, a rolling 24h budget, a velocity limit, a recipient allowlist, an
approval TTL and a median-amount spike detector. Approved intents are written to
an append-only JSONL ledger that doubles as the replay guard, so a restarted
agent cannot pay the same intent twice. The signing key never enters the agent
process: the repo emits a canonical envelope and its SHA-256 digest, and
`near-cli` signs it on the ops box. Nine attack scenarios — one-shot drain, six
sub-cap transfers in a minute, unknown recipient, replay, stale approval, kill
switch, value spike — are asserted in a stdlib-only test suite.

## Demo post draft (X)

> Built for @NEARProtocol #NEARHackathon — track 06, AI Security & Defense.
>
> Blast Radius Zero: an agent that holds a NEAR wallet and still cannot drain it.
> Nine attacks, all stopped or escalated: drain, split transfer, replay, stale
> approval, value spike, kill switch.
>
> Stdlib only, tests in the repo. [repo link]
>
> One idea: give the agent money, never the key.

## Before submitting

- [ ] repo is public and the README renders
- [ ] `python -m unittest discover -s tests` passes on a clean clone
- [ ] demo post published and public
- [ ] wallet address filled in (testnet is fine)
