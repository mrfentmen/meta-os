# Science Lab evaluation

First eval baseline for Science Lab: 28 scenarios, all grounded in
material that ships — no invented science, no model calls, no network.

## What it measures

Whether the 13 hosted Science Lab researchers still do what
`hana/science-lab-tools` wired them to do: each duty runs over the
records that ship and reports its own check. This is the baseline
"whatever raises eval scores" is measured against. A later change
that breaks a duty, drops an agent from the registry, or re-drafts
an agent shows up here as a failing scenario before it ships.

## Files

- `scenarios.json` — 28 scenarios: 13 `--check` runs, 13 full duty
  runs (each asserting its duty's check name in the receipt the duty
  writes — except research-director, whose success rows are a
  per-cycle census with no check key, so that scenario asserts row
  shape and the two shipped cycle ids instead), 1 registry-shape check (all 13 entries carry the hosted.py
  command with `hosted: true`), 1 refusal check (an unknown agent
  exits 2 with "it stays a draft").
- `run.py` — the runner. Copies the shipped records to a temp dir,
  runs the real `hosted.py` against that copy, reads each duty's own
  receipt file for the full findings. Prints a deterministic report
  (no timestamps) and exits non-zero unless every scenario passes.
  Duty receipts land in the runner's state dir, not in the repo.
- `baseline.json` — the expected outcome: 28/28 pass on the shipped
  records, recorded 2026-11-03 (see `baseline-run-report.md`).
- `baseline-run-report.md` — the recorded baseline run.

## Run it

```sh
python3 eval/science-lab/run.py
python3 eval/science-lab/run.py --out /tmp/sl-report.json
python3 tests/science-lab/test_eval_science_lab.py
```

## What it does NOT measure

The duties are audits, not science: they report what the shipped
records carry (cycle-level falsifier statements, fit statistics,
literature shelves, compute provenance). No scenario asserts a
hypothesis is true, a design is sound, or a per-record field that
does not ship — no full hypothesis record file ships on disk, and
the discipline duties say so in their own output. Judging science
quality still needs a model or a human; this harness guards the
wiring that makes that judgement possible.

## Stacking note

This branch stacks on `hana/science-lab-tools` (the 6 newly hosted
researchers). Merge after that branch, via Pax only. No merge by Hana.
