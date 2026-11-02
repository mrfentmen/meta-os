//! B207 — the four named edge cases for `crates/os-misc`:
//! empty input, maximum input, duplicate input, out-of-order input.

use os_misc::b24::send::{parse_pomodoro_duration, sanitize_basename};
use os_misc::b24::store::{store_path, MessageStore};
use os_misc::b26::admin::validate_display;
use os_misc::b27::par_clock::{enter_crew, new_state, tick};
use os_misc::b27::validate::validate_pack;
use serde_json::Value;

fn tmpdir(tag: &str) -> std::path::PathBuf {
    let n = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let dir = std::env::temp_dir().join(format!("os-misc-edge-{tag}-{n}-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    dir
}

#[test]
fn empty_input() {
    // Nothing to validate is not the same as valid.
    assert_eq!(
        validate_pack(&Value::Null),
        vec!["manifest is not a JSON object".to_string()]
    );
    assert_eq!(
        os_misc::b24::presence::render_presence(&[], &Default::default(), &Default::default()),
        "NO_ONE_ONLINE"
    );
    assert_eq!(sanitize_basename(""), "blob");
}

#[test]
fn maximum_input() {
    // 32 is the display cap; the 33rd character is the refusal.
    assert!(validate_display(&"x".repeat(32)).is_ok());
    assert!(validate_display(&"x".repeat(33)).is_err());
    // A blob basename is capped at 60 characters, not rejected.
    assert_eq!(sanitize_basename(&"a".repeat(200)).chars().count(), 60);
    // A duration that overflows u64 is refused, not wrapped.
    assert!(parse_pomodoro_duration("99999999999999999999999s").is_err());
}

#[test]
fn duplicate_input() {
    // The same body twice is two records with distinct ids.
    let dir = tmpdir("dupe");
    let st = MessageStore::new(store_path(&dir, ""), String::new());
    let a = st.append("milo", "same words", Some(10)).unwrap();
    let b = st.append("milo", "same words", Some(11)).unwrap();
    assert_ne!(a.id, b.id);
    assert_eq!(st.entries().len(), 2);

    // A duplicate watcher id in a pack manifest is refused.
    let mut m = minimal_manifest();
    m["watchers"] = serde_json::json!([
        {"id": "w1", "watches": "fire", "inputs": ["radio"]},
        {"id": "w1", "watches": "ems", "inputs": ["radio"]}
    ]);
    let errs = validate_pack(&m);
    assert!(errs.iter().any(|e| e == "duplicate watcher id: w1"));
    std::fs::remove_dir_all(&dir).ok();
}

#[test]
fn out_of_order_input() {
    // A clock that reports a time before the crew entered fires nothing.
    let inside = enter_crew(&new_state(), "crew-2", 1000, None).unwrap();
    let (events, _) = tick(&inside, 500, 600, 120);
    assert!(events.is_empty());

    // Urgency ranks may be listed in any order; only duplicates are refused.
    let mut m = minimal_manifest();
    m["urgency"] = serde_json::json!([
        {"class": "routine", "rank": 4, "meaning": "later"},
        {"class": "urgent", "rank": 2, "meaning": "now"}
    ]);
    let errs = validate_pack(&m);
    assert!(
        !errs.iter().any(|e| e.contains("urgency")),
        "out-of-order ranks were rejected: {errs:?}"
    );
}

fn minimal_manifest() -> Value {
    serde_json::json!({
        "pack": "fdny", "pack_name": "FDNY", "version": "1", "status": "spec",
        "institution_type": "fire", "summary": "s",
        "watchers": [{"id": "w1", "watches": "fire", "inputs": ["radio"]}],
        "agents": [{"nick": "chief", "role": "cmd", "serves": ["w1"]}],
        "alerts": [{"kind": "fire", "severity": "critical", "privacy": "summary",
                    "crosses_bus": true, "carries": "loc", "urgency": "urgent"}],
        "privacy_classes": {"local_only": ["a"], "bus_summary": ["b"]},
        "cross_world": {"sends": [{"to": "nypd", "kind": "fire", "carries": "loc",
                                   "never_carries": ["name"]}],
                       "receives": [{"from": "nypd", "kind": "fire", "carries": "loc"}]},
        "firstboot": [{"field": "station", "label": "Station", "required": true}],
        "urgency": [{"class": "urgent", "rank": 1, "meaning": "now"}]
    })
}
