//! Error paths for the `guardrail` crate (B158).
//!
//! Every test asserts the behaviour the code actually has, including the
//! documented swallow points (B161 gaps G1-G3): a corrupt ledger reads as
//! zero, and a failed save is ignored. Those are pinned here so a future
//! change to either is a visible test change, not a silent drift.

use guardrail::{
    build_prompt, check, estimate, load_state, record, save_state, unwrap_model_text,
    GuardrailState, UsageLog, TEST_BUDGET_USD,
};
use std::path::PathBuf;

fn tmp_path(name: &str) -> PathBuf {
    let p = std::env::temp_dir().join(format!(
        "guardrail-error-{}-{name}.json",
        std::process::id()
    ));
    let _ = std::fs::remove_file(&p);
    p
}

fn path_str(p: &PathBuf) -> String {
    p.to_string_lossy().to_string()
}

#[test]
fn check_at_budget_refuses_with_the_python_message() {
    let st = GuardrailState {
        calls: 0,
        est_cost_usd: TEST_BUDGET_USD,
        log: vec![],
    };
    let err = check(&st).expect_err("at-budget state must refuse");
    assert_eq!(
        err.to_string(),
        format!(
            "GUARDRAIL STOP: estimated test spend ${:.4} has reached the ${:.2} test budget. No call sent.",
            TEST_BUDGET_USD, TEST_BUDGET_USD
        )
    );
}

#[test]
fn check_over_budget_refuses() {
    let st = GuardrailState {
        calls: 1,
        est_cost_usd: TEST_BUDGET_USD + 0.0001,
        log: vec![],
    };
    assert!(check(&st).is_err());
}

#[test]
fn check_just_under_budget_passes() {
    let st = GuardrailState {
        calls: 1,
        est_cost_usd: TEST_BUDGET_USD - 0.000001,
        log: vec![],
    };
    assert!(check(&st).is_ok());
}

#[test]
fn missing_ledger_reads_as_zero() {
    let p = tmp_path("missing");
    let st = load_state(&path_str(&p));
    assert_eq!(st.calls, 0);
    assert_eq!(st.est_cost_usd, 0.0);
    assert!(st.log.is_empty());
}

#[test]
fn corrupt_ledger_reads_as_zero_instead_of_refusing() {
    let p = tmp_path("corrupt");
    std::fs::write(&p, "this is not json").unwrap();
    let st = load_state(&path_str(&p));
    assert_eq!(st.calls, 0);
    assert_eq!(st.est_cost_usd, 0.0);
}

#[test]
fn wrong_shape_ledger_reads_as_zero() {
    let p = tmp_path("wrong-shape");
    std::fs::write(&p, r#"{"calls":"many","est_cost_usd":"lots","log":{}}"#).unwrap();
    let st = load_state(&path_str(&p));
    assert_eq!(st.calls, 0);
}

#[test]
fn empty_object_uses_serde_defaults() {
    let p = tmp_path("empty-object");
    std::fs::write(&p, "{}").unwrap();
    let st = load_state(&path_str(&p));
    assert_eq!(st.calls, 0);
    assert_eq!(st.est_cost_usd, 0.0);
    assert!(st.log.is_empty());
}

#[test]
fn save_to_an_unwritable_path_is_silent() {
    let st = GuardrailState::default();
    // A directory that does not exist: write fails, no panic, no error value.
    save_state("/guardrail-no-such-dir-b158/ledger.json", &st);
}

#[test]
fn record_into_an_unwritable_path_still_returns_the_estimate() {
    let est = record(
        "/guardrail-no-such-dir-b158/ledger.json",
        "assess:ignis",
        "muse-spark-1.3",
        1000,
        1000,
        5,
    );
    assert!(est > 0.0);
    assert!(est < 0.01);
}

#[test]
fn empty_model_text_unwraps_to_an_empty_string() {
    assert_eq!(unwrap_model_text(""), "");
    assert_eq!(unwrap_model_text("   \n  "), "");
}

#[test]
fn text_without_an_object_is_returned_trimmed() {
    assert_eq!(unwrap_model_text("  no object here  "), "no object here");
}

#[test]
fn an_unclosed_fence_keeps_its_body() {
    let out = unwrap_model_text("```json\n{\"a\":1}");
    assert_eq!(out, "{\"a\":1}");
}

#[test]
fn prose_around_the_object_is_dropped() {
    let out = unwrap_model_text("Here you go: {\"a\":1} thanks");
    assert_eq!(out, "{\"a\":1}");
}

#[test]
fn a_non_object_with_braces_is_returned_as_the_slice() {
    // The crate slices first `{` to last `}` without parsing: garbage in,
    // garbage out, and the caller's JSON parse is the thing that refuses.
    let out = unwrap_model_text("x {not json} y");
    assert_eq!(out, "{not json}");
}

#[test]
fn build_prompt_appends_the_correction_block_when_given() {
    let p = build_prompt(
        "ignis",
        "Ignis",
        "Fire",
        &["smoke"],
        "visible only",
        "2026-11-02T00:00:00Z",
        Some("assessment.category was missing"),
    );
    assert!(p.contains("CORRECTION: a previous reply for this same frame failed these contract checks: assessment.category was missing"));
    assert!(p.contains("Do not repeat the failed checks."));
}

#[test]
fn build_prompt_omits_the_correction_block_without_one() {
    let p = build_prompt(
        "ignis",
        "Ignis",
        "Fire",
        &["smoke"],
        "visible only",
        "2026-11-02T00:00:00Z",
        None,
    );
    assert!(!p.contains("CORRECTION:"));
}

#[test]
fn estimate_never_mixes_the_two_rates() {
    // Input-only and output-only are separate; a transposed rate is a
    // budget error, so pin both ends.
    let input_only = estimate(1_000_000, 0);
    let output_only = estimate(0, 1_000_000);
    assert!((input_only - 1.25).abs() < 1e-9);
    assert!((output_only - 4.25).abs() < 1e-9);
    assert!((estimate(1_000_000, 1_000_000) - 5.5).abs() < 1e-9);
}

#[test]
fn a_logged_record_carries_the_fixed_timestamp() {
    let p = tmp_path("timestamp");
    record(&path_str(&p), "assess:ignis", "muse-spark-1.3", 1, 1, 1);
    let st = load_state(&path_str(&p));
    assert_eq!(st.log.len(), 1);
    assert_eq!(st.log[0].ts, "2026-10-30T00:00:00Z");
}

#[test]
fn a_hand_written_state_with_a_log_round_trips() {
    let p = tmp_path("round-trip");
    let st = GuardrailState {
        calls: 2,
        est_cost_usd: 0.5,
        log: vec![UsageLog {
            ts: "2026-10-30T00:00:00Z".into(),
            kind: "assess:vigiles".into(),
            model: "muse-spark-1.3".into(),
            input_tokens: 10,
            output_tokens: 20,
            latency_ms: 30,
            est_cost_usd: 0.25,
            cum_est_cost_usd: 0.5,
        }],
    };
    save_state(&path_str(&p), &st);
    let back = load_state(&path_str(&p));
    assert_eq!(back.calls, 2);
    assert_eq!(back.log.len(), 1);
    assert_eq!(back.log[0].kind, "assess:vigiles");
    assert_eq!(back.log[0].output_tokens, 20);
}
