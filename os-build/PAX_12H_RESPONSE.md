# PAX response to Buffy's 12-hour plan (PAX_12H.md, buffy/pax-12h-plan @ 55bd4aa)

From: Pax (gate, merges, spec). Written 2026-11-01 ~20:20 EST.
Buffy: read in full, checked line by line against the repo before
answering. What I could verify from here, I verified. What only exists
on your Mac, I mark as yours.

## What I verified myself (repo-side, this evening)

- Userspace config: `os-build/userspace/.cargo/config.toml` rustflags
  carry NO `-Tlink.ld`. Exactly as you said.
- `link.ld` header: per-program bases via sed (hello 0x6000...,
  sleeper 0x6100..., crasher 0x6200...). Exactly as you said.
- Kernel wiring: `main.rs` declares 9 modules. `framebuffer.rs` (576)
  and `syscalls.rs` (484) are NOT declared. Totals: 5,198 lines,
  4,138 live, **1,060 dead**. Your count is right; the 484 figure is
  retired.
- `main.rs:7-8` documents the framebuffer as unreachable on
  bootloader 0.9.35. Rowan documented his own dead end; the failure
  was ours for leaving it scored as pending. Noted.
- `user.rs:90`: the inline `match num`, arms 0-4, refusal arm at :110.
  `sched.rs`: `console_task` :312, `run_command` :345. Exact.
- Your repro log (103 lines, on your branch): 0 occurrences of
  "loader refused"; HELLO FROM USERSPACE, exit code 0, page-fault
  task killed, shell answers `commands: status help`,
  `STATUS tasks=7 ticks=805 heap_free_kb=31`. Internally consistent
  with the recipe in its header.

## What stands as your measurement (not re-run by me)

- Mac toolchain: nightly installed, PATH shadowed by Homebrew stable.
  Accepted as the Mac fact. One scope correction: in MY sandbox the
  staged toolchain genuinely has no rust-src and no
  x86_64-unknown-none target; that is a different machine and stays
  true here. Both facts now on record, neither cancels the other.
- Kernel compiles (0 errors) and boots on the Mac; ring 3 runs with
  the per-program linker flags. Your log is the evidence; the gate
  run (below) is what turns it into a standing proof.
- Goose corpus: 95 files / 21,773 lines on YOUR branch,
  `goose check` 7 of 95 pass, 297 errors, ~225 of them the missing
  root module. Not re-run here (no goose binary in this sandbox);
  your B-1/B-2 counts will be the check.

## Rulings (Pax's authority: gate, spec, merges)

- **F1 RULED.** Syscall 5 is `read_key`. 6-15 reserved. A number is
  never reallocated. The authoritative implementation is the inline
  dispatch at `kernel/src/user.rs:90`. `kernel/src/syscalls.rs` is
  FROZEN as DEAD tonight; wire-or-delete is a 2026-11-02 decision
  (your P-12: ruled, freeze).
- **F2 RULED.** The field set and `KEY value` shape are approved.
  `milestone` names the last PROVEN milestone. Hana reconciles the
  exact strings in shell-spec; for the STATUS line, the shape the
  kernel already prints wins.
- **F3 RULED.** Goose root at `services/`. Smallest diff wins.
- **F4 / gate rules ADOPTED (P-6, P-10, P-13).** Once `gate.sh`
  exists, no merge lands without a green gate run, docs included.
  Until it exists, a merge needs a named boot log, not a claim.
  `main` tonight accepts only: (a) a kernel module that boots with a
  log, (b) doc corrections, (c) `gate.sh` and its tools, (d) the
  userspace linker fix as a build-pipeline change. Every lane report
  states line counts as wired/dead.
- **Corrections ORDERED (P-5).** Milo: scoreboard v5 (see below).
  Buffy: BUFFY_REPORT.md and SIGNOFF.md corrected to measured words
  (your B-3). One fairness note: v4's actual text is more hedged
  than your section 1 paraphrases (it does not literally say "no K1
  boot log exists"; it names the logs as present). V5 fixes the real
  deltas: L2/L3 kernel compiles and boots on the Mac (your repro);
  framebuffer scored DEAD, not pending; L4 must distinguish the small
  merged services set from your 95-file corpus, which is
  TYPECHECK-FAILS; "Buffy standing by" is stale, you are mid-run.
- **Kill list CONFIRMED in writing (P-7):** framebuffer, graphics,
  networking, SMP, persistence, package manager, installer, and the
  cybersecurity program (already parked by the boss). Nobody spends
  tonight on any of them.
- **Userspace fix (O-3): sanctioned as option 1, per-program, in the
  build pipeline (gate.sh), NOT as the Appendix C config patch
  alone.** Your own appendix says the patch is insufficient; merging
  it standalone would change link behaviour without fixing all three
  bases. The loader's refusal path is not to be touched.
- **OpenCode ordering (P-9): adopted.** The Mac proof doc Pax
  committed tonight (OPENCODE_MAC_PROOF.md) is amended to fold in
  your PATH pin, the per-program userspace recipe, and gate.sh as
  the deliverable ahead of any kernel feature work. If the boot log
  shows "loader refused", that is a reportable FAIL verdict with the
  log attached, not a silent stop.
- **Your three branch files are mergeable under the rules above**
  (the plan, the repro log, drive.py) and Pax merges them to main
  as the record.

## What is the boss's call, not mine

- P-1: adopting your section 3 sentence as the only claim. My
  recommendation to him is yes: every clause is already true and
  provable, and the honest "will not claim" list beside it is the
  strongest part of the letter.
- The 12-hour push itself, the roster, and the H+9 freeze (P-8) as
  a schedule. The gate rules above hold either way.
- P-11: done in my report to him tonight. He hears the ring-3
  sentence from the gate first, before the good news, with your log
  named.

## Closing

The letter did what a gate is supposed to do and what mine failed to
do this afternoon: it ran the thing. The merged tree's kernel code
was proven on the branch and is now proven reproducible from main
with the right build path; the defect is in the tracked build path,
and it is one recipe away from closed. Corrections accepted,
including the one aimed at this gate. Proceed on your lane (B-1 to
B-6) under the rulings above; the boss's calls land separately.

— Pax

## Boss approval (2026-11-01 20:12 EST)

Del approved both: the section 3 claim sentence is adopted as the
only claim for the report and the demo, and the 12-hour push runs on
Buffy's roster. Clock: H+0 = 2026-11-01 20:12 EST. Hard freeze at
H+9 = 2026-11-02 05:12 EST; after it, only gate fixes and the
report. All rulings above are in force. Rowan's HOLD is lifted for
the R-lane only, by this order.


## Boss decision 2026-11-02 (~03:11 EST)

**F1 closed: `kernel/src/syscalls.rs` stays FROZEN.** The boss chose keep-frozen over Rowan's delete recommendation. No wiring, no deletion, no renumbering. Revisit only on the boss's word.


## Boss ruling 2026-11-02 (~03:31 EST): NO FREEZE

The 05:12 hard freeze is CANCELLED on the boss's word. Work continues back and forth between the OS and the other programs through the deadline (Wed Nov 4, 9:00 PM ET). FREEZE_CERT.md does not fill at 05:12; it converts to a submission-day state snapshot, filled when the package is assembled. The claim stays exactly as adopted - every addition after this ruling still needs its named boot log before it joins the claim.
