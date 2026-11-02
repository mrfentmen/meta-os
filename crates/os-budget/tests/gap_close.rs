//! Test-gap close (B071).
//!
//! The crate's least-covered sections were cost_check and
//! brief_cost_check (3 tests each) against the gate/forecast sections
//! (18 each). These tests bring both sections up to the same depth by
//! covering the paths their three cases did not: constants, prompt
//! construction, row assembly, totals edge shapes, rendering flags,
//! determinism, and the template record.

use os_budget::*;
use std::collections::BTreeMap;

const NOW: f64 = 1_793_093_400.0;

fn dispatch_text() -> String {
    let path = format!(
        "{}/../../os/intel/prompts/dispatch.md",
        env!("CARGO_MANIFEST_DIR")
    );
    std::fs::read_to_string(path).expect("dispatch.md readable in checkout")
}

fn row(call: &str, count_base: i64, count_worst: i64, worst: f64) -> CostRow {
    CostRow {
        call: call.to_string(),
        count_base,
        count_worst,
        tokens_in: 100,
        tokens_out_expected: 50,
        tokens_out_worst: 1024,
        cost_expected: 0.0,
        cost_worst: worst,
    }
}

fn brief_row(variant: &str, worst: f64) -> BriefCostRow {
    BriefCostRow {
        variant: variant.to_string(),
        jobs: 22,
        template_words: 200,
        template_actual_usd: 0.0,
        tokens_in: 100,
        tokens_out_expected: 50,
        tokens_out_worst: 1024,
        cost_expected: 0.0,
        cost_worst: worst,
        rate_sources: BTreeMap::new(),
    }
}

// --- cost_check: 15 cases --------------------------------------------

#[test]
fn cost_zero_tokens_is_zero() {
    assert_eq!(cost(0, 0, 3.0, 15.0), 0.0);
    assert_eq!(round6(0.0), 0.0);
}

#[test]
fn cost_uses_both_rates() {
    // 1M input at $3 + 1M output at $15.
    assert!((cost(1_000_000, 1_000_000, 3.0, 15.0) - 18.0).abs() < 1e-12);
    // Input only.
    assert!((cost(1_000_000, 0, 3.0, 15.0) - 3.0).abs() < 1e-12);
}

#[test]
fn round6_rounds_to_six_places() {
    assert_eq!(round6(1.2345674), 1.234567);
    assert_eq!(round6(1.2345676), 1.234568);
    assert_eq!(round6(-1.2345676), -1.234568);
}

#[test]
fn demo_snapshot_shape() {
    let snapshot = demo_snapshot();
    let jobs = match snapshot.get("jobs") {
        Some(Value::List(j)) => j.clone(),
        _ => panic!("jobs"),
    };
    let alerts = match snapshot.get("alerts") {
        Some(Value::List(a)) => a.clone(),
        _ => panic!("alerts"),
    };
    let messages = match snapshot.get("messages") {
        Some(Value::List(m)) => m.clone(),
        _ => panic!("messages"),
    };
    assert_eq!(jobs.len(), 5);
    assert_eq!(alerts.len(), 2);
    assert_eq!(messages.len(), 3);
    assert_eq!(
        jobs.iter()
            .filter(|j| j.get("status") == Some(&v_str("blocked")))
            .count(),
        1
    );
}

#[test]
fn brief_prompt_names_kind_and_budget() {
    let prompt = brief_prompt(&demo_snapshot(), "morning");
    assert!(prompt.contains("Write a morning brief"));
    assert!(prompt.contains("Keep it under 220 words"));
    assert!(prompt.contains("Do not invent facts"));
    assert!(prompt.contains("Sections:"));
}

#[test]
fn polish_prompt_carries_the_facts_rule() {
    let prompt = polish_prompt("two jobs claim intel/status.py");
    assert!(prompt.contains("Do not add, remove, or change any facts"));
    assert!(prompt.ends_with("two jobs claim intel/status.py"));
}

#[test]
fn build_rows_has_five_classes_and_counts() {
    let (rows, rate_in, rate_out, sources) = build_rows(&dispatch_text());
    assert_eq!(rows.len(), 5);
    assert_eq!(rate_in, 3.0);
    assert_eq!(rate_out, 15.0);
    assert!(sources.contains_key("in") && sources.contains_key("out"));
    assert_eq!(rows.iter().map(|r| r.count_base).sum::<i64>(), 5);
    assert_eq!(rows.iter().map(|r| r.count_worst).sum::<i64>(), 8);
    assert!(rows.iter().any(|r| r.call.contains("boot brief") && r.count_base == 0));
}

#[test]
fn build_rows_matches_the_disk_reader() {
    let text = dispatch_text();
    let (from_text, _, _, _) = build_rows(&text);
    let (from_disk, _, _, _) = build_rows_from_disk().expect("dispatch.md readable");
    assert_eq!(from_text, from_disk);
}

#[test]
fn cost_totals_excludes_boot_from_headline() {
    let rows = vec![row("core", 1, 1, 10.0), row("boot", 0, 1, 5.0)];
    let totals = cost_totals(&rows);
    assert!((totals.worst_usd - 10.0).abs() < 1e-12);
    assert!((totals.worst_with_boot_usd - 15.0).abs() < 1e-12);
    assert!((totals.headroom_vs_reserved_usd - 60.0).abs() < 1e-12);
    assert!(totals.passed);
}

#[test]
fn cost_totals_zero_worst_has_zero_breakeven() {
    let rows = vec![row("core", 1, 1, 0.0), row("boot", 0, 1, 0.0)];
    let totals = cost_totals(&rows);
    assert_eq!(totals.worst_with_boot_usd, 0.0);
    assert_eq!(totals.breakeven_multiplier_vs_reserved, 0);
    assert!(totals.passed);
}

#[test]
fn render_cost_table_names_every_class() {
    let (rows, rate_in, rate_out, sources) = build_rows(&dispatch_text());
    let totals = cost_totals(&rows);
    let table = render_cost_table(&rows, &totals, rate_in, rate_out, &sources);
    for call in [
        "morning brief (Shot 2)",
        "dispatch plan (Shot 5)",
        "closing brief (Shot 11)",
        "alert polish (Shots 8/8b)",
        "boot brief (Shot 0, OS-004 go only)",
    ] {
        assert!(table.contains(call), "missing {}", call);
    }
    assert!(table.contains("expected demo day:"));
    assert!(table.contains("reserved half (GOV-001):"));
    assert!(table.contains("NOT pricing facts"));
}

#[test]
fn run_cost_check_returns_a_passing_code() {
    let (rows, totals, table, code) = run_cost_check(&dispatch_text());
    assert_eq!(code, if totals.passed { 0 } else { 1 });
    assert_eq!(code, 0);
    assert_eq!(rows.len(), 5);
    assert!(table.contains("PASS"));
}

#[test]
fn brief_budget_kinds() {
    assert_eq!(brief_budget("onjoin"), 150);
    assert_eq!(brief_budget("ondemand"), 300);
    assert_eq!(brief_budget("morning"), 220);
    assert_eq!(brief_budget("anything-else"), 220);
}

#[test]
fn estimate_tokens_counts_characters_not_bytes() {
    // One em dash is 3 bytes but 1 character: byte counting would
    // overestimate this crate's dispatch row.
    assert_eq!(estimate_tokens("—"), 1);
    assert_eq!(estimate_tokens("—————"), 2);
    assert_eq!(estimate_tokens("aaaaa"), 2);
    assert_eq!(estimate_tokens(""), 0);
}

#[test]
fn build_rows_expected_output_for_dispatch_is_the_proxy() {
    let (rows, _, _, _) = build_rows(&dispatch_text());
    let dispatch = rows
        .iter()
        .find(|r| r.call.contains("dispatch plan"))
        .expect("dispatch row");
    assert_eq!(
        dispatch.tokens_out_expected,
        DISPATCH_EXPECTED_OUTPUT_TOKENS
    );
    assert_eq!(dispatch.tokens_out_worst, WORST_OUTPUT_TOKENS);
}

// --- brief_cost_check: 15 cases --------------------------------------

#[test]
fn busy_snapshot_has_22_jobs_and_6_owners() {
    let snapshot = busy_snapshot(false);
    assert_eq!(
        match snapshot.get("jobs") {
            Some(Value::List(j)) => j.len(),
            _ => 0,
        },
        22
    );
    assert_eq!(extract_owners(&snapshot).len(), 6);
    assert_eq!(
        match snapshot.get("alerts") {
            Some(Value::List(a)) => a.len(),
            _ => 0,
        },
        2
    );
}

#[test]
fn busy_snapshot_long_titles_variant() {
    let short = busy_snapshot(false);
    let long = busy_snapshot(true);
    let first_title = |snapshot: &Value| match snapshot.get("jobs") {
        Some(Value::List(j)) => match j[0].get("title") {
            Some(Value::Str(s)) => s.clone(),
            _ => String::new(),
        },
        _ => String::new(),
    };
    assert!(!first_title(&short).contains("long descriptive"));
    assert!(first_title(&long).contains("with a long descriptive title here now"));
    assert_eq!(first_title(&long).split_whitespace().count(), 9);
}

#[test]
fn brief_cost_claims_are_ten_and_match_the_manifest() {
    assert_eq!(BRIEF_COST_CLAIMS.len(), 10);
    let count = |nick: &str| BRIEF_COST_CLAIMS.iter().filter(|(n, _)| *n == nick).count();
    assert_eq!(count("milo"), 2);
    assert_eq!(count("rowan"), 2);
    assert_eq!(count("buffy"), 2);
    assert_eq!(count("del"), 2);
    assert_eq!(count("hana"), 1);
    assert_eq!(count("pax"), 1);
    assert_eq!(BRIEF_COST_OPEN.len(), 6);
    assert_eq!(BRIEF_COST_BLOCKED.len(), 3);
    assert_eq!(BRIEF_COST_DONE.len(), 3);
}

#[test]
fn measure_scored_variant_shape() {
    let (row, rate_in, rate_out) = measure_brief_cost(false, NOW);
    assert_eq!(row.variant, "scored 2-word titles");
    assert_eq!(row.jobs, 22);
    assert_eq!(rate_in, 3.0);
    assert_eq!(rate_out, 15.0);
    assert!(row.tokens_in > 0);
    assert!(row.tokens_out_expected > 0);
    assert!(row.cost_expected > 0.0);
    assert!(row.cost_worst > row.cost_expected);
    assert_eq!(row.rate_sources.get("in").map(|s| s.as_str()), Some("default"));
}

#[test]
fn measure_long_variant_shape() {
    let (row, _, _) = measure_brief_cost(true, NOW);
    assert_eq!(row.variant, "long-title stress");
    assert_eq!(row.jobs, 22);
    assert!(row.tokens_in > 0);
    assert!(row.cost_worst < RESERVED_HALF_USD);
}

#[test]
fn measure_template_fits_the_morning_budget() {
    for long_titles in [false, true] {
        let (row, _, _) = measure_brief_cost(long_titles, NOW);
        assert!(
            row.template_words <= 220,
            "{} template_words={}",
            row.variant,
            row.template_words
        );
    }
}

#[test]
fn measure_actual_spend_is_zero() {
    for long_titles in [false, true] {
        let (row, _, _) = measure_brief_cost(long_titles, NOW);
        assert_eq!(row.template_actual_usd, 0.0);
        assert_eq!(row.tokens_out_worst, WORST_OUTPUT_TOKENS);
    }
}

#[test]
fn build_rows_returns_both_variants() {
    let (rows, rate_in, rate_out) = build_brief_cost_rows(NOW);
    assert_eq!(rows.len(), 2);
    assert_eq!(rows[0].variant, "scored 2-word titles");
    assert_eq!(rows[1].variant, "long-title stress");
    assert_eq!(rate_in, 3.0);
    assert_eq!(rate_out, 15.0);
}

#[test]
fn build_rows_is_deterministic() {
    let (first, _, _) = build_brief_cost_rows(NOW);
    let (second, _, _) = build_brief_cost_rows(NOW);
    assert_eq!(first, second);
}

#[test]
fn render_brief_cost_table_names_the_ledger_note() {
    let (rows, rate_in, rate_out) = build_brief_cost_rows(NOW);
    let (text, _) = render_brief_cost_table(&rows, rate_in, rate_out);
    assert!(text.contains("BRF-027 busy-fixture brief cost check"));
    assert!(text.contains("no ledger entry written"));
    assert!(text.contains("template actual (both variants): $0.0000"));
}

#[test]
fn render_brief_cost_table_passes_under_the_caps() {
    let (rows, rate_in, rate_out) = build_brief_cost_rows(NOW);
    let (text, passed) = render_brief_cost_table(&rows, rate_in, rate_out);
    assert!(passed);
    assert!(text.contains("PASS"));
}

#[test]
fn render_brief_cost_table_breakeven_uses_the_worst_row() {
    // Worst is 10, so floor(75 / 10) = 7.
    let rows = vec![brief_row("a", 5.0), brief_row("b", 10.0)];
    let (text, passed) = render_brief_cost_table(&rows, 3.0, 15.0);
    assert!(passed);
    assert!(text.contains("7x"), "{}", text);
}

#[test]
fn run_brief_cost_check_returns_zero() {
    let (rows, passed, text, code) = run_brief_cost_check(NOW);
    assert_eq!(rows.len(), 2);
    assert!(passed);
    assert_eq!(code, 0);
    assert!(text.contains("PASS"));
}

#[test]
fn template_record_passes_kind_through() {
    let (text, record) = template_brief_record(&demo_snapshot(), "ondemand", NOW);
    assert!(text.starts_with("TEMPLATE"));
    assert_eq!(record.model, "template");
    assert_eq!(record.spend_id, None);
    assert_eq!(record.kind, "ondemand");
}

#[test]
fn measure_tokens_in_matches_brief_prompt() {
    let snapshot = busy_snapshot(false);
    let (row, _, _) = measure_brief_cost(false, NOW);
    assert_eq!(row.tokens_in, estimate_tokens(&brief_prompt(&snapshot, "morning")));
}
