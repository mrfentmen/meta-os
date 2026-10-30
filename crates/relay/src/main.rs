//! Crate `relay` — Meta OS Rust rebuild skeleton (B00).
//!
//! Batch B08 — Nuntius relay. Owner: Hana.
//! Source files this batch ports:
//! - `relay/README.md`
//! - `relay/relay.mjs`
//! - `relay/relay.test.mjs`
//!
//! Skeleton only: no logic yet. The Python/Node sources listed above are
//! the spec — port behavior, do not redesign. See BATCHES.md for the
//! compile gates and the parity rule.

// B00 gate-1 fix (Milo): a bin crate must have a main function or
// `cargo build --workspace` fails for everyone (E0601). Stub only;
// batch B08 (Hana) fills in the real relay entry point.
fn main() {}
