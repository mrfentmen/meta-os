// CB-035 — a future spend timestamp is flagged and never filed.
use guardrail::{load_state, record_at};

#[test]
fn future_timestamp_is_refused_and_ledger_is_untouched() {
    let dir = std::env::temp_dir().join(format!("guardrail-future-{}", std::process::id()));
    let _ = std::fs::create_dir_all(&dir);
    let path = dir.join("guard.json").to_string_lossy().to_string();
    let _ = std::fs::remove_file(&path);

    let err = record_at(
        &path,
        "2099-01-01T00:00:00Z",
        "2026-11-02T00:00:00Z",
        "assess:ignis",
        "muse-spark-1.3",
        1000,
        1000,
        42,
    )
    .unwrap_err();
    assert!(err.to_string().contains("future"));
    assert_eq!(load_state(&path).calls, 0);
}

#[test]
fn current_timestamp_is_filed() {
    let dir = std::env::temp_dir().join(format!("guardrail-current-{}", std::process::id()));
    let _ = std::fs::create_dir_all(&dir);
    let path = dir.join("guard.json").to_string_lossy().to_string();
    let _ = std::fs::remove_file(&path);

    let est = record_at(
        &path,
        "2026-11-02T00:00:00Z",
        "2026-11-02T00:00:00Z",
        "assess:ignis",
        "muse-spark-1.3",
        1000,
        1000,
        42,
    )
    .unwrap();
    assert!(est > 0.0);
    assert_eq!(load_state(&path).calls, 1);
}
