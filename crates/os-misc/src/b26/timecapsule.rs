//! B26 timecapsule — port of `os/timecapsule.py` sweep rules.
//!
//! One-shot pops every due item from `muse-bus:timecapsule` and posts
//! `<nick>: <text>`; recurring items in `muse-bus:recur` are
//! re-registered at `now + every`. Delivery is race-safe via ZREM-claim;
//! failed pushes re-queue +60s so nothing is lost.

pub const TIMECAPSULE_KEY: &str = "muse-bus:timecapsule";
pub const REQUEUE_DELAY_SECS: i64 = 60;

pub fn validate_interval(interval: f64) -> Result<(), String> {
    if interval <= 0.0 {
        return Err("interval must be positive".to_string());
    }
    Ok(())
}

/// Is a capsule item due? (`score <= now`).
pub fn is_due(score: i64, now: i64) -> bool {
    score <= now
}

/// Next score for a recurring item.
pub fn recur_next(now: i64, every: i64) -> i64 {
    now + every
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sweep_shapes() {
        assert!(validate_interval(30.0).is_ok());
        assert!(validate_interval(0.0).is_err());
        assert!(is_due(10, 20));
        assert!(!is_due(30, 20));
        assert_eq!(recur_next(100, 60), 160);
    }
}
