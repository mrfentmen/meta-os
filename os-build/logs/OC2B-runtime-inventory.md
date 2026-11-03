# OC2B-001 — runtime inventory (server/queue/*.py)

Branch: opencode2/landwalls. 23 modules, all `python3 -m py_compile` clean.
Live import scan: `OC2B-import-scan.txt` (AST, stdlib `ast` only).

## Modules (one line + sibling imports; stdlib omitted)

- `crew_common.py` — loopback guard, node/js bridge helpers. Siblings: none
  (shells out to `node` for `js/products.js`, `js/schema.js`).
- `crew_records.py` — incident/record store over `data_dir()`; validators,
  purge receipts. Siblings: none. Entry: `CrewRecords()`, `data_dir()`.
- `crew.py` — staged pipeline (flag→review→judge→response, SIMULATED
  dispatch to 127.0.0.1:8935). Siblings: `crew_common, crew_records,
  evidence, judge, models, orchestrator, spark_gen, trio_store`.
  Entry: `build_arg_parser()`; patrol's library.
- `evidence.py` — face-box detection + BOLO extraction (collect-only).
  Siblings: none. Lazy third-party: `cv2`, `numpy`, `PIL` (absence → honest
  `unavailable`, never fatal).
- `hosted_imperium.py` — one-pass drill harness (three stages, one receipt).
  Siblings: none (drives services over HTTP, child env overrides).
- `judge_replay.py` — replay harness. Siblings: `crew_common, judge`.
  Entry: argparse `main`.
- `judge.py` — deterministic judge + optional model path. Siblings: none.
  Consumed by `crew.py`, `judge_replay.py`.
- `livecam_record_validate.py` — validates live-reading v2 block. Siblings:
  `trio_repo`, `record_validate.validate_v2_incident`.
- `livecams.py` — camera source + CLI (`--list`, `--assess-one`).
  Siblings: `spark_gen` (lazy, assess path only). Entry: `main(argv)` /
  `build_arg_parser()`. EXECUTABLE BIT SET this session (was 644).
- `livehunt.py` — bounded live-flag hunt (budget governor → crew check →
  record). Siblings: `crew, crew_common, crew_records, patrol,
  spark_gen, spark_guardrail`.
- `models.py` — multi-model client; appends receipt JSONL per call.
  Siblings: `spark_guardrail`. Key: `SPARK_API_KEY` from environ only.
- `orchestrator.py` — deterministic decision engine; no model calls, $0.
  Siblings: `crew_common, spark_guardrail`.
- `patrol.py` — patrol worker (round-robin + priority, budget governor).
  Siblings: `crew, crew_common, crew_records, spark_guardrail`.
  Entry: `main()` (`--interval/--once/--max-checks/--reserve-usd`);
  shebang. EXECUTABLE BIT SET this session.
- `queue_service.py` — Trio queue HTTP service (`POST /jobs`,
  `GET /jobs/<id>/result`, `GET /health`, 127.0.0.1 only). Siblings:
  `crew_records, trio_repo, trio_store`. Entry: `main()` (`--port`);
  shebang. EXECUTABLE BIT SET this session.
- `receipt_validate.py` — shape checks for model receipt JSONL.
  Siblings: none. Entry: CLI `<receipts.jsonl>`.
- `record_validate.py` — named-field validator for v2 record. Siblings:
  none (stdlib datetime only).
- `spark_gen.py` — generation transport (direct `SPARK_API_KEY` POST via
  guardrail; DEV-ONLY helper path). Siblings: `spark_guardrail, trio_repo`.
- `spark_guardrail.py` — $75 hard-stop ledger over `STATE_PATH`.
  Siblings: none.
- `supervisor.py` — read-only behavior supervisor ($0). Siblings:
  `crew_records, spark_guardrail`. Entry: argparse `main`.
- `trio_agent.py` — resident agent (claim → verify SHA-256 → generate →
  validate → write `trio:{jid}:result`). Siblings: `spark_gen,
  trio_repo, trio_store`. Entry: `main()` (`--once/--lease/--nick/
  --schema/--poll-interval`); shebang. EXECUTABLE BIT SET this session.
- `trio_repo.py` — repo anchors (`QUEUE_DIR`, `SCHEMA_PATH`,
  `PRODUCTS_PATH`); loads products by shelling `node`. Siblings: none.
  Node sidecar required, no python fallback.
- `trio_store.py` — `UpstashStore` first, `LocalSqliteStore` fallback;
  `JobStore` on top. Siblings: none. Result prefix always
  `trio:<jid>:result`.
- `verdict_validate.py` — named-field validator for judge verdict.
  Siblings: none.

Data in tree: `livecam_records/` (frames + readings),
`spark_guardrail_state.json` (live ledger), `.gitignore`, `README.md`.

## Entry-point bits (OC2B-005..008 packaging fix, this session)

`chmod +x` applied to the 4 entry points (shebang present, were 644):
`queue_service.py, trio_agent.py, patrol.py, livecams.py` now 755.
`--help` exits 0 on all four (proofs: `OC2B-entry-*.txt`).
`--version` UNSUPPORTED on all four (argparse error, exit 2 — proof:
`OC2B-versions.txt`). OC2B-023 UNPROVEN, needs-feature (owner: OC2,
one-line argparse proposal, runtime edit deferred, named here honestly).
