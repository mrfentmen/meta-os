//! Port of `os/intel/dem018_local_check.py` — local demo audio check.
//!
//! Same probe contract as `boot_audio_check` with the DEM-018 volume
//! floor: average volume must clear 0.01 or the room hears nothing.

use super::boot_audio_check::{probe_duration, volumes};
use crate::b12a_drills::{DrillReport, PhaseResult};

pub fn max_volume(samples: &[f32]) -> f32 {
    volumes(samples).0
}

pub fn check(samples: &[f32], rate: u32) -> Result<String, String> {
    let (_peak, avg) = volumes(samples);
    if avg < 0.01 {
        return Err("below DEM-018 volume floor".to_string());
    }
    Ok(format!("dem018 ok: {:.2}s", probe_duration(samples, rate)))
}

pub fn run() -> DrillReport {
    DrillReport::new(
        "dem018_local_check",
        vec![match check(&[0.2, -0.2], 44100) {
            Ok(d) => PhaseResult::pass("probe", d),
            Err(e) => PhaseResult::fail("probe", e),
        }],
    )
}
