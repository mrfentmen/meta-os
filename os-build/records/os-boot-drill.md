# Failure drill — `crates/os-boot` (B009)

What breaks first when its inputs stop arriving, written from the code. Run on a scratch clone;
steps 3 and 4 move a file and restore it in the same shell.

Machine rule: one crate, `-j1`, no workspace build.

## Step 0 — baseline

```sh
cargo test -p os-boot -j1
```

Expected: 23 tests pass (16 `cli`, 4 `git`, 3 `carried`). If this fails, stop: the first break
is the compile, not any input below.

## Step 1 — the asset input disappears

The crate's only file input outside git is the carried manifest.

```sh
set -e
tmp=$(mktemp -d); cp -R crates/os-boot "$tmp/"
mv crates/os-boot/assets/os/README.md "$tmp/README.md.bak"
cargo test -p os-boot -j1 carried -- --nocapture || true
mv "$tmp/README.md.bak" crates/os-boot/assets/os/README.md
rm -rf "$tmp"
```

Expected first break: `test_carried_files_byte_identical` panics with
`asset missing for os/README.md: ...` (`carried.rs:116-120`). The count test still passes, which
is the point: a missing file is caught by identity, not by the count.

## Step 2 — argv disappears

```sh
cargo test -p os-boot -j1 run_cli_arg_errors -- --nocapture
```

Expected: `run_cli(&[])` returns `code = 2`, `err = "usage: mos.py {register|caps|dispatch|tick|verify|worker|reconcile|review|merge}\n"`
(`cli.rs:539-541`, `:482-484`). Nothing is printed to stdout.

First break in a real call: the process exits 2 before any backend is touched. No backend can
fail first because parsing runs before dispatch.

## Step 3 — the `@spec` file disappears

```sh
cargo test -p os-boot -j1 dispatch_at_file_error -- --nocapture
```

Expected: `cmd_dispatch` with `@/nonexistent-os-boot-file-xyz` returns `code = 1` and stderr
`ERROR: cannot read /nonexistent-os-boot-file-xyz: <os error>` (`cli.rs:318-325`,
`:235-254`). Note this is exit **1**, not the usage exit 2: a missing input file is a different
class from a malformed command line.

## Step 4 — the git input disappears

Three separate breaks, in guard order:

1. **Not a repo** — `cmd_review` on a plain directory → exit 2,
   `ERROR: not a git repo: <path>` (`git.rs:69-71`).
2. **Repo, unknown branch** — `cmd_review` with `nope` → exit 2,
   `ERROR: unknown branch: nope` (`git.rs:75-79`).
3. **Repo, both branches, dirty tree on merge** — `cmd_merge` with an untracked file present →
   exit 2, `ERROR: working tree dirty — refusing to merge` (`git.rs:108-111`).

`cargo test -p os-boot -j1 gitops -- --nocapture` exercises all three.

## Step 5 — the `git` binary disappears

```sh
PATH=/nonexistent cargo test -p os-boot -j1 gitops -- --nocapture
```

Expected first break: the git tests fail at repo setup (`git init` cannot spawn), before the
crate's own error path is reached. To see the crate's message without that noise, call
`os_boot::git::is_repo("/")` under the stripped `PATH`: it returns `false`, because `git()`
maps spawn failure to `GitError("git not found on PATH")` (`git.rs:22-29`).

## Step 6 — the backend disappears (the real first break)

There is no production implementation of `CapabilitiesBackend`, `OverseerBackend`,
`WorkerBackend`, or `ReconcileBackend` in the repository (search: only test fakes). A caller
that tries to construct `Backends` has nothing to put in four of its five fields
(`cli.rs:219-233`). This is the crate's first real failure in any end-to-end use: not an error
message, a compile-time absence.

## Step 7 — the worker poll is empty

```sh
cargo test -p os-boot -j1 worker_once_claim_skip_and_empty -- --nocapture
```

Expected: empty queue → stdout exactly `NO_DISPATCHES\n`, exit 0 (`cli.rs:424-425`). Found but
unmatched → `SKIP <jid> (req <sorted>)\n`, exit 0 (`:409-413`). Found, matched, claim refused →
`CLAIM_FAILED <jid>\n`, exit 0 (`:423`). Note: no error code for any of these; the CLI reports,
it does not fail.

## Order of breakage (summary)

1. Compile (if the crate is broken).
2. Backend absence (compile-time, end-to-end use).
3. argv shape → exit 2 before any I/O.
4. `@file` read → exit 1.
5. git repo → branch → dirty tree, in that order.
6. git binary → `git not found on PATH`.
7. Empty worker poll → `NO_DISPATCHES`, exit 0 (not a failure).
