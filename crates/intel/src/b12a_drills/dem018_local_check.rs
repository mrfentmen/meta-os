//! Port of `os/intel/dem018_local_check.py` — DEM-018 (partial):
//! local pre-check for every demo audio asset.
//!
//! For all 12 assets: each file is an MP3, decodes cleanly
//! through ffmpeg, has a sane duration, and peaks below 0 dB.
//! The listening check on the actual demo machine stays OPEN;
//! this script is the pre-check only, and its closing lines
//! say so. `execute` is the script body: (exit code, lines).

use super::audiocheck::{
    decodes_clean, max_volume, probe_duration, py_bytes_repr, read_head3, CheckLog, CmdRunner,
};
use super::value::py_float_str;

pub const ASSETS: [&str; 12] = [
    "demo-assets/audio/wdg030-watchdog-segment-take1.mp3",
    "demo-assets/audio/wdg030-watchdog-segment-take2.mp3",
    "demo-assets/audio/wdg031-opening-framing-take1.mp3",
    "demo-assets/audio/wdg031-opening-framing-take2.mp3",
    "demo-assets/audio/dem014-final-mix.mp3",
    "demo-assets/audio/wdg033-fallback-full-demo.mp3",
    "demo-assets/audio/dem015-caption-watchdog-moment.mp3",
    "demo-assets/audio/dem017-ambient-bed.mp3",
    "demo-assets/audio/wdg034-alert-sting.mp3",
    "demo-assets/audio/wdg034-success-sting.mp3",
    "submission-assets/audio/os039-boot-sting.mp3",
    "submission-assets/audio/os039-boot-voice-line.mp3",
];

/// This script's subprocess timeout (the source's run default).
const TIMEOUT: u64 = 180;

/// The script's main(): exit 0 when every local check passes.
pub fn execute<R: CmdRunner>(runner: &R) -> (i32, Vec<String>) {
    let mut log = CheckLog::default();
    let missing: Vec<&str> = ASSETS
        .iter()
        .copied()
        .filter(|path| !std::path::Path::new(path).is_file())
        .collect();
    let assets_detail = if missing.is_empty() {
        "12/12".to_string()
    } else {
        format!("missing: {}", missing.join(", "))
    };
    log.check(
        "all 12 expected assets present",
        missing.is_empty(),
        &assets_detail,
    );
    let mut peaks: Vec<(&str, f64)> = Vec::new();
    for path in ASSETS {
        if !std::path::Path::new(path).is_file() {
            continue;
        }
        match read_head3(path) {
            Ok(head) => {
                log.check(
                    &format!("{} is MP3", path),
                    head == b"ID3",
                    &py_bytes_repr(&head),
                );
            }
            Err(err) => {
                log.print(format!("error: {}: {}", path, err));
                return (1, log.lines);
            }
        }
        let decoded = decodes_clean(runner, path, TIMEOUT);
        log.check(
            &format!("{} decodes clean", path),
            decoded.code == 0,
            &super::audiocheck::stderr_head(&decoded.stderr),
        );
        let duration = match probe_duration(runner, path, TIMEOUT) {
            Ok(d) => d,
            Err(err) => {
                log.print(format!("error: {}", err));
                return (1, log.lines);
            }
        };
        log.check(
            &format!("{} duration sane (>0 s)", path),
            duration > 0.0,
            &format!("{:.2} s", duration),
        );
        let peak = match max_volume(runner, path, TIMEOUT) {
            Ok(p) => p,
            Err(err) => {
                log.print(format!("error: {}", err));
                return (1, log.lines);
            }
        };
        peaks.push((path, peak));
        log.check(
            &format!("{} no clipping (peak < 0 dB)", path),
            peak < 0.0,
            &format!("max {} dB", py_float_str(peak)),
        );
        log.print(format!(
            "  {}: {:.2} s, peak {} dB",
            path,
            duration,
            py_float_str(peak)
        ));
    }
    if !peaks.is_empty() {
        // Python max/min with key: first best in insertion order.
        let mut loudest = peaks[0];
        let mut quietest = peaks[0];
        for entry in &peaks[1..] {
            if entry.1 > loudest.1 {
                loudest = *entry;
            }
            if entry.1 < quietest.1 {
                quietest = *entry;
            }
        }
        let spread = loudest.1 - quietest.1;
        log.print(format!(
            "peak spread across assets: {:.1} dB (loudest {}, quietest {})",
            spread, loudest.0, quietest.0
        ));
        log.print(
            "NOTE: spread is reported, not gated — stingers and the ambient bed are meant to sit quieter than narration."
                .to_string(),
        );
    }
    log.print(
        "DEM-018 status: LOCAL PRE-CHECK ONLY — the demo-machine listening check (speakers + headphones, machine named) remains OPEN."
            .to_string(),
    );
    if !log.failures.is_empty() {
        log.print(format!("{} check(s) FAILED", log.failures.len()));
        return (1, log.lines);
    }
    log.print("all local checks PASS".to_string());
    (0, log.lines)
}
