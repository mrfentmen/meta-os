//! T058 [B31] port of `os/tests/test_os_uplink.py` (same name roots).
//!
//! OS uplink: the unit wiring + image-route pins run for real. The 11
//! queue/state-machine cases need the `relay_uplink` program port —
//! absent on main (os-worker still the B00 skeleton; Milo's B22
//! unmerged) — recorded blocked, never dropped.
//!
//! TREE DRIFT: `os/…` paths live under the folded tree (`os/os/…`).

use std::path::{Path, PathBuf};

pub const CASES: &[&str] = &[
    "sequence and cap",
    "failure sets retry and success clears",
    "valid order intakes signed",
    "valid order unsigned outside crew mode",
    "invalid orders rejected with reason",
    "duplicate id yields no second record",
    "tick never mutates inputs",
    "queue then drain in order and reset",
    "crew mode unsigned stays pending then intakes with key",
    "once prints then duplicate",
    "malformed orders exits 2",
    "unit wiring",
    "enabled on all three image routes",
];
pub const EXCLUSION_BLOCKED: &[&str] = &[
    "sequence and cap (needs relay_uplink port, absent on main)",
    "failure sets retry and success clears (needs relay_uplink port, absent on main)",
    "valid order intakes signed (needs relay_uplink port, absent on main)",
    "valid order unsigned outside crew mode (needs relay_uplink port, absent on main)",
    "invalid orders rejected with reason (needs relay_uplink port, absent on main)",
    "duplicate id yields no second record (needs relay_uplink port, absent on main)",
    "tick never mutates inputs (needs relay_uplink port, absent on main)",
    "queue then drain in order and reset (needs relay_uplink port, absent on main)",
    "crew mode unsigned stays pending then intakes with key (needs relay_uplink port, absent on main)",
    "once prints then duplicate (needs relay_uplink CLI port, absent on main)",
    "malformed orders exits 2 (needs relay_uplink CLI port, absent on main)",
];

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("..")
}
fn os_inner() -> PathBuf {
    root().join("os").join("os")
}
fn read(p: &Path) -> String {
    std::fs::read_to_string(p).unwrap_or_default()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_unit_wiring() {
        let unit = read(&os_inner().join("services").join("relay-uplink.service"));
        for needle in [
            "After=network-online.target relay-jobs.service",
            "PartOf=relay.target",
            "WantedBy=relay.target",
            "ConditionPathExists=/etc/metaos/secrets.env",
            "User=relay",
            "Restart=on-failure",
        ] {
            assert!(unit.contains(needle), "unit missing {needle:?}");
        }
        let exec = unit.split("ExecStart=").nth(1).unwrap().lines().next().unwrap();
        assert!(exec.contains("--key-file /etc/metaos/signing.key"), "{exec}");
        assert!(!exec.contains("token="), "{exec}");
        assert!(!exec.contains("MUSE_"), "{exec}");
        assert!(read(&os_inner().join("services").join("relay.target")).contains("relay-uplink.service"));
    }

    #[test]
    fn test_enabled_on_all_three_image_routes() {
        for rel in ["build-image.sh", "packer/metaos.pkr.hcl", "live-build/config/hooks/live/0900-metaos-services.hook.chroot"] {
            let text = read(&os_inner().join(rel));
            assert!(text.contains("relay-uplink.service"), "{rel}");
        }
    }
}
