# `dashboard` — failure drill (B153)

A drill another agent can run. It changes only a scratch copy or a
temporary test input; it never edits the committed fixtures.

Precondition: a machine with `cargo` (single crate, `-j1`; the lane
rule forbids a workspace build).

## Step 0 — baseline

```sh
cargo test -p dashboard -j1
```

Expected: the 7 in-file unit tests, the 4 existing parity files
(`b15_parity`, `b15_crewboard`, `b15_spec_notes`,
`b15_rollback_parity`) and this pass's three files all pass. Any
failure here is the first break, before any input is removed.

## Step 1 — remove a fixture (compile-time input stops arriving)

```sh
mv crates/dashboard/fixtures/DASHBOARD_SPEC.md /tmp/DASHBOARD_SPEC.md.bak
cargo test -p dashboard -j1
mv /tmp/DASHBOARD_SPEC.md.bak crates/dashboard/fixtures/DASHBOARD_SPEC.md
```

Expected: the test target fails to compile with an `include_str!`
error naming `../fixtures/DASHBOARD_SPEC.md`. The crate library itself
still compiles; only the tests that read the document break. This is
the **first** thing that breaks, because the fixtures are the crate's
only external input.

## Step 2 — starve the runbook check

In a scratch copy of a runbook string, delete the word `Deployments`:

```rust
assert_eq!(
    rollback_runbook_ok("All deployments Rollback to this deployment …"),
    Err("missing rollback step: Deployments".to_string())
);
```

Expected: the first missing item is named, and no later rule is
reported. Removing the docs URL instead yields
`missing official docs citation`; removing the id field yields
`previous deployment id not explicitly addressed`.

## Step 3 — malformed brief record

```rust
let mut p = good_payload();
p.kind = "evening".into();
assert_eq!(validate_brief_payload(&p), Err("bad brief kind: evening".to_string()));
```

Expected: refused with the kind named. A matching kind but a
mismatched id yields `bad brief id: …`; an empty room or a negative
timestamp yields `bad brief timestamps`.

## Step 4 — lifecycle out of order

Acknowledge a resolved alert, then resolve it again:

Expected, in order: `LifecycleResult::RefusedResolved`, then
`LifecycleResult::AlreadyResolved`. Re-acknowledging an already
acknowledged alert returns `AlreadyAcknowledged` and does **not**
re-stamp `acknowledged_at`.

## Step 5 — empty inputs

`alerts_feed(Vec::new())` returns an empty vector;
`count_today_records(&[], &[], None, &[], now)` returns
`TodayCounts { 0, 0, 0, 0 }`; `files_line(Some(""))` and
`deps_line(Some(" , "))` return `None`. No panic, no placeholder row.

## What breaks first, and what cannot break

The crate has no runtime inputs, so there is no degradation ladder
inside it: nothing polls, nothing times out, nothing goes stale on its
own. The failure order is:

1. **Compile time** — a missing fixture or a changed public signature
   stops the test target (Step 1).
2. **Call boundary** — a caller that omits `now` cannot compile;
   time is never read from a clock.
3. **Value validation** — malformed records are refused by the
   functions in the refusal table in `dashboard.md`.
4. **Panic** — `wcag_luminance` on a colour shorter than `#rrggbb`
   (pinned by `error_paths.rs`). That is the only known panic path.

A caller that stops sending data does not make this crate unhealthy;
it simply stops calling it.
