//! CB2-335..337 — guardrail ceiling, cumulative spend, and trip/reset.

use guardrail::{
    check, estimate, load_state, record_at, save_state, GuardrailState, TEST_BUDGET_USD,
};

fn path(tag: &str) -> String {
    let n = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    std::env::temp_dir()
        .join(format!("guardrail-{tag}-{}-{n}.json", std::process::id()))
        .to_string_lossy()
        .into_owned()
}

#[test]
fn guardrail_ceiling_boundary() {
    let mut state = GuardrailState::default();
    state.est_cost_usd = TEST_BUDGET_USD - 0.000_001;
    assert!(check(&state).is_ok(), "one micro-dollar under the ceiling passes");
    state.est_cost_usd = TEST_BUDGET_USD;
    assert!(check(&state).is_err(), "exactly at the ceiling trips");
    state.est_cost_usd = TEST_BUDGET_USD + 0.01;
    assert!(check(&state).is_err(), "over the ceiling trips");
}

#[test]
fn guardrail_cumulative() {
    // 200k in + 100k out per call = $0.25 + $0.425 = $0.675.
    // Five calls total $3.375.
    assert!((estimate(200_000, 100_000) - 0.675).abs() < 1e-12);
    let p = path("cumulative");
    for _ in 0..5 {
        record_at(
            &p,
            "2026-11-02T00:00:00Z",
            "2026-11-02T00:00:00Z",
            "chat",
            "muse-spark-1.3",
            200_000,
            100_000,
            10,
        )
        .unwrap();
    }
    let state = load_state(&p);
    assert_eq!(state.calls, 5);
    assert!((state.est_cost_usd - 3.375).abs() < 1e-9, "got {}", state.est_cost_usd);
    assert_eq!(state.log.len(), 5);
    assert!((state.log[4].cum_est_cost_usd - 3.375).abs() < 1e-9);
    let _ = std::fs::remove_file(&p);
}

#[test]
fn guardrail_tripped_refuses() {
    let p = path("trip");
    let mut state = GuardrailState::default();
    state.est_cost_usd = TEST_BUDGET_USD;
    save_state(&p, &state);
    assert!(check(&load_state(&p)).is_err(), "tripped state refuses");
    assert!(record_at(
        &p,
        "2026-11-02T00:00:00Z",
        "2026-11-02T00:00:00Z",
        "chat",
        "muse-spark-1.3",
        1,
        1,
        1,
    )
    .is_ok(), "record_at does not itself gate; check() is the gate");
    // Reset: write a zero ledger, then the guard passes again.
    save_state(&p, &GuardrailState::default());
    assert!(check(&load_state(&p)).is_ok());
    let _ = std::fs::remove_file(&p);
}
