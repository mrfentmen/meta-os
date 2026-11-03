//! Proof-of-work execution throttler.
//!
//! An agent that runs the same failing command in a loop burns money
//! and compute. This gate counts recent identical failures and
//! force-slows the loop: escalating mandatory waits plus a required
//! written self-reflection before the next attempt is allowed.
//!
//! Pure logic over caller-supplied records — no clock reads inside the
//! decision (callers pass `now_secs`), so every rule is unit-testable.

/// One executed attempt, as filed by the caller.
#[derive(Debug, Clone)]
pub struct Attempt {
    /// Stable key for "the same action", e.g. argv joined.
    pub key: String,
    pub exit_ok: bool,
    pub at_secs: u64,
}

/// Throttler state. Callers persist it; nothing here touches the fs.
#[derive(Debug, Default)]
pub struct Throttle {
    pub attempts: Vec<Attempt>,
    /// Seconds a reflection note stays valid once filed.
    pub reflection_ttl_secs: u64,
    /// (attempts, wait_secs) escalation ladder.
    pub ladder: Vec<(usize, u64)>,
}

impl Throttle {
    pub fn new() -> Self {
        Throttle {
            attempts: Vec::new(),
            reflection_ttl_secs: 3600,
            ladder: vec![(3, 60), (5, 300), (8, 900), (12, 3600)],
        }
    }

    pub fn file(&mut self, a: Attempt) {
        self.attempts.push(a);
    }

    /// Consecutive failures for `key` ending at the latest record.
    pub fn streak(&self, key: &str) -> usize {
        let mut n = 0;
        for a in self.attempts.iter().rev() {
            if a.key != key {
                continue;
            }
            if a.exit_ok {
                break;
            }
            n += 1;
        }
        n
    }

    /// Mandatory wait before `key` may run again at `now_secs`.
    pub fn wait_secs(&self, key: &str) -> u64 {
        let s = self.streak(key);
        let mut wait = 0;
        for (need, secs) in &self.ladder {
            if s >= *need {
                wait = *secs;
            }
        }
        wait
    }

    /// Whether `key` needs a fresh written reflection first: any streak
    /// at or past the second ladder rung with no valid reflection filed.
    pub fn needs_reflection(&self, key: &str, reflections: &[Reflection], now_secs: u64) -> bool {
        let s = self.streak(key);
        if self.ladder.len() < 2 || s < self.ladder[1].0 {
            return false;
        }
        !reflections.iter().any(|r| {
            r.key == key && r.at_secs + self.reflection_ttl_secs > now_secs && !r.note.trim().is_empty()
        })
    }
}

/// A written self-reflection note unblocking the next attempt.
#[derive(Debug, Clone)]
pub struct Reflection {
    pub key: String,
    pub note: String,
    pub at_secs: u64,
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fails(key: &str, n: usize, from: u64) -> Throttle {
        let mut t = Throttle::new();
        for i in 0..n {
            t.file(Attempt { key: key.into(), exit_ok: false, at_secs: from + i as u64 });
        }
        t
    }

    #[test]
    fn calm_loop_has_no_wait() {
        let mut t = Throttle::new();
        t.file(Attempt { key: "a".into(), exit_ok: true, at_secs: 1 });
        t.file(Attempt { key: "a".into(), exit_ok: false, at_secs: 2 });
        assert_eq!(t.wait_secs("a"), 0);
        assert!(!t.needs_reflection("a", &[], 3));
    }

    #[test]
    fn repeated_failures_escalate() {
        let t = fails("k", 3, 100);
        assert_eq!(t.streak("k"), 3);
        assert_eq!(t.wait_secs("k"), 60);
        let t = fails("k", 6, 100);
        assert_eq!(t.wait_secs("k"), 300);
        let t = fails("k", 12, 100);
        assert_eq!(t.wait_secs("k"), 3600);
    }

    #[test]
    fn success_resets_the_streak() {
        let mut t = fails("k", 5, 100);
        t.file(Attempt { key: "k".into(), exit_ok: true, at_secs: 200 });
        assert_eq!(t.streak("k"), 0);
        assert_eq!(t.wait_secs("k"), 0);
    }

    #[test]
    fn reflection_gate_opens_with_a_note() {
        let t = fails("k", 5, 100);
        assert!(t.needs_reflection("k", &[], 200));
        let r = vec![Reflection { key: "k".into(), note: "different flag next".into(), at_secs: 150 }];
        assert!(!t.needs_reflection("k", &r, 200));
        // Expired note does not count.
        assert!(t.needs_reflection("k", &r, 150 + 3600 + 1));
        // Empty note does not count.
        let blank = vec![Reflection { key: "k".into(), note: "  ".into(), at_secs: 150 }];
        assert!(t.needs_reflection("k", &blank, 200));
    }

    #[test]
    fn other_keys_do_not_interfere() {
        let mut t = fails("k", 5, 100);
        t.file(Attempt { key: "other".into(), exit_ok: true, at_secs: 200 });
        assert_eq!(t.streak("k"), 5);
        assert_eq!(t.streak("other"), 0);
    }
}
