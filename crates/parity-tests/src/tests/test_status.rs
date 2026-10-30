//! T060 [B31] port record for `os/tests/test_status.py` (same name roots).
//!
//! Status messages: every case needs the excluded `relay_common` store
//! (`status_set/get`, TTL, bulk reads, presence beat) plus the
//! `send`/`presence` CLIs — recorded blocked, never dropped, never
//! faked green.
//!
//! No live-store equivalent is implemented here on purpose: the store
//! semantics belong to the excluded `relay_common` module, and the
//! length cap (`MAX_TEXT`) lives there too, so even the boundary value

//! cannot be pinned from this tree. When a Rust status store lands,
//! these roots become real tests.

pub const CASES: &[&str] = &[
    "status set and get round trip",
    "empty status clears key",
    "status expires after ttl",
    "status too long rejected",
    "status get missing is none",
    "status get many bulk",
    "beat refreshes status ttl",
    "beat without status is a noop",
    "status fades when nick goes quiet",
    "send status sets key",
    "send status empty clears",
    "send status too long rejected",
    "send status rejects combinations",
    "presence shows status next to nick",
    "presence bare nick without status",
    "presence expired status shows bare nick",
    "status survives a regular send beat",
];
pub const EXCLUSION_BLOCKED: &[&str] = &[
    "all 17 cases need the excluded relay_common store (status_set/get, TTL, bulk, presence beat) + send/presence CLIs; MAX_TEXT cap also lives there",
];
