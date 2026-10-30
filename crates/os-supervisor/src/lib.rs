//! Crate `os-supervisor` — Meta OS Rust rebuild skeleton (B00).
//!
//! Batch B21 — Supervisor & watchdog. Owner: Milo.
//! Source files this batch ports:
//! - `os/intel/drills/kill_worker.py`
//! - `os/intel/drills/watchman_boot.py`
//! - `os/intel/drills/watchman_bridge.py`
//! - `os/intel/drills/watchman_bridge_tick.py`
//! - `os/intel/drills/watchman_cycle.py`
//! - `os/intel/drills/watchman_loop.py`
//! - `os/intel/drills/watchman_runner.py`
//! - `os/intel/drills/watchman_service.py`
//! - `os/intel/drills/watchman_service_cli.py`
//! - `os/intel/drills/watchman_watch.py`
//! - `os/intel/e2e_watchdog_surfaces.py`
//! - `os/intel/thresholds.py`
//! - `os/intel/watchdog.py`
//! - `os/intel/watchdog_load_check.py`
//! - `os/intel/watchman_boot.py`
//! - `os/intel/watchman_bridge.py`
//! - `os/intel/watchman_cycle.py`
//! - `os/intel/watchman_loop.py`
//! - `os/intel/watchman_runner.py`
//! - `os/intel/watchman_service.py`
//! - `os/intel/watchman_watch.py`
//! - `os/mos/overseer.py`
//! - `os/mos/reconcile.py`
//! - `os/os/watchman/relay_watchman.py`
//! - `os/tests/test_intel_e2e_watchdog_surfaces.py`
//! - `os/tests/test_intel_watchdog.py`
//! - `os/tests/test_intel_watchdog_load.py`
//! - `os/tests/test_intel_watchdog_service.py`
//! - `os/tests/test_intel_watchman_boot.py`
//! - `os/tests/test_intel_watchman_bridge.py`
//! - `os/tests/test_intel_watchman_bridge_tick.py`
//! - `os/tests/test_intel_watchman_cycle.py`
//! - `os/tests/test_intel_watchman_loop.py`
//! - `os/tests/test_intel_watchman_runner.py`
//! - `os/tests/test_intel_watchman_service.py`
//! - `os/tests/test_intel_watchman_service_cli.py`
//! - `os/tests/test_intel_watchman_service_unit.py`
//! - `os/tests/test_intel_watchman_watch.py`
//! - `os/tests/test_os_watchman.py`
//!
//! B21 ported (gate 1): the modules below implement the batch.
//! Layout mirrors the source tree: root modules are `os/intel/*` and
//! `os/mos/*` plus `os/os/watchman/relay_watchman.py`; `drills` holds
//! `os/intel/drills/*`. Cross-module seams (thresholds embedded in
//! watchdog.rs, trait seams for out-of-batch modules) are noted in
//! each module's docs. See batches/B21.md for the parity rule.

// Supervisor & watchdog modules (B21). Order follows the watchman chain:
// watch -> bridge -> loop -> cycle -> runner -> service, boot standalone.
pub mod thresholds;
pub mod watchdog;
pub mod watchdog_load_check;
pub mod e2e_watchdog_surfaces;
pub mod reconcile;
pub mod overseer;
pub mod relay_watchman;
pub mod watchman_watch;
pub mod watchman_bridge;
pub mod watchman_loop;
pub mod watchman_cycle;
pub mod watchman_runner;
pub mod watchman_service;
pub mod watchman_boot;
pub mod drills;
