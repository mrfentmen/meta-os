# OC1B §16 — Goose services gate-2 (OC1B-376..400)

Tree: `94010c76ee095fa6c6bcfa4405cd56a9695f32d3`. Date (UTC): 2026-11-02.
Goose binary: `goose b781587 (runtime 3901ec457ba9)` (same version at both
paths below). All goose executions ran in /tmp copies except the runner
itself; tree left clean (reverts noted).

## Runner + toolchain (OC1B-377/378/383/385)

- OC1B-377 runner path verbatim (`services/run-goose-tests.sh` line 8):
  `GOOSE=/Users/test/mcp-servers/toolchains/goose-src/build/goose`
- OC1B-378 existence: present, executable. OC1B-385 version:
  `goose b781587 (runtime 3901ec457ba9)`.
- OC1B-383 other builds: `/opt/homebrew/bin/goose` exists on PATH — same
  version string (b781587), not a toolchain fork. `goose toolchain`: clang
  21.0.0, cmake 4.4.4, git 2.54.0. No install performed.

## Run 1 as-is (OC1B-379/380/381/382/386)

Full output: `os-build/logs/OC1B-goose-run1.txt`. Command:
`sh services/run-goose-tests.sh`, EXIT=1, WALL=5 s.

- OC1B-380 per-check table (the runner's 7 checks, not per-service):

| # | check | ran? | result | reason |
|---|---|---|---|---|
| 1 | echo round-trips | yes | PASS | `echo: hi` |
| 2 | hello prints | yes | PASS | `HELLO FROM GOOSE` |
| 3 | host lists echo tool | yes | PASS | tools:["echo"] |
| 4 | host answers echo | yes | PASS | result t |
| 5 | host refuses unknown | yes | PASS | unknown tool |
| 6 | heartbeat beats then stops | yes | PASS | beats>=3 then stops |
| 7 | updater stages release | yes | ABORT | import-root failure (see below); `set -eu` kills script before the check + summary lines |

- OC1B-381 counts from run 1: checks run 7, passed 6, failed 0, aborted 1
  (updater — never reached its assertion; no `goose tests:` summary line).
- OC1B-382 never-ran: only the updater assertion — cause: `cd updater`
  breaks module resolution (`common.err.err` sought at
  `services/updater/common/...`), exit 1 under `set -eu`.
- OC1B-386 Buffy's runner-path fix: NOT LANDED. Only commit ever touching
  `services/run-goose-tests.sh` on any branch is 75e1febf; no buffy fix
  exists to re-run against. The hardcoded path itself is CORRECT on this Mac
  (binary present); the breakage is the updater invocation, not the path.
  No run 2 (named, not silent).

## Updater failure chain (OC1B-389/390/391)

- OC1B-389 verbatim (tree-copy repro, cwd-independent):
  `updater.goose:40: error: cannot find the module common.err.err, looked for
  /private/.../updater/common/err/err.goose
  /Users/test/mcp-servers/toolchains/goose-src/stdlib/common/err/err.goose`
  and even with imports resolvable: `program needs exactly one global fn main()`
  — `services/updater/updater.goose` defines NO `main` (it is a library), so
  `goose run updater.goose` can never execute as written. Two stacked defects,
  both in the runner invocation, neither in the updater module.
- OC1B-390 classification: RUNNER defect (environment-invariant: fails on any
  machine this way, independent of macOS). Service code not implicated
  (`goose check root.goose` typechecks the whole library incl. updater: exit 0,
  warnings only).
- OC1B-391 defect reports for Buffy/Pax (not edited here):
  D1. `run-goose-tests.sh` updater step unrunnable: `cd updater` breaks
  script-relative import resolution AND target has no `main`. Suggested fix
  direction (theirs): drive updater through a root-placed test (t58/t138
  pattern) or give the runner a runnable updater entry.
  D2. Design gap the run exposes: every `services/tests/t*.goose` program
  imports `common.*`/siblings script-relatively, so NONE can run via
  `goose run services/tests/<t>.goose` from any cwd (verified verbatim for
  t58 + all five core tests).
  D3. Kernel-link ceiling: all t-tests import `common.sys` (syscall externs
  `_sys_exit`, `_sys_write_serial`, `_sys_write_console`); they compile but
  cannot LINK on macOS — host execution of service tests is impossible
  without kernel stubs or a hosted runtime (cf. `os-build/layer1/K6_NEEDS.md` Q5).

## Core-5 bypass (OC1B-384)

Entry points exist (`fn main` in tests/t107_bootlog, t110_console,
t111_dashboard, t114_dhcp, t116_dns). Run bypass in a /tmp services copy
(imports resolve to identical modules; tree untouched):

| service | test | `goose run` (root-placed copy) | `goose check` |
|---|---|---|---|
| dashboard | t111 | compiles; LINK fails: unresolved `_sys_write_serial`, `_sys_exit` | exit 0, 0 warnings |
| console | t110 | compiles; LINK fails: unresolved `_sys_write_console`, `_sys_exit` | exit 0, 2 warnings |
| bootlog | t107 | compiles; LINK fails: unresolved `_sys_exit` (+serial) | exit 0, 0 warnings |
| dhcp | t114 | compiles; LINK fails: unresolved `_sys_exit` (+serial) | exit 0, 3 warnings |
| dns | t116 | compiles; LINK fails: unresolved `_sys_exit` (+serial) | exit 0, 11 warnings (redundant-`as` style only) |

Full outputs: `os-build/logs/OC1B-goose-core5.txt`. Verdict per service:
no-runnable-entry-point ON THIS MAC (environment ceiling D3); typecheck
clean across all five (a real, if partial, signal — check runs nothing).

## Hygiene + timing + cross-check (OC1B-392/393/394/395)

- OC1B-392 tree-clean: the runner appends 3 lines to TRACKED
  `services/host.log` per run and rewrites tracked `services/updater/CURRENT`,
  `RELEASED`, `side-B/staged-version` (byte-identical values this run).
  All reverted after the run (`git checkout -- services/host.log ...`);
  the /tmp-copy probes wrote nothing to the tree. Final `git status` for
  services/: clean.
- OC1B-393 wall-clock: 5 s (only completed run).
- OC1B-394 Buffy hosted results: NO hosted gate results posted anywhere in
  the tree (no goose gate-results file found) — no-hosted-results line stands.
- OC1B-395 Mac-side evidence count: 6/7 runner checks PASS (host-runnable
  mini-programs: echo/hello/host×3/heartbeat); 0 inventoried services with
  passing Mac-side RUN evidence (kernel-link ceiling); 5/5 core services +
  full library root typecheck-clean (`goose check root.goose` exit 0).

## Verdict (OC1B-396/397/398/399)

- OC1B-396 gate-2 verdict: **BLOCKED (runner cannot complete a run)**.
  Deciding numbers: 6/7 runner checks pass, check 7 aborts (no summary line,
  exit 1); 0/N inventoried services executable on macOS (link ceiling);
  5/5 core + library root typecheck exit 0.
- OC1B-397 what gate-2 does NOT prove: hosted behaviour (nothing here ran
  against the kernel), cross-service integration, or updater staging end to
  end — the claim boundary.
- OC1B-398 terminal error: `updater.goose:40: error: cannot find the module
  common.err.err ...` then script death under `set -eu`; deeper:
  `program needs exactly one global fn main()`.
- OC1B-399/400: Goose rows + commit sha in
  `os-build/logs/OC1B-s14-STATUS-SNIPPET.md` (status file owned by coordinator).
