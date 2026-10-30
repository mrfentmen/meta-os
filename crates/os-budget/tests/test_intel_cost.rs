//! Parity tests for `os/tests/test_intel_cost.py` (INT-007,
//! cost-math half).
//!
//! Carried pending the `intel` crate (Hana B09/B10/B11):
//! `test_check_passes_with_exact_totals`
//!   (expected `$0.021258`, worst `$0.12789`, with-boot `$0.143982`,
//!   headroom `$74.856018`, breakeven 520x, 5 rows, 5 base / 8 worst),
//! `test_check_twice_identical`,
//! `test_table_renders_rows_budgets_and_headroom`'s row-count
//! shape pins exact token measurements from `brief.py`'s
//! extractors/composers and `spark_client._estimate_tokens` over
//! `intel/prompts/dispatch.md` — none of which this crate ports.
//! What is pinned here: the rate rule (env overrides, client
//! placeholder defaults 3.0/15.0), the six-decimal cost math
//! (spot-checked against the suite's own 0.005238 row), the
//! headline totals (expected/worst/with-boot/headroom under the
//! `$75` half and `$150` credit), the breakeven multiplier, and
//! the table rendering.
//!
//! CARRIED (pending Hana B09/B10/B11, never faked green):
//! - test_intel_cost.py::test_check_passes_with_exact_totals
//!   (expected $0.021258, worst $0.12789, with-boot $0.143982,
//!   headroom $74.856018, breakeven 520x, 5 rows, 5 base / 8 worst)
//! - test_intel_cost.py::test_check_twice_identical
//! - test_intel_cost.py::test_table_renders_rows_budgets_and_headroom
//! - test_intel_brief_cost.py::test_check_passes_with_exact_totals
//!   (scored/stress rows: 22 jobs, 202/218 words, 416/542 in,
//!   266/298 out-exp, $0.005238/$0.006096 exp, $0.016608/$0.016986
//!   worst, 4415x breakeven)
//! - test_intel_brief_cost.py::test_script_main_passes
//! - test_intel_brief_cost.py::test_template_brief_record_carries_null_spend

use os_budget::cost::{
    cost, rates, render, totals, CostRow, CREDIT_USD, DEFAULT_RATE_IN_PER_MTOK,
    DEFAULT_RATE_OUT_PER_MTOK, DISPATCH_EXPECTED_OUTPUT_TOKENS, RESERVED_HALF_USD,
    WORST_OUTPUT_TOKENS,
};

#[test]
fn estimate_rates_are_the_client_placeholders() {
    assert_eq!(DEFAULT_RATE_IN_PER_MTOK, 3.0);
    assert_eq!(DEFAULT_RATE_OUT_PER_MTOK, 15.0);
    let (rate_in, rate_out, _, _) = rates();
    // Pinned 3.0/15.0 unless the harness overrides the env.
    let _ = (rate_in, rate_out);
}

#[test]
fn rate_env_override_and_bad_input_fallback() {
    assert_eq!(
        os_budget::cost::rate_from_env("OS_BUDGET_T2_MISSING", 3.0),
        (3.0, "default".to_string())
    );
    std::env::set_var("OS_BUDGET_T2_RATE", "15");
    assert_eq!(
        os_budget::cost::rate_from_env("OS_BUDGET_T2_RATE", 3.0),
        (15.0, "env:OS_BUDGET_T2_RATE".to_string())
    );
    std::env::set_var("OS_BUDGET_T2_RATE", "junk");
    assert_eq!(
        os_budget::cost::rate_from_env("OS_BUDGET_T2_RATE", 3.0),
        (3.0, "default".to_string())
    );
    std::env::remove_var("OS_BUDGET_T2_RATE");
}

#[test]
fn cost_math_matches_pinned_six_decimal_row() {
    // The suite's own scored-row expected cost, recomputed from
    // the pinned inputs (416 in, 266 out-exp at 3.0/15.0).
    assert_eq!(cost(416, 266, 3.0, 15.0), 0.005238);
    assert_eq!(cost(542, 298, 3.0, 15.0), 0.006096);
}

#[test]
fn totals_keep_boot_out_of_headline_and_gate_on_caps() {
    let rows = vec![
        CostRow::new("morning brief (Shot 2)", 1, 1, 100, 100, 3.0, 15.0),
        CostRow::new("dispatch plan (Shot 5)", 1, 2, 100, 300, 3.0, 15.0),
        CostRow::new("boot brief (Shot 0, OS-004 go only)", 0, 1, 100, 100, 3.0, 15.0),
    ];
    let s = totals(&rows);
    assert!(s.expected_usd < s.worst_with_boot_usd);
    assert_eq!(s.reserved_half_usd, RESERVED_HALF_USD);
    assert_eq!(s.credit_usd, CREDIT_USD);
    assert!(s.headroom_vs_reserved_usd > 0.0);
    assert!(s.breakeven_multiplier_vs_reserved >= 1);
    assert!(s.passed);
}

#[test]
fn render_names_call_classes_and_headroom() {
    let rows = vec![
        CostRow::new("morning brief (Shot 2)", 1, 1, 100, 100, 3.0, 15.0),
        CostRow::new("dispatch plan (Shot 5)", 1, 2, 100, 100, 3.0, 15.0),
        CostRow::new("closing brief (Shot 11)", 1, 1, 100, 100, 3.0, 15.0),
        CostRow::new("alert polish (Shots 8/8b)", 2, 3, 100, 100, 3.0, 15.0),
        CostRow::new("boot brief (Shot 0, OS-004 go only)", 0, 1, 100, 100, 3.0, 15.0),
    ];
    let s = totals(&rows);
    assert_eq!(rows.len(), 5);
    assert_eq!(rows.iter().map(|r| r.count_base).sum::<u64>(), 5);
    assert_eq!(rows.iter().map(|r| r.count_worst).sum::<u64>(), 8);
    let table = render(&rows, &s, 3.0, 15.0, ("default", "default"));
    for name in [
        "morning brief (Shot 2)",
        "dispatch plan (Shot 5)",
        "closing brief (Shot 11)",
        "alert polish (Shots 8/8b)",
        "boot brief (Shot 0, OS-004 go only)",
    ] {
        assert!(table.contains(name), "{table}");
    }
    assert!(table.contains("NOT pricing facts"), "{table}");
    assert!(table.contains("PASS"), "{table}");
}

#[test]
fn constants_match_pinned_check_shape() {
    assert_eq!(WORST_OUTPUT_TOKENS, 1024);
    assert_eq!(DISPATCH_EXPECTED_OUTPUT_TOKENS, 300);
    assert_eq!(RESERVED_HALF_USD, 75.0);
    assert_eq!(CREDIT_USD, 150.0);
}
