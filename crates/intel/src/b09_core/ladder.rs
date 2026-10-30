//! Port of `os/intel/ladder.py` — the self-repair ladder (OS-095).
//!
//! Pure rung selection from snapshot facts: present worker -> nudge;
//! registered-but-absent worker -> restart; claimer outside the caps
//! registry -> reassign (baton preserves title/progress/files). Malformed
//! stalls (no nick/job) or missing job records yield no action, never crash.
//! The ladder never pushes, never mutates jobs/claims.

pub const NUDGE: &str = "nudge";
pub const RESTART: &str = "restart";
pub const REASSIGN: &str = "reassign";
pub const RUNGS: &[&str] = &[NUDGE, RESTART, REASSIGN];

#[derive(Debug, Clone, PartialEq)]
pub struct Stall {
    pub nick: Option<String>,
    pub job: Option<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Baton {
    pub job_id: String,
    pub title: String,
    pub progress: String,
    pub files: Vec<String>,
    pub from_nick: String,
}

#[derive(Debug, Clone, Default)]
pub struct Snapshot {
    /// registered worker identities (caps registry)
    pub registered: Vec<String>,
    /// present workers (presence)
    pub present: Vec<String>,
    /// job_id -> (title, progress, files)
    pub jobs: Vec<(String, String, String, Vec<String>)>,
}

fn job_by_id<'a>(snap: &'a Snapshot, id: &str) -> Option<&'a (String, String, String, Vec<String>)> {
    snap.jobs.iter().find(|(jid, _, _, _)| jid == id)
}

/// Classify a stall to a rung, or `None` for no action.
pub fn classify(snap: &Snapshot, stall: &Stall) -> Option<&'static str> {
    let nick = stall.nick.clone().filter(|s| !s.is_empty())?;
    let job_id = stall.job.clone().filter(|s| !s.is_empty())?;
    job_by_id(snap, &job_id)?;
    if !snap.registered.contains(&nick) {
        return Some(REASSIGN);
    }
    if snap.present.contains(&nick) {
        Some(NUDGE)
    } else {
        Some(RESTART)
    }
}

pub fn baton_for(snap: &Snapshot, stall: &Stall) -> Option<Baton> {
    let job_id = stall.job.clone()?;
    let (_, title, progress, files) = job_by_id(snap, &job_id)?.clone();
    Some(Baton {
        job_id,
        title,
        progress,
        files,
        from_nick: stall.nick.clone().unwrap_or_default(),
    })
}

#[derive(Debug, Clone, PartialEq)]
pub struct LadderAction {
    pub rung: String,
    pub nick: String,
    pub job: String,
    pub baton: Option<Baton>,
}

pub fn ladder_action(snap: &Snapshot, stall: &Stall) -> Option<LadderAction> {
    let rung = classify(snap, stall)?;
    Some(LadderAction {
        rung: rung.to_string(),
        nick: stall.nick.clone().unwrap_or_default(),
        job: stall.job.clone().unwrap_or_default(),
        baton: if rung == REASSIGN { baton_for(snap, stall) } else { None },
    })
}

pub fn ladder_tick(snap: &Snapshot, stalls: &[Stall]) -> Vec<LadderAction> {
    stalls.iter().filter_map(|s| ladder_action(snap, s)).collect()
}

pub fn ladder_brief_lines(actions: &[LadderAction]) -> Vec<String> {
    actions
        .iter()
        .map(|a| format!("Ladder {}: {} on job {} ({})", a.rung, a.nick, a.job, a.nick))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn snap() -> Snapshot {
        Snapshot {
            registered: vec!["milo".to_string(), "hana".to_string()],
            present: vec!["milo".to_string()],
            jobs: vec![("j1".to_string(), "t".to_string(), "p".to_string(), vec!["f".to_string()])],
        }
    }

    #[test]
    fn present_worker_nudges() {
        let s = Stall { nick: Some("milo".to_string()), job: Some("j1".to_string()) };
        assert_eq!(classify(&snap(), &s), Some(NUDGE));
    }

    #[test]
    fn absent_registered_worker_restarts() {
        let s = Stall { nick: Some("hana".to_string()), job: Some("j1".to_string()) };
        assert_eq!(classify(&snap(), &s), Some(RESTART));
    }

    #[test]
    fn walk_on_reassigns_with_baton() {
        let s = Stall { nick: Some("stranger".to_string()), job: Some("j1".to_string()) };
        assert_eq!(classify(&snap(), &s), Some(REASSIGN));
        let a = ladder_action(&snap(), &s).unwrap();
        assert!(a.baton.is_some());
    }

    #[test]
    fn malformed_stall_yields_nothing() {
        let s = Stall { nick: None, job: Some("j1".to_string()) };
        assert_eq!(classify(&snap(), &s), None);
        let s2 = Stall { nick: Some("milo".to_string()), job: Some("missing".to_string()) };
        assert_eq!(classify(&snap(), &s2), None);
    }
}
