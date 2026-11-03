//! CB2-338 — a populated snapshot renders all five frozen sections.
//!
//! The empty-input form is pinned by CB2-339. This is the other half: real rows
//! in a real snapshot, and every documented heading on the page with its items
//! underneath. The rows are fixture input to `compose_brief`; nothing is fetched
//! and no model is called.

use intel::b10_brief::brief::{compose_brief, TemplateSnapshot, BRIEF_SECTIONS};
use intel::b10_brief::sections::{SnapAlert, SnapJob, SnapMessage, Snapshot};
use intel::b10_brief::window::WindowInput;

fn populated() -> TemplateSnapshot {
    TemplateSnapshot {
        base: Snapshot {
            messages: vec![
                SnapMessage { nick: "milo".into(), text: "DONE: wall raised to course four".into(), ts: Some(1_793_600_000) },
                SnapMessage { nick: "bond".into(), text: "BLOCKED: no cement on site until Friday".into(), ts: Some(1_793_600_100) },
                SnapMessage { nick: "milo".into(), text: "DECISION: cap the wall before the frost".into(), ts: Some(1_793_600_200) },
            ],
            // `claimed` is what in-flight and owners read; `blocked` is its own
            // section, with the reason carried verbatim from the note.
            jobs: vec![
                SnapJob {
                    id: "job-7".into(),
                    title: "cap the west wall".into(),
                    status: "claimed".into(),
                    claim: "milo".into(),
                    note: "half capped".into(),
                    last_progress_at: Some(1_793_600_300),
                    claimed_at: Some(1_793_600_000),
                },
                SnapJob {
                    id: "job-8".into(),
                    title: "order cement".into(),
                    status: "blocked".into(),
                    claim: "bond".into(),
                    note: "supplier moved it to Friday".into(),
                    last_progress_at: Some(1_793_600_250),
                    claimed_at: Some(1_793_600_050),
                },
            ],
            alerts: vec![SnapAlert {
                id: "alert-1".into(),
                summary: "cement delivery slipped".into(),
                explanation: "the supplier moved it to Friday".into(),
            }],
            source_window: None,
        },
        window: WindowInput { source_window: None, window_start: Some("2026-11-02T00:00:00Z".into()) },
        ..Default::default()
    }
}

#[test]
fn intel_brief_sections() {
    let brief = compose_brief(&populated(), "morning", None, None, None, Some(1_793_600_400), false, None);

    // Every frozen heading appears, and appears in the frozen order.
    let mut at = 0;
    for section in BRIEF_SECTIONS {
        let found = brief[at..]
            .find(section)
            .unwrap_or_else(|| panic!("section {section:?} is missing from:\n{brief}"));
        at += found + section.len();
    }

    // The items under the headings are the snapshot's own words.
    assert!(brief.contains("wall raised to course four"), "decision item rendered:\n{brief}");
    assert!(brief.contains("no cement on site until Friday"), "blocked reason stays verbatim:\n{brief}");
    assert!(brief.contains("job-7"), "in-flight job rendered:\n{brief}");
    assert!(brief.contains("cap the west wall"), "by its title:\n{brief}");
    assert!(brief.contains("milo"), "owner rendered:\n{brief}");
    assert!(brief.contains("supplier moved it to Friday"), "blocked job reason:\n{brief}");
    assert!(brief.contains("cement delivery slipped"), "watch item rendered:\n{brief}");

    // A brief is text, not a claim of a model call.
    assert!(!brief.trim().is_empty());
}
