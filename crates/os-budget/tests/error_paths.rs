//! Error-path tests (B062): every refusal and failure branch the crate
//! documents gets a test that proves the refusal it describes.
//!
//! Integration tests use only the public surface. The one file-read
//! branch lives behind a private seam and is pinned by the unit test
//! `missing_dispatch_is_an_error` in `src/lib.rs`.

use os_budget::*;
use std::collections::{BTreeMap, HashMap, HashSet};

fn close(a: f64, b: f64) -> bool {
    (a - b).abs() < 1e-9
}

fn budget_entry(lane: &str, spent: Value, cap: Value) -> Value {
    v_dict(vec![("lane", v_str(lane)), ("spent", spent), ("cap", cap)])
}

fn cost_row(call: &str, count_base: i64, cost_worst: f64) -> CostRow {
    CostRow {
        call: call.to_string(),
        count_base,
        count_worst: 1,
        tokens_in: 0,
        tokens_out_expected: 0,
        tokens_out_worst: 0,
        cost_expected: 0.0,
        cost_worst,
    }
}

fn summary(passed: bool) -> CostSummary {
    CostSummary {
        expected_usd: 0.0,
        worst_usd: 0.0,
        worst_with_boot_usd: 0.0,
        reserved_half_usd: 75.0,
        credit_usd: 150.0,
        headroom_vs_reserved_usd: 75.0,
        breakeven_multiplier_vs_reserved: 0,
        passed,
    }
}

// --- budgets ---------------------------------------------------------

#[test]
fn env_int_refuses_blank_bad_and_out_of_range() {
    // Every bad shape falls back; none raises and none invents a value.
    assert_eq!(env_int_value(None, 80, 1, 100), 80);
    assert_eq!(env_int_value(Some(""), 80, 1, 100), 80);
    assert_eq!(env_int_value(Some("   "), 80, 1, 100), 80);
    assert_eq!(env_int_value(Some("eighty"), 80, 1, 100), 80);
    assert_eq!(env_int_value(Some("0"), 80, 1, 100), 80);
    assert_eq!(env_int_value(Some("101"), 80, 1, 100), 80);
    assert_eq!(env_int_value(Some("-1"), 80, 1, 100), 80);
    assert_eq!(env_int_value(Some(" 100 "), 80, 1, 100), 100);
}

#[test]
fn spend_ratio_refuses_non_int_zero_cap_and_negative() {
    assert_eq!(spend_ratio(&Value::Bool(true), &v_int(100)), None);
    assert_eq!(spend_ratio(&Value::Float(50.0), &v_int(100)), None);
    assert_eq!(spend_ratio(&v_str("80"), &v_int(100)), None);
    assert_eq!(spend_ratio(&v_int(80), &v_str("100")), None);
    assert_eq!(spend_ratio(&v_int(50), &v_int(0)), None);
    assert_eq!(spend_ratio(&v_int(50), &v_int(-1)), None);
    assert_eq!(spend_ratio(&v_int(-5), &v_int(100)), None);
}

#[test]
fn budget_gate_never_warns_or_holds_malformed_figures() {
    // Strings, floats, nulls, zero caps and negative spend are all
    // unbudgeted: no warning, no hold, claims allowed.
    for (spent, cap) in [
        (v_str("80"), v_str("100")),
        (Value::Float(80.0), v_int(100)),
        (v_int(80), v_int(0)),
        (v_int(-5), v_int(100)),
        (Value::Null, Value::Null),
    ] {
        assert!(!at_warning(&spent, &cap, None));
        assert!(!at_cap(&spent, &cap));
        assert!(claim_allowed(&spent, &cap));
        assert_eq!(budget_state(&budget_entry("x", spent, cap)), "unbudgeted");
    }
}

#[test]
fn budgets_from_snapshot_skips_bad_entries() {
    let snap = v_dict(vec![(
        "budgets",
        Value::List(vec![
            budget_entry("ok", v_int(1), v_int(2)),
            v_str("not-a-dict"),
            v_dict(vec![("spent", v_int(1)), ("cap", v_int(2))]),
            budget_entry("", v_int(1), v_int(2)),
        ]),
    )]);
    let entries = budgets_from_snapshot(&snap);
    assert_eq!(entries.len(), 1);
    assert_eq!(entries[0].get("lane"), Some(&v_str("ok")));
    assert!(budgets_from_snapshot(&v_dict(vec![("budgets", v_str("nope"))])).is_empty());
}

// --- forecast --------------------------------------------------------

#[test]
fn forecast_refuses_unprojectable_inputs() {
    assert_eq!(project_end_of_day(&v_int(-1), &v_int(8), &v_int(24)), None);
    assert_eq!(project_end_of_day(&v_int(80), &v_int(0), &v_int(24)), None);
    assert_eq!(project_end_of_day(&v_int(80), &v_int(-1), &v_int(24)), None);
    assert_eq!(project_end_of_day(&v_int(80), &v_int(8), &v_int(0)), None);
    assert_eq!(project_end_of_day(&v_str("x"), &v_int(8), &v_int(24)), None);
    assert_eq!(confidence_for(&v_int(0)), "unknown");
    assert_eq!(confidence_for(&v_str("soon")), "unknown");
    assert_eq!(
        forecast_entry(&v_str(""), &v_int(80), &v_int(100), &v_int(8), &v_int(24)),
        None
    );
    assert_eq!(
        forecast_entry(&v_str("x"), &v_int(80), &v_int(0), &v_int(8), &v_int(24)),
        None
    );
    assert_eq!(
        forecast_entry(&v_str("x"), &Value::Null, &v_int(100), &v_int(8), &v_int(24)),
        None
    );
}

#[test]
fn preempt_refuses_every_other_state() {
    let running_low = v_dict(vec![("status", v_str("running")), ("priority", v_str("low"))]);
    let running_high = v_dict(vec![("status", v_str("running")), ("priority", v_str("high"))]);
    let paused_low = v_dict(vec![("status", v_str("paused")), ("priority", v_str("low"))]);
    for lane in ["ok", "capped", "unbudgeted"] {
        assert_eq!(preempt_decision(&running_low, lane), None, "lane={}", lane);
    }
    assert_eq!(preempt_decision(&running_high, "warning"), None);
    for lane in ["warning", "capped"] {
        assert_eq!(preempt_decision(&paused_low, lane), None, "lane={}", lane);
    }
    assert_eq!(preempt_decision(&Value::Null, "warning"), None);
    assert_eq!(
        preempt_decision(&v_dict(vec![("status", v_str("running"))]), "warning"),
        None
    );
}

// --- gate and spend line ---------------------------------------------

#[test]
fn spend_line_refuses_entries_without_a_usable_figure() {
    assert_eq!(budget_spend_line(&v_str("nope"), ""), None);
    assert_eq!(budget_spend_line(&v_dict(vec![("spent", v_int(1))]), ""), None);
    assert_eq!(
        budget_spend_line(&v_dict(vec![("lane", v_str("")), ("spent", v_int(1))]), ""),
        None
    );
    assert_eq!(
        budget_spend_line(&v_dict(vec![("lane", v_str("x"))]), ""),
        None
    );
}

#[test]
fn fake_queue_refuses_claim_at_cap_and_keeps_job_open() {
    let mut queue = FakeQueue::new();
    queue.post("1", "spark");
    assert!(queue.claim("1", &v_int(99), &v_int(100)));
    queue.post("2", "spark");
    assert!(!queue.claim("2", &v_int(100), &v_int(100)));
    assert_eq!(queue.status_of("2").as_deref(), Some("open"));
    assert_eq!(queue.holds, vec!["2".to_string()]);
    assert_eq!(queue.status_of("missing"), None);
}

// --- cost tables -----------------------------------------------------

#[test]
fn bad_rate_falls_back_to_default() {
    assert_eq!(rate_value(None, 3.0, "X"), (3.0, "default".to_string()));
    assert_eq!(rate_value(Some(""), 3.0, "X"), (3.0, "default".to_string()));
    assert_eq!(rate_value(Some("junk"), 3.0, "X"), (3.0, "default".to_string()));
    assert_eq!(rate_value(Some(" 2.5 "), 3.0, "X"), (2.5, "env:X".to_string()));
}

#[test]
#[should_panic(expected = "boot row")]
fn cost_totals_panics_without_a_boot_row() {
    // The Python original raises IndexError here; the Rust panics with
    // a named message. Both refuse; neither invents a total (finding:
    // a Result would be kinder, see the gap list).
    let _ = cost_totals(&vec![cost_row("core", 1, 1.0)]);
}

#[test]
fn breach_flips_passed_and_headroom() {
    let rows = vec![cost_row("core", 1, 100.0), cost_row("boot", 0, 75.0)];
    let totals = cost_totals(&rows);
    assert!(!totals.passed);
    assert!(totals.worst_with_boot_usd > totals.reserved_half_usd);
    assert!(close(totals.headroom_vs_reserved_usd, -100.0));
    assert_eq!(totals.breakeven_multiplier_vs_reserved, 0);
}

#[test]
fn render_tables_mark_fail_for_breach() {
    let sources = BTreeMap::from([
        ("in".to_string(), "default".to_string()),
        ("out".to_string(), "default".to_string()),
    ]);
    let table = render_cost_table(&vec![cost_row("core", 1, 0.0)], &summary(false), 3.0, 15.0, &sources);
    assert!(table.contains("FAIL"));
    assert!(!table.contains("PASS"));

    let rows = vec![BriefCostRow {
        variant: "breach".to_string(),
        jobs: 22,
        template_words: 200,
        template_actual_usd: 0.0,
        tokens_in: 1,
        tokens_out_expected: 1,
        tokens_out_worst: 1,
        cost_expected: 0.0,
        cost_worst: 100.0,
        rate_sources: BTreeMap::new(),
    }];
    let (text, passed) = render_brief_cost_table(&rows, 3.0, 15.0);
    assert!(!passed);
    assert!(text.contains("FAIL"));
    assert!(text.contains("no ledger entry written"));
}

// --- audit -----------------------------------------------------------

#[test]
fn parse_artifact_ref_refuses_every_malformed_shape() {
    for bad in [
        "",
        "artifact:",
        "artifact:job",
        "artifact:job/",
        "artifact:/out@v1",
        "artifact:job/out",
        "artifact:job/out@v",
        "artifact:job/out@vx",
        "artifact:job/@v1",
        "not-artifact:job/out@v1",
    ] {
        assert_eq!(parse_artifact_ref(bad), None, "accepted {:?}", bad);
    }
    assert_eq!(
        parse_artifact_ref("artifact:job/out@v2"),
        Some(("job".to_string(), "out".to_string(), 2))
    );
}

#[test]
fn audit_refuses_non_list_records() {
    let stores = FakeStores::default();
    assert_eq!(
        audit(&stores, &stores, &v_str("not a list")),
        Err("job records must be a list".to_string())
    );
}

#[test]
fn unreadable_artifact_store_is_a_leak() {
    let mut stores = FakeStores::default();
    stores.unreadable_store_jobs.insert("job-1".to_string());
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
    assert!(!result.passed);
    assert!(result.leaks.iter().any(|l| {
        l.get("layer") == Some(&v_str("artifacts"))
            && matches!(l.get("detail"), Some(Value::Str(d)) if d.contains("store unreadable"))
    }));
}

#[test]
fn unreadable_journal_is_one_leak_per_agent() {
    let mut stores = FakeStores::default();
    stores.agent_journal_errors.insert("milo".to_string());
    let mut jobs = Vec::new();
    for id in ["a", "b"] {
        jobs.push(v_dict(vec![
            ("id", v_str(id)),
            ("status", v_str("claimed")),
            ("title", v_str("T")),
            ("spec", v_str("Goal: g")),
            ("claim", v_str("milo")),
            ("decisions", Value::List(vec![v_str("k")])),
        ]));
    }
    let result = audit(&stores, &stores, &Value::List(jobs)).unwrap();
    let journal_leaks = result
        .leaks
        .iter()
        .filter(|l| l.get("layer") == Some(&v_str("memory-journal")))
        .count();
    assert_eq!(journal_leaks, 1);
}

#[test]
fn audit_files_record_and_spec_leaks() {
    let stores = FakeStores::default();
    let records = Value::List(vec![
        v_str("not-a-dict"),
        v_dict(vec![("status", v_str("open"))]),
        v_dict(vec![
            ("id", v_str("job-1")),
            ("status", v_str("claimed")),
            ("spec", v_str("S")),
        ]),
    ]);
    let result = audit(&stores, &stores, &records).unwrap();
    assert!(!result.passed);
    let layers: Vec<String> = result
        .leaks
        .iter()
        .filter_map(|l| match l.get("layer") {
            Some(Value::Str(s)) => Some(s.clone()),
            _ => None,
        })
        .collect();
    assert_eq!(layers.iter().filter(|l| l.as_str() == "record").count(), 2);
    assert!(layers.contains(&"spec".to_string()));
    assert!(layers.contains(&"baton".to_string()));
    assert!(layers.contains(&"claim".to_string()));
}

// --- cgroup ----------------------------------------------------------

#[test]
fn slice_mismatch_fails_file_phase() {
    assert!(!slice_file_passes(&parse_slice("[Slice]\nCPUQuota=50%\nMemoryMax=1G\n")));
    assert!(!slice_file_passes(&parse_slice("[Slice]\nCPUQuota=100%\n")));
    assert!(!slice_file_passes(&parse_slice("")));
    // Values outside [Slice] are not values.
    assert!(!slice_file_passes(&parse_slice("[Service]\nCPUQuota=100%\nMemoryMax=1G\n")));
}

#[test]
fn cgroup_gate_reports_missing_controllers() {
    assert!(cgroup_gate_missing(Some("cpu memory pids")).is_empty());
    assert_eq!(cgroup_gate_missing(Some("cpu")), vec!["memory".to_string()]);
    assert_eq!(cgroup_gate_missing(Some("")), vec!["cpu".to_string(), "memory".to_string()]);
    assert_eq!(cgroup_gate_missing(None), vec!["cpu".to_string(), "memory".to_string()]);
}

// --- empty inputs ----------------------------------------------------

#[test]
fn empty_snapshot_is_unbudgeted_not_zero() {
    let empty = v_dict(vec![]);
    assert!(budgets_from_snapshot(&empty).is_empty());
    assert!(claim_allowed(&Value::Null, &Value::Null));
    assert_eq!(budget_state(&empty), "unbudgeted");
    assert!(!at_warning(&Value::Null, &Value::Null, None));
    assert!(!at_cap(&Value::Null, &Value::Null));
}

#[test]
fn empty_snapshot_yields_empty_sections() {
    let empty = v_dict(vec![]);
    assert_eq!(message_parts(&Value::Null), (String::new(), String::new()));
    assert!(extract_decisions(&empty).is_empty());
    assert!(extract_owners(&empty).is_empty());
    assert!(extract_blocked(&empty).is_empty());
    assert!(extract_watch_items(&empty).is_empty());
    assert!(forecast_lines(&Value::List(vec![])).is_empty());
    assert!(budget_warning_alerts(&empty, 0).is_empty());
    let brief = morning_template_brief(&empty, "morning");
    assert!(brief.starts_with("TEMPLATE"));
    assert!(brief.contains("Nothing reported in this window"));
}

#[test]
fn audit_empty_list_passes_vacuously() {
    let stores = FakeStores::default();
    let result = audit(&stores, &stores, &Value::List(vec![])).unwrap();
    assert!(result.passed);
    assert!(result.jobs.is_empty());
    assert!(result.decisions.is_empty());
    assert!(result.leaks.is_empty());
}

// --- compile-time sanity for the fixtures used above -----------------

#[test]
fn fixtures_used_by_this_file_are_the_public_shapes() {
    let _: HashMap<String, Vec<String>> = HashMap::new();
    let _: HashSet<String> = HashSet::new();
    assert_eq!(CREDIT_USD, 150.0);
    assert_eq!(RESERVED_HALF_USD, 75.0);
}
