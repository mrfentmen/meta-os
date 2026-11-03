# Meta Hospital eval — first slice

The Hospital world pack (`os/worlds/hospital/`) is status `spec` on main:
a definition only — PACK.md plus pack.json, no runtime code at all.
Before this slice, `eval/` had no Hospital harness at all, so there was
no Hospital baseline for "whatever raises eval scores" to be measured
against. This is that first harness. It scores the pack's own
contract — not a real ward, a real patient, or any live feed.

## What it checks (11 scenarios, all from committed material)

| ID | Check | Source |
| --- | --- | --- |
| HOSP-VAL-01 | Committed validator `os/worlds/validate_pack.py` accepts `os/worlds/hospital/pack.json` (exit 0) | pack.json |
| HOSP-WATCH-01 | 4 watchers, 5 agents, every `serves` entry resolves to a watcher | pack.json |
| HOSP-ALERT-01 | 7 alert kinds, severity/privacy/urgency inside the shared sets, urgency ranks 1–4 exactly once | pack.json |
| HOSP-PRIV-01 | An alert crosses the bus exactly when its privacy class is summary — here, only diversion-status-change crosses | pack.json |
| HOSP-PRIV-02 | Both cross-world sends declare a non-empty `never_carries` list including patient names, patient identifiers, diagnoses of any individual, and images or video | pack.json |
| HOSP-XWORLD-01 | Cross-world declarations checked both ways against nypd, fdny, ems packs | pack.json (all four) |
| HOSP-XWORLD-02 | Other packs' hospital declarations checked for a matching hospital side | pack.json (all four) |
| HOSP-FIRST-01 | 6 firstboot fields, all labelled; all 6 required, none optional | pack.json |
| HOSP-STATUS-01 | Status honestly `spec`, version 0.1.0; `os/worlds/hospital/` holds PACK.md and pack.json only, no runtime key | pack.json + directory |
| HOSP-PRIVCLASSES-01 | Privacy classes match: 6 local_only items that never move, 3 bus_summary items that may ride | pack.json |
| HOSP-DOC-01 | PACK.md names the same 5 agent nicks, 7 alert kinds, the capacity-status send kind, and carries the SPEC, NOT BUILT label | PACK.md |

## The cross-world picture (named, not hidden, not patched)

HOSP-XWORLD-01 passes when the measurement matches committed reality,
and on the hospital pack's own declarations it is clean:

- Sends, 2/2 reciprocated: ems declares receiving `capacity-status`
  from hospital, and fdny declares receiving `capacity-status` from
  hospital.
- Receives, 2/2 reciprocated: ems sends `incoming-patient-summary`
  to hospital, and fdny sends `incoming-casualty-summary` to hospital.

HOSP-XWORLD-02 looks from the other side, and that is where the gaps
sit:

- Unmatched inbound: ems sends `multi-casualty-summary` to hospital,
  but the hospital pack declares no `multi-casualty-summary` receive
  from ems at all. Hospital's declared ems receive is
  `incoming-patient-summary` only.
- Unmatched outbound expectation: nypd declares receiving
  `capacity-status` from hospital, but the hospital pack declares no
  `capacity-status` send to nypd — its capacity-status sends go to ems
  and fdny only.
- Whether a receipt should be added, or a source pack should drop or
  redirect its send, is a pack-owner decision for Pax; this harness
  does not invent either side, and a future change on either side
  would change this scenario's expected values, which is the point
  of measuring it.

Note the mirror: the NYPD slice found nypd's `capacity-status`
receive from hospital unreciprocated, and this slice finds the same
edge from the hospital side — nypd expects that message, hospital
does not declare sending it there.

## What it never does

- Never watches a patient, never carries patient information or
  personal identifiers. Every value read is a pack declaration.
- Never calls a live feed, never calls a model. The validator run
  is the only subprocess.
- Never touches a pack file. The read-only guard in
  `adapter.test.mjs` proves `pack.json` is byte-identical after a
  run, and the adapter writes no repo file.
- This is the Hospital world pack (IV guardian, turn watcher, waiting
  room watcher, code recorder), not the Trio Medicus app:
  `eval/medicus/` already covers Medicus, and this slice does not
  duplicate it.

## Usage

```sh
node eval/hospital/run.mjs            # real run, exit 1 on any failure
node eval/hospital/run.mjs --baseline # label-only fixture, always exit 0
node --test eval/hospital/adapter.test.mjs
```

## Results (from the runs in this slice)

- Real run: 11/11 (exit 0).
- Baseline (label-only reader, claims `spec`, reads nothing): 1/11 —
  only HOSP-STATUS-01, the label row, by chant.
- Adapter tests: 9/9.
- Full package test suite: not run — the change is additive (one new
  eval directory plus one test-script token); the new tests plus both
  runs are the verification for this slice.
