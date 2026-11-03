# MT-03 in full detail — Science Lab gateway, live backend (PREP ONLY)

Status: PREP ONLY as of 2026-11-02 22:18 EST. This is a fixture/spec, not a
run. No live-key call has been made from Milo's VM for this slice, no
gateway cycle has been run under MT-03, and nothing below is a pass.
Firing waits on BOTH: (1) Del tops up Meta API billing (HTTP 402 during
Pax's live hunt #3), and (2) Del picks a key route (Route A: key placed
on Milo's VM; Route B: Milo specs, Pax executes the live run and posts
the receipt, Milo verdicts it). Pax confirmed 2026-11-02 22:17 EST that
MT-03 detail comes next as PREP ONLY, $0, no live-key call — prep
continues, it is not held at MT-02, and live-key runs stay held until
Del picks a key route AND the 402 is topped up. Del's 22:17 EST order
that the crew work over blockers and go back later when they are
unblocked points the same way: this prep is written now, the live run
waits for the blockers to clear. Spend cap $10 total for the whole
directive, guardrail-tracked; cost for MT-03 is TBD at fire time from
the published Spark rates, never invented here. Nothing dials a real
service from this prep, ever.

## What the check is

One discovery cycle through the Science Lab gateway on the live backend,
with a real query. Per os-build/MILO_TEST_SLICE.md and
os-build/MILO_TEST_PREP.md, the backend is the MCP-GATEWAY backend
(mcp-gateway/, Pax bench 1). The check is the lab's own discovery cycle
run through its own gateway, not a new path invented for this slice:
the cycle is opened, the query is put to the gateway on the live
backend, and the cycle is carried to its record. A cycle that runs on
any other backend does not satisfy MT-03, and a cycle whose gateway
record names any other backend does not satisfy MT-03.

## The query

The firing run uses one real query — a genuine question put to the
gateway, not a canned string chosen to guarantee an answer. The exact
query text is set at fire time and recorded verbatim in the cycle
record, so the run can be re-read and re-checked. A query written here
in advance would be a placeholder, not a firing input, so none is
claimed here: what this prep fixes is the rule, not the text. The rule
is: one query, recorded verbatim, answered by the live backend, with
the answer filed as it came back — a lead to be checked, never
presented as settled evidence on its own.

## Pass rules

MT-03 passes only when all of these hold on the fired record:

1. The cycle record exists and is findable from MILO_TEST_STATUS.md,
   landed on main by Pax (Route B) or by Milo (Route A), named so the
   check is in the filename.
2. The gateway record exists alongside it and names the backend
   verbatim: "MCP-GATEWAY". A record that names a different backend,
   or that omits the backend name, does not satisfy MT-03.
3. The query is recorded verbatim, and every gateway call in the cycle
   is recorded with its result as it came back — none hidden, none
   smoothed over.
4. A gateway failure, if one happens, is recorded as a failure with
   its cause named. A failed call is never answered with fabricated
   data, never relabelled as a success, and never dropped from the
   record. A run with a hidden failure is BLOCKED (incomplete record)
   or FAIL (result mishandled), never a pass.
5. Spend for the record is stated in actual dollars, and the running
   total against the $10 cap is updated in MILO_TEST_STATUS.md at
   fire time. A record with no spend line is incomplete.

An honest empty or negative answer is a passing shape only if the
cycle ran clean: the query recorded, the gateway record naming
"MCP-GATEWAY", every call filed, every failure named. A run with a
missing record, a missing backend name, a hidden call, or a
fabricated answer is not a pass.

## Run record shape — one cycle record plus one gateway record

One record pair, landed on main by Pax (Route B) or by Milo
(Route A), for example os-build/MILO_TEST_MT03_RECORD.md plus the
gateway's own record file (the exact filenames are set at fire time;
what matters is that both records exist and are findable from
MILO_TEST_STATUS.md). Each record contains, verbatim field names
where the lab already uses them:

- `check`: `"MT-03"`.
- `main_tip`: the origin/main commit the run was fired from.
- `route`: `"A"` or `"B"`, plus who executed the live steps and who
  issued the verdict (Route B: Pax executed, Milo verdicts from the
  receipt; Route A: Milo executed and verdicts).
- `spend_usd`: actual spend for this record; running total against
  the $10 cap is updated in MILO_TEST_STATUS.md at fire time.
- `query`: the real query text, verbatim.
- `backend`: `"MCP-GATEWAY"`, verbatim, on the gateway record and
  repeated on the cycle record. Any other value fails the check.
- `calls`: every gateway call in the cycle, in order, each with its
  result as it came back or its failure with the cause named.
- `outcome`: `"pass"` | `"fail"` | `"partial"` — pass only when
  every rule above holds; partial means the run stopped early (for
  example at a budget stop) and the record says where it stopped and
  what never ran.
- `failures`: every failure named, none hidden.

## Firing steps, by route (same steps, different hands)

Route B (the route that works once credits exist, no key movement):
Pax executes the single discovery cycle on the live backend, posts
the cycle record plus the gateway record naming "MCP-GATEWAY", and
Milo verdicts it against the pass rules above, in his own words, on
room 1 and in MILO_TEST_STATUS.md.

Route A (only after Del places the key on Milo's VM): Milo executes
the same single cycle himself, inside the cap, posts the records,
and verdicts them the same way.

Either route: if the 402 is still present at fire time, the run does
not start; MT-03 stays BLOCKED and the attempt (not a result) is
noted in MILO_TEST_STATUS.md. If the cap is hit mid-cycle, the cycle
stops, the record is marked partial, and the tally is posted to
room 1.

## What this prep does NOT claim

- No MT-03 run has happened. No gateway cycle has been run under
  MT-03, and no gateway record naming "MCP-GATEWAY" exists yet from
  this check.
- No spend has occurred ($0 on this slice). No cost estimate is
  claimed here; cost is TBD at fire time from the published Spark
  rates.
- No query text is fixed here, and no gateway answer is previewed,
  quoted, or assumed.
- The 12-hour brand-kit audit is NOT started here: Pax's 22:17 EST
  note says it still stands by for OC1's kit commit (bond/12h is
  Bond's ISO status doc, not OC1's kit commit). That lane stands by,
  it is not claimed as done.
- This file does not change the slice: MT-04..MT-08 keep their prep
  specs in MILO_TEST_PREP.md, and MT-08 gate duty stays with Milo's
  rust-work loop — this 5-minute job runs no gate-1.
