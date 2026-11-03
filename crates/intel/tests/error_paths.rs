//! B170 — refusal paths across intel's public surface.
//!
//! Each test pins the exact refusal the code produces today, with the
//! message the caller sees. Where a branch is unreachable from the
//! public API (private parser internals), it is named in
//! `os-build/records/intel.md` instead of being simulated here.
use std::collections::HashMap;

use intel::b09_core::capability::{check_action, Grant};
use intel::b09_core::explanations::render;
use intel::b09_core::gate::{as_int, JobInt};
use intel::b09_core::join::{
    validate_machine, validate_room_address, validate_room_key, validate_trusted_kids,
};
use intel::b09_core::store::{validate_alert, AlertRecord, Store};
use intel::b10_brief::brief::{
    failure_copy_for_kind, parse_since, validate_brief_record, BriefRecord,
};
use intel::b10_brief::dispatch::{
    check_dep_graph, check_file_overlap, check_no_secrets, parse_plan, Plan, PlanJob,
};
use intel::b10_brief::push::{build_push, validate_push, JobView, Push};
use intel::b11_spark::spark_client::{
    complete, CompletionRequest, SparkError, StubTransport, TransportKind,
};
use intel::b13_devpack::{
    brief_entry, plan_preview, serde_json_like::Json, PreviewJob, PreviewPlan,
};

fn plan_job(key: &str, files: &[&str], deps: &[&str]) -> PlanJob {
    PlanJob {
        key: key.to_string(),
        title: format!("job {key}"),
        files: files.iter().map(|f| f.to_string()).collect(),
        deps: deps.iter().map(|d| d.to_string()).collect(),
        max_attempts: 3,
        // The shape-only parser fills neither: spec and accept stay empty
        // unless a fuller parse reads them.
        spec: String::new(),
        accept: Vec::new(),
    }
}

fn plan(jobs: Vec<PlanJob>) -> Plan {
    Plan { goal: "goal".to_string(), jobs }
}

fn alert(id: &str) -> AlertRecord {
    AlertRecord {
        id: id.to_string(),
        kind: "presence-stall".to_string(),
        severity: "critical".to_string(),
        room: "main".to_string(),
        explanation: "worker absent".to_string(),
        created_at: 10,
        last_seen: 0,
        status: String::new(),
        dedupe_key: format!("d:{id}"),
        resolved_at: None,
        acknowledged_at: None,
    }
}

#[test]
fn parse_plan_refuses_empty_goal_unknown_fields_and_blank_jobs() {
    assert_eq!(parse_plan("", vec![], &[]).unwrap_err().0, "missing goal");
    assert_eq!(
        parse_plan("g", vec![], &["extra".to_string()]).unwrap_err().0,
        "unknown fields: extra"
    );
    assert_eq!(
        parse_plan("g", vec![("k".to_string(), " ".to_string())], &[])
            .unwrap_err()
            .0,
        "job needs key + title"
    );
}

#[test]
fn file_overlap_refused_unless_a_dependency_orders_the_jobs() {
    let mut jobs = vec![
        plan_job("a", &["shared.rs"], &[]),
        plan_job("b", &["shared.rs"], &["a"]),
    ];
    assert!(check_file_overlap(&plan(jobs.clone())).is_ok());
    jobs[1].deps.clear();
    let err = check_file_overlap(&plan(jobs)).unwrap_err();
    assert_eq!(err.0, "file overlap on shared.rs: a vs b");
}

#[test]
fn dependency_graph_refuses_unknown_deps_and_cycles() {
    let unknown = plan(vec![plan_job("a", &[], &["ghost"])]);
    assert_eq!(
        check_dep_graph(&unknown).unwrap_err().0,
        "unknown dep ghost in a"
    );
    let cycle = plan(vec![
        plan_job("a", &[], &["b"]),
        plan_job("b", &[], &["a"]),
    ]);
    assert_eq!(check_dep_graph(&cycle).unwrap_err().0, "dependency cycle");
}

#[test]
fn secret_scan_refuses_each_marker() {
    for marker in ["BEGIN PRIVATE KEY", "sk-live", "api_token"] {
        let err = check_no_secrets(&format!("body {marker} body")).unwrap_err();
        assert_eq!(err.0, "plan carries a possible secret");
    }
}

#[test]
fn since_parser_refuses_malformed_windows() {
    for bad in ["bogus", "-1", "10x", "1.5h", ""] {
        let err = parse_since(bad, 1000).unwrap_err();
        assert_eq!(err, format!("bad --since: {bad}"));
    }
}

#[test]
fn brief_validation_refuses_each_missing_field_and_unknown_kind() {
    let ok = BriefRecord {
        room: "main".to_string(),
        ts: 1,
        text: "text".to_string(),
        kind: "morning".to_string(),
    };
    assert!(validate_brief_record(&ok).is_ok());
    assert_eq!(
        validate_brief_record(&BriefRecord { room: String::new(), ..ok.clone() }).unwrap_err(),
        "brief: missing room"
    );
    assert_eq!(
        validate_brief_record(&BriefRecord { ts: -1, ..ok.clone() }).unwrap_err(),
        "brief: bad ts"
    );
    assert_eq!(
        validate_brief_record(&BriefRecord { text: "   ".to_string(), ..ok.clone() }).unwrap_err(),
        "brief: empty text"
    );
    assert_eq!(
        validate_brief_record(&BriefRecord { kind: "nope".to_string(), ..ok }).unwrap_err(),
        "brief: unknown kind nope"
    );
}

#[test]
fn failure_copy_refuses_an_unknown_kind() {
    assert_eq!(
        failure_copy_for_kind("other").unwrap_err(),
        "unknown brief failure kind: 'other'"
    );
}

#[test]
fn push_builders_refuse_unknown_types_and_invalid_records() {
    let job = JobView {
        id: "j".to_string(),
        title: "T".to_string(),
        status: "done".to_string(),
        verified: true,
        note: String::new(),
    };
    assert_eq!(
        build_push("other", &job, None, None).unwrap_err(),
        "unknown push type: other"
    );
    let bad_type = Push {
        push_type: "nope".to_string(),
        job_id: "j".to_string(),
        title: "T".to_string(),
        text: "x".to_string(),
    };
    assert_eq!(validate_push(&bad_type).unwrap_err(), "bad push type: nope");
    let missing = Push { push_type: "done".to_string(), job_id: String::new(), title: String::new(), text: String::new() };
    assert_eq!(validate_push(&missing).unwrap_err(), "push missing job/text");
}

#[test]
fn devpack_refuses_non_int_timestamps_and_incomplete_order() {
    let mut no_generated = HashMap::new();
    no_generated.insert("text".to_string(), Json::Str("x".to_string()));
    assert!(brief_entry(&no_generated, &Json::Int(10)).is_err());

    let mut string_generated = HashMap::new();
    string_generated.insert("generated_at".to_string(), Json::Str("10".to_string()));
    assert!(brief_entry(&string_generated, &Json::Int(10)).is_err());

    let mut good = HashMap::new();
    good.insert("generated_at".to_string(), Json::Int(10));
    assert_eq!(
        brief_entry(&good, &Json::Str("10".to_string())).unwrap_err().0,
        "as_of must be an int epoch timestamp"
    );

    let preview = PreviewPlan {
        summary: "s".to_string(),
        jobs: vec![PreviewJob {
            key: "a".to_string(),
            title: "A".to_string(),
            files: vec![],
            deps: vec![],
            max_attempts: 3,
            accept: vec![],
            req: vec![],
        }],
    };
    assert_eq!(
        plan_preview(&preview, &["b".to_string()]).unwrap_err().0,
        "posting order must cover exactly the plan jobs"
    );
}

#[test]
fn alert_validation_refuses_each_required_field() {
    assert!(validate_alert(&alert("a")).is_ok());
    let cases: [(&str, AlertRecord); 4] = [
        ("alert: missing id", AlertRecord { id: String::new(), ..alert("a") }),
        ("alert: missing kind", AlertRecord { kind: String::new(), ..alert("a") }),
        ("alert: missing explanation", AlertRecord { explanation: String::new(), ..alert("a") }),
        ("alert: missing dedupe_key", AlertRecord { dedupe_key: String::new(), ..alert("a") }),
    ];
    for (expected, record) in cases {
        assert_eq!(validate_alert(&record).unwrap_err(), expected);
    }
    let mut store = Store::default();
    assert!(store.write_alert(AlertRecord { kind: String::new(), ..alert("b") }).is_err());
}

#[test]
fn gate_reads_bools_floats_and_decimal_strings_as_unbudgeted() {
    assert_eq!(as_int(&JobInt::Bool(true)), None);
    assert_eq!(as_int(&JobInt::Float(2.0)), None);
    assert_eq!(as_int(&JobInt::Str("2.5".to_string())), None);
    assert_eq!(as_int(&JobInt::Str("1e3".to_string())), None);
    assert_eq!(as_int(&JobInt::Str(String::new())), None);
    assert_eq!(as_int(&JobInt::Int(-1)), None);
    assert_eq!(as_int(&JobInt::Str("3".to_string())), Some(3));
}

#[test]
fn join_validators_refuse_bad_machine_room_key_and_kids() {
    assert!(validate_machine("").is_err());
    assert!(validate_machine(&"a".repeat(65)).is_err());
    assert!(validate_machine("bad space").is_err());
    assert!(validate_room_address("https://relay").is_err());
    assert!(validate_room_address("").is_err());
    assert!(validate_room_key("short").is_err());
    assert!(validate_trusted_kids(&[String::new()]).is_err());
    assert!(validate_machine("milo-box").is_ok());
}

#[test]
fn explanations_refuse_unknown_templates_and_missing_placeholders() {
    assert_eq!(
        render("nope", &HashMap::new()).unwrap_err(),
        "unknown template: nope"
    );
    let err = render("presence-stall", &HashMap::new()).unwrap_err();
    assert!(err.starts_with("missing placeholder: "), "got {err}");
}

#[test]
fn capability_refuses_missing_grant_missing_flag_and_outside_path() {
    let no_grant = check_action(None, "write_file", Some("ok/a.rs"), None).unwrap();
    assert!(!no_grant.allowed);
    assert_eq!(no_grant.reason.as_deref(), Some("no capability grant on file"));

    assert!(check_action(None, "dance", None, None).is_none());

    let grant = Grant {
        identity: "milo".to_string(),
        bus_post: false,
        spend: true,
        network: false,
        write_paths: vec!["workspace".to_string()],
    };
    let flag_off = check_action(Some(&grant), "bus_post", None, None).unwrap();
    assert!(!flag_off.allowed);
    assert_eq!(flag_off.reason.as_deref(), Some("capability not granted"));

    let escape = check_action(Some(&grant), "write_file", Some("../etc/passwd"), None).unwrap();
    assert!(!escape.allowed);
    assert_eq!(escape.reason.as_deref(), Some("write path outside grant"));

    let inside = check_action(Some(&grant), "write_file", Some("workspace/a.rs"), None).unwrap();
    assert!(inside.allowed);
}

#[test]
fn spark_transport_and_cap_refuse_before_any_call() {
    assert!(matches!(
        TransportKind::from_env("pigeon"),
        Err(SparkError::NotConfigured(_))
    ));
    assert!(matches!(TransportKind::from_env("http"), Ok(TransportKind::Http)));

    let stub = StubTransport::default();
    let req = CompletionRequest {
        lane_feature: "l".to_string(),
        system: "s".to_string(),
        prompt: "p".to_string(),
        max_tokens: 8,
        job_ns: "n".to_string(),
    };
    assert!(matches!(
        complete(&stub, &TransportKind::Http, &req, 75.0, 75.0),
        Err(SparkError::Budget(_))
    ));
}
