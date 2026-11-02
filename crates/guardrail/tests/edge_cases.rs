//! Edge cases for the `guardrail` crate (B159): empty, maximum,
//! duplicate and out-of-order inputs, one named test each plus the
//! boundaries the budget maths turns on.

use guardrail::{
    build_prompt, check, estimate, load_state, record, status_of, unwrap_model_text,
    GuardrailState, TEST_BUDGET_USD,
};
use std::path::PathBuf;

fn tmp_path(name: &str) -> PathBuf {
    let p = std::env::temp_dir().join(format!(
        "guardrail-edge-{}-{name}.json",
        std::process::id()
    ));
    let _ = std::fs::remove_file(&p);
    p
}

fn path_str(p: &PathBuf) -> String {
    p.to_string_lossy().to_string()
}

#[test]
fn empty_input_builds_a_prompt_without_panicking() {
    let p = build_prompt("", "", "", &[], "", "", None);
    assert!(p.contains("You are the visual assessment model for  ()."));
    assert!(p.contains("Categories (assessment.category and every observation category must be one of these): ."));
    assert!(p.contains("Limits: "));
}

#[test]
fn maximum_input_builds_a_prompt_and_a_finite_estimate() {
    let big = "x".repeat(1_000_000);
    let cats = ["a".repeat(1_000_000)];
    let cat_refs: Vec<&str> = cats.iter().map(String::as_str).collect();
    let p = build_prompt(&big, &big, &big, &cat_refs, &big, &big, Some(&big));
    assert!(p.len() > 4_000_000);
    assert!(estimate(u64::MAX, u64::MAX).is_finite());
}

#[test]
fn duplicate_input_is_counted_each_time_not_deduplicated() {
    let p = tmp_path("duplicate");
    record(&path_str(&p), "assess:ignis", "muse-spark-1.3", 1000, 1000, 1);
    record(&path_str(&p), "assess:ignis", "muse-spark-1.3", 1000, 1000, 1);
    let st = load_state(&path_str(&p));
    assert_eq!(st.calls, 2);
    assert_eq!(st.log.len(), 2);
    assert!((st.est_cost_usd - 0.011).abs() < 1e-9);
}

#[test]
fn out_of_order_latency_is_kept_in_call_order() {
    let p = tmp_path("out-of-order");
    record(&path_str(&p), "assess:ignis", "muse-spark-1.3", 10, 10, 9999);
    record(&path_str(&p), "assess:ignis", "muse-spark-1.3", 10, 10, 0);
    let st = load_state(&path_str(&p));
    assert_eq!(st.log[0].latency_ms, 9999);
    assert_eq!(st.log[1].latency_ms, 0);
    assert!(st.log[1].cum_est_cost_usd >= st.log[0].cum_est_cost_usd);
}

#[test]
fn cumulative_cost_is_rounded_to_six_decimals() {
    let p = tmp_path("rounding");
    record(&path_str(&p), "assess:ignis", "muse-spark-1.3", 333, 777, 1);
    let st = load_state(&path_str(&p));
    let reprojected = (st.est_cost_usd * 1e6).round() / 1e6;
    assert!((reprojected - st.est_cost_usd).abs() < 1e-12);
}

#[test]
fn zero_tokens_cost_nothing_but_still_count_the_call() {
    let p = tmp_path("zero");
    let est = record(&path_str(&p), "assess:ignis", "muse-spark-1.3", 0, 0, 0);
    assert_eq!(est, 0.0);
    let st = load_state(&path_str(&p));
    assert_eq!(st.calls, 1);
    assert_eq!(st.est_cost_usd, 0.0);
    assert!(check(&st).is_ok());
}

#[test]
fn one_input_token_costs_the_published_rate() {
    assert!((estimate(1, 0) - 1.25e-6).abs() < 1e-15);
}

#[test]
fn status_goes_negative_once_the_budget_is_passed() {
    let st = GuardrailState {
        calls: 1,
        est_cost_usd: TEST_BUDGET_USD + 5.0,
        log: vec![],
    };
    let v = status_of(&st);
    assert_eq!(v["remaining_usd"].as_f64().unwrap(), -5.0);
    assert!(check(&st).is_err());
}

#[test]
fn a_fence_after_prose_still_yields_the_object() {
    let out = unwrap_model_text("result:\n```json\n{\"a\":1}\n```\n");
    assert_eq!(out, "{\"a\":1}");
}

#[test]
fn product_and_profile_fields_appear_verbatim_in_the_prompt() {
    let p = build_prompt(
        "vigiles",
        "Vigiles",
        "Public safety",
        &["normal activity", "crowd gathered"],
        "no identity claims",
        "2026-11-02T12:00:00Z",
        None,
    );
    assert!(p.contains("\"product\": \"vigiles\""));
    assert!(p.contains("\"timestamp\": \"2026-11-02T12:00:00Z\""));
    assert!(p.contains("normal activity, crowd gathered"));
    assert!(p.contains("(Public safety)"));
    assert!(p.contains("no identity claims"));
}
