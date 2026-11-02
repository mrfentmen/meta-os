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
