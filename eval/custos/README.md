# Meta Custos eval — first slice

Custos was already built and pinning-tested on main (os/worlds/custos/
runtime/patrol.py, scheduler.py, dedup.py, false_positives.py, and
tests/custos/ — 125 tests) but eval/ had no custos harness, so there
was no Custos baseline for "whatever raises eval scores" to be
measured against. This is that first harness: a replay of the
patrol's own rules through the real code.

## What it scores: the patrol's own rules, not a live patrol

| source | what the harness checks |
|---|---|
| PACK.md KEV watcher + committed runs/patrol-001.jsonl | a match against the configured inventory is red and escalates to the labelled SIMULATED endpoint only, with steps record/notify/page/ticket |
| tests/custos seen-state claim | a matched CVE, and a seen CT id, are never re-recorded on a later patrol with the same state |
| PACK.md KEV ageing (RW-006) | matches sort oldest listing first and carry days_since_listing plus the aged flag at the 30-day threshold |
| PACK.md CT watcher + runs/patrol-002.jsonl shape | a new CT entry for a watched domain is yellow certificate-issued, never an escalation |
| PACK.md DNS drift | first sighting is silent; a later change is yellow dns-drift carrying the added/removed diff |
| PACK.md false-positive log (RW-009) | a dismissed finding becomes a dismissed audit record, never re-raises, never escalates |
| PACK.md certificate watcher | days remaining fall on the right side of the tier boundary: 10 days expiring (yellow), negative expired (red), 90 days baseline |
| PACK.md service watch | an undeclared sensitive port is yellow; a down service is red and escalates |
| patrol.py SECURITY_HEADERS | missing headers are a yellow record carrying the missing list; all five present is baseline |
| patrol.py DEFAULT_TLS_BASELINE (min TLSv1.2) | a posture below baseline is yellow drift; a strong posture is baseline |
| PACK.md subdomain sweep | a subdomain outside its expected networks is yellow; inside is baseline |
| PACK.md alert dedup (RW-008) + hosts.example.json 24h window | an identical yellow finding inside the window is suppressed on the repeat patrol |
| PACK.md scheduling (RW-007) + runs/scheduler-cycle-proof.jsonl | a cycle runs due sources; the immediate next cycle runs nothing but still writes its cycle record |
| os/worlds/validate_pack.py + pack.json | the manifest passes the world validator and every cross-world send declares a non-empty never_carries list |

## What it is not

- Not a live patrol. No watched host is probed, no real KEV/CT/DNS
  feed is fetched, nothing is patched, restarted, or reconfigured.
  CLI scenarios use fixture feeds and tmp state dirs; host scenarios
  run patrol.run_patrol through eval/custos/probe_driver.py with
  every signal injected — the same method tests/custos/ uses — and
  their evidence says "injected probes" so the two kinds are never
  confused.
- Not an escalation to a real responder. Stage 1 ends at the labelled
  SIMULATED endpoint; the harness asserts that, and asserts yellow
  observations produce zero escalation records.
- Not a registry check. Custos has no agents/registry.json entry on
  main: its pack agents (patrol-runner, watch-scribe,
  escalation-messenger) are not registry agents. That gap is noted
  here, not scored, and no registry entry was invented to make a
  scenario pass.
- Not a rewrite of the committed record. runs/ is never written by
  this harness; adapter.test.mjs proves it byte-identical before and
  after a run.

## How to run

```
node eval/custos/run.mjs            # real patrol code, exits 1 on any fail
node eval/custos/run.mjs --baseline # empty-outcome fixture, always exits 0
node --test eval/custos/adapter.test.mjs
```

## Baseline: the empty-outcome reader

A fixture that predicts nothing happened for every scenario. It passes
exactly the one scenario whose honest answer IS the empty outcome
(CU-EMPTY-01) and fails every scenario that requires a real patrol
record: 1/16. An empty outcome is not a verification. The real run
passes 16/16 by running the patrol code; see baseline-run-report.md
for the baseline table.

## Results (this slice, main af457ebd)

- Real run: 16/16 (exit 0).
- Baseline: 1/16 (the empty row by chant).
- Adapter tests: 5/5.
- Existing Custos pinning tests still pass: 125/125 (no custos
  runtime file was touched; this slice only adds eval/custos/ and
  one test-script token).
