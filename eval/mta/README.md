# Meta MTA eval — first slice

The MTA world pack (`os/worlds/mta/`) is status `spec` on main:
a definition only — PACK.md plus pack.json, no runtime code at all.
Before this slice, `eval/` had no MTA harness at all, so there was
no MTA baseline for "whatever raises eval scores" to be measured
against. This is that first harness. It scores the pack's own
contract — not a real transit system, a real train, or any live feed.

## What it checks (11 scenarios, all from committed material)

| ID | Check | Source |
| --- | --- | --- |
| MTA-VAL-01 | Committed validator `os/worlds/validate_pack.py` accepts `os/worlds/mta/pack.json` (exit 0) | pack.json |
| MTA-WATCH-01 | 4 watchers, 5 agents, every `serves` entry resolves to a watcher | pack.json |
| MTA-ALERT-01 | 6 alert kinds, severity/privacy/urgency inside the shared sets, urgency ranks 1–4 exactly once | pack.json |
| MTA-PRIV-01 | An alert crosses the bus exactly when its privacy class is summary — here, only incident-casualty-summary and service-status-summary cross | pack.json |
| MTA-PRIV-02 | All 3 cross-world sends declare a non-empty `never_carries` list including rider names, worker names, and crew rosters and overtime records | pack.json |
| MTA-XWORLD-01 | Cross-world declarations checked both ways against nypd, fdny, ems, dsny, doe, dep, hospital packs | pack.json (all eight) |
| MTA-XWORLD-02 | Other packs' mta declarations checked for a matching mta side | pack.json (all eight) |
| MTA-FIRST-01 | 6 firstboot fields, all labelled; all 6 required, none optional | pack.json |
| MTA-STATUS-01 | Status honestly `spec`, version 0.1.0; `os/worlds/mta/` holds PACK.md and pack.json only, no runtime key | pack.json + directory |
| MTA-PRIVCLASSES-01 | Privacy classes match: 4 local_only items that never move, 3 bus_summary items that may ride | pack.json |
| MTA-DOC-01 | PACK.md names the same 5 agent nicks, 6 alert kinds, both send kinds, and carries the SPEC, NOT BUILT label | PACK.md |

## The cross-world picture (named, not hidden, not patched)

MTA-XWORLD-01 passes when the measurement matches committed reality,
and on the mta pack's own declarations that reality is gappy:

- Receives, 2/3 reciprocated: dsny sends `road-clearing-status` to
  mta, and dep sends `water-advisory` to mta. The third receive is
  unreciprocated: mta declares receiving `scene-safety-summary` from
  nypd, but the nypd pack declares no `scene-safety-summary` send to
  mta at all.
- Sends, 0/3 reciprocated: no destination pack declares receiving
  `incident-casualty-summary` from mta (neither ems nor nypd), and
  dsny declares no `service-status-summary` receive from mta — its
  mta receive is `service-diversion` instead (see below).

MTA-XWORLD-02 looks from the other side, and that is where the
remaining gaps sit:

- Unmatched inbound: none. Every send addressed to mta has a
  matching mta receive (dep `water-advisory`, dsny
  `road-clearing-status`).
- Unmatched outbound: doe and dsny both declare receiving
  `service-diversion` from mta, but the mta pack declares no
  `service-diversion` send to either — its dsny send is
  `service-status-summary`, and it declares no doe send at all.
- Whether receipts should be added, or source packs should drop or
  redirect their sends, is a pack-owner decision for Pax; this
  harness does not invent either side, and a future change on either
  side would change these scenarios' expected values, which is the
  point of measuring them.

One wording variance, noted not smoothed over: the ems and nypd
sends never carry "images or video of the scene", while the dsny
send never carries "images or video". The check requires only the
three wordings all three sends share (rider names, worker names,
crew rosters and overtime records); unifying the imagery wording is
a pack-owner call.

## What it never does

- Never runs a transit system, never carries rider or worker
  information or personal identifiers. Every value read is a pack
  declaration.
- Never calls a live feed, never calls a model. The validator run
  is the only subprocess.
- Never touches a pack file. The read-only guard in
  `adapter.test.mjs` proves `pack.json` is byte-identical after a
  run, and the adapter writes no repo file.

## Usage

```sh
node eval/mta/run.mjs            # real run, exit 1 on any failure
node eval/mta/run.mjs --baseline # label-only fixture, always exit 0
node --test eval/mta/adapter.test.mjs
```

## Results (from the runs in this slice)

- Real run: 11/11 (exit 0).
- Baseline (label-only reader, claims `spec`, reads nothing): 1/11 —
  only MTA-STATUS-01, the label row, by chant.
- Adapter tests: 9/9.
- Full package test suite: not run — the change is additive (one new
  eval directory plus one test-script token); the new tests plus both
  runs are the verification for this slice.
