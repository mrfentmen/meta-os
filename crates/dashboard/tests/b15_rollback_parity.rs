//! B15 parity — INT-031 rollback pins not covered by `b15_parity.rs`.
//!
//! Ports the remaining cases from `os/tests/test_dashboard_rollback_int031.py`
//! (T241) against the carried runbook fixture (byte-identical to
//! `os/docs/DEPLOY_RUNBOOK.md`). The two exact-steps / valid-target /
//! docs-citation / id-addressed cases already live in `b15_parity.rs`
//! via `rollback_runbook_ok`; these five are the ones that did not:
//! the no-invented-id rule, the unconfirmed project restore, the
//! failover-card copy, the previous-batch marker, and the
//! no-credentials rule.

/// Mirrors Python `\b[0-9a-f]{8,}\b`: a token of 8+ lowercase hex chars.
/// Splitting on non-word characters is exactly equivalent here: any 8+
/// hex run inside a token is either the whole token (a match) or cut by
/// a non-hex word character (no word boundary, no match).
fn has_invented_id(span: &str) -> bool {
    span.split(|ch: char| !(ch.is_ascii_alphanumeric() || ch == '_'))
        .any(|token| {
            token.len() >= 8
                && token
                    .chars()
                    .all(|ch| ch.is_ascii_hexdigit() && !ch.is_ascii_uppercase())
        })
}

fn runbook() -> &'static str {
    include_str!("../fixtures/DEPLOY_RUNBOOK.md")
}

/// The id field must not carry a plausible-looking identifier next to it.
#[test]
fn test_rollback_previous_id_no_invented_id() {
    let text = runbook();
    let marker = "Previous production deployment id";
    assert!(text.contains(marker), "id field missing");
    assert!(
        text.contains("not yet recorded"),
        "id field must say not yet recorded"
    );
    // Python takes the id line plus the following line; check that span.
    let start = text.find(marker).unwrap();
    let rest = &text[start..];
    let span = match rest.find('\n') {
        Some(first) => match rest[first + 1..].find('\n') {
            Some(second) => &rest[..first + 1 + second],
            None => rest,
        },
        None => rest,
    };
    assert!(
        !has_invented_id(span),
        "invented-looking id in the acceptance field"
    );
}

/// The project restore half stays marked unconfirmed.
#[test]
fn test_rollback_project_restore_still_marked_unconfirmed() {
    let text = runbook();
    assert!(text.contains("INT-031"), "INT-031 pin missing");
    assert!(text.contains("unconfirmed"), "restore must stay unconfirmed");
}

/// Failover-card copy must be present with the live pages URL.
#[test]
fn test_rollback_failover_card_copy_present() {
    let text = runbook();
    assert!(text.contains("Failover-card copy"), "failover-card copy missing");
    assert!(
        text.contains("https://muse-relay-live.pages.dev"),
        "live pages URL missing"
    );
}

/// Rollback is verified by the previous batch's marker.
#[test]
fn test_rollback_verified_by_previous_marker() {
    assert!(
        runbook().contains("previous batch's marker"),
        "previous-batch marker missing"
    );
}

/// No credential material may be recorded in the runbook.
#[test]
fn test_rollback_no_credential_recorded() {
    let text = runbook();
    for forbidden in ["api_token", "CF_API_TOKEN", "Bearer "] {
        assert!(
            !text.contains(forbidden),
            "credential material recorded: {forbidden}"
        );
    }
}
