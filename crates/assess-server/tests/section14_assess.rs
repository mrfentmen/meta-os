//! CB2-332/346/347 — the frozen v2 assessment contract.
//!
//! The validator lives in `agent_runtime::validate_assessment` and this crate
//! calls it on every model and queue answer, so the contract cases are pinned
//! here, from the side that refuses a bad record before it reaches a screen.
use agent_runtime::validate_assessment;
use serde_json::{json, Value};

const PRODUCT: &str = "vigiles";

fn valid_record() -> Value {
    json!({
        "product": "vigiles",
        "timestamp": "2026-11-02T10:00:00Z",
        "observations": [{
            "category": "normal activity",
            "description": "people walking",
            "evidence": "frames 1-3",
            "confidence": 0.8,
            "region": { "x": 10, "y": 20, "width": 100, "height": 50 }
        }],
        "assessment": {
            "category": "normal activity",
            "summary": "nothing to report",
            "uncertainty": ["distance"],
            "requires_human_review": true
        },
        "processing": { "model": "spark", "latency_ms": 12.5 }
    })
}

#[test]
fn assess_response_contract() {
    let (ok, errors) = validate_assessment(&valid_record(), PRODUCT);
    assert!(ok, "the reference record is valid: {errors:?}");

    // Removing any one of the five contract keys is refused, and the error
    // names the key that went missing.
    for key in ["product", "timestamp", "observations", "assessment", "processing"] {
        let mut record = valid_record();
        record.as_object_mut().expect("object").remove(key);
        let (ok, errors) = validate_assessment(&record, PRODUCT);
        assert!(!ok, "a record without {key} is refused");
        assert!(
            errors.iter().any(|e| e.starts_with(&format!("{key}:"))),
            "the missing key is named: {errors:?}",
        );
    }

    // A wrong product is refused by name rather than accepted as another
    // service's record.
    let mut wrong = valid_record();
    wrong["product"] = json!("ignis");
    let (ok, errors) = validate_assessment(&wrong, PRODUCT);
    assert!(!ok);
    assert!(errors.iter().any(|e| e.contains("expected \"vigiles\", got \"ignis\"")), "{errors:?}");
}

#[test]
fn assess_region_bounds() {
    let in_frame = valid_record();
    assert!(validate_assessment(&in_frame, PRODUCT).0, "a box inside 0..1000 passes");

    // The frame's edge is inclusive; one past it is refused, named by field.
    let mut edge = valid_record();
    edge["observations"][0]["region"] = json!({ "x": 0, "y": 1000, "width": 1000, "height": 0 });
    assert!(validate_assessment(&edge, PRODUCT).0, "0 and 1000 are inside the frame");

    let mut outside = valid_record();
    outside["observations"][0]["region"] = json!({ "x": 1001, "y": 0, "width": 10, "height": 10 });
    let (ok, errors) = validate_assessment(&outside, PRODUCT);
    assert!(!ok, "a coordinate past 1000 is refused");
    assert_eq!(errors, vec!["observations[0].region.x: outside 0..1000"]);

    let mut negative = valid_record();
    negative["observations"][0]["region"] = json!({ "x": -1, "y": 0, "width": 10, "height": 10 });
    let (ok, errors) = validate_assessment(&negative, PRODUCT);
    assert!(!ok);
    assert!(errors.iter().any(|e| e.contains(".region.x: outside 0..1000")), "{errors:?}");

    // A region that is not an object, or a coordinate that is not a number, is
    // refused rather than skipped.
    let mut wrong_type = valid_record();
    wrong_type["observations"][0]["region"] = json!("top left");
    let (ok, errors) = validate_assessment(&wrong_type, PRODUCT);
    assert!(!ok);
    assert_eq!(errors, vec!["observations[0].region: must be an object or null"]);

    let mut string_coord = valid_record();
    string_coord["observations"][0]["region"] = json!({ "x": "10", "y": 0, "width": 1, "height": 1 });
    let (ok, errors) = validate_assessment(&string_coord, PRODUCT);
    assert!(!ok);
    assert_eq!(errors, vec!["observations[0].region.x: must be a number"]);

    // A region may be absent or explicitly null: the field is optional.
    let mut absent = valid_record();
    absent["observations"][0].as_object_mut().expect("object").remove("region");
    assert!(validate_assessment(&absent, PRODUCT).0);
    let mut null = valid_record();
    null["observations"][0]["region"] = Value::Null;
    assert!(validate_assessment(&null, PRODUCT).0);
}

#[test]
fn assess_confidence_types() {
    // Numeric and null are the only accepted forms.
    for good in [json!(0.0), json!(0.8), json!(1.0), Value::Null] {
        let mut record = valid_record();
        record["observations"][0]["confidence"] = good.clone();
        let (ok, errors) = validate_assessment(&record, PRODUCT);
        assert!(ok, "confidence {good} is accepted: {errors:?}");
    }

    // A string is refused, named by field, never coerced to a number.
    let mut text = valid_record();
    text["observations"][0]["confidence"] = json!("high");
    let (ok, errors) = validate_assessment(&text, PRODUCT);
    assert!(!ok);
    assert_eq!(errors, vec!["observations[0].confidence: must be null or a number"]);

    // Out of range is refused at both ends.
    let mut above = valid_record();
    above["observations"][0]["confidence"] = json!(1.5);
    let (ok, errors) = validate_assessment(&above, PRODUCT);
    assert!(!ok);
    assert!(errors.iter().any(|e| e.contains("out of range 0..1")), "{errors:?}");

    let mut below = valid_record();
    below["observations"][0]["confidence"] = json!(-0.1);
    let (ok, errors) = validate_assessment(&below, PRODUCT);
    assert!(!ok);
    assert!(errors.iter().any(|e| e.contains("must not be below 0")), "{errors:?}");

    // The field must be present: a missing confidence is not "unknown".
    let mut missing = valid_record();
    missing["observations"][0].as_object_mut().expect("object").remove("confidence");
    let (ok, errors) = validate_assessment(&missing, PRODUCT);
    assert!(!ok);
    assert!(
        errors.iter().any(|e| e.contains("missing (must be present, null when unreported)")),
        "{errors:?}",
    );
}
