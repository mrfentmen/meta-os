# Redis-outage drill: INT-009 (Pax, 2026-10-27)

Script: `intel/redis_down_drill.py`. Transcript:
`intel/evals/redis_down.log`. Tests:
`tests/test_intel_redis_down.py`.

Run it (from the repo root):

```
python3 intel/redis_down_drill.py
```

The drill, in order: it points the shipped CLI at a
closed localhost port (MUSE_RELAY_URL http://127.0.0.1:9,
a dummy token file that is removed when the drill
finishes), then runs every intel command against that
dead store. The precondition stage proves the store is
really down: the shipped relay_common.api_get raises
RuntimeError (curl rc=7, connection refused, after 4
attempts), not a stubbed failure.

## Results from the landing run

| Command | Store down gives | Engaged |
| --- | --- | --- |
| snapshot | RELAY_ERROR, exit 2, empty stdout, no traceback | Yes, already clean before INT-009 |
| brief --morning (store path) | RELAY_ERROR, exit 2, empty stdout, no traceback | Yes, INT-009 fix |
| brief --morning --dry-run | Exit 0, TEMPLATE brief | Correct, store-free by dry run |
| brief --list | RELAY_ERROR, exit 2, empty stdout, no traceback | Yes, INT-009 fix |
| brief --show | RELAY_ERROR, exit 2, empty stdout, no traceback | Yes, INT-009 fix |
| dispatch --show | RELAY_ERROR, exit 2, empty stdout, no traceback | Yes, INT-009 fix |
| dispatch --undo | RELAY_ERROR, exit 2, empty stdout, no traceback | Yes, INT-009 fix |
| dispatch posting (--approve, demo plan) | RELAY_ERROR, exit 2, stderr names that no dispatch record was stored | Yes, already clean before INT-009 |
| dispatch --dry-run | Exit 0, plan renders | Correct, pure validation, no store touch |
| alerts --show | RELAY_ERROR, exit 2, empty stdout, no traceback | Yes, already clean before INT-009 |
| alerts query (--room --since) | RELAY_ERROR, exit 2, empty stdout, no traceback | Yes, already clean before INT-009 |
| watch | RELAY_ERROR UNIMPLEMENTED, exit 2 | Pre-existing stub, not a Redis failure |
| watchdog engine | Tick still returns the progress-stall alert with no store wired in; write_alert raises RuntimeError, caught | Yes, detection pure, writes fail loudly |

## What changed to make the drill pass

Five CLI paths let a store failure escape as a Python
traceback before this batch: brief generation (morning,
ondemand, boot), brief --list, brief --show, dispatch
--show, and dispatch --undo. Each caught only its own
narrow error type (ValueError, ShowError, UndoError) and
let the RuntimeError from relay_common through. INT-009
adds a generic Exception handler after the narrow ones
on each of those five paths, printing RELAY_ERROR with
exit 2, matching the snapshot and alerts paths, which
already had it. No engine changed: engines raising is
correct, and the CLI is the surface that must never
trace.

Two commands succeed during the outage, and both are
correct, not gaps. A dry-run morning brief stores nothing
and the BRF-028 guard fails open on a dead store, so it
is store-free in effect and exits 0 with a template
brief. A dispatch dry-run is pure validation on the plan
text (DSP-006) and never touches the store, so it renders
the plan. The drill asserts both exits 0, so a future
change that makes either one depend on the store fails
the drill instead of failing silently in an outage.

## What it proves, and what it does not

- Proved: with the store dead, every Redis-dependent
  intel command fails loudly with RELAY_ERROR and exit 2
  and never prints a traceback or partial output, and the
  two store-free commands still succeed.
- Proved: the failure itself is real, not stubbed. The
  precondition stage raises RuntimeError from the shipped
  transport against a closed port (connection refused),
  and the CLI stages run the real intel.py as subprocesses
  against that port.
- Proved: nothing is posted during the drill. The dead
  endpoint answers nothing, so no bus write, job post, or
  dispatch record can complete; the posting stage asserts
  stderr names that no dispatch record was stored.
- Not proved: other failure shapes (slow responses,
  partial reads, a store that answers garbage). The
  transport retries 4 times and then raises, which is the
  shape this drill exercises; a store that answers wrong
  data is a different failure and is not covered here.
- Not proved: the watch route under a real outage. The
  watch subcommand is still the unimplemented stub
  (FND-016), so its RELAY_ERROR is the stub reporting
  itself, not a Redis failure. Wiring watch to Milo's loop
  with the same surface rule is the remaining work, not
  a claim this drill makes.
- Not proved: dashboard rendering in a browser. The
  honest states asserted here are the exact strings the
  dashboard renders verbatim; the viewer panels that
  render them are Rowan's lane, not this drill.
