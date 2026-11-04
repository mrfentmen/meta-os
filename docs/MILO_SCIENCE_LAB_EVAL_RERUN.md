# Milo independent re-run: Science Lab eval harness

Per Pax's room 1 scope (final-12h Science Lab ask): independently
re-run Hana's `science-lab-eval` harness and report plainly.
Branch only, nothing merged. No duplicate build: Hana's harness code
was run as-is, not rebuilt or modified.

## What was run

- Harness checkout: `hana/science-lab-eval` @ `adb6af0a`
  ("Science Lab eval: make baseline report byte-deterministic"),
  stacked on `hana/science-lab-tools` @ `00a4dfd5`.
- Commands (fresh worktree, no repo files changed by the run):
  - `python3 eval/science-lab/run.py --out /tmp/milo-sl-rerun-report.json`
  - `python3 tests/science-lab/test_eval_science_lab.py`
- This branch (`milo/science-lab-eval-rerun`, off `origin/main`
  @ `af457ebd`) carries only this report. No code, no merge.

## Result

- **28/28 scenarios pass, 0 fail** — identical to Hana's baseline.
- The rerun report JSON is **byte-identical** to Hana's committed
  `eval/science-lab/baseline.json`.
- Harness tests: **2/2 pass** (`Ran 2 tests ... OK`).
- Breakdown, same as baseline: 13 `--check` scenarios (every
  researcher reads the shipped records), 13 duty scenarios (every
  duty runs and reports its own check; research-director asserts
  per-cycle census rows for CYCLE-EXAMPLE-001 and
  DRESS-REHEARSAL-001), 1 registry-shape check (all 13 entries
  carry the hosted.py command with `hosted: true`), 1 refusal check
  (unknown agent exits 2 with "it stays a draft").

## Honest cap — what this does NOT show

Same cap Hana stated, and Milo stated in his 00:53 ack: these evals
test the harness wiring, not science. No scenario asserts a
hypothesis is true, a design is sound, or a cure or compound is
real. **This re-run establishes no cancer cure and no new chemical
compound.** That would need lab validation, and no such claim is
made here.

## Gap in the scope as worded — sealed CURE-1103/GEN-1103 records

Pax's scope named "the sealed CURE-1103/GEN-1103 records". Milo
searched for those IDs in all three trees that matter here:

- `hana/science-lab-eval` @ `adb6af0a` — not present
- `hana/science-lab-tools` @ `00a4dfd5` — not present
- `origin/main` @ `af457ebd` — not present

No file, record, or ledger entry carrying CURE-1103 or GEN-1103
was found, and the harness itself runs only against the shipped
records (the two shipped cycles above). So the "against the sealed
records" portion could not be executed as specified — there was
nothing matching those IDs to run against, and Milo did not invent
substitute records.

**Open question for Pax:** where do the sealed CURE-1103/GEN-1103
records live (branch, path, or sealed store)? Point Milo at them
and he will re-run against exactly those records and report that
result. If the shipped-records re-run above already satisfies the
scope, no further action is needed from Milo on this item.
