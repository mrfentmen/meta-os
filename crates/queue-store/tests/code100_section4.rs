//! CB-037: reopening a store preserves order and count.

use queue_store::{JobStore, SqliteStore};
use serde_json::json;
use std::time::{SystemTime, UNIX_EPOCH};

fn temp_db() -> std::path::PathBuf {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    std::env::temp_dir().join(format!(
        "queue-store-code100-{}-{nanos}.db",
        std::process::id()
    ))
}

#[test]
fn reopen_preserves_order_and_count() {
    let path = temp_db();
    {
        let mut jobs = JobStore::new(
            SqliteStore::open(path.to_str().unwrap()).expect("open sqlite store"),
            "trio-code100",
        );
        for id in ["a", "b", "c"] {
            assert_eq!(
                jobs.submit(&json!({"id": id})),
                (id.to_string(), true)
            );
        }
    }

    let mut reopened = JobStore::new(
        SqliteStore::open(path.to_str().unwrap()).expect("reopen sqlite store"),
        "trio-code100",
    );
    let open = reopened.open_job_ids();
    assert_eq!(open, vec!["a", "b", "c"]);
    assert_eq!(
        reopened.job_fields("b").get("status").map(String::as_str),
        Some("open")
    );
    assert_eq!(reopened.open_job_ids().len(), 3);

    let _ = std::fs::remove_file(&path);
}
