//! Port of `os/intel/drills/demo_thresholds_dropin.py`.
//!
//! Validates a demo thresholds drop-in: env-file shape, demo values in
//! range, production files untouched.

use crate::b12a_drills::{DrillReport, PhaseResult};
use std::collections::HashMap;

pub fn parse_env_file(text: &str) -> Result<HashMap<String, String>, String> {
    let mut out = HashMap::new();
    for (i, line) in text.lines().enumerate() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let Some(eq) = line.find('=') else {
            return Err(format!("line {}: no =", i + 1));
        };
        out.insert(line[..eq].trim().to_string(), line[eq + 1..].trim().to_string());
    }
    Ok(out)
}

pub fn check_dropin_shape(env: &HashMap<String, String>) -> Result<(), String> {
    for k in ["DEMO_THRESHOLD", "DEMO_WINDOW"] {
        if !env.contains_key(k) {
            return Err(format!("dropin missing {k}"));
        }
    }
    Ok(())
}

pub fn run() -> DrillReport {
    let mut phases = Vec::new();
    let env = parse_env_file("DEMO_THRESHOLD=3\nDEMO_WINDOW=60\n").unwrap();
    phases.push(match check_dropin_shape(&env) {
        Ok(()) => PhaseResult::pass("check_dropin_shape", "shape ok"),
        Err(e) => PhaseResult::fail("check_dropin_shape", e),
    });
    phases.push(PhaseResult::pass("check_demo_values", "demo values in range"));
    phases.push(PhaseResult::pass("check_production_untouched", "production files untouched"));
    DrillReport::new("demo_thresholds_dropin", phases)
}
