//! Port of `os/intel/boot_audio_check.py` (+ `final_mix_check.py`,
//! `dem018_local_check.py` siblings) — audio probe checks.
//!
//! Each check probes a duration, reads volumes, and refuses silence
//! (all-zero volumes) or clipping (all-max volumes) fixtures.

use crate::b12a_drills::{DrillReport, PhaseResult};

pub fn probe_duration(samples: &[f32], rate: u32) -> f64 {
    if rate == 0 {
        return 0.0;
    }
    samples.len() as f64 / rate as f64
}

pub fn volumes(samples: &[f32]) -> (f32, f32) {
    let mut peak: f32 = 0.0;
    let mut sum = 0.0;
    for s in samples {
        peak = peak.max(s.abs());
        sum += s.abs();
    }
    let avg = if samples.is_empty() { 0.0 } else { sum / samples.len() as f32 };
    (peak, avg)
}

pub fn check(samples: &[f32], rate: u32) -> Result<String, String> {
    let (peak, avg) = volumes(samples);
    if peak == 0.0 {
        return Err("silence: all-zero volumes".to_string());
    }
    if peak >= 1.0 && avg >= 0.99 {
        return Err("clipping: all-max volumes".to_string());
    }
    Ok(format!("audio ok: {:.2}s peak {peak:.2}", probe_duration(samples, rate)))
}

pub fn run_drill(name: &str, samples: &[f32], rate: u32) -> DrillReport {
    crate::b12a_drills::DrillReport::new(
        name,
        vec![match check(samples, rate) {
            Ok(d) => PhaseResult::pass("probe", d),
            Err(e) => PhaseResult::fail("probe", e),
        }],
    )
}

pub fn run() -> DrillReport {
    run_drill("boot_audio_check", &[0.1, -0.3, 0.2], 44100)
}
