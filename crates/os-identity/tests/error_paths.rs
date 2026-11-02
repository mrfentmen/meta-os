//! B050 — every refusal and failure branch in `os-identity`, through the
//! public API only. No production item was widened to make these compile.
//!
//! The expected values are read from `src/lib.rs`; the behaviour record
//! `os-build/records/os-identity.md` cites the lines each one comes from.

use os_identity::{
    CapStore, CapabilityRegistry, Config, MemoryStore, RegisterError, RegistryError, StoreError,
};

fn memory() -> CapabilityRegistry<MemoryStore> {
    CapabilityRegistry::new(MemoryStore::new(), Config::default(), "test-host".to_string())
}

/// Every operation fails, for the two documented swallow paths and the
/// propagate paths.
#[derive(Debug, Default)]
struct FailingStore;

impl CapStore for FailingStore {
    fn hgetall(&self, _key: &str) -> Result<Vec<(String, String)>, StoreError> {
        Err(StoreError("boom".to_string()))
    }
    fn hset(&mut self, _key: &str, _fields: &[(String, String)]) -> Result<(), StoreError> {
        Err(StoreError("boom".to_string()))
    }
    fn del(&mut self, _key: &str) -> Result<(), StoreError> {
        Err(StoreError("boom".to_string()))
    }
    fn zadd(&mut self, _index: &str, _score: i64, _member: &str) -> Result<(), StoreError> {
        Err(StoreError("boom".to_string()))
    }
    fn zrem(&mut self, _index: &str, _member: &str) -> Result<(), StoreError> {
        Err(StoreError("boom".to_string()))
    }
    fn zrange(&self, _index: &str) -> Result<Vec<String>, StoreError> {
        Err(StoreError("boom".to_string()))
    }
    fn job_claims(&self) -> Result<Vec<os_identity::JobClaim>, StoreError> {
        Err(StoreError("boom".to_string()))
    }
}

/// Index and writes work; per-agent reads fail. This separates the caught
/// index error from the propagating hash error in `agents`.
#[derive(Debug, Default)]
struct HashFailingStore;

impl CapStore for HashFailingStore {
    fn hgetall(&self, _key: &str) -> Result<Vec<(String, String)>, StoreError> {
        Err(StoreError("hash boom".to_string()))
    }
    fn hset(&mut self, _key: &str, _fields: &[(String, String)]) -> Result<(), StoreError> {
        Ok(())
    }
    fn del(&mut self, _key: &str) -> Result<(), StoreError> {
        Ok(())
    }
    fn zadd(&mut self, _index: &str, _score: i64, _member: &str) -> Result<(), StoreError> {
        Ok(())
    }
    fn zrem(&mut self, _index: &str, _member: &str) -> Result<(), StoreError> {
        Ok(())
    }
    fn zrange(&self, _index: &str) -> Result<Vec<String>, StoreError> {
        Ok(vec!["milo".to_string()])
    }
    fn job_claims(&self) -> Result<Vec<os_identity::JobClaim>, StoreError> {
        Ok(vec![])
    }
}

/// Listing works and the one record is stale, but `del` fails: the only
/// way to make `prune_stale` return an error without failing `agents`.
#[derive(Debug, Default)]
struct DelFailingStore;

impl CapStore for DelFailingStore {
    fn hgetall(&self, _key: &str) -> Result<Vec<(String, String)>, StoreError> {
        Ok(vec![("updated".to_string(), "0".to_string())])
    }
    fn hset(&mut self, _key: &str, _fields: &[(String, String)]) -> Result<(), StoreError> {
        Ok(())
    }
    fn del(&mut self, _key: &str) -> Result<(), StoreError> {
        Err(StoreError("del boom".to_string()))
    }
    fn zadd(&mut self, _index: &str, _score: i64, _member: &str) -> Result<(), StoreError> {
        Ok(())
    }
    fn zrem(&mut self, _index: &str, _member: &str) -> Result<(), StoreError> {
        Ok(())
    }
    fn zrange(&self, _index: &str) -> Result<Vec<String>, StoreError> {
        Ok(vec!["milo".to_string()])
    }
    fn job_claims(&self) -> Result<Vec<os_identity::JobClaim>, StoreError> {
        Ok(vec![])
    }
}

#[test]
fn register_blank_nick_refused_with_python_wording() {
    let mut r = memory();
    for nick in ["", "   "] {
        let err = r.register(nick, &["python"], "", 1, "", "").unwrap_err();
        assert_eq!(
            err,
            RegistryError::Validation(RegisterError::NickRequired),
            "nick {nick:?} must be refused before any write"
        );
        assert_eq!(err.to_string(), "nick required");
    }
    assert!(r.get("milo").unwrap().is_none());
}

#[test]
fn register_without_a_usable_capability_refused() {
    let mut r = memory();
    let err = r.register("milo", &[], "", 1, "", "").unwrap_err();
    assert_eq!(
        err,
        RegistryError::Validation(RegisterError::AtLeastOneCapabilityRequired)
    );
    assert_eq!(err.to_string(), "at least one capability required");

    let err = r
        .register("milo", &["", "   "], "", 1, "", "")
        .unwrap_err();
    assert_eq!(
        err,
        RegistryError::Validation(RegisterError::AtLeastOneCapabilityRequired)
    );
    assert!(r.get("milo").unwrap().is_none(), "refusal stores nothing");
}

#[test]
fn register_store_failure_is_wrapped_as_store_error() {
    let mut r = CapabilityRegistry::new(FailingStore, Config::default(), "h".to_string());
    match r.register("milo", &["python"], "", 1, "", "") {
        Err(RegistryError::Store(StoreError(msg))) => assert_eq!(msg, "boom"),
        other => panic!("expected a store error, got {other:?}"),
    }
}

#[test]
fn touch_unknown_is_false_and_store_failure_propagates() {
    let mut r = memory();
    assert_eq!(r.touch("ghost"), Ok(false), "unknown heartbeat is False");

    let mut f = CapabilityRegistry::new(FailingStore, Config::default(), "h".to_string());
    assert!(f.touch("ghost").is_err(), "a read failure is an error, not False");
}

#[test]
fn unregister_store_failure_propagates() {
    let mut f = CapabilityRegistry::new(FailingStore, Config::default(), "h".to_string());
    assert!(f.unregister("milo").is_err());
}

#[test]
fn get_store_failure_propagates() {
    let f = CapabilityRegistry::new(FailingStore, Config::default(), "h".to_string());
    assert!(f.get("milo").is_err());
}

#[test]
fn agents_index_error_is_an_empty_list_not_an_error() {
    let f = CapabilityRegistry::new(FailingStore, Config::default(), "h".to_string());
    assert_eq!(
        f.agents(),
        Ok(Vec::new()),
        "the Python except path returns an empty listing"
    );
}

#[test]
fn agents_per_agent_hash_error_propagates() {
    let f = CapabilityRegistry::new(HashFailingStore, Config::default(), "h".to_string());
    assert!(
        f.agents().is_err(),
        "only the index read is caught; a hash read must surface"
    );
}

#[test]
fn find_for_propagates_a_per_agent_read_error() {
    let f = CapabilityRegistry::new(HashFailingStore, Config::default(), "h".to_string());
    assert!(f.find_for(&["python"]).is_err());
}

#[test]
fn active_claims_job_error_is_zero() {
    let f = CapabilityRegistry::new(FailingStore, Config::default(), "h".to_string());
    assert_eq!(f.active_claims("milo"), 0);
}

#[test]
fn prune_stale_propagates_a_delete_error() {
    let mut f = CapabilityRegistry::new(DelFailingStore, Config::default(), "h".to_string());
    assert!(
        f.prune_stale().is_err(),
        "a stale agent whose delete fails must surface the error"
    );
}

#[test]
fn store_error_display_and_conversion() {
    let e = StoreError("boom".to_string());
    assert_eq!(e.to_string(), "store error: boom");
    let wrapped: RegistryError = e.into();
    assert_eq!(wrapped, RegistryError::Store(StoreError("boom".to_string())));
    assert_eq!(wrapped.to_string(), "store error: boom");
}
