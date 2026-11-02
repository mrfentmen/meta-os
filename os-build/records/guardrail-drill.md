# crates/guardrail — failure drill (B165)

Question the drill answers: when the guardrail's inputs stop arriving,
what breaks FIRST? Written from the code, runnable by another agent on
a light machine. It uses one crate test build (`-j1`), no workspace
build, no network.

Setup (once):

```bash
cd "$(git rev-parse --show-toplevel)"
cargo test -p guardrail --no-run -j1
LEDGER="$(mktemp /tmp/guardrail-drill-XXXXXX.json)"
rm -f "$LEDGER"        # start with no ledger at all
```

## D1 — token usage stops arriving (the realistic first failure)

1. Call `record(ledger, "assess:ignis", "muse-spark-1.3", 0, 0, 40)`.
2. Call `check(&load_state(ledger))`.

**Expected order of breakage:** `calls` increments to 1 and the log gets
a row, but `est_cost_usd` stays `0.0` (`lib.rs:88-99`), so `check`
returns `Ok(())` (`lib.rs:70-78`). First visible symptom is a ledger
whose `calls` keeps rising while `est_cost_usd` is flat: the cap is
disarmed while looking healthy. A caller that silently normalises a
missing `usage` to zero produces exactly this.

## D2 — the ledger is corrupt (second, and worse)

1. Write `not json` into `$LEDGER`.
2. `check(&load_state(ledger))`.

**Expected:** `load_state` returns `Default` (`lib.rs:57-62`), so the
check passes at $0 spend even if the previous file recorded $74.99.
Python raises here; the Rust port forgets the spend. This is the first
break when the file is truncated mid-write.

## D3 — the ledger is unwritable

1. Point the path at a directory that does not exist, e.g.
   `/guardrail-no-such-dir/ledger.json`.
2. `record(path, ...)` then `load_state(path)`.

**Expected:** `record` returns the estimate and does NOT panic; the save
is discarded (`save_state`, 64-68), the file is never created, and the
next `load_state` is a fresh zero ledger. The call is sent and never
counted.

## D4 — `check` is never called (ordering failure)

**Expected:** the crate is passive; nothing refuses on its own. A
caller that records after the send but checks never, or checks after
the send, spends first and asks later. The crate cannot detect misuse.

## D5 — the budget is reached

1. Write `{"calls":1,"est_cost_usd":75.0,"log":[]}` into `$LEDGER`.
2. `check(&load_state(ledger))`.

**Expected:** `Err` from `check` (70-78, message built at 72-76) with exactly

```
GUARDRAIL STOP: estimated test spend $75.0000 has reached the $75.00 test budget. No call sent.
```

No network send happens in this crate at all; the caller must stop.

## D6 — time stops being usable

**Expected:** every row's `ts` is `2026-10-30T00:00:00Z` (`lib.rs:92`).
Ordering by timestamp is meaningless; only array order tells you the
call sequence. Any spend report grouped by day collapses into one day.

## What breaks first, in one line

The money counter: `calls` rises, `est_cost_usd` does not, because a
missing usage map or a damaged ledger both resolve to zero before
`check` ever runs.
