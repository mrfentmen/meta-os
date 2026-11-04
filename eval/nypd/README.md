# Meta NYPD eval — first slice

The NYPD world pack (`os/worlds/nypd/`) is status `spec` on main:
a definition only — PACK.md plus pack.json, no runtime code at all.
Before this slice, `eval/` had no NYPD harness at all, so there was
no NYPD baseline for "whatever raises eval scores" to be measured
against. This is that first harness. It scores the pack's own
contract — not a real precinct, a real unit, or any live feed.

## What it checks (10 scenarios, all from committed material)

| ID | Check | Source |
| --- | --- | --- |
| NYPD-VAL-01 | Committed validator `os/worlds/validate_pack.py` accepts `os/worlds/nypd/pack.json` (exit 0) | pack.json |
| NYPD-WATCH-01 | 3 watchers, 4 agents, every `serves` entry resolves to a watcher | pack.json |
| NYPD-ALERT-01 | 4 alert kinds, severity/privacy/urgency inside the shared sets, urgency ranks 1–4 exactly once | pack.json |
| NYPD-PRIV-01 | An alert crosses the bus exactly when its privacy class is summary — here, no alert crosses at all | pack.json |
| NYPD-PRIV-02 | All 3 cross-world sends declare a non-empty `never_carries` list including case details, suspect or victim names, any personal identifiers, and record contents | pack.json |
| NYPD-XWORLD-01 | Cross-world declarations checked both ways against fdny, ems, hospital packs | pack.json (all four) |
| NYPD-FIRST-01 | 6 firstboot fields, all labelled; 5 required, tour_schedule the only optional field | pack.json |
| NYPD-STATUS-01 | Status honestly `spec`, version 0.1.0; `os/worlds/nypd/` holds PACK.md and pack.json only, no runtime key | pack.json + directory |
| NYPD-PRIVCLASSES-01 | Privacy classes match: 5 local_only items that never move, 3 bus_summary items that may ride | pack.json |
| NYPD-DOC-01 | PACK.md names the same 4 agent nicks, 4 alert kinds, both send kinds, and carries the SPEC, NOT BUILT label | PACK.md |

## The reciprocity gaps (named, not hidden, not patched)

NYPD-XWORLD-01 passes when the measurement matches committed reality:

- Sends, 2/3 reciprocated: ems declares receiving
  `road-closure-summary` from nypd, and fdny declares receiving
  `scene-safety-summary` from nypd.
- NOT reciprocated, send side: `road-closure-summary` to fdny.
  NYPD declares sending it, but the fdny pack declares no
  `road-closure-summary` receive from nypd at all.
- Receives, 0/3 reciprocated: fdny sends
  `incoming-casualty-summary` only to hospital and ems, never to
  nypd; ems sends no `transport-status` to anyone; hospital sends
  `capacity-status` only to ems and fdny, never to nypd.
- Whether any receipt should be dropped, or any source pack should
  add the send, is a pack-owner decision for Pax; this harness does
  not invent either side, and a future change on either side would
  change this scenario's expected values, which is the point of
  measuring it.

Note the mirrors: the FDNY slice found fdny's `transport-status`
receive from ems unreciprocated, and this slice finds the same edge
from the third side — nypd also declares receiving `transport-status`
from ems, and ems declares no such send to anyone. The two packs
that expect that message agree with each other and disagree with
the pack that would have to send it.

## What it never does

- Never dispatches a unit, never orders anyone, never carries case
  information or personal identifiers. Every value read is a pack
  declaration.
- Never calls a live feed, never calls a model. The validator run
  is the only subprocess.
- Never touches a pack file. The read-only guard in
  `adapter.test.mjs` proves `pack.json` is byte-identical after a
  run, and the adapter writes no repo file.
- This is the NYPD world pack (precinct board, roll call, verified
  record), not the Trio Vigiles app: `eval/vigiles/` already covers
  Vigiles, and this slice does not duplicate it.

## Usage

```sh
node eval/nypd/run.mjs            # real run, exit 1 on any failure
node eval/nypd/run.mjs --baseline # label-only fixture, always exit 0
node --test eval/nypd/adapter.test.mjs
```

## Results (from the runs in this slice)

- Real run: 10/10 (exit 0).
- Baseline (label-only reader, claims `spec`, reads nothing): 1/10 —
  only NYPD-STATUS-01, the label row, by chant.
- Adapter tests: 8/8.
- Full package test suite: not run — the change is additive (one new
  eval directory plus one test-script token); the new tests plus both
  runs are the verification for this slice.
