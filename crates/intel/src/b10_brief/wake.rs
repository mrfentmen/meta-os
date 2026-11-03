//! Port of `os/intel/wake.py` — sleeping-Muse wake bundles.
//!
//! A Muse that is sleeping (absent presence + no recent progress) gets at
//! most one wake bundle per dedupe key; the bundle quotes the deposited
//! spec text verbatim and never invents acceptance criteria.

pub fn is_sleeping_muse(present: bool, idle_minutes: i64) -> bool {
    !present && idle_minutes >= 15
}

pub fn should_wake(sleeping: bool, already_sent: bool, has_spec: bool) -> bool {
    sleeping && !already_sent && has_spec
}

/// The journal dedupe key for one wake, in wake.py order: job id
/// first, agent nick second (`wake:{job}:{nick}`).
pub fn dedupe_key(job: &str, nick: &str) -> String {
    format!("wake:{job}:{nick}")
}

pub fn compose_bundle(nick: &str, job: &str, spec_text: &str, acceptance: &[String]) -> String {
    let acc = if acceptance.is_empty() {
        "(no acceptance recorded)".to_string()
    } else {
        acceptance.join("; ")
    };
    format!("WAKE {nick} re: {job}\n{spec_text}\nacceptance: {acc}")
}

/// A posted job as seen by the wake tick: the job id, who it is
/// addressed to, and the bundle material for that job.
#[derive(Debug, Clone, PartialEq)]
pub struct WakeJob {
    pub id: String,
    pub addressed_to: String,
    pub spec_text: String,
    pub acceptance: Vec<String>,
}

/// An agent record as seen by the wake tick.
#[derive(Debug, Clone, PartialEq)]
pub struct WakeAgent {
    pub nick: String,
    pub machine: String,
    pub sleeping: bool,
}

/// One journal wake record (wake.py `wake_tick` record shape).
#[derive(Debug, Clone, PartialEq)]
pub struct WakeRecord {
    pub kind: String,
    pub dedupe_key: String,
    pub job: String,
    pub agent: String,
    pub machine: String,
    pub bundle: String,
    pub created_at: i64,
}

/// One wake tick: one new wake record per sleeping agent addressed by
/// a posted job, unless that pair already has a wake record in the
/// journal (keys passed in) or earlier in this same tick. Returns the
/// new records only; the caller appends them. Inputs are never
/// mutated. A job with no id, an agent with no nick, a job addressed
/// to someone else, or a non-sleeping agent yields no record.
pub fn wake_tick(
    jobs: &[WakeJob],
    agents: &[WakeAgent],
    journal_keys: &[String],
    now: i64,
) -> Vec<WakeRecord> {
    let mut seen: Vec<String> = journal_keys.to_vec();
    let mut new_records = Vec::new();
    for job in jobs {
        if job.id.trim().is_empty() {
            continue;
        }
        for agent in agents {
            if !agent.sleeping || agent.nick.trim().is_empty() {
                continue;
            }
            if job.addressed_to != agent.nick {
                continue;
            }
            let key = dedupe_key(&job.id, &agent.nick);
            if seen.contains(&key) {
                continue;
            }
            seen.push(key.clone());
            new_records.push(WakeRecord {
                kind: "wake".to_string(),
                dedupe_key: key,
                job: job.id.clone(),
                agent: agent.nick.clone(),
                machine: agent.machine.clone(),
                bundle: compose_bundle(
                    &agent.nick,
                    &job.id,
                    &job.spec_text,
                    &job.acceptance,
                ),
                created_at: now,
            });
        }
    }
    new_records
}

/// One brief line per wake record, in record order. Other record
/// kinds render nothing, so a mixed journal briefs only its wakes.
/// Empty fields render as "?" (wake.py `brief_lines`).
pub fn brief_lines(records: &[WakeRecord]) -> Vec<String> {
    records
        .iter()
        .filter(|r| r.kind == "wake")
        .map(|r| {
            let agent = if r.agent.trim().is_empty() { "?" } else { r.agent.as_str() };
            let job = if r.job.trim().is_empty() { "?" } else { r.job.as_str() };
            let machine = if r.machine.trim().is_empty() { "?" } else { r.machine.as_str() };
            format!("Wake: {agent} woken for job {job} on {machine}")
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn wake_gates() {
        assert!(is_sleeping_muse(false, 20));
        assert!(!is_sleeping_muse(true, 99));
        assert!(should_wake(true, false, true));
        assert!(!should_wake(true, true, true));
    }
    #[test]
    fn bundle_quotes_spec() {
        assert!(compose_bundle("m", "j", "spec words", &[]).contains("spec words"));
    }

    fn tick_job() -> WakeJob {
        WakeJob { id: "j1".into(), addressed_to: "hana".into(), spec_text: "spec words".into(), acceptance: vec!["check".into()] }
    }
    fn tick_agent() -> WakeAgent {
        WakeAgent { nick: "hana".into(), machine: "mac".into(), sleeping: true }
    }

    #[test]
    fn wake_tick_one_record_per_pair_and_dedupes() {
        let recs = wake_tick(&[tick_job()], &[tick_agent()], &[], 42);
        assert_eq!(recs.len(), 1);
        // wake.py order: job id first, agent nick second.
        assert_eq!(recs[0].dedupe_key, "wake:j1:hana");
        assert_eq!(dedupe_key("j1", "hana"), "wake:j1:hana");
        assert_eq!(recs[0].created_at, 42);
        assert!(recs[0].bundle.contains("spec words"));
        // Journal dedupe: same pair again journals nothing new.
        let keys = vec![recs[0].dedupe_key.clone()];
        assert!(wake_tick(&[tick_job()], &[tick_agent()], &keys, 43).is_empty());
        // Same tick, duplicate job/agent pair: second occurrence skipped.
        let recs2 = wake_tick(&[tick_job(), tick_job()], &[tick_agent()], &[], 44);
        assert_eq!(recs2.len(), 1);
    }

    #[test]
    fn wake_tick_skips_wrong_addressee_awake_and_anonymous() {
        let other = WakeAgent { nick: "rowan".into(), ..tick_agent() };
        assert!(wake_tick(&[tick_job()], &[other], &[], 0).is_empty());
        let awake = WakeAgent { sleeping: false, ..tick_agent() };
        assert!(wake_tick(&[tick_job()], &[awake], &[], 0).is_empty());
        let anon = WakeJob { id: String::new(), ..tick_job() };
        assert!(wake_tick(&[anon], &[tick_agent()], &[], 0).is_empty());
        let nickless = WakeAgent { nick: String::new(), ..tick_agent() };
        assert!(wake_tick(&[tick_job()], &[nickless], &[], 0).is_empty());
    }

    #[test]
    fn brief_lines_only_wakes_in_order() {
        let recs = wake_tick(&[tick_job()], &[tick_agent()], &[], 0);
        let mut mixed = recs.clone();
        mixed.push(WakeRecord { kind: "claim".into(), dedupe_key: "x".into(), job: "j9".into(), agent: "rowan".into(), machine: "mac".into(), bundle: String::new(), created_at: 0 });
        assert_eq!(brief_lines(&mixed), vec!["Wake: hana woken for job j1 on mac".to_string()]);
        let blank = WakeRecord { kind: "wake".into(), dedupe_key: "y".into(), job: "j2".into(), agent: "hana".into(), machine: String::new(), bundle: String::new(), created_at: 0 };
        assert_eq!(brief_lines(&[blank]), vec!["Wake: hana woken for job j2 on ?".to_string()]);
    }
}
