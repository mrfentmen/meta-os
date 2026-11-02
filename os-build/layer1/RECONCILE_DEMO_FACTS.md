# DEMO_FACTS vs the claim audit — reconciliation status (BF5-09)

BF5-09 asks for a written reconciliation of any number the two documents state differently. **The
claim audit is not in this checkout**, so this page cannot reconcile against it. What it does instead
is give the comparison a fixed shape: the exact numbers this lane stands behind, the command that
reproduces each one, and what to do when Milo's file disagrees.

Checked 2026-11-02: `find . -iname '*claim*'` returns `os/tests/test_claims.py` (a different
project's test) and nothing under `os-build/`. **Status: NOT RECONCILED — blocked, not skipped.**

## The numbers this lane will defend, and how to re-derive each

| # | Number | Where it is stated | Command that produces it |
|---|---|---|---|
| 1 | 32 test drivers run, exit 0 | `DEMO_FACTS.md`, `SERVICE_RUNS.md`, `FREEZE_AUDIT.md` | `./os-build/layer1/run_native.sh` |
| 2 | 1,180 passing assertions, 0 failing | same three | `awk -F'\|' '/^tests\// {s+=$3} END {print s}' os-build/layer1/host/run_rows.txt` |
| 3 | 38 programs typecheck, 0 errors | `DEMO_FACTS.md`, `GATE_RERUN.md` | `./os-build/layer1/check_services.sh` |
| 4 | 114 Goose files | `DEMO_FACTS.md`, `SERVICES_FINAL.md` | `find services -name '*.goose' \| wc -l` |
| 5 | 24,369 lines | `SERVICES_FINAL.md`, `FREEZE_AUDIT.md` | `cat $(find services -name '*.goose') \| wc -l` |
| 6 | 25 services with code, 4 placeholders | `SERVICES_SCOPE.md`, `FREEZE_AUDIT.md` | `jq '.services \| length' os-build/layer1/services.json`; `ls -d services/*/` |
| 7 | 17 services need no kernel call, 8 need a proposal | `SERVICES_SYSCALL_MAP.md`, `services.json` | `python3 os-build/layer1/gen_services.py` |
| 8 | 155.2 KiB static storage | `DEMO_FACTS.md` | `python3 os-build/layer1/size_audit.py` |
| 9 | 22 of 75 limits exercised | `LIMITS.md` | `python3 os-build/layer1/gen_limits.py` |
| 10 | 3 services start, 1 hangs, 18 have no entry | `BOOT_REHEARSAL.md`, `FREEZE_AUDIT.md` | `./os-build/layer1/boot_rehearsal.sh 5` |
| 11 | 67 dormant permission rows | `DEMO_FACTS.md`, the summary line `callmatrix_audit.py` prints | `python3 os-build/layer1/callmatrix_audit.py` |
| 12 | 100 status lines, 0 stale | `FREEZE_AUDIT.md` | `python3 os-build/layer1/audit_status.py` |

## The usual ways two audits disagree, and which number wins

1. **Driver count vs service count.** 32 drivers is not 32 services and not 25 services. Nine
   drivers cover libraries and cross-service behaviour (`t45`–`t48`, `t62`–`t64`). If the audit says
   "32 services", it read the wrong row.
2. **Assertion count.** The manifest's per-service `checks` column sums to 751, not 1,180, because a
   test shared by two services is counted for each of them. **The 1,180 is the driver total and it
   is the one to quote.**
3. **Typecheck count.** 38 is roots plus test roots; 32 of those also run. Neither number is a
   service count.
4. **"Runs" vs "boots".** If any document says a service was *started*, it must point at
   `BOOT_REHEARSAL.md` and it must say *host process*. Three services start there. None is started
   by the kernel.
5. **Branches.** These numbers are on `buffy/layer1-goose-services` at the Round-5 close. A number
   measured on `main` will differ and neither is wrong; say which tree.

## What to do when the audit lands

1. Run each of the twelve commands above on this branch and diff against the audit's column.
2. If a number differs, **fix this lane's number first** — the command is the tie-breaker, and if the
   command disagrees with this file, this file is stale.
3. If the audit's number came from `main`, note the branch in the reconciliation and stop; two
   branches with two states is not a disagreement.
4. Anything the audit states that is not in the twelve rows should be treated as a new claim and
   given a command before it is quoted in the demo.

## Honest status line

**Not reconciled: the counterpart document is absent.** Nothing in this file should be read as
agreement with an audit nobody in this checkout has seen.
