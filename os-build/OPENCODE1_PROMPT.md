# PROMPT FOR OPENCODE 1 — from Pax, 2026-11-02 (boss: Mrfentmen)

Pull the latest main of mrfentmen/meta-os and read this file first.

## Lane note
The boot lane is Buffy's now (RK-007, K3/K4 re-gates). Do not take boot
work back unless Mrfentmen tells you directly. Your §5 K3 pack and §6 K4
pack are on main and read by Pax: K3 demand leg FAILED (err 0x5, zero map
lines, held for a Rowan fix); K4 IPC lines all UNPROVEN (no talker/listener
pair, no spawn swap, held). Neither merges. That part is closed for you.

## Your work, in order
1. Finish §19, the submission rehearsal. Your status file says PARTIAL
   (463/465 runbook gaps, 452 freshness, 453 receipts open, X draft
   missing) while a commit message says DONE. Resolve it: finish each
   item, or file it BLOCKED in OPENCODE1_500_STATUS.md with the exact
   reason. The status file is the record that counts.
2. §7 soak: bring the fresh-main soak to a verdict. If the earlier soak
   died with your session, record that honestly in the status file and
   run a new one. No verdict carried over from memory.
3. Verify the §11 film on merged main: os-build/demo/demo-3min.mp4.
   ffprobe it — duration must be exactly 180.000s. Check every line of
   CAPTURE_NOTES.md against the film and the records. If a line is off,
   fix the notes or re-capture. Report the result in the status file.
4. §16 Officina run 2: run it only if Buffy's fix is on main. If it is
   not, re-file the blocker in one line and move on.
5. Continue OPENCODE1_TASKS_500.md (os-build/) in order from wherever
   OPENCODE1_500_STATUS.md says you stopped. Commit per section to
   branch opencode/500. Keep the status file current.

## Fences (unchanged, absolute)
- kernel/src is Rowan's pen. kernel/src/syscalls.rs is FROZEN.
- Imperium dispatch is the labelled simulated loopback endpoint only.
  Never a real 911 service, never a non-loopback dispatch URL.
- No mock or placeholder work presented as done. Label every claim
  VERIFIED / CODE-INSPECTED / UNIMPLEMENTED / BLOCKED.
- All merges to main go through Pax. You commit to your branch; he merges.
- Post build status to room 1 as things land, not only at the end.
