# `os-jobs` — callers, and what they expect

B031. Two callers exist in two different worlds: the Rust crate has no
production caller yet, while the Python original it ports is imported
by a large part of `os/`. The table separates them so nobody reads a
Python expectation as a Rust integration.

## The Rust crate (`crates/os-jobs`)

| Caller | What it uses | Expectation | Flag |
|---|---|---|---|
| `crates/os-jobs/src/lib.rs` `mod tests` | every public item | the ported Python cases, same name roots (2604-4347) | none |
| `crates/os-jobs/tests/error_paths.rs` (this lane) | `JobQueue`, `JobStore`, `PostArgs`, `FakeStore`, `FakeClock`, `CmdOutcome`, `EnvRecord`, `parse_keyring`, keys | exit codes and messages as the code returns them | none |
| `crates/os-jobs/tests/edge_cases.rs` (this lane) | `JobQueue`, `PostArgs`, `FakeStore` | empty/max/duplicate/out-of-order real behaviour | none |
| `crates/os-jobs/tests/gap_close.rs` (this lane) | the pure encoders (`sha256`, `hmac_sha256`, `json_escape`, `canonical_*`, `url_*`, `ct_eq`, `python_repr`, `hex_digest`) | fixed published vectors | none |
| `crates/parity-tests/src/tests/test_os094_job_artifacts.rs` | **its own copy** of `parse_artifact_ref` (line 37), not `os_jobs::parse_artifact_ref` | same shape `(String, String, u64)` | it duplicates the rule instead of calling the crate; a change in the crate will not fail that test. Flagged, not changed (parity-tests is another batch's file). |
| `crates/os-supervisor/src/overseer.rs:19` | nothing | comment explicitly says it does **not** import `os-jobs` | none |
| workspace `Cargo.toml:16` | the package as a member | builds with `cargo test -p os-jobs` | none |

**No production Rust binary or service constructs a `JobQueue` today.**
That is the single biggest integration gap: the crate is a library with
tests, not a running queue. G1 (transport) and G3 (CLI) in
`os-jobs-gaps.md` are the blockers.

## The Python original (`os/jobs.py`) — what its callers expect

These are not callers of the Rust crate. They are the behaviour the
port must eventually replace, and they show what a real caller needs.

| Caller | Call | Expectation | Does the Rust crate provide it? |
|---|---|---|---|
| `os/intel/dispatch.py:1436,1696` | `jobs.main(argv)` | a CLI that prints `JOB <id>` and returns an exit code | **No** — methods exist, no argv parser (G3) |
| `os/intel/e2e1.py:273-279` | `jobs.main(["claim", …])`, `progress`, `done` | same CLI triples | **No** (G3) |
| `os/intel/e2e3.py:256-313` | `jobs.main([...])` | same CLI triples | **No** (G3) |
| `os/intel/dispatch.py:1765,1778,1830` | `jobs.job_get(job_id)` | `(dict, spec_text)`; a missing job is `(None, "")` | **Yes**, same pair (`Option<HashMap>, String`, 1035-1057) |
| `os/intel/drills/trust_enforcement.py:72` | `jobs._sign_job_v2(...)` | a private helper used to build fixtures | **Yes**, public `sign_job_v2` (650-670); the Rust name is public, not private |
| `os/intel/drills/trust_negative.py:104` | `jobs._sign_job_v2(...)` | same | **Yes** as above |
| `os/tests/test_os094_job_artifacts.py:66-70` | `jobs.parse_artifact_ref(...)` | `(job, name, version)` or `None`; v0/backslash/None rejected | **Yes**, with `u64` versions (G9) |
| `os/mos/overseer.py:23`, `os/mos/reconcile.py:21`, `os/mos/worker.py:32` | `import jobs` then `job_get`/commands | dict-shaped job rows; status words | **Partly** — rows are `HashMap<String,String>`, same text values |
| `os/intel/watchdog.py:442-718` | reads `deps`/`files`/`attempts` in their stored comma/int form | the hash shape, not the API | **Yes** — `post` writes the same text shape (1423-1435) |
| `os/intel/brief.py:1098-1400,2589` | `environment_jobs_record`, `environment_lines` | claimed jobs only; not-reported wording | **Yes** (2318-2597) |
| `os/tests/helpers.py:13` | `import jobs`; `run_cli(jobs.main, ...)` | CLI capture | **No** (G3) |

## Flags

1. **A Rust caller cannot go through a CLI yet.** Every Python
   integration calls `jobs.main`; the Rust crate exposes methods only.
   Any port of `intel/dispatch.py` must either call methods directly
   (and lose the CLI's message text) or wait for G3.
2. **`job_get` shape differs by language, not by behaviour.** Python
   returns a dict; Rust returns `(Option<HashMap>, String)`. The values
   are the same text; a port must not expect ints from `attempts` or
   `lease` (they are stored as strings; `list --json` converts).
3. **`parity-tests` duplicates `parse_artifact_ref`.** Its shape test
   passes independently of this crate. If the crate's rule changes, the
   parity test will not notice; that is a wiring defect in the test, not
   a crate defect.
4. **The Python module is imported by ~40 files** (`intel/`, `mos/`,
   `tests/`). None of those imports resolve to the Rust crate; a cutover
   needs a shim or a re-pointed import, and neither exists.
