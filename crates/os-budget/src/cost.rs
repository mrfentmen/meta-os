//! Cost checks: INT-007 demo-day Spark cost (Milo lane) and
//! BRF-027 busy-brief cost (`os/intel/cost_check.py`,
//! `os/intel/brief_cost_check.py`).
//!
//! Measurement caveat (read before quoting a total): the exact
//! per-call token counts are measured from Hana's `intel` crate
//! (`brief.py` extractors/composers, `spark_client._estimate_tokens`,
//! `intel/prompts/dispatch.md`, B09/B10/B11). Those modules are not
//! ported here, so the exact-measurement rows are **carried
//! pending the intel crate** — named in the report, never faked.
//! This module ports everything the checks own outright: the
//! rate rule (env overrides or the client's placeholder estimate
//! rates), the six-decimal cost math, the headline totals
//! (expected/worst/with-boot/headroom/breakeven), the table
//! rendering, and the demo fixture constants. All dollar totals
//! remain projections at placeholder rates, never pricing facts.

/// The client's estimate rates (labeled in the client source,
/// verbatim, "Planning placeholders for cost estimates only --
/// NOT pricing facts"). Canonical home: `intel/spark_client.py`
/// (Hana B11); repeated here as the constants the checks read.
pub const DEFAULT_RATE_IN_PER_MTOK: f64 = 3.0;
pub const DEFAULT_RATE_OUT_PER_MTOK: f64 = 15.0;

pub const CREDIT_USD: f64 = 150.0;
pub const RESERVED_HALF_USD: f64 = 75.0;
pub const WORST_OUTPUT_TOKENS: u64 = 1024;
pub const DISPATCH_EXPECTED_OUTPUT_TOKENS: u64 = 300;

/// One env-overridable rate: blank/unparseable falls back to the
/// default. Mirrors `cost_check._rate`.
pub fn rate_from_env(name: &str, default: f64) -> (f64, String) {
    match std::env::var(name) {
        Ok(raw) => {
            let raw = raw.trim();
            if raw.is_empty() {
                (default, "default".to_string())
            } else {
                match raw.parse::<f64>() {
                    Ok(v) => (v, format!("env:{name}")),
                    Err(_) => (default, "default".to_string()),
                }
            }
        }
        Err(_) => (default, "default".to_string()),
    }
}

/// `(in_rate, out_rate, in_source, out_source)` from env overrides
/// or defaults. Mirrors `cost_check.rates`.
pub fn rates() -> (f64, f64, String, String) {
    let (rate_in, src_in) = rate_from_env("META_MODEL_API_INPUT_USD_PER_MTOK", DEFAULT_RATE_IN_PER_MTOK);
    let (rate_out, src_out) = rate_from_env("META_MODEL_API_OUTPUT_USD_PER_MTOK", DEFAULT_RATE_OUT_PER_MTOK);
    (rate_in, rate_out, src_in, src_out)
}

/// Six-decimal cost of one call class. Mirrors `cost_check._cost`.
pub fn cost(tokens_in: u64, tokens_out: u64, rate_in: f64, rate_out: f64) -> f64 {
    round6(tokens_in as f64 * rate_in / 1_000_000.0 + tokens_out as f64 * rate_out / 1_000_000.0)
}

fn round6(v: f64) -> f64 {
    (v * 1_000_000.0).round() / 1_000_000.0
}

/// One cost-table row: one demo-day call class.
#[derive(Debug, Clone)]
pub struct CostRow {
    pub call: String,
    pub count_base: u64,
    pub count_worst: u64,
    pub tokens_in: u64,
    pub tokens_out_expected: u64,
    pub tokens_out_worst: u64,
    pub cost_expected: f64,
    pub cost_worst: f64,
}

impl CostRow {
    pub fn new(
        call: &str,
        count_base: u64,
        count_worst: u64,
        tokens_in: u64,
        tokens_out_expected: u64,
        rate_in: f64,
        rate_out: f64,
    ) -> Self {
        CostRow {
            call: call.to_string(),
            count_base,
            count_worst,
            tokens_in,
            tokens_out_expected,
            tokens_out_worst: WORST_OUTPUT_TOKENS,
            cost_expected: cost(tokens_in * count_base, tokens_out_expected * count_base, rate_in, rate_out),
            cost_worst: cost(tokens_in * count_worst, WORST_OUTPUT_TOKENS * count_worst, rate_in, rate_out),
        }
    }
}

/// Headline totals; boot brief kept out of the headline.
/// Mirrors `cost_check.totals`.
#[derive(Debug, Clone)]
pub struct CostTotals {
    pub expected_usd: f64,
    pub worst_usd: f64,
    pub worst_with_boot_usd: f64,
    pub reserved_half_usd: f64,
    pub credit_usd: f64,
    pub headroom_vs_reserved_usd: f64,
    pub breakeven_multiplier_vs_reserved: u64,
    pub passed: bool,
}

pub fn totals(rows: &[CostRow]) -> CostTotals {
    let core: Vec<&CostRow> = rows.iter().filter(|r| r.count_base > 0).collect();
    let expected = round6(core.iter().map(|r| r.cost_expected).sum());
    let worst = round6(core.iter().map(|r| r.cost_worst).sum());
    let boot_worst = rows
        .iter()
        .find(|r| r.count_base == 0)
        .map(|r| r.cost_worst)
        .unwrap_or(0.0);
    let worst_with_boot = round6(worst + boot_worst);
    let breakeven = if worst_with_boot > 0.0 {
        (RESERVED_HALF_USD / worst_with_boot).floor() as u64
    } else {
        0
    };
    CostTotals {
        expected_usd: expected,
        worst_usd: worst,
        worst_with_boot_usd: worst_with_boot,
        reserved_half_usd: RESERVED_HALF_USD,
        credit_usd: CREDIT_USD,
        headroom_vs_reserved_usd: round6(RESERVED_HALF_USD - worst_with_boot),
        breakeven_multiplier_vs_reserved: breakeven,
        passed: worst_with_boot < RESERVED_HALF_USD && worst_with_boot < CREDIT_USD,
    }
}

/// The cost table, as text. Mirrors `cost_check.render`.
pub fn render(rows: &[CostRow], summary: &CostTotals, rate_in: f64, rate_out: f64, sources: (&str, &str)) -> String {
    let mut lines = vec![
        "INT-007 demo-day Spark cost check".to_string(),
        format!(
            "rates: in ${rate_in}/Mtok ({}), out ${rate_out}/Mtok ({}) -- client defaults are planning placeholders, NOT pricing facts (see module docstring)",
            sources.0, sources.1
        ),
        "transport note: primary agent transport carries no API cost; totals below are the HTTP fallback case".to_string(),
        String::new(),
        format!(
            "{:38} {:>4} {:>5} {:>7} {:>11} {:>9} {:>9}",
            "call", "base", "worst", "tok_in", "tok_out_exp", "$exp", "$worst"
        ),
    ];
    for row in rows {
        lines.push(format!(
            "{:38} {:>4} {:>5} {:>7} {:>11} {:>9.4} {:>9.4}",
            row.call,
            row.count_base,
            row.count_worst,
            row.tokens_in,
            row.tokens_out_expected,
            row.cost_expected,
            row.cost_worst
        ));
    }
    lines.extend(vec![
        String::new(),
        format!("expected demo day: ${:.4}", summary.expected_usd),
        format!("worst demo day: ${:.4}", summary.worst_usd),
        format!("worst with boot brief: ${:.4}", summary.worst_with_boot_usd),
        format!(
            "reserved half (GOV-001): ${:.2}; headroom: ${:.4}",
            summary.reserved_half_usd, summary.headroom_vs_reserved_usd
        ),
        format!(
            "credit: ${:.2}; real rates would have to exceed placeholder rates by {}x before the reserved half is breached",
            summary.credit_usd, summary.breakeven_multiplier_vs_reserved
        ),
        (if summary.passed { "PASS" } else { "FAIL" }).to_string(),
    ]);
    lines.join("\n") + "\n"
}

/// The INT-007 demo goal (the call inventory's fixed fixture).
pub const DEMO_GOAL: &str = "Build a small status page feature for the relay repo: an intel status module with tests, a viewer panel stub, docs for both, and a review pass -- each as separate jobs with clear file ownership.";

/// The BRF-027 busy-snapshot shape constants the check pins:
/// 22 jobs (10 claimed, 6 open, 3 blocked, 3 done).
pub const BRF027_JOB_COUNT: usize = 22;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn estimate_rates_are_the_client_placeholders() {
        let (rate_in, rate_out, src_in, src_out) = rates();
        // Pinned by test_intel_cost / test_intel_brief_cost — unless
        // the harness overrides the env (then sources say env:).
        if src_in == "default" && src_out == "default" {
            assert_eq!(rate_in, 3.0);
            assert_eq!(rate_out, 15.0);
        }
        assert_eq!(DEFAULT_RATE_IN_PER_MTOK, 3.0);
        assert_eq!(DEFAULT_RATE_OUT_PER_MTOK, 15.0);
    }

    #[test]
    fn rate_env_override_and_bad_input_fallback() {
        assert_eq!(rate_from_env("OS_BUDGET_TEST_RATE_MISSING", 3.0), (3.0, "default".to_string()));
        std::env::set_var("OS_BUDGET_TEST_RATE", "9.5");
        assert_eq!(rate_from_env("OS_BUDGET_TEST_RATE", 3.0), (9.5, "env:OS_BUDGET_TEST_RATE".to_string()));
        std::env::set_var("OS_BUDGET_TEST_RATE", "  ");
        assert_eq!(rate_from_env("OS_BUDGET_TEST_RATE", 3.0), (3.0, "default".to_string()));
        std::env::set_var("OS_BUDGET_TEST_RATE", "junk");
        assert_eq!(rate_from_env("OS_BUDGET_TEST_RATE", 3.0), (3.0, "default".to_string()));
        std::env::remove_var("OS_BUDGET_TEST_RATE");
    }

    #[test]
    fn cost_math_rounds_to_six_decimals() {
        // 416 in * 3.0 + 266 out * 15.0 per million, six decimals.
        assert_eq!(cost(416, 266, 3.0, 15.0), 0.005238);
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
        assert_eq!(s.reserved_half_usd, 75.0);
        assert_eq!(s.credit_usd, 150.0);
        assert!(s.headroom_vs_reserved_usd > 0.0);
        assert!(s.breakeven_multiplier_vs_reserved >= 1);
        assert!(s.passed);
    }

    #[test]
    fn render_names_rows_and_headroom() {
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
    fn demo_fixture_constants() {
        assert!(!DEMO_GOAL.is_empty());
        assert_eq!(WORST_OUTPUT_TOKENS, 1024);
        assert_eq!(DISPATCH_EXPECTED_OUTPUT_TOKENS, 300);
        assert_eq!(BRF027_JOB_COUNT, 22);
    }
}
