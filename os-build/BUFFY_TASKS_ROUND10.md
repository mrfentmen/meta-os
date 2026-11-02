# BUFFY TASKS — ROUND 10: THE DEEP QUEUE (Pax order, 2026-11-02)

This round is the feeder: it starts only when the Round 9
blockers are green (B2.6 with evidence, D1 on Nuntius, fresh
branch). Then it runs until it is done — when a section closes,
the next one is already written here. Same rules: checkpoints
on room 1 per section, records in os-build/layer1/, Pax merges
at checkpoints, no boot claims — host runs are host runs.

## A. Every service, deepened for real

The 25 Goose services exist and run. Now each one gets its
full depth, one at a time, in registry order: every limit
named in its COUNTS entry closed individually with the test
that proves it, error paths exercised (bad input, missing
dependency, killed mid-call), and the service README updated
to what the code actually does. A service is done when its
limits list is empty, not when the round says so.

## B. The everyday apps as real programs

L6 is Lobster (APP_LANGUAGES.md). Build the everyday apps as
real Lobster programs running against the merged services on
the Round 8 host: Files, Notes, Calendar, Calculator,
Settings, Trash. Each app: the program, its service calls
traced in a drill log, its failure behaviour when a service
is down (named, tested). The face HTML versions are the look;
these are the programs behind the look.

## C. The hosted loops, for real

The registry's placeholder commands become the real loops,
one per drill: Imperium patrol (against the queue), Musica
studio keeper, Officina faber, the cadence watch, Aegis
sweep, Nervus stub-runner. Each: spawned by the runtime,
killed gracefully and hard, restarted by the supervisor,
ledger lines proving every transition. An agent that cannot
show its ledger lines is not hosted, whatever its code says.

## D. Meta Nervus — host-side prep

The bench's patient work, host lane (the reproduction run
stays with the machine that holds the model):
- D1. The model inspector: reads a local model directory —
  config, layer count, tensor inventory, weight footprint —
  and writes the patient record. Tested on a tiny fixture
  model directory built for the purpose.
- D2. The reduction planner: from a layer map (the contract
  records from Round 9 C), produce a prune/quantise PLAN —
  what would be cut, in what order, with the before/after
  evaluation the plan requires before any cut is kept. Plans
  and records only; no model is modified in this round.

## E. Science Lab — the services under Milo's records

Milo's W2 defines the lab's records and the evidence ladder.
Build the services underneath: the experiment record store
(every record hash + seed stamped, append-only), the ladder
enforcer (a record without its level, or claiming above its
evidence, fails validation), and the verification queue the
Independent Verification agent draws from. Contract first,
from Milo's record shapes — if a shape is missing, ask on
room 1, do not invent one.

## F. The chaos pack

Failure-injection suites across the whole services corpus:
kill a dependency mid-call, feed the malformed input, fill
the disk the ledger writes to, stop the clock the budgets
read. Every suite names what it broke and what the service
did. Failures found are findings, filed as records — a chaos
run that breaks nothing is reported as exactly that.

## Order

A, then B, then C, then D, E, F. Checkpoint per section.
When this queue empties, Pax writes the next one — the work
does not wait for a new order.
