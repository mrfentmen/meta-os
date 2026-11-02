//! CB2-306..307 — identity registration edges.

use os_identity::{CapabilityRegistry, Config, MemoryStore};

fn memory() -> CapabilityRegistry<MemoryStore> {
    CapabilityRegistry::new(MemoryStore::new(), Config::default(), "test-host".to_string())
}

#[test]
fn identity_empty_name() {
    let mut r = memory();
    assert!(r.register("", &["python"], "", 1, "", "").is_err());
    assert!(r.register("   ", &["python"], "", 1, "", "").is_err());
    assert!(r.agents().unwrap().is_empty(), "a refused register writes nothing");
}

#[test]
fn identity_id_unique() {
    // The registry keys agents by nick; re-registering the same nick
    // refreshes that one record instead of adding a second. That is
    // how this crate guarantees two records never share an identity.
    let mut r = memory();
    r.register("milo", &["python"], "", 1, "", "").unwrap();
    r.register("milo", &["rust"], "", 2, "", "").unwrap();
    let agents = r.agents().unwrap();
    assert_eq!(agents.len(), 1);
    assert_eq!(agents[0].0, "milo");
    assert_eq!(agents[0].1.cap_set(), vec!["rust".to_string()]);
}
