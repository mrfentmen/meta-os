# Public surface of `crates/os-boot` (B010)

Every `pub` name, one line each. "Used" means referenced outside its defining module **in this
repository**, including tests; there is no production caller of the crate (see
`os-boot-callers.md`), so "tests only" is the strongest use that exists today.

## `lib.rs`

| Name | Kind | Used? |
|---|---|---|
| `carried` | module | yes — `carried` tests |
| `cli` | module | yes — `git` tests import `crate::cli` |
| `git` | module | yes — `git` tests |

## `carried`

| Name | Kind | Used? |
|---|---|---|
| `CARRIED` | `&[&str]` const, 47 entries | tests only (`carried.rs:107-140`) |
| `CARRIED_COUNT` | `usize` const = 47 | tests only (`:107-110`) |
| `source_path` | `fn(&str) -> PathBuf` | tests only (`:112-128`) |
| `asset_path` | `fn(&str) -> PathBuf` | tests only (`:112-140`) |

## `cli` — types

| Name | Kind | Used? |
|---|---|---|
| `CliOutcome` | struct `{ code: i32, out: String, err: String }` | yes — every `cmd_*` return |
| `AgentRecord` | struct `{ caps, roles, host, updated: String }` | yes — `cmd_caps` |
| `CapabilitiesBackend` | trait `register`, `agents` | yes — `cmd_register`/`cmd_caps`; **no impl** |
| `TickReport` | struct `{ swept, pruned, verified, failed, errors: Vec<String> }` | yes — `cmd_tick` |
| `OverseerBackend` | trait `dispatch`, `tick`, `verify_done` | yes — three commands; **no impl** |
| `WorkerBackend` | trait `register`, `heartbeat`, `poll_dms`, `matches`, `claim`, `job_spec` | yes — `cmd_worker_once`; **no impl** |
| `ReconcileBackend` | trait `main` | yes — `cmd_reconcile`; **no impl** |
| `ReviewSummary` | struct `{ branch, base, files, stat, commits, commit_count }` | yes — `git`, `cmd_review` |
| `GitError` | tuple struct `String` + `Display` | yes — `git`, `cmd_review`/`cmd_merge` |
| `GitopsBackend` | trait `review_branch`, `approve_merge` | yes — `cmd_review`/`cmd_merge`; one impl (`GitCliBackend`) |
| `Backends<'a>` | struct of five trait references | yes — `run_cli` |

## `cli` — functions

| Name | Signature (abridged) | Used? |
|---|---|---|
| `expand_text` | `(&str) -> Result<String, String>` | yes — `cmd_dispatch` |
| `split_caps` | `(&str) -> Vec<String>` | yes — `cmd_register`, `cmd_dispatch` |
| `cmd_register` | `(nick, caps, roles, max_jobs, dm, &mut dyn CapabilitiesBackend) -> CliOutcome` | yes — `run_cli` + tests |
| `cmd_caps` | `(&dyn CapabilitiesBackend) -> CliOutcome` | yes — `run_cli` + tests |
| `cmd_dispatch` | 9 args incl. `&mut dyn OverseerBackend` | yes — `run_cli` + tests |
| `cmd_tick` | `(Option<&str>, Option<&str>, &dyn OverseerBackend) -> CliOutcome` | yes — `run_cli` + tests |
| `cmd_verify` | `(&str, Option<&str>, Option<&str>, &dyn OverseerBackend) -> CliOutcome` | yes — `run_cli` + tests |
| `cmd_worker_once` | `(&mut dyn WorkerBackend) -> CliOutcome` | yes — `run_cli` + tests |
| `cmd_reconcile` | `(&dyn ReconcileBackend) -> CliOutcome` | yes — `run_cli` + tests |
| `cmd_review` | `(&str, &str, &str, &dyn GitopsBackend) -> CliOutcome` | yes — `run_cli` + git tests |
| `cmd_merge` | `(&str, &str, &str, &dyn GitopsBackend) -> CliOutcome` | yes — `run_cli` + git tests |
| `run_cli` | `(&[String], &mut Backends) -> CliOutcome` | tests only (`cli.rs:1102-1160`) |

## `git`

| Name | Signature (abridged) | Used? |
|---|---|---|
| `is_repo` | `(&str) -> bool` | yes — `review_branch` |
| `current_branch` | `(&str) -> Result<String, GitError>` | yes — `approve_merge` |
| `clean_tree` | `(&str) -> Result<bool, GitError>` | yes — `approve_merge` |
| `branch_exists` | `(&str, &str) -> bool` | yes — `review_branch`, `approve_merge` |
| `review_branch` | `(&str, &str, &str) -> Result<ReviewSummary, GitError>` | yes — `GitCliBackend` + tests |
| `approve_merge` | `(&str, &str, &str) -> Result<String, GitError>` | yes — `GitCliBackend` + tests |
| `GitCliBackend` | unit struct implementing `GitopsBackend` | tests only (`git.rs:192-243`) |

## Exported methods and fields (trait surface)

| Owner | Member | Used? |
|---|---|---|
| `CapabilitiesBackend` | `register`, `agents` | tests fake only |
| `OverseerBackend` | `dispatch`, `tick`, `verify_done` | tests fake only |
| `WorkerBackend` | `register`, `heartbeat`, `poll_dms`, `matches`, `claim`, `job_spec` | tests fake only |
| `ReconcileBackend` | `main` | tests fake only |
| `GitopsBackend` | `review_branch`, `approve_merge` | `GitCliBackend` + tests |
| `CliOutcome` | `code`, `out`, `err` (pub fields) | every command |
| `TickReport` | five `Vec<String>` pub fields | `cmd_tick` |
| `ReviewSummary` | six pub fields | `cmd_review` |
| `AgentRecord` | four pub `String` fields | `cmd_caps` |
| `Backends` | five pub fields | `run_cli` |

## Unused-in-repo names

- `run_cli` — no production caller.
- `GitCliBackend` — no production caller.
- All five backend traits — no production implementor.
- `CARRIED`, `CARRIED_COUNT`, `source_path`, `asset_path` — tests only.
