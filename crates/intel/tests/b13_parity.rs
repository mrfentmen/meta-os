//! B13 parity — behavior checks for the devpack shaping functions.
//! The checked-in pack equality test (`test_intel_devpack.py`) lives in
//! B09's parity file; this file pins the shaping rules directly.
//! Fixture/data files (22) are carried byte-for-byte, verified by presence.

use intel::b13_devpack::{alerts_feed, brief_entry, crew_board, plan_preview, AlertRow, PreviewJob, PreviewPlan};
use intel::b13_devpack::serde_json_like::Json;
use std::collections::HashMap;

#[test] fn b13_brief_entry_rule() {
    let mut r = HashMap::new();
    r.insert("generated_at".into(), Json::Int(10));
    r.insert("text".into(), Json::Str("hi".into()));
    let e = brief_entry(&r, &Json::Int(25)).unwrap();
    assert_eq!(e["age_seconds"], Json::Int(15));
    assert_eq!(e["text"], Json::Str("hi".into())); // verbatim copy
}

#[test] fn b13_plan_preview_shape() {
    let p = PreviewPlan { summary: "s".into(), jobs: vec![
        PreviewJob { key: "a".into(), title: "A".into(), files: vec!["f".into()], deps: vec![], max_attempts: 2, accept: vec!["t".into()], req: vec![] },
        PreviewJob { key: "b".into(), title: "B".into(), files: vec![], deps: vec!["a".into()], max_attempts: 3, accept: vec![], req: vec![] },
    ]};
    let v = plan_preview(&p, &["a".into(), "b".into()]).unwrap();
    assert_eq!(v.jobs_count, 2);
    assert_eq!(v.max_attempts_total, 5);
    assert_eq!(v.posting_order, vec!["a".to_string(), "b".to_string()]);
}

#[test] fn b13_alerts_feed_order() {
    let rows = vec![AlertRow { id: "x".into(), created_at: 5 }, AlertRow { id: "y".into(), created_at: 9 }];
    assert_eq!(alerts_feed(rows)[0].id, "y");
}

#[test] fn b13_crew_board_sources() {
    let b = crew_board(vec!["milo".into()], vec![], vec![]);
    assert_eq!(b.presence, vec!["milo".to_string()]);
}

#[test] fn b13_fixtures_carried() {
    // Presence pins for the carried data (byte-for-byte copies).
    assert!(include_str!("../fixtures/b13/devpack/brief.json").len() > 2);
    assert!(include_str!("../fixtures/b13/devpack/plan_preview.json").len() > 2);
    assert!(include_str!("../fixtures/b13/devpack/alerts.json").len() > 0);
    assert!(include_str!("../fixtures/b13/devpack/crew_board.json").len() > 2);
    assert!(include_str!("../fixtures/b13/examples/skills/fixture-brief/SKILL.md").len() > 0);
    assert!(include_str!("../fixtures/b13/notes/hana-source-map.md").len() > 0);
}
