//! B15 crewboard parity (T237) — the rule halves of the five
//! `test_crewboard_*.py` files, checked against their exact fixture
//! values. The card/detail HTML rendering halves stay
//! exclusion-blocked: they drive the fold-excluded `crew-board.html`
//! through a Node driver, which this crate does not reproduce.
//! Also still blocked, named here: the OS-084 JSON-string-field
//! parse (viewer Redis-hash handling), the live attach() cross-check
//! (real `mos/artifact_store` deposits), and the signing test's
//! `admin.py` keyless-verify cross-check (B26's contract, not this
//! crate's) — the entry shapes themselves are ported below.

use dashboard::contract::*;

// ---- test_crewboard_alert_ribbon.py (DSH-025) ----

fn alert(id: &str, severity: &str, subjects: &[&str]) -> CrewAlert {
    CrewAlert {
        id: Some(id.into()),
        kind: "stall".into(),
        severity: severity.into(),
        status: None,
        resolved_at: None,
        subjects: subjects.iter().map(|s| s.to_string()).collect(),
    }
}

#[test]
fn test_crewboard_ribbon_bare_subject_links_to_alert() {
    let r = alert_ribbon("42", &[alert("alert:1", "critical", &["milo", "42"])]).unwrap();
    assert_eq!(r.text, "critical alert: stall");
    assert_eq!(r.href.as_deref(), Some("bus.html#intel/alert/alert%3A1"));
}

#[test]
fn test_crewboard_ribbon_job_form_matches_case_insensitively() {
    let r = alert_ribbon("42", &[alert("alert:2", "critical", &["Job 42"])]).unwrap();
    assert_eq!(r.href.as_deref(), Some("bus.html#intel/alert/alert%3A2"));
}

#[test]
fn test_crewboard_ribbon_uppercase_severity_matches() {
    let r = alert_ribbon("42", &[alert("alert:3", "CRITICAL", &["42"])]).unwrap();
    assert_eq!(r.href.as_deref(), Some("bus.html#intel/alert/alert%3A3"));
}

#[test]
fn test_crewboard_ribbon_warning_and_info_get_none() {
    assert!(alert_ribbon("42", &[alert("alert:4", "warning", &["42"])]).is_none());
    assert!(alert_ribbon("42", &[alert("alert:5", "info", &["42"])]).is_none());
}

#[test]
fn test_crewboard_ribbon_resolved_gets_none() {
    let mut resolved = alert("alert:6", "critical", &["42"]);
    resolved.status = Some("resolved".into());
    assert!(alert_ribbon("42", &[resolved]).is_none());
    let mut legacy = alert("alert:7", "critical", &["42"]);
    legacy.resolved_at = Some(1700000100);
    assert!(alert_ribbon("42", &[legacy]).is_none());
}

#[test]
fn test_crewboard_ribbon_acknowledged_keeps_ribbon() {
    let mut acked = alert("alert:8", "critical", &["42"]);
    acked.status = Some("acknowledged".into());
    let r = alert_ribbon("42", &[acked]).unwrap();
    assert_eq!(r.href.as_deref(), Some("bus.html#intel/alert/alert%3A8"));
}

#[test]
fn test_crewboard_ribbon_other_job_and_no_alerts_get_none() {
    assert!(alert_ribbon("42", &[alert("alert:9", "critical", &["7"])]).is_none());
    assert!(alert_ribbon("42", &[]).is_none());
}

#[test]
fn test_crewboard_ribbon_without_id_has_no_link() {
    let mut no_id = alert("alert:1", "critical", &["42"]);
    no_id.id = None;
    let r = alert_ribbon("42", &[no_id]).unwrap();
    assert_eq!(r.text, "critical alert: stall");
    assert!(r.href.is_none());
}

#[test]
fn test_crewboard_ribbon_kind_and_id_are_escaped() {
    let mut escaped = alert("alert:<x>", "critical", &["42"]);
    escaped.kind = "<b>".into();
    let r = alert_ribbon("42", &[escaped]).unwrap();
    assert_eq!(r.text, "critical alert: &lt;b&gt;");
    assert!(!r.text.contains("<b>"));
    assert_eq!(
        r.href.as_deref(),
        Some("bus.html#intel/alert/alert%3A%3Cx%3E")
    );
}

#[test]
fn test_crewboard_ribbon_first_matching_critical_wins() {
    let mut second = alert("alert:11", "critical", &["42"]);
    second.kind = "collision".into();
    let r = alert_ribbon(
        "42",
        &[alert("alert:10", "critical", &["42"]), second],
    )
    .unwrap();
    assert_eq!(r.text, "critical alert: stall");
    assert!(!r.text.contains("collision"));
}

// ---- test_crewboard_attempts.py (DSH-024) ----

#[test]
fn test_crewboard_attempts_thresholds() {
    let zero = attempts_badge(Some("0"), Some("3")).unwrap();
    assert_eq!(zero.text, "attempts 0/3");
    assert_eq!(zero.class, "pill attempts");
    let one = attempts_badge(Some("1"), Some("3")).unwrap();
    assert_eq!(one.class, "pill attempts");
    let warn = attempts_badge(Some("2"), Some("3")).unwrap();
    assert_eq!(warn.text, "attempts 2/3");
    assert_eq!(warn.class, "pill attempts warn");
    let maxed = attempts_badge(Some("3"), Some("3")).unwrap();
    assert_eq!(maxed.class, "pill attempts danger");
    let over = attempts_badge(Some("5"), Some("3")).unwrap();
    assert_eq!(over.text, "attempts 5/3");
    assert_eq!(over.class, "pill attempts danger");
}

#[test]
fn test_crewboard_attempts_absent_blank_junk_no_badge() {
    assert!(attempts_badge(None, None).is_none());
    assert!(attempts_badge(Some(""), Some("")).is_none());
    assert!(attempts_badge(Some("two"), Some("three")).is_none());
    assert!(attempts_badge(Some("1"), None).is_none());
}

// ---- test_crewboard_files_deps.py (DSH-023) ----

#[test]
fn test_crewboard_files_and_deps_lines() {
    assert_eq!(
        files_line(Some("intel/a.py, intel/b.py")).as_deref(),
        Some("files: intel/a.py, intel/b.py")
    );
    assert_eq!(
        deps_line(Some("3, 7")).as_deref(),
        Some("deps: #3, #7")
    );
}

#[test]
fn test_crewboard_files_deps_old_and_blank_render_nothing() {
    assert!(files_line(None).is_none());
    assert!(deps_line(None).is_none());
    assert!(files_line(Some(" , ")).is_none());
    assert!(deps_line(Some("")).is_none());
}

#[test]
fn test_crewboard_files_names_escaped() {
    assert_eq!(
        files_line(Some("<b>&amp;</b>")).as_deref(),
        Some("files: &lt;b&gt;&amp;amp;&lt;/b&gt;")
    );
}

// ---- test_crewboard_os084_artifacts.py (artifact part) ----

fn artifact(path: &str, reference: &str, version: i64) -> Artifact {
    Artifact {
        path: Some(path.into()),
        reference: reference.into(),
        version,
        sha256: "aa".into(),
    }
}

#[test]
fn test_crewboard_artifact_links_store_paths() {
    let first = artifact_link(&artifact(
        "jobs/42/report.md",
        "artifact:42/report.md@v2",
        2,
    ))
    .unwrap();
    assert_eq!(first.href, "jobs/42/report.md");
    assert_eq!(first.title, "artifact:42/report.md@v2");
    assert_eq!(first.label, "report.md v2");
    let second = artifact_link(&artifact(
        "jobs/42/notes/out.txt",
        "artifact:42/notes/out.txt@v1",
        1,
    ))
    .unwrap();
    assert_eq!(second.href, "jobs/42/notes/out.txt");
    assert_eq!(second.label, "out.txt v1");
}

#[test]
fn test_crewboard_artifact_old_job_has_no_links() {
    let links: Vec<ArtifactLink> = Vec::new()
        .iter()
        .filter_map(|a: &Artifact| artifact_link(a))
        .collect();
    assert!(links.is_empty());
}

#[test]
fn test_crewboard_artifact_bad_paths_dropped() {
    assert!(artifact_link(&artifact("../escape.txt", "artifact:11/escape.txt@v1", 1)).is_none());
    assert!(artifact_link(&artifact("/abs.txt", "artifact:11/abs.txt@v1", 1)).is_none());
    assert!(artifact_link(&Artifact {
        path: None,
        reference: "artifact:11/nopath@v1".into(),
        version: 1,
        sha256: "gg".into(),
    })
    .is_none());
    assert!(artifact_link(&artifact("jobs/11/ok.txt", "artifact:11/ok.txt@v1", 1)).is_some());
}

#[test]
fn test_crewboard_artifact_paths_escaped() {
    let link = artifact_link(&artifact(
        "jobs/12/<b>.txt",
        "artifact:12/<b>.txt@v1",
        1,
    ))
    .unwrap();
    assert_eq!(link.href, "jobs/12/&lt;b&gt;.txt");
    assert!(!link.href.contains("<b>"));
}

// ---- test_crewboard_signing.py (keyless interop) ----

#[test]
fn test_crewboard_signing_pystr_matches_json_dumps() {
    let cases: &[(&str, &str)] = &[
        ("plain", "\"plain\""),
        ("quote \" and backslash \\", "\"quote \\\" and backslash \\\\\""),
        (
            "line1\nline2\ttab\rcarriage",
            "\"line1\\nline2\\ttab\\rcarriage\"",
        ),
        ("café", "\"caf\\u00e9\""),
        ("emoji 😀", "\"emoji \\ud83d\\ude00\""),
        ("", "\"\""),
        ("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\""),
    ];
    for (input, want) in cases {
        assert_eq!(py_str_json(input), *want, "pyStr mismatch for {input:?}");
    }
    // DEL passes through raw under ensure_ascii, like Python's dumps.
    assert_eq!(py_str_json("del\u{7f}"), "\"del\u{7f}\"");
}

#[test]
fn test_crewboard_signing_nonce_shape() {
    assert!(is_nonce_hex("0123456789abcdef"));
    assert!(!is_nonce_hex("0123456789ABCDEF"));
    assert!(!is_nonce_hex("0123456789abcde"));
}

#[test]
fn test_crewboard_signing_log_entry_is_keyless_json() {
    let entry = RenameLogEntry {
        actor: "Mrfentmen".into(),
        nick: "alice".into(),
        display: "Alice Cooper".into(),
    };
    let json = entry.to_json();
    assert!(json.contains("\"v\":1"));
    assert!(json.contains("\"cmd\":\"rename\""));
    assert!(json.contains("\"nick\":\"alice\""));
    assert!(json.contains("\"display\":\"Alice Cooper\""));
    assert!(json.contains("\"actor\":\"Mrfentmen\""));
    assert!(!json.contains("sig"));
}

#[test]
fn test_crewboard_signing_hash_and_history_entry_shapes() {
    let hash = NamesHashEntry {
        display: "Alice Cooper".into(),
        set_by: "Mrfentmen".into(),
        set_at: 1758390000,
    };
    assert_eq!(
        hash.to_json(),
        "{\"display\":\"Alice Cooper\",\"set_by\":\"Mrfentmen\",\"set_at\":1758390000}"
    );
    let hist = NamesHistoryEntry {
        nick: "alice".into(),
        display: "Alice Cooper".into(),
        set_by: "Mrfentmen".into(),
        set_at: 1758390000,
    };
    assert_eq!(
        hist.to_json(),
        "{\"nick\":\"alice\",\"display\":\"Alice Cooper\",\"set_by\":\"Mrfentmen\",\"set_at\":1758390000}"
    );
}
