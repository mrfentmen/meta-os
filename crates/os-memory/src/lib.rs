//! Crate `os-memory` — Meta OS Rust rebuild, batch B17 (Milo).
//!
//! Memory service (`os/mos/memory.py`) plus the parity cases from
//! its assigned test files:
//!
//! - `os/mos/memory.py`
//! - `os/tests/test_intel_brief_memory_depth_caller.py`
//! - `os/tests/test_os078_memory.py`
//!
//! The Python/Node originals stay the live fallback until this
//! batch is PORTED — nothing here edits them. The full brief
//! composer that consumes `memory_depth` records is Hana's B10
//! territory; [`brief_depth`] ports exactly the caller plus the
//! line renderer the B17 tests pin.
#![allow(clippy::result_large_err)]

pub mod bake;
pub mod brief_depth;
pub mod memory;
