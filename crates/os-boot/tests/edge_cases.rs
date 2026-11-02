//! B003 — edge cases named for the case: empty, maximum, duplicate, out-of-order.
//!
//! Each test is one case, against the public API. Nothing here re-tests a refusal already
//! covered by `error_paths.rs`; the subject is the boundary, not the error.

use os_boot::cli::{
    run_cli, split_caps, AgentRecord, Backends, CapabilitiesBackend, CliOutcome, GitError,
    GitopsBackend, OverseerBackend, ReconcileBackend, ReviewSummary, TickReport, WorkerBackend,
};
use std::collections::HashMap;

// ---------------------------------------------------------------- fakes

struct Caps {
    last: Option<(String, Vec<String>)>,
}
impl CapabilitiesBackend for Caps {
    fn register(
        &mut self,
        nick: &str,
        caps: &[String],
        _roles: &str,
        _max: i64,
        _dm: &str,
    ) -> Result<(), String> {
        self.last = Some((nick.to_string(), caps.to_vec()));
        Ok(())
    }
    fn agents(&self) -> HashMap<String, AgentRecord> {
        HashMap::new()
    }
}

struct Overseer {
    last_title: String,
    last_lease: i64,
}
impl OverseerBackend for Overseer {
    fn dispatch(
        &mut self,
        title: &str,
        _spec: &str,
        _accept: &str,
        _req: &[String],
        _room: &str,
        lease: i64,
        _branch: &str,
        _base: &str,
    ) -> (String, Vec<(String, bool, String)>) {
        self.last_title = title.to_string();
        self.last_lease = lease;
        ("1".to_string(), vec![])
    }
    fn tick(&self, _r: Option<&str>, _w: Option<&str>) -> TickReport {
        TickReport::default()
    }
    fn verify_done(&self, _j: &str, _r: Option<&str>, _w: Option<&str>) -> (bool, String) {
        (true, String::new())
    }
}

struct Worker;
impl WorkerBackend for Worker {
    fn register(&mut self) {}
    fn heartbeat(&mut self) {}
    fn poll_dms(&mut self) -> Vec<(String, String, Vec<String>)> {
        vec![]
    }
    fn matches(&self, _r: &[String]) -> bool {
        true
    }
    fn claim(&mut self, _j: &str) -> (bool, String) {
        (true, String::new())
    }
    fn job_spec(&self, _j: &str) -> String {
        String::new()
    }
}

struct Rec;
impl ReconcileBackend for Rec {
    fn main(&self, _a: &[String]) -> i32 {
        0
    }
}

struct Git;
impl GitopsBackend for Git {
    fn review_branch(&self, _r: &str, _b: &str, _base: &str) -> Result<ReviewSummary, GitError> {
        Err(GitError("unused".into()))
    }
    fn approve_merge(&self, _r: &str, _b: &str, _base: &str) -> Result<String, GitError> {
        Err(GitError("unused".into()))
    }
}

struct Fx {
    caps: Caps,
    ov: Overseer,
    worker: Worker,
    rec: Rec,
    git: Git,
}

fn fx() -> Fx {
    Fx {
        caps: Caps { last: None },
        ov: Overseer {
            last_title: String::new(),
            last_lease: 0,
        },
        worker: Worker,
        rec: Rec,
        git: Git,
    }
}

fn call(f: &mut Fx, argv: &[&str]) -> CliOutcome {
    let owned: Vec<String> = argv.iter().map(|s| s.to_string()).collect();
    let mut b = Backends {
        caps: &mut f.caps,
        overseer: &mut f.ov,
        worker: &mut f.worker,
        reconcile: &f.rec,
        gitops: &f.git,
    };
    run_cli(&owned, &mut b)
}

// ---------------------------------------------------------------- empty

#[test]
fn empty_argv_is_the_empty_case() {
    let mut f = fx();
    let out = call(&mut f, &[]);
    assert_eq!(out.code, 2);
    assert!(out.out.is_empty());
    assert!(out.err.starts_with("usage: mos.py"), "{}", out.err);
}

#[test]
fn empty_caps_string_registers_with_no_capabilities() {
    let mut f = fx();
    let out = call(&mut f, &["register", "--caps", "", "--dm", "s"]);
    assert_eq!(out.code, 0);
    assert_eq!(out.out, "REGISTERED : \n");
    assert_eq!(f.caps.last.as_ref().unwrap().1, Vec::<String>::new());
}

#[test]
fn whitespace_only_caps_is_empty() {
    let mut f = fx();
    let out = call(&mut f, &["register", "--caps", " , , ", "--dm", "s"]);
    assert_eq!(out.code, 0);
    assert_eq!(out.out, "REGISTERED : \n");
}

#[test]
fn an_at_sign_alone_is_an_empty_path_and_refuses() {
    // "@" strips to the empty path, which cannot be read.
    assert!(os_boot::cli::expand_text("@").is_err());
}

// ---------------------------------------------------------------- maximum

#[test]
fn maximum_input_passes_through_untouched() {
    // 1 MiB of text: expand_text has no length limit; it must not truncate.
    let big = "x".repeat(1024 * 1024);
    let got = os_boot::cli::expand_text(&big).unwrap();
    assert_eq!(got.len(), big.len());
    assert_eq!(got, big);
}

#[test]
fn maximum_caps_string_keeps_every_entry() {
    let many = (0..1000).map(|i| format!("c{i}")).collect::<Vec<_>>().join(",");
    let got = split_caps(&many);
    assert_eq!(got.len(), 1000);
    assert_eq!(got[0], "c0");
    assert_eq!(got[999], "c999");
}

// ---------------------------------------------------------------- duplicate

#[test]
fn duplicate_caps_are_kept_in_order() {
    assert_eq!(
        split_caps("a,a,b,a"),
        vec!["a".to_string(), "a".to_string(), "b".to_string(), "a".to_string()]
    );
}

#[test]
fn duplicate_flags_take_the_first_value() {
    let mut f = fx();
    let out = call(
        &mut f,
        &[
            "--title", "FIRST", "--title", "SECOND", "--spec", "s",
        ],
    );
    // The argv above has no subcommand, so it is a usage error; the real case below has one.
    assert_eq!(out.code, 2);
    let out = call(
        &mut f,
        &[
            "dispatch", "--title", "FIRST", "--title", "SECOND", "--spec", "s",
        ],
    );
    assert_eq!(out.code, 0);
    assert_eq!(f.ov.last_title, "FIRST", "first occurrence wins");
}

// ---------------------------------------------------------------- out of order

#[test]
fn flags_in_reverse_order_parse_the_same() {
    let mut f = fx();
    let out = call(
        &mut f,
        &[
            "dispatch", "--lease", "7", "--spec", "s", "--title", "T",
        ],
    );
    assert_eq!(out.code, 0);
    assert_eq!(f.ov.last_title, "T");
    assert_eq!(f.ov.last_lease, 7, "the lease is not positional-dependent");
}

#[test]
fn equals_form_and_space_form_agree() {
    let mut f = fx();
    let a = call(&mut f, &["dispatch", "--title=T", "--spec=s", "--lease=9"]);
    assert_eq!(a.code, 0);
    assert_eq!(f.ov.last_title, "T");
    assert_eq!(f.ov.last_lease, 9);
    let b = call(&mut f, &["dispatch", "--title", "U", "--spec", "s", "--lease", "10"]);
    assert_eq!(b.code, 0);
    assert_eq!(f.ov.last_title, "U");
    assert_eq!(f.ov.last_lease, 10);
}
