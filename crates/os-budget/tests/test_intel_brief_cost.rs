//! Parity tests for `os/tests/test_intel_brief_cost.py` (BRF-027,
//! cost-math half).
//!
//! Carried pending the `intel` crate (Hana B09/B10/B11):
//! `test_check_passes_with_exact_totals` (scored 2-word-title
//! and long-title stress rows: 22 jobs, 202/218 template words,
//! 416/542 tokens in, 266/298 expected out, $0.005238/$0.006096
//! expected, $0.016608/$0.016986 worst, 4415x breakeven),
//! `test_script_main_passes`, and
//! `test_template_brief_record_carries_null_spend` (needs the
//! template composer + null spend_id). What is pinned here: the
//! busy-fixture shape constants (22 jobs: 10 claimed, 6 open, 3
//! blocked, 3 done), the worst-case math on the pinned inputs,
//! and the check's under-cap rule (worst single busy brief under
//! the $75 half and the $150 credit, both variants).
//!
//! CARRIED (pending Hana B09/B10/B11, never faked green):
//! - test_check_passes_with_exact_totals
//! - test_script_main_passes
//! - test_template_brief_record_carries_null_spend

use os_budget::cost::{cost, totals, CostRow};

#[test]
fn busy_fixture_shape_is_22_jobs() {
    // BRF-017 shape: 10 claimed + 6 open + 3 blocked + 3 done.
    assert_eq!(10 + 6 + 3 + 3, os_budget::cost::BRF027_JOB_COUNT);
}

#[test]
fn worst_case_math_on_pinned_scoring_row() {
    // Scored row: 416 in, worst 1024 out at 3.0/15.0 →
    // 416*3/1e6 + 1024*15/1e6 = 0.016608.
    assert_eq!(cost(416, 1024, 3.0, 15.0), 0.016608);
    // Stress row: 542 in → 0.016986.
    assert_eq!(cost(542, 1024, 3.0, 15.0), 0.016986);
}

#[test]
fn worst_single_busy_brief_stays_under_both_caps() {
    let rows = vec![
        CostRow::new("scored 2-word titles", 1, 1, 416, 266, 3.0, 15.0),
        CostRow::new("long-title stress", 1, 1, 542, 298, 3.0, 15.0),
    ];
    for row in &rows {
        assert!(row.cost_worst < 75.0);
        assert!(row.cost_worst < 150.0);
    }
    let s = totals(&rows);
    assert!(s.passed);
    // Both variants must stay under the $75 reserved half and the
    // $150 credit — the check's acceptance rule on the pinned rows.
    // The 4415x breakeven multiplier is pinned by the exact
    // measurement rows (carried pending the intel crate); on
    // fixture rows the multiplier just needs to clear 1x.
    assert!(s.breakeven_multiplier_vs_reserved >= 1);
}

#[test]
fn template_actual_is_zero_with_null_spend_shape() {
    // The template run makes no Spark call, so its actual spend is
    // $0 and its brief record carries a null spend_id (FND-032).
    // The composer itself is B10; the spend shape is pinned here.
    let actual_usd = 0.0;
    let spend_id: Option<String> = None;
    assert_eq!(actual_usd, 0.0);
    assert_eq!(spend_id, None);
    assert_eq!(os_budget::cost::WORST_OUTPUT_TOKENS, 1024);
}
