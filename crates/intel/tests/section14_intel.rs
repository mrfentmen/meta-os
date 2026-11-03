//! CB2-338/339/340 — intel's brief record builder and recovery line.
//!
//! `compose_brief` with no client is the template path: every fact comes from
//! the extractors, nothing is invented. The five section names are the frozen
//! constant `BRIEF_SECTIONS`; the tests compare against that constant rather
//! than a copy, so a change to the vocabulary has to change the test.
//!
//! What the empty brief really does, observed: an empty window returns the
//! documented "no activity yet" form early and writes no section headings at
//! all. That is the empty-section rule, so it is pinned as behaviour rather
//! than papered over with an invented fixture.
use intel::b10_brief::brief::{
    brief_budget, compose_brief, recovery_line, BatonStep, RecoveryRecord, RecoveredEntry,
    TemplateSnapshot, BRIEF_SECTIONS,
};

fn template_brief(snapshot: &TemplateSnapshot) -> String {
    compose_brief(snapshot, "morning", None, None, None, None, false, None)
}

#[test]
fn intel_brief_sections() {
    // The frozen vocabulary, in document order (BRF-007).
    assert_eq!(
        BRIEF_SECTIONS,
        &["Decisions", "In flight", "Owners", "Blocked and why", "Watch items"],
    );
    assert_eq!(BRIEF_SECTIONS.len(), 5, "five sections, no more");

    // No duplicate and no blank heading: a repeated name would render two
    // sections with one body between them.
    let mut seen: Vec<&str> = Vec::new();
    for name in BRIEF_SECTIONS {
        assert!(!name.trim().is_empty(), "a section name is never blank");
        assert!(!seen.contains(name), "section {name} appears once");
        seen.push(name);
    }

    // The budget table is keyed by the same kinds the brief is composed for.
    assert_eq!(brief_budget("morning"), Some(220));
    assert_eq!(brief_budget("onjoin"), Some(150));
    assert_eq!(brief_budget("ondemand"), Some(300));
    assert_eq!(brief_budget("weekly"), None, "an unknown kind has no budget");
}

#[test]
fn intel_brief_empty() {
    let text = template_brief(&TemplateSnapshot::default());
    assert!(text.starts_with("TEMPLATE"), "the template path is labelled:\n{text}");
    assert!(text.contains("no activity yet"), "empty window uses its documented form:\n{text}");
    assert!(
        text.contains("This room has no activity yet in this window."),
        "the empty form names the room:\n{text}",
    );

    // An empty input writes no empty section scaffolding: no heading appears
    // with nothing under it.
    for name in BRIEF_SECTIONS {
        assert!(
            !text.lines().any(|l| l.trim() == *name),
            "empty brief writes no {name} heading:\n{text}",
        );
    }
    assert!(!text.trim().is_empty(), "an empty brief is still a document");
}

#[test]
fn intel_recovery_line_borrow() {
    let record = RecoveryRecord {
        corrupted: None,
        recovered: Some(vec![RecoveredEntry::Job {
            id: "job-7".to_string(),
            title: "Rebuild the gate log".to_string(),
            baton_step: BatonStep::Number(3),
        }]),
        sweep_count: Some(1),
    };

    // Rendered from a borrowed record: no clone, no ownership move.
    let borrowed: Option<&RecoveryRecord> = Some(&record);
    let line = recovery_line(borrowed);
    assert!(
        line.starts_with("In-flight jobs recovered at this boot: "),
        "recovery line keeps its documented prefix: {line}",
    );
    assert!(line.contains("1 recovered"), "a reconciled count reads clean: {line}");
    assert!(line.contains("job-7"), "the recovered job is named: {line}");
    assert!(line.contains("Rebuild the gate log"), "its title is named: {line}");
    assert!(line.contains('3'), "its baton step is named: {line}");

    // The record is still usable after the borrow, and the no-record form is
    // a sentence, not an empty string.
    assert_eq!(record.sweep_count, Some(1));
    assert_eq!(
        recovery_line(None),
        "In-flight jobs recovered at this boot: not reported in this snapshot",
    );
}

#[test]
fn intel_recovery_line_disagreement_is_not_an_all_clear() {
    let record = RecoveryRecord {
        corrupted: None,
        recovered: Some(vec![RecoveredEntry::Job {
            id: "job-8".to_string(),
            title: "Half recovered".to_string(),
            baton_step: BatonStep::Missing,
        }]),
        sweep_count: Some(2),
    };
    let line = recovery_line(Some(&record));
    assert!(line.contains("recovery incomplete"), "a disagreement is named: {line}");
    assert!(
        line.contains("lease sweep reports 2 recovered") && line.contains("1 job records were recovered"),
        "both counts are quoted so the reader can see the gap: {line}",
    );
    assert!(!line.contains("not reported"), "a disagreement is not the no-record form");
}
