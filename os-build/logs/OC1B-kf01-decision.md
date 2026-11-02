# OC1B-kf01 decision record (OC1B-040/045/046/047) — measured 2026-11-02, OpenCode 1

## Attempts
- Attempt 1: BLOCKED — origin/rowan/kernel-kf01-spike @ 8e725f4b is
  evidence-synthesis prose only (pin stays 0.9, no build, no boot).
  Classification (OC1B-033): NO ATTEMPT — nothing to classify; no log
  excerpt exists. Evidence: os-build/logs/OC1B-kf01-attempt1-branch.txt.
- Attempt 2: BLOCKED — no second fresh candidate branch exists anywhere.
  Classification (OC1B-039): NO ATTEMPT. Evidence:
  os-build/logs/OC1B-kf01-attempt2-branch.txt.

## OC1B-040 hard stop
HARD STOP: both KF-01 attempt slots stand EMPTY (0 of 2 consumed — the
round7 pair 0.10.9 API-fail / 0.11 std-fail counts as history, never
re-run, never charged). NO THIRD ATTEMPT will be made. Fallback route:
restored pin = the existing 0.9.35 pin (nothing ever moved).

## Decision (OC1B-045)
Route the evidence picks: RESTORED PIN (0.9.35). There is no upgraded
stack to gate — no upgraded tree exists. The pin record matches
OC1B-kf01-start.txt exactly (kernel/Cargo.toml:11 `version = "0.9"`;
kernel/Cargo.lock bootloader 0.9.35 checksum
e22d5a0b9e11dd5bee9d24a68885de6dc7ed367f897323b1c1286150fd469374).
Evidence paths: OC1B-kf01-start.txt, OC1B-kf01-attempt1-branch.txt,
OC1B-kf01-attempt2-branch.txt, OC1B-kf01-restored-gate.log.

## Timebox (OC1B-046)
Elapsed Mac-lane time from first spike-branch inspection to this decision:
~35 minutes (branch inventory + exhaustive pin scan + record writing,
2026-11-02 ~11:05–11:40 UTC). No builds were run against spike candidates
because none exist; the control gate run is recorded separately.

## OC1B-047 — syscalls.rs freeze verification
Command (run on /tmp/oc500, merge-base..tip for each gated Rowan branch):
  git diff <mb>..<tip> -- kernel/src/syscalls.rs
Output for origin/rowan/kernel-kf01-spike @ 8e725f4b:
  (empty — zero lines)
Output for origin/rowan/bootloader-spike @ 779012ed:
  (empty — zero lines)
Output for origin/spike/bootloader-0.11 @ db0b0020 (history, not gated):
  (empty — zero lines)
Output for origin/rowan/kernel-k3-build @ 7bb72075 (§5 gate):
  (empty — zero lines)
Output for origin/rowan/kernel-k4-build @ 4a37f998 (§6 gate):
  (empty — zero lines)
Quoted verdict: every diff above is EMPTY. kernel/src/syscalls.rs is
untouched on all Rowan branches this lane gates. FROZEN holds.
