//! Port of `os/intel/timer_sweep.py` — OS-121 timer fallback sweep.
//!
//! Dormant while the watchman is healthy (zero claims, zero dupes);
//! claims when dead within one interval of posting; holds on unknown
//! (never guesses); open-only + roster-addressed + ledger-deduped;
//! cadence-gated (first tick always runs); malformed never claims or
//! crashes; inputs never mutated. Decision only: never spawns, rings,
//! moves claims, or posts.

#[derive(Debug, Clone, PartialEq)]
pub struct SweepJob {
    pub id: Option<String>,
    pub status: String,
    pub posted_at: Option<i64>,
    pub addressed_to: Option<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct SweepTick {
    pub claimed: Vec<String>,
    pub skipped: Vec<String>,
    pub ran: bool,
    pub ledger_after: Vec<String>,
}

pub fn default_interval_seconds() -> i64 {
    300
}

/// One sweep tick. `watchman_alive`: Some(true) healthy, Some(false)
/// dead, None unknown.
pub fn sweep_cycle(
    jobs: &[SweepJob],
    roster: &[String],
    ledger: &[String],
    last_sweep_at: Option<i64>,
    now: i64,
    interval: i64,
    watchman_alive: Option<bool>,
) -> SweepTick {
    let blank = |ran: bool| SweepTick { claimed: vec![], skipped: vec![], ran, ledger_after: ledger.to_vec() };
    if watchman_alive != Some(false) {
        return blank(true); // healthy or unknown: claim nothing
    }
    if let Some(last) = last_sweep_at {
        if now < last + interval {
            return blank(false); // cadence: not yet
        }
    }
    let mut claimed = Vec::new();
    let mut skipped = Vec::new();
    let mut after = ledger.to_vec();
    for job in jobs {
        let Some(id) = job.id.clone().filter(|s| !s.is_empty()) else {
            skipped.push("(malformed)".to_string());
            continue;
        };
        if job.status != "open" {
            continue; // claimed/done: lease sweep owns those
        }
        let posted_ok = job.posted_at.is_some_and(|t| t <= now);
        if !posted_ok {
            skipped.push(id);
            continue;
        }
        match &job.addressed_to {
            Some(who) if roster.contains(who) => (),
            _ => {
                skipped.push(id);
                continue;
            }
        }
        if after.contains(&id) {
            continue; // already swept: zero duplicates
        }
        claimed.push(id.clone());
        after.push(id);
    }
    SweepTick { claimed, skipped, ran: true, ledger_after: after }
}

pub fn sweep_brief_lines(tick: &SweepTick) -> Vec<String> {
    vec![format!("sweep: {} claimed, {} skipped", tick.claimed.len(), tick.skipped.len())]
}

#[cfg(test)]
mod tests {
    use super::*;

    fn job(id: &str, status: &str, posted: i64, to: Option<&str>) -> SweepJob {
        SweepJob { id: Some(id.into()), status: status.into(), posted_at: Some(posted), addressed_to: to.map(str::to_string) }
    }

    #[test]
    fn healthy_claims_nothing() {
        let t = sweep_cycle(&[job("a", "open", 1, Some("m"))], &["m".into()], &[], None, 500, 300, Some(true));
        assert!(t.claimed.is_empty() && t.ran);
    }
    #[test]
    fn unknown_holds() {
        let t = sweep_cycle(&[job("a", "open", 1, Some("m"))], &["m".into()], &[], None, 500, 300, None);
        assert!(t.claimed.is_empty());
    }
    #[test]
    fn dead_claims_within_interval() {
        let t = sweep_cycle(&[job("a", "open", 400, Some("m"))], &["m".into()], &[], None, 500, 300, Some(false));
        assert_eq!(t.claimed, vec!["a".to_string()]);
    }
    #[test]
    fn ledger_dedupes() {
        let t = sweep_cycle(&[job("a", "open", 1, Some("m"))], &["m".into()], &["a".into()], None, 500, 300, Some(false));
        assert!(t.claimed.is_empty());
    }
    #[test]
    fn wrong_machine_skipped_not_dropped() {
        let t = sweep_cycle(&[job("a", "open", 1, Some("other"))], &["m".into()], &[], None, 500, 300, Some(false));
        assert!(t.claimed.is_empty() && t.skipped == vec!["a".to_string()]);
    }
}
