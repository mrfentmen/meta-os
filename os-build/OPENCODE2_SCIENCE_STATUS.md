# OpenCode2 Science Lab — status file (per task rules, updated per section)

Branch: `opencode2/science-lab`, off main 2904e743. NEVER push to main. Pax merges.
Source: boss's LABORATORY text in `os/worlds/science-lab/` (PACK.md, pack.json). Six systems: Research Intelligence, Scientific Reasoning, Computational Lab, Discovery Engine, Independent Verification, Knowledge Repository. Ladder 0-6. Phases 1-7 sourced; steps 9/10 human-gated; no verified text for step 8 — gap is explicit UNIMPLEMENTED.

## Section 1 — Foundations (1–10) — LANDED 2026-11-02

Task 1 audit (`os/worlds/science-lab/` vs LABORATORY text):
- PRESENT: PACK.md, pack.json (13 agents, alerts, cross-world, firstboot), schemas/experiment.schema.json, schemas/hypothesis.schema.json, hortus/ runtime (engine, model, verifier, records, calibration + demo/calibrated/hunt records), gate/ Delaney prep (GATE_PREP.md, run_gate.py, prep_results.json, delaney SOURCES + csv), agents/registry.json 13 lab entries (research-director … research-archivist, owner system:science-lab)
- STUB (before this section, now BUILT): lab-local agent jobs, ladder model/guard, general ledger, cycle record/machine, lab config, lab CLI, tests/science-lab/
- MISSING (still, Sections 2-10): literature job/brief assembler/shelves, hypothesis-generator/analyst/math/stat/critic jobs + reasoning chain, department runners/sandbox/compute budget, cycle driver/recovery/report, verifier isolation/blind re-run/comparison/rotation/repository, Hortus variant/lineage integration, MCP gateway allowlist/call records, lab session export/review page/archive/board, full dress rehearsal/failure drill/claim audit/README
- HONESTY gaps (carried as UNIMPLEMENTED in code): code hash + environment + agent timestamp fields (schema has no slots — ledger layer only), step 8 silent (cycle.STEP_8 marker, always blocks), levels 4-6 automated promotion (no code path, ladder.py MAX_AUTOMATED_LEVEL=3), model-call budgets (caps checked, actual spend metering UNIMPLEMENTED)

What landed (tasks 2-9):
- Task 2: `os/worlds/science-lab/agents/` 13 files + README.md (verbatim pack roles, serves, MUST-NOTs, ladder 0-6, UNIMPLEMENTED step 8)
- Task 3/4: `ladder.py` LEVELS 0-6, can_promote/next_required, assert_export_allowed, cap_for_experiment, MAX_AUTOMATED_LEVEL=3
- Task 5/6: `ledger.py` append-only JSONL hash chain (append_record/verify_chain/read_all, GENESIS); experiment schema verified (question->research_question, method->software+model+parameters, data hash->input_hash, seed->random_seed, etc.)
- Task 7: `schemas/cycle.schema.json` + `cycle.py` (PHASES 1-7, STEP_8 UNIMPLEMENTED, HUMAN_GATES wetlab/publication, park/resume, one transition = one ledger entry)
- Task 8: `lab_config.json` + `lab_config.py` (endpoint placeholder file://local Muse Spark helper, key Mac line1 only; per-agent + cycle caps; check_budget + write_receipt)
- Task 9: `cli.py` (cycle start/status/advance, experiment list/show, ladder show; real records under `records/`; blocked advances exit 1 with reason)

Tests (task 10):
- `tests/science-lab/test_ladder.py`: 22 tests OK
- `tests/science-lab/test_section1.py`: 14 tests OK (schemas round-trip, ledger chain verifies + tamper breaks, ladder guard blocks over-level, cycle gate refusal, human-gate park/resume, budget stop + receipt)
- Full `tests/science-lab/`: 36 tests OK (`python3 -m unittest discover -s tests/science-lab -v`)
- Existing suites untouched: `os/tests/test_hortus_engine.py` 9 tests OK; `node agents/runtime.mjs list` loads registry (25 entries incl. 13 lab)
- CLI smoke: cycle start/status, ladder show L2, blocked advance to verification (missing critique, exit 1), verify_chain ok

Still UNIMPLEMENTED (Sections 2-10 queued, in order): Research Intelligence jobs, Reasoning chain jobs, Computational Lab runners, Discovery cycle driver, Verification isolation + Repository, Hortus variant integration, MCP gateway, OS outputs (export/session/archive/board), demo cycle + truth pass. No cycle run filed yet; `records/` holds only .gitkeeps.

Next: Section 2 — Research Intelligence (11–20), in order.

## Section 2 — Research Intelligence (11–20) — LANDED 2026-11-02

- 11/13/16: `literature.py` literature_search (deterministic local only, no network; search_remote/synthesize_with_model UNIMPLEMENTED), assemble_brief (unpinned dropped + ledger `brief-claim-dropped`, phantom citations warned), mark_contested (supports+disputes -> contested, never resolved silently)
- 12: `schemas/source.schema.json` (citation, retrieved_at, access_note, supports_claim, locator+content_hash, stance supports/disputes)
- 14: `reproduction_target.json` via find_prior_result() — Delaney 2004 ESOL, 1128 rows sha256 8c06a76f… verified live, qualifies (inputs available / checkable / no paywall on method), target numbers TO_BE_READ_AT_RUN, gate NOT attempted
- 15: `shelves/` biology/chemistry/physics_math/materials (4 seeds each, only DOI asserted 10.1021/ci034243x, rest plain URLs)
- 17: check_source_budget (caps from lab_config, receipt on stop under records/literature/)
- 18: status_record + file_status_record (sources_read, pinned/dropped/contested + counts)
- 20: `records/examples/research_intelligence_example.json` (Q: Delaney reported RMSE? 3 pinned, 1 dropped TO_BE_READ_AT_RUN, contested [] honest, ledger 2 entries verified, at most L1)
- 19 tests: test_section2a 26 OK (unpinned dropped, contested marked) + test_section2b 6 OK (budget stop, status counts, target, example honesty)
- Full suite: 68 tests OK (`discover -s tests/science-lab`); hortus 9 OK; registry loads
- UNIMPLEMENTED carried: remote adapters (openalex/archive-org/etc), model judgement calls, live paper extraction (run-time per SLICE1 §4)

## Section 3 — Scientific Reasoning (21–30) — LANDED 2026-11-02
- reasoning.py: new_hypothesis (L0, disproof required), generate_hypotheses (3-5, falsifierless rejected+logged), decompose, check_math (deterministic), preregister (hashed to ledger BEFORE results, late refused), critique (required record)
- reasoning_chain.py: build_chain hash-linked brief->hyps->decomp->prereg->critique, verify_chain_links, gate_to_computational (missing critique/prereg blocks; step-8 never invented; prereg-before-result enforced via ledger)
- Example records/examples/reasoning_example.json (Delaney RH1-3, prereg R2>=0.5 filed, critique null -> gate blocked honestly, no paper figure hardcoded)
- Tests test_section3.py 4 OK; full suite 72 OK; hortus 9 OK
- UNIMPLEMENTED: model judgement calls (synthesize_with_model), live math-symbolic engine beyond deterministic checks
