# Meta EMS eval — first slice

The EMS world pack (`os/worlds/ems/`) is status `spec` on main: a
definition only, no runtime. Before this slice, `eval/` had no EMS
harness at all, so there was no EMS baseline for "whatever raises eval
scores" to be measured against. This is that first harness. It scores
the pack's own contract, not an ambulance, a hospital, or any live feed.

## What it checks (9 scenarios, all from committed material)

| ID | Check | Source |
| --- | --- | --- |
| EMS-VAL-01 | Committed validator `os/worlds/validate_pack.py` accepts `os/worlds/ems/pack.json` (exit 0) | pack.json |
| EMS-WATCH-01 | 3 watchers, 3 agents, every `serves` entry resolves to a watcher | pack.json |
| EMS-ALERT-01 | 4 alert kinds, severity/privacy/urgency inside the shared sets, urgency ranks 1–4 exactly once | pack.json |
| EMS-PRIV-01 | An alert crosses the bus exactly when its privacy class is summary | pack.json |
| EMS-PRIV-02 | All 3 cross-world sends declare a non-empty `never_carries` list including patient names and identifiers | pack.json |
| EMS-XWORLD-01 | Cross-world declarations checked both ways against hospital, fdny, nypd packs | pack.json (all four) |
| EMS-FIRST-01 | 5 firstboot fields, all required with labels | pack.json |
| EMS-STATUS-01 | Status honestly `spec`, version 0.1.0; `os/worlds/ems/` holds only PACK.md and pack.json | pack.json + directory |
| EMS-DOC-01 | PACK.md names the same 3 agent nicks, 4 alert kinds, and the multi-casualty send kind | PACK.md |

## The reciprocity gap (named, not hidden, not patched)

EMS-XWORLD-01 passes when the measurement matches committed reality:

- Receives, 3/3 reciprocated: hospital `capacity-status`, nypd
  `road-closure-summary`, fdny `incoming-casualty-summary` are all
  declared as sends to EMS by their source packs.
- Sends, 1/3 reciprocated: only `incoming-patient-summary` to hospital
  is declared as received by its destination.
- NOT reciprocated: `multi-casualty-summary` to fdny and
  `multi-casualty-summary` to hospital. Neither destination pack
  declares receiving a multi-casualty summary from EMS (fdny declares
  receiving `transport-status` from EMS; hospital declares receiving
  `incoming-patient-summary` from EMS). Whether those receipts should
  be added is a pack-owner decision for Pax; this harness does not
  invent them, and a future receipt would change this scenario's
  expected values, which is the point of measuring it.

## What it never does

- Never dispatches a unit, never moves a patient, never carries patient
  information. Every value read is a pack declaration.
- Never calls a live hospital capacity or diversion feed, never calls
  a model. The validator run is the only subprocess, and it is
  read-only (pure validation, no writes).
- Never touches a pack file. The read-only guard in
  `adapter.test.mjs` proves `pack.json` is byte-identical after a run.
- This is the EMS world pack (ambulance ride), not the Trio Medicus
  app: `eval/medicus/` already covers Medicus scene awareness, and
  this slice does not duplicate it.

## Usage

```sh
node eval/ems/run.mjs            # real run, exit 1 on any failure
node eval/ems/run.mjs --baseline # label-only fixture, always exit 0
node --test eval/ems/adapter.test.mjs
```

## Results (from the runs in this slice)

- Real run: 9/9 (exit 0).
- Baseline (label-only reader, claims `spec`, reads nothing): 1/9 —
  only EMS-STATUS-01, the label row, by chant.
- Adapter tests: 8/8.
- Full package test suite: not run — the change is additive (one new
  eval directory plus one test-script token); the new tests plus both
  runs are the verification for this slice.
