//! Port of `os/intel/explanations.py` — alert explanation templates.
//!
//! One one-liner + one suggested fix per detector kind, rendered from
//! `{name}` placeholders. Unknown template -> `Err`; missing placeholder ->
//! `Err` (never ship a half-filled explanation). Optional Spark polish:
//! with no/failed/empty client the template text comes back unchanged.

use std::collections::HashMap;

/// (template_key, explanation_template, fix_template).
const TEMPLATES: &[(&str, &str, &str)] = &[
    ("presence-stall",
     "{nick} holds claimed job {job} but has been absent from presence for over {stall_minutes} minutes with no progress on it for {age_minutes} minutes.",
     "Check on {nick}; if the worker is gone, the lease sweep will requeue job {job} for another worker."),
    ("progress-stall",
     "{nick} is present and holding claimed job {job}, but has made no progress on it for {age_minutes} minutes (over the {window_minutes}-minute window): the worker is alive, the work is stuck.",
     "Nudge {nick} about job {job}; if it stays stuck, restart the worker."),
    ("file-collision",
     "{nick_a} and {nick_b} both claim jobs touching {path}: only one can land first.",
     "Have {nick_a} and {nick_b} agree on who lands {path} first."),
    ("file-collision-merged",
     "{nick} claims a job touching {path} but the branch already landed it: rebase onto the merged work.",
     "Rebase the job touching {path} onto the landed branch."),
    ("dead-dep",
     "Job {job} waits on {dep} which cannot proceed.{blocking_note}",
     "Clear the blocker on {dep} or re-target job {job}."),
    ("capability-refusal",
     "{identity} attempted {action} but was refused: {reason}.",
     "Grant the capability or stop attempting {action}."),
];

fn required_placeholders(template: &str) -> Vec<String> {
    let mut out = Vec::new();
    let mut rest = template;
    while let Some(a) = rest.find('{') {
        let after = &rest[a + 1..];
        if let Some(b) = after.find('}') {
            out.push(after[..b].to_string());
            rest = &after[b + 1..];
        } else {
            break;
        }
    }
    out.sort();
    out.dedup();
    out
}

fn fill(template: &str, fields: &HashMap<String, String>) -> Result<String, String> {
    for need in required_placeholders(template) {
        if !fields.contains_key(&need) {
            return Err(format!("missing placeholder: {need}"));
        }
    }
    let mut out = template.to_string();
    for (k, v) in fields {
        out = out.replace(&format!("{{{k}}}"), v);
    }
    Ok(out)
}

/// Render (explanation, suggested_fix) for a template key.
pub fn render(key: &str, fields: &HashMap<String, String>) -> Result<(String, String), String> {
    let (_, expl, fix) = TEMPLATES
        .iter()
        .find(|(k, _, _)| *k == key)
        .ok_or_else(|| format!("unknown template: {key}"))?;
    // dead-dep special: blocking_note defaults to "" then formats.
    let mut f = fields.clone();
    if *key == "dead-dep" && !f.contains_key("blocking_note") {
        f.insert("blocking_note".to_string(), String::new());
    }
    Ok((fill(expl, &f)?, fill(fix, &f)?))
}

/// Optional Spark polish: `polish=None` / `Err` / empty -> template unchanged.
pub fn polish_explanation(
    template_text: &str,
    polish: Option<Result<String, String>>,
) -> String {
    match polish {
        Some(Ok(s)) if !s.trim().is_empty() => s,
        _ => template_text.to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fields(pairs: &[(&str, &str)]) -> HashMap<String, String> {
        pairs.iter().map(|(k, v)| (k.to_string(), v.to_string())).collect()
    }

    #[test]
    fn renders_presence_stall() {
        let (e, f) = render(
            "presence-stall",
            &fields(&[("nick", "milo"), ("job", "j1"), ("stall_minutes", "12"), ("age_minutes", "9")]),
        )
        .unwrap();
        assert!(e.contains("milo") && e.contains("j1"));
        assert!(f.contains("milo"));
    }

    #[test]
    fn unknown_template_errors() {
        assert!(render("nope", &fields(&[])).is_err());
    }

    #[test]
    fn missing_placeholder_errors() {
        assert!(render("presence-stall", &fields(&[("nick", "milo")])).is_err());
    }

    #[test]
    fn polish_fallback_keeps_template() {
        assert_eq!(polish_explanation("abc", None), "abc");
        assert_eq!(polish_explanation("abc", Some(Err("down".to_string()))), "abc");
        assert_eq!(polish_explanation("abc", Some(Ok("  ".to_string()))), "abc");
    }
}
