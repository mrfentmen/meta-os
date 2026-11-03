# Stale claims — ISO lane, scanned 2026-11-03

The lane has changed faster than its own paperwork. This is every claim about
the ISO lane that the scan found, with the verdict and what happened to it.
Other lanes' records were read and left alone.

## How this was scanned

```
grep -rnE '[0-9]+ +(passed|checks?|rules|tests?)' os-build/*.md
grep -rniE '(four|five) (apps|launchers|programs|ids)' os-build/*.md iso/**/*.md
grep -rn 'agent-status' os-build/*.md iso/**/*.md
grep -rn -- '--user' os-build/*.md
grep -rniE 'blocked|no binary|33 passed' iso --include='*.md'
git show origin/bond/round13-records:os-build/BUFFY_ROUND13_STATUS.md
```

## Found and fixed here

| File | Line | Said | True now | Verdict |
|---|---|---|---|---|
| `iso/apps/README.md` | 18 | "four launchers: Files, Terminal, Settings, Web" | five, including agent status | **STALE** |
| `iso/apps/README.md` | 40 | "four apps in the order listed" | five | **STALE** |
| `iso/apps/README.md` | 80 | `agent-status` "Status: BLOCKED, waiting on an entry point" | ships since `9020439c` | **STALE** |

## Stale on this branch, already corrected elsewhere

| File | Line | Says here | Corrected value | Where |
|---|---|---|---|---|
| `os-build/BUFFY_ROUND13_STATUS.md` | C row | "10 / 10; 1 drilled, 9 gaps" | "25 / 25; 1 drilled, 24 gaps" | `bond/round13-records` @ `de25c6eb` |
| same | S row | "19 implemented, 1 partial" | section rewritten against the closeout | `bond/round13-records` |
| same | T row | "COMPLETE … 15 SIMULATED drills" | closeout corrected; the row was not the only false count | `bond/round13-records` |

Not edited on purpose. `bond/round13-records` already carries the corrected
table; editing the same file on this branch would guarantee a conflict on the
merge that matters.

## Read and left alone, with reason

| File | Why it is not stale |
|---|---|
| `os-build/BUFFY_ISO_STATUS.md` | rewritten 2026-11-03; 101 checks, 14 doctor rows, current |
| `os-build/ISO_LANE_HANDOFF.md` | rewritten 2026-11-03; commit table generated from `git log` |
| `os-build/PAX_12H.md`, `PAX_12H_B6.md`, `PAX_12H_RESPONSE.md` | different clock (H+0 2026-11-01 20:12), written before this lane existed. A record of a past plan, not a claim about now |
| `os-build/README_AUDIT_BOND.md` | dated audit of README numbers across the whole repo; its verdicts are still the verdicts |
| `os-build/PROGRAM_PROOF_LEDGER.md`, `BOND_TASKS_STATUS.md`, `BOND_WAVE2_STATUS.md` | dated measurements of other programs, each row stamped with its date and log |
| `os-build/BUFFY_FINISH_TONIGHT.md` | says on its own face that it supersedes two task lists; itself superseded |
| `os-build/METAOS_1.0_RELEASE_CHECKLIST.md` | 23 boxes, all open, all still accurate — the release gate reads it directly |

## Cleared by the scan

- No `--user` reference survives anywhere in `os-build`. `apply.sh` dropped the
  flag when dock items stopped targeting a guessed home.
- No "33 passed" claim survives. The checker is at 101 and the two files that
  quote a number quote that one.
- The only "agent-status is BLOCKED" text left in the repo was in
  `iso/apps/README.md`, fixed here.
