# BUFFY TASKS — ROUND 9 (Pax order, 2026-11-02)

Round 8 checkpoint is merged (65 files, tree-verified). Pax ran
the merged-tree tests: 62/63. Round 9 opens with the one failure,
then builds the two systems the boss lit up this morning:
Aegis for real, and Meta Nervus's first slice. Same rules as
always: branch buffy/round9 (or buffy/layer1-goose-services for
service work), records in os-build/layer1/, call the checkpoint
per section on room 1, Pax merges code at checkpoints, no boot
claims — host runs are host runs.

## A. Close the B2.6 failure (yours, named at the merge)

tests/agents-bridge.test.mjs B2.6: after a budget kill the
bridge still reports the agent 'running'; the test expects
'stopped'. Answer with evidence whether it is a race in the
test or a real status bug in the bridge, fix the guilty side,
and show the test green on the merged tree shape (Pax re-runs
it at your checkpoint).

## B. Aegis — run the first real sweep

The service pack landed in Round 8 (aegis/*.mjs + tests). Now
the sweep itself:
- B1. Sweep v1 over the meta-os tree's package manifests +
  shipped MCP manifests, OSV via the boss's own osv server;
  findings as records (severity, evidence, ledger lines);
  report under os-build/aegis/. Zero findings is a valid
  result — report zero, never pad.
- B2. Secret-hygiene count over the meta-os tree (counts only,
  never values) into the same report.
- B3. OSINT v1 (spec: AEGIS_SPEC wings): certificate-
  transparency + DNS review over the boss's named domains
  (meta-os.pages.dev, muse-relay-live.pages.dev,
  clipraiders.com, watchpeoplefight.com); public records only;
  exposures as counts + locations, never republished values.
- B4. OPSEC v1: write the pre-publish checklist from the spec,
  then RUN it over the hackathon submission materials (demo
  script, site copy, README) and file the findings as records.
  Deadline-shaped: the submission goes out Nov 4.

## C. Meta Nervus — first slice (standalone system, boss-named)

Spec: os-build/NEURON_SURGERY_SPEC.md. Build the contract
layer only — the reproduction run belongs to the machine with
the model, not this lane.
- C1. Tool contracts for the five operations (sweep, steer,
  ablate, evaluate-delta, map-layers): inputs, outputs, the
  ledger record shape (model hash, layer, neuron, dose, probe,
  result) — as schemas + contract tests with a stub runner
  clearly labelled stub.
- C2. The instrument-tray manifest: the boss's existing tools
  (per the spec's tray list) as a machine-readable manifest
  the bench loads — name, gateway prefix, bench job. Validate
  every named tool exists in the gateway's backend list; a
  named tool that does not exist is a finding, not a footnote.
- C3. The dose-window and probe-dependence rules as executable
  contract checks (a record missing its probe fails validation;
  a steer record without its dose zone fails validation).

## D. Agent layer — the two standing TODOs

- D1. Watchman listens to crew room 1: a job file can arrive
  from the bus (orders posted as job JSON), claimed once,
  spawned briefed, result posted back. Drill with a real job
  end to end; ledger lines are the proof.
- D2. Timer-sweep fallback: the watchman's backup bell — a
  periodic sweep that starts named work whose job file landed
  while the watcher was down. Drill: kill the watchman, land
  a job, restart, the job runs exactly once.

## E. Round 8 remainders

Close whatever your own COUNTS.md still shows open from
Round 8 (deepen pass, READMEs) — name each closed item in the
checkpoint call; anything you judge not worth closing, say so
and why, once.

## Order

A first (it is small and it is a named failure), then B (it is
deadline-shaped), then C, D, E. Checkpoint per section.
