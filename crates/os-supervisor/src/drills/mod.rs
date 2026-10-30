//! Drill scripts (`os/intel/drills/*`) for the supervisor & watchdog batch.
//!
//! Each drill is a scenario harness: setup, run the intel module under
//! test, assert outcomes. Drills build on the landed intel watchman
//! chain (`crate::watchman_*`) and thresholds; watchdog interaction
//! goes through small local traits where noted in each drill file.

pub mod kill_worker;
pub mod watchman_boot;
pub mod watchman_bridge;
pub mod watchman_bridge_tick;
pub mod watchman_cycle;
pub mod watchman_loop;
pub mod watchman_runner;
pub mod watchman_service;
pub mod watchman_service_cli;
pub mod watchman_watch;
