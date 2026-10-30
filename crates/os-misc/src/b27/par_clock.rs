//! B27 par_clock — port of `os/worlds/fdny/runtime/par_clock.py` (T015).
//!
//! FDNY PAR clock: per-crew accountability timer. Human officer feeds
//! enter/complete/exit; clock raises `par-check-due` (warning/urgent)
//! then `crew-unaccounted` (critical/life-safety). Pure core:
//! `tick` and state fns never mutate inputs, take no counter, no model
//! calls. CLI is the only I/O (at the gate).

use std::collections::{BTreeMap, BTreeSet};

pub const DEFAULT_INTERVAL_SECONDS: i64 = 600;
pub const DEFAULT_GRACE_SECONDS: i64 = 120;

pub const KIND_PAR_CHECK_DUE: &str = "par-check-due";
pub const KIND_CREW_UNACCOUNTED: &str = "crew-unaccounted";

pub const SEVERITY_WARNING: &str = "warning";
pub const SEVERITY_CRITICAL: &str = "critical";

pub const TL_ENTER: &str = "par-enter";
pub const TL_COMPLETE: &str = "par-complete";
pub const TL_EXIT: &str = "par-exit";

#[derive(Debug, Clone, PartialEq)]
pub struct CrewRecord {
    pub crew_id: String,
    pub entered_at: i64,
    pub last_par_at: Option<i64>,
    pub location: Option<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct TimelineEvent {
    pub kind: String,
    pub crew: String,
    pub ts: i64,
    pub location: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Default)]
pub struct ParState {
    pub roster: BTreeMap<String, CrewRecord>,
    pub ledger: Vec<String>,
    pub timeline: Vec<TimelineEvent>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct AlertEvent {
    pub kind: String,
    pub severity: String,
    pub urgency: String,
    pub alert_id: String,
    pub crew: String,
    pub due_at: i64,
    pub entered_at: i64,
    pub ts: i64,
    pub explanation: String,
    pub suggested_fix: String,
    pub location: Option<String>,
}

/// Crew id: non-empty string, no whitespace.
pub fn validated_crew_id(crew_id: &str) -> Result<String, String> {
    let c = crew_id.trim();
    if c.is_empty() {
        return Err("crew id may not be empty".to_string());
    }
    if c.chars().any(|ch| ch.is_whitespace()) {
        return Err("crew id may not contain whitespace".to_string());
    }
    Ok(c.to_string())
}

pub fn new_state() -> ParState {
    ParState::default()
}

fn is_int(v: &serde_json::Value) -> bool {
    matches!(v, serde_json::Value::Number(n) if n.as_i64().is_some())
}

pub fn enter_crew(
    state: &ParState,
    crew_id: &str,
    entered_at: i64,
    location: Option<&str>,
) -> Result<ParState, String> {
    let crew_id = validated_crew_id(crew_id)?;
    let mut out = state.clone();
    if out.roster.contains_key(&crew_id) {
        return Err(format!("crew {crew_id} is already inside"));
    }
    let loc = location
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(str::to_string);
    out.roster.insert(
        crew_id.clone(),
        CrewRecord {
            crew_id: crew_id.clone(),
            entered_at,
            last_par_at: None,
            location: loc.clone(),
        },
    );
    out.timeline.push(TimelineEvent {
        kind: TL_ENTER.to_string(),
        crew: crew_id,
        ts: entered_at,
        location: loc,
    });
    Ok(out)
}

pub fn complete_par(state: &ParState, crew_id: &str, now: i64) -> Result<ParState, String> {
    let crew_id = validated_crew_id(crew_id)?;
    let mut out = state.clone();
    match out.roster.get_mut(&crew_id) {
        None => Err(format!("crew {crew_id} is not inside")),
        Some(rec) => {
            rec.last_par_at = Some(now);
            out.timeline.push(TimelineEvent {
                kind: TL_COMPLETE.to_string(),
                crew: crew_id,
                ts: now,
                location: None,
            });
            Ok(out)
        }
    }
}

pub fn exit_crew(state: &ParState, crew_id: &str, now: i64) -> Result<ParState, String> {
    let crew_id = validated_crew_id(crew_id)?;
    let mut out = state.clone();
    if !out.roster.contains_key(&crew_id) {
        return Err(format!("crew {crew_id} is not inside"));
    }
    out.timeline.push(TimelineEvent {
        kind: TL_EXIT.to_string(),
        crew: crew_id.clone(),
        ts: now,
        location: None,
    });
    out.roster.remove(&crew_id);
    let prefix = format!("par:{crew_id}:");
    out.ledger.retain(|k| !k.starts_with(&prefix));
    Ok(out)
}

fn make_event(
    kind: &str,
    severity: &str,
    urgency: &str,
    crew_id: &str,
    due_at: i64,
    now: i64,
    record: &CrewRecord,
) -> AlertEvent {
    let (alert_id, explanation, fix) = if kind == KIND_PAR_CHECK_DUE {
        (
            format!("par-due-{crew_id}-{due_at}"),
            format!(
                "PAR check for crew {crew_id} is due now (due {} seconds ago) and has not completed.",
                now - due_at
            ),
            format!(
                "Have the accountability officer complete the PAR check with the crew, then run complete --crew {crew_id}."
            ),
        )
    } else {
        let minutes = (now - due_at) / 60;
        (
            format!("par-unaccounted-{crew_id}-{due_at}"),
            format!(
                "No completed PAR for crew {crew_id} and the grace window has passed ({minutes} minutes overdue). Treat as a mayday-standard check failure."
            ),
            "Escalate to the incident commander now. Do not let this clock clear itself; only a confirmed PAR check or an exit clears it.".to_string(),
        )
    };
    AlertEvent {
        kind: kind.to_string(),
        severity: severity.to_string(),
        urgency: urgency.to_string(),
        alert_id,
        crew: crew_id.to_string(),
        due_at,
        entered_at: record.entered_at,
        ts: now,
        explanation,
        suggested_fix: fix,
        location: record.location.clone(),
    }
}

/// One clock cycle. Returns (events, new_state). Pure: input never mutated.
pub fn tick(
    state: &ParState,
    now: i64,
    interval_seconds: i64,
    grace_seconds: i64,
) -> (Vec<AlertEvent>, ParState) {
    let mut out = state.clone();
    let mut ledger: BTreeSet<String> = out.ledger.iter().cloned().collect();
    let mut events = vec![];
    // BTreeMap iteration = deterministic crew order (Python dict order differs;
    // behavior parity is per-crew, order-independent).
    for (crew_id, record) in out.roster.clone().iter() {
        let base = record.last_par_at.unwrap_or(record.entered_at);
        let due_at = base + interval_seconds;
        if now < due_at {
            continue;
        }
        let prefix = format!("par:{crew_id}:");
        let key_due = format!("{prefix}due:{due_at}");
        if !ledger.contains(&key_due) {
            events.push(make_event(
                KIND_PAR_CHECK_DUE,
                SEVERITY_WARNING,
                "urgent",
                crew_id,
                due_at,
                now,
                record,
            ));
            ledger.insert(key_due);
        }
        if now >= due_at + grace_seconds {
            let key_over = format!("{prefix}over:{due_at}");
            if !ledger.contains(&key_over) {
                events.push(make_event(
                    KIND_CREW_UNACCOUNTED,
                    SEVERITY_CRITICAL,
                    "life-safety",
                    crew_id,
                    due_at,
                    now,
                    record,
                ));
                ledger.insert(key_over);
            }
        }
    }
    out.ledger = ledger.into_iter().collect();
    (events, out)
}

/// Frozen FND-020 line: `ALERT:<id> <severity> <kind>`.
pub fn render_alert(event: &AlertEvent) -> String {
    format!("ALERT:{} {} {}", event.alert_id, event.severity, event.kind)
}

#[allow(dead_code)]
fn _assert_no_mutation_hint(_v: &serde_json::Value) -> bool {
    is_int(_v)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn entered(crew: &str, at: i64, loc: Option<&str>) -> ParState {
        enter_crew(&new_state(), crew, at, loc).unwrap()
    }

    #[test]
    fn enter_twice_refused_and_id_rules() {
        let s = entered("crew-2", 1000, None);
        assert!(enter_crew(&s, "crew-2", 1100, None).is_err());
        assert!(enter_crew(&new_state(), "crew 2", 1, None).is_err());
        assert!(enter_crew(&new_state(), "", 1, None).is_err());
    }

    #[test]
    fn quiet_before_interval_and_once_per_cycle() {
        let s = entered("crew-2", 1000, None);
        assert!(tick(&s, 1599, 600, 120).0.is_empty());
        let (ev, out) = tick(&s, 1600, 600, 120);
        assert_eq!(ev.iter().map(|e| e.kind.as_str()).collect::<Vec<_>>(), [KIND_PAR_CHECK_DUE]);
        assert!(tick(&out, 1610, 600, 120).0.is_empty());
    }

    #[test]
    fn grace_escalates_and_dedupes() {
        let s = entered("crew-2", 1000, None);
        let (ev, out) = tick(&s, 1720, 600, 120);
        let kinds: Vec<&str> = ev.iter().map(|e| e.kind.as_str()).collect();
        assert_eq!(kinds, [KIND_PAR_CHECK_DUE, KIND_CREW_UNACCOUNTED]);
        let over = ev.iter().find(|e| e.kind == KIND_CREW_UNACCOUNTED).unwrap();
        assert_eq!(over.severity, "critical");
        assert_eq!(over.urgency, "life-safety");
        assert!(tick(&out, 1900, 600, 120).0.is_empty());
    }

    #[test]
    fn complete_resets_and_exit_silences() {
        let s = entered("crew-2", 1000, None);
        let (_, out) = tick(&s, 1800, 600, 120);
        let done = complete_par(&out, "crew-2", 1800).unwrap();
        assert!(tick(&done, 1801, 600, 120).0.is_empty());
        let (ev, _) = tick(&done, 2400, 600, 120);
        assert_eq!(ev[0].due_at, 2400);
        let exited = exit_crew(&out, "crew-2", 2000).unwrap();
        assert!(tick(&exited, 5000, 600, 120).0.is_empty());
    }

    #[test]
    fn alert_line_shape() {
        let s = entered("crew-2", 1000, None);
        let (ev, _) = tick(&s, 1800, 600, 120);
        let over = ev.iter().find(|e| e.kind == KIND_CREW_UNACCOUNTED).unwrap();
        assert_eq!(render_alert(over), "ALERT:par-unaccounted-crew-2-1600 critical crew-unaccounted");
        for e in &ev {
            assert!(!e.alert_id.contains(' '));
        }
    }

    #[test]
    fn inputs_never_mutated_and_crews_independent() {
        let s = entered("crew-1", 1000, None);
        let before = format!("{:?}", s);
        let _ = tick(&s, 10000, 600, 120);
        assert_eq!(format!("{:?}", s), before);
        let s = enter_crew(&s, "crew-2", 1200, None).unwrap();
        let (ev, _) = tick(&s, 1600, 600, 120);
        assert_eq!(ev.len(), 1);
        assert_eq!(ev[0].crew, "crew-1");
    }
}
