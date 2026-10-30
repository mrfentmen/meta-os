//! Port of `os/intel/final_mix_check.py` — final-mix audio check.
//!
//! Same probe contract as `boot_audio_check`; the final mix must clear
//! a longer minimum duration (30s) or the demo has no bed.

use super::boot_audio_check::{check, probe_duration};
use crate::b12a_drills::{DrillReport, PhaseResult};

pub const MIN_SECONDS: f64 = 30.0;

pub fn run_check(samples: &[f32], rate: u32) -> Result<String, String> {
    let base = check(samples, rate)?;
    if probe_duration(samples, rate) < MIN_SECONDS {
        return Err("final mix shorter than 30s".to_string());
    }
    Ok(base)
}

pub fn run() -> DrillReport {
    let samples = vec![0.2f32; 44100 * 31];
    DrillReport::new(
        "final_mix_check",
        vec![match run_check(&samples, 44100) {
            Ok(d) => PhaseResult::pass("run", d),
            Err(e) => PhaseResult::fail("run", e),
        }],
    )
}
