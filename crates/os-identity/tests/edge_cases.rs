//! B051 — empty, maximum, duplicate and out-of-order inputs for
//! `os-identity`, through the public API only.

use os_identity::{
    is_fresh, AgentRecord, CapabilityRegistry, Config, JobClaim, MemoryStore,
};

fn memory() -> CapabilityRegistry<MemoryStore> {
    CapabilityRegistry::new(MemoryStore::new(), Config::default(), "test-host".to_string())
}

#[test]
fn empty_requirement_list_matches_every_fresh_agent_with_capacity() {
    let mut r = memory();
    r.register("zoe", &["python"], "", 1, "", "").unwrap();
    r.register("amy", &["docs"], "", 1, "", "").unwrap();
    r.register("max", &["testing"], "", 1, "", "").unwrap();
    assert_eq!(
        r.find_for(&[]).unwrap(),
        vec!["amy".to_string(), "max".to_string(), "zoe".to_string()],
        "empty requirements are a subset of every cap set, sorted by nick"
    );
}

#[test]
fn empty_capability_slice_is_refused() {
    let mut r = memory();
    assert!(r.register("milo", &[], "", 1, "", "").is_err());
    assert!(r.get("milo").unwrap().is_none());
}

#[test]
fn maximum_capability_list_and_job_capacity() {
    let mut r = memory();
    let caps: Vec<String> = (0..500).map(|i| format!("cap{i:03}")).collect();
    let refs: Vec<&str> = caps.iter().map(|s| s.as_str()).collect();
    r.register("milo", &refs, "", i64::MAX, "", "").unwrap();

    let rec = r.get("milo").unwrap().unwrap();
    assert_eq!(rec.max_jobs, i64::MAX.to_string());
    assert_eq!(rec.cap_set().len(), 500);
    assert_eq!(
        r.find_for(&["cap499"]).unwrap(),
        vec!["milo".to_string()],
        "the last capability is still matchable"
    );
}

#[test]
fn maximum_nick_length_round_trips() {
    let mut r = memory();
    let nick = "n".repeat(10_000);
    r.register(&nick, &["python"], "", 1, "", "").unwrap();
    assert!(r.get(&nick).unwrap().is_some());
    assert_eq!(
        Config::default().key_for(&nick).len(),
        "muse-bus:cap:".len() + 10_000,
        "the key is the prefix plus the nick, nothing truncated"
    );
}

#[test]
fn duplicate_capabilities_are_deduped_and_sorted() {
    let mut r = memory();
    r.register(
        "milo",
        &["Python", " testing ", "python", "DOCS"],
        "",
        1,
        "",
        "",
    )
    .unwrap();
    assert_eq!(r.get("milo").unwrap().unwrap().caps, "docs,python,testing");
}

#[test]
fn duplicate_registration_updates_one_record_and_one_index_member() {
    let mut r = memory();
    r.register("milo", &["python"], "", 1, "", "").unwrap();
    r.register("milo", &["testing"], "", 2, "", "").unwrap();

    let rec = r.get("milo").unwrap().unwrap();
    assert_eq!(rec.caps, "testing");
    assert_eq!(rec.max_jobs, "2");
    assert_eq!(r.agents().unwrap().len(), 1, "no duplicate index entry");
}

#[test]
fn out_of_order_registration_returns_sorted_nicks() {
    let mut r = memory();
    for nick in ["zoe", "amy", "max"] {
        r.register(nick, &["python"], "", 1, "", "").unwrap();
    }
    assert_eq!(
        r.find_for(&["python"]).unwrap(),
        vec!["amy".to_string(), "max".to_string(), "zoe".to_string()]
    );
}

#[test]
fn out_of_order_index_scores_list_in_score_order() {
    let mut store = MemoryStore::new();
    for (nick, score) in [("late", 30), ("early", 10), ("mid", 20)] {
        store.put_hash(
            &format!("muse-bus:cap:{nick}"),
            &[("caps", "python"), ("updated", "30")],
        );
        store.put_index_member("muse-bus:cap:index", score, nick);
    }
    let r = CapabilityRegistry::new(store, Config::default(), "h".to_string());
    let nicks: Vec<String> = r
        .agents()
        .unwrap()
        .into_iter()
        .map(|(nick, _)| nick)
        .collect();
    assert_eq!(nicks, vec!["early", "mid", "late"]);
}

#[test]
fn staleness_boundary_is_inclusive() {
    let record = AgentRecord {
        updated: "1000".to_string(),
        ..Default::default()
    };
    assert!(is_fresh(&record, 1900, 900), "exactly stale_after is fresh");
    assert!(!is_fresh(&record, 1901, 900), "one second past is stale");
}

#[test]
fn future_and_unparseable_updated_values() {
    let future = AgentRecord {
        updated: "2000".to_string(),
        ..Default::default()
    };
    assert!(is_fresh(&future, 1900, 900), "a future heartbeat is fresh");

    let broken = AgentRecord {
        updated: "not-a-number".to_string(),
        ..Default::default()
    };
    assert!(!is_fresh(&broken, 1900, 900), "unparseable is stale");
}

#[test]
fn extreme_positive_updated_does_not_overflow() {
    let record = AgentRecord {
        updated: i64::MAX.to_string(),
        ..Default::default()
    };
    assert!(
        is_fresh(&record, 1_700_000_000, 900),
        "a far-future heartbeat is fresh and the subtraction stays in range"
    );
}

#[test]
fn capacity_zero_behaves_as_one() {
    let mut r = memory();
    r.register("milo", &["python"], "", 0, "", "").unwrap();
    r.store_mut().set_jobs(vec![JobClaim {
        status: "claimed".to_string(),
        claim: "milo".to_string(),
    }]);
    assert_eq!(
        r.find_for(&["python"]).unwrap(),
        Vec::<String>::new(),
        "max(1, 0) means one claimed job fills capacity"
    );
}
