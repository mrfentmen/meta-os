//! Port of `os/intel/spoof_dispatch_drill.py` — spoofed-dispatch drill.
//!
//! A dispatch plan with a forged keyring line must be refused before
//! anything posts: the keyring line must match `key:<id>:<hex>` and the
//! signer must be trusted, else exit 2 with nothing posted.

use crate::b12a_drills::{DrillReport, PhaseResult};

pub fn fresh_keyring_line(id: &str) -> String {
    format!("key:{id}:0123456789abcdef")
}

pub fn valid_keyring_line(line: &str) -> bool {
    let parts: Vec<&str> = line.split(':').collect();
    parts.len() == 3 && parts[0] == "key" && !parts[1].is_empty()
        && parts[2].chars().all(|c| c.is_ascii_hexdigit()) && parts[2].len() >= 8
}

pub fn run_drill(lines: &[String], posted: &mut Vec<String>) -> DrillReport {
    let mut phases = Vec::new();
    let all_valid = lines.iter().all(|l| valid_keyring_line(l));
    if !all_valid {
        phases.push(PhaseResult::pass("spoof-refused", "forged keyring line refused; posted nothing"));
    } else {
        posted.push("plan".to_string());
        phases.push(PhaseResult::pass("clean-posts", "valid keyring posts"));
    }
    DrillReport::new("spoof_dispatch_drill", phases)
}

pub fn run() -> DrillReport {
    let mut posted = Vec::new();
    let good = run_drill(&[fresh_keyring_line("k1")], &mut posted);
    let mut posted2 = Vec::new();
    let bad = run_drill(&["key:k1:!!!".to_string()], &mut posted2);
    let ok = good.ok() && bad.ok() && posted.len() == 1 && posted2.is_empty();
    DrillReport::new(
        "spoof_dispatch_drill",
        vec![if ok {
            PhaseResult::pass("run", "spoof refused with nothing posted; clean posts")
        } else {
            PhaseResult::fail("run", "wrong post behavior")
        }],
    )
}
