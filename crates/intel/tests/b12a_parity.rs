//! B12a parity — honest version (Pax, replacing the fleet's
//! stub-era test, which called argument-free `run()`s that
//! only existed in the shallow stub ports and asserted every
//! stub passed).
//!
//! What runs here: the behavior that is self-contained in
//! the B12a port itself — the SHA-256 implementation, the
//! Python-semantics Value layer, the soak review logic, the
//! security scan, the boot self-check fixtures, the tuning
//! case table, and the demo drop-in env parsing. These are
//! real assertions over the ported code.
//!
//! What does NOT run here yet, by design: every drill whose
//! behavior rides a sibling-batch surface (watchdog B21,
//! gate/baton/ladder B09, brief/dispatch/wake B10, spark
//! B11, trust/timer-sweep B14, jobs signing B16). Those
//! ports take the surface as a trait; until the owning
//! batches land implementations, there is nothing honest to
//! run them against. They are listed as ignored tests below
//! so gate 1 has the checklist in one place — un-ignore
//! each as its surface lands. The B09/B31 test lists carry
//! the caller-side cases for the same behavior.

use intel::b12a_drills::deps::Thresholds;
use intel::b12a_drills::drills::demo_thresholds_dropin;
use intel::b12a_drills::sha256::sha256_hex;
use intel::b12a_drills::value::{parse_json, py_float_str, to_json, Value};
use intel::b12a_drills::{boot_selfcheck, sam_check, security_pass, soak_review, watchdog_tuning};

#[test]
fn sha256_known_vectors() {
    // FIPS 180-4 examples — the from-scratch implementation
    // the sam_check and trust drills stand on.
    assert_eq!(
        sha256_hex(b""),
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    );
    assert_eq!(
        sha256_hex(b"abc"),
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    );
    assert_eq!(
        sha256_hex(b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"),
        "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"
    );
}

#[test]
fn value_json_round_trip_and_python_formatting() {
    let parsed = parse_json(
        "{\"a\": 1, \"b\": [true, null, \"x\"], \"c\": 2.5}",
    )
    .expect("fixture parses");
    assert_eq!(parsed.get("a"), Value::Int(1));
    assert_eq!(parsed.get("c"), Value::Float(2.5));
    // Python str(float) keeps the trailing .0; dict order is
    // insertion order through a dump/parse cycle.
    assert_eq!(py_float_str(2.0), "2.0");
    assert_eq!(Value::Float(2.0).py_str(), "2.0");
    let reparsed = parse_json(&to_json(&parsed)).expect("round trip parses");
    assert_eq!(reparsed, parsed);
    // Missing keys read as Null, the port's dict.get default.
    assert_eq!(parsed.get("missing"), Value::Null);
}

#[test]
fn soak_review_clean_and_gap_weeks() {
    // The drill fixtures, run through the ported reviewer.
    let journal = intel::b12a_drills::drills::soak_review::clean_journal();
    let report = soak_review::review_journal(&journal);
    assert_eq!(report.get("verdict").as_str(), Some("clean"));
    assert_eq!(report.get("total_failures").as_int(), Some(3));
    assert_eq!(report.get("covered_failures").as_int(), Some(3));
    assert_eq!(report.get("unexplained_gaps"), Value::List(vec![]));

    let gap_journal = Value::List(
        journal
            .as_list()
            .unwrap()
            .iter()
            .filter(|e| {
                !(e.get("kind").as_str() == Some("bug")
                    && e.get("failure_id").as_str() == Some("f2"))
            })
            .cloned()
            .collect(),
    );
    let gap = soak_review::review_journal(&gap_journal);
    assert_eq!(gap.get("verdict").as_str(), Some("gaps"));
    assert_eq!(
        gap.get("unexplained_gaps"),
        Value::List(vec![Value::s("f2")])
    );
    assert!(soak_review::soak_brief_lines(&gap)
        .iter()
        .any(|line| line.contains("f2")));
    // A non-list journal reads as empty, never crashes.
    assert_eq!(
        soak_review::review_journal(&Value::Null)
            .get("total_failures")
            .as_int(),
        Some(0)
    );
}

#[test]
fn security_pass_clean_tree_and_skip_dirs() {
    let root = std::env::temp_dir().join(format!(
        "b12a_parity_security_{}",
        std::process::id()
    ));
    let _ = std::fs::remove_dir_all(&root);
    std::fs::create_dir_all(root.join(".git")).unwrap();
    std::fs::write(root.join("clean.txt"), b"nothing to see here\n").unwrap();
    // Content inside a skipped directory is never scanned.
    std::fs::write(root.join(".git/config"), b"token = aaaaaaaaaaaaaaaa\n").unwrap();
    let (findings, _fixtures, scanned) = security_pass::scan_root(&root);
    assert!(findings.is_empty(), "clean tree findings: {:?}", findings);
    assert_eq!(scanned, 1);
    let _ = std::fs::remove_dir_all(&root);
}

#[test]
fn boot_selfcheck_fixture_shape() {
    let expected = boot_selfcheck::expected();
    let kinds = expected.as_map().expect("expected() is a map");
    assert_eq!(kinds.len(), 10);
    assert!(kinds.iter().all(|(_, v)| *v == Value::Int(1)));
    let fixture = boot_selfcheck::seeded_fixture(100000, &Thresholds::locked());
    assert!(fixture.is_dict());
    assert!(!fixture.get("jobs").as_list().unwrap().is_empty());
}

#[test]
fn watchdog_tuning_case_table() {
    let cases = watchdog_tuning::cases();
    assert_eq!(cases.len(), 26);
    assert!(cases.iter().all(|c| !c.name.is_empty() && !c.detector.is_empty()));
    assert_eq!(watchdog_tuning::NOW, 10000);
}

#[test]
fn demo_thresholds_dropin_env_parsing() {
    let env = demo_thresholds_dropin::parse_env_file(
        "# comment\n\nWATCHDOG_STALL_MINUTES=1\nNO_EQUALS_LINE\nOTHER= x \n",
    );
    assert_eq!(env.get("WATCHDOG_STALL_MINUTES"), Value::s("1"));
    assert_eq!(env.get("OTHER"), Value::s("x"));
    assert!(!env.contains_key("NO_EQUALS_LINE"));
    let vars = demo_thresholds_dropin::watchdog_vars(&env);
    assert_eq!(vars.len(), 1);
    let resolved = Thresholds::from_env_map(&vars);
    assert_eq!(resolved.stall_minutes, 1);
    // Everything unset stays at the production default.
    assert_eq!(resolved.progress_stall_minutes, 10);
    assert_eq!(demo_thresholds_dropin::expected_thresholds().stall_minutes, 1);
}

#[test]
fn sam_check_constants() {
    assert_eq!(sam_check::SET_ID, "sam-eval-alerts-panel-v1");
    assert_eq!(sam_check::PNG_MAGIC[0], 0x89);
}

// ----------------------------------------------------------------
// Gate-1 checklist: drills blocked on sibling-batch surfaces.
// Each un-ignores when the named surface has an implementation
// to run against. Do not delete; do not fake a pass.
// ----------------------------------------------------------------

#[test]
#[ignore = "gate 1: needs the B21 watchdog implementation (tick, detectors, journal watch, restart note)"]
fn drills_behind_watchdog_surface() {}

#[test]
#[ignore = "gate 1: needs B09 gate/store/capability/ladder implementations"]
fn drills_behind_b09_surfaces() {}

#[test]
#[ignore = "gate 1: needs B10 brief/dispatch/push/baton/wake implementations"]
fn drills_behind_b10_surfaces() {}

#[test]
#[ignore = "gate 1: needs B11 spark client + B14 trust/timer-sweep + B16 jobs signing implementations"]
fn drills_behind_spark_trust_jobs_surfaces() {}

#[test]
#[ignore = "gate 1: needs a PanelDriver implementation (browser seat) for sam_render"]
fn sam_render_behind_panel_driver() {}
