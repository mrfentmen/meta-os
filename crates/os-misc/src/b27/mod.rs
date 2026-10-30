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

/// T017 verify-carried: doe + dsny packs (byte-identical, left in place).
pub const T017_FILES: &[&str] = &[
    "os/worlds/doe/PACK.md",
    "os/worlds/doe/pack.json",
    "os/worlds/dsny/PACK.md",
    "os/worlds/dsny/pack.json",
];

/// T018 verify-carried: ems + fdny packs (byte-identical, left in place).
pub const T018_FILES: &[&str] = &[
    "os/worlds/ems/PACK.md",
    "os/worlds/ems/pack.json",
    "os/worlds/fdny/PACK.md",
    "os/worlds/fdny/pack.json",
];

/// T019 verify-carried: hospital + mta packs (byte-identical, left in place).
pub const T019_FILES: &[&str] = &[
    "os/worlds/hospital/PACK.md",
    "os/worlds/hospital/pack.json",
    "os/worlds/mta/PACK.md",
    "os/worlds/mta/pack.json",
];

/// T020 verify-carried: nypd pack (byte-identical, left in place).
pub const T020_FILES: &[&str] = &[
    "os/worlds/nypd/PACK.md",
    "os/worlds/nypd/pack.json",
];
