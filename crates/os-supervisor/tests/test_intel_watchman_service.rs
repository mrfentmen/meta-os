//! Parity tests for `os/tests/test_intel_watchman_service.py`.
//!
//! The repeating production loop: carried priors and journal,
//! sleeps only between cycles, max_cycles bounds, should_stop,
//! contained failures, and caller-input immutability.

use os_supervisor::watchman_service as service;
use serde_json::{json, Value};
use std::collections::BTreeMap;

// --- service tests ---

#[test]
fn priors_and_journal_carry_across_cycles() {
    use os_supervisor::watchman_service as service;
    let seen: std::rc::Rc<std::cell::RefCell<Vec<BTreeMap<String, Value>>>> =
        std::rc::Rc::new(std::cell::RefCell::new(Vec::new()));
    let seen_in = seen.clone();
    let sleeps: std::rc::Rc<std::cell::RefCell<Vec<u64>>> =
        std::rc::Rc::new(std::cell::RefCell::new(Vec::new()));
    let sleeps_in = sleeps.clone();
    let result = service::serve_cycles(
        &["alpha".to_string()],
        Some(Box::new(move |input: service::CycleInput| {
            seen_in.borrow_mut().push(input.priors.clone());
            let mut records = BTreeMap::new();
            records.insert("alpha".to_string(), json!({"watchman_alive": true, "last_tick": input.now}));
            Ok(service::CycleOutput {
                records,
                new_journal: vec![json!(format!("note-{}", input.now as i64))],
                diagnostics: Value::Object(Default::default()),
            })
        })),
        Some(Box::new(move || Some(1_000_000.0))),
        Some(Box::new(move |s: u64| sleeps_in.borrow_mut().push(s))),
        Some(2),
        Some(30),
        None,
        None,
        None,
        None,
    );
    assert_eq!(result.cycles_run, 2);
    assert_eq!(*sleeps.borrow(), vec![30]);
    let seen = seen.borrow();
    assert!(seen[0].is_empty());
    assert_eq!(seen[1]["alpha"]["last_tick"], json!(1_000_000.0));
    assert_eq!(result.journal, vec![json!("note-1000000"), json!("note-1000000")]);
}

#[test]
fn zero_cycles_runs_nothing() {
    use os_supervisor::watchman_service as service;
    let result = service::serve_cycles(
        &["alpha".to_string()],
        Some(Box::new(|_: service::CycleInput| panic!("must not run"))),
        None,
        None,
        Some(0),
        Some(30),
        None,
        None,
        None,
        None,
    );
    assert_eq!(result.cycles_run, 0);
    assert!(result.records.is_empty());
}

#[test]
fn should_stop_stops_without_sleep() {
    use os_supervisor::watchman_service as service;
    let sleeps: std::rc::Rc<std::cell::RefCell<Vec<u64>>> =
        std::rc::Rc::new(std::cell::RefCell::new(Vec::new()));
    let sleeps_in = sleeps.clone();
    let result = service::serve_cycles(
        &["alpha".to_string()],
        Some(Box::new(|input: service::CycleInput| {
            let mut records = BTreeMap::new();
            records.insert("alpha".to_string(), json!({"watchman_alive": true, "last_tick": input.now}));
            Ok(service::CycleOutput {
                records,
                new_journal: Vec::new(),
                diagnostics: Value::Object(Default::default()),
            })
        })),
        Some(Box::new(move || Some(1_000_000.0))),
        Some(Box::new(move |s: u64| sleeps_in.borrow_mut().push(s))),
        Some(5),
        Some(30),
        Some(Box::new(|index: usize, _, _| index == 0)),
        None,
        None,
        None,
    );
    assert_eq!(result.cycles_run, 1);
    assert!(sleeps.borrow().is_empty());
}

#[test]
fn raising_cycle_contained_and_loop_recovers() {
    use os_supervisor::watchman_service as service;
    let calls = std::rc::Rc::new(std::cell::RefCell::new(0usize));
    let calls_in = calls.clone();
    let result = service::serve_cycles(
        &["alpha".to_string()],
        Some(Box::new(move |_: service::CycleInput| {
            let mut n = calls_in.borrow_mut();
            *n += 1;
            if *n == 1 {
                return Err("RuntimeError".to_string());
            }
            let mut records = BTreeMap::new();
            records.insert("alpha".to_string(), json!({"watchman_alive": true}));
            Ok(service::CycleOutput {
                records,
                new_journal: Vec::new(),
                diagnostics: Value::Object(Default::default()),
            })
        })),
        Some(Box::new(move || Some(1_000_000.0))),
        Some(Box::new(|_: u64| {})),
        Some(2),
        Some(30),
        None,
        None,
        None,
        None,
    );
    assert_eq!(result.cycles_run, 2);
    assert_eq!(
        result.diagnostics_by_cycle[0].get("cycle_error").and_then(|v| v.as_str()),
        Some("RuntimeError")
    );
    assert_eq!(
        result.records.get("alpha").and_then(|r| r.get("watchman_alive")),
        Some(&json!(true))
    );
}

#[test]
fn raising_callback_and_stop_contained() {
    use os_supervisor::watchman_service as service;
    let result = service::serve_cycles(
        &["alpha".to_string()],
        Some(Box::new(|input: service::CycleInput| {
            let mut records = BTreeMap::new();
            records.insert("alpha".to_string(), json!({"watchman_alive": true, "last_tick": input.now}));
            Ok(service::CycleOutput {
                records,
                new_journal: Vec::new(),
                diagnostics: Value::Object(Default::default()),
            })
        })),
        Some(Box::new(move || Some(1_000_000.0))),
        Some(Box::new(|_: u64| {})),
        Some(2),
        Some(30),
        Some(Box::new(|_: usize, _, _| -> bool { panic!("stop boom") })),
        Some(Box::new(|_: usize, _, _: &[Value], _: &Value| panic!("callback boom"))),
        None,
        None,
    );
    assert_eq!(result.cycles_run, 2);
    // Both raises are contained (panics recorded, loop continues).
    assert_eq!(result.callback_errors.len(), 2);
}

#[test]
fn sleep_only_between_cycles() {
    use os_supervisor::watchman_service as service;
    let sleeps: std::rc::Rc<std::cell::RefCell<Vec<u64>>> =
        std::rc::Rc::new(std::cell::RefCell::new(Vec::new()));
    let sleeps_in = sleeps.clone();
    let result = service::serve_cycles(
        &["alpha".to_string()],
        Some(Box::new(|input: service::CycleInput| {
            let mut records = BTreeMap::new();
            records.insert("alpha".to_string(), json!({"watchman_alive": true, "last_tick": input.now}));
            Ok(service::CycleOutput {
                records,
                new_journal: Vec::new(),
                diagnostics: Value::Object(Default::default()),
            })
        })),
        Some(Box::new(move || Some(1_000_000.0))),
        Some(Box::new(move |s: u64| sleeps_in.borrow_mut().push(s))),
        Some(3),
        Some(7),
        None,
        None,
        None,
        None,
    );
    assert_eq!(result.cycles_run, 3);
    assert_eq!(*sleeps.borrow(), vec![7, 7]);
}

#[test]
fn negative_interval_means_no_sleep_delay() {
    use os_supervisor::watchman_service as service;
    let sleeps: std::rc::Rc<std::cell::RefCell<Vec<u64>>> =
        std::rc::Rc::new(std::cell::RefCell::new(Vec::new()));
    let sleeps_in = sleeps.clone();
    service::serve_cycles(
        &["alpha".to_string()],
        Some(Box::new(|input: service::CycleInput| {
            let mut records = BTreeMap::new();
            records.insert("alpha".to_string(), json!({"watchman_alive": true, "last_tick": input.now}));
            Ok(service::CycleOutput {
                records,
                new_journal: Vec::new(),
                diagnostics: Value::Object(Default::default()),
            })
        })),
        Some(Box::new(move || Some(1_000_000.0))),
        Some(Box::new(move |s: u64| sleeps_in.borrow_mut().push(s))),
        Some(2),
        Some(-5),
        None,
        None,
        None,
        None,
    );
    assert_eq!(*sleeps.borrow(), vec![0, 0]);
}

#[test]
fn inputs_never_mutated() {
    use os_supervisor::watchman_service as service;
    let machines = vec!["alpha".to_string()];
    let priors = BTreeMap::from([("alpha".to_string(), json!({"watchman_alive": false}))]);
    let journal = vec![json!("old")];
    let before = (machines.clone(), priors.clone(), journal.clone());
    service::serve_cycles(
        &machines,
        Some(Box::new(|input: service::CycleInput| {
            Ok(service::CycleOutput {
                records: input.priors,
                new_journal: Vec::new(),
                diagnostics: Value::Object(Default::default()),
            })
        })),
        Some(Box::new(move || Some(1_000_000.0))),
        Some(Box::new(|_: u64| {})),
        Some(1),
        Some(30),
        None,
        None,
        Some(priors),
        Some(journal),
    );
    // Caller-owned inputs come back unchanged (the loop clones).
    assert_eq!(before.0, machines);
}

