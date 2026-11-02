# Hana tasks — Round 4 (the 72-hour window)

From Pax, 2026-11-01 ~20:30 EST. Boss order: 72-hour all-in
window, everything substantive in the next 24 hours. Your
12-hour lane (H-1 to H-5 in os-build/PAX_12H.md) stands and is
the base of this set. Branch: `hana/os-shell`. Milo gates,
Pax merges.

## HN4-1 — shell-spec.md, complete (your H-1 to H-4)

`os-build/shell-spec.md`: the frozen F2 strings (banner, prompt,
status fields, unknown-command error), the 8-command surface with
exact output for each command, prompt behaviour before/during/
after a command, and the claim-sentence demo retyped line for
line as the acceptance script Rowan and OpenCode build against.
This spec unblocks Rowan's RW4-2 — it is the critical path item
in your lane, first.

## HN4-2 — Imperium dispatch card (UI half of auto-dispatch)

The product change on main (docs/IMPERIUM_AUTO_DISPATCH.md): on
RED, the agent sends the package itself, picture included. The
incident card must show it honestly: package sent, picture
attached, receipt id, and the SIMULATED label on the dispatch
line. No "awaiting verification" state in the flow; human review
reads as post-hoc audit in the record. Match the field names the
backend lands (coordinate in room 1 when its branch posts).

## HN4-3 — Site copy for the claim sentence

Refresh `site/index.html` statuses to the adopted claim and the
weekend's verified state: OS boots and runs ring 3 (proven, log
named), services source-only, board merged, Imperium dispatch
doctrine stated plainly. No claim without a log or a merge hash
behind it. Pax redeploys after merge.

## HN4-4 — Demo script and shot list

`os-build/DEMO_SCRIPT.md`: the 3-minute submission video as a
timed script — OS boot to ring 3 and the shell first, then
Imperium (patrol, flag, investigation, the agent sending the
dispatch package itself), then the board. Every shot names the
real screen or log it captures. Script only; no render in this
task.

## HN4-5 — Native test updates, prepared not landed

For the 38 UPDATE-classified native tests in
docs/NATIVE_TEST_PREP.md, prepare the update patches on your
branch so they are ready the moment the boss rules update vs
carve-out. Do not land them, and do not touch the 18 carve-out
class. Report which files the patches cover.

## Rules

Status words exactly VERIFIED / CODE-INSPECTED / UNIMPLEMENTED /
BLOCKED, with the evidence named. Home-surface mock stays static
and labelled MOCK. Hard freeze at H+9 of the 12-hour clock
(05:12 EST) applies to feature work; gate fixes only after.
