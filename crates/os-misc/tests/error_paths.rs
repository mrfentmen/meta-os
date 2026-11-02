//! B206 — every refusal and failure branch in `crates/os-misc`, proven
//! through the public API only.
//!
//! Each test asserts the message the code actually produces. A branch
//! that is unreachable from the public surface is named in
//! `os-build/records/os-misc-gaps.md`, not tested here.

use std::collections::HashMap;
use std::path::PathBuf;

use os_misc::b24::poll::{poll_one, read_seen};
use os_misc::b24::send::{parse_duration, parse_pomodoro_duration, parse_ttl, parse_when};
use os_misc::b24::store::{store_path, MessageStore};
use os_misc::b24::transport::BusTransport;
use os_misc::b24::watch::{validate_interval, watch_once, Target};
use os_misc::b25::announce::gate;
use os_misc::b25::edits::validate_edit_text;
use os_misc::b25::paste::verify_clip;
use os_misc::b26::admin::{validate_display, validate_rekey_digest};
use os_misc::b26::digest::validate_hours;
use os_misc::b26::timecapsule::validate_interval as capsule_interval;
use os_misc::b26::webhook::{resolve_url, validate_interval as webhook_interval};
use os_misc::b27::par_clock::{
    complete_par, enter_crew, exit_crew, new_state, validated_crew_id,
};
use os_misc::b27::validate::validate_pack;
use serde_json::Value;

fn tmpdir(tag: &str) -> PathBuf {
    let n = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let dir = std::env::temp_dir().join(format!("os-misc-err-{tag}-{n}-{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();
    dir
}

struct FailingBus;
impl BusTransport for FailingBus {
    fn bus_get(&self, _seen: i64, _key: &str) -> Result<Vec<String>, String> {
        Err("boom".to_string())
    }
    fn presence_beat(&self, _key: &str) -> Result<(), String> {
        Err("beat-down".to_string())
    }
    fn mark_seen(&self, _key: &str, _nick: &str, _seen: i64) -> Result<(), String> {
        Err("receipt-down".to_string())
    }
}

#[test]
fn duration_refusals_name_the_accepted_shapes() {
    for bad in ["10x", "abc", "", "s"] {
        let err = parse_duration(bad).unwrap_err();
        assert!(
            err.contains("not a duration (try 30s, 10m, 2h, 1d)"),
            "unexpected message for {bad:?}: {err}"
        );
    }
    let ttl = parse_ttl("nope").unwrap_err();
    assert_eq!(
        ttl,
        "--ttl needs a duration (30s, 10m, 2h, 1d), got \"nope\""
    );
    for bad in ["25x", "", "0m", "m", "1h 2"] {
        assert!(
            parse_pomodoro_duration(bad).is_err(),
            "pomodoro accepted {bad:?}"
        );
    }
    let when = parse_when("garbage!!", 1_700_000_000).unwrap_err();
    assert!(when.contains("can't parse --at"));
    assert!(parse_when("2026-13-01", 1_700_000_000).is_err());
}

#[test]
fn store_refuses_empty_nick_and_empty_text() {
    let dir = tmpdir("store-empty");
    let st = MessageStore::new(store_path(&dir, ""), String::new());
    assert_eq!(st.append("", "hi", None).unwrap_err(), "nick is empty");
    assert_eq!(
        st.append("milo", "", None).unwrap_err(),
        "message text is empty"
    );
    std::fs::remove_dir_all(&dir).ok();
}

#[test]
fn store_edit_refusals_are_exact() {
    let dir = tmpdir("store-edit");
    let st = MessageStore::new(store_path(&dir, ""), String::new());
    let e = st.append("milo", "first", Some(1)).unwrap();
    assert_eq!(
        st.edit(&e.id, "milo", "", None).unwrap_err().0,
        "new text is empty"
    );
    assert_eq!(
        st.edit("999", "milo", "x", None).unwrap_err().0,
        "no such message: 999"
    );
    let wrong = st.edit(&e.id, "pax", "x", None).unwrap_err().0;
    assert!(wrong.contains("was sent by 'milo'; only the original nick may edit it"));
    std::fs::remove_dir_all(&dir).ok();
}

#[test]
fn store_write_failure_is_returned_not_panicked() {
    let missing = std::env::temp_dir().join(format!(
        "os-misc-no-such-dir-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    let st = MessageStore::new(missing.join("messages.jsonl"), String::new());
    assert!(st.append("milo", "hi", None).is_err());
}

#[test]
fn poll_surfaces_transport_failure_and_warns_on_best_effort_writes() {
    let dir = tmpdir("poll");
    let store = MessageStore::new(dir.join("messages.jsonl"), String::new());
    let missing_seen = dir.join("no-such-subdir").join("seen");
    let err = poll_one(
        &FailingBus,
        "muse-bus",
        &missing_seen.to_string_lossy(),
        "milo",
        &store,
    )
    .err()
    .expect("the failing bus must be an error");
    assert_eq!(err, "poll failed: boom");

    // A bus that answers, but whose heartbeat/receipt and seen write fail.
    struct HalfBus;
    impl BusTransport for HalfBus {
        fn bus_get(&self, _seen: i64, _key: &str) -> Result<Vec<String>, String> {
            Ok(vec!["pax: hello".to_string()])
        }
        fn presence_beat(&self, _key: &str) -> Result<(), String> {
            Err("beat-down".to_string())
        }
        fn mark_seen(&self, _key: &str, _nick: &str, _seen: i64) -> Result<(), String> {
            Err("receipt-down".to_string())
        }
    }
    let out = poll_one(
        &HalfBus,
        "muse-bus",
        &missing_seen.to_string_lossy(),
        "milo",
        &store,
    )
    .unwrap();
    assert_eq!(out.new_from_others, vec!["pax: hello".to_string()]);
    assert!(out.warnings.iter().any(|w| w.contains("presence heartbeat failed: beat-down")));
    assert!(out.warnings.iter().any(|w| w.contains("seen write failed")));
    assert!(out.warnings.iter().any(|w| w.contains("read-receipt write failed: receipt-down")));
    std::fs::remove_dir_all(&dir).ok();
}

#[test]
fn missing_seen_file_reads_as_zero() {
    assert_eq!(read_seen("/definitely/not/here/seen-xyz"), 0);
}

#[test]
fn watch_refuses_nonpositive_interval_and_bus_error() {
    assert_eq!(
        validate_interval(0.0).unwrap_err(),
        "interval must be positive"
    );
    assert!(validate_interval(-1.5).is_err());
    let mut targets = vec![Target {
        label: "main".into(),
        key: "muse-bus".into(),
        seen_file: "/tmp/os-misc-never-written".into(),
        seen: 0,
    }];
    let err = watch_once(&FailingBus, &mut targets, "milo", &|_| {
        MessageStore::new(std::env::temp_dir().join("unused.jsonl"), String::new())
    })
    .err()
    .expect("the failing bus must be an error");
    assert_eq!(err, "poll failed: boom");
}

#[test]
fn announce_gate_names_claim_holder_and_mods() {
    let held = gate("milo", Some("host-a"), &[]).unwrap();
    assert!(held.contains("you don't hold the nick claim for 'milo'"));
    assert!(held.contains("held by 'host-a'"));
    let mods = gate("milo", None, &["alice".into()]).unwrap();
    assert_eq!(mods, "only room mods can change announce mode (mods: alice)");
    assert!(gate("alice", None, &["alice".into()]).is_none());
}

#[test]
fn edit_text_refuses_empty_and_over_max() {
    assert_eq!(validate_edit_text("   ").unwrap_err(), "new text is empty");
    let long = "x".repeat(os_misc::b24::transport::MAX_TEXT + 1);
    let err = validate_edit_text(&long).unwrap_err();
    assert!(err.contains("text too long (2001 chars; max 2000)"));
    assert!(validate_edit_text(&"x".repeat(os_misc::b24::transport::MAX_TEXT)).is_ok());
}

#[test]
fn clip_hash_mismatch_is_loud() {
    let err = verify_clip(b"hello", "deadbeefdeadbeef").unwrap_err();
    assert!(err.contains("don't match their hash"));
    assert!(err.contains("corrupt or partial"));
}

#[test]
fn admin_display_and_rekey_refusals() {
    assert_eq!(validate_display("").unwrap_err(), "display name is empty");
    assert_eq!(
        validate_display(&"x".repeat(33)).unwrap_err(),
        "display name too long (max 32 chars)"
    );
    assert_eq!(
        validate_display("a:b").unwrap_err(),
        "display name may not contain ':' or newlines"
    );
    assert_eq!(
        validate_rekey_digest("xyz").unwrap_err(),
        "new-sha256 must be 64 hex chars (sha256 of the new secret)"
    );
}

#[test]
fn positive_only_intervals() {
    assert_eq!(validate_hours(0.0).unwrap_err(), "--hours must be positive");
    assert_eq!(
        capsule_interval(0.0).unwrap_err(),
        "interval must be positive"
    );
    assert_eq!(
        webhook_interval(-1.0).unwrap_err(),
        "--interval must be positive"
    );
}

#[test]
fn webhook_url_resolution_refusals() {
    let env = |k: &str| match k {
        "MISSING" => None,
        "EMPTY" => Some("   ".into()),
        "NOT_URL" => Some("ftp://x".into()),
        _ => None,
    };
    assert_eq!(
        resolve_url("MISSING", &env).unwrap_err(),
        "env var \"MISSING\" is not set or empty"
    );
    assert_eq!(
        resolve_url("EMPTY", &env).unwrap_err(),
        "env var \"EMPTY\" is not set or empty"
    );
    assert_eq!(
        resolve_url("NOT_URL", &env).unwrap_err(),
        "env var \"NOT_URL\" does not hold an http(s) URL"
    );
}

#[test]
fn crew_id_rules_and_lifecycle_refusals() {
    assert_eq!(
        validated_crew_id("").unwrap_err(),
        "crew id may not be empty"
    );
    assert_eq!(
        validated_crew_id("crew 2").unwrap_err(),
        "crew id may not contain whitespace"
    );
    let inside = enter_crew(&new_state(), "crew-2", 1000, None).unwrap();
    assert_eq!(
        enter_crew(&inside, "crew-2", 1100, None).unwrap_err(),
        "crew crew-2 is already inside"
    );
    assert_eq!(
        complete_par(&new_state(), "crew-9", 1).unwrap_err(),
        "crew crew-9 is not inside"
    );
    assert_eq!(
        exit_crew(&new_state(), "crew-9", 1).unwrap_err(),
        "crew crew-9 is not inside"
    );
}

#[test]
fn pack_validator_refuses_non_object_and_missing_keys() {
    let errs = validate_pack(&Value::Null);
    assert_eq!(errs, vec!["manifest is not a JSON object".to_string()]);
    let errs = validate_pack(&serde_json::json!({ "pack": "fdny" }));
    assert!(errs.iter().any(|e| e == "missing required key: pack_name"));
    assert!(errs.iter().any(|e| e == "missing required key: urgency"));
}

#[test]
fn pack_validator_names_unknown_serves_and_bad_severity() {
    let mut m = minimal_manifest();
    m["agents"][0]["serves"] = serde_json::json!(["not-a-watcher"]);
    m["alerts"][0]["severity"] = serde_json::json!("bad");
    let errs = validate_pack(&m);
    assert!(errs.iter().any(|e| e.contains("serves names unknown watcher: not-a-watcher")));
    assert!(errs.iter().any(|e| e.contains("severity must be one of")));
}

#[test]
fn presence_render_carries_both_suffixes() {
    let nicks = vec!["milo".to_string()];
    let statuses = HashMap::from([("milo".to_string(), "heads down".to_string())]);
    let holders = HashMap::from([("milo".to_string(), "host-a".to_string())]);
    assert_eq!(
        os_misc::b24::presence::render_presence(&nicks, &statuses, &holders),
        "milo [host-a] (heads down)"
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
