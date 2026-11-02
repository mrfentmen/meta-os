# OC1B §14 — Science Lab + Hortus Mac verification (OC1B-326..350)

Tree: `94010c76ee095fa6c6bcfa4405cd56a9695f32d3` (`opencode/500` tip at pass start).
Date (UTC): 2026-11-02. All runs LIVE on Del's Mac. No `os/worlds/science-lab/` code
edited; probe side-effect files reverted (see defect block).

## Suite runs

- **OC1B-326** `python3 -m unittest discover -s tests/science-lab` → **Ran 163 tests,
  OK** (0.893 s test time). Full output: `os-build/logs/OC1B-science-suite.txt`.
- **OC1B-327** per-file counts (same command, `-p <file>`), recorded in
  `os-build/logs/OC1B-science-suite.txt`:
  test_ladder 22, test_section1 14, test_section2a 26, test_section2b 6,
  test_section3 4, test_section4 9, test_section5 25, test_section6 13,
  test_section7 14, test_section8 11, test_section9 13, test_section10 6.
  Sum = 22+14+26+6+4+9+25+13+14+11+13+6 = **163** (matches the full-run count).
- **OC1B-328** `python3 -m unittest discover -s os/tests -p "test_hortus*.py"` →
  **Ran 14 tests, OK** (0.132 s). Per-file: test_hortus_calibration 5,
  test_hortus_engine 9. Output: `os-build/logs/OC1B-hortus-suite.txt`.
- **OC1B-343** wall-clock: science 0.893 s test time (WALL 1 s measured);
  hortus 0.132 s (WALL 0 s); hortus engine demo run ~1 s (§339).

## Dress-rehearsal re-run (OC1B-329..333)

**OC1B-329** Re-ran the rehearsal end to end via
`export.run_dress_rehearsal(file_to_records=False)` — full recompute from the
archived CSV, no duplicate ledger/repository rows (the
`DRESS-REHEARSAL-001 already filed; recomputed only` guard held).
Fresh output saved: `os-build/logs/oc1b-science-rerun.json`
(filed record it recomputes: `os/worlds/science-lab/records/examples/dress_rehearsal.json`).

- **OC1B-330** run_chem RMSE on held-out rows 11–30: **0.8177471797566775** vs
  pre-registered RMSE ≤ 1.5 → scientific verdict **match**.
  File sha256 recomputed at run time: `8c06a76f0c64…89` (matches the archive pin).
- **OC1B-331** blind-reproduce verdict: **agree**
  (`hash_comparison.diff: agree: hashes match (616e42f33e61…) and outcomes match ('match')`).
- **OC1B-332** gate confirmed at recorded level **2**; automated promotion went no
  higher than the L3 cap (`ladder.MAX_AUTOMATED_LEVEL = 3`; filed_level 2).
- **OC1B-333** model spend: **0** (`timing.model_spend_note: 0 -- no model calls on
  this path; deterministic stdlib only`).

## Fresh discovery cycle (OC1B-334)

New question, run through literature → reasoning → compute → verify → repository
(real functions, temp ledger `/tmp`, no repo filing). Record:
`os-build/logs/oc1b-science-freshcycle.json`.
Question: "Can ESOL-style linear model predict solubility for 20 held-out
compounds (rows 31-50) within RMSE 1.5?"
RMSE rows 31–50: **0.5844340852482852** → verdict **match**; reproduce
**reproduced**; gate **confirmed L2**; 2 hypotheses generated (third rejected:
no falsifier); prior shelf hit: true. Cycle machine parked 3 of 6 transitions
with explicit `requires inputs` blocks (hypotheses/critic/sealing gates held —
the guardrails, not the path, stopped the toy driver).

## Failure drill (OC1B-335)

`export.run_failure_drill()` (in-memory; record saved
`os-build/logs/oc1b-science-failuredrill.json`):
`behaviour: refused`, `refused: true`, **`fake_success: false`**,
`refusal_message: blocked: phase 'cheap-computations' requires inputs ['hypotheses']; file them first.`
Second probe: `run_bio with invalid bases; behaviour: refused: run_bio: invalid
bases ['X', 'Z'] in sequence`.

## Gateway LOCAL-SHELF (OC1B-336)

- `gateway.py` line 28: "No function here opens a socket."
- `Gateway.status`: `backend: local-shelf`, `network: no external network touched
  on this path`.
- Allowlisted call `call_tool("literature-researcher", "openalex", …)` returns
  `result.backend: LOCAL-SHELF` (Delaney citation, quarantined UNCONFIRMED).
- Non-allowlisted tool refused: `GatewayRefused: refused: tool 'remote-evil' not
  in gateway allowlist (9 allowed servers)`.
- No remote MCP adapter invoked anywhere in this section: **confirmed LOCAL-SHELF
  only**.

## STEP_8 marker (OC1B-337)

`cycle.STEP_8 = 'step-8-unimplemented'`; `transition(...STEP_8...)` →
`blocked: ValueError: UNIMPLEMENTED: step 8 is silent in the source text; no
behaviour defined. Route around or park blocked-on-source.` **Still blocks.**

## Claim-audit sample (OC1B-338)

`export.audit_own_claims()`: **checked 19, backed 19, cut []** (matches wave-1).
5 traces resolved file + JSON-path → live export doc
(saved `os-build/logs/oc1b-science-claimsample.json`):
CYCLE-EXAMPLE-001-reasoning L1 +basis; CYCLE-EXAMPLE-001-computation L2 +basis;
CYCLE-EXAMPLE-001-ledger-0 L1 +basis; CYCLE-EXAMPLE-001-ledger-1 L2 +basis;
(second reasoning entry, same file, L1 +basis).

## Review page (OC1B-341)

`python3 os/worlds/science-lab/export.py --review` regenerates
`labs/science-lab-review/index.html`; diff vs committed page = the footer
timestamp line ONLY (content renders CYCLE-EXAMPLE-001 + its 5 claims + ledger
state). Timestamp churn reverted; page confirmed current.

## Mac vs wave-1 comparison (OC1B-342)

| item | OC2 wave-1 | this Mac pass | delta |
|---|---|---|---|
| science suite | 163 OK | 163 OK | none |
| hortus suite | 9 OK (engine file only) | 14 OK (engine 9 + calibration 5) | counting scope: both hortus files ship in merge 55e226fc ("hortus python 14/14 on the merged tree"); wave-1 counted the engine file only — UNKNOWN whether deliberate; no test delta either way |
| claim audit | 19 checked / 19 backed | 19 / 19 / 0 cut | none |
| rehearsal RMSE | 0.818 ≤ 1.5 match | 0.8177471797566775 match | none (fp print width) |
| blind reproduce | agree | agree | none |
| gate level | confirmed L2 | confirmed L2 | none |
| model spend | 0 | 0 | none |

## Defects (OC1B-344)

1. **Test-hygiene defect (filed for Pax/OpenCode 2, not fixed here):
   `tests/science-lab/test_section2b.py` writes `C-BUDGET.budget-receipt.json`
   into the REAL `os/worlds/science-lab/records/literature/` on every suite
   run.** Confirmed by reappearance: removed the file, re-ran the suite, file
   back. Suite still green. Stray file removed after each run; tree clean.
   Same defect class: every suite run rewrites tracked
   `records/exports/CYCLE-EXAMPLE-001.json` (`generated_at` timestamp churn
   only — verified identical apart from the timestamp, then reverted).
   No source edited.
2. Probe-footgun note (not a code defect): `breeding.preserve_dead_ends` /
   `select_survivor` default to filing in the real repository when `base` is
   omitted — my first breeding probe filed 5 `P-OC1B-001-*` rows into
   `records/repository/*.jsonl`; spotted in `git status`, reverted with
   `git checkout`. Lesson recorded; the committed records are untouched.
3. Observation (by design, not a defect): shipped `records/examples/*_example`
   docs are composite worked examples and do NOT validate as bare schema
   records — bare-record validation below uses real records instead. No other
   failures: **no other defects.**

## Schema validation (OC1B-345)

`jsonschema` 4.25.1 (`python3 -m pip install jsonschema`, machine-local only —
no repo change). All five schemas VALID against a real record each
(`os-build/logs/oc1b-science-schemas.json`,
`os-build/logs/oc1b-science-schemas2.json`,
`os-build/logs/oc1b-science-source.json`):

- cycle.schema ↔ `records/cycles/DRESS-REHEARSAL-001.json`: VALID
- experiment.schema ↔ fresh in-memory `compute.run_chem` record: VALID
- hypothesis.schema ↔ fresh `reasoning.generate_hypotheses` item: VALID
- repository.schema ↔ live store aggregate (claims+experiments+cycles built
  from `records/repository/*.jsonl`): VALID
- source.schema ↔ real Delaney source record (citation + DOI locator +
  sha256 of `gate/delaney/SOURCES.md`): lab validator `[]`, jsonschema VALID

## Ledger (OC1B-346)

`ledger.read_all`: **20 entries**; `verify_chain`: **(True, 'ok: 20 entries
verified')**. Append-only file parses clean; never rewritten by these runs
(probe filings used `/tmp` ledgers; the one accidental repo write reverted).

## UNIMPLEMENTED, confirmed by runs (OC1B-348)

Remote MCP adapters (gateway refuses everything off-allowlist; LOCAL-SHELF
only); model judgement calls (spend 0 on every path; no call exists to meter);
spend metering (caps checked, actual spend UNIMPLEMENTED); ladder levels 4–6
automation (`MAX_AUTOMATED_LEVEL=3`, no code path above); STEP_8 behaviour
(always-blocking marker); voice transcription (untouched seam).

## Verdict (OC1B-349)

**Science Lab + Hortus VERIFIED ON MAC**: 163 + 14 tests green, rehearsal
recomputed end to end (RMSE 0.8177 ≤ 1.5, blind agree, gate confirmed L2,
spend 0), ledger verifies (20 entries), all 5 schemas validate against real
records, Hortus engine + breeding integration both ran for real. One filed
test-hygiene defect (C-BUDGET stray receipt); no code edited.

## Status-file rows (OC1B-347/350)

OC1B-347 addendum committed to `os/worlds/science-lab/SCIENCE_LAB_STATUS.md`
on this branch (Pax merges). OC1B-350: section commit sha recorded in
`os-build/logs/OC1B-s14-STATUS-SNIPPET.md` (coordinator owns
`OPENCODE1_500_STATUS.md`; not edited here per lane instructions).
