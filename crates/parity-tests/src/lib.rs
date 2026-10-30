//! Crate `parity-tests` — B31 parity test harness.
//!
//! Owner: Buffy. Harness first (`support::fake_redis`, `support::helpers`,
//! `support::acceptance`) then case-by-case ports. Exclusion-blocked
//! cases (need excluded `relay_common`/viewer code) are named, never
//! dropped, never faked green.

pub mod support;
pub mod tests;
