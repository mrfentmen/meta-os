//! Test-gap close for `guardrail` (B167).
//!
//! The crate is one module, so "the module with the fewest tests" is the
//! module itself: these cover the functions the original five unit tests
//! never touched — `status_of`, `via_helper`, the rate/path constants,
//! partial-state loading and the ledger/state agreement after a record.

use guardrail::{
    check, estimate, load_state, record, save_state, status_of, unwrap_model_text, via_helper,
    GuardrailState, RATE_IN_PER_M, RATE_OUT_PER_M, SPARK_ENDPOINT, SPARK_MODEL, TEST_BUDGET_USD,
};
use std::path::PathBuf;

fn tmp_path(name: &str) -> PathBuf {
    let p = std::env::temp_dir().join(format!(
        "guardrail-gap-{}-{name}.json",
        std::process::id()
    ));
    let _ = std::fs::remove_file(&p);
    p
}

fn path_str(p: &PathBuf) -> String {
    p.to_string_lossy().to_string()
}

#[test]
fn status_of_reports_the_four_contract_fields() {
    let st = GuardrailState {
        calls: 2,
        est_cost_usd: 12.5,
        log: vec![],
    };
    let v = status_of(&st);
    assert_eq!(v["calls"].as_u64(), Some(2));
    assert_eq!(v["est_cost_usd"].as_f64(), Some(12.5));
    assert_eq!(v["test_budget_usd"].as_f64(), Some(75.0));
    assert_eq!(v["remaining_usd"].as_f64(), Some(62.5));
}

#[test]
fn status_remaining_is_exactly_zero_at_the_budget() {
    let st = GuardrailState {
        calls: 0,
        est_cost_usd: TEST_BUDGET_USD,
        log: vec![],
    };
    assert_eq!(status_of(&st)["remaining_usd"].as_f64(), Some(0.0));
}

#[test]
fn via_helper_is_true_only_for_the_literal_one() {
    std::env::set_var("TRIO_SPARK_VIA_HELPER", "1");
    assert!(via_helper());
    std::env::set_var("TRIO_SPARK_VIA_HELPER", "true");
    assert!(!via_helper());
    std::env::set_var("TRIO_SPARK_VIA_HELPER", "0");
    assert!(!via_helper());
    std::env::remove_var("TRIO_SPARK_VIA_HELPER");
    assert!(!via_helper());
}

#[test]
fn a_partial_state_object_loads_with_defaults() {
    let p = tmp_path("partial");
    std::fs::write(&p, r#"{"calls":2}"#).unwrap();
    let st = load_state(&path_str(&p));
    assert_eq!(st.calls, 2);
    assert_eq!(st.est_cost_usd, 0.0);
    assert!(st.log.is_empty());
}

#[test]
fn one_record_leaves_the_log_and_the_state_agreeing() {
    let p = tmp_path("agree");
    record(&path_str(&p), "assess:medicus", "muse-spark-1.3", 1000, 1000, 12);
    let st = load_state(&path_str(&p));
    assert_eq!(st.log.len(), 1);
    assert!((st.log[0].est_cost_usd - st.est_cost_usd).abs() < 1e-12);
    assert!((st.log[0].est_cost_usd - 0.0055).abs() < 1e-12);
    assert_eq!(st.log[0].cum_est_cost_usd, st.est_cost_usd);
}

#[test]
fn the_rate_card_and_public_endpoints_are_the_documented_values() {
    assert_eq!(TEST_BUDGET_USD, 75.0);
    assert_eq!(RATE_IN_PER_M, 1.25);
    assert_eq!(RATE_OUT_PER_M, 4.25);
    assert_eq!(SPARK_MODEL, "muse-spark-1.3");
    assert_eq!(SPARK_ENDPOINT, "https://api.meta.ai/v1/chat/completions");
}

#[test]
fn saved_state_survives_the_pretty_json_writer() {
    let p = tmp_path("pretty");
    let st = GuardrailState {
        calls: 0,
        est_cost_usd: 0.0,
        log: vec![],
    };
    save_state(&path_str(&p), &st);
    let raw = std::fs::read_to_string(&p).unwrap();
    assert!(raw.contains('\n'), "save_state writes pretty JSON");
    let back = load_state(&path_str(&p));
    assert_eq!(back.calls, 0);
}

#[test]
fn an_empty_object_model_text_is_its_own_object() {
    assert_eq!(unwrap_model_text("{}"), "{}");
}

#[test]
fn a_negative_budget_state_still_passes_check() {
    // Not reachable through `record`, but the type permits it and the
    // guardrail must not invent a refusal: only >= budget stops.
    let st = GuardrailState {
        calls: 0,
        est_cost_usd: -1.0,
        log: vec![],
    };
    assert!(check(&st).is_ok());
    assert!(estimate(0, 0) == 0.0);
}
