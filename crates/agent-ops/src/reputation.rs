//! Agent QA and reputation: measured trust, not vibes.
//!
//! Before an agent is trusted with important work the OS scores it:
//! historical success rate, tool reliability, error and recovery
//! rates, instruction-following consistency, and security violations.
//! Scores map to trust tiers; low tiers cannot receive sensitive
//! delegations (pairs with authority.rs — the score is the gate).

/// One finished task, as filed.
#[derive(Debug, Clone)]
pub struct TaskRecord {
    /// Task succeeded without supervisor rescue.
    pub success: bool,
    /// Needed recovery (restore/retry) to finish.
    pub recovered: bool,
    /// Followed the instruction as written.
    pub followed_instruction: bool,
    /// Caused a security violation (prompt-inject relay, exfil, ...).
    pub violation: bool,
    /// Tool calls made / failed.
    pub tool_calls: u32,
    pub tool_failures: u32,
}

/// Aggregate score 0..=100.
#[derive(Debug)]
pub struct Score {
    pub value: u8,
    pub tasks: usize,
    pub notes: Vec<String>,
}

/// Trust tiers gate delegation of sensitive capabilities.
#[derive(Debug, PartialEq)]
pub enum Tier {
    /// New or thin history: supervised only.
    Probation,
    /// Solid record: standard work.
    Trusted,
    /// Long clean record: sensitive work (money, secrets, prod).
    Vetted,
}

pub fn score(records: &[TaskRecord]) -> Score {
    let mut notes = Vec::new();
    if records.is_empty() {
        notes.push("no history".into());
        return Score { value: 0, tasks: 0, notes };
    }
    let n = records.len() as f64;
    let succ = records.iter().filter(|r| r.success).count() as f64 / n;
    let rec = records.iter().filter(|r| r.recovered).count() as f64 / n;
    let foll = records.iter().filter(|r| r.followed_instruction).count() as f64 / n;
    let viol = records.iter().filter(|r| r.violation).count();
    let calls: u32 = records.iter().map(|r| r.tool_calls).sum();
    let fails: u32 = records.iter().map(|r| r.tool_failures).sum();
    let tool_rel = if calls == 0 { 1.0 } else { 1.0 - (fails as f64 / calls as f64) };
    // Weights: success .4, recovery .1, instruction-following .2, tool
    // reliability .2, violations −25 each (floor 0).
    let mut v = 100.0 * (0.4 * succ + 0.1 * rec.max(0.5) + 0.2 * foll + 0.2 * tool_rel) - 25.0 * viol as f64;
    v = v.clamp(0.0, 100.0);
    if viol > 0 {
        notes.push(format!("{} violation(s)", viol));
    }
    if succ < 0.5 {
        notes.push("success under half".into());
    }
    Score { value: v.round() as u8, tasks: records.len(), notes }
}

pub fn tier(s: &Score) -> Tier {
    if s.tasks < 3 {
        return Tier::Probation;
    }
    if s.value >= 85 {
        Tier::Vetted
    } else if s.value >= 60 {
        Tier::Trusted
    } else {
        Tier::Probation
    }
}

/// Sensitive capabilities require Vetted; standard ones Trusted+.
/// Returns the refusal reason or None when allowed.
pub fn gate_delegation(t: &Tier, sensitive: bool) -> Option<String> {
    match (t, sensitive) {
        (Tier::Vetted, _) => None,
        (Tier::Trusted, false) => None,
        (Tier::Trusted, true) => Some("sensitive work needs Vetted tier".into()),
        (Tier::Probation, _) => Some("probation agents work supervised only".into()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn good() -> TaskRecord {
        TaskRecord { success: true, recovered: false, followed_instruction: true, violation: false, tool_calls: 10, tool_failures: 0 }
    }

    #[test]
    fn new_agent_is_probation() {
        let s = score(&[]);
        assert_eq!(s.value, 0);
        assert_eq!(tier(&s), Tier::Probation);
    }

    #[test]
    fn clean_record_vets() {
        let rs = vec![good(), good(), good(), good(), good()];
        let s = score(&rs);
        assert!(s.value >= 85, "got {}", s.value);
        assert_eq!(tier(&s), Tier::Vetted);
        assert_eq!(gate_delegation(&Tier::Vetted, true), None);
    }

    #[test]
    fn violation_tanks_score() {
        let mut rs = vec![good(), good(), good()];
        rs.push(TaskRecord { violation: true, ..good() });
        let s = score(&rs);
        assert!(s.value < 85, "got {}", s.value);
        assert!(s.notes.iter().any(|n| n.contains("violation")));
    }

    #[test]
    fn trusted_cannot_take_sensitive() {
        let mut rs = vec![good(), good(), good()];
        rs.push(TaskRecord { success: false, recovered: true, ..good() });
        let s = score(&rs);
        let t = tier(&s);
        assert!(gate_delegation(&t, true).is_some());
    }

    #[test]
    fn thin_history_stays_probation() {
        let s = score(&[good(), good()]);
        assert_eq!(tier(&s), Tier::Probation);
    }
}
