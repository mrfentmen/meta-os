//! Minimal blocked-push builder (`os/intel/push.py`,
//! blocked-push half, as pinned by OS-122).
//!
//! Canonical home is Hana's `intel` crate (B10). This module
//! carries exactly what `watchman_watch` needs: build the blocked
//! push for a parked job, or `None` when gated out, plus
//! validation. Pushes are built, never sent: sending belongs to
//! the Web Push worker outside this repo, so this module has no
//! network, no bus post, and no secret.

use serde_json::{Map, Value};

/// Push types that exist. Anything else raises (a typo must fail
/// loudly rather than silently become a new kind of ring).
pub const PUSH_TYPES: &[&str] = &["done", "blocked"];

fn job_id(job: &Map<String, Value>) -> Option<String> {
    match job.get("id") {
        Some(Value::String(s)) if !s.is_empty() => Some(s.clone()),
        Some(Value::Number(n)) => Some(n.to_string()),
        _ => None,
    }
}

fn job_title(job: &Map<String, Value>) -> String {
    match job.get("title") {
        Some(Value::String(s)) if !s.is_empty() => s.clone(),
        _ => "untitled job".to_string(),
    }
}

/// Build the blocked push for a parked job, or `None`.
///
/// The question is the caller's question when one is given, else
/// the job's stored note. With neither, or with a job that is
/// not status "blocked", returns `None`: no question is ever
/// invented.
pub fn build_blocked_push(job: &Map<String, Value>, question: Option<&str>) -> Option<Value> {
    let jid = job_id(job)?;
    if job.get("status").and_then(|v| v.as_str()) != Some("blocked") {
        return None;
    }
    let q = match question {
        Some(q) if !q.trim().is_empty() => q.trim().to_string(),
        _ => match job.get("note").and_then(|v| v.as_str()) {
            Some(note) if !note.trim().is_empty() => note.trim().to_string(),
            _ => return None,
        },
    };
    let title = job_title(job);
    let mut push = Map::new();
    push.insert("type".to_string(), Value::String("blocked".to_string()));
    push.insert("job_id".to_string(), Value::String(jid));
    push.insert("title".to_string(), Value::String(title.clone()));
    push.insert(
        "body".to_string(),
        Value::String(format!("{title} is blocked. Question: {q}")),
    );
    push.insert("question".to_string(), Value::String(q));
    Some(Value::Object(push))
}

/// `true` only for a well-formed push of a known type.
pub fn validate_push(push: &Value) -> bool {
    let obj = match push.as_object() {
        Some(o) => o,
        None => return false,
    };
    match obj.get("type").and_then(|v| v.as_str()) {
        Some("done") | Some("blocked") => {}
        _ => return false,
    }
    if job_id_like(obj.get("job_id")).is_none() {
        return false;
    }
    match obj.get("body").and_then(|v| v.as_str()) {
        Some(body) if !body.trim().is_empty() => true,
        _ => false,
    }
}

fn job_id_like(value: Option<&Value>) -> Option<String> {
    match value {
        Some(Value::String(s)) if !s.is_empty() => Some(s.clone()),
        Some(Value::Number(n)) => Some(n.to_string()),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn parked() -> Map<String, Value> {
        json!({"id": "watchman:m1", "title": "Watchman on machine m1",
               "status": "blocked", "note": "why is it dark?"})
            .as_object()
            .unwrap()
            .clone()
    }

    #[test]
    fn blocked_push_builds_with_question() {
        let push = build_blocked_push(&parked(), Some("Dale's call is needed.")).unwrap();
        assert!(validate_push(&push));
        assert_eq!(push["type"], json!("blocked"));
        assert!(push["body"].as_str().unwrap().contains("Dale's call is needed."));
    }

    #[test]
    fn note_is_the_fallback_question() {
        let push = build_blocked_push(&parked(), None).unwrap();
        assert!(push["body"].as_str().unwrap().contains("why is it dark?"));
    }

    #[test]
    fn gated_out_without_question_or_note_or_unblocked() {
        let mut job = parked();
        job.remove("note");
        assert!(build_blocked_push(&job, None).is_none());
        let mut job = parked();
        job.insert("status".to_string(), json!("open"));
        assert!(build_blocked_push(&job, Some("q")).is_none());
        assert!(!validate_push(&json!({"type": "nonsense"})));
        assert!(!validate_push(&json!({"type": "blocked"})));
    }
}
