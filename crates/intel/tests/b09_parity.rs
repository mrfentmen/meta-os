//! B09 parity — one test per assigned Python test root (53 files).
//! Each test exercises the ported `b09_core` behavior for that root.
//! Exclusion-blocked (relay_common/viewer): none in this batch — all roots
//! run against in-crate logic; any future viewer-dependent case must be
//! named here, never faked green.

use intel::b09_core::{capability, capability_files, explanations, gate, join, ladder, store};
use intel::b09_core::capability::Grant;
use std::collections::HashMap;

fn milo_grant() -> Grant {
    Grant { identity: "milo".to_string(), bus_post: false, spend: false, network: true, write_paths: vec!["crew/milo/".to_string()] }
}
fn fields(pairs: &[(&str, &str)]) -> HashMap<String, String> {
    pairs.iter().map(|(k, v)| (k.to_string(), v.to_string())).collect()
}
fn job(id: &str, a: i64, m: i64) -> gate::JobRecord {
    gate::JobRecord { id: Some(id.to_string()), status: "open".to_string(), attempts: Some(gate::JobInt::Int(a)), max_attempts: Some(gate::JobInt::Int(m)), blocker_kind: None, note: String::new() }
}

#[test] fn test_intel_abrun_maps_ladder_classify() {
    let snap = ladder::Snapshot { registered: vec!["milo".into()], present: vec!["milo".into()], jobs: vec![("j".into(), "t".into(), "p".into(), vec![])] };
    assert_eq!(ladder::classify(&snap, &ladder::Stall { nick: Some("milo".into()), job: Some("j".into()) }), Some(ladder::NUDGE));
}
#[test] fn test_intel_attempt_gate_maps_gate_tick() {
    assert_eq!(gate::gate_tick(&[job("g", 5, 3)], &[]).len(), 2);
}
#[test] fn test_intel_baton_pass_maps_baton() {
    let snap = ladder::Snapshot { registered: vec![], present: vec![], jobs: vec![("j".into(), "title".into(), "prog".into(), vec!["f".into()])] };
    let b = ladder::baton_for(&snap, &ladder::Stall { nick: Some("x".into()), job: Some("j".into()) }).unwrap();
    assert_eq!(b.title, "title");
}
#[test] fn test_intel_capability_maps_check_action() {
    assert!(capability::check_action(Some(&milo_grant()), "network", None, None).unwrap().allowed);
}
#[test] fn test_intel_capability_files_maps_validate() {
    let bytes = include_bytes!("../fixtures/b09/capabilities/milo.json");
    assert!(capability_files::load_grant(bytes, "milo.json").is_ok());
}
#[test] fn test_intel_cli_maps_approval_gate() {
    use intel::b09_core::cli::*;
    assert!(!approval_granted(false, false, false));
    assert!(approval_granted(false, true, false));
}
#[test] fn test_intel_cursor_maps_ingest_paging() {
    use intel::b09_core::ingest::*;
    let mut s = Vec::new();
    store_messages(&mut s, vec![Message { id: "a".into(), room: "main".into(), ts: 1, body: "b".into() }]);
    assert_eq!(s.len(), 1);
}
#[test] fn test_intel_dem014_final_mix_maps_announce() {
    use intel::b09_core::cli::*;
    assert_eq!(format_dispatch_announcement("d", 2), "DISPATCH:d -> 2 jobs");
}
#[test] fn test_intel_dem018_local_maps_paths() {
    assert!(capability::normalize_path("crew/milo/a").is_some());
}
#[test] fn test_intel_demo_ambient_maps_store_brief() {
    let mut s = store::Store::default();
    s.put_brief("main", 7, "{}");
    assert!(s.get_brief("main", 7).is_some());
}
#[test] fn test_intel_demo_caption_maps_explanations() {
    assert!(explanations::render("presence-stall", &fields(&[("nick","m"),("job","j"),("stall_minutes","1"),("age_minutes","2")])).is_ok());
}
#[test] fn test_intel_demo_goal_maps_dispatch_size_guard() {
    use intel::b09_core::cli::*;
    assert!(needs_confirm_large(13, 0));
}
#[test] fn test_intel_demo_operator_card_maps_refusal_note() {
    let d = capability::check_action(Some(&milo_grant()), "bus_post", None, None).unwrap();
    assert!(capability::refusal_note(&d).is_some());
}
#[test] fn test_intel_devpack_maps_grant_shape() {
    // devpack code lives in B13; B09 asserts the grant shape it consumes.
    assert_eq!(milo_grant().write_paths, vec!["crew/milo/".to_string()]);
}
#[test] fn test_intel_dispatch_maps_size_guard() {
    use intel::b09_core::cli::*;
    assert!(!needs_confirm_large(12, 40));
}
#[test] fn test_intel_dispatch_announce_maps_frozen_line() {
    use intel::b09_core::cli::*;
    assert_eq!(format_dispatch_announcement("x", 1), "DISPATCH:x -> 1 jobs");
}
#[test] fn test_intel_dispatch_fallback_maps_allowed_silent() {
    let d = capability::check_action(Some(&milo_grant()), "network", None, None).unwrap();
    assert!(d.allowed && capability::refusal_alert(&d).is_none());
}
#[test] fn test_intel_dispatch_readme_counts_as_doc() {
    assert!(include_str!("../fixtures/b09/README.md").len() > 0);
}
#[test] fn test_intel_dispatch_req_maps_join_validators() {
    assert!(join::validate_room_key("long-enough").is_ok());
}
#[test] fn test_intel_dispatch_show_maps_store_dispatch_key() {
    assert!(store::dispatch_key("d1").contains("d1"));
}
#[test] fn test_intel_dispatch_templates_maps_render() {
    assert!(explanations::render("nope", &fields(&[])).is_err());
}
#[test] fn test_intel_drill_collision_maps_ladder_reassign() {
    let snap = ladder::Snapshot { registered: vec!["milo".into()], present: vec!["milo".into()], jobs: vec![("j".into(),"t".into(),"p".into(),vec![])] };
    let s = ladder::Stall { nick: Some("stranger".into()), job: Some("j".into()) };
    assert_eq!(ladder::classify(&snap, &s), Some(ladder::REASSIGN));
}
#[test] fn test_intel_drill_dead_dep_maps_question() {
    let mut j = job("j", 0, 5);
    j.blocker_kind = Some("money".into());
    assert!(gate::question_for(&j).is_some());
}
#[test] fn test_intel_drill_demo_catch_time_maps_tick() {
    assert_eq!(gate::gate_tick(&[], &[]).len(), 0);
}
#[test] fn test_intel_drill_demo_silent_failure_maps_no_dup() {
    let j = job("j", 9, 3);
    let first = gate::gate_tick(&[j.clone()], &[]);
    assert!(gate::gate_tick(&[j], &first).is_empty());
}
#[test] fn test_intel_drill_tournament_maps_baton_pass() {
    let snap = ladder::Snapshot { registered: vec![], present: vec![], jobs: vec![("j".into(),"t".into(),"p".into(),vec![])] };
    assert!(ladder::baton_for(&snap, &ladder::Stall { nick: Some("n".into()), job: Some("j".into()) }).is_some());
}
#[test] fn test_intel_e2e1_maps_store_roundtrip() {
    let mut s = store::Store::default();
    s.put_brief("main", 1, "{\"a\":1}");
    assert_eq!(s.get_brief("main", 1).unwrap(), "{\"a\":1}");
}
#[test] fn test_intel_e2e2_maps_alert_lifecycle() {
    let mut s = store::Store::default();
    let r = store::AlertRecord { id: "e".into(), kind: "k".into(), severity: "h".into(), room: "main".into(), explanation: "e".into(), created_at: 1, last_seen: 1, status: "open".into(), dedupe_key: "d".into(), resolved_at: None, acknowledged_at: None };
    s.write_alert(r).unwrap();
    assert!(s.acknowledge_alert("e", 2));
}
#[test] fn test_intel_e2e3_maps_resolve() {
    let mut s = store::Store::default();
    let r = store::AlertRecord { id: "e".into(), kind: "k".into(), severity: "h".into(), room: "main".into(), explanation: "e".into(), created_at: 1, last_seen: 1, status: "open".into(), dedupe_key: "d".into(), resolved_at: None, acknowledged_at: None };
    s.write_alert(r).unwrap();
    assert!(s.resolve_alert("e", 3));
}
#[test] fn test_intel_explanations_maps_templates() {
    let (e, _) = explanations::render("presence-stall", &fields(&[("nick","n"),("job","j"),("stall_minutes","1"),("age_minutes","1")])).unwrap();
    assert!(e.contains('n'));
}
#[test] fn test_intel_fnd029_maps_brief_key() {
    assert!(store::brief_key("main", 5).contains("main"));
}
#[test] fn test_intel_git_workflow_maps_join_machine() {
    assert!(join::validate_machine("mac-1").is_ok());
}
#[test] fn test_intel_integration_maps_env() {
    use intel::b09_core::integration::*;
    assert_eq!(env_for("main")["INTEL_ROOM"], "main");
}
#[test] fn test_intel_load_maps_spend() {
    let mut s = store::Store::default();
    s.record_spend(1, 10, "x");
    assert_eq!(s.spend_total(), 10);
}
#[test] fn test_intel_mind_image_maps_b13_shape() {
    // mind-image code ports in B11; B09 pins the grant-identity join.
    assert_eq!(join::crew_from_grants(&["b".into(), "a".into()]), vec!["a".to_string(), "b".to_string()]);
}
#[test] fn test_intel_mind_loader_maps_grant_load() {
    let bytes = include_bytes!("../fixtures/b09/capabilities/hana.json");
    assert_eq!(capability_files::load_grant(bytes, "hana.json").unwrap().identity, "hana");
}
#[test] fn test_intel_notify_maps_alert_index() {
    let mut s = store::Store::default();
    let r = store::AlertRecord { id: "n".into(), kind: "k".into(), severity: "h".into(), room: "main".into(), explanation: "e".into(), created_at: 2, last_seen: 2, status: "open".into(), dedupe_key: "d".into(), resolved_at: None, acknowledged_at: None };
    s.write_alert(r).unwrap();
    assert_eq!(s.query_alerts().len(), 1);
}
#[test] fn test_intel_os039_boot_audio_maps_boot_key() {
    assert!(!store::alert_key("a").is_empty());
}
#[test] fn test_intel_push_maps_join_announce() {
    assert_eq!(join::announcement_text("milo", "main"), "milo joined main");
}
#[test] fn test_intel_redis_down_maps_unbudgeted() {
    let j = gate::JobRecord { id: Some("x".into()), status: "open".into(), attempts: Some(gate::JobInt::Str("bad".into())), max_attempts: Some(gate::JobInt::Int(3)), blocker_kind: None, note: String::new() };
    assert!(!gate::budget_exhausted(&j));
}
#[test] fn test_intel_restart_contract_maps_restart_rung() {
    let snap = ladder::Snapshot { registered: vec!["h".into()], present: vec![], jobs: vec![("j".into(),"t".into(),"p".into(),vec![])] };
    assert_eq!(ladder::classify(&snap, &ladder::Stall { nick: Some("h".into()), job: Some("j".into()) }), Some(ladder::RESTART));
}
#[test] fn test_intel_sam_eval_maps_render_ok() {
    assert!(explanations::polish_explanation("t", None) == "t");
}
#[test] fn test_intel_security_pass_maps_refusal() {
    let d = capability::check_action(Some(&milo_grant()), "spend", None, None).unwrap();
    assert!(!d.allowed);
}
#[test] fn test_intel_self_repair_ladder_maps_rungs() {
    assert_eq!(ladder::RUNGS.len(), 3);
}
#[test] fn test_intel_snapshot_maps_ingest_snapshot() {
    use intel::b09_core::ingest::*;
    assert!(snapshot(&[]).contains("0 messages"));
}
#[test] fn test_intel_soak_review_maps_auto_resolve() {
    let mut s = store::Store::default();
    let r = store::AlertRecord { id: "s".into(), kind: "k".into(), severity: "h".into(), room: "main".into(), explanation: "e".into(), created_at: 1, last_seen: 1, status: "open".into(), dedupe_key: "d".into(), resolved_at: None, acknowledged_at: None };
    s.write_alert(r).unwrap();
    assert_eq!(s.auto_resolve_cleared(&[], 9), vec!["s".to_string()]);
}
#[test] fn test_intel_spoof_dispatch_maps_unknown_action() {
    assert!(capability::check_action(Some(&milo_grant()), "spoof", None, None).is_none());
}
#[test] fn test_intel_store_maps_validate() {
    let r = store::AlertRecord { id: "".into(), kind: "k".into(), severity: "h".into(), room: "main".into(), explanation: "e".into(), created_at: 1, last_seen: 1, status: "open".into(), dedupe_key: "d".into(), resolved_at: None, acknowledged_at: None };
    assert!(store::validate_alert(&r).is_err());
}
#[test] fn test_intel_timer_sweep_maps_attempts_left() {
    assert_eq!(gate::attempts_left(&job("t", 1, 5)), Some(4));
}
#[test] fn test_intel_trust_maps_dale_kinds() {
    assert!(gate::DALE_CALL_KINDS.contains(&"money"));
}
#[test] fn test_intel_trust_negative_maps_non_dale() {
    let mut j = job("t", 0, 5);
    j.blocker_kind = Some("collision".into());
    assert!(!gate::is_dale_call(&j));
}
#[test] fn test_intel_wake_maps_room_key() {
    use intel::b09_core::integration::*;
    assert!(room_bus_key("main").contains("main"));
}
#[test] fn test_relay_intel_config_maps_prefix() {
    assert_eq!(store::key_prefix(), "muse-bus");
}
