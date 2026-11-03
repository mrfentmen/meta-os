//! CB2-344/345 — parity fixtures shared with the Python queue tests.
//!
//! These tests read the same bytes the Python suite reads: one generated
//! envelope fixture, and the real live-reading record the queue files. Nothing
//! is hand-copied into Rust, so a field rename on either side fails here.

use queue_core::{validate_envelope, Envelope, EnvelopeImage};
use serde_json::Value;

const ENVELOPE_JSON: &str = include_str!("../../../tests/fixtures/parity/envelope.json");
// The v2 record the staged Imperium run produced, extracted byte-for-byte from
// the brief step of os-build/logs/R5-imperium/incident.json. The crew incident
// record is a different shape, so the test reads the record the pipeline filed.
const INCIDENT_JSON: &str = include_str!("../../../tests/fixtures/parity/incident.json");
const PY_VALIDATOR: &str = include_str!("../../../server/queue/record_validate.py");

fn parsed(json: &str) -> Value {
    serde_json::from_str(json).expect("fixture is valid JSON")
}

/// The envelope the Python `build_job_envelope` writes, as the queue-core struct.
fn envelope_from(v: &Value, product: &str, timestamp: &str) -> Envelope {
    let image = &v["image"];
    Envelope {
        version: v["version"].as_i64().expect("version is an integer"),
        kind: v["kind"].as_str().expect("kind is a string").to_string(),
        id: v["id"].as_str().expect("id is a string").to_string(),
        product: product.to_string(),
        timestamp: timestamp.to_string(),
        image: EnvelopeImage {
            data_url: image["dataUrl"].as_str().expect("dataUrl").to_string(),
            byte_length: image["byteLength"].as_u64().expect("byteLength") as usize,
            sha256: image["sha256"].as_str().expect("sha256").to_string(),
        },
    }
}

#[test]
fn parity_envelope_fixture() {
    let v = parsed(ENVELOPE_JSON);

    // The Python-side values that do not depend on the frame bytes.
    assert_eq!(v["version"], 1i64);
    assert_eq!(v["kind"], "trio-assessment");
    assert_eq!(v["product"], "vigiles");
    assert_eq!(v["timestamp"], "2026-11-02T00:00:00Z");
    assert_eq!(v["image"]["mediaType"], "image/jpeg");
    assert!(
        v["image"]["dataUrl"].as_str().unwrap().starts_with("data:image/jpeg;base64,"),
        "the data URL carries the media type the queue service expects",
    );

    // Building the parsed envelope must satisfy queue-core's own validation,
    // which is the check the HTTP layer runs before a job is accepted.
    let env = envelope_from(
        &v,
        v["product"].as_str().unwrap(),
        v["timestamp"].as_str().unwrap(),
    );
    assert_eq!(env.image.byte_length, v["image"]["byteLength"].as_u64().unwrap() as usize);
    assert!(
        validate_envelope(&env, &["vigiles", "ignis", "medicus", "science-lab"]).is_none(),
        "queue-core accepts the fixture envelope",
    );
    // An unknown product is refused, so the fixture is not passing by default.
    assert!(validate_envelope(&env, &["ignis"]).is_some());
}

#[test]
fn parity_incident_keys() {
    let record = parsed(INCIDENT_JSON);
    let object = record.as_object().expect("the record is an object");

    let required = required_keys_from_python();
    assert_eq!(required.len(), 5, "the contract lists five keys");

    let mut got: Vec<String> = object.keys().cloned().collect();
    let mut want: Vec<String> = required.clone();
    got.sort();
    want.sort();
    assert_eq!(got, want, "the real record carries exactly the contract key set");

    // The nested observation keys are part of the same contract, so pin them
    // too: a field added on one side only would otherwise pass unnoticed.
    let observation_keys = required_keys_from_python_list("OBSERVATION_KEYS");
    let first = record["observations"][0].as_object().expect("an observation object");
    for key in first.keys() {
        assert!(
            observation_keys.contains(key),
            "{key} is not an observation field in the Python contract",
        );
    }
    // The three the contract requires to be present on every observation.
    for key in ["category", "description", "confidence"] {
        assert!(first.contains_key(key), "{key} is on the real observation");
    }
}

/// Extract a tuple of quoted strings from the Python validator source.
fn required_keys_from_python_list(name: &str) -> Vec<String> {
    let start = PY_VALIDATOR
        .find(&format!("{name} = ("))
        .unwrap_or_else(|| panic!("{name} is declared in the Python validator"));
    let rest = &PY_VALIDATOR[start..];
    let end = rest.find(')').expect("the tuple closes");
    let body = &rest[..end];
    body.split('"')
        .enumerate()
        .filter(|(i, _)| i % 2 == 1)
        .map(|(_, s)| s.to_string())
        .filter(|s| !s.is_empty())
        .collect()
}

fn required_keys_from_python() -> Vec<String> {
    required_keys_from_python_list("REQUIRED_KEYS")
}
