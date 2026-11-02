# `crates/os-budget` — public surface inventory (B070)

Every `pub` name in `crates/os-budget/src/lib.rs`, one line each.
Status is about callers in THIS repo today:

- **used** — called by another non-test function in this crate.
- **tests** — no non-test caller; the crate's tests are the only user.
- **unused** — no caller anywhere in the repo.

There is no external Rust caller (see `os-budget-callers.md`), so
“used” never means another crate.

## Value model

| Name | Kind | Used by | Status |
|---|---|---|---|
| `Value` | enum | every module in the crate | used |
| `v_str` / `v_int` / `v_dict` | fn | builders across the crate | used |
| `Value::get` | fn | all extractors, audit | used |
| `Value::as_text` | fn | audit, prompt helpers | used |
| `Value::as_str_list` | fn | audit helpers | used |
| `Value::usable_int` | fn | budgets, gate | used |
| `Value::usable_number` | fn | forecast, cost | used |
| `Value::py_num_str` | fn | forecast lines, brief renderer | used |
| `Value::py_repr` | fn | `brief_prompt` | used |
| `py_float_str` | fn | `py_num_str`, `py_repr` | used |
| `py_str_repr` | fn | `py_repr` | used |

## Budgets and gate

| Name | Kind | Used by | Status |
|---|---|---|---|
| `env_int_value` | fn | `budget_warn_percent` | used |
| `budget_warn_percent` | fn | `at_warning` | used |
| `spend_ratio` | fn | `at_warning`, `at_cap`, `budget_state` | used |
| `at_warning` | fn | `budget_state`, `budget_warning_alerts` | used |
| `at_cap` | fn | `claim_allowed`, `budget_state`, `hold_entry` | used |
| `claim_allowed` | fn | `FakeQueue::claim` | used |
| `budget_state` | fn | — | tests |
| `budgets_from_snapshot` | fn | `budget_warning_alerts` | used |
| `hold_entry` | fn | — | tests |
| `FakeQueue` (+ `new`, `post`, `claim`, `status_of`) | struct/impl | — | tests |
| `budget_warning_alerts` | fn | — | tests |
| `budget_spend_line` | fn | — | tests |

## Forecast

| Name | Kind | Used by | Status |
|---|---|---|---|
| `FORECAST_DAY_HOURS` | const | `forecast_lines` | used |
| `FORECAST_LOW_BELOW` | const | `confidence_for` | used |
| `FORECAST_HIGH_AT` | const | `confidence_for` | used |
| `project_end_of_day` | fn | `forecast_entry` | used |
| `confidence_for` | fn | `forecast_entry` | used |
| `format_hours` | fn | `forecast_entry` | used |
| `ForecastEntry` | struct | `forecast_entry` | used |
| `forecast_entry` | fn | `forecast_lines` | used |
| `forecast_lines` | fn | — | tests |
| `preempt_decision` | fn | — | tests |
| `preempt_record` | fn | — | tests |

## Brief-measure helpers

| Name | Kind | Used by | Status |
|---|---|---|---|
| `brief_budget` | fn | `brief_prompt`, `compose_brief_no_client` | used |
| `estimate_tokens` | fn | cost builders, brief cost | used |
| `message_parts` | fn | `extract_decisions` | used |
| `match_decision` | fn | `extract_decisions` | used |
| `extract_decisions` | fn | `brief_prompt`, `morning_template_brief` | used |
| `extract_owners` | fn | same | used |
| `extract_blocked` | fn | same | used |
| `extract_watch_items` | fn | `morning_template_brief` | used |
| `window_line` | fn | `morning_template_brief` | used |
| `trim_to_budget` | fn | `compose_brief_no_client` | used |
| `cap_snapshot_window` | fn | `compose_brief_no_client` | used |
| `morning_template_brief` | fn | `compose_brief_no_client` | used |
| `compose_brief_no_client` | fn | `measure_brief_cost`, `template_brief_record` | used |
| `redact_secrets` | fn | `morning_template_brief` | used |

## Demo-day cost

| Name | Kind | Used by | Status |
|---|---|---|---|
| `CREDIT_USD` | const | `cost_totals`, render | used |
| `RESERVED_HALF_USD` | const | `cost_totals`, brief-cost render | used |
| `WORST_OUTPUT_TOKENS` | const | `build_rows`, `measure_brief_cost` | used |
| `DISPATCH_EXPECTED_OUTPUT_TOKENS` | const | `build_rows` | used |
| `DEMO_GOAL` | const | `build_rows` | used |
| `demo_snapshot` | fn | `build_rows` | used |
| `brief_prompt` | fn | `build_rows`, `measure_brief_cost` | used |
| `polish_prompt` | fn | `build_rows` | used |
| `rate_value` | fn | `rates` | used |
| `rates` | fn | `build_rows`, `measure_brief_cost` | used |
| `cost` | fn | `build_rows`, measure | used |
| `round6` | fn | `cost`, `cost_totals` | used |
| `CostRow` | struct | `build_rows`, render | used |
| `CostSummary` | struct | `cost_totals`, render | used |
| `build_rows` | fn | `run_cost_check`, tests | used |
| `build_rows_from_disk` | fn | — | **unused** |
| `cost_totals` | fn | `run_cost_check` | used |
| `render_cost_table` | fn | `run_cost_check` | used |
| `run_cost_check` | fn | — | tests |

## Busy-fixture brief cost

| Name | Kind | Used by | Status |
|---|---|---|---|
| `BRIEF_COST_CLAIMS` | const | `busy_snapshot` | used |
| `BRIEF_COST_OPEN` | const | `busy_snapshot` | used |
| `BRIEF_COST_BLOCKED` | const | `busy_snapshot` | used |
| `BRIEF_COST_DONE` | const | `busy_snapshot` | used |
| `busy_snapshot` | fn | `measure_brief_cost` | used |
| `BriefCostRow` | struct | measure/render | used |
| `measure_brief_cost` | fn | `build_brief_cost_rows` | used |
| `build_brief_cost_rows` | fn | `run_brief_cost_check` | used |
| `render_brief_cost_table` | fn | `run_brief_cost_check` | used |
| `run_brief_cost_check` | fn | — | tests |
| `TemplateBriefRecord` | struct | `template_brief_record` | used |
| `template_brief_record` | fn | — | tests |

## Cgroup portable parts

| Name | Kind | Used by | Status |
|---|---|---|---|
| `CGROUP_EXPECTED` | const | `slice_file_passes` | used |
| `HOG_TARGET_CHUNKS` | const | — | **unused** |
| `HOG_CHUNK_MB` | const | — | **unused** |
| `HOG_TEST_CAP` | const | — | **unused** |
| `parse_slice` | fn | — | tests |
| `slice_value` | fn | `slice_file_passes` | used |
| `slice_file_passes` | fn | — | tests |
| `cgroup_gate_missing` | fn | — | tests |

The three hog constants belong to the unported host enforcement phase
(gap list item 12). They are kept because the phase's numbers are
specified; they are dead until a host drill exists.

## Disk audit

| Name | Kind | Used by | Status |
|---|---|---|---|
| `ArtifactEntry` | struct | store trait, audit | used |
| `ArtifactStore` | trait | `audit`, `FakeStores` | used |
| `MemoryStore` | trait | `audit`, `FakeStores` | used |
| `parse_artifact_ref` | fn | `audit` | used |
| `audit_goal` | fn | `audit` | used |
| `audit_progress_notes` | fn | `audit` | used |
| `audit_remaining_files` | fn | `audit` | used |
| `audit_job_out` | fn | `audit` | used |
| `AuditResult` | struct | `audit` | used |
| `audit` | fn | — | tests |
| `FakeStores` | struct/impl | — | tests |

## Summary

- 76 public functions (including the 11 public methods on `Value`
  and `FakeQueue`), 9 public structs, 1 public enum, 2 public traits,
  16 public constants.
- **Used in the crate:** the mirrors and builders that feed each other.
- **Tests only:** gate helpers, forecast preemption, `audit`,
  `run_*_check`, `template_brief_record`, `budget_spend_line`.
- **Unused:** `build_rows_from_disk` (no caller yet) and the three
  `HOG_*` constants (host phase not ported).
- No `pub` item is reachable from another crate today.
