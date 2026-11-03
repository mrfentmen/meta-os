# BOND — CODE WAVE 2 STATUS (CB2-001 .. CB2-500)

Branch `bond/code-wave-2`, stacked on the finished code100 wave and merged
with main `fca4512b`. One line per finished task. Status is CODE + LIGHT
TEST only; Pax verifies on the merged tree.

## Section 1 — Queue Python, crew seams (CB2-001..025) — 25/25

| Task | File | Result |
|---|---|---|
| CB2-001 | `crew_common.py` | loopback guard extracted as pure `check_dispatch_url`; crew keeps an alias |
| CB2-002 | `test_crew_dispatch_url_edges.py` | 0.0.0.0, bare `::1`, and userinfo refused; 5 tests |
| CB2-003 | `test_crew_dispatch_url_edges.py` | query/fragment current behaviour pinned (loopback authority passes) |
| CB2-004 | `test_crew_stop_conditions.py` | 8-action cap stops with no network call |
| CB2-005 | `test_crew_stop_conditions.py` | 12-call cap stops before the 13th call |
| CB2-006 | `test_crew_stop_conditions.py` | $0.50 cap stops before the crossing action |
| CB2-007 | `test_crew_review_seam.py` | model transport error falls back; fallback named on timeline |
| CB2-008 | `test_crew_review_seam.py` | unset `TRIO_JUDGE_MODEL` records `judge_mode: deterministic` |
| CB2-009 | `test_crew_review_seam.py` | stubbed model judge records `judge_mode: model` |
| CB2-010 | `test_crew_routing_table.py` | vigiles/police, ignis/fire, medicus/hospital paths pinned |
| CB2-011 | `test_crew_routing_table.py` | unknown division returns no route; never defaults (premise said raise, real API returns `None`) |
| CB2-012 | `test_crew_receipt_ids.py` | `sim-` + 16 hex, deterministic, key-order independent |
| CB2-013 | `crew_records.py` | pure `validate_incident_record`; missing field named |
| CB2-014 | `test_crew_records_validate.py` | unexpected fields reported, not ignored |
| CB2-015 | `test_crew_records_append.py` | existing JSONL bytes preserved when appending |
| CB2-016 | `test_crew_records_append.py` | torn final line returned as `partial`, intact lines kept |
| CB2-017 | `crew_common.py` | `iso_to_epoch` handles Z and numeric offsets |
| CB2-018 | `test_crew_common_time.py` | naive timestamp refused |
| CB2-019 | `test_crew_tier_mapping.py` | display table wins: small finding yellow, emergency red |
| CB2-020 | `test_crew_tier_mapping.py` | `requires_human_review` is audit-only; simulated dispatch still runs |
| CB2-021 | `test_crew_incident_walk.py` | full stubbed incident reaches brief/bolo/dispatch |
| CB2-022 | `test_crew_incident_walk.py` | investigation never exceeds 6 calls |
| CB2-023 | `test_crew_reading_input.py` | missing review category rules inconclusive (premise said raise; real seam records and holds) |
| CB2-024 | `test_crew_reading_input.py` | string confidence is handled without changing the verdict |
| CB2-025 | `test_crew_cli_parse.py` | `--dry-run` accepted; unknown flag exits 2 |

Section 1 verification, one command per file, all exit 0:
`test_crew_dispatch_url_edges.py` 5, `test_crew_stop_conditions.py` 3,
`test_crew_review_seam.py` 3, `test_crew_routing_table.py` 4,
`test_crew_receipt_ids.py` 5, `test_crew_records_validate.py` 5,
`test_crew_records_append.py` 4, `test_crew_common_time.py` 5,
`test_crew_tier_mapping.py` 4, `test_crew_incident_walk.py` 2,
`test_crew_reading_input.py` 2, `test_crew_cli_parse.py` 3.
**45 tests pass, 0 fail.**

## Section 2 — Queue Python, judge rules (CB2-026..050) — 25/25

| Task | File | Result |
|---|---|---|
| CB2-026 | `test_judge_combine_edges.py` | agreeing emergency confirmed; one reason |
| CB2-027 | `test_judge_combine_edges.py` | disagreeing flagged readings confirm; both named (premise said held; real judge confirms two flagged readings) |
| CB2-028 | `test_judge_combine_edges.py` | either missing reading rules inconclusive |
| CB2-029 | `test_judge_lookalike_edges.py` | bench-sleeper/baseline shape and ignis steam lookalike clear |
| CB2-030 | `test_judge_lookalike_edges.py` | crowd gathered never red; real tier is `None` (ungated), not yellow |
| CB2-031 | `test_judge_model_stub.py` | stubbed confirm maps verdict/category/reasons |
| CB2-032 | `test_judge_model_stub.py` | unknown outcome rules inconclusive, never coerced |
| CB2-033 | `test_judge_model_stub.py` | invalid JSON rules inconclusive |
| CB2-034 | `test_judge_model_stub.py` | missing verdict rules inconclusive |
| CB2-035 | `test_judge_prompt_shape.py` | both readings present; secret/extra incident fields omitted |
| CB2-036 | `test_judge_prompt_shape.py` | "never confirm on a guess" and confidence rule appear once |
| CB2-037 | `test_judge_region_edges.py` | null and full 0-1000 box accepted |
| CB2-038 | `test_judge_region_edges.py` | 1001 and negative edges refused by `validate_reading` |
| CB2-039 | `test_judge_region_edges.py` | overlapping boxes still one verdict/reason |
| CB2-040 | `test_judge_golden_replay.py` | five emergency pairs confirm |
| CB2-041 | `test_judge_golden_replay.py` | eight non-emergency pairs never confirm |
| CB2-042 | `test_judge_time_edges.py` | earliest parseable timestamp wins, including offsets |
| CB2-043 | `test_judge_time_edges.py` | unknown product refused by validator and prompt builder |
| CB2-044 | `judge.py` | one `build_verdict_record` used by crew; both modes share keys |
| CB2-045 | `test_judge_record_shape.py` | `judge_mode` limited to deterministic/model |
| CB2-046 | `test_judge_smoke_shape.py` | staged visible-flame pair confirms and stays red |
| CB2-047 | `test_judge_never_red_property.py` | seeded 50-pair property: no red tier without an emergency category |
| CB2-048 | `judge.py` | category strip/lower normalization; mixed case pinned |
| CB2-049 | `test_judge_normalisation.py` | duplicate identical readings yield one reason, not two confirmations |
| CB2-050 | `judge_replay.py` | offline JSONL replay prints outcome counts only |

Section 2 verification, one command per file, all exit 0: 36 tests pass,
0 fail (`test_judge.py`'s existing 11 also pass; `test_crew.py` 21 pass
against the new verdict builder).

## Section 3 — Queue Python, models client (CB2-051..075) — 25/25

| Task | File | Result |
|---|---|---|
| CB2-051 | `test_models_sam_parse.py` | one box maps to the 0-1000 contract scale unchanged |
| CB2-052 | `test_models_sam_parse.py` | no box raises; no invented region |
| CB2-053 | `test_models_sam_parse.py` | mask-only raises; box-only returns `mask: None` |
| CB2-054 | `test_models_sam_bounds.py` | exact 0 and 1000 accepted; 1001 refused |
| CB2-055 | `test_models_sam_bounds.py` | inverted box refused |
| CB2-056 | `test_models_image_magic.py` | PNG/JPEG/WebP magic labels |
| CB2-057 | `test_models_image_magic.py` | unknown image format raises, never a placeholder |
| CB2-058 | `test_models_image_items.py` | absent image item raises `EmptyResponseError` |
| CB2-059 | `test_models_image_items.py` | truncated base64 raises named error |
| CB2-060 | `test_models_chat_models.py` | Wonder id sent verbatim |
| CB2-061 | `test_models_chat_models.py` | Spark 1.3 sent verbatim; 1.2/1.1 refused as unverified (premise said pass-through) |
| CB2-062 | `test_models_chat_models.py` | empty prompt refused before transport |
| CB2-063 | `test_models_receipts.py` | one call adds one line with model, surface, latency |
| CB2-064 | `test_models_receipts.py` | Spark receipt has a dollar estimate; Wonder receipt null |
| CB2-065 | `test_models_transcribe_block.py` | transcribe names the unresolved surface |
| CB2-066 | `test_models_transcribe_block.py` | transcribe never calls transport |
| CB2-067 | `test_models_error_map.py` | HTTP 429 maps to `RateLimitError` |
| CB2-068 | `test_models_error_map.py` | 401/403 distinct `AuthError`; 500 `ServerError` |
| CB2-069 | `test_models_error_map.py` | empty 200 body and empty chat/segment/image payloads named |
| CB2-070 | `test_models_responses_shape.py` | SAM `/v1/responses` input_text + input_image shape |
| CB2-071 | `test_models_responses_shape.py` | chat messages/model shape; no responses fields |
| CB2-072 | `models.py` | `MAX_PROMPT_CHARS` added; overlong prompt refused before transport |
| CB2-073 | `models.py` | empty/non-image segment input refused before transport |
| CB2-074 | `test_models_id_constants.py` | verified ids and registry surfaces exact |
| CB2-075 | `test_models_no_fabrication.py` | failure paths raise; no placeholder result |

Section 3 verification, one command per file, all exit 0: **36 new tests
pass, 0 fail**; existing `test_models.py` **7 pass**.

## Section 4 — Queue Python, livecams/patrol/evidence (CB2-076..100) — 25/25

| Task | File | Result |
|---|---|---|
| CB2-076 | `test_livecams_parse_edges.py` | string `"true"`/`"false"` online flags parsed correctly |
| CB2-077 | `test_livecams_parse_edges.py` | missing coordinates skipped and counted |
| CB2-078 | `test_livecams_pick.py` | same list + area picks the same camera deterministically |
| CB2-079 | `test_livecams_pick.py` | area with no online camera returns empty |
| CB2-080 | `test_livecams_snapshot.py` | JPEG/PNG accepted; non-image refused |
| CB2-081 | `test_livecams_roundrobin.py` | three cameras cycle and wrap |
| CB2-082 | `test_livecams_roundrobin.py` | camera that goes offline is skipped |
| CB2-083 | `test_livecams_cli_parse.py` | `--list/--area/--division` parse; unknown flag exits 2 |
| CB2-084 | `test_patrol_budget.py` | reserve floor pauses and files nothing |
| CB2-085 | `test_patrol_budget.py` | pause event carries guardrail cost |
| CB2-086 | `test_patrol_frame_flow.py` | baseline activity creates no incident |
| CB2-087 | `test_patrol_frame_flow.py` | category list comes from the JS source |
| CB2-088 | `test_evidence_bolo.py` | exact BOLO key set; no identity field |
| CB2-089 | `test_evidence_bolo.py` | descriptions deduped; direction never invented |
| CB2-090 | `test_evidence_purge.py` | files deleted; purge receipt + timeline recorded |
| CB2-091 | `test_evidence_purge.py` | second purge is idempotent |
| CB2-092 | `test_orchestrator_order.py` | review → investigation → response order |
| CB2-093 | `test_crew_halt.py` | judge failure writes halt step and stops |
| CB2-094 | `test_supervisor_failures.py` | repeated failure recorded once, never restarted |
| CB2-095 | `test_supervisor_failures.py` | no restart/backoff implementation; gap pinned |
| CB2-096 | `test_queue_envelope_edges.py` | missing id, unknown product, bad hash refused |
| CB2-097 | `test_trio_store_roundtrip.py` | nested result round-trip; duplicate submit idempotent |
| CB2-098 | `test_spark_guardrail_refusal.py` | cumulative spend adds up |
| CB2-099 | `test_spark_guardrail_refusal.py` | at/over budget refused with clear wording |
| CB2-100 | `test_spark_guardrail_refusal.py` | under budget allowed |

Section 4 verification: **459 queue-Python tests pass, 0 fail**
(`python3 -m unittest discover -s tests/queue-python`).

## Section 5 — Science Lab — literature and gateway shelf (CB2-101..125) — 25/25

| Task | File | Result |
|---|---|---|
| CB2-101 | `test_literature_source_edges.py` | missing title rejected with named error |
| CB2-102 | `test_literature_dedupe.py` | DOI dedupe is case-insensitive |
| CB2-103 | `test_literature_dedupe.py` | no-DOI dedupe uses normalised title |
| CB2-104 | `test_literature_shelves.py` | chemistry tag lands; untagged is unfiled |
| CB2-105 | `test_literature_source_edges.py` | missing abstract stays null |
| CB2-106 | `test_literature_year.py` | four-digit year accepted; range refused |
| CB2-107 | `test_gateway_allowlist.py` | all nine allowlisted servers accepted |
| CB2-108 | `test_gateway_allowlist.py` | near-miss hyphen and unknown names refused |
| CB2-109 | `test_gateway_local_shelf.py` | local shelf answers without constructing an adapter |
| CB2-110 | `test_gateway_local_shelf.py` | remote adapter raises UNIMPLEMENTED and names it |
| CB2-111 | `test_gateway_query.py` | empty query refused before lookup |
| CB2-112 | `test_gateway_query.py` | hit shape is exactly id/title/shelf |
| CB2-113 | `test_literature_citation.py` | golden citation string matches exactly |
| CB2-114 | `test_literature_citation.py` | empty authors use pinned fallback |
| CB2-115 | `test_literature_provenance.py` | origin server survives parse and filing |
| CB2-116 | `test_literature_corpus.py` | 12 records: 6 parsed, 3 duplicate, 3 rejected |
| CB2-117 | `test_lab_config_edges.py` | missing name raises a named error |
| CB2-118 | `test_lab_config_edges.py` | unknown top-level key is ignored (pinned rule) |
| CB2-119 | `test_lab_config_edges.py` | empty optional sections yield defaults |
| CB2-120 | `test_literature_authors.py` | string and list both normalise to list |
| CB2-121 | `test_literature_authors.py` | whitespace-only author dropped |
| CB2-122 | `test_literature_shelves.py` | three filings list in filing order |
| CB2-123 | `test_gateway_query.py` | shelf routing searches only that shelf |
| CB2-124 | `test_literature_source_edges.py` | archive URL stays archive URL, not DOI |
| CB2-125 | `test_literature_schema_fit.py` | every parsed fixture validates against source schema |

Section 5 verification: **203 Science Lab tests pass, 0 fail**
(`python3 -m unittest discover -s tests/science-lab`).

## Section 6 — Science Lab — reasoning and step chains (CB2-126..150) — 25/25

| Task | File | Result |
|---|---|---|
| CB2-126 | `test_reasoning_hypothesis_edges.py` | missing statement rejected with named error |
| CB2-127 | `test_reasoning_hypothesis_edges.py` | parsed hypothesis validates against schema |
| CB2-128 | `test_reasoning_variables.py` | two named variables keep order |
| CB2-129 | `test_reasoning_variables.py` | no variable -> untestable |
| CB2-130 | `test_reasoning_chain_links.py` | three linked steps keep parent pointers |
| CB2-131 | `test_reasoning_chain_links.py` | chain cycle rejected |
| CB2-132 | `test_reasoning_chain_links.py` | missing parent id named |
| CB2-133 | `test_reasoning_chain_roundtrip.py` | step chain dict round-trip equal |
| CB2-134 | `test_reasoning_prediction.py` | directional prediction sets direction |
| CB2-135 | `test_reasoning_prediction.py` | vague prediction needs refinement |
| CB2-136 | `test_reasoning_step8_block.py` | step 8 always returns blocking UNIMPLEMENTED marker |
| CB2-137 | `test_reasoning_step8_block.py` | no reasoning function returns a step-8 result |
| CB2-138 | `test_reasoning_chain_limits.py` | depth 8 allowed; depth 9 refused |
| CB2-139 | `test_reasoning_chain_limits.py` | empty chain documented form rebuilds |
| CB2-140 | `test_reasoning_evidence_links.py` | two source ids kept |
| CB2-141 | `test_reasoning_evidence_links.py` | unknown source id refused |
| CB2-142 | `test_reasoning_chain_types.py` | unknown step type rejected |
| CB2-143 | `test_reasoning_chain_types.py` | every documented step type accepted |
| CB2-144 | `test_reasoning_confidence.py` | unset confidence stays null |
| CB2-145 | `test_reasoning_confidence.py` | out-of-range confidence rejected |
| CB2-146 | `test_reasoning_corpus.py` | 8 hypotheses counted by classification |
| CB2-147 | `test_reasoning_chain_branch.py` | two children kept and visited once |
| CB2-148 | `test_reasoning_chain_branch.py` | traversal order deterministic |
| CB2-149 | `test_reasoning_duplicates.py` | same statement flagged |
| CB2-150 | `test_reasoning_duplicates.py` | whitespace-only difference is duplicate |

Section 6 verification: **228 Science Lab tests pass, 0 fail**
(`python3 -m unittest discover -s tests/science-lab`).

## Section 7 — Science Lab — compute, cycle, ladder (CB2-151..175) — 25/25

| Task | File | Result |
|---|---|---|
| CB2-151 | `test_compute_rmse.py` | identical series -> zero error |
| CB2-152 | `test_compute_rmse.py` | known two-point RMSE matches to 6 places |
| CB2-153 | `test_compute_rmse.py` | different lengths refused |
| CB2-154 | `test_compute_rmse.py` | empty series refused |
| CB2-155 | `test_compute_run_chem.py` | 5-row fixture reproduces exact RMSE |
| CB2-156 | `test_compute_run_chem.py` | missing target column named |
| CB2-157 | `test_compute_rows.py` | non-numeric cell reports row index |
| CB2-158 | `test_compute_rows.py` | row order stable through parse |
| CB2-159 | `test_cycle_record.py` | new cycle validates against schema |
| CB2-160 | `test_cycle_transitions.py` | each forward transition accepted |
| CB2-161 | `test_cycle_transitions.py` | backwards transition rejected |
| CB2-162 | `test_cycle_transitions.py` | skipped phase rejected |
| CB2-163 | `test_cycle_prereg.py` | same question/plan -> same hash |
| CB2-164 | `test_cycle_prereg.py` | changed plan -> different hash |
| CB2-165 | `test_cycle_prereg.py` | edited plan detected by mismatch |
| CB2-166 | `test_ladder_levels.py` | level 0 lists required evidence |
| CB2-167 | `test_ladder_levels.py` | complete evidence promotes 1 -> 2 |
| CB2-168 | `test_ladder_cap.py` | automated path stops at level 3 |
| CB2-169 | `test_ladder_cap.py` | fake fixture never promotes |
| CB2-170 | `test_ladder_levels.py` | removing evidence demotes level |
| CB2-171 | `test_compute_stats.py` | mean/count hand-checked |
| CB2-172 | `test_compute_stats.py` | constant series has zero variance |
| CB2-173 | `test_cycle_prereg.py` | question whitespace collapses before hashing |
| CB2-174 | `test_cycle_record.py` | cycle dict round-trip |
| CB2-175 | `test_ladder_levels.py` | level names match 0-6 ladder |

Section 7 verification: **253 Science Lab tests pass, 0 fail**
(`python3 -m unittest discover -s tests/science-lab`).

## Section 8 — Science Lab — verify, repository, ledger, export (CB2-176..200) — 25/25

| Task | File | Result |
|---|---|---|
| CB2-176 | `test_verify_blind.py` | identical blind runs agree and record hashes/time |
| CB2-177 | `test_verify_blind.py` | numbers beyond tolerance disagree |
| CB2-178 | `test_verify_tolerance.py` | difference exactly at tolerance passes |
| CB2-179 | `test_verify_tolerance.py` | different row counts refused |
| CB2-180 | `test_verify_failure_drill.py` | claimed success with mismatched numbers yields fake_success false |
| CB2-181 | `test_verify_gate.py` | 0.818 RMSE against 1.5 threshold is a match |
| CB2-182 | `test_verify_gate.py` | above-threshold RMSE is a no-match |
| CB2-183 | `test_repository_records.py` | experiment validates against schema before storage |
| CB2-184 | `test_repository_records.py` | failing schema names the missing field |
| CB2-185 | `test_repository_records.py` | stored record reads back identical |
| CB2-186 | `test_repository_listing.py` | three records list in insertion order |
| CB2-187 | `test_repository_listing.py` | duplicate record id refused |
| CB2-188 | `test_repository_listing.py` | cycle-id filter over mixed records |
| CB2-189 | `test_ledger_append.py` | two entries stay intact and ordered |
| CB2-190 | `test_ledger_append.py` | tampered middle line detected at line 2 |
| CB2-191 | `test_ledger_read.py` | trailing blank lines ignored, count exact |
| CB2-192 | `test_export_shape.py` | every documented export section present |
| CB2-193 | `test_export_shape.py` | missing optional data is explicit null |
| CB2-194 | `test_export_review.py` | review-page fields enumerated and exported |
| CB2-195 | `test_export_review.py` | levels 4-6 never automatically confirmed |
| CB2-196 | `test_verify_gate.py` | matching reproduction assigns level 2 |
| CB2-197 | `test_repository_schemas_load.py` | all five schemas load and parse |
| CB2-198 | `test_repository_records.py` | wrong schema type refused |
| CB2-199 | `test_ledger_read.py` | strict write refuses missing recorded_at |
| CB2-200 | `test_export_claim_audit.py` | five backed claims plus one flagged unbacked claim |

Section 8 verification: **285 Science Lab tests pass, 0 fail**
(`python3 -m unittest discover -s tests/science-lab`).

## Section 9 — Science Lab — Hortus (CB2-201..225) — 25/25

| Task | File | Result |
|---|---|---|
| CB2-201 | `test_hortus_genome.py` | valid fixture parses to four documented fields |
| CB2-202 | `test_hortus_genome.py` | unknown gene key refused |
| CB2-203 | `test_hortus_breeding_step.py` | child genes come only from the two parents |
| CB2-204 | `test_hortus_breeding_step.py` | same parents and seed reproduce same child |
| CB2-205 | `test_hortus_breeding_step.py` | 10-seed sweep yields at least two outcomes |
| CB2-206 | `test_hortus_mutation.py` | maximum mutation differs from pure crossover |
| CB2-207 | `test_hortus_mutation.py` | zero mutation keeps every gene in the parents |
| CB2-208 | `test_hortus_population.py` | six parents produce configured generation of eight |
| CB2-209 | `test_hortus_population.py` | population stays size six across five generations |
| CB2-210 | `test_hortus_verifier.py` | invalid child flags named min_spacing_m constraint |
| CB2-211 | `test_hortus_verifier.py` | valid reference child passes with no violations |
| CB2-212 | `test_hortus_records.py` | one generation writes one parent/child record |
| CB2-213 | `test_hortus_records.py` | duplicate child id refused |
| CB2-214 | `test_hortus_fitness.py` | reference scores its unpenalised heat exactly |
| CB2-215 | `test_hortus_fitness.py` | same individual scores identically across calls |
| CB2-216 | `test_hortus_selection.py` | top-scoring individual always selected |
| CB2-217 | `test_hortus_selection.py` | selection never exceeds configured parent count |
| CB2-218 | `test_hortus_five_gen.py` | generation records run 1..5 in order |
| CB2-219 | `test_hortus_five_gen.py` | every generation passes verify_child |
| CB2-220 | `test_hortus_calibration.py` | 14 fixture parts load, 10 calibration / 4 validation |
| CB2-221 | `test_hortus_calibration.py` | missing score skipped and counted |
| CB2-222 | `test_hortus_genome.py` | genome serialisation round-trips |
| CB2-223 | `test_hortus_population.py` | empty population refused with named error |
| CB2-224 | `test_hortus_breeding_step.py` | crossover result pinned exactly |
| CB2-225 | `test_hortus_records.py` | generation-2 filter over mixed records |

Section 9 verification: **312 Science Lab tests pass, 0 fail**
(`python3 -m unittest discover -s tests/science-lab`).

## Section 10 — Nuntius relay — protocol edges (CB2-226..250) — 25/25

| Task | File | Result |
|---|---|---|
| CB2-226 | `relay/relay.test.mjs` | empty message body refused |
| CB2-227 | `relay/relay.test.mjs` | 2000-char body passes; 2001 refused |
| CB2-228 | `relay/relay.test.mjs` | nick containing a colon keeps nick/body split |
| CB2-229 | `relay/relay.test.mjs` | line with no separator refused by parser |
| CB2-230 | `relay/relay.test.mjs` | emoji and combining body round-trip unchanged |
| CB2-231 | `relay/relay.test.mjs` | newline body refused |
| CB2-232 | `relay/relay.test.mjs` | five messages read in post order |
| CB2-233 | `relay/relay.test.mjs` | same cursor twice returns no duplicates |
| CB2-234 | `relay/relay.test.mjs` | cursor beyond end returns empty page |
| CB2-235 | `relay/relay.test.mjs` | negative cursor refused |
| CB2-236 | `relay/relay.test.mjs` | two concurrent writers lose nothing, per-writer order held |
| CB2-237 | `relay/relay.test.mjs` | room A message absent from room B |
| CB2-238 | `relay/relay.test.mjs` | whitespace room name refused |
| CB2-239 | `relay/relay.test.mjs` | timestamps assigned and non-decreasing |
| CB2-240 | `relay/relay.test.mjs` | malformed JSON frame refused with named error |
| CB2-241 | `relay/relay.mjs` | message validation extracted as `validateMessage` |
| CB2-242 | `relay/relay.test.mjs` | nick length 1 and 40 pass |
| CB2-243 | `relay/relay.test.mjs` | newline in nick refused |
| CB2-244 | `relay/relay.test.mjs` | room cap trims oldest, exact count |
| CB2-245 | `relay/relay.test.mjs` | trimming never drops below 10 retained lines |
| CB2-246 | `relay/relay.test.mjs` | empty room returns empty list |
| CB2-247 | `relay/relay.test.mjs` | limit=2 returns oldest two of five |
| CB2-248 | `relay/relay.test.mjs` | limit=0 refused |
| CB2-249 | `relay/relay.test.mjs` | 100 posted messages have 100 unique ids |
| CB2-250 | `relay/relay.test.mjs` | documented exports exist with expected types |

Section 10 verification: **34 relay tests pass, 0 fail**
(`node --test relay/relay.test.mjs`).

## Section 11 — Nuntius board — store and rendering (CB2-251..275) — 25/25

| Task | File | Result |
|---|---|---|
| CB2-251 | `board/board.test.mjs` | empty title refused |
| CB2-252 | `board/board.test.mjs` | 2000-char body passes; 2001 refused |
| CB2-253 | `board/board.test.mjs` | three notes list oldest-first |
| CB2-254 | `board/board.test.mjs` | note survives a temp store round-trip |
| CB2-255 | `board/board.test.mjs` | corrupted store raises named error |
| CB2-256 | `board/board.test.mjs` | wrong-shape JSON refused |
| CB2-257 | `board/board.test.mjs` | two concurrent notes survive reload |
| CB2-258 | `board/board.test.mjs` | 50 notes have unique ids |
| CB2-259 | `board/board.test.mjs` | body HTML escaped by renderer |
| CB2-260 | `board/board.test.mjs` | script-title markup asserted exactly |
| CB2-261 | `board/board.mjs` | `renderPost` exported and exact plain markup |
| CB2-262 | `board/board.test.mjs` | empty-board markup exact |
| CB2-263 | `board/board.test.mjs` | timestamps present, equal-time sort stable |
| CB2-264 | `board/board.test.mjs` | delete leaves a tombstone after reload; other notes untouched |
| CB2-265 | `board/board.test.mjs` | edit preserves id and original timestamp |
| CB2-266 | `board/board.test.mjs` | unicode note round-trips |
| CB2-267 | `board/board.test.mjs` | fresh store path creates documented JSONL file |
| CB2-268 | `board/board.test.mjs` | directory store path refused by name |
| CB2-269 | `board/board.test.mjs` | note without author refused |
| CB2-270 | `board/board.test.mjs` | author 40 chars passes; 41 refused |
| CB2-271 | `board/board.test.mjs` | limit=2 returns oldest two of five |
| CB2-272 | `board/board.mjs` | `messageToNote` uses nick as author |
| CB2-273 | `board/board.test.mjs` | duplicate submissions create two notes (no idempotency) |
| CB2-274 | `board/board.test.mjs` | partial tail raises, never returns partial notes |
| CB2-275 | `board/board.test.mjs` | documented exports exist with expected types |

Section 11 verification: **38 board tests pass, 0 fail**
(`node --test board/board.test.mjs`).

## Section 12 — Rust queue/relay error paths (CB2-276..300) — 25/25

| Task | File | Result |
|---|---|---|
| CB2-276..282 | `crates/queue-core/tests/section12.rs` | empty id, unknown kind, priority order, FIFO tie-break, empty dequeue, duplicate id, payload bounds |
| CB2-283..288 | `crates/queue-store/tests/section12.rs` | record round-trip, append-only violation, missing read, torn tail, insertion order, empty list |
| CB2-289..294 | `crates/relay/tests/section12.rs` | empty body, first-colon nick split, append order, cursor clamp, room isolation, trim oldest |
| CB2-295..299 | crate tests | wrong-type deserialisation, missing write field, length after mixed, monotonic timestamps, concurrent appends |
| CB2-300 | `crates/queue-core/src/lib.rs` | rustdoc example on `PriorityQueue`, runs as a doc test |

Two real gaps were closed in code while pinning the tests:
- `queue-core`: added `PriorityQueue` enqueue/dequeue and the payload cap.
- `queue-store`: added the append-only `RecordStore`.
- `relay`: added the message-line parser and room trimming.
- **Bug found by CB2-299**: `RecordStore::append` used `writeln!`, which issues a
  separate syscall for the newline. Two O_APPEND writers interleaved text and
  newline, gluing records onto one line (~1 in 3 runs). Fixed by writing one
  buffer in one `write_all`; 25/25 repeat runs now clean.

Section 12 verification: `cargo test -p queue-core -p queue-store -p relay` and
`cargo test -p queue-core --doc` both exit 0.

## Section 13 — Rust os-* error paths (CB2-301..325) — 14/25 delivered, 11 blocked

Delivered against the crates' real public APIs:

| Task | File | Result |
|---|---|---|
| CB2-303 | `crates/os-budget/tests/section13.rs` | at-cap spend allowed; one unit over refused |
| CB2-304 | `crates/os-budget/tests/section13.rs` | negative amount refused; negative spent has no ratio |
| CB2-305 | `crates/os-budget/tests/section13.rs` | three-spend sequence checked against hand arithmetic |
| CB2-306 | `crates/os-identity/tests/section13.rs` | empty and blank nick refused, nothing written |
| CB2-307 | `crates/os-identity/tests/section13.rs` | same nick re-registers one record, never two |
| CB2-311 | `crates/os-memory/tests/section13.rs` | zero-byte alloc leaves outstanding at 0 |
| CB2-312 | `crates/os-memory/tests/section13.rs` | second free refused with the named error |
| CB2-313 | `crates/os-memory/tests/section13.rs` | alloc 100+50, free 30 -> 120 outstanding |
| CB2-325 | `crates/os-budget/src/lib.rs` | rustdoc example on `spend_allowed`/`at_cap`, runs as a doc test |
| CB2-321 | `crates/os-workspace/tests/section13_workspace.rs` | `..`, absolute, and `..`-job-id deposits refused; nothing written |
| CB2-322 | `crates/os-workspace/tests/section13_workspace.rs` | deposit then latest and v1 reads are byte-identical; listing agrees |
| CB2-323 | `crates/os-workspace/tests/section13_workspace.rs` | missing job and empty job both list zero records |
| CB2-314 | `crates/os-misc/tests/section13_misc.rs` | string helpers at their edges: empty basename becomes `blob`, unit-less duration refused by name, room keys round-trip, non-ascii folds to `_`, 60-char cap |
| CB2-315 | `crates/os-misc/tests/section13_misc.rs` | numeric edges: zero duration and zero timestamp kept, `i64::MAX` accepted and one past refused, ISO time-of-day exact, interval zero/negative/`-0.0` refused |

Blocked — the named API does not exist, and inventing it would be fake code:
- CB2-301, 302, 324: `os-boot` is the agent CLI crate; it has no boot-config type.
- CB2-308, 309, 310: `os-jobs` has `JobQueue` but no job-with-steps creation or
  cancel-finished API.
- CB2-314, 315: delivered against the real B24 helpers. Correction to an
  earlier note: `os-misc` does carry a string/numeric helper set
  (`b24::send`, `b24::transport`, `b24::watch`), so the edge tests were written
  rather than skipped.
- CB2-316, 317, 318: `os-supervisor` is the watchdog crate; there is no restart
  policy or backoff sequence to test.
- CB2-319, 320: `os-worker` has `Worker`/`JobSpec`/drivers, not a task-payload or
  result-order API.
- CB2-325: only the spend half landed — there is no `remaining()` function.

Section 13 verification: `cargo test -p os-budget -p os-identity -p os-memory
-p os-workspace`, `cargo test -p os-misc --test section13_misc` (8 pass), and
`cargo test -p os-budget --doc` all exit 0.

## Section 14 — Rust agent/dashboard/guardrail/intel/stack (CB2-326..350) — 8/25 delivered, 17 blocked

| Task | File | Result |
|---|---|---|
| CB2-330 | `crates/assess-server/src/main.rs` | missing product named by `validate_assess_request` |
| CB2-331 | `crates/assess-server/src/main.rs` | unknown product refused, never defaulted |
| CB2-335 | `crates/guardrail/tests/section14.rs` | one micro-dollar under passes; at and over the ceiling trip |
| CB2-336 | `crates/guardrail/tests/section14.rs` | five $0.675 calls total $3.375, hand-checked |
| CB2-337 | `crates/guardrail/tests/section14.rs` | tripped state refuses; a zeroed ledger resets it |
| CB2-350 | `crates/guardrail/src/lib.rs` | rustdoc example on `estimate`, runs as a doc test |
| CB2-339 | `crates/intel/tests/section14_intel.rs` | empty brief uses its documented "no activity yet" form, writes no empty section headings, never panics |
| CB2-340 | `crates/intel/tests/section14_intel.rs` | recovery line rendered from a borrowed `Option<&RecoveryRecord>`; a sweep-count disagreement is named, never an all-clear |

Blocked — the named API does not exist:
- CB2-326..328, 348: `agent-runtime` exposes `Agent::serve_job` and
  `validate_assessment`; it has no registry loader, duplicate-name check, or
  draft detection.
- CB2-329, 332: invalid JSON is rejected at the HTTP layer (already covered by
  `http_invalid_json_is_a_400`); response-contract checking lives in
  `agent-runtime::validate_assessment`, not in assess-server.
- CB2-333, 334, 349: `dashboard` is the brief/contract crate; it has no metrics
  snapshot or CPU/memory/storage/network card builders.
- CB2-338: partly closed and partly still open. The frozen five-section
  vocabulary and its order are now pinned from `BRIEF_SECTIONS`, and the
  empty-input form is pinned (CB2-339). What is not proven is "all sections
  for a full fixture input": `compose_brief` returns early with
  "no activity yet" on an empty window, and the crate exposes no public
  fixture builder, so a populated snapshot would have to invent `SnapMessage`
  and `SnapJob` rows that no real record produced.
- CB2-341..343: `stack` is a service-config planner; it has no push/pop/capacity.
- CB2-344, 345: `parity-tests` has the harness but no queue-envelope or incident
  fixture cases yet.
- CB2-346, 347: region and confidence checks live in
  `agent-runtime::validate_assessment`, not in assess-server.

Section 14 verification: `cargo test -p guardrail`, `cargo test -p guardrail --doc`,
`cargo test -p assess-server`, and `cargo test -p intel --test section14_intel`
(4 pass) all exit 0.

## Section 15 — Schemas and validators (CB2-351..375) — 25/25

| Task | File | Result |
|---|---|---|
| CB2-356 | `agents/registry_validate.mjs` | real registry checked: name, command array, owner (the badge-equivalent), optional badge |
| CB2-357 | `tests/agents-registry-validate.test.mjs` | `["true"]` reported as a draft, never runnable |
| CB2-358 | `tests/agents-registry-validate.test.mjs` | duplicate names reported with both indexes |
| CB2-359 | `server/queue/receipt_validate.py` | model, surface/endpoint, latency, estimate-or-null |
| CB2-360 | `tests/queue-python/test_receipt_validate.py` | Spark without an estimate fails; non-Spark with one fails |
| CB2-361 | `tests/queue-python/test_receipt_validate.py` | malformed JSON reported with its line number |
| CB2-362 | `tools/validate_science_schemas.py` | all five schemas loaded; top-level keys checked |
| CB2-363 | `tests/science-lab/test_science_schemas_wellformed.py` | cycle enum == `cycle.ALL_PHASES`, read as data |
| CB2-364 | `tests/science-lab/test_science_schemas_wellformed.py` | every required hypothesis field is read by `parse_hypothesis` |
| CB2-375 | `tools/schema_index.py` | Markdown index of schemas and validators, fixture-tested |
| CB2-351..355 | `server/queue/record_validate.py` | v2 incident record: exact five-key set, observation/assessment/processing fields, region 0..1000, extra keys named |
| CB2-365..366 | `server/queue/livecam_record_validate.py` | frame (camera id, name, timestamp, sha256) plus reading outcome that must be a category from js/products.js |
| CB2-367 | `relay/message_validate.mjs` | parsed message: nick 40 / body 2000 caps, control chars, ts non-negative integer |
| CB2-368 | `board/note_validate.mjs` | note: id, room, title 200, author 40, text 0..2000, ts, tombstone boolean |
| CB2-369..370 | `os/worlds/science-lab/hortus/record_validate.py` | generation record; duplicate ids, own-parent, unknown parent via `child_parents` |
| CB2-371..372 | `tests/aegis-secrets-counts.test.mjs` | known counts per pattern; serialised report proven to hold no fixture value |
| CB2-373..374 | `server/queue/verdict_validate.py` | the builder's real key set, verdict and judge_mode enums |

All 25 delivered. Every validator returns named field errors and never
repairs a record.

Section 15 verification: record 21, livecam 18, verdict 14, Hortus 14, Aegis 7,
relay 43, board 50 tests — every file exits 0.

## Section 18 — Tooling scripts (CB2-426..450) — 25/25

All tools read logs as data; none writes to a log or to `kernel/src`.

| Task | File | Result |
|---|---|---|
| CB2-426..430 | `tools/bootlog_parse.py` | banner, alive, panic count, readkey events, status ticks, programs, fault isolation |
| CB2-431..432 | `tools/bootlog_verdict.py` | four named checks; removing one line flips only that check |
| CB2-433..435 | `tools/proof_index.py` | Markdown index; non-log files skipped and counted; sorted by filename |
| CB2-436..438 | `tools/receipt_check.py` | reuses the receipt rules; negative latency and Spark-estimate rules by line |
| CB2-439..440 | `tools/kernel_census.py` | per-file line table; extension filter configurable |
| CB2-441..442 | `tools/fetch_screen_parse.py` | tasks/frames/heap; missing memory lines named, never zeroed |
| CB2-443..444 | `tools/ps_rows_parse.py` | pid/name/state rows; unknown state kept and flagged |
| CB2-445..446 | `tools/gate_log_check.py` | PASS/FAIL by name; 6 of 7 names the failing check |
| CB2-447 | `tools/soak_summary.py` | duration, tick range, panic count only |
| CB2-448 | `tools/log_diff_claims.py` | lists only checks whose pass state changed |
| CB2-449 | `tools/screendump_note.py` | Markdown proof note, names and values only |
| CB2-450 | `tests/queue-python/test_bootlog_pipeline.py` | parse -> verdict -> index over three fixture logs |

Section 18 verification: 12 test files, **50 tests pass, 0 fail** (one command
per file; every exit status checked).

## Section 19 — Officina and Musica pure code (CB2-451..475) — 15/25 delivered

Officina's pure modules: `heatsink.py` (simulator + bounds), `design_loop.py`
(post/claim/score/held-out gate), `brief.py` (rough-words parser + iterator),
`prior_art.py`, `memory.py`, `faber.py`, `pack_export.py`.

| Task | File | Result |
|---|---|---|
| CB2-451 | `tests/officina/test_officina_bounds.py` | FIN_HEIGHT_MM (5,80) and BASE_THICKNESS_MM (2,12) pinned |
| CB2-452 | `tests/officina/test_officina_bounds.py` | height 80 accepted; 81 refused by name |
| CB2-453 | `tests/officina/test_officina_bounds.py` | base 1.9 refused; 2.0 accepted |
| CB2-456 | `tests/officina/test_officina_description.py` | plain description yields DEFAULT_PARAMS |
| CB2-457 | `tests/officina/test_officina_description.py` | missing dimensions fall back and the unknowns list flags it |
| CB2-471 | `os/worlds/officina/spec_validate.py` | four fields, numeric, in range; bool refused |
| CB2-472 | `tests/officina/test_officina_spec_validate.py` | non-numeric field named |
| CB2-475 | `tests/officina/test_officina_pack_shape.py` | pack.json parses; every declared runtime part exists |
| CB2-463 | `tests/musica-catalogue-edges.test.mjs` | every published track has a title and duration; key and tempo joined from its take record |
| CB2-464 | `os/worlds/musica/catalogue_validate.mjs` | duplicate take ids refused, naming both indexes |
| CB2-467 | `tests/musica-library-data.test.mjs` | real library round-trips; keeper list length and keeper rate match the counts |
| CB2-468 | `os/worlds/musica/catalogue_validate.mjs` | a holding with no licence line is flagged `rights missing` |
| CB2-473 | `tests/musica-normalize-data.test.mjs` | title transform trims, single-spaces, title-cases |
| CB2-474 | `tests/musica-normalize-data.test.mjs` | idempotent on every real title; a non-string is refused, never coerced |
| CB2-454 | `tests/officina/test_officina_loop_record.py` | every amendment names round, change and reason; every decision-log entry carries its round and result; `rounds_used` matches the highest logged round; harness jobs name the violation when failed |

Two things the Musica data revealed while pinning these tests:
- The catalogue's own tracks carry `title`, `take_id`, `duration_s`, `licence`.
  Key and tempo live on the take record, so CB2-463 joins the two by
  `take_id` instead of inventing fields the studio never writes.
- `gate-packet/library.json` holdings carry no licence field. CB2-468 pins the
  validator that requires one and proves it flags the gap on a fixture; the
  published file is not repaired here, because rewriting studio output to
  satisfy a test would be exactly the fake the wave forbids.

Correction: CB2-454 first looked blocked because `DesignJob` has no iteration
record. The loop's record is not on the job — it is the run file, whose
`amendments` and `decision_log` carry round, change and reason per iteration.
The test reads those real files.

Not delivered: CB2-455 (no STOP-file check function), CB2-458 (no schematic module),
CB2-459 (no enumerated 14-check gate list), CB2-460..462 (no JS note/semitone
module; the mapping lives in `runtime/theory.py`), CB2-465..466 (no JS
variation generator; `runtime/compose.py` owns it), CB2-469..470 (the take log
has a `timestamp` and a `verdict`, not a start/end keeper window).

Section 19 verification: `python3 -m unittest discover -s tests/officina -p
"test_*.py"` runs the whole Officina tree at **84 tests pass, 0 fail**; the
loop-record file alone is 7. Musica adds 11 new node tests (4 + 3 + 4), all
passing.

## Section 20 — Documentation-as-code (CB2-476..500) — 21/25 delivered

| Task | File | Result |
|---|---|---|
| CB2-476..490 | `docs/readme-data/*.json` | 15 program records: imperium, ignis, medicus, science-lab, hortus, officina, musica, aegis, nervus, hands-free, agent-layer, nuntius, kernel, live-cams, goose-services |
| CB2-491 | `tests/readme-data.test.mjs` | every file parses, carries the six keys, status in the four-value set |
| CB2-492 | `tests/readme-data.test.mjs` | no file contains `Custos` |
| CB2-493 | `tools/readme_data_index.py` | Markdown table (name, status, proof), fixture- and real-tree-tested |
| CB2-499 | `docs/readme-data/face.json` | face is the design running in a carrier/browser; kernel graphics in progress |
| CB2-497 | `tests/aegis-watch-data.test.mjs` | every target the Aegis watch builder emits is a local file path; a pasted URL is a path, never a fetch |
| CB2-498 | `tests/aegis-findings-shape.test.mjs` | finding carries the documented key set, severity from `SEVERITIES`, and no `value` field; bad severity refused with the ledger untouched |

Correction to an earlier note in this file: `nervus/contracts.mjs` **does**
exist. It holds the five operations as data with `requires` (inputs) and
`produces` (outputs). What it does not hold is the third thing CB2-494 asks
for — a real-run-required flag — so the operation table cannot be asserted
against a field nobody wrote.

Not delivered:
- CB2-494: `nervus/contracts.mjs` has `requires` and `produces` per operation
  but no real-run-required flag; `stub-runner.mjs` marks its own output STUB
  in prose, which is not a contract field.
- CB2-495: no contract carries a ledger field; `RECORD_FIELDS` is
  model_hash/operation/probe/result with no ledger name.
- CB2-496: the layer curve (L4 4.6, L8 19.5, L16 12.8, L24 10.2) appears in no
  Nervus file — `nervus/*.mjs` has none of those values.
- CB2-500: `agents/registry.json` lists agent nicks, not programs, so a
  program-file set cannot be matched against it without inventing a mapping.

Section 20 verification: `node --test tests/readme-data.test.mjs` 5 pass;
`test_readme_data_index.py` 3 pass; 7 new Aegis tests pass (3 + 4).

## Section 16 — Agent layer Node (CB2-376..400) — 22/25

| Task | File | Result |
|---|---|---|
| CB2-376 | `tests/agents-runtime-edges.test.mjs` | empty command array refused at load |
| CB2-377 | `tests/agents-runtime-edges.test.mjs` | placeholder accepted; the registry's own `draft` flag is what marks it (pinned: no runtime detector) |
| CB2-380 | `tests/agents-watchman-edges.test.mjs` | a content change gives exactly one change note |
| CB2-381 | `tests/agents-watchman-edges.test.mjs` | three polls with no change stay silent |
| CB2-383 | `tests/agents-baton-edges.test.mjs` | baton carries job id, step index, state, artifacts |
| CB2-386 | `tests/agents-baton-edges.test.mjs` | a chain with a changed job id is refused |
| CB2-389 | `tests/agents-lessons-edges.test.mjs` | one teach writes one JSONL line with agent, text, timestamp |
| CB2-391 | `tests/agents-lessons-edges.test.mjs` | lessons read in append order and every agent sees them |
| CB2-394 | `tests/agents-watchdog-edges.test.mjs` | one missed beat is fine; two alarm once, then stay quiet |
| CB2-398 | `tests/agents-clock-edges.test.mjs` | same inputs give the same times; backward jump flagged, not negative |
| CB2-399 | `tests/agents-runtime-edges.test.mjs` | torn final ledger line skipped; next record stays whole |
| CB2-400 | `tests/agents-registry-shape.test.mjs` | every entry has name, owner (badge field), and a string command array |
| CB2-390 | `tests/agents-lessons-edges.test.mjs` | `teach` refuses empty text and empty agent by name; nothing written |
| CB2-396 | `tests/agents-safewrite-edges.test.mjs` | `writeIfChanged` reports changed:false on identical bytes; mtime untouched |
| CB2-397 | `tests/agents-safewrite-edges.test.mjs` | `writeWithinRoot` refuses ../, siblings, and absolute paths |
| CB2-378 | `tests/agents-runtime-budget.test.mjs` | over-cap job refused before spawn; no child, no poll, no timer |
| CB2-379 | `tests/agents-runtime-budget.test.mjs` | `budget-receipt` and `refused` events name the cap and the estimate |
| CB2-387 | `agents/gym.mjs` | `loadDrillFile` refuses an unknown step type with the type and index named |
| CB2-388 | `tests/agents-gym-edges.test.mjs` | drill file runs through the real `spawnAgent`; one score per declared step |
| CB2-395 | `tests/agents-queue-edges.test.mjs` | three posted jobs drain in id order, once each; a second drain runs nothing |
| CB2-382 | `agents/runtime.mjs`, `tests/agents-watchman-edges.test.mjs` | `LARGE_CHANGE_BYTES` threshold in the runtime; a change at the boundary takes the alarm form, a small one stays a note, a delete is always an alarm with no byte delta |
| CB2-385 | `agents/baton.mjs`, `tests/agents-baton-resume.test.mjs` | `stepsRemaining` resumes after the last done step; a step-run log proves no completed step runs twice; a baton with no usable index is refused, never restarted from zero |

Not delivered: CB2-384 — `writeBaton` has six callers (a drill script and five
tests) that build a baton with no step index, so requiring one at construction
is a behaviour change that breaks them, not a test. CB2-392..393 — `bridge.mjs`
is the supervisor verb (start/stop/boot); it shapes no messages, so there is
no wire shape to assert.

Section 16 verification: 13 test files, **56 tests pass, 0 fail**; the whole agent
suite (`node --test tests/agents-*.test.mjs`) is 126/126.

## Section 17 — Face tests (CB2-401..425) — 0/25, blocked

`face/face.js` is a classic browser script: zero `export`/`module.exports`,
87 functions closing over `document` and `localStorage`, and no pure logic
module. The section forbids editing face source, and a test-local fixture
model would test the fixture rather than the app, so no test was written.
Unblocking needs one of: extracting the calculator/calendar/notes/window
logic into an importable module, or agreeing that fixture-model tests count.

Per-task check (2026-11-02):
- CB2-401..405: there is no `tests/face-apps.test.mjs` and no
  `tests/kernel-records.test.mjs` in the tree to re-check; the held files are
  not present, so there is no fixture path to repair.
- CB2-418..419: `DOCK` carries three systems only (imperium, musica, science).
  Officina, Aegis, and Nervus have no dock entry, and no app-id -> repo-path
  map exists, so "all six systems present" cannot be asserted without editing
  face source. Custos is absent (checked).
- CB2-420..421: there is no test-mirror copy of the category list to compare
  with, and `js/products.js` has no per-category definition field: products
  carry tagline/limitations, while categories are bare strings.
- CB2-406..417, 422..425: no importable pure logic exists for calculator,
  calendar, notes, terminal, settings, files, trash, or window state.

## Closeout — 428 of 500 delivered, 72 open

Every delivered line above rests on a real API or a real data file. Every open
one is open for a named reason, not for want of trying.

| Section | Delivered | Open |
|---|---|---|
| 1–12 (Python, relay, board, Rust queue) | 300 | 0 |
| 13 Rust os-* error paths | 14 | 11 |
| 14 Rust agent/dashboard/intel/stack | 8 | 17 |
| 15 Schemas and validators | 25 | 0 |
| 16 Agent layer Node | 20 | 5 |
| 17 Face tests | 0 | 25 |
| 18 Tooling scripts | 25 | 0 |
| 19 Officina and Musica | 15 | 10 |
| 20 Documentation-as-code | 21 | 4 |
| **Total** | **428** | **72** |

### The 73, by the decision that unblocks them

1. **Face source (25).** Section 17 forbids editing `face/face.js`, and that
   file has no exports and 87 functions closing over the DOM. One yes unlocks
   all 25: either extract the calculator/calendar/notes/terminal/window logic
   into an importable module, or agree that fixture-model tests count.
2. **New APIs (17, Section 14).** `dashboard` is a 61-line stub with zero
   public functions and no metrics type; `stack` plans service configs and has
   no push/pop; `agent-runtime` has no registry loader. Building these is new
   feature work, not test work.
3. **New APIs (11, Section 13).** `os-boot` is the agent CLI crate (no boot
   config type), `os-jobs` has no job-with-steps API, `os-supervisor` has no
   restart policy or backoff sequence, `os-worker` has no payload type.
4. **Missing data (4, Section 20).** Nervus has no real-run flag and no ledger
   field on its contracts, and the layer curve (L4 4.6, L8 19.5, L16 12.8,
   L24 10.2) appears in no file. CB2-500 needs a program list the registry
   does not carry.
5. **Python-only logic (10, Section 19).** Note math, variation and keeper
   windows live in `runtime/*.py`. A JS copy would be a second implementation
   to drift, so no test was written against a mirror.
6. **Missing behaviour (5, Section 16).** No large-change alarm threshold, no
   baton step-index check, no resume function, and `bridge.mjs` is a
   supervisor verb rather than a message shaper.

### Two red tests that are older than this wave, left visible

- `tests/musica-budget.test.mjs` — the cap-hit path prints its takes but never
  the `budget stop` line. A real bug in the budget module.
- `tests/musica-export.test.mjs` — crashes when `pretty_midi` is absent.
  `tests/musica-midi.test.mjs` skips for exactly this reason; export does not.

Neither was skipped or patched to green: a green run that hides a real gap is
worse than a red one that names it.

### One break repaired on the way

`cargo test -p intel` did not compile: `PlanJob` gained `spec` and `accept`
while two test fixtures still built the old field set, so none of the crate's
suites could run. Both fixtures now fill the two fields empty — what the
shape-only parser leaves them as — and the crate is green at 124 passed.

`cargo check --workspace` exits 0. It still prints pre-existing dead-code
warnings (140 in `parity-tests`, 2 in `intel`); none were introduced here and
none were silenced.
