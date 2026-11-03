# OC1B §16 gate-2 verdict (OC1B-396..398)

Tree: `94010c76ee095fa6c6bcfa4405cd56a9695f32d3`. Date (UTC): 2026-11-02.

**GATE-2: BLOCKED (runner cannot complete a run on this Mac).**

Deciding numbers:

- Runner's own 7 checks: 6 PASS (echo, hello, host×3, heartbeat), check 7
  (updater) ABORTS the script under `set -eu` — no summary line, exit 1.
- Inventoried services with passing Mac-side RUN evidence: 0 of 42 dirs
  (kernel-syscall link ceiling: `_sys_exit`, `_sys_write_serial`,
  `_sys_write_console` unresolvable on macOS for every `common.sys`
  importer, i.e. every service test).
- Partial positive signal (not a run): 5/5 core service tests + full library
  `root.goose` typecheck exit 0 (`goose check`).

Terminal error (OC1B-398):

```text
updater.goose:40: error: cannot find the module common.err.err, looked for
    /private/tmp/gupd/common/err/err.goose
    /Users/test/mcp-servers/toolchains/goose-src/stdlib/common/err/err.goose
```

with the deeper cause `program needs exactly one global fn main()` —
`services/updater/updater.goose` is a library with no `main`.

What gate-2 does NOT prove (OC1B-397): hosted/kernel behaviour of any
service, cross-service integration, updater staging end to end. The 6
passing checks prove the host-runnable Goose subset works on this Mac and
nothing more.
