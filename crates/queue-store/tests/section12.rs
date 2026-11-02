use queue_store::RecordStore;
use serde_json::json;
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

fn path(tag: &str) -> PathBuf {
    let n = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos();
    std::env::temp_dir().join(format!("queue-record-{tag}-{}-{n}.jsonl", std::process::id()))
}

#[test]
fn record_roundtrip() {
    let p = path("roundtrip");
    let s = RecordStore::open(&p).unwrap();
    let rec = json!({"id":"r1","value":42});
    s.append(&rec).unwrap();
    assert_eq!(s.get("r1"), Some(rec));
    let _ = std::fs::remove_file(p);
}

#[test]
fn append_only_violation() {
    let p = path("duplicate");
    let s = RecordStore::open(&p).unwrap();
    let rec = json!({"id":"r1"});
    s.append(&rec).unwrap();
    assert!(s.append(&rec).unwrap_err().0.contains("duplicate"));
    let _ = std::fs::remove_file(p);
}

#[test]
fn read_missing() {
    let p = path("missing");
    let s = RecordStore::open(&p).unwrap();
    assert_eq!(s.get("nope"), None);
    let _ = std::fs::remove_file(p);
}

#[test]
fn truncated_tail_load() {
    let p = path("tail");
    std::fs::write(&p, "{\"id\":\"good\"}\n{\"id\":\"bad\"").unwrap();
    let s = RecordStore::open(&p).unwrap();
    assert_eq!(s.list().len(), 1);
    assert!(s.partial_line().unwrap().contains("bad"));
    let _ = std::fs::remove_file(p);
}

#[test]
fn list_insertion_order() {
    let p = path("order");
    let s = RecordStore::open(&p).unwrap();
    for i in 1..=5 {
        s.append(&json!({"id":format!("r{i}")})).unwrap();
    }
    let ids: Vec<String> = s.list().iter().map(|r| r["id"].as_str().unwrap().to_string()).collect();
    assert_eq!(ids, vec!["r1", "r2", "r3", "r4", "r5"]);
    let _ = std::fs::remove_file(p);
}

#[test]
fn list_empty() {
    let p = path("empty");
    let s = RecordStore::open(&p).unwrap();
    assert!(s.list().is_empty());
    let _ = std::fs::remove_file(p);
}

#[test]
fn write_missing_field() {
    let p = path("field");
    let s = RecordStore::open(&p).unwrap();
    assert!(s.append(&json!({"value":1})).unwrap_err().0.contains("id"));
    let _ = std::fs::remove_file(p);
}

#[test]
fn concurrent_append() {
    let p = path("concurrent");
    let a = RecordStore::open(&p).unwrap();
    let b = RecordStore::open(&p).unwrap();
    std::thread::scope(|scope| {
        scope.spawn(|| a.append(&json!({"id":"a"})).unwrap());
        scope.spawn(|| b.append(&json!({"id":"b"})).unwrap());
    });
    let s = RecordStore::open(&p).unwrap();
    assert_eq!(s.list().len(), 2);
    let _ = std::fs::remove_file(p);
}
