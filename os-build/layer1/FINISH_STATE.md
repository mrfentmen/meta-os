# The state post: BF4 and BF5, item by item (A1)

Written 2026-11-02 at the finish-list close, on `buffy/layer1-goose-services`. This is the written
answer to "did you get it / did you already do it": every id from `BUFFY_TASKS_ROUND4.md` (BF4-01 to
BF4-24) and `BUFFY_TASKS_ROUND5.md` (BF5-01 to BF5-14), with one of three words and the artifact
that carries it. Nothing here is "in progress" — the point of the page is that each line is decidable
by opening the file it names.

**Counted: BF4 21 DONE / 2 PARTIAL / 1 NOT STARTED. BF5 13 DONE / 1 PARTIAL / 0 NOT STARTED.**

The two PARTIALs and the one NOT STARTED are at the end, together, because they are the only rows
that need a decision from someone other than me.

## The finish list's own 12 items, A1 to C4

The tables below are keyed to BF4/BF5 because that is how the work was tracked. `BUFFY_FINISH_TONIGHT.md`
is keyed A/B/C, so here it is in that numbering — same work, the list's headings:

| Id | What the finish list asked | State | Where it is answered |
|---|---|---|---|
| **A1** | Checkpoint commit + a written state post, item by item, DONE / PARTIAL / NOT STARTED | **DONE** | checkpoint `40ad49d`; the two BF tables below are the post |
| **A2** | The BF5-01 deviation closed properly: run it in a Lobster host or state it plainly | **DONE, deviation stated** | `BOOT_REHEARSAL.md` opens with it: the rehearsal ran in the **host runtime**, because there are zero `.lobster` files in this tree. Repeated in `SERVICES_FINAL.md` and `SIGNOFF.md` |
| **A3** | Whole-corpus `goose check` with `services/root.goose` in place — pass and error count — plus one table of every service with its measured word | **DONE** | `check_services.sh`: **39 ok, 0 failed**, exit 0 (6 roots + 33 test roots). `FINISH_STATUS.md`: 25 services — **24 RUNS, 1 TYPECHECKS, 0 NEITHER**, 1,253 assertions |
| **B1** | Failure matrix complete: each service's failure modes, each exercised, one table | **DONE** | `FAILURE_MATRIX.md`. The four blank rows (`devices`, `session`, `socket`, `timesync`) were closed by `t77_gaps` (73 checks), which found three defects |
| **B2** | Supervisor under load: 10 services, mixed crashes, policies firing, quotas — one transcript with counts | **DONE** | `tests/t75_supervisor_load` (32 checks) + `TRANSCRIPTS.md` §BF5-04 |
| **B3** | Shell driving the real demo commands natively, aligned line by line with the kernel's newest K7 session log | **DONE** | `K7_ALIGN.md` against `os-build/logs/K7-boot.txt`. Checked against main's tip: that is still the newest *full* session — `MERGED-boot-2.txt` (same merge, `a89d505`) ends at `status`, so it cannot be the alignment target |
| **B4** | Syscall/ABI map regenerated after `read_key` (5); state the final counts | **DONE** | `SERVICES_SYSCALL_MAP.md` + `services.json`: **17 library / 8 need a proposal / 0 host-only**. No class moved — `read_key` was already inside the F1 freeze |
| **B5** | Integration packs for the first 3 services in load order | **DONE** | `integration/{bootlog,storage,time}.md` + `integration/README.md`: entry point, ABI needs against the frozen table, host shim today, smallest kernel-side change to load each |
| **C1** | `SERVICES_FINAL.md` for the submission record | **DONE** | `SERVICES_FINAL.md` — six defects named, every claim with its command |
| **C2** | The freeze audit in one page: counts by status word | **DONE** | `FREEZE_AUDIT.md`, re-measured tonight |
| **C3** | `DEMO_FACTS`, final: every number the demo says, each with its source | **DONE** | `DEMO_FACTS.md` is generated; `gen_demo_facts.py --check` reports "DEMO_FACTS.md is current" |
| **C4** | One page: what the layer needs from the kernel after the hackathon, in dependency order | **DONE** | `KERNEL_NEEDS_AFTER.md` |

That is 12 of 12 answered, and the freeze line is not crossed: the list's H+9 freeze is 2026-11-02
05:12 EST and this pass closed before it.

## BF4 — Round 4

| Id | What was asked | State | Evidence |
|---|---|---|---|
| BF4-01 | Run every service natively; pass/fail table with real output | **DONE** | `SERVICE_RUNS.md` — 38 rows, 33 drivers RUNS, 1,253 checks, 0 failed; `./os-build/layer1/run_native.sh` |
| BF4-02 | Fix what the runs expose, dependency order | **DONE** | six defects fixed, each named in `SERVICES_FINAL.md` §"The six defects" and in the commit that fixed it |
| BF4-03 | Supervisor story proven natively: start, stop, restart-on-crash of two services | **PARTIAL** | `TRANSCRIPTS.md` §BF4-03, `tests/t52_supervisor` (53 checks) + `t75` (32). The *decisions* are proven; no process is spawned or killed — `sys_spawn`/`sys_kill` are proposals (P3) |
| BF4-04 | Log service end to end: write, rotate, read back, quota | **DONE** | `TRANSCRIPTS.md` §BF4-04 (two sections: `t50_logd` 19 checks, `t71_rotate` 48), `t74` for the full-ring case |
| BF4-05 | Storage contract against the RAM backend | **DONE** | `TRANSCRIPTS.md` §BF4-05, `tests/t54_storage` (26 checks) |
| BF4-06 | Shell service natively against the real filesystem | **DONE** | `TRANSCRIPTS.md` §BF4-06, `tests/t66_shell` (57 checks) and `t76_demo_session` (25) |
| BF4-07 | Syscall map against the F1 freeze, three classes | **DONE** | `SERVICES_SYSCALL_MAP.md` + `services.json`, regenerated: 17 library, 8 need a proposal, 0 host-only |
| BF4-08 | Exact proposed numbers and signatures for the proposal class | **DONE** | `PROPOSALS.md` P1–P8; nothing allocated, the freeze holds |
| BF4-09 | One status shape across the OS (`KEY value`, kernel-compatible) | **DONE** | `services/common/status/status.goose`, `tests/t70_status` (20 checks), `K7_ALIGN.md` for the kernel comparison |
| BF4-10 | Lobster host binding, one real round trip, log committed | **NOT STARTED** | zero `.lobster` files in this repo; `LOBSTER_BINDING.md` states the measurement and the shortest path. Not doable inside this tree without a host |
| BF4-11 | Machine-readable manifest generated from the corpus | **DONE** | `os-build/layer1/services.json` (25 services) by `gen_services.py`; `FINISH_STATUS.md` is its table |
| BF4-12 | `BOOT_PLAN.md`: ordered plan for loading services once a surface is ruled | **DONE** | `BOOT_PLAN.md`, cross-checked by `bootorder_check.py` (22 services, no cycles) |
| BF4-13 | Malformed-input suite for format/config/hash | **DONE** | `tests/t72_hostile` — 77 checks, `SERVICE_RUNS.md` |
| BF4-14 | Parser hardening round 2 on the shell's argument parser | **DONE** | `tests/t73_shell_hard` — 46 checks |
| BF4-15 | Protocol pack exercised pairwise, not against a wire | **DONE** | `TRANSCRIPTS.md` §BF4-15, `tests/t68_proto` (41 checks) via `tests/harness/link.goose` |
| BF4-16 | MOSFS01 edge cases: full disk, deep paths, collisions, delete-while-open | **DONE** | `TRANSCRIPTS.md` §BF4-16, `tests/t65_fs` (75 checks) |
| BF4-17 | Every limit in the corpus gets one test that tries to break it | **PARTIAL** | `LIMITS.md` — **26 of 75** exercised, the other 49 marked UNPROVEN by name |
| BF4-18 | Second full-corpus audit pass, every status word re-measured | **DONE** | `audit_status.py`: 101 lines, 0 stale. It found 6 stale tonight (`devices`, `hotplug`, `session`, `login`, `socket`, `timesync`) and `--fix` rewrote them measured |
| BF4-19 | `DEMO_FACTS.md`, every number sourced to a command | **DONE** | generated by `gen_demo_facts.py`; `--check` reports "DEMO_FACTS.md is current" |
| BF4-20 | `SERVICES_SCOPE.md` refresh after Waves 1–2 | **DONE** | `SERVICES_SCOPE.md`, rewritten 2026-11-02, status words measured |
| BF4-21 | `BUFFY_REPORT.md` + `SIGNOFF.md` correction pass, measured words | **DONE** | both rewritten today; every count in them matches `DEMO_FACTS.md` as of this commit |
| BF4-22 | Index the tools: what each gate helper does, and how to prove it | **DONE** | `os-build/tools/README.md` + `os-build/tools/drive.py` |
| BF4-23 | One page: what a Flock-style deployment needs that this build does not have | **DONE** | `os-build/research/flock-deployment.md` |
| BF4-24 | Wire-or-delete input: which services to load first, in order | **DONE** | `LOAD_ORDER_1102.md` |

## BF5 — Round 5

| Id | What was asked | State | Evidence |
|---|---|---|---|
| BF5-01 | Boot rehearsal | **DONE, with a stated deviation** | `BOOT_REHEARSAL.md` + `boot_rehearsal.sh 5`: 22 services started in order in the **host runtime** — 3 start, 1 hangs, 18 have no entry. It is not a Lobster-host run and the file says so in its first paragraph |
| BF5-02 | Failure matrix, one table, each cell exercised or named | **DONE** | `FAILURE_MATRIX.md`; the four blank rows (`devices`, `session`, `socket`, `timesync`) were closed tonight by `t77_gaps` (73 checks) |
| BF5-03 | Gates re-run after `read_key` | **DONE** | `GATE_RERUN.md` — 33 of 33, 1,253 assertions, 0 failed; no ABI class moved (`read_key` was already in the freeze) |
| BF5-04 | Supervisor under load: 10 services, mixed crashes, quotas | **DONE** | `TRANSCRIPTS.md` §BF5-04, `tests/t75_supervisor_load` (32 checks) |
| BF5-05 | Shell service driving the demo commands end to end | **DONE** | `TRANSCRIPTS.md` §BF5-05, `DEMO_SHELL.md`, `tests/t76_demo_session` (25 checks) |
| BF5-06 | Integration packs for the first 3 services in load order | **DONE** | `integration/{bootlog,storage,time}.md` + `integration/README.md` |
| BF5-07 | Freeze audit at H+9: one page, counts by status word | **DONE** | `FREEZE_AUDIT.md`, refreshed tonight off the current tree |
| BF5-08 | `SERVICES_FINAL.md` for the submission record | **DONE** | `SERVICES_FINAL.md`; §"The six defects" and the proof table are current |
| BF5-09 | Demo-facts reconciliation against the claim audit | **PARTIAL — blocked** | `RECONCILE_DEMO_FACTS.md` says it plainly: no claim-audit file exists in this checkout. The page instead fixes the 13 numbers this lane will defend and the command for each |
| BF5-10 | What the layer needs from the kernel next, dependency order | **DONE** | `KERNEL_NEEDS_AFTER.md` |
| BF5-11 | 30-second demo segment, every line traced to a run | **DONE** | `DEMO_30S.md` |
| BF5-12 | Post-fix captures | **DONE** | `captures/demo-{1-supervisor-under-load,2-filesystem,3-shell-session}.txt` |
| BF5-13 | Submission-grade README section for the layer | **DONE** | `README.md` §"The services layer" — 33 programs, 1,253 checks, boundary stated |
| BF5-14 | Closing report for the window | **DONE** | `BUFFY_REPORT.md` §"The finish-list close" + this page |

## The three rows that need someone else

| Row | What is missing | What unblocks it |
|---|---|---|
| **BF4-10** Lobster round trip | a `.lobster` host and a program that calls a service | the host existing in a checkout; my half (`LOBSTER_BINDING.md`, one no-argument `svc_entry` per service) is done |
| **BF4-17** every limit tested | 49 of 75 constants still UNPROVEN | time — each one is a driver of its own, and `LIMITS.md` names all 49 |
| **BF5-09** reconciliation | Milo's or Pax's claim-audit file | the file landing in this tree; the 13 numbers and their commands are ready to diff against it |

## The numbers this page is standing on

Measured in this commit, all four re-runnable with one command each:

| Number | Value | Command |
|---|---|---|
| Native drivers RUNS | **33 of 33, 1,253 assertions, 0 failed** | `./os-build/layer1/run_native.sh` |
| Whole-corpus typecheck | **39 programs, 0 errors** | `./os-build/layer1/check_services.sh` |
| Status words current | **101 lines, 0 stale** | `python3 os-build/layer1/audit_status.py` |
| Corpora counts | 115 files, 24,785 lines, 165.4 KiB static | `python3 os-build/layer1/gen_demo_facts.py` |

**Nothing in this list booted.** Every DONE above is a host process, a generated document, or a
static analysis — and the layer that says "RUNS" says it about a process with a substituted syscall
surface. That word has not changed all night and it is not going to change in a status post.
