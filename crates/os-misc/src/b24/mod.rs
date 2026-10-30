//! B24 — Bus messaging core.
//!
//! Ports `os/poll.py`, `os/presence.py`, `os/send.py`, `os/store.py`,
//! `os/watch.py`, `os/watch_nick.py`.
//!
//! The excluded `relay_common` transport is NOT ported. Bus I/O goes
//! through the [`BusTransport`] trait implemented by the caller (live
//! Redis/Upstash at gate, in-memory fake in parity tests). Pure logic
//! (id counters, duration parsing, edit/store rules) matches the
//! Python byte-for-byte in behavior.

pub mod poll;
pub mod presence;
pub mod send;
pub mod store;
pub mod transport;
pub mod watch;
pub mod watch_nick;
