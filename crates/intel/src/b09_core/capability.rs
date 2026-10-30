//! Port of `os/intel/capability.py` — capability refusal enforcement.
//!
//! Rules (in check order):
//! 1. Non-dict attempt / unknown action -> no decision (`None`).
//! 2. No grant or grant without identity -> refused, "no capability grant on file".
//! 3. Known action whose flag is not exactly `true` -> refused, "capability not granted".
//! 4. `write_file` with no path -> "no file path given"; path escaping grant
//!    prefixes (whole-segment match) or empty grant prefixes -> "write path outside grant".
//! 5. Else allowed; allowed attempts journal nothing.

/// Known judged actions.
pub const ACTIONS: &[&str] = &["bus_post", "spend", "network", "write_file"];

/// A capability grant in OS-080 shape.
#[derive(Debug, Clone, PartialEq)]
pub struct Grant {
    pub identity: String,
    pub bus_post: bool,
    pub spend: bool,
    pub network: bool,
    pub write_paths: Vec<String>,
}

/// Refusal / allowance decision.
#[derive(Debug, Clone, PartialEq)]
pub struct Decision {
    pub allowed: bool,
    pub identity: String,
    pub action: String,
    pub subject: Option<String>,
    pub missing_capability: Option<String>,
    pub reason: Option<String>,
}

/// Lexically normalize a relative path; `None` if it escapes (absolute,
/// empty, `..` above root, or no surviving segments).
pub fn normalize_path(path: &str) -> Option<String> {
    if path.is_empty() || path.starts_with('/') {
        return None;
    }
    let mut parts: Vec<&str> = Vec::new();
    for seg in path.split('/') {
        if seg.is_empty() || seg == "." {
            continue;
        }
        if seg == ".." {
            if parts.is_empty() {
                return None;
            }
            parts.pop();
            continue;
        }
        parts.push(seg);
    }
    if parts.is_empty() {
        return None;
    }
    Some(parts.join("/"))
}

fn path_inside(path: &str, prefix: &str) -> bool {
    let (Some(p), Some(q)) = (normalize_path(path), normalize_path(prefix)) else {
        return false;
    };
    let p: Vec<&str> = p.split('/').collect();
    let q: Vec<&str> = q.split('/').collect();
    p.len() >= q.len() && p[..q.len()] == q[..]
}

fn refused(
    identity: &str,
    action: &str,
    subject: Option<String>,
    missing: Option<String>,
    reason: &str,
) -> Decision {
    Decision {
        allowed: false,
        identity: identity.to_string(),
        action: action.to_string(),
        subject,
        missing_capability: missing,
        reason: Some(reason.to_string()),
    }
}

/// Judge one action. `grant=None` models a missing/non-dict grant.
/// Unknown action -> `None` (no decision, never silently allowed).
pub fn check_action(
    grant: Option<&Grant>,
    action: &str,
    subject: Option<&str>,
    identity_override: Option<&str>,
) -> Option<Decision> {
    if !ACTIONS.contains(&action) {
        return None;
    }
    let g = grant?;
    if g.identity.is_empty() {
        let id = identity_override.unwrap_or("").to_string();
        return Some(refused(&id, action, subject.map(str::to_string), None, "no capability grant on file"));
    }
    let identity = identity_override.unwrap_or(&g.identity).to_string();
    let flag = match action {
        "bus_post" => g.bus_post,
        "spend" => g.spend,
        "network" => g.network,
        "write_file" => true, // judged by path below, not by a flag
        _ => return None,
    };
    if action != "write_file" && !flag {
        return Some(refused(
            &identity,
            action,
            subject.map(str::to_string),
            Some(action.to_string()),
            "capability not granted",
        ));
    }
    if action == "write_file" {
        let Some(subj) = subject else {
            return Some(refused(&identity, action, None, Some("write:".to_string()), "no file path given"));
        };
        if normalize_path(subj).is_none() {
            return Some(refused(
                &identity,
                action,
                Some(subj.to_string()),
                Some(format!("write:{subj}")),
                "write path outside grant",
            ));
        }
        let inside = g.write_paths.iter().any(|p| path_inside(subj, p));
        if !inside {
            return Some(refused(
                &identity,
                action,
                Some(subj.to_string()),
                Some(format!("write:{subj}")),
                "write path outside grant",
            ));
        }
        return Some(Decision {
            allowed: true,
            identity,
            action: action.to_string(),
            subject: Some(subj.to_string()),
            missing_capability: None,
            reason: None,
        });
    }
    Some(Decision {
        allowed: true,
        identity,
        action: action.to_string(),
        subject: subject.map(str::to_string),
        missing_capability: None,
        reason: None,
    })
}

/// Build the alert record map for a refusal (caller persists via store).
/// Returns (kind, severity, explanation, suggested_fix) triple data.
pub fn refusal_alert(decision: &Decision) -> Option<RefusalAlert> {
    if decision.allowed {
        return None;
    }
    Some(RefusalAlert {
        kind: "capability-refusal".to_string(),
        severity: "high".to_string(),
        identity: decision.identity.clone(),
        action: decision.action.clone(),
        subject: decision.subject.clone(),
        reason: decision.reason.clone().unwrap_or_default(),
    })
}

/// Plain-English refusal note.
pub fn refusal_note(decision: &Decision) -> Option<String> {
    if decision.allowed {
        return None;
    }
    Some(format!(
        "{} attempted {} ({}) but was refused: {}.",
        decision.identity,
        decision.action,
        decision.subject.clone().unwrap_or_default(),
        decision.reason.clone().unwrap_or_default()
    ))
}

#[derive(Debug, Clone, PartialEq)]
pub struct RefusalAlert {
    pub kind: String,
    pub severity: String,
    pub identity: String,
    pub action: String,
    pub subject: Option<String>,
    pub reason: String,
}

/// One capability tick: judge a batch of attempts, returning refusal alerts
/// for refused attempts only (allowed attempts journal nothing). Skips
/// attempts already journaled (dedupe keys supplied by caller).
pub fn capability_tick(
    grant: Option<&Grant>,
    attempts: &[(String, Option<String>)],
    already_journaled: &[String],
) -> Vec<RefusalAlert> {
    let mut out = Vec::new();
    for (action, subject) in attempts {
        let key = format!("capability:{}:{}", action, subject.clone().unwrap_or_default());
        if already_journaled.contains(&key) {
            continue;
        }
        if let Some(d) = check_action(grant, action, subject.as_deref(), None) {
            if !d.allowed {
                if let Some(a) = refusal_alert(&d) {
                    out.push(a);
                }
            }
        }
    }
    out
}

/// Brief lines for refusal alerts.
pub fn brief_lines(alerts: &[RefusalAlert]) -> Vec<String> {
    alerts
        .iter()
        .map(|a| {
            format!(
                "Capability refusal: {} attempted {}{} — {}.",
                a.identity,
                a.action,
                a.subject.clone().map(|s| format!(" {s}")).unwrap_or_default(),
                a.reason
            )
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn grant() -> Grant {
        Grant {
            identity: "milo".to_string(),
            bus_post: false,
            spend: false,
            network: true,
            write_paths: vec!["crew/milo/".to_string()],
        }
    }

    #[test]
    fn unknown_action_yields_no_decision() {
        assert!(check_action(Some(&grant()), "fly", None, None).is_none());
    }

    #[test]
    fn missing_grant_is_refused() {
        let d = check_action(None, "bus_post", None, None).unwrap();
        assert!(!d.allowed);
        assert_eq!(d.reason.as_deref(), Some("no capability grant on file"));
    }

    #[test]
    fn ungranted_flag_refused() {
        let d = check_action(Some(&grant()), "bus_post", None, None).unwrap();
        assert!(!d.allowed);
        assert_eq!(d.missing_capability.as_deref(), Some("bus_post"));
    }

    #[test]
    fn network_allowed_silent() {
        let d = check_action(Some(&grant()), "network", None, None).unwrap();
        assert!(d.allowed);
        assert!(refusal_alert(&d).is_none());
    }

    #[test]
    fn write_inside_grant_allowed() {
        let d = check_action(Some(&grant()), "write_file", Some("crew/milo/notes.md"), None).unwrap();
        assert!(d.allowed);
    }

    #[test]
    fn write_outside_grant_refused_whole_segments() {
        // "crew/milo2/x" must NOT match prefix "crew/milo/"
        let d = check_action(Some(&grant()), "write_file", Some("crew/milo2/x"), None).unwrap();
        assert!(!d.allowed);
        assert_eq!(d.reason.as_deref(), Some("write path outside grant"));
    }

    #[test]
    fn absolute_path_refused() {
        let d = check_action(Some(&grant()), "write_file", Some("/etc/passwd"), None).unwrap();
        assert!(!d.allowed);
    }

    #[test]
    fn dotdot_escape_refused() {
        let d = check_action(Some(&grant()), "write_file", Some("crew/milo/../../x"), None).unwrap();
        assert!(!d.allowed);
    }

    #[test]
    fn normalize_dot_segments() {
        assert_eq!(normalize_path("crew/milo/./a").as_deref(), Some("crew/milo/a"));
        assert_eq!(normalize_path("crew/milo/sub/../a").as_deref(), Some("crew/milo/a"));
    }
}
