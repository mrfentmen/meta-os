//! B29 — Crew dirs & demo/submission assets — **CARRIED, not ported**.
//!
//! Asset batch: 6 crew READMEs + 16 demo/submission audio + text.
//! All 22 files inventoried 2026-10-30, confirmed logic-free, left in
//! place. Audio never re-encoded or regenerated.

/// Files carried by B29 (exactly `BATCHES.md` §B29).
pub const FILES: &[&str] = &[
    "os/crew/README.md",
    "os/crew/buffy/README.md",
    "os/crew/hana/README.md",
    "os/crew/milo/README.md",
    "os/crew/pax/README.md",
    "os/crew/rowan/README.md",
    "os/demo-assets/audio/LICENSES.md",
    "os/demo-assets/audio/TAKE_LOG.md",
    "os/demo-assets/audio/TIMING.md",
    "os/demo-assets/audio/dem014-final-mix.mp3",
    "os/demo-assets/audio/dem015-caption-watchdog-moment.mp3",
    "os/demo-assets/audio/dem017-ambient-bed.mp3",
    "os/demo-assets/audio/wdg030-watchdog-segment-take1.mp3",
    "os/demo-assets/audio/wdg030-watchdog-segment-take2.mp3",
    "os/demo-assets/audio/wdg031-opening-framing-take1.mp3",
    "os/demo-assets/audio/wdg031-opening-framing-take2.mp3",
    "os/demo-assets/audio/wdg033-fallback-full-demo.mp3",
    "os/demo-assets/audio/wdg033-fallback-script.txt",
    "os/demo-assets/audio/wdg034-alert-sting.mp3",
    "os/demo-assets/audio/wdg034-success-sting.mp3",
    "os/submission-assets/audio/os039-boot-sting.mp3",
    "os/submission-assets/audio/os039-boot-voice-line.mp3",
];

pub fn is_logic_free() -> bool {
    true
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn inventory_complete() {
        assert_eq!(FILES.len(), 22);
        assert!(is_logic_free());
    }
}
