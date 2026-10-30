//! Crate `os-identity` — Meta OS Rust rebuild, batch B18 (Milo).
//!
//! Identity & capabilities service (`os/mos/capabilities.py`):
//! which agents exist and what they can do. Agents register
//! their capabilities (e.g. python, testing, docs) and heartbeat
//! them. The overseer assigns jobs only to agents whose
//! capabilities cover the job's requirements, who are fresh
//! (recent heartbeat), and who have spare job capacity.
//!
//! The Python/Node originals stay the live fallback until this
//! batch is PORTED — nothing here edits them. The Redis transport
//! (`relay_common`, excluded) is modeled in-memory in
//! [`capabilities`], with identical registry semantics; the live
//! claim-count wiring reads the jobs index (B16) and is injected
//! here as a caller-supplied count so the gate logic itself is
//! pinned without a transport.

pub mod capabilities;
