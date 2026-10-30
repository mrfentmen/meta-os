//! Port of `os/intel/spoof_dispatch_drill.py` — INT-010:
//! spoofed dispatch (BAD signature), scripted drill.
//!
//! An attacker rewrites a signed job's spec after the
//! overseer posts it; a worker's claim must be refused by the
//! shipped verifier (jobs.py v2 HMAC signer over a real
//! keyring file), the job stays open, the fake bus carries
//! the REJECTED line, and the watchdog turns that line into
//! exactly one critical rejected-dispatch alert that validates
//! into a WDG-010 record. Negatives: clean, malformed,
//! duplicate, and dict-shaped EXPIRED lines. Unsigned jobs
//! still claim with a warning, by design.
//!
//! Seams: the jobs CLI + suite fake store ride [`SpoofSurface`]
//! (in the source, `unittest.mock` patches relay_common/jobs
//! onto tests/fake_redis.FakeUpstash — that fake and
//! relay_common are test-harness modules outside the cleaned
//! os/intel tree, so the surface is a trait here, with the
//! same call shapes). The keyring holds a fresh random
//! secret generated per run (INT-011: no committed keyring
//! literal), never a real credential, removed after the run.

use super::deps::{AlertRecords, Watchdog};
use super::redis_down_drill::DrillResult;
use super::value::{py_repr_str, Value};

pub const NOW: i64 = 10000;
pub const JOB_NS: &str = "muse-bus:tjob";

const STAGE_NAMES: [&str; 6] = [
    "fixture",
    "tamper",
    "claim-refused",
    "watchdog",
    "negatives",
    "unsigned-allowed",
];

/// The jobs CLI + fake store surface (one shared fake for
/// stages 1–3, a fresh one for stage 6 via `reset_fake`).
pub trait SpoofSurface {
    /// A jobs.py CLI main run as (ns, nick): (code, out, err).
    fn jobs_cli(&self, ns: &str, nick: &str, argv: &[String]) -> (i32, String, String);
    /// `jobs.job_get(job_id)` -> (header dict, spec text).
    fn job_get(&self, ns: &str, job_id: &str) -> (Option<Value>, String);
    /// `jobs.api_post(path, value)` — a direct store write.
    fn store_post(&self, path: &str, value: &str);
    /// The fake's recorded bus pushes: (key, body) pairs.
    fn pushes(&self) -> Vec<(String, String)>;
    /// Swap in a fresh fake (stage 6's new FakeUpstash).
    fn reset_fake(&self);
}

/// `_fresh_keyring_line` — "crew-2026-09:" + 16 random bytes
/// as hex. Randomness here is per-run uniqueness only (the
/// value is never asserted): sha256 over the clock and pid
/// stands in for `secrets.token_hex(16)`.
pub fn fresh_keyring_line() -> String {
    let nanos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    let seed = format!("{}:{}", nanos, std::process::id());
    let hex = super::sha256::sha256_hex(seed.as_bytes());
    format!("crew-2026-09:{}", &hex[..32])
}

fn write_keyring() -> std::path::PathBuf {
    let nanos = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    let path = std::env::temp_dir().join(format!(
        "spoof-drill-{}-{}.keyring",
        std::process::id(),
        nanos
    ));
    let _ = std::fs::write(&path, format!("{}\n", fresh_keyring_line()));
    path
}

fn stage(
    stages: &mut Vec<super::e2e1::Stage>,
    name: &str,
    f: impl FnOnce() -> Result<String, String>,
) {
    match f() {
        Ok(detail) => stages.push(super::e2e1::Stage {
            name: name.to_string(),
            ok: true,
            detail,
        }),
        Err(msg) => stages.push(super::e2e1::Stage {
            name: name.to_string(),
            ok: false,
            detail: format!("AssertionError: {}", msg),
        }),
    }
}

fn argv(parts: &[&str]) -> Vec<String> {
    parts.iter().map(|s| s.to_string()).collect()
}

/// `run_drill(write_log)` — the INT-010 drill.
pub fn run_drill(
    surface: &dyn SpoofSurface,
    watchdog: &dyn Watchdog,
    records: &dyn AlertRecords,
) -> DrillResult {
    let mut stages: Vec<super::e2e1::Stage> = Vec::new();
    let keyring = write_keyring();
    let keyring_path = keyring.to_string_lossy().to_string();
    let mut rejected_line = String::new();

    stage(&mut stages, STAGE_NAMES[0], || {
        let (code, out, err) = surface.jobs_cli(
            JOB_NS,
            "overseer",
            &argv(&[
                "post",
                "--title",
                "Ship the drill note",
                "--spec",
                "write the note and file it",
                "--secret-file",
                &keyring_path,
            ]),
        );
        if code != 0 {
            return Err(format!("post exited {}: {}", code, err));
        }
        if !out.contains("JOB 1") {
            return Err(format!("post output is not JOB 1: {:?}", out));
        }
        let (header, _spec) = surface.job_get(JOB_NS, "1");
        let header = header.ok_or("posted job 1 not readable")?;
        if !header.get("sig").truthy() {
            return Err("posted job carries no signature".to_string());
        }
        if header.get("sig_v").as_str() != Some("2") {
            return Err(format!(
                "posted job sig_v is {:?}, not 2",
                header.get("sig_v").py_repr()
            ));
        }
        if header.get("signed_by").as_str() != Some("overseer") {
            return Err(format!(
                "signed_by is {:?}",
                header.get("signed_by").py_repr()
            ));
        }
        let (code, out, err) = surface.jobs_cli(
            JOB_NS,
            "overseer",
            &argv(&["verify", "1", "--secret-file", &keyring_path]),
        );
        if code != 0 {
            return Err(format!("verify exited {}: {}", code, err));
        }
        if out.trim() != "OK" {
            return Err(format!(
                "verify before tamper is {:?}, not OK",
                out.trim()
            ));
        }
        Ok("signed job 1 posted (v2, overseer), verify OK before tamper".to_string())
    });

    stage(&mut stages, STAGE_NAMES[1], || {
        surface.store_post("set/muse-bus:tjob:1:spec", "do the EVIL thing");
        let (_header, spec) = surface.job_get(JOB_NS, "1");
        if spec != "do the EVIL thing" {
            return Err(format!("spec tamper did not land: {:?}", spec));
        }
        let (code, out, err) = surface.jobs_cli(
            JOB_NS,
            "overseer",
            &argv(&["verify", "1", "--secret-file", &keyring_path]),
        );
        if code != 1 {
            return Err(format!("verify exited {}, not 1: {}", code, err));
        }
        if out.trim() != "BAD" {
            return Err(format!(
                "verify after tamper is {:?}, not BAD",
                out.trim()
            ));
        }
        Ok("spec rewritten in store, shipped verifier says BAD".to_string())
    });

    stage(&mut stages, STAGE_NAMES[2], || {
        let (code, out, err) = surface.jobs_cli(
            JOB_NS,
            "worker",
            &argv(&["claim", "1", "--secret-file", &keyring_path]),
        );
        if code != 1 {
            return Err(format!("claim exited {}, not 1: {} {}", code, out, err));
        }
        if !err.contains("signature BAD") {
            return Err(format!("claim stderr does not name BAD: {:?}", err));
        }
        let (header, _spec) = surface.job_get(JOB_NS, "1");
        let header = header.ok_or("job 1 not readable after claim")?;
        if header.get("status").as_str() != Some("open") {
            return Err(format!(
                "job status is {:?}, not open",
                header.get("status").py_repr()
            ));
        }
        let claim = header.get("claim");
        if !(claim.is_null() || claim.as_str() == Some("")) {
            return Err(format!(
                "refused job carries a claim: {:?}",
                claim.py_repr()
            ));
        }
        let pushes = surface.pushes();
        let line = pushes
            .iter()
            .filter(|(key, body)| key == "muse-bus" && body.contains("REJECTED:1 BAD"))
            .map(|(_, body)| body.clone())
            .next()
            .ok_or_else(|| format!("no REJECTED:1 BAD line on the fake bus: {:?}", pushes))?;
        if !line.contains("signed_by=overseer") {
            return Err(format!("REJECTED line lacks the poster: {:?}", line));
        }
        if !line.contains("rejected_by=worker") {
            return Err(format!("REJECTED line lacks the refuser: {:?}", line));
        }
        rejected_line = line.clone();
        Ok(format!(
            "claim refused (exit 1, signature BAD), job stays open, bus line: {}",
            py_repr_str(&line)
        ))
    });

    stage(&mut stages, STAGE_NAMES[3], || {
        let snapshot = Value::obj(vec![
            (
                "messages",
                Value::List(vec![
                    Value::obj(vec![
                        ("nick", Value::s("overseer")),
                        ("text", Value::s("shipping the drill")),
                    ]),
                    Value::s(&rejected_line),
                ]),
            ),
            (
                "jobs",
                Value::List(vec![Value::obj(vec![
                    ("id", Value::s("1")),
                    ("status", Value::s("open")),
                    ("title", Value::s("Ship the drill note")),
                ])]),
            ),
            ("presence", Value::List(vec![])),
            ("caps", Value::obj(vec![])),
        ]);
        let mut emitted: Vec<Value> = Vec::new();
        let alerts = watchdog.tick_emit(&snapshot, Some(NOW), &mut |a| {
            emitted.push(a.clone());
        });
        let rejected: Vec<Value> = alerts
            .iter()
            .filter(|a| a.get("kind").as_str() == Some("rejected-dispatch"))
            .cloned()
            .collect();
        if rejected.len() != 1 {
            return Err(format!(
                "tick yields {} rejected-dispatch alerts, not 1: {}",
                rejected.len(),
                Value::List(alerts).py_repr()
            ));
        }
        let alert = rejected[0].clone();
        if alert.get("severity").as_str() != Some("critical") {
            return Err(format!(
                "severity is {:?}, not critical",
                alert.get("severity").py_repr()
            ));
        }
        if alert.get("dedupe_key").as_str() != Some("rejected-dispatch:1:BAD") {
            return Err(format!(
                "dedupe key is {:?}",
                alert.get("dedupe_key").py_repr()
            ));
        }
        if alert.get("job").as_str() != Some("1") || alert.get("verdict").as_str() != Some("BAD") {
            return Err(format!(
                "alert names job {:?} verdict {:?}",
                alert.get("job").py_repr(),
                alert.get("verdict").py_repr()
            ));
        }
        if alert.get("signed_by").as_str() != Some("overseer") {
            return Err(format!(
                "signed_by is {:?}",
                alert.get("signed_by").py_repr()
            ));
        }
        if alert.get("rejected_by").as_str() != Some("worker") {
            return Err(format!(
                "rejected_by is {:?}",
                alert.get("rejected_by").py_repr()
            ));
        }
        let explanation = alert.get("explanation").py_str();
        if !(explanation.contains('1') && explanation.contains("BAD")) {
            return Err(format!(
                "explanation does not name job and verdict: {:?}",
                explanation
            ));
        }
        if !(emitted.len() == 1 && emitted[0] == alert || emitted.contains(&alert)) {
            return Err("emit callback did not receive the alert".to_string());
        }
        let announcement = watchdog.format_announcement(&alert);
        let announcement_ok = announcement
            .as_ref()
            .map(|a| a.starts_with("ALERT:rejected-dispatch:1:BAD rejected-dispatch:"))
            .unwrap_or(false);
        if !announcement_ok {
            return Err(format!(
                "announcement line is wrong: {:?}",
                announcement
            ));
        }
        let record = records.build_alert_record(&alert, "main");
        if record.get("id").as_str() != Some("rejected-dispatch:1:BAD") {
            return Err(format!("record id is {:?}", record.get("id").py_repr()));
        }
        let subjects: Vec<String> = record
            .get("subjects")
            .as_list()
            .map(|items| items.iter().map(|v| v.py_str()).collect())
            .unwrap_or_default();
        if subjects != vec!["1".to_string()] {
            return Err(format!("record subjects are {:?}", subjects));
        }
        if record.get("status").as_str() != Some("open") {
            return Err(format!(
                "record status is {:?}",
                record.get("status").py_repr()
            ));
        }
        Ok("one critical rejected-dispatch alert, emit received, ALERT line formed, WDG-010 record valid (id = dedupe key, subjects = job)".to_string())
    });

    stage(&mut stages, STAGE_NAMES[4], || {
        let rejected_only = |alerts: &[Value]| -> Vec<Value> {
            alerts
                .iter()
                .filter(|a| a.get("kind").as_str() == Some("rejected-dispatch"))
                .cloned()
                .collect()
        };
        let clean = Value::obj(vec![
            (
                "messages",
                Value::List(vec![Value::obj(vec![
                    ("nick", Value::s("pax")),
                    ("text", Value::s("all quiet")),
                ])]),
            ),
            (
                "jobs",
                Value::List(vec![Value::obj(vec![
                    ("id", Value::s("1")),
                    ("status", Value::s("open")),
                ])]),
            ),
        ]);
        if !rejected_only(&watchdog.tick(&clean, Some(NOW))).is_empty() {
            return Err("clean snapshot fired a rejected alert".to_string());
        }
        let malformed = Value::obj(vec![
            (
                "messages",
                Value::List(vec![
                    Value::s("worker: REJECTED:abc BAD signed_by=x rejected_by=y"),
                    Value::s("worker: REJECTED:2 OK signed_by=x rejected_by=y"),
                    Value::s("worker: REJECTED"),
                    Value::s("worker: job 3 was rejected yesterday"),
                ]),
            ),
            ("jobs", Value::List(vec![])),
        ]);
        if !rejected_only(&watchdog.tick(&malformed, Some(NOW))).is_empty() {
            return Err("malformed REJECTED lines fired an alert".to_string());
        }
        let line = "worker: REJECTED:4 BAD signed_by=spoof rejected_by=worker";
        let dup = Value::obj(vec![
            (
                "messages",
                Value::List(vec![
                    Value::s(line),
                    Value::s(line),
                    Value::obj(vec![
                        ("nick", Value::s("worker")),
                        ("text", Value::s(line)),
                    ]),
                ]),
            ),
            ("jobs", Value::List(vec![])),
        ]);
        let got = rejected_only(&watchdog.tick(&dup, Some(NOW)));
        if got.len() != 1 {
            return Err(format!(
                "duplicate lines yield {} alerts, not 1",
                got.len()
            ));
        }
        if got[0].get("dedupe_key").as_str() != Some("rejected-dispatch:4:BAD") {
            return Err(format!(
                "duplicate dedupe key is {:?}",
                got[0].get("dedupe_key").py_repr()
            ));
        }
        let expired = Value::obj(vec![
            (
                "messages",
                Value::List(vec![Value::obj(vec![
                    ("nick", Value::s("worker")),
                    (
                        "text",
                        Value::s(
                            "REJECTED:5 EXPIRED signed_by=overseer rejected_by=worker",
                        ),
                    ),
                ])]),
            ),
            ("jobs", Value::List(vec![])),
        ]);
        let got = rejected_only(&watchdog.tick(&expired, Some(NOW)));
        if got.len() != 1 || got[0].get("verdict").as_str() != Some("EXPIRED") {
            return Err(format!(
                "dict-shaped EXPIRED line yields {}",
                Value::List(got).py_repr()
            ));
        }
        Ok("clean: none; malformed: none; duplicates: one; dict-shaped EXPIRED: one".to_string())
    });

    stage(&mut stages, STAGE_NAMES[5], || {
        surface.reset_fake();
        let keyring2 = write_keyring();
        let keyring2_path = keyring2.to_string_lossy().to_string();
        let result = (|| -> Result<String, String> {
            let (code, _out, err) = surface.jobs_cli(
                JOB_NS,
                "worker",
                &argv(&[
                    "post",
                    "--title",
                    "Plain job",
                    "--spec",
                    "no signature on this one",
                ]),
            );
            if code != 0 {
                return Err(format!("unsigned post exited {}: {}", code, err));
            }
            let (code, out, err) = surface.jobs_cli(
                JOB_NS,
                "worker",
                &argv(&["claim", "1", "--secret-file", &keyring2_path]),
            );
            if code != 0 {
                return Err(format!("unsigned claim exited {}, not 0: {}", code, err));
            }
            if !out.contains("CLAIMED 1") {
                return Err(format!("claim output: {:?}", out));
            }
            if !err.to_lowercase().contains("unsigned") {
                return Err(format!("unsigned claim gave no warning: {:?}", err));
            }
            let messages: Vec<Value> = surface
                .pushes()
                .into_iter()
                .filter(|(key, _)| key == "muse-bus")
                .map(|(_, body)| Value::s(&body))
                .collect();
            let snapshot = Value::obj(vec![
                ("messages", Value::List(messages)),
                (
                    "jobs",
                    Value::List(vec![Value::obj(vec![
                        ("id", Value::s("1")),
                        ("status", Value::s("claimed")),
                        ("claim", Value::s("worker")),
                    ])]),
                ),
            ]);
            let got: Vec<Value> = watchdog
                .tick(&snapshot, Some(NOW))
                .into_iter()
                .filter(|a| a.get("kind").as_str() == Some("rejected-dispatch"))
                .collect();
            if !got.is_empty() {
                return Err(format!("unsigned claim fired {}", Value::List(got).py_repr()));
            }
            Ok("unsigned job claims with a warning, no rejected alert".to_string())
        })();
        let _ = std::fs::remove_file(&keyring2);
        result
    });

    // Keyring cleanup is best-effort, as in the source.
    let _ = std::fs::remove_file(&keyring);

    let ok = stages.iter().all(|s| s.ok);
    let mut lines: Vec<String> = vec![
        "INT-010 spoofed-dispatch drill: BAD signature refused, REJECTED alert visible, watchdog notes the refused job".to_string(),
        "Store: suite in-memory fake, job namespace muse-bus:tjob; keyring: fresh random secret per run, removed after the run".to_string(),
        format!("Clock: {} (fixed, so the drill is repeatable)", NOW),
    ];
    for s in &stages {
        lines.push(format!(
            "[{}] {}: {}",
            if s.ok { "PASS" } else { "FAIL" },
            s.name,
            s.detail
        ));
    }
    lines.push(format!(
        "RESULT: {}",
        if ok {
            "PASS, refusal chain holds end to end"
        } else {
            "FAIL"
        }
    ));
    DrillResult { ok, stages, lines }
}
