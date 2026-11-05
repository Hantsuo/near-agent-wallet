# Two-minute demo

Screen recording, 1440×900, terminal + browser. Start the server before recording.

```bash
python demo/server.py
```

| time | on screen | say |
|---|---|---|
| 0:00 | browser at `127.0.0.1:8770`, fresh state | "An agent with a wallet is one prompt injection away from being someone else's wallet. This is the layer that decides what it is allowed to do." |
| 0:10 | point at the policy card | "Five NEAR per call, twenty a day, five calls an hour, anything over one NEAR needs a human, three allowlisted recipients. None of these live in the agent." |
| 0:20 | click **drain** | "One thousand NEAR. Denied twice over: over the per-call cap, over the daily budget." |
| 0:32 | click **split** | "So it tries smaller. Five pass, the sixth is refused — not because of the amount, because of the count. This is the attack a spending cap never sees." |
| 0:48 | click **stranger**, then **approve** in the right panel | "An unknown recipient is never paid automatically. A human sees the address and the reason, and approves — and that approval is timestamped." |
| 1:05 | click **replay** | "The agent crashed mid-loop and retried. The idempotency key is already settled, so the second attempt cannot pay twice." |
| 1:18 | click **spike** | "Three normal payments, then four and a half. Every static limit passes. The median check does not, because this wallet has only ever spent half a NEAR." |
| 1:35 | click **kill**, show the pill turn off | "And when it is clear something is wrong, one switch freezes the whole agent — not one rule, all of them." |
| 1:45 | scroll the ledger | "Every decision is in an append-only ledger: what was proposed, which rule fired, what was paid. Replayable after a restart." |
| 1:55 | back to the policy card | "The agent proposes, the policy decides, a separate signer pays. Give the agent money, never the key." |

## Shots to capture for the submission

1. The dashboard with the feed populated (use `docs/ui.png` as the poster).
2. The terminal running `python -m unittest discover -s tests` — four green lines.
3. A close-up of the `stranger` approval with the reason text visible.

## Failure to avoid on camera

Do not click **reset** mid-recording; the feed clears and the story restarts.
Do not run two servers on the same port — the second binds silently on Windows and
you end up demoing two different states.
