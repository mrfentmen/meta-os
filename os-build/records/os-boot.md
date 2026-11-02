# Record — crate `os-boot`, from the code

Scope: `crates/os-boot` as it stands on `main` @ `6d8d54e` (2026-11-02).
Every claim cites a file and line range in the crate. The Python originals are cited only
where this record compares the port to them; their own behaviour is not described here.

Status word: **LIVE** means the code exists and is exercised by a test in the crate.
**UNWIRED** means the code exists but no production caller exists in this repository.

## What it is

Three modules, no binary target (`crates/os-boot/Cargo.toml:1-5`):

| Module | What it is | State |
|---|---|---|
| `carried` | The manifest of 47 deployment assets carried byte-identical from `os/os/`, plus source/asset path resolvers | LIVE |
| `cli` | The MOS command surface (`os/mos/cli.py`), dispatching through backend traits | UNWIRED as a program; tests only |
| `git` | A real git-CLI backend for `review` / `merge` | LIVE in tests; UNWIRED from a binary |

`lib.rs:58-60` declares exactly those three modules. There is no `main.rs`, no `[[bin]]`, and
no caller of `run_cli` anywhere outside the crate's own tests — so the crate is a library today,
not a command that can be run.

## carried — the manifest

- `CARRIED` (`carried.rs:29-85`) is the ordered list of 47 entries, grouped by the batch task
  that carried them: T153 (10 systemd units), T154 (10 more), T155 (10 docs/bin/build scripts),
  T156 (9 image-build files), Meta Custos stage 2 (4), metaos-loop (4). `CARRIED_COUNT = 47`
  (`carried.rs:88`).
- `source_path(entry)` (`carried.rs:91-95`) resolves `<repo>/os/<entry>` using the compile-time
  `CARGO_MANIFEST_DIR`. `asset_path(entry)` (`carried.rs:97-101`) resolves
  `<crate>/assets/<entry>`. Neither returns a `Result`: a bad entry becomes a bad path, and the
  failure appears only when the caller opens it.
- The binding test is byte identity, one panic per file naming the entry
  (`carried.rs:112-128`). A count test (`carried.rs:107-110`) and a unit-shape test
  (`carried.rs:130-140`) guard the manifest itself.

Refusals: none. The module has no rejecting branch. A missing source or asset is a test panic,
not a typed error.

## cli — the command surface

### Entry and value types

- `run_cli(argv, backends)` (`cli.rs:538-695`) is the whole dispatcher. `argv` excludes the
  program name; an empty `argv` is usage + exit 2 (`cli.rs:539-541`).
- `CliOutcome { code, out, err }` (`cli.rs:40-70`) is the return shape; each line is
  newline-terminated (`cli.rs:49-68`).
- `split_caps` (`cli.rs:257-261`) splits on `,`, drops entries whose `trim()` is empty, and keeps
  the surviving strings **verbatim** — `" testing "` keeps its spaces.
- `expand_text` (`cli.rs:235-254`) reads `@file`, expands a leading `~/` through `HOME`, and
  otherwise passes the string through. A read failure is `cannot read <path>: <os error>`.

### Commands and their output

| Command | Function | Output contract |
|---|---|---|
| `register` | `cmd_register` (`263-285`) | `REGISTERED <nick>: <sorted caps>`; backend error → `ERROR: <e>` + exit 1 |
| `caps` | `cmd_caps` (`287-308`) | `NO_AGENTS` when empty; otherwise one sorted `nick: caps=… roles=… host=… updated=…` line |
| `dispatch` | `cmd_dispatch` (`310-346`) | `DISPATCHED <jid>`, one `  DM <nick>: OK|FAIL <detail>` per DM, or `  (no capable workers registered)` |
| `tick` | `cmd_tick` (`348-377`) | `SWEPT`/`PRUNED`/`VERIFIED`/`ACCEPTANCE_FAILED` lines, `ERROR <e>` on stderr, `TICK_CLEAN` when everything is empty; exit 2 when errors exist |
| `verify` | `cmd_verify` (`379-394`) | report line, then `VERIFIED` / `NOT_VERIFIED`; exit 0 / 1 |
| `worker --once` | `cmd_worker_once` (`396-425`) | `SKIP <jid> (req <sorted>)`, or `CLAIMED <jid>: <title>` + `--- spec ---` + spec, or `CLAIM_FAILED <jid>`; `NO_DISPATCHES` only when nothing was found at all |
| `reconcile` | `cmd_reconcile` (`427-431`) | exit code passes through; no output |
| `review` | `cmd_review` (`433-460`) | `branch <b> vs <base>: <n> commits, <m> files`, commit lines, stat when non-empty; `ERROR: <e>` + exit 2 |
| `merge` | `cmd_merge` (`462-480`) | `MERGED <branch> -> <base>: <hash>`; `ERROR: <e>` + exit 2 |

### Argument parsing and refusals

`run_cli` uses a hand parser (`cli.rs:482-536`), not argparse. These are the refusal branches,
all exit 2 with the one-line `USAGE` string (`cli.rs:482-484`):

- empty argv, unknown command (`cli.rs:539-541`, `693-695`);
- `register` without `--caps`, with a stray positional, or a non-integer `--max-jobs`
  (`cli.rs:545-559`);
- `caps`, `reconcile` with any argument (`cli.rs:568-572`, `657-660`);
- `dispatch` without `--title` or `--spec`, stray positional, or non-integer `--lease`
  (`cli.rs:574-600`);
- `tick`/`verify` with a stray positional or missing `jid` (`cli.rs:604-620`);
- `worker` with a stray positional; loop mode (no `--once`) is stderr
  `worker loop: agent-driven; use --once per cycle` + exit 2 (`cli.rs:622-655`);
- `review`/`merge` without `--repo` or `--branch` (`cli.rs:662-691`);
- non-integer numbers through `parse_int` (`cli.rs:524-536`).

`@file` read failures are **not** usage errors: `dispatch` prints `ERROR: cannot read …` and
exits 1 (`cli.rs:318-325`).

### The backends are traits, not implementations

`CapabilitiesBackend` (`85-99`), `OverseerBackend` (`116-142`), `WorkerBackend` (`144-161`),
`ReconcileBackend` (`163-170`), and `GitopsBackend` (`200-217`) are all traits. On `main`, no
crate implements the first four, and `GitCliBackend` is the only `GitopsBackend`
(`git.rs:130-149`). The crate's tests supply fakes (`cli.rs:707-830`). The CLI therefore cannot
be constructed by a production caller from this crate alone.

## git — the real backend

- `git(repo, args)` (`git.rs:20-42`) spawns `git -C <repo>`. Spawn failure →
  `GitError("git not found on PATH")`; nonzero exit → `git <args> failed: <last 500 chars of
  stderr>`. There is no timeout (the Python source has 120 s — `gitops.py:17-30`).
- `review_branch` (`git.rs:64-99`) refuses, in order: not a repo (`:70`), branch == base
  (`:73`), unknown branch (`:76-79`). Then returns `files` from `diff --name-only`, `stat` from
  `diff --stat`, and `commits` from `log --format=%h %s`.
- `approve_merge` (`git.rs:101-126`) refuses, in order: branch == base (`:107`), dirty tree
  (`:110`), unknown branch (`:113-116`). Then it checks out the base if needed and merges with
  `--no-ff` and the fixed message `Merge <branch> (MOS approved)`, returning `rev-parse HEAD`.
  It does **not** check `is_repo` first: a non-repo reaches `clean_tree` and fails as
  `git status --porcelain failed: …`, a different message from `review`'s `not a git repo: …`.
  Python has the same order and the same difference (`gitops.py:76-94`).

There is no force-push path anywhere in the module.

## What it refuses

| Input | Refusal | Line |
|---|---|---|
| review branch == base | `refusing to review base against itself` | `git.rs:73` |
| merge branch == base | `refusing to merge base into itself` | `git.rs:107` |
| review/merge on a non-repo (review only) | `not a git repo: <path>` | `git.rs:70` |
| review/merge with an unknown branch | `unknown branch: <b>` | `git.rs:76-79`, `113-116` |
| merge with a dirty tree | `working tree dirty — refusing to merge` | `git.rs:110` |
| `git` not on `PATH` | `git not found on PATH` | `git.rs:27-29` |
| any `git` command exits nonzero | `git <args> failed: <stderr tail>` | `git.rs:31-39` |
| unreadable `@file` | `ERROR: cannot read <path>: <err>` (exit 1) | `cli.rs:235-254`, `318-325` |
| bad CLI shape / bad integer | `USAGE` (exit 2) | `cli.rs:524-536`, `538-695` |

## What it writes down

The crate writes no files. Its records are stdout/stderr lines and one git commit message:
`REGISTERED`, `NO_AGENTS`, agent lines, `DISPATCHED`, `DM`, `SWEPT`, `PRUNED`, `VERIFIED`,
`ACCEPTANCE_FAILED`, `ERROR`, `TICK_CLEAN`, `CLAIMED`, `SKIP`, `CLAIM_FAILED`,
`NO_DISPATCHES`, the review block, `MERGED`, and `Merge <branch> (MOS approved)`. The shaped
examples are in `os-build/records/os-boot-records.md`.

## Findings (doc versus code; docs fixed in this crate where the code is right)

1. **`lib.rs:1` says the crate is a "skeleton (B00)".** It is not: 1,607 source lines, 23 tests,
   and real git behaviour. Fixed the header in this pass.
2. **`lib.rs:39` says "39 `os/os/` deployment assets".** The manifest has 47
   (`carried.rs:29-88`). Fixed the header in this pass.
3. **`cli.rs:31-36` says the backend crates "are not merged to main yet".** The crates are
   workspace members (`Cargo.toml:7-23`); what is missing is an implementation of these traits,
   which no crate provides. Reworded to say that, because "not merged" is the wrong fact.
4. **The CLI has no production caller and no binary.** `run_cli` is referenced only by tests
   (`cli.rs:1102-1160`); `GitCliBackend` only by tests (`git.rs:192-243`). This is not a doc
   disagreement, but it is the crate's biggest practical limit: the port cannot be run.
5. **`cli.rs:44-46` documents a dropped `job_get` header.** Python returns `(header, spec)`
   (`cli.py:111`) and the CLI prints only the spec; the Rust `WorkerBackend::job_spec` drops the
   header entirely. Behaviour matches the printed output, but the data is unavailable to any
   future caller. Recorded as a gap, not "fixed" (widening the trait is a design change).
6. **`git.rs:9-12` documents the missing git timeout.** Confirmed: `Command::output()` with no
   timeout, versus Python's 120 s. A hung `git` hangs the call indefinitely.
