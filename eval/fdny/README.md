# Meta FDNY eval — first slice

The FDNY world pack (`os/worlds/fdny/`) is status `partial` on main:
a definition plus exactly one built runtime, the PAR clock
(`os/worlds/fdny/runtime/par_clock.py`). Before this slice, `eval/`
had no FDNY harness at all, so there was no FDNY baseline for
"whatever raises eval scores" to be measured against. This is that
first harness. It scores the pack's own contract plus a real smoke
run of the one runtime that ships — not a real fireground, a real
station, or any live feed.

## What it checks (11 scenarios, all from committed material)

| ID | Check | Source |
| --- | --- | --- |
| FDNY-VAL-01 | Committed validator `os/worlds/validate_pack.py` accepts `os/worlds/fdny/pack.json` (exit 0) | pack.json |
| FDNY-WATCH-01 | 4 watchers, 4 agents, every `serves` entry resolves to a watcher | pack.json |
| FDNY-ALERT-01 | 4 alert kinds, severity/privacy/urgency inside the shared sets, urgency ranks 1–4 exactly once | pack.json |
| FDNY-PRIV-01 | An alert crosses the bus exactly when its privacy class is summary | pack.json |
| FDNY-PRIV-02 | Both cross-world sends declare a non-empty `never_carries` list including patient names, patient identifiers, member names, and medical details of any individual | pack.json |
| FDNY-XWORLD-01 | Cross-world declarations checked both ways against hospital, ems, nypd packs | pack.json (all four) |
| FDNY-FIRST-01 | 7 firstboot fields, all labelled; 6 required, battalion the only optional field | pack.json |
| FDNY-STATUS-01 | Status honestly `partial`, version 0.1.0; `os/worlds/fdny/` holds PACK.md, pack.json, and runtime/ | pack.json + directory |
| FDNY-RUNTIME-01 | The one declared runtime part exists on disk (pack.json paths are relative to `os/`, so `worlds/fdny/runtime/par_clock.py` resolves under `os/`) | pack.json + disk |
| FDNY-PAR-01 | PAR clock smoke with its own `--now` fake clock, in a temp dir only: enter a crew at 1000, par-check-due warning at 1700 (no ALERT line), crew-unaccounted critical plus the frozen FND-020 `ALERT:` line at 1800, silent repeat tick (dedupe) | par_clock.py |
| FDNY-DOC-01 | PACK.md names the same 4 agent nicks, 4 alert kinds, and the incoming-casualty-summary send kind | PACK.md |

## The reciprocity gap (named, not hidden, not patched)

FDNY-XWORLD-01 passes when the measurement matches committed reality:

- Sends, 2/2 reciprocated: hospital and ems both declare receiving
  `incoming-casualty-summary` from fdny.
- Receives, 2/3 reciprocated: hospital `capacity-status` and nypd
  `scene-safety-summary` are both declared as sends to fdny by their
  source packs.
- NOT reciprocated: `transport-status` from ems. FDNY declares
  receiving it, but the ems pack declares no `transport-status` send
  to fdny at all — ems sends `multi-casualty-summary` to fdny
  instead, and `transport-status` only to nypd. Whether that receipt
  should be dropped, or ems should add the send, is a pack-owner
  decision for Pax; this harness does not invent either side, and a
  future change on either side would change this scenario's
  expected values, which is the point of measuring it.

Note the mirror: the EMS slice found ems's `multi-casualty-summary`
sends to fdny unreciprocated, and this slice finds fdny's
`transport-status` receive from ems unreciprocated. The two packs
disagree about the same cross-world edge, in opposite directions.

## What it never does

- Never dispatches a unit, never orders a crew, never carries member
  or patient information. Every value read is a pack declaration,
  and the smoke test's only identifiers are a fixture crew id in a
  temporary state file that is deleted after the run.
- Never calls a live feed, never calls a model. The validator run
  and the PAR clock smoke are the only subprocesses; the clock run
  uses its own `--now` fake clock, so it is deterministic.
- Never touches a pack file. The read-only guard in
  `adapter.test.mjs` proves `pack.json` is byte-identical after a
  run, and the adapter writes no repo file (its only writes are
  the clock's temp-dir state file).
- This is the FDNY world pack (fire-department accountability), not
  the Trio Ignis app: `eval/ignis/` already covers Ignis scene
  awareness, and this slice does not duplicate it. The PAR clock is
  an accountability aid, not a commander: it completes a PAR only
  when a human says so, and it never invents a location.

## Usage

```sh
node eval/fdny/run.mjs            # real run, exit 1 on any failure
node eval/fdny/run.mjs --baseline # label-only fixture, always exit 0
node --test eval/fdny/adapter.test.mjs
```

## Results (from the runs in this slice)

- Real run: 11/11 (exit 0).
- Baseline (label-only reader, claims `partial`, reads nothing): 1/11 —
  only FDNY-STATUS-01, the label row, by chant.
- Adapter tests: 9/9.
- Full package test suite: not run — the change is additive (one new
  eval directory plus one test-script token); the new tests plus both
  runs are the verification for this slice.
- One harness bug was caught by the first run and fixed in the
  harness, not the pack: the PAR clock's event field is `crew`, not
  `crew_id`. After the fix the smoke passes unchanged on the clock.
