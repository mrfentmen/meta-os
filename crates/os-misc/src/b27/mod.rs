//! B27 — World packs.
//!
//! Mixed batch: `PACK.md` / `pack.json` are **data — carried unchanged**
//! (originals stay in `os/worlds/`); the only code is
//! `os/worlds/validate_pack.py` — ported here as [`validate`].
//! Parity test `test_worlds_pack.py` lives in B31.

pub mod validate;
