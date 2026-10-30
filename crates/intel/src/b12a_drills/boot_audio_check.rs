//! Port of `os/intel/boot_audio_check.py` — OS-039 boot-audio
//! check: sting + voice line are clean, unclipped, and mixable.
//!
//! Both files exist as MP3, decode cleanly, the sting is short
//! and quiet enough to sit under narration, and a sting-then-
//! voice mix measures no clipping. `execute` is the script body;
//! it returns (exit code, printed lines) like the source's main.

use super::audiocheck::{
    decodes_clean, probe_duration, py_bytes_repr, read_head3, stderr_head, volumes, CheckLog,
    CmdRunner,
};
use super::value::py_float_str;

pub const STING: &str = "submission-assets/audio/os039-boot-sting.mp3";
pub const VOICE: &str = "submission-assets/audio/os039-boot-voice-line.mp3";
pub const MIX: &str = "/tmp/os039-boot-mix.wav";

/// The script's main(): exit 0 when every check passes.
pub fn execute<R: CmdRunner>(runner: &R) -> (i32, Vec<String>) {
    let mut log = CheckLog::default();
    for path in [STING, VOICE] {
        match read_head3(path) {
            Ok(head) => {
                log.check(
                    &format!("{} is MP3", path),
                    head == b"ID3",
                    &py_bytes_repr(&head),
                );
            }
            Err(err) => {
                // The source opens the file bare: a missing asset
                // raises and the script dies non-zero.
                log.print(format!("error: {}: {}", path, err));
                return (1, log.lines);
            }
        }
        let decoded = decodes_clean(runner, path, 120);
        log.check(&format!("{} decodes clean", path), decoded.code == 0, "");
    }

    let sting_dur = match probe_duration(runner, STING, 120) {
        Ok(d) => d,
        Err(err) => {
            log.print(format!("error: {}", err));
            return (1, log.lines);
        }
    };
    log.check(
        "sting is short (1.5-2.5 s)",
        (1.5..=2.5).contains(&sting_dur),
        &format!("{:.2} s", sting_dur),
    );
    let voice_dur = match probe_duration(runner, VOICE, 120) {
        Ok(d) => d,
        Err(err) => {
            log.print(format!("error: {}", err));
            return (1, log.lines);
        }
    };
    log.check(
        "voice line is one short line (under 10 s)",
        voice_dur < 10.0,
        &format!("{:.2} s", voice_dur),
    );

    let (sting_mean, sting_max) = match volumes(runner, STING, 120) {
        Ok(v) => v,
        Err(err) => {
            log.print(format!("error: {}", err));
            return (1, log.lines);
        }
    };
    let (_voice_mean, voice_max) = match volumes(runner, VOICE, 120) {
        Ok(v) => v,
        Err(err) => {
            log.print(format!("error: {}", err));
            return (1, log.lines);
        }
    };
    log.check(
        "sting peak below voice peak (sits under narration)",
        sting_max < voice_max,
        &format!(
            "sting max {} dB, voice max {} dB",
            py_float_str(sting_max),
            py_float_str(voice_max)
        ),
    );
    log.check(
        "sting mean below -20 dB",
        sting_mean < -20.0,
        &format!("{} dB", py_float_str(sting_mean)),
    );

    // Mix test: sting, then the voice line, one track.
    let mixed = runner.run(
        &[
            "ffmpeg", "-y", "-v", "error", "-i", STING, "-i", VOICE, "-filter_complex",
            "[0:a][1:a]concat=n=2:v=0:a=1[out]", "-map", "[out]", MIX,
        ],
        120,
    );
    log.check(
        "sting+voice concat renders",
        mixed.code == 0,
        &stderr_head(&mixed.stderr),
    );
    if mixed.code == 0 {
        match volumes(runner, MIX, 120) {
            Ok((_mean, mix_max)) => {
                log.check(
                    "mixed track does not clip",
                    mix_max < 0.0,
                    &format!("mix max {} dB", py_float_str(mix_max)),
                );
            }
            Err(err) => {
                log.print(format!("error: {}", err));
                return (1, log.lines);
            }
        }
    }

    if log.failures.is_empty() {
        log.print("OS-039 boot audio: ALL PASS".to_string());
        (0, log.lines)
    } else {
        log.print(format!("OS-039 boot audio: {} FAILURES", log.failures.len()));
        (1, log.lines)
    }
}
