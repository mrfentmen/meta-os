//! B059 — the least-covered public surface. The in-crate module
//! (`src/lib.rs`) is the crate's best-covered module; this file closes the
//! items it never touches: the error trait impls, `MemoryStore`'s direct
//! operations, and the record-conversion edge cases.

use std::collections::HashMap;

use os_identity::{
    AgentRecord, CapStore, CapabilityRegistry, Config, MemoryStore, RegisterError,
    RegistryError, StoreError, DEFAULT_CAPNS, DEFAULT_STALE_AFTER,
};

#[test]
fn config_defaults_are_the_documented_constants() {
    let cfg = Config::default();
    assert_eq!(cfg.capns, DEFAULT_CAPNS);
    assert_eq!(cfg.stale_after, DEFAULT_STALE_AFTER);
    assert_eq!(cfg.key_for("milo"), "muse-bus:cap:milo");
    assert_eq!(cfg.index(), "muse-bus:cap:index");
}

#[test]
fn all_three_error_types_are_std_errors() {
    fn assert_error<E: std::error::Error + 'static>(e: E) {
        let _: Box<dyn std::error::Error> = Box::new(e);
    }
    assert_error(StoreError("boom".to_string()));
    assert_error(RegisterError::NickRequired);
    assert_error(RegistryError::Validation(
        RegisterError::AtLeastOneCapabilityRequired,
    ));
}

#[test]
fn register_error_messages_are_python_exact() {
    assert_eq!(RegisterError::NickRequired.to_string(), "nick required");
    assert_eq!(
        RegisterError::AtLeastOneCapabilityRequired.to_string(),
        "at least one capability required"
    );
}

#[test]
fn registry_error_display_covers_both_variants() {
    assert_eq!(
        RegistryError::Validation(RegisterError::NickRequired).to_string(),
        "nick required"
    );
    assert_eq!(
        RegistryError::Store(StoreError("boom".to_string())).to_string(),
        "store error: boom"
    );
}

#[test]
fn memory_store_round_trips_direct_operations() {
    let mut store = MemoryStore::new();
    assert!(store.hgetall("missing").unwrap().is_empty());

    store.put_hash("k", &[("a", "1")]);
    assert_eq!(
        store.hgetall("k").unwrap(),
        vec![("a".to_string(), "1".to_string())]
    );

    store
        .hset("k", &[("b".to_string(), "2".to_string())])
        .unwrap();
    assert_eq!(store.hgetall("k").unwrap().len(), 2, "hset adds fields");

    store.put_index_member("i", 5, "x");
    assert_eq!(store.zrange("i").unwrap(), vec!["x".to_string()]);
    store.zrem("i", "x").unwrap();
    assert!(store.zrange("i").unwrap().is_empty());

    store.del("k").unwrap();
    assert!(store.hgetall("k").unwrap().is_empty());
}

#[test]
fn memory_store_zrange_orders_equal_scores_by_member() {
    let mut store = MemoryStore::new();
    for member in ["b", "a", "c"] {
        store.put_index_member("i", 7, member);
    }
    assert_eq!(
        store.zrange("i").unwrap(),
        vec!["a".to_string(), "b".to_string(), "c".to_string()],
        "equal scores fall back to member order, like Redis"
    );
}

#[test]
fn memory_store_job_claims_reflect_set_jobs() {
    let mut store = MemoryStore::new();
    store.set_jobs(vec![
        os_identity::JobClaim {
            status: "claimed".to_string(),
            claim: "milo".to_string(),
        },
        os_identity::JobClaim {
            status: "done".to_string(),
            claim: "rowan".to_string(),
        },
    ]);
    let claims = store.job_claims().unwrap();
    assert_eq!(claims.len(), 2);
    assert_eq!(claims[0].status, "claimed");
    assert_eq!(claims[1].claim, "rowan");
}

#[test]
fn from_fields_defaults_and_ignores_unknown_fields() {
    let mut fields = HashMap::new();
    fields.insert("caps".to_string(), "python".to_string());
    fields.insert("unknown".to_string(), "ignored".to_string());

    let rec = AgentRecord::from_fields(&fields);
    assert_eq!(rec.caps, "python");
    assert_eq!(rec.max_jobs, "1", "missing max_jobs defaults to 1");
    assert_eq!(rec.updated, "0", "missing updated defaults to 0");
    assert_eq!(rec.host, "");
    assert!(rec.roles.is_none());
    assert!(rec.dm.is_none());
    assert!(rec.info.is_none());
}

#[test]
fn to_fields_skips_empty_values() {
    let rec = AgentRecord {
        caps: "python".to_string(),
        roles: None,
        max_jobs: "2".to_string(),
        host: "h".to_string(),
        updated: "1".to_string(),
        dm: Some("secret".to_string()),
        info: None,
    };
    let fields: HashMap<String, String> = rec.to_fields().into_iter().collect();
    assert_eq!(fields.len(), 5);
    assert!(!fields.contains_key("roles"));
    assert!(!fields.contains_key("info"));
    assert_eq!(fields.get("dm").map(String::as_str), Some("secret"));
    assert_eq!(AgentRecord::from_fields(&fields), rec);
}

#[test]
fn cap_set_drops_empties_from_ragged_caps() {
    let rec = AgentRecord {
        caps: "python,,testing,".to_string(),
        ..Default::default()
    };
    assert_eq!(rec.cap_set(), vec!["python", "testing"]);
}

#[test]
fn negative_max_jobs_behaves_as_one() {
    let mut r = CapabilityRegistry::new(MemoryStore::new(), Config::default(), "h".to_string());
    r.register("milo", &["python"], "", -5, "", "").unwrap();
    r.store_mut().set_jobs(vec![os_identity::JobClaim {
        status: "claimed".to_string(),
        claim: "milo".to_string(),
    }]);
    assert_eq!(
        r.find_for(&["python"]).unwrap(),
        Vec::<String>::new(),
        "max(1, -5) is 1"
    );
}
