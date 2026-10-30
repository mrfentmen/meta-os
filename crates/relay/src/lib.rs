//! Crate `relay` — Meta Nuntius relay (batch B08, owner: Hana).
//!
//! Port of `relay/relay.mjs` (Node, stdlib only). The source is the
//! spec: port behavior, do not redesign. Same inputs, outputs, edge
//! cases, error shapes — oddities ported and noted.
//!
//! Modules:
//! - `validation`, `notify`, `sha256`, `store`, `json`: the pure core
//!   (validation caps, notify ids, in-memory / JSONL room store).
//! - `http`: the server layer (routes, bodies, viewer, std TCP serve),
//!   plus the parity tests whose name roots mirror
//!   `relay/relay.test.mjs`.
//!
//! No external crates: SHA-256 and the small JSON handling are
//! implemented here, mirroring the original's stdlib-only stance.

pub mod http;
pub mod json;
pub mod notify;
pub mod sha256;
pub mod store;
pub mod validation;
