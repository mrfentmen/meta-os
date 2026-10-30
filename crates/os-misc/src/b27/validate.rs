//! B27 validator — port of `os/worlds/validate_pack.py`.
//!
//! Pure function: manifest JSON -> list of contract error strings.
//! Empty list = satisfies the pack contract. Pack files are data
//! (carried unchanged); this is the only code in B27.

use serde_json::Value;

const STATUSES: &[&str] = &["spec", "partial", "built"];
const SEVERITIES: &[&str] = &["critical", "warning"];
const PRIVACY: &[&str] = &["local", "summary"];
const URGENCY: &[&str] = &["life-safety", "urgent", "routine", "digest"];

const REQUIRED: &[&str] = &[
    "pack", "pack_name", "version", "status", "institution_type",
    "summary", "watchers", "agents", "alerts", "privacy_classes",
    "cross_world", "firstboot", "urgency",
];

fn is_token(v: &Value) -> bool {
    match v.as_str() {
        Some(s) => {
            let mut c = s.chars();
            match c.next() {
                Some(f) if f.is_ascii_lowercase() || f.is_ascii_digit() => {},
                _ => return false,
            }
            s.chars().all(|x| x.is_ascii_lowercase() || x.is_ascii_digit() || x == '-')
        }
        None => false,
    }
}

fn nonempty_str(v: &Value) -> bool {
    matches!(v.as_str(), Some(s) if !s.trim().is_empty())
}

fn is_field(s: &str) -> bool {
    let mut c = s.chars();
    match c.next() {
        Some(f) if f.is_ascii_lowercase() || f.is_ascii_digit() => {},
        _ => return false,
    }
    s.chars().all(|x| x.is_ascii_lowercase() || x.is_ascii_digit() || x == '_')
}

/// Validate a pack manifest. Returns error strings (empty = valid).
pub fn validate_pack(manifest: &Value) -> Vec<String> {
    let mut errors = vec![];
    let obj = match manifest.as_object() {
        Some(o) => o,
        None => return vec!["manifest is not a JSON object".to_string()],
    };
    for k in REQUIRED {
        if !obj.contains_key(*k) {
            errors.push(format!("missing required key: {k}"));
        }
    }
    if !errors.is_empty() {
        return errors;
    }
    // pack token + names.
    if !obj.get("pack").map(is_token).unwrap_or(false) {
        errors.push(format!("pack must be a lowercase token: {:?}", obj.get("pack")));
    }
    for k in ["pack_name", "version", "institution_type", "summary"] {
        if !obj.get(k).map(nonempty_str).unwrap_or(false) {
            errors.push(format!("{k} must be a non-empty string"));
        }
    }
    if !obj.get("status").and_then(Value::as_str).map(|s| STATUSES.contains(&s)).unwrap_or(false) {
        errors.push(format!("status must be one of {}: {:?}", STATUSES.join(", "), obj.get("status")));
    }
    // Watchers.
    let mut watcher_ids = std::collections::HashSet::new();
    match obj.get("watchers") {
        Some(Value::Array(ws)) if !ws.is_empty() => {
            for (i, w) in ws.iter().enumerate() {
                let where_ = format!("watchers[{i}]");
                let o = match w.as_object() {
                    Some(o) => o,
                    None => { errors.push(format!("{where_} is not an object")); continue; }
                };
                match o.get("id") {
                    Some(id) if is_token(id) => {
                        let id = id.as_str().unwrap();
                        if !watcher_ids.insert(id.to_string()) {
                            errors.push(format!("duplicate watcher id: {id}"));
                        }
                    }
                    _ => errors.push(format!("{where_}.id must be a lowercase token")),
                }
                if !o.get("watches").map(nonempty_str).unwrap_or(false) {
                    errors.push(format!("{where_}.watches must be a non-empty string"));
                }
                match o.get("inputs") {
                    Some(Value::Array(ins)) if !ins.is_empty() && ins.iter().all(nonempty_str) => {},
                    _ => errors.push(format!("{where_}.inputs must be a non-empty list of strings")),
                }
            }
        }
        _ => errors.push("watchers must be a non-empty list".to_string()),
    }
    // Agents (serves must reference watcher ids).
    let mut nicks = std::collections::HashSet::new();
    match obj.get("agents") {
        Some(Value::Array(agents)) if !agents.is_empty() => {
            for (i, a) in agents.iter().enumerate() {
                let where_ = format!("agents[{i}]");
                let o = match a.as_object() {
                    Some(o) => o,
                    None => { errors.push(format!("{where_} is not an object")); continue; }
                };
                match o.get("nick") {
                    Some(n) if is_token(n) => {
                        let n = n.as_str().unwrap();
                        if !nicks.insert(n.to_string()) {
                            errors.push(format!("duplicate agent nick: {n}"));
                        }
                    }
                    _ => errors.push(format!("{where_}.nick must be a lowercase token")),
                }
                if !o.get("role").map(nonempty_str).unwrap_or(false) {
                    errors.push(format!("{where_}.role must be a non-empty string"));
                }
                match o.get("serves") {
                    Some(Value::Array(serves)) => {
                        for wid in serves {
                            let wid = wid.as_str().unwrap_or("");
                            if !watcher_ids.contains(wid) {
                                errors.push(format!("{where_}.serves names unknown watcher: {wid}"));
                            }
                        }
                    }
                    _ => errors.push(format!("{where_}.serves must be a list")),
                }
            }
        }
        _ => errors.push("agents must be a non-empty list".to_string()),
    }
    // Alerts.
    let mut kinds = std::collections::HashSet::new();
    match obj.get("alerts") {
        Some(Value::Array(alerts)) if !alerts.is_empty() => {
            for (i, a) in alerts.iter().enumerate() {
                let where_ = format!("alerts[{i}]");
                let o = match a.as_object() {
                    Some(o) => o,
                    None => { errors.push(format!("{where_} is not an object")); continue; }
                };
                match o.get("kind") {
                    Some(k) if is_token(k) => {
                        let k = k.as_str().unwrap();
                        if !kinds.insert(k.to_string()) {
                            errors.push(format!("duplicate alert kind: {k}"));
                        }
                    }
                    _ => errors.push(format!("{where_}.kind must be a lowercase token")),
                }
                if !o.get("severity").and_then(Value::as_str).map(|s| SEVERITIES.contains(&s)).unwrap_or(false) {
                    errors.push(format!("{where_}.severity must be one of {}", SEVERITIES.join(", ")));
                }
                let priv_ok = o.get("privacy").and_then(Value::as_str).map(|s| PRIVACY.contains(&s)).unwrap_or(false);
                if !priv_ok {
                    errors.push(format!("{where_}.privacy must be one of {}", PRIVACY.join(", ")));
                }
                match o.get("crosses_bus") {
                    Some(Value::Bool(b)) => {
                        if *b && o.get("privacy").and_then(Value::as_str) != Some("summary") {
                            errors.push(format!("{where_} crosses the bus but its privacy is not 'summary'; only summaries may cross"));
                        }
                    }
                    _ => errors.push(format!("{where_}.crosses_bus must be a boolean")),
                }
                if !o.get("carries").map(nonempty_str).unwrap_or(false) {
                    errors.push(format!("{where_}.carries must be a non-empty string"));
                }
                if !o.get("urgency").and_then(Value::as_str).map(|s| URGENCY.contains(&s)).unwrap_or(false) {
                    errors.push(format!("{where_}.urgency must be one of {}", URGENCY.join(", ")));
                }
            }
        }
        _ => errors.push("alerts must be a non-empty list".to_string()),
    }
    // privacy_classes.
    match obj.get("privacy_classes").and_then(Value::as_object) {
        Some(pc) => {
            for k in ["local_only", "bus_summary"] {
                match pc.get(k) {
                    Some(Value::Array(v)) if !v.is_empty() && v.iter().all(nonempty_str) => {},
                    _ => errors.push(format!("privacy_classes.{k} must be a non-empty list of strings")),
                }
            }
        }
        None => errors.push("privacy_classes must be an object".to_string()),
    }
    // cross_world.
    match obj.get("cross_world").and_then(Value::as_object) {
        Some(cw) => {
            for k in ["sends", "receives"] {
                if !matches!(cw.get(k), Some(Value::Array(_))) {
                    errors.push(format!("cross_world.{k} must be a list"));
                }
            }
            if let Some(Value::Array(sends)) = cw.get("sends") {
                for (i, s) in sends.iter().enumerate() {
                    let where_ = format!("cross_world.sends[{i}]");
                    let o = match s.as_object() {
                        Some(o) => o,
                        None => { errors.push(format!("{where_} is not an object")); continue; }
                    };
                    if !o.get("to").map(is_token).unwrap_or(false) {
                        errors.push(format!("{where_}.to must be a lowercase token"));
                    }
                    if !o.get("kind").map(is_token).unwrap_or(false) {
                        errors.push(format!("{where_}.kind must be a lowercase token"));
                    }
                    if !o.get("carries").map(nonempty_str).unwrap_or(false) {
                        errors.push(format!("{where_}.carries must be a non-empty string"));
                    }
                    match o.get("never_carries") {
                        Some(Value::Array(n)) if !n.is_empty() && n.iter().all(nonempty_str) => {},
                        _ => errors.push(format!("{where_}.never_carries must be a non-empty list of strings; a message that may cross the bus must say what it never carries")),
                    }
                }
            }
            if let Some(Value::Array(recvs)) = cw.get("receives") {
                for (i, r) in recvs.iter().enumerate() {
                    let where_ = format!("cross_world.receives[{i}]");
                    let o = match r.as_object() {
                        Some(o) => o,
                        None => { errors.push(format!("{where_} is not an object")); continue; }
                    };
                    if !o.get("from").map(is_token).unwrap_or(false) {
                        errors.push(format!("{where_}.from must be a lowercase token"));
                    }
                    if !o.get("kind").map(is_token).unwrap_or(false) {
                        errors.push(format!("{where_}.kind must be a lowercase token"));
                    }
                    if !o.get("carries").map(nonempty_str).unwrap_or(false) {
                        errors.push(format!("{where_}.carries must be a non-empty string"));
                    }
                }
            }
        }
        None => errors.push("cross_world must be an object".to_string()),
    }
    // firstboot.
    match obj.get("firstboot") {
        Some(Value::Array(fb)) if !fb.is_empty() => {
            let mut fields = std::collections::HashSet::new();
            for (i, e) in fb.iter().enumerate() {
                let where_ = format!("firstboot[{i}]");
                let o = match e.as_object() {
                    Some(o) => o,
                    None => { errors.push(format!("{where_} is not an object")); continue; }
                };
                match o.get("field").and_then(Value::as_str) {
                    Some(f) if is_field(f) => {
                        if !fields.insert(f.to_string()) {
                            errors.push(format!("duplicate firstboot field: {f}"));
                        }
                    }
                    _ => errors.push(format!("{where_}.field must be a lowercase field name")),
                }
                if !o.get("label").map(nonempty_str).unwrap_or(false) {
                    errors.push(format!("{where_}.label must be a non-empty string"));
                }
                if !matches!(o.get("required"), Some(Value::Bool(_))) {
                    errors.push(format!("{where_}.required must be a boolean"));
                }
            }
        }
        _ => errors.push("firstboot must be a non-empty list".to_string()),
    }
    // urgency (unique classes + unique ranks).
    match obj.get("urgency") {
        Some(Value::Array(us)) if !us.is_empty() => {
            let mut seen_c = std::collections::HashSet::new();
            let mut seen_r = std::collections::HashSet::new();
            for (i, e) in us.iter().enumerate() {
                let where_ = format!("urgency[{i}]");
                let o = match e.as_object() {
                    Some(o) => o,
                    None => { errors.push(format!("{where_} is not an object")); continue; }
                };
                match o.get("class").and_then(Value::as_str) {
                    Some(c) if URGENCY.contains(&c) => {
                        if !seen_c.insert(c.to_string()) {
                            errors.push(format!("duplicate urgency class: {c}"));
                        }
                    }
                    _ => errors.push(format!("{where_}.class must be one of {}", URGENCY.join(", "))),
                }
                match o.get("rank") {
                    Some(Value::Number(n)) if n.as_u64().map(|r| r >= 1).unwrap_or(false) => {
                        let r = n.as_u64().unwrap();
                        if !seen_r.insert(r) {
                            errors.push(format!("duplicate urgency rank: {r}"));
                        }
                    }
                    _ => errors.push(format!("{where_}.rank must be a positive integer")),
                }
                if !o.get("meaning").map(nonempty_str).unwrap_or(false) {
                    errors.push(format!("{where_}.meaning must be a non-empty string"));
                }
            }
        }
        _ => errors.push("urgency must be a non-empty list".to_string()),
    }
    errors
}

/// Pack-name-must-match-directory check (ports `validate_pack_at` tail).
pub fn pack_dir_matches(manifest: &Value, dirname: &str) -> Option<String> {
    match manifest.get("pack").and_then(Value::as_str) {
        Some(p) if p != dirname => Some(format!("pack name {p:?} does not match its directory {dirname:?}")),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_non_object_and_missing_keys() {
        assert_eq!(validate_pack(&Value::Null), vec!["manifest is not a JSON object".to_string()]);
        let m = serde_json::json!({"pack": "fdny"});
        let errs = validate_pack(&m);
        assert!(errs.iter().any(|e| e.contains("missing required key")));
    }

    #[test]
    fn privacy_crossing_rule() {
        // Minimal valid manifest, then flip privacy to trigger the crossing rule.
        let mut m = minimal_manifest();
        m["alerts"][0]["privacy"] = serde_json::json!("local");
        // crosses_bus=true + local => error.
        let errs = validate_pack(&m);
        assert!(errs.iter().any(|e| e.contains("only summaries may cross")));
    }

    #[test]
    fn dir_match() {
        let m = serde_json::json!({"pack": "fdny"});
        assert!(pack_dir_matches(&m, "fdny").is_none());
        assert!(pack_dir_matches(&m, "nypd").is_some());
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
}
