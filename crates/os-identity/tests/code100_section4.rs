//! CB-033: an empty name and a 10k-char name are handled without panic.

use os_identity::{CapabilityRegistry, Config, MemoryStore};

fn memory() -> CapabilityRegistry<MemoryStore> {
    CapabilityRegistry::new(MemoryStore::new(), Config::default(), "test-host".to_string())
}

#[test]
fn empty_name_is_refused_not_stored() {
    let mut r = memory();
    assert!(r.register("", &["python"], "", 1, "", "").is_err());
    assert!(r.get("").unwrap().is_none());
}

#[test]
fn ten_thousand_char_name_round_trips() {
    let mut r = memory();
    let nick = "n".repeat(10_000);
    assert!(r.register(&nick, &["python"], "", 1, "", "").is_ok());
    assert!(r.get(&nick).unwrap().is_some());
    assert_eq!(
        Config::default().key_for(&nick).len(),
        "muse-bus:cap:".len() + 10_000
    );
}
