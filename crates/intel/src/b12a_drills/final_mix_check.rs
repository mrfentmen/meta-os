//! Port of `os/intel/final_mix_check.py` — DEM-014: narration
//! final mix, picked takes combined, level-checked.
//!
//! The mix combines the two provisional-final narration takes
//! (WDG-031 opening framing, a 0.5 s silence gap, then the
//! WDG-030 watchdog segment). The mix must decode cleanly, run
//! the expected length, peak below 0 dB, and sit within 3 dB
//! of the louder input (no level jump at the join). The
//! WDG-033 fallback peak is reported for reference, not gated.
//! `execute` is the script body: (exit code, printed lines).

use super::audiocheck::{
    decodes_clean, probe_duration, py_bytes_repr, read_head3, stderr_head, volumes, CheckLog,
    CmdRunner,
};
use super::value::py_float_str;

pub const OPENING: &str = "demo-assets/audio/wdg031-opening-framing-take1.mp3";
pub const WATCHDOG_ASSET: &str = "demo-assets/audio/wdg030-watchdog-segment-take1.mp3";
pub const FALLBACK: &str = "demo-assets/audio/wdg033-fallback-full-demo.mp3";
pub const MIX: &str = "demo-assets/audio/dem014-final-mix.mp3";
pub const GAP_SECONDS: f64 = 0.5;

/// The script's main(): exit 0 when every check passes. A
/// render failure ends the run early, as in the source.
pub fn execute<R: CmdRunner>(runner: &R) -> (i32, Vec<String>) {
    let mut log = CheckLog::default();
    for path in [OPENING, WATCHDOG_ASSET] {
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
        let decoded = decodes_clean(runner, path, 120);
        log.check(&format!("{} decodes clean", path), decoded.code == 0, "");
    }

    let open_dur = match probe_duration(runner, OPENING, 120) {
        Ok(d) => d,
        Err(err) => {
            log.print(format!("error: {}", err));
            return (1, log.lines);
        }
    };
    let watch_dur = match probe_duration(runner, WATCHDOG_ASSET, 120) {
        Ok(d) => d,
        Err(err) => {
            log.print(format!("error: {}", err));
            return (1, log.lines);
        }
    };
    let expected = open_dur + GAP_SECONDS + watch_dur;
    log.check(
        "inputs match the take log (19.9 s + 48.1 s)",
        (open_dur - 19.92).abs() < 0.5 && (watch_dur - 48.07).abs() < 0.5,
        &format!("opening {:.2} s, watchdog {:.2} s", open_dur, watch_dur),
    );

    // Build the mix: opening, 0.5 s of silence, watchdog — one
    // MP3 track. anullsrc gives the gap; concat joins the three.
    let mixed = runner.run(
        &[
            "ffmpeg", "-y", "-v", "error", "-i", OPENING, "-f", "lavfi", "-t", "0.5", "-i",
            "anullsrc=r=44100:cl=stereo", "-i", WATCHDOG_ASSET, "-filter_complex",
            "[0:a][1:a][2:a]concat=n=3:v=0:a=1[out]", "-map", "[out]", MIX,
        ],
        120,
    );
    log.check(
        "final mix renders",
        mixed.code == 0,
        &stderr_head(&mixed.stderr),
    );
    if mixed.code != 0 {
        log.print(format!(
            "DEM-014 final mix: {} FAILURES",
            log.failures.len()
        ));
        return (1, log.lines);
    }

    match read_head3(MIX) {
        Ok(head) => {
            log.check("mix is MP3", head == b"ID3", &py_bytes_repr(&head));
        }
        Err(err) => {
            log.print(format!("error: {}: {}", MIX, err));
            return (1, log.lines);
        }
    }
    let decoded = decodes_clean(runner, MIX, 120);
    log.check("mix decodes clean", decoded.code == 0, "");

    let mix_dur = match probe_duration(runner, MIX, 120) {
        Ok(d) => d,
        Err(err) => {
            log.print(format!("error: {}", err));
            return (1, log.lines);
        }
    };
    log.check(
        "mix length is opening + gap + watchdog (±2 s)",
        (mix_dur - expected).abs() < 2.0,
        &format!("{:.2} s vs expected {:.2} s", mix_dur, expected),
    );

    let vol = |path: &str| volumes(runner, path, 120);
    let (_open_mean, open_max) = match vol(OPENING) {
        Ok(v) => v,
        Err(err) => {
            log.print(format!("error: {}", err));
            return (1, log.lines);
        }
    };
    let (_watch_mean, watch_max) = match vol(WATCHDOG_ASSET) {
        Ok(v) => v,
        Err(err) => {
            log.print(format!("error: {}", err));
            return (1, log.lines);
        }
    };
    let (_mix_mean, mix_max) = match vol(MIX) {
        Ok(v) => v,
        Err(err) => {
            log.print(format!("error: {}", err));
            return (1, log.lines);
        }
    };
    let (_fb_mean, fallback_max) = match vol(FALLBACK) {
        Ok(v) => v,
        Err(err) => {
            log.print(format!("error: {}", err));
            return (1, log.lines);
        }
    };
    log.check(
        "mix does not clip",
        mix_max < 0.0,
        &format!("mix max {} dB", py_float_str(mix_max)),
    );
    let loudest_input = open_max.max(watch_max);
    log.check(
        "no level jump at the join (mix peak within 3 dB of louder input)",
        (mix_max - loudest_input).abs() < 3.0,
        &format!(
            "mix max {} dB, louder input {} dB",
            py_float_str(mix_max),
            py_float_str(loudest_input)
        ),
    );
    log.print(format!(
        "INFO fallback reference peak {} dB (same voice, different edit)",
        py_float_str(fallback_max)
    ));

    if log.failures.is_empty() {
        log.print("DEM-014 final mix: ALL PASS".to_string());
        (0, log.lines)
    } else {
        log.print(format!(
            "DEM-014 final mix: {} FAILURES",
            log.failures.len()
        ));
        (1, log.lines)
    }
}
