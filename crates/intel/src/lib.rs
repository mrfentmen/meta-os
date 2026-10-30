//! Crate `intel` — Relay Intelligence (batch B09 docs, owner: Hana).
//!
//! Port of the Meta OS `os/intel/` package: the intel wire formats,
//! record schemas, and the core registry modules. The Python originals
//! stay the live fallback until this batch is PORTED (both gates +
//! parity). Later batches (B10–B14) extend this crate in their own
//! module subtrees; this header documents the shared contract points
//! from `os/intel/README.md`.
//!
//! ## Wire format freeze (FND-020)
//!
//! Intel announcement lines are one-line bus messages that point at a
//! record. They are never the record itself: the full text lives in
//! the store (see [`b09_core::store`] key layout), the line carries
//! only the id and the fields a reader needs to triage without a
//! lookup. Wire announcements are best-effort chat lines; store state
//! is the source of truth.
//!
//! Rules for every intel line:
//! - Exactly one line. No newline, no trailing free text beyond the
//!   shape. A line that does not match its shape exactly is not an
//!   intel line; parsers ignore it.
//! - No secrets, no spec text, no job titles, no credential-shaped
//!   strings. A line names a record; it never quotes one.
//! - Ids contain no spaces. Readers split a line on spaces: the
//!   first token is the prefixed id, the remaining tokens are the
//!   shape's fixed fields in order.
//! - A frozen shape changes only with a new dated note, never a
//!   silent edit. Lanes already parsing a shape must keep working
//!   across any change, or the change does not land.
//!
//! ## Announcement shapes
//!
//! - `BRIEF:<room>:<ts> <kind>` — a brief was stored. `<kind>` is one
//!   of `morning`, `onjoin`, `ondemand`. The `<ts>` matches the `<ts>`
//!   in the store key `muse-bus:intel:brief:<room>:<ts>`. The line
//!   carries no section text; sections live only in the stored brief
//!   record.
//! - `ALERT:<id> <severity> <kind>` — a critical alert was raised.
//!   `<severity>` is `critical` or `warning`; only critical alerts
//!   are announced. Warnings accumulate silently for the brief and
//!   the dashboard and never produce a line. The line carries no
//!   explanation text and no suggested fix.
//! - `DISPATCH:<id> -> <n> jobs` — a plan was posted. `<n>` is the
//!   number of jobs actually posted, not the number planned. The line
//!   carries no job titles, no file lists, no specs.
//!
//! ## Posting gate (GOV-002)
//!
//! No intel announcement line is posted until the owner approves
//! posting. Lanes build against these shapes now; the posting call
//! sites stay gated.
//!
//! ## Module map (B09 — `b09_core` subtree)
//!
//! - `os/intel.py` -> [`b09_core::cli`]
//! - `os/intel/__init__.py` -> [`b09_core::init`]
//! - `os/intel/capability.py` -> [`b09_core::capability`]
//! - `os/intel/capability_files.py` -> [`b09_core::capability_files`]
//! - `os/intel/explanations.py` -> [`b09_core::explanations`]
//! - `os/intel/gate.py` -> [`b09_core::gate`]
//! - `os/intel/ingest.py` -> [`b09_core::ingest`]
//! - `os/intel/integration.py` -> [`b09_core::integration`]
//! - `os/intel/join.py` -> [`b09_core::join`]
//! - `os/intel/ladder.py` -> [`b09_core::ladder`]
//! - `os/intel/store.py` -> [`b09_core::store`]
//!
//! Fixtures carried byte-for-byte under `crates/intel/fixtures/b09/`:
//! the five crew capability grants (`capabilities/*.json`) plus the
//! fixtures README. Checksums verified against the sources (T179).
//!
//! ## Module map (B10 — `b10_brief` subtree)
//!
//! - `os/intel/alerts.py` -> [`b10_brief::alerts`]
//! - `os/intel/baton.py` -> [`b10_brief::baton`]
//! - `os/intel/brief.py` -> [`b10_brief::brief`]
//! - `os/intel/dispatch.py` -> [`b10_brief::dispatch`]
//! - `os/intel/forecast.py` -> [`b10_brief::forecast`]
//! - `os/intel/notify.py` -> [`b10_brief::notify`]
//! - `os/intel/push.py` -> [`b10_brief::push`]
//! - `os/intel/wake.py` -> [`b10_brief::wake`]

pub mod b09_core;
pub mod b10_brief;
pub mod b11_spark;
pub mod b13_devpack;
pub mod b14_trust;
