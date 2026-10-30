//! B12a parity — behavior-for-behavior: every drill/check `run()` passes.
//! No test files are assigned to B12a in the batch map; the drill-acceptance
//! halves (attempt budgets, baton, capability, ladder, brief naming) are
//! exercised here against the ported code. B09-owned test roots
//! (`test_intel_abrun`, `test_intel_drill_*`, …) exercise the same gates
//! from the caller side.

use intel::b12a_drills::*;

#[test] fn b12a_all_drills_pass() {
    let reports = vec![
        drills::ab_run::run(),
        drills::attempt_gate::run(),
        drills::baton_pass::run(),
        drills::boot_selfcheck::run(),
        drills::boot_status::run(),
        drills::capability_refusal::run(),
        drills::collision::run(),
        drills::dead_dep::run(),
        drills::demo_catch_time::run(),
        drills::demo_silent_failure::run(),
        drills::demo_thresholds_dropin::run(),
        drills::journal_watch::run(),
        drills::power_cut::run(),
        drills::restart_contract::run(),
        drills::self_repair_ladder::run(),
        drills::soak_review::run(),
        drills::timer_sweep::run(),
        drills::tournament::run(),
        drills::trust_enforcement::run(),
        drills::trust_negative::run(),
        drills::wake::run(),
    ];
    for r in &reports {
        assert!(r.ok(), "{} FAILED: {}", r.drill, r.pass_line());
    }
    assert_eq!(reports.len(), 21);
}

#[test] fn b12a_all_checks_pass() {
    let reports = vec![
        abrun::run(),
        boot_audio_check::run(),
        boot_selfcheck::run(),
        dem018_local_check::run(),
        e2e2::run(),
        e2e3::run(),
        watchdog_tuning::run(),
        final_mix_check::run(),
        load_check::run(),
        redis_down_drill::run(),
        sam_check::run(),
        security_pass::run(),
        soak_review::run(),
        spark_down_drill::run(),
        spoof_dispatch_drill::run(),
    ];
    for r in &reports {
        assert!(r.ok(), "{} FAILED: {}", r.drill, r.pass_line());
    }
    // e2e1 scenario one
    let e1 = e2e1::run_loop("e2e1", &[("j1".to_string(), "open".to_string())]);
    assert!(e1.ok());
    // sam_render shape
    assert!(sam_render::render(&[("p".into(), "q".into(), "pass".into())]).contains("## p"));
}
