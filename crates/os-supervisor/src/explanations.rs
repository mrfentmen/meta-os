//! Alert explanation templates (`os/intel/explanations.py`,
//! detector templates used by B21).
//!
//! Canonical home is Hana's `intel` crate (B09). This module
//! carries exactly the templates the watchdog detectors render,
//! plus the WDG-012 polish rule: with no client, a raising
//! client, or an empty reply, the template text comes back
//! unchanged. `render` raises for an unknown template key, and
//! missing placeholders are a hard error (a half-filled
//! explanation must never reach a human).

use std::collections::BTreeMap;

/// Render one template with the given fields.
pub fn render(kind: &str, fields: &BTreeMap<&str, String>) -> Result<(String, String), String> {
    let (exp_tpl, fix_tpl) = template(kind)?;
    Ok((fill(exp_tpl, fields)?, fill(fix_tpl, fields)?))
}

fn template(kind: &str) -> Result<(&'static str, &'static str), String> {
    match kind {
        "presence-stall" => Ok((
            "{nick} holds claimed job {job} but has been absent from presence for over {stall_minutes} minutes with no progress on it for {age_minutes} minutes.",
            "Check on {nick}; if the worker is gone, the lease sweep will requeue job {job} for another worker.",
        )),
        "progress-stall" => Ok((
            "{nick} is present and holding claimed job {job}, but has made no progress on it for {age_minutes} minutes (over the {window_minutes}-minute window): the worker is alive, the work is stuck.",
            "Check what {nick} is stuck on for job {job}; if the work is blocked, the lease sweep will requeue it for another worker.",
        )),
        "lease-risk" => Ok((
            "Claimed job {job} held by {nick} has its lease expiring in {minutes_to_expiry} minute(s) with no heartbeat in the last {quiet_minutes} minutes: renew it or the lease sweep will requeue the job.",
            "Have {nick} heartbeat job {job} to renew the lease, or let the sweep requeue it for another worker.",
        )),
        "dead-dep" => Ok((
            "Job {job} cannot proceed: its dependency {dep} is {dep_status}.{blocking_note}",
            "Unblock or replace dependency {dep} (currently {dep_status}) so job {job} can proceed, or repost job {job} without that dependency.",
        )),
        "missing-dep" => Ok((
            "Job {job} depends on job {dep}, which does not exist in the job index: the dependency was never posted, was deleted, or was mistyped.",
            "Repost job {job} without dependency {dep}, or post the missing job {dep} first, then re-check job {job}.",
        )),
        "file-collision" => Ok((
            "Jobs {job} and {other_job} both touch {shared_path}: two workers editing the same file will collide at merge time.",
            "Coordinate jobs {job} and {other_job} before either finishes: split {shared_path} between them, or hold one job until the other merges.",
        )),
        "file-collision-done" => Ok((
            "Claimed job {job} touches {shared_path}, which job {other_job} already finished on branch {branch}: the new claim risks redoing or clobbering finished work.",
            "Coordinate jobs {job} and {other_job} before either finishes: split {shared_path} between them, or hold one job until the other merges.",
        )),
        "attempt-warning" => Ok((
            "Job {job} has used {attempts} of {max_attempts} attempts: one attempt left before the job goes failed-final instead of requeueing.",
            "Fix the blocker on job {job} now, or repost it with a larger attempt budget before the last attempt burns.",
        )),
        "attempt-exhaustion" => Ok((
            "Job {job} has used {attempts} of {max_attempts} attempts: its attempt budget is spent and the job is failed-final, not requeued.",
            "Do not requeue job {job} as-is: fix the blocker, then repost it with a fresh attempt budget.",
        )),
        "silent-room" => Ok((
            "The room has claimed jobs ({claimed_ids}) but no messages for {age_minutes} minutes (over the {window_minutes}-minute window): the crew may be stuck, or heads-down in deep work.",
            "No action required: this is informational only. If the crew is stuck, check on the claimed jobs; if they are heads-down, this record needs nothing.",
        )),
        "rejected-dispatch" => Ok((
            "Job {job} was refused: its signature verdict is {verdict} (posted as {signed_by}, refused by {rejected_by}). The job stays open and unclaimed, and the refusal is the evidence, not an accusation against the refuser.",
            "Do not claim job {job} without verifying its signature against the crew keyring. If the poster is legitimate, repost the job with a fresh signature; if it is not, leave the job open and tell the crew who posted it.",
        )),
        "budget-warning" => Ok((
            "The {lane} lane has spent {spent} of its {cap} budget ({remaining} remaining): it is past the {warn_percent}% warning threshold, so the next claims could hit the cap and stop the lane silently.",
            "Slow new {lane} claims, raise the lane cap, or let the lane finish its current work before posting more — at cap, new claims are held and the job stays open.",
        )),
        _ => Err(format!("unknown explanation template {kind:?}")),
    }
}

fn fill(template: &str, fields: &BTreeMap<&str, String>) -> Result<String, String> {
    let mut out = String::new();
    let mut rest = template;
    loop {
        match rest.find('{') {
            None => {
                out.push_str(rest);
                return Ok(out);
            }
            Some(open) => {
                out.push_str(&rest[..open]);
                let after = &rest[open + 1..];
                match after.find('}') {
                    None => return Err("unclosed placeholder".to_string()),
                    Some(close) => {
                        let key = &after[..close];
                        match fields.get(key) {
                            Some(v) => out.push_str(v),
                            None => return Err(format!("missing placeholder {key:?}")),
                        }
                        rest = &after[close + 1..];
                    }
                }
            }
        }
    }
}

/// WDG-012 polish pass: rewrite for clarity only when a client is
/// supplied. With no client, a raising client, or an empty reply,
/// the template text stands. The suggested fix is never polished.
/// `polish` is `Fn(&str) -> Option<String>` (the Spark call);
/// `None` or empty means failure and keeps the template.
pub fn polish_explanation<F>(template_text: &str, polish: Option<F>) -> String
where
    F: Fn(&str) -> Option<String>,
{
    match polish {
        None => template_text.to_string(),
        Some(f) => match f(template_text) {
            Some(polished) if !polished.trim().is_empty() => polished,
            _ => template_text.to_string(),
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fields(pairs: &[(&str, &str)]) -> BTreeMap<&str, String> {
        pairs
            .iter()
            .map(|(k, v)| (*k, v.to_string()))
            .collect()
    }

    #[test]
    fn presence_stall_template() {
        let (exp, _fix) = render(
            "presence-stall",
            &fields(&[("nick", "pax"), ("job", "7"), ("stall_minutes", "10"), ("age_minutes", "61")]),
        )
        .unwrap();
        assert!(exp.contains("pax holds claimed job 7"), "{exp}");
        assert!(exp.contains("over 10 minutes"), "{exp}");
    }

    #[test]
    fn unknown_template_raises() {
        assert!(render("nope", &fields(&[])).is_err());
    }

    #[test]
    fn missing_placeholder_raises() {
        assert!(render("presence-stall", &fields(&[("nick", "pax")])).is_err());
    }

    #[test]
    fn polish_toggle_off_and_failure() {
        assert_eq!(polish_explanation::<fn(&str) -> Option<String>>("T", None), "T");
        assert_eq!(polish_explanation("T", Some(|_: &str| None)), "T");
        assert_eq!(polish_explanation("T", Some(|_: &str| Some(String::new()))), "T");
        assert_eq!(polish_explanation("T", Some(|_: &str| Some("  ".to_string()))), "T");
        assert_eq!(polish_explanation("T", Some(|t: &str| Some(format!("{t}!")))), "T!");
    }

    #[test]
    fn budget_warning_template_names_lane_figures_threshold() {
        let (exp, _fix) = render(
            "budget-warning",
            &fields(&[
                ("lane", "spark"),
                ("spent", "80"),
                ("cap", "100"),
                ("remaining", "20"),
                ("warn_percent", "80"),
            ]),
        )
        .unwrap();
        assert!(exp.contains("spark"), "{exp}");
        assert!(exp.contains("80"), "{exp}");
        assert!(exp.contains("80% warning threshold"), "{exp}");
    }
}
