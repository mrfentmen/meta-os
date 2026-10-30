//! Crate `os-supervisor` - Meta OS Rust rebuild, batch B21 (Milo).
//!
//! Supervisor and watchdog:
//!
//! - `os/intel/thresholds.py` (FND-030/WDG-018/WDG-026)
//! - `os/intel/watchdog.py` (WDG-001..WDG-009, WDG-012..WDG-017,
//!   WDG-024..WDG-026, WDG-028, INT-010, OS-034, OS-037)
//! - `os/intel/watchman_*.py` (OS-122 service loop, OS-129 boot
//!   verification)
//! - `os/intel/drills/kill_worker.py`, `watchman_*.py` drills,
//!   `os/intel/e2e_watchdog_surfaces.py` (stages the supervisor
//!   owns; dashboard surface needs the excluded bus.html and is
//!   marked exclusion-blocked)
//! - `os/mos/overseer.py`, `os/mos/reconcile.py` (dispatch,
//!   verify, recover over an injected backend)
//! - `os/os/watchman/relay_watchman.py` (OS-118 resident bell)
//!
//! The Python/Node originals stay the live fallback until this
//! batch is PORTED - nothing here edits them. The alert store
//! writer (`intel/store.py`, Hana B09), the brief composers
//! (`intel/brief.py`, Hana B10), the Spark client (`intel/*`,
//! Hana B11), and the push sender (Hana B10, never called here)
//! are carried as seams: this crate ports the exact detector,
//! judge, loop, and lifecycle behavior B21's tests pin, with the
//! canonical home named in each module.

pub mod alert_store;
pub mod backend;
pub mod budget_gate;
pub mod drills;
pub mod drills_watchman;
pub mod watchdog_detectors;
pub mod explanations;
pub mod overseer;
pub mod push_lite;
pub mod reconcile;
pub mod thresholds;
pub mod watchdog;
pub mod watchman;
pub mod watchman_boot;
pub mod watchman_bridge;
pub mod watchman_cycle;
pub mod watchman_loop;
pub mod watchman_runner;
pub mod watchman_service;
pub mod watchman_watch;
