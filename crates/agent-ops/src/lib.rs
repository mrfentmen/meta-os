//! Crate `agent-ops` — operator-side agent subsystems for Meta OS.
//!
//! The missing pieces of the agent-OS blueprint, as one honest crate:
//!
//! - [`vectors`]: lexical vector memory (TF-IDF cosine) over ledger
//!   records. Deterministic, no embedding model. Paraphrase similarity
//!   needs a real embedding backend; raw texts are kept for re-indexing.
//! - [`snapshot`]: workspace snapshots + instant rollbacks (sha256
//!   manifests, env + dependency fingerprints).
//! - [`throttle`]: proof-of-work execution throttler: escalating waits
//!   plus mandatory written reflection before retrying failures.
//! - [`egress`]: audited egress guard. Allowlist routing only — no
//!   proxies, no CAPTCHA solving, no fingerprint spoofing, ever.
//! - [`router`]: local/cloud tier routing decisions with an explicit
//!   NO_BACKEND outcome instead of silent downgrade.
//! - [`budgetsim`]: token-budget what-if engine (tested core behind
//!   the interactive dashboard).
//!
//! Everything here is pure logic + tests. Execution, backends, and
//! humans stay with the callers.

pub mod budgetsim;
pub mod egress;
pub mod router;
pub mod snapshot;
pub mod throttle;
pub mod vectors;
