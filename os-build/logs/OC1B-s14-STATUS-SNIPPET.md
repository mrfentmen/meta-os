# OC1B-s14 STATUS SNIPPET (coordinator merges into OPENCODE1_500_STATUS.md)

Lane: verification engineer, Del's Mac. Branch: `opencode/500-s14`.
Base tree for all runs: `94010c76ee095fa6c6bcfa4405cd56a9695f32d3`.
Fences obeyed: no push to main, no commit to opencode/500, no `kernel/src`
edits (syscalls.rs untouched), no face/web work, loopback dispatch untouched
(no dispatch run in these sections), no padded counts, every number from the
named command, SPARK key never read (no live-model section here — no key
needed, none used).

## §14 Science Lab + Hortus (OC1B-326..350) — VERIFIED ON MAC

- OC1B-326 PROVEN (`os-build/logs/OC1B-science-suite.txt`): 163 tests, OK.
- OC1B-327 PROVEN (same file): per-file 22/14/26/6/4/9/25/13/14/11/13/6 = 163.
- OC1B-328 PROVEN (`os-build/logs/OC1B-hortus-suite.txt`): 14 tests, OK
  (calibration 5 + engine 9).
- OC1B-329 PROVEN (`os-build/logs/oc1b-science-rerun.json` + rehearsal md):
  fresh recompute rows 11-30, no re-filing.
- OC1B-330 PROVEN: RMSE 0.8177471797566775 ≤ 1.5, verdict match.
- OC1B-331 PROVEN: blind reproduce agree (hashes match 616e42f33e61…).
- OC1B-332 PROVEN: gate confirmed L2; MAX_AUTOMATED_LEVEL=3.
- OC1B-333 PROVEN: model spend 0.
- OC1B-334 PROVEN (`os-build/logs/oc1b-science-freshcycle.json`): fresh
  question rows 31-50, RMSE 0.5844, match, reproduced, confirmed L2.
- OC1B-335 PROVEN (`os-build/logs/oc1b-science-failuredrill.json`):
  refused/true/fake_success false.
- OC1B-336 PROVEN: LOCAL-SHELF only (allowlisted→LOCAL-SHELF backend;
  off-allowlist refused; "No function here opens a socket").
- OC1B-337 PROVEN: STEP_8 still blocks (ValueError UNIMPLEMENTED).
- OC1B-338 PROVEN (`os-build/logs/oc1b-science-claimsample.json`): audit
  19/19/0 cut, 5 traces with basis.
- OC1B-339 PROVEN (`os-build/logs/oc1b-hortus-breeding.json`,
  `os-build/logs/oc1b-hortus-run.jsonl`): engine 300 gens / breeding 3→1.
- OC1B-340 PROVEN (`os-build/logs/OC1B-hortus-runs.md`): engine first best
  74.9996 / final best 138.3907 / mean 119.0601 / champion 9086 / verifier
  PASSED (cap L2); breeding V001–V003 = -3.989 each (same slice — machinery
  proven, not diversity), survivor V001, lineage verifies.
- OC1B-341 PROVEN: `--review` regen idempotent (timestamp line only, reverted).
- OC1B-342 PROVEN (comparison table in rehearsal md): only delta vs wave-1 is
  counting scope (hortus 14 vs 9 — both files ship in merge 55e226fc).
- OC1B-343 PROVEN: science 0.893 s / hortus 0.132 s / engine run ~1 s.
- OC1B-344 DEFECT REPORT (not fixed): test_section2b drops
  C-BUDGET.budget-receipt.json into real records/literature/ every run;
  suite rewrites tracked CYCLE-EXAMPLE-001.json timestamp every run. Both
  reverted. No code defects found.
- OC1B-345 PROVEN (`oc1b-science-schemas*.json`, `oc1b-science-source.json`):
  all 5 schemas VALID vs real records (jsonschema 4.25.1 machine-local).
- OC1B-346 PROVEN: ledger 20 entries, verify_chain ok.
- OC1B-347 PROVEN: addendum committed in SCIENCE_LAB_STATUS.md (this branch).
- OC1B-348 PROVEN: unimplemented block (remote MCP, model judgement, spend
  metering, L4-6, STEP_8, voice).
- OC1B-349 verdict: VERIFIED ON MAC.
- OC1B-350 commit: §14 sha below.

## §15 Musica (OC1B-351..375) — SUITE 39/39, REGISTRY DRAFT STAYS DRAFT

- OC1B-351 PROVEN (`os-build/logs/OC1B-musica-basal.txt` + `-full.txt`):
  Bond's exact command, 39 pass / 0 fail (14 s).
- OC1B-352 PROVEN (same file): no basal failures — pretty_midi 0.2.11.post0
  pre-installed machine-wide; Bond's 2 failures unreproducible here.
- OC1B-353 PROVEN (`OC1B-musica-install.txt`): no install performed (already
  present); version recorded.
- OC1B-354 PROVEN (`OC1B-musica-after.txt`): 39/39 after (12 s).
- OC1B-355 PROVEN: no remaining failures. OC1B-368: no other missing dep.
- OC1B-356 PROVEN (`OC1B-musica-node.txt`): the Node suite IS the 28-file
  musica suite; no separate Python suite exists.
- OC1B-357 PROVEN (`OC1B-musica-registry.md`): command `["true"]` quoted.
- OC1B-358 PROVEN: placeholder, no backing file.
- OC1B-359/360 NOT RUN (by design): command does not verify; running `true`
  proves nothing.
- OC1B-361 verdict: DRAFT STAYS DRAFT (exact reason recorded).
- OC1B-362 PROVEN (`OC1B-musica-gate.txt`): gate_packet.py exit 0, 19 s,
  packet built to /tmp.
- OC1B-363 PROVEN (`oc1b-musica/keeper.txt`, `keeper-report.json`):
  overnight short form exit 0, 4 takes / 4 keepers / 0 rejects, 7.2 s.
- OC1B-364 PROVEN: face data present (`design/meta-musica-notes.html`,
  `os-build/face/musica.html`), nothing built.
- OC1B-365 PROVEN (`OC1B-musica-after2.txt`): 39/39 stable (13 s).
- OC1B-366 PROVEN: `python3 -m pip install pretty_midi==0.2.11.post0`.
- OC1B-367 PROVEN: delta +2 tests in tree, 0 failures.
- OC1B-369 verdict: suite 39/39 STABLE, registry DRAFT STAYS DRAFT, keeper REAL RUN DONE.
- OC1B-370 spend: none. OC1B-371: `os/worlds/musica/` git-clean (verified at
  commit). OC1B-372: timings recorded. OC1B-373: no code defects.
- OC1B-374/375: Musica rows here; commit sha below.

## §16 Goose gate-2 (OC1B-376..400) — BLOCKED (runner cannot complete)

- OC1B-376 PROVEN (`OC1B-goose-inventory.txt`): 42 dirs listed.
- OC1B-377 PROVEN: `GOOSE=/Users/test/mcp-servers/toolchains/goose-src/build/goose`.
- OC1B-378 PROVEN: binary present. OC1B-385: `goose b781587 (runtime 3901ec457ba9)`.
- OC1B-379 PROVEN (`OC1B-goose-run1.txt`): EXIT=1, 5 s, 6 PASS then abort.
- OC1B-380/381/382 PROVEN (runner md): 6 pass / 0 fail / 1 abort (updater).
- OC1B-383 PROVEN: `/opt/homebrew/bin/goose` same version; `goose toolchain`
  clang 21.0.0; no install.
- OC1B-384 PROVEN (`OC1B-goose-core5.txt`): entry points exist; root-placed
  copies compile, LINK fails on kernel externs (`_sys_exit` etc.); `goose check`
  exit 0 all five (t111 0 / t110 2 / t107 0 / t114 3 / t116 11 warnings).
- OC1B-386 BLOCKED with reason: Buffy fix not landed anywhere (only 75e1febf
  ever touched the runner); path already correct — no run 2.
- OC1B-387/388 NOT RUN: no run 2 (fix-not-landed line stands).
- OC1B-389 PROVEN (`OC1B-goose-failures.txt`): import-root error + no-main
  error, verbatim.
- OC1B-390 PROVEN: RUNNER defect (machine-invariant).
- OC1B-391 defects D1/D2/D3 filed in runner md; no services/ edit.
- OC1B-392 PROVEN: runner appends tracked host.log + rewrites updater
  tracked files; all reverted; services/ clean.
- OC1B-393 timing: 5 s. OC1B-394: no-hosted-results line (none in tree).
- OC1B-395 PROVEN: 6/7 checks pass; 0 services with run evidence; 5/5 core +
  root typecheck clean.
- OC1B-396 verdict: BLOCKED. OC1B-397 boundary recorded. OC1B-398 terminal
  error quoted. OC1B-399/400: rows here; commit sha below.

## Section commits (opencode/500-s14)

- §14: 1434b2cf7683d1f56b2b94ec15c9f21e1eb3cb55
- §15: cdadb4848c8da89f7af1d0aa3dd369e9753c76ea
- §16: 275e105c014560931fb5d522efb7be4e079eb30f

## Tree-integrity incident (unattributed writes, reverted)

At ~16:11:30–33Z, tracked files `os-build/aegis/*`, `os-build/handsfree/*`,
`os-build/nervus/*` were modified by an unattributed writer (concurrent lane
activity on this shared Mac is the leading hypothesis — no command in this
lane references those paths; verified by grep). Evidence preserved at
`os-build/logs/oc1b-unattributed-writes.diff`; all reverted before commit.
`os/worlds/science-lab/records/exports/CYCLE-EXAMPLE-001.json` timestamp churn
from the science suite re-run reverted likewise. Final `git status` at each
commit contains only sanctioned files.

UNPROVEN list (named, none silent): OC1B-359/360 (registry has no runnable
command — DRAFT correct); OC1B-386..388 run 2 (Buffy fix not landed);
per-service Goose RUN evidence (kernel-link ceiling, environment).
