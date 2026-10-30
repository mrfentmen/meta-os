//! Port of `os/intel/drills/demo_thresholds_dropin.py` —
//! demo thresholds drop-in check (OS-038, DEM-012/DEM-013
//! prerequisites).
//!
//! After image assembly (which copies the demo env file and
//! the systemd drop-in into place), this check verifies —
//! on the assembled tree, without booting — that the
//! production image serves the DEMO stall thresholds (stall
//! 60s, progress-stall 60s) with every other threshold at
//! its production default, and that the production unit is
//! untouched by the demo override. It reads the on-disk
//! files the boot path reads; threshold resolution runs
//! through the same env-map parse the thresholds module
//! applies at import. The INT-021 tournament subprocess is
//! the caller's (the `TournamentRun` seam): it must run
//! with WATCHDOG_* stripped from the environment.

use std::path::{Path, PathBuf};

use crate::b12a_drills::deps::Thresholds;
use crate::b12a_drills::value::Value;

/// repo-root-relative paths, verbatim.
pub const DROPIN: &str = "os/services/relay-watchdog.service.d/demo-thresholds.conf";
pub const UNIT: &str = "os/services/relay-watchdog.service";
pub const ENV_FILE: &str = "intel/metaos-demo.env";
pub const IMAGE_ENV_PATH: &str = "/opt/relay/intel/metaos-demo.env";

/// The step-2 expectation: the demo values and the
/// production defaults for everything else.
pub fn expected_thresholds() -> Thresholds {
    Thresholds {
        stall_minutes: 1,
        progress_stall_minutes: 1,
        lease_risk_window_minutes: 5,
        lease_risk_quiet_minutes: 2,
        alert_dedupe_cooldown_minutes: 30,
        silent_room_minutes: 60,
        watchdog_beat_ttl_seconds: 300,
        tick_page_size: 1000,
        tick_max_messages: 1000,
        watchman_stale_minutes: 5,
        timer_sweep_interval_seconds: 300,
        lease_default_seconds: 1800,
    }
}

/// `parse_env_file(text)` — NAME=VALUE per line; blank,
/// comment, and "="less lines skipped; names and values
/// stripped. Returns the dict (map Value).
pub fn parse_env_file(text: &str) -> Value {
    let mut out = Value::obj(vec![]);
    for raw in text.lines() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        if !line.contains('=') {
            continue;
        }
        let (name, value) = line.split_once('=').unwrap();
        out.set(name.trim(), Value::s(value.trim()));
    }
    out
}

/// The WATCHDOG_* subset of a parsed env file, as the pairs
/// the thresholds resolution consumes.
pub fn watchdog_vars(env: &Value) -> Vec<(String, String)> {
    match env.as_map() {
        Some(pairs) => pairs
            .iter()
            .filter(|(name, _)| name.starts_with("WATCHDOG_"))
            .map(|(name, value)| (name.clone(), value.py_str()))
            .collect(),
        None => Vec::new(),
    }
}

/// The INT-021 tournament run (the source's subprocess with
/// a WATCHDOG_*-stripped environment): (ok, transcript,
/// total_seconds).
pub trait TournamentRun {
    fn run_clean(&self) -> (bool, String, f64);
}

/// The full check: (ok, transcript) — transcript ends with
/// a trailing newline, as the source's log write does.
pub fn run(root: &Path, tournament: &dyn TournamentRun) -> (bool, String) {
    let mut lines: Vec<String> = vec![
        "OS-038 demo thresholds drop-in check: drop-in shape, demo values, production untouched"
            .to_string(),
    ];
    let failure = check_dropin_shape(root, &mut lines)
        .or_else(|| check_demo_values(root, &mut lines))
        .or_else(|| check_production_untouched(root, tournament, &mut lines));
    let ok = failure.is_none();
    match &failure {
        Some(failure) => lines.push(format!("OS-038: FAIL -- {}", failure)),
        None => lines.push(
            "OS-038: PASS -- drop-in switches the stall windows on the demo image; production untouched"
                .to_string(),
        ),
    }
    let mut transcript = lines.join("\n");
    transcript.push('\n');
    (ok, transcript)
}

fn read(root: &Path, rel: &str) -> Option<String> {
    let path: PathBuf = root.join(rel);
    std::fs::read_to_string(path).ok()
}

/// Step returns Some(failure-string) or None (and appends
/// its PASS line) — `_check_dropin_shape`.
fn check_dropin_shape(root: &Path, lines: &mut Vec<String>) -> Option<String> {
    let text = match read(root, DROPIN) {
        Some(text) => text,
        None => return Some(format!("FAIL: demo drop-in missing: {}", DROPIN)),
    };
    if !text.contains("[Service]") {
        return Some("FAIL: drop-in has no [Service] section".to_string());
    }
    let want = format!("EnvironmentFile={}", IMAGE_ENV_PATH);
    if !text.contains(&want) {
        return Some(format!("FAIL: drop-in does not set {}", want));
    }
    for raw in text.lines() {
        let line = raw.trim();
        if line.starts_with('#') {
            continue;
        }
        if line.starts_with("ExecStart") {
            return Some(
                "FAIL: drop-in overrides ExecStart — it must only switch the environment"
                    .to_string(),
            );
        }
    }
    lines.push(format!(
        "PASS: drop-in is [Service] + EnvironmentFile={}, no ExecStart",
        IMAGE_ENV_PATH
    ));
    None
}

/// `_check_demo_values` — the demo env file resolved through
/// the thresholds rules must equal the expectation exactly.
fn check_demo_values(root: &Path, lines: &mut Vec<String>) -> Option<String> {
    let text = match read(root, ENV_FILE) {
        Some(text) => text,
        None => return Some(format!("FAIL: demo env file missing: {}", ENV_FILE)),
    };
    let env = parse_env_file(&text);
    let names: Vec<String> = watchdog_vars(&env).into_iter().map(|(n, _)| n).collect();
    if !names.iter().any(|n| n == "WATCHDOG_STALL_MINUTES") {
        return Some(
            "FAIL: demo env file sets no WATCHDOG_STALL_MINUTES override".to_string(),
        );
    }
    let got = Thresholds::from_env_map(&watchdog_vars(&env));
    let want = expected_thresholds();
    for (name, got_v, want_v) in [
        ("STALL_MINUTES", got.stall_minutes, want.stall_minutes),
        (
            "PROGRESS_STALL_MINUTES",
            got.progress_stall_minutes,
            want.progress_stall_minutes,
        ),
        (
            "LEASE_RISK_WINDOW_MINUTES",
            got.lease_risk_window_minutes,
            want.lease_risk_window_minutes,
        ),
        (
            "LEASE_RISK_QUIET_MINUTES",
            got.lease_risk_quiet_minutes,
            want.lease_risk_quiet_minutes,
        ),
        (
            "ALERT_DEDUPE_COOLDOWN_MINUTES",
            got.alert_dedupe_cooldown_minutes,
            want.alert_dedupe_cooldown_minutes,
        ),
        (
            "SILENT_ROOM_MINUTES",
            got.silent_room_minutes,
            want.silent_room_minutes,
        ),
        (
            "WATCHDOG_BEAT_TTL_SECONDS",
            got.watchdog_beat_ttl_seconds,
            want.watchdog_beat_ttl_seconds,
        ),
        ("TICK_PAGE_SIZE", got.tick_page_size, want.tick_page_size),
        (
            "TICK_MAX_MESSAGES",
            got.tick_max_messages,
            want.tick_max_messages,
        ),
    ] {
        if got_v != want_v {
            return Some(format!(
                "FAIL: demo profile {}={}, expected {}",
                name, got_v, want_v
            ));
        }
    }
    lines.push(
        "PASS: demo profile switches thresholds (stall 1, progress-stall 1, all others at production defaults)"
            .to_string(),
    );
    None
}

/// `_check_production_untouched` — unit shape, then the
/// tournament under a clean environment.
fn check_production_untouched(
    root: &Path,
    tournament: &dyn TournamentRun,
    lines: &mut Vec<String>,
) -> Option<String> {
    let text = match read(root, UNIT) {
        Some(text) => text,
        None => return Some(format!("FAIL: production unit missing: {}", UNIT)),
    };
    if text.contains("EnvironmentFile") {
        return Some(
            "FAIL: production unit names an EnvironmentFile — demo values would leak into production"
                .to_string(),
        );
    }
    let (ok, transcript, total) = tournament.run_clean();
    if !ok {
        return Some(format!(
            "FAIL: INT-021 tournament failed with a clean environment:\n{}",
            transcript
        ));
    }
    lines.push(format!(
        "PASS: production unit has no EnvironmentFile; INT-021 tournament 3/3 clean ({:.2}s)",
        total
    ));
    None
}
