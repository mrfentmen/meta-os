# Round 13 — Hands-Free summary (Section P)

| section | state | counts | evidence |
|---|---|---|---|
| Hands-Free intake | **COMPLETE** | 25 / 25; **25 tests pass**, 14 findings, 3 fences checked | `os-build/round13/handsfree/SECTION_P.md` |

## What the 25 cases found

- All 25 pass, and every case asserts the same invariant: filed + refused accounts for every line, so nothing is silently dropped.
- **The refusal catalogue is not wired into intake.** `handsfree/refusals.mjs` refuses "send the report"; `intake.mjs` files it as a job anyway (R13-394). The fence exists as data and is never consulted.
- No size cap, no case normalisation, no verb check, no duplicate check. A pasted log, a pasted error and a timestamped line become orders whose "agent" is `12`, `Error` and `2026-11-02 14`.
- A spoken `STOP` is filed as work, not as a stop.
- The voice seam remains a blocker: `handsfree/voice.mjs` is a text formatter with no audio path, and nothing in this round changed that.
