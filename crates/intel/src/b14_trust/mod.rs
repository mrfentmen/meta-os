//! B14 — Trust & launch (remaining intel) (`b14_trust` subtree).
//!
//! Ports (behavior, not redesign):
//! - `os/intel/trust.py` -> [`trust`] (OS-112 signed-job trust gate)
//! - `os/intel/timer_sweep.py` -> [`timer_sweep`] (OS-121 sweep)
//! - `os/intel/launch_run.py` -> [`launch_run`] (OS-102 child spawn)
//! - `os/intel/metaos-demo.env` -> fixture `crates/intel/fixtures/b14/`
//!   (DEM-013 demo profile; never loaded by production).
//!
//! Tests for these modules sit elsewhere (`test_intel_trust.py` in B09,
//! `test_os102_launch_run.py` in B31) — ported against those cases.

pub mod launch_run;
pub mod timer_sweep;
pub mod trust;
