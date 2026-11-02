# OpenCode — FINISH TONIGHT (the complete list)

From Pax, 2026-11-01 ~23:45 EST. Boss order: finish the OS
tonight. This list SUPERSEDES OPENCODE_TASKS_ROUND5.md and
OPENCODE_TASKS_ROUND6.md as your working list — everything still
owed from both is folded in here, plus the Debian image lane.
Nothing outside this list is owed tonight.

**The finish line: the H+9 freeze, 2026-11-02 05:12 EST.**
After it: gate fixes and the report only.

Work on branch `opencode/round5` (already started, 930e7b8);
open `opencode/round6` only if Pax says. Pax merges. Every
claim names its log. Spend: the Imperium live runs use the
standing caps (log every cent; the ceiling is the boss's
"don't spend like 20 bucks").

## A — Prove current main (the claim sentence, clause by clause)

The claim: "Meta OS boots on x86_64 in QEMU, drops to ring 3,
runs three userspace programs, isolates a fault to one task,
and gives you a shell that reports the machine's real state —
reproduced from a clean checkout by one command, every claim
backed by a committed boot log."

- A1. Record the main tip hash you start from. From a CLEAN
  clone, run `os-build/gate.sh` end to end: GATE GREEN 7/7.
  Commit the gate log.
- A2. Fresh boot log of current main at
  `os-build/logs/MERGED-boot-2.txt`. Required lines, all of
  them: banner `META OS 0.1 (K6)`, the alive line, the mem
  summary, HELLO FROM USERSPACE, the after-sleep line, exit
  codes, the bad-call refusal, the faulted task killed.
  Loader refused must be 0. Panic must be 0.
- A3. Refresh the K7 typed demo session ON CURRENT MAIN:
  `status`, `help`, `uptime`, `mem`, `ps` each typed and
  answered with real values. (The Round 4 session predated
  RW4-1, so mem/ps were honestly refused in that log; on
  current main they must answer.) Commit the session log.
- A4. Exercise `clear` in that session. It is VGA-only, so
  state exactly how you verified it (screendump before/after
  is best). Commit the evidence.
- A5. read_key end to end (syscall 5): a small userspace
  probe program that calls syscall 5 and prints the byte it
  got; drive a key in with `os-build/tools/drive.py` sendkey;
  the log shows the probe receiving that key. Commit probe
  source under `os-build/userspace/` and the log.
- A6. Attract screen proof: boot, type nothing, let the idle
  entry fire; QEMU screendump showing the spinning loop and
  the `META OS 0.1` label; press a key; second screendump
  showing the shell restored exactly. Commit both PNGs under
  `os-build/captures/`.
- A7. Ten-minute soak on current main: no panic, final
  `status` sane. Commit the log tail.

## B — Imperium live loop (first full run)

- B1. On the Mac, run the full chain once: staged LABELLED
  feed → flag → investigation → auto-dispatch WITH the
  picture → simulated receipt. Commit the run record: the
  receipt id, and the package showing the `picture` field
  present. If it blocks, the result is the blocker verbatim
  plus what you tried — that counts, hiding it does not.
- B2. If B1 succeeds, run it once more on a different
  division (Ignis or Medicus). Commit that record too.

## C — The Debian dev-carrier image (the Linux side)

The image exists (`metaos-2026-11-01.img`, boot-verified
PARTIAL). Close what can be closed tonight, in QEMU:

- C1. For EACH of these, prove it or name the blocker in one
  line: getty autologin shell; DHCP lease (show the address);
  dashboard HTTP answering; the passive updater's git pull
  running. Write the results to
  `os-build/image-status-2026-11-02.md` on your branch.
- C2. If one fails on a config-level cause (autologin
  override, DHCP client not enabled), fix the in-repo image
  build inputs, rebuild, re-prove. TIMEBOX: if a rebuild
  cannot finish by 04:00 EST, record the blocker and stop —
  a named blocker beats a rushed image.

## D — Demo and freeze

- D1. Demo capture session. If Hana's DEMO_SCRIPT has landed
  on main, follow it. If it has not landed by 03:00 EST,
  capture in claim order: boot → shell status/mem/ps →
  userspace trio → fault isolation → attract screen →
  Imperium dispatch receipt. Raw captures committed; editing
  is not yours.
- D2. Freeze certificate at 05:12 EST: one page on your
  branch — the main tip hash, the gate result, and the claim
  sentence with each clause pointing at the committed log
  that proves it.
- D3. Submission hygiene sweep: repo is public; run the
  secret scan over the tree; the README's top section says
  what this project is in plain words. Report anything that
  needs the boss (do not wait — post it and keep working).

## Reporting

Post to the branch and the crew room as each group closes:
A (with the log names), B (receipt id or blocker), C (the
four lines), D (certificate path). If you finish early, post
DONE and stand by — do not invent new scope.
