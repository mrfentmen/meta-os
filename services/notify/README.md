# notify — the top bar's feed, and the four things a feed gets wrong

Status: **RUNS** — `tests/t95_notify` passes in the native host corpus
(`run_native.sh t95_notify`, measured 2026-11-02: `RUNS=1 FAILS=0`), and the
program typechecks under `os-build/layer1/check_services.sh`. Layer 5, face
service 7.

## What it is

One feed for the things the machine has to say to the user: a board post arrived,
an update is available, a receipt landed, a service degraded. Before this, each of
those was a line in the log (where nobody looks) or a badge on one app's tile
(which the user is not looking at either).

## The four properties, each one here because the obvious version gets it wrong

1. **Duplicates are one notification, not twelve.** Identical `(source, text)`
   inside `NT_DEDUPE_MS` returns the id that is already there plus a code saying
   so, and `nt_duplicate_total` counts it. A producer that retries, or a feed that
   fires on every tick, cannot fill the bar with the same sentence.
2. **A dismissal is a record, not a deletion.** Dismissing frees the slot — a feed
   full of dismissed items must not become a feed that can never show anything
   again — but the dismissal is kept in a ring with its time
   (`nt_dismissal_at`, `nt_dismissal_sev_at`, `nt_dismissal_when_at`), so "the
   user saw this and closed it" survives the slot being reused. That ring is the
   audit trail for the bar.
3. **Refusal is counted.** A thirteenth notification with twelve on screen is
   refused with `E_NO_SPACE` and counted by `nt_refusal_total`. Silently dropping
   the oldest is how a feed loses the one message that mattered.
4. **The bar dot is derived, not told.** `nt_worst()` is computed from what is in
   the feed, so nothing has to keep a second severity variable in sync with the
   list — and there is no state where the dot disagrees with the items.

## Surface

| Function | Answers |
|---|---|
| `nt_post` | add a notification; dedupe and capacity are applied here |
| `nt_dismiss` | close one, keeping the dismissal record |
| `nt_count`, `nt_id_at`, `nt_sev_at`, `nt_when_at`, `nt_text_at`, `nt_source_at` | the feed in order |
| `nt_unread` | how many are newer than a `since_id` |
| `nt_worst` | the severity the bar dot should show |
| `nt_fetch` | the feed as text after a `since_id` |
| `nt_refusal_total`, `nt_duplicate_total`, `nt_dismissal_total` | the three counters |
| `nt_sev_name` | the severity as a printable word |

## Where the proof is

`services/tests/t95_notify.goose` — dedupe, refusal at capacity, and a dismissal
that frees the slot while leaving its record behind.
