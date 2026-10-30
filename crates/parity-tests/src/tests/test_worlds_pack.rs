//! T061 [B31] port of `os/tests/test_worlds_pack.py` (same name roots).
//!
//! Worlds pack contract (WORLDS-001): shipped manifests validate, docs
//! ship, honesty gate (spec vs backed-up partial), plus the validator's
//! rule battery on a hand-built manifest. Tested against the real ported
//! validator (`os_misc::b27::validate`, landed via T014) and the real
//! shipped packs under `os/worlds/` (no fold drift on this path).
//! This is the case T061 that B27 closes on.

use os_misc::b27::validate as vp;
use serde_json::{json, Value};
use std::path::PathBuf;

pub const CASES: &[&str] = &[
    "shipped packs validate",
    "shipped packs have docs",
    "shipped packs are honest spec",
    "valid manifest passes",
    "missing key fails",
    "bad status fails",
    "local alert may not cross bus",
    "summary alert may cross bus",
    "send without never carries fails",
    "unknown urgency class fails",
    "agent serving unknown watcher fails",
    "duplicate urgency rank fails",
    "bad severity fails",
];
pub const EXCLUSION_BLOCKED: &[&str] = &[];

pub const SHIPPED_PACKS: &[&str] = &["fdny", "nypd", "hospital", "ems", "dsny", "doe", "mta", "dep"];

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("..")
}
fn pack_path(name: &str) -> PathBuf {
    root().join("os").join("worlds").join(name).join("pack.json")
}
fn read_manifest(name: &str) -> Value {
    serde_json::from_str(&std::fs::read_to_string(pack_path(name)).unwrap()).unwrap()
}

fn valid_manifest() -> Value {
    json!({
        "pack": "testworld",
        "pack_name": "Test world pack",
        "version": "0.1.0",
        "status": "spec",
        "institution_type": "test institution",
        "summary": "A pack used only by the validator tests.",
        "watchers": [
            {"id": "board", "watches": "A state board.", "inputs": ["status reports"]},
        ],
        "agents": [
            {"nick": "keeper", "role": "Keeps the board.", "serves": ["board"]},
        ],
        "alerts": [
            {"kind": "board-stale", "severity": "warning",
             "privacy": "local", "crosses_bus": false,
             "carries": "The board id.", "urgency": "routine"},
        ],
        "privacy_classes": {
            "local_only": ["board contents"],
            "bus_summary": ["board state counts"],
        },
        "cross_world": {
            "sends": [
                {"to": "crew", "kind": "board-state",
                 "carries": "Counts only.",
                 "never_carries": ["board contents"]},
            ],
            "receives": [],
        },
        "firstboot": [
            {"field": "room_name", "label": "Bus room", "required": true},
        ],
        "urgency": [
            {"class": "routine", "rank": 3, "meaning": "State changes."},
        ],
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_shipped_packs_validate() {
        for name in SHIPPED_PACKS {
            let m = read_manifest(name);
            let errors = vp::validate_pack(&m);
            assert_eq!(errors, Vec::<String>::new(), "{name} failed validation: {errors:?}");
        }
    }

    #[test]
    fn test_shipped_packs_have_docs() {
        for name in SHIPPED_PACKS {
            let dir = root().join("os").join("worlds").join(name);
            for fname in ["PACK.md", "pack.json"] {
                assert!(dir.join(fname).is_file(), "{name} is missing {fname}");
            }
        }
    }

    #[test]
    fn test_shipped_packs_are_honest_spec() {
        for name in SHIPPED_PACKS {
            let m = read_manifest(name);
            let status = m["status"].as_str().unwrap_or("");
            if status == "spec" {
                continue;
            }
            assert_eq!(status, "partial", "{name} may only be honest spec or honest partial");
            let parts = m.pointer("/runtime/parts").and_then(Value::as_array).cloned().unwrap_or_default();
            assert!(!parts.is_empty(), "{name} claims partial without a runtime record");
            for part in &parts {
                let rel = part.get("path").and_then(Value::as_str).unwrap_or("");
                assert!(root().join("os").join(rel).is_file(), "{name} runtime part {rel} does not exist on disk");
                assert!(part.get("what").and_then(Value::as_str).map(|s| !s.is_empty()).unwrap_or(false)
                    && part.get("proven").and_then(Value::as_str).map(|s| !s.is_empty()).unwrap_or(false),
                    "{name} runtime part must state what it is and what is proven");
            }
        }
    }

    #[test]
    fn test_valid_manifest_passes() {
        assert_eq!(vp::validate_pack(&valid_manifest()), Vec::<String>::new());
    }

    #[test]
    fn test_missing_key_fails() {
        let mut m = valid_manifest();
        m.as_object_mut().unwrap().remove("alerts");
        let errors = vp::validate_pack(&m);
        assert!(errors.iter().any(|e| e.contains("alerts")), "{errors:?}");
    }

    #[test]
    fn test_bad_status_fails() {
        let mut m = valid_manifest();
        m["status"] = json!("live");
        let errors = vp::validate_pack(&m);
        assert!(errors.iter().any(|e| e.contains("status")), "{errors:?}");
    }

    #[test]
    fn test_local_alert_may_not_cross_bus() {
        let mut m = valid_manifest();
        m["alerts"][0]["crosses_bus"] = json!(true);
        let errors = vp::validate_pack(&m);
        assert!(errors.iter().any(|e| e.contains("crosses the bus")), "{errors:?}");
    }

    #[test]
    fn test_summary_alert_may_cross_bus() {
        let mut m = valid_manifest();
        m["alerts"][0]["privacy"] = json!("summary");
        m["alerts"][0]["crosses_bus"] = json!(true);
        assert_eq!(vp::validate_pack(&m), Vec::<String>::new());
    }

    #[test]
    fn test_send_without_never_carries_fails() {
        let mut m = valid_manifest();
        m["cross_world"]["sends"][0]["never_carries"] = json!([]);
        let errors = vp::validate_pack(&m);
        assert!(errors.iter().any(|e| e.contains("never_carries")), "{errors:?}");
    }

    #[test]
    fn test_unknown_urgency_class_fails() {
        let mut m = valid_manifest();
        m["alerts"][0]["urgency"] = json!("whenever");
        let errors = vp::validate_pack(&m);
        assert!(errors.iter().any(|e| e.contains("urgency")), "{errors:?}");
    }

    #[test]
    fn test_agent_serving_unknown_watcher_fails() {
        let mut m = valid_manifest();
        m["agents"][0]["serves"] = json!(["no-such-watcher"]);
        let errors = vp::validate_pack(&m);
        assert!(errors.iter().any(|e| e.contains("unknown watcher")), "{errors:?}");
    }

    #[test]
    fn test_duplicate_urgency_rank_fails() {
        let mut m = valid_manifest();
        m["urgency"].as_array_mut().unwrap().push(json!({"class": "urgent", "rank": 3, "meaning": "Also rank 3."}));
        let errors = vp::validate_pack(&m);
        assert!(errors.iter().any(|e| e.contains("rank")), "{errors:?}");
    }

    #[test]
    fn test_bad_severity_fails() {
        let mut m = valid_manifest();
        m["alerts"][0]["severity"] = json!("loud");
        let errors = vp::validate_pack(&m);
        assert!(errors.iter().any(|e| e.contains("severity")), "{errors:?}");
    }
}
