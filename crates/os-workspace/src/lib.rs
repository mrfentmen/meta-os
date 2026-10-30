//! Crate `os-workspace` — Meta OS Rust rebuild, batch B19 (Milo).
//!
//! Workspace & artifact store:
//!
//! - `os/mos/artifact_store.py` (OS-083): git-backed versioned
//!   shared filesystem where dispatched jobs deposit work products.
//! - `os/mos/gitops.py`: safe Git review/merge — workers never
//!   push to main.
//!
//! The Python/Node originals stay the live fallback until this
//! batch is PORTED — nothing here edits them. No bus post, no
//! live Redis, no network: deposits are local files plus local
//! git only.

pub mod artifact_store;
pub mod git;
pub mod gitops;
