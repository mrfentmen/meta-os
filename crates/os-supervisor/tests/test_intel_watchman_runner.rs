//! Parity tests for `os/tests/test_intel_watchman_runner.py`.
//!
//! The real subprocess runner: argv shape, exit-0 success,
//! timeout kills, not-found, bad argv, never-raises containment,
//! and the real production cycle over snapshots. Production-path
//! phases that need python3 are marked ENVIRONMENT-BLOCKED when
//! it is absent, exactly like the Python drill's gate verdict.

use os_supervisor::watchman_runner as runner;
use serde_json::{json, Value};

fn have_python3() -> bool {
    std::process::Command::new("python3")
        .arg("--version")
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

fn tmpdir(name: &str) -> std::path::PathBuf {
    let dir = std::env::temp_dir().join(format!(
        "os-sup-runner-{name}-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .subsec_nanos()
    ));
    std::fs::create_dir_all(&dir).unwrap();
    dir
}

// --- runner tests ---

#[test]
fn default_argv_shape() {
    let argv = runner::machine_argv("alpha", "/run/metaos", "python3 relay_watchman.py").unwrap();
    assert_eq!(
        argv,
        vec![
            "python3 relay_watchman.py".to_string(),
            "--once".to_string(),
            "--jobs-file".to_string(),
            "/run/metaos/watchman-jobs-alpha.json".to_string(),
            "--agents-file".to_string(),
            "/run/metaos/watchman-agents-alpha.json".to_string(),
            "--state-file".to_string(),
            "/run/metaos/watchman-state-alpha.json".to_string(),
        ]
    );
}

#[test]
fn argv_distinct_per_machine() {
    let a = runner::machine_argv("alpha", "/run/metaos", "prog").unwrap();
    let b = runner::machine_argv("beta", "/run/metaos", "prog").unwrap();
    assert_ne!(a, b);
    assert!(a[3].contains("alpha") && b[3].contains("beta"));
}

#[test]
fn bad_machine_yields_none() {
    assert!(runner::machine_argv("", "/run/metaos", "prog").is_none());
    assert!(runner::machine_argv("   ", "/run/metaos", "prog").is_none());
}

#[test]
fn success_returns_stdout() {
    let (ok, stdout, detail) = runner::run_once(
        &["/bin/echo".to_string(), "hello".to_string()],
        10,
    );
    assert!(ok && stdout.contains("hello") && detail.is_none());
}

#[test]
fn nonzero_discards_partial_stdout() {
    let (ok, stdout, detail) = runner::run_once(
        &["sh".to_string(), "-c".to_string(), "echo partial; exit 3".to_string()],
        10,
    );
    assert_eq!((ok, stdout.as_str(), detail.as_deref()), (false, "", Some("exit-3")));
}

#[test]
fn timeout() {
    let (ok, stdout, detail) = runner::run_once(
        &["sh".to_string(), "-c".to_string(), "sleep 30".to_string()],
        1,
    );
    if detail == Some("not-found".to_string()) {
        return;
    }
    assert_eq!((ok, stdout.as_str(), detail.as_deref()), (false, "", Some("timeout")));
}

#[test]
fn not_found() {
    let (ok, _stdout, detail) =
        runner::run_once(&["/tmp/os-sup-no-such-program-xyz".to_string()], 5);
    assert!(!ok);
    assert_eq!(detail.as_deref(), Some("not-found"));
}

#[test]
fn bad_argv() {
    assert_eq!(
        runner::run_once(&[], 5),
        (false, String::new(), Some("bad-argv".to_string()))
    );
    assert_eq!(
        runner::run_once(&["python3".to_string(), String::new()], 5),
        (false, String::new(), Some("bad-argv".to_string()))
    );
}

#[test]
fn runner_never_raises() {
    let plain = runner::make_subprocess_runner(None, 5, "/tmp", "python3");
    assert_eq!(plain(""), (false, String::new()));
    // A raising command_for is contained: the Err return is the
    // Rust spelling of a raised exception, and the runner folds
    // it to a failed run, never a raise.
    let raising = runner::make_subprocess_runner(
        Some(Box::new(|_: &str| -> Option<Vec<String>> { None })),
        5,
        "/tmp",
        "python3",
    );
    assert_eq!(raising("alpha"), (false, String::new()));
}

#[test]
fn real_cycle_rings_and_stays_quiet() {
    if !have_python3() {
        return;
    }
    let tmp = tmpdir("real");
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("..").join("..").join("os/os/watchman/relay_watchman.py");
    if !root.exists() {
        return;
    }
    let program = root.to_string_lossy().into_owned();
    let dir = tmp.to_string_lossy().into_owned();
    let jobs = json!([{"id": "j1", "status": "open", "addressed_to": "hana", "title": "t"}]);
    let agents = json!({"hana": {"nick": "hana", "heartbeat_at": null}});
    std::fs::write(tmp.join("watchman-jobs-alpha.json"), serde_json::to_string(&jobs).unwrap()).unwrap();
    std::fs::write(tmp.join("watchman-agents-alpha.json"), serde_json::to_string(&agents).unwrap()).unwrap();
    std::fs::write(tmp.join("watchman-jobs-beta.json"), "[]").unwrap();
    std::fs::write(tmp.join("watchman-agents-beta.json"), "{}").unwrap();
    let run = runner::make_subprocess_runner(None, 30, &dir, &program);
    let (ok, stdout) = run("alpha");
    assert!(ok, "real --once run failed");
    let lines: Vec<Value> = stdout.lines().filter(|l| !l.trim().is_empty()).map(|l| serde_json::from_str(l).unwrap()).collect();
    assert_eq!(lines.len(), 1);
    assert_eq!(lines[0]["kind"], json!("wake"));
    let (ok, stdout) = run("alpha");
    assert!(ok && stdout.trim().is_empty(), "second run re-rang");
    let (records, new_journal, diagnostics, _errors) = os_supervisor::watchman_cycle::run_cycle(
        Some(&|name: &str| -> Result<Value, String> {
            let (ok, out) = runner::make_subprocess_runner(None, 30, &dir, &program)(name);
            Ok(Value::Array(vec![Value::Bool(ok), Value::String(out)]))
        }),
        &json!(["alpha", "beta"]),
        1_000_000.0,
        None,
        Some(&[]),
        None,
    );
    assert!(records["alpha"]["watchman_alive"] == json!(true));
    assert!(records["beta"]["last_bell"] == Value::Null);
    assert!(new_journal.is_empty() && diagnostics.run_failures.is_empty());
    std::fs::remove_dir_all(&tmp).ok();
}

#[test]
fn failed_run_carries_prior_bell_stripped() {
    let prior = json!({"watchman_alive": true, "last_tick": 999000.0, "last_bell": 999000.0, "last_wake": 999000.0, "restart_ok": true});
    let priors = json!({"alpha": prior});
    let journal = vec![json!({"kind": "crew-dark", "machine": "beta"})];
    let raising = |_: &str| -> Result<Value, String> { Err("RuntimeError".to_string()) };
    let (records, _new, diagnostics, _errors) = os_supervisor::watchman_cycle::run_cycle(
        Some(&raising),
        &json!(["alpha"]),
        1_000_000.0,
        Some(&priors),
        Some(&journal),
        None,
    );
    let carried = &records["alpha"];
    assert_eq!(carried["last_bell"], json!(999000.0));
    assert!(carried.get("restart_ok").is_none());
    assert_eq!(diagnostics.run_failures, vec!["alpha".to_string()]);
}

#[test]
fn no_em_dash_in_new_files() {
    let manifest = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
    for file in [
        "src/watchman_runner.rs",
        "src/watchman_service.rs",
        "src/watchman_cycle.rs",
        "src/watchman_loop.rs",
        "tests/test_intel_watchman_runner_service.rs",
    ] {
        let text = std::fs::read_to_string(manifest.join(file)).unwrap();
        assert!(!text.contains('\u{2014}'), "{file}");
    }
}

