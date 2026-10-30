//! Crate `os-budget` — Meta OS Rust rebuild, batch B20 (Milo).
//!
//! Budget & resource policy:
//!
//! - `os/intel/brief_cost_check.py` (BRF-027; cost math and table
//!   shape — exact token measurements ride Hana's `intel` crate,
//!   named as carried in [`cost`])
//! - `os/intel/budgets.py` (OS-085)
//! - `os/intel/cost_check.py` (INT-007; same measurement caveat)
//! - `os/intel/drills/budget_forecast.py`, `budget_gate.py`,
//!   `cgroup_limits.py`
//! - `os/mos/disk_audit.py` (OS-128)
//!
//! The Python/Node originals stay the live fallback until this
//! batch is PORTED — nothing here edits them. Budget behavior
//! that canonically lives in Hana's `intel` crate (`forecast.py`,
//! the brief composers, the watchdog tick) is carried here only
//! as the budget-side behavior B20's own tests pin, with the
//! canonical home named in each module.

pub mod brief_budget;
pub mod budgets;
pub mod cost;
pub mod disk_audit;
pub mod drills;
pub mod forecast;
pub mod stores;
pub mod watch_budget;
