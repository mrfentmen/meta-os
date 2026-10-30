//! B27 — World packs.
//!
//! Mixed batch: `PACK.md` / `pack.json` are **data — carried unchanged**
//! (originals stay in `os/worlds/`); the only code is
//! `os/worlds/validate_pack.py` — ported here as [`validate`].
//! Parity test `test_worlds_pack.py` lives in B31.

pub mod par_clock;
pub mod validate;

/// T016 verify-carried: world README + dep pack (byte-identical, left in place).
pub const T016_FILES: &[&str] = &[
    "os/worlds/README.md",
    "os/worlds/dep/PACK.md",
    "os/worlds/dep/pack.json",
];
