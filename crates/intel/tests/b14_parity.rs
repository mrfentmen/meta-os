//! B14 parity — trust/timer/launch behavior (mirrors `test_intel_trust.py`
//! in B09 and `test_os102_launch_run.py` in B31 against these modules).

use intel::b14_trust::{launch_run, timer_sweep, trust};
use std::collections::HashMap;

fn trust_setup() -> (trust::JobInput, trust::TrustList, HashMap<String, String>) {
    let job = trust::JobInput {
        id: Some("j".into()),
        status: "open".into(),
        kid: Some("crew-a".into()),
        sig_version: Some(2),
        signature: None,
        body: "work".into(),
        nonce: Some("n".into()),
        issued_at: Some(100),
        expires_at: Some(9999),
        badge_claims: vec![],
    };
    let tl = trust::TrustList { trusted_kids: vec!["crew-a".into()], allowed_badges: Some(vec!["agent".into()]) };
    let kr = HashMap::from([("crew-a".into(), "s3cret".into())]);
    (job, tl, kr)
}

#[test] fn test_intel_trust_unsigned_refused() {
    let (j, t, k) = trust_setup();
    let d = trust::claim_decision(&j, &t, &k, 200).unwrap();
    assert!(!d.claimable && d.reason.as_deref() == Some("signature absent"));
}

#[test] fn test_intel_trust_negative_spoof_refused() {
    let (mut j, t, k) = trust_setup();
    j.kid = Some("milo".into());
    j.sig_version = Some(2);
    j.signature = Some(trust::recompute_sig("x", "j", "milo", "work", "n", 100));
    assert!(!trust::claim_decision(&j, &t, &k, 200).unwrap().claimable);
}

#[test] fn test_intel_trust_tick_dedupes() {
    let (mut j, t, k) = trust_setup();
    j.signature = Some(trust::recompute_sig("s3cret", "j", "crew-a", "work", "n", 100));
    // badge clamping still applies on the passing decision
    let d = trust::claim_decision(&j, &t, &k, 200).unwrap();
    assert!(d.claimable);
    let unsigned = trust::JobInput { signature: None, ..j.clone() };
    let r1 = trust::trust_tick(&[unsigned.clone()], &t, &k, &[], 200);
    assert_eq!(r1.len(), 1);
    let r2 = trust::trust_tick(&[unsigned], &t, &k, &[r1[0].dedupe_key.clone()], 200);
    assert!(r2.is_empty());
}

#[test] fn test_intel_timer_sweep_dead_claims() {
    let jobs = vec![timer_sweep::SweepJob { id: Some("a".into()), status: "open".into(), posted_at: Some(1), addressed_to: Some("m".into()) }];
    let t = timer_sweep::sweep_cycle(&jobs, &["m".into()], &[], None, 500, 300, Some(false));
    assert_eq!(t.claimed, vec!["a".to_string()]);
}

#[test] fn test_os102_launch_run_verify_first() {
    struct Bad;
    impl launch_run::Verifier for Bad {
        fn verify(&self, _: &str) -> launch_run::VerifyReport {
            launch_run::VerifyReport { ok: false, errors: vec!["e".into()] }
        }
    }
    assert!(launch_run::run_from_launch(&Bad, "/l", &["x".into()], true, true).is_err());
}

#[test] fn test_demo_env_profile_carried() {
    let env = include_str!("../fixtures/b14/metaos-demo.env");
    assert!(env.contains("WATCHDOG_STALL_MINUTES=1")); // demo-shortened
    assert!(env.contains("DEMO_TICK_INTERVAL_SECONDS=5"));
    assert!(env.contains("WATCHDOG_BEAT_TTL_SECONDS=300")); // unchanged production value listed
}
