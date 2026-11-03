# OC2 Cross-check: Bond's 5th frozen app — agent-status reader

Branch: `opencode2/landwalls` (worktree files read; post-merge identical).
Scope: READ-ONLY on `iso/`; no VM, no builds, no installs, no network. Only action: ran the app's own unittest suite (local subprocess, no network).

## Files read
- `iso/apps/agent-status/meta-agent-status.py` (148 lines, executable)
- `iso/apps/desktop/meta-agent-status.desktop` (11 lines)
- `iso/apps/plank/meta-agent-status.dockitem` (2 lines)

## Check 1 — Test suite passes
Command (repo root): `python3 -m unittest discover -s tests -p "test_iso_agent_status*" -v`
Result: **Ran 10 tests, OK** (0 failures, 0 errors, 0.374s). Verbatim tail:
```
test_absent_optional_row_does_not_fail_the_run (test_iso_agent_status.AgentStatusTest) ... ok
test_bad_usage_exits_two (test_iso_agent_status.AgentStatusTest) ... ok
test_gym_ledger_counts_non_blank_lines (test_iso_agent_status.AgentStatusTest) ... ok
test_job_queue_counts_json_files (test_iso_agent_status.AgentStatusTest) ... ok
test_json_mode_is_machine_readable (test_iso_agent_status.AgentStatusTest) ... ok
test_missing_required_row_fails_with_a_named_reason (test_iso_agent_status.AgentStatusTest) ... ok
test_registry_counts_agents_and_drafts (test_iso_agent_status.AgentStatusTest) ... ok
test_stale_heartbeat_is_reported_stale (test_iso_agent_status.AgentStatusTest) ... ok
test_strict_treats_a_stale_heartbeat_as_failure (test_iso_agent_status.AgentStatusTest) ... ok
test_tool_writes_nothing (test_iso_agent_status.AgentStatusTest) ... ok
----------------------------------------------------------------------
Ran 10 tests in 0.374s
OK
```
Runner is unittest (per `tests/test_iso_agent_status.py:1-5,104-105` header `unittest.main()`; no pytest needed).
**AGREE** — suite exists, runner as documented, 10/10 pass.

## Check 2a — Reads only files (no network/subprocess)
- Imports (`meta-agent-status.py:18-23`): `argparse, json, os, sys, time, pathlib` only. No `socket/urllib/requests/http/subprocess`.
- Grep for `socket|urllib|requests|http\.|subprocess|os\.system|os\.popen|popen|Popen|...` on the script: **no matches**.
- Only `os.` use is `os.environ.get("METAOS_ROOT", ...)` (`:121`); only `sys.` use is `sys.exit(main())` (`:148`).
- File ops are read-only: `read_text` (`:50,:55`), `stat().st_mtime` (`:91`), `is_file/is_dir/iterdir` (`:74-77,:83`); output is `print` to stdout (`:138,:140-143`). No writes.
- Corroborated by `test_tool_writes_nothing` (`tests/test_iso_agent_status.py:85-89`, asserts mtimes unchanged) — passed.
**AGREE** — file-read-only claim holds.

## Check 2b — Exit codes 0/1/2 paths exist
- 0: `meta-agent-status.py:144` `return 1 if failed else 0`; exercised by `test_registry_counts_agents_and_drafts` (asserts `returncode == 0`).
- 1: same line, `failed` = required row `missing/unreadable` (`:132`), plus `stale` under `--strict` (`:133-134`); exercised by `test_missing_required_row_fails_with_a_named_reason` and `test_strict_treats_a_stale_heartbeat_as_failure` (both assert `returncode == 1`).
- 2: no literal `2` in the script — comes from `argparse` (`:120-126`) on bad usage; exercised by `test_bad_usage_exits_two` (`--nope` asserts `returncode == 2`, passed).
**AGREE** — all three exit paths exist and are test-covered (2 via argparse, as is conventional).

## Check 2c — .desktop Exec points at the real script
- `.desktop:7`: `Exec=meta-agent-status` (PATH lookup, `Terminal=true`).
- Install mapping `iso/tools/apply.sh:139`: `put "$ISO/apps/agent-status/meta-agent-status.py" "/usr/local/bin/meta-agent-status" 755` — so `meta-agent-status` on PATH IS this script, executable bit set.
- Corroborated: `iso/apps/README.md:23` maps it to `/usr/local/bin/`; `tests/test_iso_apply.py:62,72` expects `usr/local/bin/meta-agent-status` + exec bit; `iso/base/meta-doctor.py:101` expects exe at `usr/local/bin/meta-agent-status`.
**AGREE** — Exec resolves to the real script via the installer mapping.

## Check 2d — Dockitem references match
- `.dockitem:1-2`: `[PlankDockItemPreferences]` + `Launcher=file:///usr/share/applications/meta-agent-status.desktop`.
- That filename matches the desktop file `iso/apps/desktop/meta-agent-status.desktop`; `tests/test_iso_apply.py:48` expects it installed at `usr/share/applications/meta-agent-status.desktop`, dockitem at `usr/share/metaos/dock/meta-agent-status.dockitem` (`:50`).
**AGREE** — dockitem Launcher matches the shipped desktop entry name and expected install path.

CROSS-CHECK VERDICT: AGREE
