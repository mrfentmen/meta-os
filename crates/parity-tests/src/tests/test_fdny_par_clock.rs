//! T035 [B31] port of `os/tests/test_fdny_par_clock.py` (same name roots).
//!
//! PAR clock integrated against the real ported module
//! (`os_misc::b27::par_clock`, landed via T015) — not a reimplementation.
//! Interval 600s / grace 120s (the frozen `DEFAULT_*` constants).
//!
//! Blocked (needs the `par_clock` file CLI `main`, absent from the Rust
//! lib port; state JSON needs `Serialize`, also absent — named, not dropped):
//! - CLI show + full lifecycle on disk
//! - CLI bad crew exits 2
//! - CLI state survives reopen

use os_misc::b27::par_clock as pc;

pub const CASES: &[&str] = &[
    "enter starts interval from entry",
    "enter twice is refused",
    "crew id rules",
    "exit removes crew and cleans ledger",
    "exit unknown crew is refused",
    "quiet before interval",
    "due fires once per cycle",
    "grace escalates to life safety",
    "completion resets cycle and clears alarm",
    "exit silences overdue",
    "location present on life safety event",
    "inputs never mutated",
    "second crew counts independently",
    "line matches fnd020 shape",
    "ids carry no spaces or explanations",
];
pub const EXCLUSION_BLOCKED: &[&str] = &[
    "cli show and full lifecycle on disk (needs par_clock file CLI main, not in Rust lib port)",
    "cli bad crew exits 2 (needs par_clock file CLI main, not in Rust lib port)",
    "cli state survives reopen (needs par_clock file CLI main + JSON state, not in Rust lib port)",
];

const I: i64 = pc::DEFAULT_INTERVAL_SECONDS;
const G: i64 = pc::DEFAULT_GRACE_SECONDS;

fn entered(crew: &str, at: i64, location: Option<&str>) -> pc::ParState {
    pc::enter_crew(&pc::new_state(), crew, at, location).unwrap()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_enter_starts_interval_from_entry() {
        let (state, _) = (entered("crew-2", 1000, None), ());
        let rec = &state.roster["crew-2"];
        assert_eq!(rec.entered_at, 1000);
        assert_eq!(rec.last_par_at, None);
    }

    #[test]
    fn test_enter_twice_is_refused() {
        let state = entered("crew-2", 1000, None);
        let err = pc::enter_crew(&state, "crew-2", 1100, None).unwrap_err();
        assert!(err.contains("already inside"), "{err}");
    }

    #[test]
    fn test_crew_id_rules() {
        let err = pc::enter_crew(&pc::new_state(), "crew 2", 1, None).unwrap_err();
        assert!(err.contains("whitespace"), "{err}");
        let err = pc::enter_crew(&pc::new_state(), "", 1, None).unwrap_err();
        assert!(err.contains("empty"), "{err}");
    }

    #[test]
    fn test_exit_removes_crew_and_cleans_ledger() {
        let state = entered("crew-2", 1000, None);
        let (_, st) = pc::tick(&state, 1000 + 700, I, G);
        assert!(!st.timeline.is_empty());
        let done = pc::exit_crew(&st, "crew-2", 1700).unwrap();
        assert!(!done.roster.contains_key("crew-2"));
        assert!(done.timeline.iter().any(|t| t.kind == pc::TL_EXIT));
        let (events2, _) = pc::tick(&done, 10000, I, G);
        assert_eq!(events2, vec![]);
    }

    #[test]
    fn test_exit_unknown_crew_is_refused() {
        let err = pc::exit_crew(&pc::new_state(), "ghost", 1).unwrap_err();
        assert!(err.contains("not inside"), "{err}");
    }

    #[test]
    fn test_quiet_before_interval() {
        let state = entered("crew-2", 1000, None);
        let (events, _) = pc::tick(&state, 1000 + 599, I, G);
        assert_eq!(events, vec![]);
    }

    #[test]
    fn test_due_fires_once_per_cycle() {
        let state = entered("crew-2", 1000, None);
        let (events, out) = pc::tick(&state, 1000 + 600, I, G);
        let kinds: Vec<_> = events.iter().map(|e| e.kind.as_str()).collect();
        assert_eq!(kinds, [pc::KIND_PAR_CHECK_DUE]);
        let (events2, _) = pc::tick(&out, 1000 + 610, I, G);
        assert_eq!(events2, vec![]);
    }

    #[test]
    fn test_grace_escalates_to_life_safety() {
        let state = entered("crew-2", 1000, None);
        let (events, out) = pc::tick(&state, 1000 + 600 + 120, I, G);
        let kinds: Vec<_> = events.iter().map(|e| e.kind.as_str()).collect();
        assert_eq!(kinds, [pc::KIND_PAR_CHECK_DUE, pc::KIND_CREW_UNACCOUNTED]);
        let over = events.iter().find(|e| e.kind == pc::KIND_CREW_UNACCOUNTED).unwrap();
        assert_eq!(over.severity, "critical");
        assert_eq!(over.urgency, "life-safety");
        let (events2, _) = pc::tick(&out, 1000 + 900, I, G);
        assert_eq!(events2, vec![]);
    }

    #[test]
    fn test_completion_resets_cycle_and_clears_alarm() {
        let state = entered("crew-2", 1000, None);
        let (_, out) = pc::tick(&state, 1000 + 800, I, G);
        let done = pc::complete_par(&out, "crew-2", 1800).unwrap();
        let (events2, out2) = pc::tick(&done, 1801, I, G);
        assert_eq!(events2, vec![]);
        let (events3, _) = pc::tick(&out2, 1800 + 600, I, G);
        let kinds: Vec<_> = events3.iter().map(|e| e.kind.as_str()).collect();
        assert_eq!(kinds, [pc::KIND_PAR_CHECK_DUE]);
        assert_eq!(events3[0].due_at, 1800 + 600);
    }

    #[test]
    fn test_exit_silences_overdue() {
        let state = entered("crew-2", 1000, None);
        let (_, out) = pc::tick(&state, 1000 + 800, I, G);
        let done = pc::exit_crew(&out, "crew-2", 2000).unwrap();
        let (events, _) = pc::tick(&done, 5000, I, G);
        assert_eq!(events, vec![]);
    }

    #[test]
    fn test_location_present_on_life_safety_event() {
        let state = entered("crew-2", 1000, Some("division 2 stairwell"));
        let (events, _) = pc::tick(&state, 1000 + 800, I, G);
        let over = events.iter().find(|e| e.kind == pc::KIND_CREW_UNACCOUNTED).unwrap();
        assert_eq!(over.location.as_deref(), Some("division 2 stairwell"));
    }

    #[test]
    fn test_inputs_never_mutated() {
        let state = entered("crew-2", 1000, None);
        let before = format!("{state:?}");
        pc::tick(&state, 10000, I, G);
        assert_eq!(format!("{state:?}"), before);
    }

    #[test]
    fn test_second_crew_counts_independently() {
        let state = entered("crew-1", 1000, None);
        let state = pc::enter_crew(&state, "crew-2", 1200, None).unwrap();
        let (events, _) = pc::tick(&state, 1600, I, G);
        assert_eq!(events.len(), 1);
        assert_eq!(events[0].crew, "crew-1");
    }

    #[test]
    fn test_line_matches_fnd020_shape() {
        let state = entered("crew-2", 1000, None);
        let (events, _) = pc::tick(&state, 1000 + 800, I, G);
        let over = events.iter().find(|e| e.kind == pc::KIND_CREW_UNACCOUNTED).unwrap();
        let line = pc::render_alert(over);
        assert_eq!(line, "ALERT:par-unaccounted-crew-2-1600 critical crew-unaccounted");
        assert!(!line.contains("  "));
        assert!(!line.contains('\n'));
    }

    #[test]
    fn test_ids_carry_no_spaces_or_explanations() {
        let state = entered("crew-2", 1000, None);
        let (events, _) = pc::tick(&state, 1000 + 800, I, G);
        for e in &events {
            assert!(!e.alert_id.contains(' '));
            let line = pc::render_alert(e);
            assert!(line.starts_with("ALERT:"));
            assert_eq!(line.split_whitespace().count(), 3);
        }
    }
}
