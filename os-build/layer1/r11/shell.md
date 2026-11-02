# shell — Round 11 record

Source: `services/shell/shell.goose` · Test: `services/tests/t131_shell_r11.goose` · Status: RUNS
Existing driver: `services/tests/t66_shell.goose` (57 checks) · cwd edge: `t80_limit_drivers2`

## 1. Limits — PROVEN, with one gap

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `SH_LINE_MAX` | 192 | `shell.goose` | **NAMED GAP — unreachable from a host driver** | enforced only in `sh_run`'s fixed `u8[..192]` buffer (`line_len < SH_LINE_MAX`), and `sh_run` reads `sys_read_key`. `t131` cannot enter that branch. |
| `SH_CWD_MAX` | 128 | `shell.goose` | proven by `t80_limit_drivers2` | a 300-byte path is stored as 127 bytes; `sh_set_path` truncates rather than overflowing. |
| `SH_OUT_MAX` | 4096 | `shell.goose` | **not a limit** — caller-supplied | every writer takes `cap` from the caller. `t131` proves the clamp at `cap=3` (`"hel"`, no newline, still `CODE_OK`) and at `cap=0`. |

**Finding for LIMITS.md.** Its row says `SH_LINE_MAX` is "driven by `tests/t66_shell` — a line
past the shell's buffer is refused". `t66` never calls `sh_run`; it drives `sh_exec` only, and
`sh_exec` has no line-length check (the parser caps arguments at `ARG_TEXT_MAX` instead). The row
is wrong and should read unreachable-on-host, with the kernel path named.

## 2. Refusals — PROVEN

| refusal | code | assertion in `t131` |
|---|---|---|
| `|` pipe | `E_UNSUPPORTED` | "pipe is E_UNSUPPORTED" |
| `>` output redirection | `E_UNSUPPORTED` | "output redirection is E_UNSUPPORTED" |
| `<` input redirection | `E_UNSUPPORTED` | "input redirection is E_UNSUPPORTED" |
| `;` sequencing | `E_UNSUPPORTED` | "sequencing is E_UNSUPPORTED" |
| `&` background | `E_UNSUPPORTED` | "background is E_UNSUPPORTED" |
| `cat`/`cp`/`rm`/`mkdir` with too few arguments | `E_INVAL` | four arity assertions |
| missing file/dir/command | `E_NOTFOUND` | `cat nope`, `cd nope`, `ls nope`, `frobnicate` |
| unterminated quote | `E_SYNTAX` | "an unterminated quote is E_SYNTAX" |
| blank line | `CODE_OK` | "a blank line is not an error" |

A refusal that prints nothing is named by the dispatcher (`cat: <error>`); `t131` asserts the
prefix, so a silent failure cannot pass as a silent success.

## 3. Restart — NAMED GAP

The shell holds `sh_cwd`, `sh_cwd_path`, `sh_lines`, `sh_errors` and `sh_exit_requested` in module
state. None is persisted, so a supervisor restart loses the working directory, both counters and
the exit flag: the user comes back at `/` with `lines=0 errors=0`. Nothing is corrupted by that,
and nothing claims continuity. No restart drill has been run; this is the loss, named.

## 4. Contract — PROVEN (matrix row present)

| direction | other service | call | in the matrix? |
|---|---|---|---|
| out | `fs` | `fs_resolve`, `fs_read`, `fs_write`, `fs_create_path`, `fs_unlink_path`, `fs_readdir`, `fs_truncate`, `fs_dirent_count` | yes — `SVC_SHELL` row carries `SVC_FS` |
| out | `supervisor` | `sup_slot_count`, `sup_slot_name`, `sup_slot_state_name`, `sup_slot_restarts`, `sup_slot_enabled` | yes — `SVC_SUPERVISOR` |
| out | `logd` | `loss_stats` | yes — `SVC_LOG` |
| out | `audit` | `audit_used` | yes — `SVC_AUDIT` |
| out | `time` | `clock_init`, `clock_uptime_ms` | yes — `SVC_TIME` |
| in | none | no service imports `shell` yet | — |

Every call the file makes is covered by the matrix row. No unknown edge.

## 5. Load — pending the run

The batch runs 200 commands: 100 `echo batch` (accepted) and 100 `frobnicate` (refused with
`E_NOTFOUND`), counting each outcome. It approaches no internal limit — the shell's caps are
per-line — so the interesting number is that the counters stay exact across 200 dispatches.

RUNS pass=23 fail=0 · `LOAD shell ops=200 ok=100 refused=100`

## 6. README truth pass — PROVEN

- **Status line:** said `WRITTEN. Not COMPILED, not RUN`. Now `RUNS`, with `t66` (57 checks) named;
  the service has had a measured host run since the status word was written.
- **Tests line:** listed only `t66`. Now lists `t66`, the `t80` cwd-truncation case and `t131`.
- **Kept, deliberately:** "`sh_run` has never read a key." Still true and still the reason the
  REPL path, including `SH_LINE_MAX`, has no host proof. It is now scoped to the REPL rather than
  read as "the shell has never run".
