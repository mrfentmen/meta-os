//! B09 — Intel core & capability registry (`b09_core` subtree).
//!
//! Ports (behavior, not redesign):
//! - `os/intel.py` -> [`cli`]
//! - `os/intel/__init__.py` -> [`init`]
//! - `os/intel/capability.py` -> [`capability`]
//! - `os/intel/capability_files.py` -> [`capability_files`]
//! - `os/intel/explanations.py` -> [`explanations`]
//! - `os/intel/gate.py` -> [`gate`]
//! - `os/intel/ingest.py` -> [`ingest`]
//! - `os/intel/integration.py` -> [`integration`]
//! - `os/intel/join.py` -> [`join`]
//! - `os/intel/ladder.py` -> [`ladder`]
//! - `os/intel/store.py` -> [`store`]
//!
//! Fixtures carried byte-for-byte under `crates/intel/fixtures/b09/`:
//! capabilities/*.json (5 crew grants), README.md.
//! The Python originals stay the live fallback until PORTED.

pub mod capability;
pub mod capability_files;
pub mod cli;
pub mod explanations;
pub mod gate;
pub mod ingest;
pub mod init;
pub mod integration;
pub mod join;
pub mod ladder;
pub mod store;
