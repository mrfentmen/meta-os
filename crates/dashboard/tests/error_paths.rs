//! B146 — error-path tests for the dashboard contract.
//!
//! Every refusal branch the crate exposes returns `Result<_, String>`
//! or `Option<_>`; this file pins the exact message or `None` each one
//! produces. Branches that panic (the WCAG helper on a short colour)
//! are pinned as panics, because that is what the code does today.

use dashboard::contract::*;

fn good_payload() -> BriefPayload {
    BriefPayload {
        id: "brief:main:100".into(),
        room: "main".into(),
        kind: "morning".into(),
        generated_at: 100,
        age_seconds: 10,
        template: false,
    }
}

// ---- brief payload refusals (contract.rs:49-62) ----

#[test]
fn bad_brief_kind_is_refused_with_the_kind_named() {
    let mut p = good_payload();
    p.kind = "evening".into();
    assert_eq!(
        validate_brief_payload(&p),
        Err("bad brief kind: evening".to_string())
    );
}

#[test]
fn bad_brief_id_is_refused_with_the_id_named() {
    let mut p = good_payload();
    p.id = "brief:other:100".into();
    assert_eq!(
        validate_brief_payload(&p),
        Err("bad brief id: brief:other:100".to_string())
    );
}

#[test]
fn empty_room_is_refused() {
    let p = BriefPayload {
        id: "brief::100".into(),
        room: String::new(),
        ..good_payload()
    };
    assert_eq!(
        validate_brief_payload(&p),
        Err("bad brief timestamps".to_string())
    );
}

#[test]
fn negative_generated_at_is_refused() {
    let mut p = good_payload();
    p.generated_at = -1;
    p.id = "brief:main:-1".into();
    assert_eq!(
        validate_brief_payload(&p),
        Err("bad brief timestamps".to_string())
    );
}

#[test]
fn negative_age_is_refused() {
    let mut p = good_payload();
    p.age_seconds = -5;
    assert_eq!(
        validate_brief_payload(&p),
        Err("bad brief timestamps".to_string())
    );
}

// ---- rollback runbook refusals (contract.rs:377-405) ----

const STEPS: &str = "Deployments All deployments Rollback to this deployment muse-relay-live";
const TARGET: &str = "Only successfully built deployments.";
const PREVIEW: &str = "Preview deployments are **not** valid rollback targets.";
const DOCS: &str = "https://developers.cloudflare.com/pages/configuration/rollbacks/";
const ID_FIELD: &str = "Previous production deployment id: not recorded.";

fn full_runbook() -> String {
    format!("{STEPS} {TARGET} {PREVIEW} {DOCS} {ID_FIELD}")
}

#[test]
fn a_complete_runbook_is_accepted() {
    assert_eq!(rollback_runbook_ok(&full_runbook()), Ok(()));
}

#[test]
fn every_missing_step_names_itself() {
    for step in ROLLBACK_STEPS.iter().copied() {
        let text = full_runbook().replace(step, "x");
        assert_eq!(
            rollback_runbook_ok(&text),
            Err(format!("missing rollback step: {step}"))
        );
    }
}

#[test]
fn missing_valid_target_rule_is_refused() {
    let text = full_runbook().replace("successfully built", "built");
    assert_eq!(
        rollback_runbook_ok(&text),
        Err("missing valid-target rule".to_string())
    );
}

#[test]
fn missing_preview_rule_is_refused() {
    let text = full_runbook().replace("Preview deployments are **not** valid", "Previews");
    assert_eq!(
        rollback_runbook_ok(&text),
        Err("missing preview-invalid rule".to_string())
    );
}

#[test]
fn missing_docs_citation_is_refused() {
    let text = full_runbook().replace(DOCS, "");
    assert_eq!(
        rollback_runbook_ok(&text),
        Err("missing official docs citation".to_string())
    );
}

#[test]
fn missing_id_field_is_refused() {
    let text = full_runbook().replace("Previous production deployment id", "id");
    assert_eq!(
        rollback_runbook_ok(&text),
        Err("previous deployment id not explicitly addressed".to_string())
    );
}

#[test]
fn an_empty_runbook_fails_on_the_first_step() {
    assert_eq!(
        rollback_runbook_ok(""),
        Err("missing rollback step: Deployments".to_string())
    );
}

// ---- panel error rows (contract.rs:339-349) ----

#[test]
fn token_rejection_names_the_panel_and_the_fix() {
    let row = error_row("brief", &SourceError::TokenRejected);
    assert!(row.contains("can't read brief"));
    assert!(row.contains("Paste a token above to load brief."));
}

#[test]
fn unreachable_names_the_panel_and_spares_the_log() {
    let row = error_row("alerts", &SourceError::Unreachable);
    assert!(row.contains("Can't reach the bus store"));
    assert!(row.contains("alerts is paused"));
    assert!(row.contains("The log above is unaffected."));
}

// ---- badge parsing refusals (contract.rs:508-527) ----

#[test]
fn unparseable_attempts_have_no_badge() {
    assert!(attempts_badge(Some("one"), Some("3")).is_none());
    assert!(attempts_badge(
        Some("999999999999999999999999"),
        Some("3")
    )
    .is_none());
}

// ---- artifact links refuse unsafe paths (contract.rs:585-604) ----

fn artifact(path: Option<&str>) -> Artifact {
    Artifact {
        path: path.map(str::to_string),
        reference: "artifact:1/x@v1".into(),
        version: 1,
        sha256: "aa".into(),
    }
}

#[test]
fn unsafe_or_missing_artifact_paths_are_dropped() {
    assert!(artifact_link(&artifact(None)).is_none());
    assert!(artifact_link(&artifact(Some("/abs/x.txt"))).is_none());
    assert!(artifact_link(&artifact(Some("../x.txt"))).is_none());
    assert!(artifact_link(&artifact(Some("jobs//x.txt"))).is_none());
    assert!(artifact_link(&artifact(Some(""))).is_none());
}

// ---- deep links refuse anything not intel ----

#[test]
fn non_intel_and_id_less_deep_links_are_none() {
    assert_eq!(parse_deep_link("intel/brief/1"), None); // no '#'
    assert_eq!(parse_deep_link("#other/brief/1"), None);
    assert_eq!(parse_deep_link("#intel/other/1"), None);
    assert_eq!(parse_deep_link("#intel/brief/"), None);
    assert_eq!(parse_deep_link("#intel/alert/"), None);
    assert_eq!(parse_deep_link("#"), None);
}

// ---- WCAG helper: the real failure mode is a panic ----

#[test]
#[should_panic]
fn a_short_colour_panics_in_the_wcag_helper() {
    // contract.rs:105-116 slices hex[1..3], hex[3..5], hex[5..7]
    // with no length guard; "#fff" is a real crash, not an Err.
    let _ = wcag_luminance("#fff");
}

#[test]
fn non_hex_digits_read_as_zero_channels() {
    // from_str_radix(...).unwrap_or(0) turns junk into black, silently.
    assert_eq!(wcag_luminance("#zzzzzz"), 0.0);
    assert_eq!(wcag_contrast_ratio("#zzzzzz", "#zzzzzz"), 1.0);
}
