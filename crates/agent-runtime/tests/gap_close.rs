//! B107 — test-gap close for `agent-runtime`.
//!
//! The crate has one module (`lib.rs`) and its three unit tests cover the
//! serve path plus the headline validator vectors. The public functions
//! with the thinnest coverage were `is_valid_iso8601` (indirect, via one
//! bad date), `check_nullable_number`'s missing/lower edges,
//! `relay_notify_payload`'s no-job-id path, and `now_iso`. This file
//! closes those gaps without changing production code.
use agent_runtime::{now_iso, relay_notify_payload, validate_assessment, Outcome};
use serde_json::{json, Value};

fn canned() -> Value {
    json!({
        "product": "ignis",
        "timestamp": "2026-10-30T06:00:00.000Z",
        "observations": [{
            "category": "visible smoke",
            "description": "grey plume",
            "evidence": "frame centre",
            "confidence": null
        }],
        "assessment": {
            "category": "visible smoke",
            "summary": "Smoke visible.",
            "uncertainty": [],
            "requires_human_review": true
        },
        "processing": { "model": "muse-spark-1.3", "latency_ms": null }
    })
}

fn with_timestamp(ts: &str) -> Value {
    let mut v = canned();
    v["timestamp"] = json!(ts);
    v
}

#[test]
fn iso8601_accepts_zulu_seconds_fractions_and_numeric_offsets() {
    for ts in [
        "2026-10-30T06:00:00.000Z",
        "2026-10-30T06:00Z",
        "2026-10-30T06:00:59+05:30",
        "2026-10-30T06:00:59-0800",
        "2024-02-29T00:00:00Z",
    ] {
        let (ok, errors) = validate_assessment(&with_timestamp(ts), "ignis");
        assert!(ok, "{ts} should parse: {errors:?}");
    }
}

#[test]
fn iso8601_rejects_impossible_dates_times_and_offsets() {
    for ts in [
        "2026-02-30T06:00:00Z",
        "2026-13-01T06:00:00Z",
        "2026-01-01T24:00:00Z",
        "2026-01-01T00:60:00Z",
        "2026-01-01T00:00:00+24:00",
        "2026-01-01 00:00:00Z",
        "2026-2-30T06:00:00Z",
    ] {
        let (ok, errors) = validate_assessment(&with_timestamp(ts), "ignis");
        assert!(!ok, "{ts} must be rejected");
        assert!(
            errors.iter().any(|e| e.contains("not a parseable ISO-8601")),
            "{ts}: {errors:?}"
        );
    }
}

#[test]
fn observations_must_be_an_array_not_null() {
    let mut v = canned();
    v["observations"] = Value::Null;
    let (ok, errors) = validate_assessment(&v, "ignis");
    assert!(!ok);
    assert!(errors.iter().any(|e| e.contains("observations: missing or not an array")));
}

#[test]
fn observation_item_must_be_an_object() {
    let mut v = canned();
    v["observations"] = json!([3]);
    let (ok, errors) = validate_assessment(&v, "ignis");
    assert!(!ok);
    assert!(errors.iter().any(|e| e.contains("observations[0]: not an object")));
}

#[test]
fn observation_evidence_must_be_present_and_a_string() {
    let mut v = canned();
    v["observations"][0].as_object_mut().unwrap().remove("evidence");
    let (ok, errors) = validate_assessment(&v, "ignis");
    assert!(!ok);
    assert!(errors.iter().any(|e| e.contains("evidence: missing or not a string")));
}

#[test]
fn an_empty_evidence_string_is_accepted() {
    // The code checks the type only (`lib.rs:223-225`); this records it.
    let mut v = canned();
    v["observations"][0]["evidence"] = json!("");
    let (ok, errors) = validate_assessment(&v, "ignis");
    assert!(ok, "{errors:?}");
}

#[test]
fn observation_category_cannot_be_whitespace_only() {
    let mut v = canned();
    v["observations"][0]["category"] = json!("   ");
    let (ok, errors) = validate_assessment(&v, "ignis");
    assert!(!ok);
    assert!(errors.iter().any(|e| e.contains("observations[0].category")));
}

#[test]
fn confidence_key_must_be_present_even_when_null() {
    let mut v = canned();
    v["observations"][0]
        .as_object_mut()
        .unwrap()
        .remove("confidence");
    let (ok, errors) = validate_assessment(&v, "ignis");
    assert!(!ok);
    assert!(errors
        .iter()
        .any(|e| e.contains("confidence: missing (must be present, null when unreported)")));
}

#[test]
fn summary_must_be_a_string() {
    let mut v = canned();
    v["assessment"]["summary"] = json!(5);
    let (ok, errors) = validate_assessment(&v, "ignis");
    assert!(!ok);
    assert!(errors.iter().any(|e| e.contains("assessment.summary")));
}

#[test]
fn uncertainty_must_be_an_array_of_strings() {
    let mut v = canned();
    v["assessment"]["uncertainty"] = json!("none");
    let (ok, errors) = validate_assessment(&v, "ignis");
    assert!(!ok);
    assert!(errors.iter().any(|e| e.contains("assessment.uncertainty")));

    let mut v = canned();
    v["assessment"]["uncertainty"] = json!([1]);
    let (ok, errors) = validate_assessment(&v, "ignis");
    assert!(!ok);
    assert!(errors.iter().any(|e| e.contains("assessment.uncertainty[0]")));
}

#[test]
fn requires_human_review_must_be_boolean() {
    let mut v = canned();
    v["assessment"]["requires_human_review"] = json!(1);
    let (ok, errors) = validate_assessment(&v, "ignis");
    assert!(!ok);
    assert!(errors
        .iter()
        .any(|e| e.contains("assessment.requires_human_review")));
}

#[test]
fn processing_block_is_required_with_model_and_latency() {
    let mut v = canned();
    v.as_object_mut().unwrap().remove("processing");
    let (ok, errors) = validate_assessment(&v, "ignis");
    assert!(!ok);
    assert!(errors.iter().any(|e| e.contains("processing: missing")));

    let mut v = canned();
    v["processing"]["latency_ms"] = json!(-1);
    let (ok, errors) = validate_assessment(&v, "ignis");
    assert!(!ok);
    assert!(errors.iter().any(|e| e.contains("must not be below 0")));
}

#[test]
fn extra_fields_are_tolerated_and_do_not_change_the_result() {
    let mut v = canned();
    v["extra"] = json!({"ignored": true});
    v["observations"][0]["extra"] = json!("ignored");
    let (ok, errors) = validate_assessment(&v, "ignis");
    assert!(ok, "{errors:?}");
}

#[test]
fn product_must_match_exactly_including_case_and_spacing() {
    for product in ["Ignis", " ignis", "ignis "] {
        let (ok, errors) = validate_assessment(&canned(), product);
        // The assessment names "ignis"; every variant above must mismatch.
        assert!(!ok, "{product:?} must not match");
        assert!(errors.iter().any(|e| e.contains("product: expected")), "{errors:?}");
    }
}

#[test]
fn relay_payload_needs_a_job_id() {
    assert!(relay_notify_payload(&json!({"status": "ok"}), Some("ignis")).is_none());
    assert!(relay_notify_payload(&json!({"status": "failed", "error": "x"}), None).is_none());
}

#[test]
fn now_iso_is_epoch_millis_not_iso8601() {
    // Documents gap G2: the name promises ISO, the code returns digits.
    let value = now_iso();
    assert!(!value.is_empty());
    assert!(value.chars().all(|c| c.is_ascii_digit()), "{value}");
    assert!(value.len() >= 13, "epoch millis should be at least 13 digits: {value}");
    assert!(!value.contains('T'), "not ISO-8601: {value}");
}

#[test]
fn outcome_values_are_distinct() {
    assert_ne!(Outcome::Done, Outcome::Failed);
    assert_ne!(Outcome::Skipped, Outcome::Lost);
    assert_eq!(Outcome::Done, Outcome::Done);
}
