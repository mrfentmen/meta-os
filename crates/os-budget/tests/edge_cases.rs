//! Edge-case tests (B063): empty, maximum, duplicate, out-of-order.
//!
//! One test per named case, as the task asks. Where the Rust answer
//! differs from the Python original, the assertion pins the CURRENT
//! Rust behaviour and the comment names the divergence (the gap list
//! carries the task).

use os_budget::*;
use std::collections::HashMap;

fn budget_entry(lane: &str, spent: i64, cap: i64) -> Value {
    v_dict(vec![
        ("lane", v_str(lane)),
        ("spent", v_int(spent)),
        ("cap", v_int(cap)),
    ])
}

fn clean_job(id: &str) -> Value {
    v_dict(vec![
        ("id", v_str(id)),
        ("status", v_str("open")),
        ("title", v_str("T")),
        ("spec", v_str("S")),
    ])
}

// --- empty -----------------------------------------------------------

#[test]
fn empty_input_is_handled_everywhere() {
    assert_eq!(parse_slice(""), Vec::<(String, String)>::new());
    assert_eq!(parse_artifact_ref(""), None);
    assert_eq!(project_end_of_day(&Value::Null, &Value::Null, &Value::Null), None);
    assert_eq!(estimate_tokens(""), 0);
    assert_eq!(trim_to_budget("", 10), "");
    assert_eq!(redact_secrets(""), "");
    assert!(forecast_lines(&Value::List(vec![])).is_empty());
    assert!(extract_decisions(&v_dict(vec![])).is_empty());
    assert!(message_parts(&v_str("")).0.is_empty());
    assert_eq!(message_parts(&v_str("")).1, "");

    let capped = cap_snapshot_window(&v_dict(vec![]), 500, 24, 0.0);
    let window = capped.get("source_window").expect("window record");
    assert_eq!(window.get("messages_kept"), Some(&v_int(0)));
    assert_eq!(window.get("messages_dropped"), Some(&v_int(0)));
}

// --- maximum ---------------------------------------------------------

#[test]
fn maximum_input_stays_finite() {
    let max = i64::MAX;
    assert_eq!(spend_ratio(&v_int(max), &v_int(max)), Some(1.0));
    assert!(at_cap(&v_int(max), &v_int(max)));
    assert!(!at_warning(&v_int(max), &v_int(max), None));
    assert!(!claim_allowed(&v_int(max), &v_int(max)));

    // Elapsed at or past the day returns spent itself; no multiplication
    // overflow path because the early return is taken first.
    assert_eq!(
        project_end_of_day(&v_int(max), &v_int(max), &v_int(24)),
        Some(max as f64)
    );

    // A long lane name is carried verbatim, not truncated.
    let lane = "x".repeat(1000);
    let line = budget_spend_line(&hold_entry(&lane, v_int(1), v_int(2)), "").unwrap();
    assert!(line.contains(&lane));

    // i64::MAX figures are still JSON-shaped numbers in the record.
    let held = hold_entry("max", v_int(max), v_int(max));
    assert_eq!(held.get("spent"), Some(&v_int(max)));
    assert_eq!(held.get("held"), Some(&Value::Bool(true)));
}

// --- duplicate -------------------------------------------------------

#[test]
fn duplicate_input_is_kept_and_deduped_where_documented() {
    // Budgets: both entries survive extraction; the detector files one
    // warning per lane per tick.
    let snap = v_dict(vec![(
        "budgets",
        Value::List(vec![
            budget_entry("spark", 80, 100),
            budget_entry("spark", 90, 100),
        ]),
    )]);
    assert_eq!(budgets_from_snapshot(&snap).len(), 2);
    assert_eq!(budget_warning_alerts(&snap, 1).len(), 1);

    // Decisions: duplicate markers are both kept, in order.
    let messages = v_dict(vec![(
        "messages",
        Value::List(vec![
            v_str("a: DONE: one"),
            v_str("b: DONE: two"),
        ]),
    )]);
    assert_eq!(extract_decisions(&messages).len(), 2);

    // Audit: the same decision key twice is verified twice, not deduped.
    let mut stores = FakeStores::default();
    stores.shared_keys = vec!["k".to_string()];
    let job = v_dict(vec![
        ("id", v_str("job-1")),
        ("status", v_str("open")),
        ("title", v_str("T")),
        ("spec", v_str("S")),
        ("decisions", Value::List(vec![v_str("k"), v_str("k")])),
    ]);
    let result = audit(&stores, &stores, &Value::List(vec![job])).unwrap();
    assert_eq!(
        result.jobs[0].get("decisions"),
        Some(&Value::List(vec![v_str("k"), v_str("k")]))
    );

    // Duplicate slice keys: Rust keeps the FIRST. Python's dict parse
    // keeps the LAST (gap list item 17), so this assertion documents a
    // real divergence rather than claiming parity.
    let slice = parse_slice("[Slice]\nMemoryMax=1G\nMemoryMax=2G\n");
    assert_eq!(slice_value(&slice, "MemoryMax"), Some("1G"));

    // Duplicate manifest names: Rust's `find` keeps the FIRST entry.
    // Python's dict keeps the LAST (gap list item 15).
    let mut manifests: HashMap<String, Vec<ArtifactEntry>> = HashMap::new();
    manifests.insert(
        "job-1".to_string(),
        vec![
            ArtifactEntry {
                name: "out".to_string(),
                version: 1,
            },
            ArtifactEntry {
                name: "out".to_string(),
                version: 2,
            },
        ],
    );
    let stores = FakeStores {
        manifests,
        ..Default::default()
    };
    let job = v_dict(vec![
        ("id", v_str("job-9")),
        ("status", v_str("open")),
        ("title", v_str("T")),
        ("spec", v_str("S")),
        (
            "artifacts",
            Value::List(vec![v_str("artifact:job-1/out@v1")]),
        ),
    ]);
    let result = audit(&stores, &stores, &Value::List(vec![job])).unwrap();
    assert!(result.passed);
}

// --- out of order ----------------------------------------------------

#[test]
fn out_of_order_input_keeps_input_order() {
    // Budgets keep the snapshot's order.
    let snap = v_dict(vec![(
        "budgets",
        Value::List(vec![
            budget_entry("zeta", 1, 10),
            budget_entry("alpha", 2, 10),
        ]),
    )]);
    let lanes: Vec<String> = budgets_from_snapshot(&snap)
        .iter()
        .filter_map(|e| match e.get("lane") {
            Some(Value::Str(s)) => Some(s.clone()),
            _ => None,
        })
        .collect();
    assert_eq!(lanes, vec!["zeta".to_string(), "alpha".to_string()]);

    // Forecast lines keep the entries' order.
    let entries = Value::List(vec![
        v_dict(vec![
            ("lane", v_str("zeta")),
            ("spent", v_int(10)),
            ("cap", v_int(100)),
            ("elapsed_hours", v_int(8)),
        ]),
        v_dict(vec![
            ("lane", v_str("alpha")),
            ("spent", v_int(20)),
            ("cap", v_int(100)),
            ("elapsed_hours", v_int(8)),
        ]),
    ]);
    let lines = forecast_lines(&entries);
    assert_eq!(lines.len(), 2);
    assert!(lines[0].contains("lane zeta"));
    assert!(lines[1].contains("lane alpha"));

    // Owners appear in first-claim order, not alphabetical.
    let jobs = v_dict(vec![
        (
            "jobs",
            Value::List(vec![
                v_dict(vec![
                    ("id", v_str("1")),
                    ("title", v_str("one")),
                    ("status", v_str("claimed")),
                    ("claim", v_str("zed")),
                ]),
                v_dict(vec![
                    ("id", v_str("2")),
                    ("title", v_str("two")),
                    ("status", v_str("claimed")),
                    ("claim", v_str("amy")),
                ]),
            ]),
        ),
    ]);
    let owners = extract_owners(&jobs);
    assert_eq!(owners[0].get("nick"), Some(&v_str("zed")));
    assert_eq!(owners[1].get("nick"), Some(&v_str("amy")));

    // The audit's reconstructed jobs keep the input record order.
    let stores = FakeStores::default();
    let result = audit(
        &stores,
        &stores,
        &Value::List(vec![clean_job("z"), clean_job("a")]),
    )
    .unwrap();
    assert_eq!(result.jobs[0].get("id"), Some(&v_str("z")));
    assert_eq!(result.jobs[1].get("id"), Some(&v_str("a")));

    // Slice lines keep file order in the Vec.
    let values = parse_slice("[Slice]\nMemoryMax=1G\nCPUQuota=100%\n");
    assert_eq!(values[0].0, "MemoryMax");
    assert_eq!(values[1].0, "CPUQuota");
}
