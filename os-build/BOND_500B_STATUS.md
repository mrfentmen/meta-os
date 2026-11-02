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
