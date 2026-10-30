# Example briefs gallery (DOC-014)

Three real generated briefs, one per room state: quiet, busy, stall.
Each brief below is the exact output of the BRF-008 template
composer (`intel.brief.compose_template_brief`) over a hand-written
snapshot in the same shape as the snapshots in
`tests/test_intel_brief.py`. They are TEMPLATE briefs, not
Spark-composed briefs: the first line of each says TEMPLATE, and no
Spark call was made to produce them.

Honest limits, stated plainly: these snapshots are hand-written,
not Buffy's busy fixture (not in this repo yet), so this gallery
does not prove anything about a Spark-composed brief, and it does
not replace scoring on Buffy's fixture when it lands. Every fact
in each brief traces to its snapshot; nothing was hand-typed into
a brief after generation.

## Quiet — an empty room

Annotation: an empty room is not an error; the brief says so
plainly and invents no job names.

```
TEMPLATE

Window: not stated in this snapshot

no activity yet

This room has no activity yet in this window.
```

## Busy — decisions, owners, one blocked job, one watch item

Annotation: a busy day in one page — two decisions, two owners,
one blocked job with its reason verbatim, one stall alert by id.

```
TEMPLATE
Window: 2026-10-26 08:00 ET onward, last 24 hours

Decisions
- decision: ship the brief panel first
- decision: freeze the demo fixture at noon
- done: watchdog loop passes its checks

In flight
- 2 brief panel (claimed)
- 3 dispatch poster (claimed)

Owners
- rowan: brief panel
- pax: dispatch poster

Blocked and why
- 7 spark client: waiting on the real Spark endpoint

Watch items
- ALERT-1: stall on job 2
```

## Stall — one stalled job, one blocked job, one watch item

Annotation: a stall day reads as a warning, not a status dump —
the blocked reason and the stall alert name the same stuck work.

```
TEMPLATE
Window: 2026-10-26 08:00 ET onward, last 24 hours

Decisions
- decision: hold the watchdog tick until the stall clears

In flight
- 5 watchdog loop (claimed)

Owners
- milo: watchdog loop

Blocked and why
- 9 dispatch poster: waiting on the room owner to approve posting

Watch items
- ALERT-9: stall on job 5, no progress in 90 minutes
```
