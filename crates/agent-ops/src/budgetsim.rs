//! Token-budget simulator core (what-if engine).
//!
//! Answers "what would this schedule cost?" BEFORE running it: given
//! past run records (agent, tokens, cost) and a candidate policy (per-
//! agent caps, halt thresholds), it projects totals, cap hits, and
//! savings versus uncapped. The interactive dashboard (design/) is a
//! thin view over these functions; this module is the tested core.

/// One finished run, as filed to the ledger.
#[derive(Debug, Clone)]
pub struct RunRecord {
    pub agent: String,
    pub tokens: u64,
    pub cost_usd: f64,
}

/// A candidate policy to simulate.
#[derive(Debug, Clone)]
pub struct Policy {
    /// Max tokens per single run; runs above are halted at the cap
    /// (only capped tokens billed).
    pub per_run_cap: u64,
    /// Max total tokens across the window; simulation stops there.
    pub window_cap: u64,
}

impl Default for Policy {
    fn default() -> Self {
        Policy { per_run_cap: u64::MAX, window_cap: u64::MAX }
    }
}

/// The projection for one policy over a run history.
#[derive(Debug)]
pub struct Projection {
    pub runs_seen: usize,
    pub runs_halted: usize,
    pub tokens_billed: u64,
    pub cost_usd: f64,
    pub uncapped_tokens: u64,
    pub uncapped_cost: f64,
}

impl Projection {
    pub fn saved_usd(&self) -> f64 {
        (self.uncapped_cost - self.cost_usd).max(0.0)
    }
}

/// Simulate `runs` under `policy`. Costs scale linearly with billed
/// tokens (documented assumption: flat per-token price in the records).
pub fn simulate(runs: &[RunRecord], policy: &Policy) -> Projection {
    let uncapped_tokens: u64 = runs.iter().map(|r| r.tokens).sum();
    let uncapped_cost: f64 = runs.iter().map(|r| r.cost_usd).sum();
    let mut billed = 0u64;
    let mut cost = 0.0;
    let mut halted = 0usize;
    let mut seen = 0usize;
    for r in runs {
        if billed >= policy.window_cap {
            break;
        }
        seen += 1;
        let mut take = r.tokens.min(policy.per_run_cap);
        if take < r.tokens {
            halted += 1;
        }
        if billed + take > policy.window_cap {
            take = policy.window_cap - billed;
            halted += 1;
        }
        billed += take;
        if r.tokens > 0 {
            cost += r.cost_usd * (take as f64 / r.tokens as f64);
        }
        if billed >= policy.window_cap {
            break;
        }
    }
    Projection { runs_seen: seen, runs_halted: halted, tokens_billed: billed, cost_usd: cost, uncapped_tokens, uncapped_cost }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn history() -> Vec<RunRecord> {
        vec![
            RunRecord { agent: "coder".into(), tokens: 10_000, cost_usd: 0.10 },
            RunRecord { agent: "browser".into(), tokens: 50_000, cost_usd: 0.50 },
            RunRecord { agent: "coder".into(), tokens: 5_000, cost_usd: 0.05 },
        ]
    }

    #[test]
    fn uncapped_default_changes_nothing() {
        let p = simulate(&history(), &Policy::default());
        assert_eq!(p.runs_seen, 3);
        assert_eq!(p.runs_halted, 0);
        assert_eq!(p.tokens_billed, 65_000);
        assert!((p.cost_usd - 0.65).abs() < 1e-9);
        assert_eq!(p.saved_usd(), 0.0);
    }

    #[test]
    fn per_run_cap_halts_big_runs_only() {
        let p = simulate(&history(), &Policy { per_run_cap: 20_000, window_cap: u64::MAX });
        assert_eq!(p.runs_halted, 1);
        assert_eq!(p.tokens_billed, 35_000);
        assert!(p.saved_usd() > 0.29);
    }

    #[test]
    fn window_cap_stops_the_schedule() {
        let p = simulate(&history(), &Policy { per_run_cap: u64::MAX, window_cap: 12_000 });
        assert_eq!(p.runs_seen, 2);
        assert_eq!(p.tokens_billed, 12_000);
    }
}
