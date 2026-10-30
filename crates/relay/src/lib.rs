//! Crate `relay` — Meta Nuntius relay (batch B08, owner: Hana).
//!
//! Port of `relay/relay.mjs` (Node, stdlib only). The source is the
//! spec: port behavior, do not redesign. Same inputs, outputs, edge
//! cases, error shapes — oddities ported and noted.
//!
//! This slice is the pure core: validation caps, notify ids, and the
//! in-memory / JSONL room store. The HTTP server layer (routes,
//! bodies, viewer) is the next slice; `main.rs` stays the B00 stub
//! until that slice lands.
//!
//! No external crates: SHA-256 and the small JSON string handling
//! are implemented here, mirroring the original's stdlib-only stance.

pub mod json;
pub mod notify;
pub mod sha256;
pub mod store;
pub mod validation;
