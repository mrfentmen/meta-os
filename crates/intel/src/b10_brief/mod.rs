//! B10 — Briefings & dispatch (`b10_brief` subtree).
//!
//! Ports (behavior, not redesign):
//! - `os/intel/alerts.py` -> [`alerts`]
//! - `os/intel/baton.py` -> [`baton`]
//! - `os/intel/brief.py` -> [`brief`], section derivation ->
//!   [`sections`]
//! - `os/intel/dispatch.py` -> [`dispatch`]
//! - `os/intel/forecast.py` -> [`forecast`]
//! - `os/intel/notify.py` -> [`notify`]
//! - `os/intel/push.py` -> [`push`]
//! - `os/intel/wake.py` -> [`wake`]
//!
//! Prompt fixtures carried byte-for-byte under
//! `crates/intel/fixtures/b10/prompts/` (8 prompts + README).

pub mod alerts;
pub mod baton;
pub mod brief;
pub mod dispatch;
pub mod forecast;
pub mod notify;
pub mod push;
pub mod sections;
pub mod wake;
