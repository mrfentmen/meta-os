# ROWAN — 500 KERNEL TASKS (L1–L3)

Del's order, 2026-11-02: 500 tasks, the real OS, kernel first.

- **Owner:** Rowan. All kernel code is Rowan's pen (`kernel/src/`).
- **Scope:** L1 Boot, L2 Kernel core, L3 Drivers — bootloader, K3
  demand paging, K4 IPC, framebuffer/face, drivers, memory,
  scheduler, userspace ABI, resilience, self-tests, docs.
- **Status file:** `os-build/ROWAN_500_STATUS.md` — one line per
  task (id, branch, commit, proof artifact), updated as tasks land.
- **Branches:** one per section, named in each section heading
  (`rowan/<section-slug>`). Never work on main directly.
- **Merge rule (no exceptions):** no merge without (a) a committed
  boot log or screendump proof **read by Pax**, and (b) Milo
  gate-1 GREEN on the exact tip, from his own bus message.
  Pax merges; Rowan never self-merges.
- **Frozen:** `kernel/src/syscalls.rs` is NEVER edited, in any
  task, ever. New ABI surface lands only as inline dispatch in
  `kernel/src/user.rs`. Text boot stays first at every step:
  banner, alive line, ring 3, three programs, fault isolation,
  text shell — before any graphics claim.
- **Proofs ride the Mac:** kernel compiles and boots only on
  Del's Mac (OpenCode 1 lane, `os-build/gate.sh`). Boot logs land
  in `os-build/logs/`, screendumps in `os-build/captures/`.
  A branch claim without a committed artifact is unverified.
- **Tree facts this list is grounded in** (verify-clone,
  2026-11-02): `kernel/src/` = 13 files, 5,984 lines —
  memory.rs 1004, sched.rs 748, tasks.rs 702, interrupts.rs 599,
  framebuffer.rs 576 (unwired), syscalls.rs 484 (FROZEN),
  user.rs 492, mem.rs 331, main.rs 248, vga.rs 222,
  logo_frames.rs 217, traps.rs 199, gdt.rs 162.
- **KF source:** the kernel-face sections expand
  `KERNEL_FACE_BUILD_ORDER.md` (KF-01..KF-20) into sub-steps.
- **K3 source:** design approved 2026-11-02 (design doc lives on
  Rowan's design branch, not in the verify-clone). Class
  boundary: a fault is demand-retryable only if ALL of — present
  bit clear, caused by a ring-3 (user) access, no reserved-bit
  violation, not an instruction-fetch fault, address inside a
  per-task loader-registered PROMISED region, page not already
  mapped — plus the 2 anti-loop guards (allocation/mapping
  failure while servicing is fatal, never retried; mapping is
  verified present before the retry iret). Backing is zero-fill
  only. Exactly one demand program in the fleet. Q-D1 (map in
  handler vs park-and-map in scheduler context) is decided in
  writing inside the K3 build (RK-204).
- **K4 source:** design landed @0f5b557 — 1-message mailbox,
  non-blocking, ipc_send = 6 / ipc_recv = 7, dispatch in user.rs.
  Pax's K4 review has LANDED (@6e9a9a5, `os-build/K4_REVIEW_PAX.md`):
  APPROVE WITH CHANGES, numbers 6/7 assigned, Q-I1 ruled
  (MAX_TASKS stays 8 — swap demo programs, never grow the table).
  The review's 4 required changes are build requirements, carried
  at RK-276 / RK-293 / RK-303: (1) design §6 peer-id discovery
  mechanism stated, (2) design §4 mailbox-squatting limitation
  named, (3) mailbox clearing on every removal path, the
  fault-kill path included, (4) design §7 literal gate log lines
  pinned in advance. S12–S13 build tasks are unblocked on those
  terms — the review gate is satisfied-with-changes, not pending.

---

## S1 — Bootloader spike & decision, KF-01 sub-steps (branch: rowan/bootloader-spike)

- RK-001 — Read the 0.10.9 API-fail and 0.11 std-fail evidence on `opencode/round7` and write a failure summary (exact errors, exact versions) as the first entry of the decision record in `os-build/face/KERNEL_FACE.md`. Proof: record committed on the branch; Pax reads it.
- RK-002 — Dump the current boot stack into the record: bootloader requirement line from `kernel/Cargo.toml`, locked version 0.9.35 from `kernel/Cargo.lock`, bootimage config, and the BootInfo fields `main.rs` actually reads today. Proof: record section committed; values match the tree (Pax spot-checks two).
- RK-003 — Build a version table for bootloader 0.9.35 → newest 0.11.x from docs.rs: for each, whether BootInfo carries a framebuffer and what the framebuffer type is called. Proof: table in the record with a docs.rs citation per row.
- RK-004 — Write the API-delta list between 0.9.35 and the chosen target: every renamed/removed item `main.rs`, `memory.rs`, and `mem.rs` touch. Proof: delta list in the record, one row per item, each marked "used by us" or "unused".
- RK-005 — Pick target version #1 and write the rationale (fewest delta rows that still yields a framebuffer) into the record. Proof: rationale paragraph committed; Pax approves or redirects on the bus before RK-006 starts.
- RK-006 — Create branch `rowan/bootloader-spike` off current main; change ONLY the bootloader pin (Cargo.toml + Cargo.lock). Proof: branch diff vs main touches exactly 2 files.
- RK-007 — Run the Mac build on the bumped pin and capture the full compiler error list verbatim into the record. Proof: error list committed; OpenCode 1 build log in `os-build/logs/RK007-build.txt`.
- RK-008 — Fix import/path breakage from the bump (module paths, feature flags) as its own commit, no logic changes. Proof: build log shows that error class gone; diff contains no logic edits.
- RK-009 — Fix BootInfo construction/access breakage (renamed fields, option-vs-value changes) as its own commit. Proof: build log in `os-build/logs/RK009-build.txt`; kernel links.
- RK-010 — Fix any `memory.rs` boot-memory-map API breakage from the bump, keeping the allocator's view of regions byte-identical in meaning. Proof: boot log shows the same region summary line as the pre-bump baseline log.
- RK-011 — Boot the unmodified kernel (zero graphics code) on the new bootloader in QEMU. Proof: serial log `os-build/logs/RK011-boot.txt` carries the K6 banner and the alive line.
- RK-012 — Screendump the RK-011 boot's text console. Proof: `os-build/captures/rk011-text.png` committed beside the log.
- RK-013 — Run the shell smoke on the new bootloader: type status, mem, ps via the existing input path. Proof: RK-011 log contains all three answers with real values.
- RK-014 — Run the fault-isolation smoke on the new bootloader: the crasher program faults and is killed alone. Proof: RK-011 log shows the kill line and the shell answering afterwards; panic count 0.
- RK-015 — Run the bad-syscall smoke: syscall 99 from userspace. Proof: RK-011 log shows the refusal line, shell still alive.
- RK-016 — Write the framebuffer-availability probe: one temporary serial print of whether BootInfo carries a framebuffer and its raw fields. Proof: log line `fb-probe: present <w>x<h>` or `fb-probe: absent` in `os-build/logs/RK016-boot.txt`.
- RK-017 — If RK-016 says absent on target #1: pick target version #2 from the RK-003 table and repeat the pin-only bump on the same branch. Proof: second pin commit; record updated with why #1 failed the probe.
- RK-018 — Repeat RK-007..RK-016 against target #2 (build fixes as separate commits, boot, smokes, probe). Proof: `os-build/logs/RK018-boot.txt` with banner, alive line, three smokes, and the fb-probe line.
- RK-019 — Write the spike verdict into the record: PROVEN (version, probe result) or FAILED (evidence for both targets). Proof: verdict section committed; Pax reads it and posts the route call on the bus.
- RK-020 — If FAILED: restore the 0.9.35 pin (Cargo.toml + Cargo.lock exactly as on main) on the branch. Proof: diff vs main is empty for both files.
- RK-021 — If FAILED: re-run gate.sh on the restored stack via OpenCode 1. Proof: `os-build/logs/RK021-gate.txt` — gate GREEN 7/7.
- RK-022 — If FAILED: write the UEFI-GOP re-spike brief (what GOP gives, what the bootloader bypass costs, what breaks) as a decision input for Pax — brief only, no code. Proof: brief appended to the record; Pax owns the next call.
- RK-023 — If PROVEN: freeze the spike branch; write the exact pin + lockfile hashes into the record as the new baseline. Proof: hashes in the record match the branch files (Pax verifies).
- RK-024 — Write the "what the upgrade changed for free" note: any behaviour differences observed vs 0.9.35 (boot time, memory map ordering, serial quirks). Proof: note in the record; each claim tied to a named log.
- RK-025 — Close S1: update `os-build/ROWAN_500_STATUS.md` for RK-001..RK-025 with commit + artifact per task. Proof: status file committed; Pax checks three entries at random against the artifacts.

## S2 — Gate the upgraded stack, KF-02 sub-steps (branch: rowan/bootloader-spike)

- RK-026 — Assemble the KF-02 gate pack checklist in `os-build/logs/RK026-gate-pack.md`: the seven gate elements, each with the exact log line that proves it. Proof: checklist committed before the gate run happens.
- RK-027 — Cold-boot gate run #1 on the upgraded stack, full serial capture from power-on. Proof: `os-build/logs/RK027-gate.txt` exists and starts at the banner.
- RK-028 — Verify gate element 1 (banner + alive line) in the RK-027 log and mark it in the checklist with the line numbers. Proof: checklist updated with line refs.
- RK-029 — Verify gate element 2 (ring-3 drop: the three userspace programs start) in the RK-027 log, line refs into the checklist. Proof: checklist updated.
- RK-030 — Verify gate element 3 (readkey: typed a, b, return → "readkey: enter seen, done got=3") in the RK-027 log. Proof: exact line quoted in the checklist.
- RK-031 — Verify gate element 4 (fetch screen live: real task and memory numbers) in the RK-027 log. Proof: numbers quoted in the checklist.
- RK-032 — Verify gate element 5 (status ticks advance: two status answers with increasing tick counts) in the RK-027 log. Proof: both tick values quoted.
- RK-033 — Verify gate element 6 (bad syscall 99 refused, shell alive after) in the RK-027 log. Proof: refusal line quoted.
- RK-034 — Verify gate element 7 (crasher killed, isolation holds, panic count 0) in the RK-027 log. Proof: kill line quoted; explicit "panic count: 0" written in the checklist.
- RK-035 — Screendump the gate boot at the shell. Proof: `os-build/captures/rk035-gate-shell.png`.
- RK-036 — Repeat the cold-boot gate run (#2) to prove the upgraded stack is not a one-off. Proof: `os-build/logs/RK036-gate.txt`, all seven elements present.
- RK-037 — Repeat the cold-boot gate run (#3). Proof: `os-build/logs/RK037-gate.txt`, all seven elements present.
- RK-038 — Diff the three gate logs' key values (banner, alive, got=3, tick ranges) and write the stability note. Proof: note appended to the gate-pack file; any variance named, none hidden.
- RK-039 — Confirm Cargo.lock on the branch is the ONLY dependency change vs main (no silent transitive surprises beyond the bootloader tree). Proof: lockfile diff summary in the gate-pack file.
- RK-040 — Write the rollback card into the gate-pack file: exact commands to return to the 0.9.35 pin and re-gate, for use if a later section breaks the boot. Proof: card committed; Pax reads it.
- RK-041 — Milo gate-1 request post for the S1+S2 branch tip: exact SHA, exact artifact list. Proof: bus post made by Rowan; Milo's GREEN or RED from his own message is the record.
- RK-042 — Fix any gate-1 finding from RK-041 as its own commit (no scope creep). Proof: new tip SHA posted; Milo re-gates.
- RK-043 — Pax merge-readiness summary for S1+S2: one page in the gate-pack file listing artifacts Pax must read. Proof: summary committed; merge happens only after Pax confirms reads on the bus.
- RK-044 — Post-merge regression watch: after Pax merges S1+S2, boot main once on the Mac lane and capture the log. Proof: `os-build/logs/RK044-main-boot.txt` on main with all seven elements.
- RK-045 — If RK-044 fails on main: write the bisect note (spike branch tip vs merged main, first differing file). Proof: note committed; no fix attempted until Pax calls it.
- RK-046 — Update KERNEL_FACE.md's honest-status section for the new bootloader baseline (what is now PROVEN). Proof: doc commit; claims match RK-027/RK-036/RK-037 logs.
- RK-047 — Retire the fb-probe temporary print from RK-016 (remove or gate it behind a boot flag) with the decision written in the commit message. Proof: boot log after the change carries no probe line (or only with the flag).
- RK-048 — Boot-time measurement: serial timestamps for banner, alive, shell-ready on the new stack vs the 0.9.35 baseline. Proof: numbers table in the gate-pack file, sourced from named logs.
- RK-049 — Memory-map equivalence check: region list on the new stack vs baseline, differences explained line by line. Proof: comparison table in the gate-pack file.
- RK-050 — Close S2 in `os-build/ROWAN_500_STATUS.md` (RK-026..RK-050). Proof: status file committed; Pax spot-checks the gate artifacts.


## S3 — Framebuffer wiring, KF-03 sub-steps (branch: rowan/framebuffer-wiring)

- RK-051 — Read `kernel/src/framebuffer.rs` (576 lines) end to end and write a wiring memo: constructor inputs, pixel-format assumptions, what BootInfo must supply. Proof: memo committed on the branch; Pax reads it before code lands.
- RK-052 — Map every framebuffer.rs public function to its first caller (or "no caller yet") in the memo. Proof: function table in the memo; framebuffer.rs has no other public surface unlisted.
- RK-053 — Declare `mod framebuffer;` in `kernel/src/main.rs` and get the crate compiling with the module present but unconstructed. Proof: Mac build log clean; boot log unchanged (banner + alive + shell), `os-build/logs/RK053-boot.txt`.
- RK-054 — Construct the `Framebuffer` from the new BootInfo in main.rs behind a compile-time flag, default OFF. Proof: flag-off boot log identical in claims to RK-053.
- RK-055 — Flip the flag ON in a test commit: construct the framebuffer and print the serial line `fb: <width>x<height> pitch <n> fmt <format>`. Proof: line present in `os-build/logs/RK055-boot.txt`.
- RK-056 — Clear the screen to solid blue through the framebuffer on init. Proof: screendump `os-build/captures/rk056-blue.png` — solid blue frame, no text.
- RK-057 — Verify pitch handling: clear using pitch-aware row writes (not width×bpp assumptions) and state in the commit which the code does. Proof: rk056 screendump has no diagonal tearing/striping; commit message states the addressing used.
- RK-058 — Verify pixel format: write one red, one green, one white pixel at known coordinates and confirm channel order from the screendump. Proof: `os-build/captures/rk058-rgb.png` shows the three pixels in the stated colours and order.
- RK-059 — Handle the absent-framebuffer case in code: construction failure path prints `fb: absent` on serial and continues to the text console. Proof: forced-absent boot log (flag/bootloader config) shows `fb: absent` then a working shell.
- RK-060 — Handle the unsupported-format case: unknown pixel format prints `fb: unsupported fmt <format>` and stays on text. Proof: code path committed with the exact serial string; unit-style source note in the wiring memo (runtime forcing method stated honestly, or marked code-inspected).
- RK-061 — Make the flag a boot-time choice (kernel command line or boot flag word) instead of compile-time, defaulting to text-first boot with graphics after the text phase. Proof: two boot logs, flag off and flag on, same tree.
- RK-062 — Ensure the text phase completes BEFORE any framebuffer takeover: banner, alive, programs, isolation all precede the `fb:` line in the serial order. Proof: RK-061 flag-on log shows that exact ordering.
- RK-063 — Double-buffer decision note: state whether drawing writes the front buffer directly, and what tearing that implies for animation. Proof: note in the wiring memo; KF animation sections cite it.
- RK-064 — Add a framebuffer self-check at init: write and (where the format allows) verify a test pattern region, print `fb: selfcheck ok` or the failure. Proof: serial line in the flag-on boot log.
- RK-065 — Measure clear-screen time for a full frame and print it once (`fb: clear <n> ticks`). Proof: line in the boot log; number quoted in the memo.
- RK-066 — Fix any defect found in framebuffer.rs during wiring as a separate flagged commit (per the KF-03 rule), never silently inside a wiring commit. Proof: commit exists and is flagged in the status file, or the memo states "no defects found".
- RK-067 — Screendump set for the wiring milestone: blue frame, RGB pixels, flag-off text boot. Proof: three named captures committed together.
- RK-068 — Gate rerun with the flag ON: full gate.sh. Proof: `os-build/logs/RK068-gate.txt` GREEN 7/7, panic count 0.
- RK-069 — Gate rerun with the flag OFF. Proof: `os-build/logs/RK069-gate.txt` GREEN 7/7.
- RK-070 — Milo gate-1 request post for the S3 tip (exact SHA + artifact list). Proof: Milo's verdict from his own bus message.
- RK-071 — Fix gate-1 findings from RK-070 as separate commits. Proof: new tip posted; Milo re-gates.
- RK-072 — Write the framebuffer bring-up doc section in `os-build/face/KERNEL_FACE.md`: init order, flag, failure lines, format table. Proof: doc commit; every serial string quoted exists in the code (Pax greps two).
- RK-073 — Remove any leftover probe/debug prints from the wiring path not listed in the doc. Proof: boot log diff vs RK-068 shows only listed lines.
- RK-074 — Regression boot: cold boot ×3 with flag on, confirm `fb:` line and blue frame every time. Proof: three logs + one screendump committed.
- RK-075 — Close S3 in `os-build/ROWAN_500_STATUS.md` (RK-051..RK-075). Proof: status file committed; Pax reads the RK-068/RK-069 gates before merge.

## S4 — Pixel text & pixel console, KF-04 sub-steps (branch: rowan/pixel-text)

- RK-076 — Inventory the glyph source used by `draw_glyph` in framebuffer.rs: font origin, license note (FONT_TABLE_LICENSE.md), glyph size, character coverage. Proof: inventory in the S4 section of the wiring memo.
- RK-077 — Draw the string `META OS` at fixed coordinates on the blue frame via the glyph path. Proof: screendump `os-build/captures/rk077-text.png`, string legible.
- RK-078 — Draw the K6 banner line under it, same boot. Proof: same screendump shows both strings; serial line `fbtext: ok` in `os-build/logs/RK078-boot.txt`.
- RK-079 — Implement/verify a pixel-space string writer (per-char advance, space handling) if `write_str` on the pixel console does not already cover it; state which in the commit. Proof: a pangram line drawn and screendumped, spacing visibly even.
- RK-080 — Define the text grid: columns/rows for the target framebuffer size, computed from glyph size, printed once on serial (`fbtext: grid <cols>x<rows>`). Proof: line in the boot log; numbers match the framebuffer size from the `fb:` line.
- RK-081 — Implement newline handling in the pixel console: `\n` moves to the next row start. Proof: two-line draw screendump with the second line at column 0.
- RK-082 — Implement carriage-return/overwrite semantics or explicitly reject `\r` with a memo note. Proof: memo states the behaviour; screendump or code citation backs it.
- RK-083 — Implement bottom-of-screen behaviour: `scroll_up_pixels` wired so text scrolls instead of wrapping onto the top. Proof: screendump pair — full screen of lines, then one more line, first line gone.
- RK-084 — Print the full printable ASCII range (0x20–0x7E) as pixel text in one boot for a glyph audit. Proof: `os-build/captures/rk084-ascii.png`; any missing/wrong glyph listed in the memo.
- RK-085 — Fix glyph defects found in RK-084 (one commit per glyph class). Proof: re-run screendump shows the fixed glyphs.
- RK-086 — Unknown-character behaviour: draw a defined placeholder glyph for bytes outside coverage, never panic, never skip silently. Proof: test string with 0x01 and 0x80 drawn; screendump shows placeholders.
- RK-087 — Colour control: pixel text foreground/background settable per write (default white on blue). Proof: screendump with one line in a second colour pair.
- RK-088 — Cursor for the pixel console: a visible block/underline at the next write position, drawn and erased correctly on advance. Proof: screendump pair before/after one character typed.
- RK-089 — Backspace in the pixel console: erases the previous glyph cell and moves the cursor back; at column 0 it does nothing harmful. Proof: serial-driven test draw + screendump; memo states col-0 behaviour.
- RK-090 — Long-line behaviour: lines longer than the grid wrap or clip per a written rule (choose one, write it). Proof: screendump of an over-long line behaving per the rule.
- RK-091 — Performance note: time to render one full screen of text, printed once (`fbtext: full <n> ticks`). Proof: line in a boot log; number in the memo.
- RK-092 — Keep the VGA text console untouched by S4: serial + VGA outputs unchanged when the flag is off. Proof: flag-off boot log diff vs RK-069 shows no text-console change.
- RK-093 — Dual-output check: with the flag on, shell output still goes to serial exactly as before (pixel rendering is additive). Proof: flag-on log's shell answers byte-match the flag-off answers for status/mem/ps.
- RK-094 — Gate rerun, flag on. Proof: `os-build/logs/RK094-gate.txt` GREEN 7/7.
- RK-095 — Gate rerun, flag off. Proof: `os-build/logs/RK095-gate.txt` GREEN 7/7.
- RK-096 — Milo gate-1 request post for the S4 tip. Proof: Milo's verdict from his own bus message.
- RK-097 — Fix gate-1 findings from RK-096 as separate commits. Proof: new tip; Milo re-gates.
- RK-098 — Doc: pixel-text section in KERNEL_FACE.md (grid rule, wrap rule, colours, placeholder glyph, cursor). Proof: doc commit; rules match screendumps RK-081/RK-083/RK-090.
- RK-099 — Screendump set for S4 close: banner text, ASCII audit, scrolled screen, cursor pair. Proof: four named captures committed.
- RK-100 — Close S4 in `os-build/ROWAN_500_STATUS.md` (RK-076..RK-100). Proof: status committed; Pax reads RK-094/RK-095 before merge.


## S5 — Graphics boot sequence & failure fallback, KF-05/KF-08 sub-steps (branch: rowan/graphics-boot)

- RK-101 — Define the boot-phase handover point in code: the exact function after which the text phase is complete and graphics may take the screen; name it in the S5 memo. Proof: memo committed; the handover function is greppable.
- RK-102 — Capture the boot lines of the current boot (banner, alive, milestone, program list) into a kernel-side buffer during the text phase, instead of re-typing canned strings. Proof: code committed; memo states buffer size and overflow behaviour.
- RK-103 — Re-render the captured boot lines as pixel text after handover. Proof: screendump `os-build/captures/rk103-bootlines.png`.
- RK-104 — Pax-diff check: the words in RK-103 must equal the serial log of the same boot. Proof: `os-build/logs/RK104-boot.txt` committed beside the screendump; diff result written in the status file.
- RK-105 — Include the live values (task count, ticks) in the re-rendered lines from the same boot's state, not constants. Proof: two boots with different tick values screendumped; lines differ accordingly.
- RK-106 — Boot-flag matrix doc: flag on/off × framebuffer present/absent — the four outcomes, each with its serial signature. Proof: matrix in the memo; RK-107..RK-110 produce the logs.
- RK-107 — Matrix cell 1 (flag on, fb present): full graphics boot. Proof: boot log + screendump committed.
- RK-108 — Matrix cell 2 (flag on, fb absent): fallback line `fb: unavailable, staying on text console` plus the reason, then a working text shell. Proof: `os-build/logs/RK108-fallback.txt` shows the fallback line followed by a `status` answer.
- RK-109 — Matrix cell 3 (flag off, fb present): pure text boot, no `fb:` line. Proof: boot log committed.
- RK-110 — Matrix cell 4 (flag off, fb absent): pure text boot. Proof: boot log committed.
- RK-111 — Fallback reason strings: enumerate every distinct failure reason the fallback line can carry (absent, unsupported fmt, selfcheck fail) in the memo, each mapped to its code path. Proof: memo table; RK-112 forces at least one more.
- RK-112 — Force the selfcheck-fail fallback (test hook) and boot it. Proof: log shows `fb: unavailable, staying on text console` with the selfcheck reason, shell answering after.
- RK-113 — Ensure the fallback is reachable AFTER a partial graphics init (framebuffer constructed, first draw fails) — no wedged screen, no panic. Proof: code path committed; forcing method and result stated honestly in the memo (log or code-inspected).
- RK-114 — Serial remains authoritative in all cells: every graphics-phase event that matters also prints to serial. Proof: RK-107 log contains the handover line and the draw-complete line.
- RK-115 — Add the handover serial line: `face: handover after text phase` printed exactly once per graphics boot. Proof: line present in RK-107 log, absent in RK-109 log.
- RK-116 — Add the graphics-ready line: `face: ready` after the boot lines are re-rendered. Proof: line ordering in RK-107 log (handover → ready).
- RK-117 — Boot-to-face timing: ticks from alive line to `face: ready`, printed once. Proof: line in RK-107 log; number recorded in the memo.
- RK-118 — Repeat graphics boot ×3 cold: handover and ready lines every time, no intermittent fallback. Proof: three logs committed.
- RK-119 — Repeat fallback boot ×2 cold: fallback line and shell every time. Proof: two logs committed.
- RK-120 — Gate rerun on the S5 tip (flag default). Proof: `os-build/logs/RK120-gate.txt` GREEN 7/7, panic count 0.
- RK-121 — Milo gate-1 request post for the S5 tip. Proof: Milo's verdict from his own bus message.
- RK-122 — Fix gate-1 findings from RK-121 as separate commits. Proof: new tip; Milo re-gates.
- RK-123 — Doc: boot-sequence section in KERNEL_FACE.md (handover point, flag matrix, fallback line + reasons, serial lines). Proof: doc commit; every quoted serial string greps in the code.
- RK-124 — Remove the RK-112 test hook from the shipping path or gate it behind the boot flag, with the choice stated in the commit. Proof: normal boot log carries no hook artefacts.
- RK-125 — Close S5 in `os-build/ROWAN_500_STATUS.md` (RK-101..RK-125). Proof: status committed; Pax reads RK-108 and RK-120 before merge.

## S6 — Kernel-drawn ribbon boot screen, KF-06/KF-07 sub-steps (branch: rowan/ribbon-screen)

- RK-126 — Port the ribbon math from `js/logo-background.js` to a kernel Rust module (`kernel/src/ribbon.rs` or a section of main.rs — state the choice): same sine family, same blue; no pre-rendered frames blitted. Proof: module committed; memo cites the JS lines each formula came from.
- RK-127 — Unit-shape check on paper: compute three sample points of the Rust port by hand/script from the JS and from the Rust formula; show they agree. Proof: worked numbers in the S6 memo (this is a math check, not a boot claim).
- RK-128 — Draw one static ribbon frame full-screen over the dark background. Proof: screendump `os-build/captures/rk128-ribbon.png`.
- RK-129 — Draw the boot status line (from S5's captured lines) under the ribbon on the same screen. Proof: same screendump shows both; words match the boot's serial log.
- RK-130 — Frame counter: increment per drawn frame, printed to serial every 60 frames (`face: frame <n>`). Proof: boot log shows at least `frame 60` and `frame 120`.
- RK-131 — Second-phase capture: screendump the ribbon at a different phase than RK-128. Proof: `os-build/captures/rk131-ribbon-b.png`; the two phases visibly differ; frame-counter values at each capture noted in the status file.
- RK-132 — Colour fidelity check: sample the ribbon's blue in both screendumps and state the RGB values vs the web face's blue. Proof: values written in the memo; any difference named, not smoothed over.
- RK-133 — Ribbon as a scheduled task: move frame drawing into a kernel task so the scheduler drives it, not a boot-time busy loop. Proof: `ps` output during the attract phase (via serial command or logged snapshot) lists the ribbon task.
- RK-134 — Yield behaviour: the ribbon task must not starve the shell/input path — type during animation and show the input is still read. Proof: boot log shows a keypress handled while the frame counter is advancing.
- RK-135 — Frame-rate measurement: frames drawn over a fixed tick window, printed once (`face: fps-ish <n> frames / <t> ticks` — named honestly as a tick ratio, not fps). Proof: line in a boot log; number in the memo.
- RK-136 — Keypress exit: any key ends the attract phase and hands control to the shell phase, mirroring today's text attract behaviour. Proof: boot log shows frame counter advancing, then the exit line, then a shell answer.
- RK-137 — Exit-line serial contract: `face: exit on key, shell live` printed exactly once on exit. Proof: line in the RK-136 log.
- RK-138 — No-key path: leave the attract running 5 minutes; it must not fault, leak frames, or wedge. Proof: soak log excerpt with first/last frame counters and a final keypress exit.
- RK-139 — Memory behaviour: frame drawing allocates nothing per frame after setup (state the truth of the implementation in the memo; if it allocates, say where). Proof: memo statement tied to the code; heap-used value from `mem` before/after 1,000 frames in a log.
- RK-140 — Resolution behaviour: ribbon math parameterized by the actual framebuffer width/height (no hard-coded 800×600 assumptions). Proof: memo states the parameterization; if a second resolution is testable on the Mac lane, a screendump at that size, else marked code-inspected.
- RK-141 — Dark-background contract: background colour constant named in code and in the memo, matching the approved face design. Proof: screendump background sample value quoted in the memo.
- RK-142 — Boot lines stay available: from the ribbon screen, the S5 boot lines remain on screen or one keystroke away (state which). Proof: screendump or log showing the path.
- RK-143 — Gate rerun with the ribbon in the boot path. Proof: `os-build/logs/RK143-gate.txt` GREEN 7/7 (text phase elements all present before handover).
- RK-144 — Milo gate-1 request post for the S6 tip. Proof: Milo's verdict from his own bus message.
- RK-145 — Fix gate-1 findings from RK-144 as separate commits. Proof: new tip; Milo re-gates.
- RK-146 — Doc: ribbon section in KERNEL_FACE.md (math source, task model, exit contract, frame lines). Proof: doc commit; serial strings quoted grep in the code.
- RK-147 — Screendump set for S6 close: static frame, second phase, status-line screen, exit aftermath (shell). Proof: four named captures committed.
- RK-148 — Regression: text attract screen (logo_frames.rs) still works with the flag off. Proof: flag-off boot log shows the ASCII attract cycling and exiting on key.
- RK-149 — Decide and write down the flag-off default for the ribbon (does the shipping default boot to ribbon or text attract?) as a Pax decision input — decision input only, Pax rules. Proof: input note in the memo; no default changed by this task.
- RK-150 — Close S6 in `os-build/ROWAN_500_STATUS.md` (RK-126..RK-150). Proof: status committed; Pax reads RK-136/RK-143 before merge.


## S7 — Window layer & the real shell in a window, KF-09/KF-10 sub-steps (branch: rowan/window-shell)

- RK-151 — Window geometry spec in the S7 memo: border width, title-bar height, body inset, colours — as named constants before any drawing code. Proof: memo committed; constants later grep to the values stated.
- RK-152 — Draw one filled rectangle body over the ribbon desktop background using `fill_rect`. Proof: screendump `os-build/captures/rk152-rect.png`.
- RK-153 — Draw the window border (four edges) around the body. Proof: screendump shows a closed border with no gaps at corners.
- RK-154 — Draw the title bar: a filled band across the top of the window, in the spec's title colour. Proof: screendump `os-build/captures/rk154-titlebar.png`.
- RK-155 — Draw the title text `Shell` in the title bar via the pixel text path. Proof: same screendump, title legible.
- RK-156 — Compose order contract: background → window body → border → title bar → title text, written in the memo and followed in code. Proof: memo + code citation.
- RK-157 — Window state struct: position, size, title, and a body text buffer reference — the minimal real window record. Proof: struct committed; fields listed in the memo.
- RK-158 — Move the window: redraw at a second position from the state struct (position is data, not constants). Proof: screendump pair at two positions.
- RK-159 — Resize from the state struct: redraw at a second size. Proof: screendump pair at two sizes.
- RK-160 — Clipping rule: a window partially off-screen draws only its visible part, never writes outside the framebuffer. Proof: screendump with the window half off the right edge; no wrap-around artefacts on the left.
- RK-161 — Body text area: define the body's text grid (origin inset, columns, rows) from the window size and glyph size. Proof: memo numbers; a full-grid draw screendump matches the count.
- RK-162 — Route shell output into the window body: one shell answer (`status`) rendered as pixel text inside the window. Proof: screendump `os-build/captures/rk162-shell-status.png`.
- RK-163 — Route keyboard input to the shell while the window is shown: type `status` on the real keyboard path, answer appears in the window. Proof: screendump after typing + serial log of the same boot; values match between window and serial.
- RK-164 — `mem` answered inside the window with real values. Proof: screendump; values match the same boot's serial `mem`.
- RK-165 — `ps` answered inside the window with the real task list. Proof: screendump; task rows match the same boot's serial `ps`.
- RK-166 — `uptime` and `help` answered inside the window. Proof: screendump set (one per command or one combined, stated which).
- RK-167 — Echo: typed characters appear in the window as they are typed (through the S4 cursor), including backspace correction. Proof: screendump pair — typo, then corrected line.
- RK-168 — Scrolling inside the window: more answers than body rows scroll the body only, title bar and border unmoved. Proof: screendump pair before/after overflow.
- RK-169 — Serial mirror stays exact: every answer shown in the window is byte-identical on serial for the same boot. Proof: one boot log + screendump pair where Pax can compare `ps` directly.
- RK-170 — Ribbon/desktop behind the window stays drawn (window over background, not a mode switch to a blank screen). Proof: RK-163 screendump shows the desktop around the window.
- RK-171 — Window redraw cost: ticks to redraw the full window once, printed once (`face: winredraw <n> ticks`). Proof: line in a boot log.
- RK-172 — Failure honesty: if the shell faults inside the window path, the fault isolation behaviour is the kernel's existing one (task killed, machine alive) — demonstrate with the crasher while the window is up. Proof: boot log kill line + screendump of the window still present after.
- RK-173 — Gate rerun with the window shell in the boot path. Proof: `os-build/logs/RK173-gate.txt` GREEN 7/7.
- RK-174 — Milo gate-1 request post for the S7 tip. Proof: Milo's verdict from his own bus message.
- RK-175 — Fix gate-1 findings from RK-174 as separate commits. Proof: new tip; Milo re-gates.
- RK-176 — Doc: window-layer section in KERNEL_FACE.md (geometry constants, compose order, clipping rule, mirror contract). Proof: doc commit; constants quoted match the code.
- RK-177 — Second window skeleton: draw a second, empty window (title `Notes`) overlapping the shell window, static — the overlap pixels belong to the top window per a written rule. Proof: screendump; rule stated in the memo (full focus/raising is KF-13, not claimed here).
- RK-178 — Focus indicator groundwork: the shell window's title bar drawn in the "focused" colour, the Notes window in the "unfocused" colour, statically assigned. Proof: same screendump shows both colours; memo names them.
- RK-179 — Regression: flag-off boot is untouched by S7. Proof: flag-off gate log GREEN 7/7.
- RK-180 — Close S7 in `os-build/ROWAN_500_STATUS.md` (RK-151..RK-180). Proof: status committed; Pax reads RK-163/RK-173 before merge.

## S8 — Milestone 1 proof pack & gate extension, KF-11/KF-20 sub-steps (branch: rowan/m1-proof)

- RK-181 — Write the KF-11 capture script/checklist for OpenCode 1: exact QEMU steps, exact screendump moments (text phase, ribbon, shell window), exact file names. Proof: checklist committed in `os-build/logs/RK181-kf11-checklist.md` before the run.
- RK-182 — Cold boot capture run: full serial log from power-on to shell-in-window answers. Proof: `os-build/logs/KF11-m1-boot.txt` committed; panic count 0 stated in the status file after Pax-style count.
- RK-183 — Screendump 1 of the set: text phase (banner/alive visible in VGA text). Proof: `os-build/captures/kf11-set/01-text.png`.
- RK-184 — Screendump 2 of the set: ribbon boot screen. Proof: `os-build/captures/kf11-set/02-ribbon.png`.
- RK-185 — Screendump 3 of the set: desktop with the shell window holding a live `status` answer. Proof: `os-build/captures/kf11-set/03-shell.png`.
- RK-186 — Cross-check the set: the `status` numbers in 03-shell.png equal the KF11 log's serial `status` of the same boot. Proof: comparison written in the status file with both values quoted.
- RK-187 — Gate run on the exact KF-11 tree. Proof: gate GREEN 7/7 result committed beside the log; tree SHA recorded.
- RK-188 — Second cold boot of the KF-11 tree, same captures, to prove repeatability. Proof: second log + one repeated screendump committed.
- RK-189 — Write the Milestone 1 claim page: the definition-of-done paragraph with each clause mapped to its artifact. Proof: page in `os-build/face/KERNEL_FACE.md`; Pax marks Milestone 1 only from these artifacts.
- RK-190 — List what Milestone 1 is NOT on the claim page (no mouse, no compositor, no graphical dashboard yet — Milestone 2). Proof: NOT-list present on the page.
- RK-191 — KF-20 design: how gate.sh gains the face boot log as a second artifact without weakening the text-claim gate — design note only. Proof: note committed; OpenCode 1 reviews it on the bus.
- RK-192 — Implement the gate.sh second-artifact capture (script change on the Mac lane, Rowan reviews the diff). Proof: gate output shows both artifacts produced.
- RK-193 — Run the extended gate: text gate GREEN 7/7 AND face artifact present. Proof: `os-build/logs/RK193-gate.txt`.
- RK-194 — Negative test the extension: break the face artifact path (rename) and show the TEXT gate still reports honestly (not a false green). Proof: log of the negative run committed with the expected failure named.
- RK-195 — Soak pre-check for KF-17: face up 10 minutes, ribbon animating, shell answering at the end. Proof: soak log with first/last timestamps + final `status`.
- RK-196 — Fix any soak pre-check finding (leak, wedge, counter wrap) as its own commit. Proof: re-run log, or the status file states "no findings".
- RK-197 — Milo gate-1 request post for the S8 tip. Proof: Milo's verdict from his own bus message.
- RK-198 — Fix gate-1 findings from RK-197 as separate commits. Proof: new tip; Milo re-gates.
- RK-199 — Update the honest-status section of KERNEL_FACE.md to the post-M1 truth (PROVEN / CODE-INSPECTED / UNIMPLEMENTED lists rewritten from artifacts). Proof: doc commit; every PROVEN item cites a log or capture by name.
- RK-200 — Close S8 in `os-build/ROWAN_500_STATUS.md` (RK-181..RK-200) and write the Milestone 2 entry conditions (KF-12..KF-16 dependencies) at the end of the status file. Proof: status committed; Pax confirms M1 state from artifacts, not from the status file's say-so.


## S9 — K3 demand paging: fault-handler core (branch: rowan/k3-demand-paging)

- RK-201 — Re-read the approved K3 design and write the build plan in `os-build/K3_BUILD_PLAN.md`: design section → code location mapping for every mechanism (class boundary, promised regions, zero-fill, guards). Proof: plan committed; Pax checks the mapping against the design.
- RK-202 — Locate the current page-fault path (interrupts.rs / traps.rs) and document today's behaviour for a ring-3 not-present fault (what prints, what dies). Proof: plan section with a baseline boot log showing today's behaviour on an out-of-region fault.
- RK-203 — Extract the fault error-code bits into named constants (present, write, user, reserved, fetch) in the fault path — no behaviour change. Proof: build clean; baseline boot log unchanged in behaviour.
- RK-204 — Q-D1 DECISION, in writing: map-in-handler vs park-and-map-in-scheduler, decided against the tree's own rule ("interrupts never allocate", mem.rs) and recorded in the plan with the reason and the rejected option's cost. Proof: decision section committed; Pax approves on the bus before RK-205.
- RK-205 — Implement the classifier: a function that takes (error code, fault address, current task) and returns DemandRetry or Fatal, implementing ALL six retry conditions from the design and nothing more. Proof: code committed; plan table maps each condition to its check.
- RK-206 — Wire the classifier into the fault path behind a boot flag, default OFF (all faults fatal, today's behaviour). Proof: flag-off boot log identical in behaviour to RK-202 baseline.
- RK-207 — Implement the promised-region registry: per-task list of (base, len) regions, populated only by the loader path (API in memory.rs/mem.rs — state which). Proof: code committed; a serial dump of an empty registry for a normal task in a test boot.
- RK-208 — Loader registration for the demand program's region only: exactly one program gets a promised region in this build. Proof: boot log line `demand: region registered task <id> base <addr> len <n>` for that task and no other.
- RK-209 — Zero-fill backing: allocate a frame, zero it, map it into the faulting task's OWN page-table root (per Q-D1's mechanism). Proof: code committed; the map target root is the faulting task's — stated in the commit and the plan.
- RK-210 — Guard 1: allocation or mapping failure while servicing a demand fault is FATAL (kill the task, print `demand: allocfail fatal`), never a retry. Proof: code committed; the fatal path's serial string greps.
- RK-211 — Guard 2: after mapping, verify the entry is present in the task's tables before the retry iret; if not present, fatal with `demand: mapverify fatal`. Proof: code committed; verification step visible in the fault path.
- RK-212 — Success serial contract: each serviced demand fault prints `demand: filled task <id> addr <addr>` (rate-limited or first-N only — state the choice). Proof: string greps; choice stated in the plan.
- RK-213 — Flag ON, first live trial: the demand program touches its promised region; the fault is serviced and the program continues. Proof: boot log shows `demand: filled …` followed by the program's own success line.
- RK-214 — Data correctness: the demand program reads back the filled page and verifies all zeros, printing `demand: zeros ok`. Proof: line in the RK-213 log (or its own log if split).
- RK-215 — Write-after-fill: the program writes a pattern to the filled page, reads it back, prints `demand: rw ok`. Proof: line in the boot log.
- RK-216 — Second touch of the same page: no second fault (page stays mapped). Proof: `demand: filled` count for that address is exactly 1 in the log.
- RK-217 — Two pages: the program touches a second page in the region; a second, distinct fill occurs. Proof: two `demand: filled` lines with different addresses.
- RK-218 — Region-end behaviour: touching the last byte of the promised region fills its page; touching one byte past it does NOT (that's S11's negative, staged here as a log marker). Proof: log shows the in-region fill; the past-end touch is deferred to RK-232 with a plan note.
- RK-219 — Concurrency honesty: state in the plan what happens if two tasks fault demand-style in the same tick window, given the registry is per-task and only one program has a region. Proof: plan statement; no other task can register (RK-207 API is loader-only — cite the call sites).
- RK-220 — Flag-off regression: full gate with K3 code present, flag off. Proof: `os-build/logs/RK220-gate.txt` GREEN 7/7.
- RK-221 — Flag-on regression: full gate with flag on (fleet unchanged except the demand program). Proof: `os-build/logs/RK221-gate.txt` GREEN 7/7 plus the demand lines.
- RK-222 — Milo gate-1 request post for the S9 tip. Proof: Milo's verdict from his own bus message.
- RK-223 — Fix gate-1 findings from RK-222 as separate commits. Proof: new tip; Milo re-gates.
- RK-224 — Doc: K3 section in the plan — classifier table, registry API, serial contract, guard strings. Proof: doc commit; every quoted string greps in the code.
- RK-225 — Close S9 in `os-build/ROWAN_500_STATUS.md` (RK-201..RK-225). Proof: status committed; Pax reads RK-213/RK-221 before merge.

## S10 — K3 promised regions & the demand program (branch: rowan/k3-demand-paging)

- RK-226 — Write the demand program (`demand` userspace program): touches its promised region in the RK-213..218 sequence and prints each check's result line. Proof: program source committed; its output strings listed in the plan.
- RK-227 — Loader descriptor for `demand`: the promised region declared in its load metadata (base/len as loaded), not hard-coded in the program. Proof: descriptor committed; changing the len in metadata changes the registered region in the RK-208 log line.
- RK-228 — Fleet integration: `demand` joins the boot fleet as an additional program; the original three programs are untouched. Proof: `ps` in a boot log lists the fleet including demand.
- RK-229 — Boot-order statement: where `demand` starts in the sequence and why (after the memory subsystem is up), written in the plan. Proof: plan statement; boot log ordering matches.
- RK-230 — Full demand run in one boot: registered → filled → zeros ok → rw ok → clean exit. Proof: single boot log with all five lines in order.
- RK-231 — Exit cleanliness: after `demand` exits, its frames are freed per the existing task-teardown path (no special-casing). Proof: `mem` before/after in the same log shows frames returned (or the plan honestly states teardown behaviour as-is).
- RK-232 — Past-end touch, staged as the program's final act in a DEDICATED negative boot (not the happy boot): touch one byte past the region. Proof: log shows the fatal path (task killed), shell alive after — full treatment in S11.
- RK-233 — Region-size edge: shrink the promised region to exactly one page via metadata and re-run the happy path. Proof: boot log, fills = 1.
- RK-234 — Region-size edge 2: grow the region to eight pages; the program touches pages 1 and 8 only; exactly 2 fills. Proof: boot log with exactly two `demand: filled` lines.
- RK-235 — Unaligned start: the program's first touch is at region base + 37 bytes; the containing page fills. Proof: log's filled address is the page floor of base+37.
- RK-236 — Write-fault first touch: the program's first touch of a fresh page is a WRITE (not a read); the fill still succeeds (class boundary is about present/user/fetch bits, not read-vs-write — confirm against the design). Proof: boot log line sequence; plan cites the design clause.
- RK-237 — Registry dump command or boot print: list every task's promised regions once at shell start for observability. Proof: dump in a boot log shows exactly one non-empty registry (demand's).
- RK-238 — No-region task fault unchanged: a normal program's wild pointer still kills it exactly as before K3. Proof: boot log with the crasher behaving identically to the pre-K3 baseline.
- RK-239 — Demand + crasher same boot: the crasher dies while demand's fills still work (isolation between the paths). Proof: single boot log with both stories in order.
- RK-240 — Demand program determinism: run the happy boot ×3; identical line sequence every time (ticks excepted). Proof: three logs committed.
- RK-241 — Stress the fill path: region of 32 pages, program touches all 32 sequentially; 32 fills, then rw-verify a sample. Proof: boot log; fill count stated in the status file.
- RK-242 — Frame-pressure honesty: state in the plan what happens when the frame allocator runs dry mid-region (guard 1 fatal) and whether RK-241 can reach it. Proof: plan statement with the allocator's real numbers.
- RK-243 — Gate rerun, K3 flag on, full fleet. Proof: `os-build/logs/RK243-gate.txt` GREEN 7/7 + demand lines.
- RK-244 — Milo gate-1 request post for the S10 tip. Proof: Milo's verdict from his own bus message.
- RK-245 — Fix gate-1 findings from RK-244 as separate commits. Proof: new tip; Milo re-gates.
- RK-246 — Doc: demand-program section in the plan (descriptor format, output contract, size edges). Proof: doc commit; strings grep.
- RK-247 — Screendump/log pack for S10 close: happy boot, one-page boot, 32-page boot. Proof: three named logs committed together.
- RK-248 — Remove any debug prints added during S9–S10 that are not in the documented serial contract. Proof: happy-boot log diff shows only contract lines.
- RK-249 — K3 Mac gate pack assembly (with S11): assemble the exact §7-style pack — demand leg, crasher containment, outside-region negative, one boot. Proof: pack checklist committed; executed in RK-258.
- RK-250 — Close S10 in `os-build/ROWAN_500_STATUS.md` (RK-226..RK-250). Proof: status committed; Pax reads RK-230/RK-243 before merge.


## S11 — K3 negative tests & hardening (branch: rowan/k3-demand-paging)

- RK-251 — Negative 1 (outside region): a task with NO promised region touches an unmapped page → fatal, killed, shell alive. Proof: boot log with the kill and a post-kill `status` answer.
- RK-252 — Negative 2 (past-end): the demand program touches one byte past its region → fatal, not filled. Proof: boot log shows NO `demand: filled` for that address, kill line present.
- RK-253 — Negative 3 (kernel-space address): a ring-3 task faults on a supervisor-only address (user bit clear in the error code) → fatal per class boundary. Proof: boot log; plan cites the user-bit condition.
- RK-254 — Negative 4 (instruction fetch): a task jumps into its promised region and tries to EXECUTE from a not-present page → fatal (fetch bit set), not filled. Proof: boot log; plan cites the fetch condition.
- RK-255 — Negative 5 (already-present): a fault with the present bit set (protection fault) inside the region → fatal, never "filled". Proof: boot log or, if a protection fault cannot be staged with current programs, the plan states that honestly and the classifier unit evidence (RK-259) covers it.
- RK-256 — Anti-loop proof 1: a task that faults again at the SAME address immediately after a fill (staged via a program that unmaps or corrupts — or, if unstageable, via the mapverify guard path) terminates fatally instead of looping. Proof: boot log shows bounded faults (exact count stated), then the kill.
- RK-257 — Anti-loop proof 2: guard-2's verify step — corrupt-map staging or code-level argument that a non-present verify cannot iret back into the fault. Proof: log if stageable, else a plan section walking the code path line by line (labelled code-inspected).
- RK-258 — THE K3 GATE PACK BOOT: one boot containing the demand leg (happy path), crasher containment, and the outside-region negative, in that order. Proof: single committed boot log with all three stories; panic count 0.
- RK-259 — Classifier truth table: a table in the plan of all six conditions × pass/fail → verdict, with each row tied to a log line (RK-213..218, RK-251..255) or marked code-inspected. Proof: table committed; no row unaccounted.
- RK-260 — Reserved-bit fault: stage or analyse a reserved-bit-violation fault (RSVD set) → fatal per class boundary. Proof: log if stageable, else code-inspected plan section (labelled).
- RK-261 — Nested fault safety: a fault inside the demand-fault handler itself leads to the kernel's existing double-fault path, not silent corruption — walk and document. Proof: plan section with the handler's interrupt-state facts (labelled code-inspected unless a staging exists).
- RK-262 — Fill accounting: the kernel counts fills per task and total; the counts are readable via `mem` or a boot print. Proof: log showing counts matching the fills performed in that boot.
- RK-263 — Zero-page guarantee re-check after scheduler churn: run demand AFTER the crasher and a shell command have run (order shuffled vs RK-258). Proof: boot log, zeros still ok.
- RK-264 — Concurrent-shell check: while demand is mid-region (multi-page run), the shell still answers on its input path. Proof: boot log interleaving stated honestly (cooperative scheduling facts cited).
- RK-265 — Long-run: demand 32-page run ×5 in one boot; fills total 160; no degradation. Proof: boot log summary lines.
- RK-266 — Allocator state after negatives: after all negative kills, `mem` shows no leaked frames beyond teardown's documented behaviour. Proof: before/after numbers in one log, differences explained in the plan.
- RK-267 — Gate rerun on the hardened K3 tip. Proof: `os-build/logs/RK267-gate.txt` GREEN 7/7.
- RK-268 — Milo gate-1 request post for the full K3 branch (S9–S11) at its exact tip. Proof: Milo's verdict from his own bus message.
- RK-269 — Fix gate-1 findings from RK-268 as separate commits. Proof: new tip; Milo re-gates; RK-258 pack re-run if the fix touches the fault path (stated yes/no).
- RK-270 — K3 final doc: `os-build/K3_DEMAND_PAGING.md` — as-built truth: classifier, registry, program, guards, negative results, what is NOT built (no CoW, no swap, no mmap, no file backing). Proof: doc commit; NOT-list present and accurate.
- RK-271 — Q-D1 retrospective in the final doc: did the RK-204 choice hold up; what it cost. Proof: section present, tied to code facts.
- RK-272 — Remove the K3 boot flag or make it the documented default-on — Pax decision input only (input note; Pax rules; no default changed by this task). Proof: note in the final doc.
- RK-273 — Update LAYERS.md's L2/L3 status lines for demand paging (as-built wording, Pax reviews before merge). Proof: doc diff in the K3 branch; claims match RK-258.
- RK-274 — Screendump of the K3 gate boot's shell after all stories complete. Proof: one capture committed beside RK-258's log.
- RK-275 — Close S11 in `os-build/ROWAN_500_STATUS.md` (RK-251..RK-275); K3 marked done only when Pax has read RK-258. Proof: status committed with the pack SHA.

## S12 — K4 IPC: mailbox core (branch: rowan/k4-ipc)

- RK-276 — Re-read the K4 design (@0f5b557) and Pax's K4 review (LANDED: `os-build/K4_REVIEW_PAX.md` @6e9a9a5, APPROVE WITH CHANGES, numbers 6/7 assigned); write `os-build/K4_BUILD_PLAN.md` mapping design → code, and listing every review condition as a build checkbox — including the review's 4 required changes: (1) design §6 peer-id discovery fixed and stated (fixed spawn-order ids from the gate build's loader table; `getpid` returns the caller's OWN id and cannot discover a peer's), (2) design §4 mailbox-squatting limitation named (any live task can occupy any task's single mailbox slot, no sender filtering in step 1; its revisit is assigned to the blocking-receive step), (3) mailbox clearing on EVERY removal path, not just exit — the fault-isolation kill path included (built at RK-293), (4) design §7 literal gate log lines pinned in advance for send, receive, and each refusal (full box, dead destination, unmapped buffer, undersized buffer, empty receive) before any gate run (pinned at RK-303) — plus the Q-I1 ruling carried as a checkbox: MAX_TASKS stays 8, demo programs are swapped, the table is never grown. Proof: plan committed with the four changes and the Q-I1 ruling as checkboxes; S12 code tasks proceed on those terms (review gate satisfied-with-changes, not pending).
- RK-277 — Mailbox state: one slot per task pair endpoint as the design specifies (1 message), stored kernel-side; write the state struct with empty/full as an explicit state, not a sentinel message. Proof: struct committed; plan names the states.
- RK-278 — Message representation: fixed-size message buffer as designed (state the size from the design; if the design leaves it open, propose the size in the plan for Pax's okay before coding it). Proof: size stated in the plan with its source (design section or Pax okay on the bus).
- RK-279 — Send semantics (kernel side): copy-in from the sender's userspace buffer; full mailbox → immediate non-blocking error return, never a sleep. Proof: code committed; the error value named in the plan.
- RK-280 — Recv semantics (kernel side): copy-out to the receiver's buffer; empty mailbox → immediate non-blocking error return. Proof: code committed; the error value named in the plan.
- RK-281 — Endpoint addressing: sender/receiver identified by task id as the design specifies; sending to a nonexistent task id returns the designed error. Proof: code committed; error named.
- RK-282 — Dead-peer behaviour: sending to an exited task, and receiving from a mailbox whose sender exited — behaviour per design; if the design is silent, stop and write the gap into the plan for Pax (do not invent semantics). Proof: plan entry either way.
- RK-283 — Copy safety: copy-in/copy-out validate the userspace pointer against the CALLER's own mappings (a task can only send from / receive into its own memory). Proof: code committed; validation call sites cited in the plan.
- RK-284 — No allocation on the IPC hot path: mailbox storage is static/per-task preallocated; state the truth in the plan. Proof: plan statement tied to the struct's storage.
- RK-285 — Serial contract (debug, gated): `ipc: send <from>-><to> len <n>` / `ipc: recv <task> len <n>` behind a boot flag, default off. Proof: strings grep; flag behaviour stated.
- RK-286 — Kernel-internal unit exercise: a boot-time self-test (flag-gated) that sends a message between two kernel-side endpoints and verifies the bytes. Proof: boot log line `ipc: selftest ok` with the flag on; absent with it off.
- RK-287 — Self-test negative: self-test also exercises full-mailbox and empty-recv error returns. Proof: log lines for both error cases, named in the plan.
- RK-288 — Mailbox isolation: task A's mailbox contents are never visible to task C (addressing is exact-id, no broadcast, no peek). Proof: plan argument from the addressing code + RK-286-style exercise with three endpoints if stageable, else labelled code-inspected.
- RK-289 — Message integrity: bytes received equal bytes sent for a full-size message (pattern fill). Proof: self-test or program log line `ipc: pattern ok`.
- RK-290 — Zero-length message behaviour: per design (legal or error) — implement and document whichever the design says; if silent, Pax gap note like RK-282. Proof: plan entry + code behaviour matches it.
- RK-291 — Oversize message behaviour: length beyond the buffer → designed error, no truncation-with-success. Proof: self-test log line or code-inspected plan note (labelled).
- RK-292 — Scheduler interaction: send/recv never block, so no scheduler state changes; confirm no sleep/wake paths are touched by the IPC code. Proof: diff of sched.rs is empty for S12, or any touch is flagged and justified in the plan.
- RK-293 — Mailbox clearing on EVERY removal path (K4 review change 3): on task exit AND on the fault-isolation kill path, the task's mailbox is cleared/invalidated so a recycled task id cannot inherit stale messages and no message lingers under a dead id. Proof: code committed for both paths; plan walks the exit path and the kill path (tasks.rs) line by line.
- RK-294 — Gate rerun with IPC core present but ABI not yet exposed (S13 pending): fleet behaviour unchanged. Proof: `os-build/logs/RK294-gate.txt` GREEN 7/7.
- RK-295 — Milo gate-1 request post for the S12 tip. Proof: Milo's verdict from his own bus message.
- RK-296 — Fix gate-1 findings from RK-295 as separate commits. Proof: new tip; Milo re-gates.
- RK-297 — Doc: mailbox core section in the K4 build plan (states, errors, cleanup, serial contract). Proof: doc commit; error names match the code.
- RK-298 — Design-conformance checklist: every K4 design claim mapped to built / deferred-to-S13 / gap-noted. Proof: checklist in the plan; no claim silently dropped.
- RK-299 — Pax review-condition sweep: every condition from RK-276's checkboxes closed or explicitly carried into S13 with a note. Proof: updated checkboxes in the plan.
- RK-300 — Close S12 in `os-build/ROWAN_500_STATUS.md` (RK-276..RK-300). Proof: status committed; Pax reads RK-286/RK-294 before merge.


## S13 — K4 IPC: user.rs ABI & talker/listener acceptance (branch: rowan/k4-ipc)

- RK-301 — Add syscall 6 (ipc_send) to the INLINE dispatch in `kernel/src/user.rs` only; `syscalls.rs` is not touched (its diff for the whole K4 branch stays empty). Proof: branch diff for syscalls.rs is empty; dispatch entry greps in user.rs.
- RK-302 — Add syscall 7 (ipc_recv) to the same inline dispatch, same rule. Proof: same diff check; both numbers now resolve in user.rs.
- RK-303 — Argument contract for 6/7 written into the K4 build plan BEFORE the handlers land: register meanings, length field, return values (success length / each error as a negative or sentinel — as the design states) — AND the literal gate log lines pinned in advance (K4 review change 4): the exact strings the gate boot must show for a send, a receive, and each refusal reason (full box, dead destination, unmapped buffer, undersized buffer, empty receive), so the Mac boot log is checkable line by line. Proof: contract section committed with the pinned lines verbatim; Pax reads it.
- RK-304 — ipc_send handler: marshal arguments → S12 send semantics → return value. Proof: code committed; handler is a thin marshal over the S12 core (cited in the plan).
- RK-305 — ipc_recv handler: same pattern. Proof: code committed.
- RK-306 — Unknown-number behaviour preserved: numbers other than the implemented set (including 99) still refuse exactly as before. Proof: boot log with 99 refused on the K4 tip.
- RK-307 — Reserved-number honesty: numbers 8–15 remain unimplemented refusals; the plan lists 5 (read_key), 6, 7 as the only live numbers and 8–15 as reserved. Proof: plan table; a boot log spot-check of number 8 refusing.
- RK-308 — `talker` userspace program: sends a designed greeting message to `listener`'s task id, prints `talker: sent`. Proof: program source committed; boot log line.
- RK-309 — `listener` userspace program: polls recv (non-blocking, bounded retries per the design), prints the received bytes as `listener: got <text>`. Proof: program source committed; boot log line.
- RK-310 — End-to-end boot: talker + listener in the fleet; the greeting crosses. Proof: single boot log with `talker: sent` before `listener: got …` and the text intact.
- RK-311 — Empty-recv behaviour in userspace: listener's first poll before talker sends returns the empty error and listener carries on (no crash, no hang). Proof: boot log ordering shows a poll-miss line or the plan's stated observable.
- RK-312 — Full-mailbox behaviour in userspace: talker sends twice without a recv; the second send returns the full error and talker prints it. Proof: boot log with the error line.
- RK-313 — Wrong-peer: a third program attempts to recv from listener's endpoint / send as another id (as the addressing allows staging) and is refused per RK-288. Proof: boot log refusal line, or plan marked code-inspected with the staging limit stated.
- RK-314 — Buffy pair acceptance, staged: hand Buffy the exact boot artifact + the talker/listener contract so her pair can run against this kernel (her acceptance test closes gap R11-273). Proof: handoff note committed in the plan with artifact names; Buffy's own bus report is the acceptance record.
- RK-315 — Buffy pair acceptance, result: record Buffy's verdict in the plan verbatim (pass/fail + her log reference). Proof: plan updated; if she fails it, the failure is quoted, not paraphrased away.
- RK-316 — Fix any acceptance failure as its own commit and re-run RK-310 + the Buffy artifact. Proof: new tip + new logs.
- RK-317 — IPC + fault isolation: a task that sends from an unmapped pointer is killed by the existing fault path, kernel alive, peer unaffected. Proof: boot log with the kill and the listener still answering after.
- RK-318 — IPC + exit: talker exits after sending; listener still recvs the queued message (or the design's RK-282 semantics — whichever was decided, the log must match the plan). Proof: boot log vs plan statement compared in the status file.
- RK-319 — Round-trip: listener replies via ipc_send to talker-id-shaped endpoint per the design (ping-pong, one round). Proof: boot log with both directions.
- RK-320 — Ten-message sequence with recv interleaved: contents verified in order. Proof: boot log with a sequence-ok line from the receiving program.
- RK-321 — Gate rerun on the full K4 tip: text gate intact, IPC programs in the fleet. Proof: `os-build/logs/RK321-gate.txt` GREEN 7/7 + IPC lines.
- RK-322 — Milo gate-1 request post for the full K4 branch (S12–S13) at its exact tip. Proof: Milo's verdict from his own bus message.
- RK-323 — Fix gate-1 findings from RK-322 as separate commits; re-run RK-310 if a handler changed. Proof: new tip; Milo re-gates; log presence stated.
- RK-324 — K4 final doc: `os-build/K4_IPC.md` — as-built truth: numbers 6/7, contract, errors, mailbox rules, acceptance result, NOT-list (no blocking, no broadcast, no shared memory — unless the design said otherwise). Proof: doc commit; NOT-list present.
- RK-325 — Close S13 in `os-build/ROWAN_500_STATUS.md` (RK-301..RK-325); K4 marked done only with Pax's read of RK-310/RK-321 plus Buffy's RK-315 verdict on record. Proof: status committed with all three references.

## S14 — PS/2 keyboard depth (branch: rowan/keyboard-depth)

- RK-326 — Document the current readkey path end to end (IRQ → buffer → syscall 5 → program) from interrupts.rs, user.rs, and the readkey program, in `os-build/drivers/KEYBOARD.md`. Proof: doc committed; every step cites a file/function.
- RK-327 — Scancode set inventory: which set the controller is in, how the code knows, and what the decode table covers today. Proof: doc section with the table's actual coverage counted.
- RK-328 — Modifier state: shift handling verified for the full letter row set (a–z shifted/unshifted) via a scripted input boot. Proof: boot log with both cases per a sampled subset + the method stated.
- RK-329 — Caps lock: implement or explicitly document as unimplemented with the observable behaviour today. Proof: doc line + boot log if implemented.
- RK-330 — Number row + symbols: decode coverage for the number row, both shift states, listed char by char against the table. Proof: table in the doc; gaps named.
- RK-331 — Special keys inventory: enter, backspace, tab, space, escape — each one's current behaviour in the shell and in readkey. Proof: doc table; boot log lines for enter/backspace (already proven paths cited).
- RK-332 — Backspace in the shell input line: erase semantics verified at line start (no underflow, no garbage char). Proof: boot log of a typed-and-corrected command answering correctly.
- RK-333 — Key release handling: confirm make/break filtering (a held key does not inject break codes as characters). Proof: boot log from a held-key staging, or doc marked code-inspected with the filter cited.
- RK-334 — Typematic repeat: state today's behaviour (controller repeat passes through or not) from evidence. Proof: boot log timing or doc statement with the staging described.
- RK-335 — Buffer depth: the keyboard ring buffer's size, and overflow behaviour (drop-new, drop-old, or block) — from the code, stated plainly. Proof: doc entry with the size constant cited.
- RK-336 — Overflow staging: feed more keys than the buffer holds before a read; observe and record the RK-335 behaviour live. Proof: boot log; observed matches documented (or doc corrected).
- RK-337 — Non-US layout honesty: doc states the table is US-layout only (or what it actually is) — no silent assumptions. Proof: doc line.
- RK-338 — Unknown scancode: an unmapped key produces no character and no panic. Proof: boot log staging (e.g. an F-key) with the shell answering after.
- RK-339 — Controller init sequence documented: reset, defaults, scan enable — as the code actually does it at boot. Proof: doc section citing the init code.
- RK-340 — IRQ sharing/ordering note: keyboard IRQ vs timer IRQ handling order as interrupts.rs implements it. Proof: doc section with citations.
- RK-341 — Readkey edge: read_key with no key pending returns per its contract (blocking/non-blocking as built) — verify and document. Proof: boot log or doc citation of the proven combined-tree behaviour.
- RK-342 — Multiple readers: two programs calling read_key — who gets the key, per the current design; document, do not redesign. Proof: doc statement; staging log if the fleet allows.
- RK-343 — Fix any decode-table gap found in RK-330 that the shell needs (one commit per gap class). Proof: boot log showing the fixed characters typed correctly.
- RK-344 — Gate rerun on the S14 tip. Proof: `os-build/logs/RK344-gate.txt` GREEN 7/7 including the readkey line got=3.
- RK-345 — Milo gate-1 request post for the S14 tip. Proof: Milo's verdict from his own bus message.
- RK-346 — Fix gate-1 findings from RK-345 as separate commits. Proof: new tip; Milo re-gates.
- RK-347 — Doc close: KEYBOARD.md final (coverage tables, buffer, modifiers, known gaps list). Proof: doc commit; gaps list present.
- RK-348 — Regression: the attract screen still exits on any key (S6-era behaviour) with the deepened driver. Proof: boot log line sequence.
- RK-349 — Regression: shell line editing (backspace/shift) works in one combined staging boot. Proof: boot log with a corrected, shifted command answering.
- RK-350 — Close S14 in `os-build/ROWAN_500_STATUS.md` (RK-326..RK-350). Proof: status committed; Pax reads KEYBOARD.md's gaps list before merge.


## S15 — PS/2 mouse & pointer, KF-12/KF-13 sub-steps (branch: rowan/mouse-pointer)

- RK-351 — Mouse feasibility note: PS/2 auxiliary port state on the current boot path — what the controller config byte says today, from the code. Proof: note in `os-build/drivers/MOUSE.md`; citation, not a guess.
- RK-352 — Enable the auxiliary device in controller init (keyboard path untouched, its init order preserved). Proof: boot log shows keyboard readkey still working in the same boot as the mouse enable.
- RK-353 — Mouse reset + ID read: send the reset, capture the device ID bytes on serial (`mouse: id <n>`). Proof: line in a boot log.
- RK-354 — Enable data reporting on the mouse. Proof: serial line `mouse: reporting on` in a boot log.
- RK-355 — Packet assembly: implement the 3-byte packet state machine (sync bit discipline: a byte without the sync pattern in position 0 is dropped, not misaligned forever). Proof: code committed; state machine described in MOUSE.md.
- RK-356 — Packet decode: buttons (L/R/M), sign bits, overflow bits → a MouseEvent struct. Proof: struct committed; decode table in MOUSE.md.
- RK-357 — Serial packet log (flag-gated): print decoded movement for the first N packets (`mouse: dx <n> dy <n> btn <bits>`). Proof: boot log with real movement lines from a QEMU mouse move on the Mac lane.
- RK-358 — Cursor state: x/y position state in the kernel, clamped to the framebuffer bounds. Proof: code committed; clamp rule in MOUSE.md.
- RK-359 — Draw the cursor: a defined cursor glyph (arrow or cross — state the shape) drawn at the cursor position on the framebuffer. Proof: screendump `os-build/captures/rk359-cursor.png`.
- RK-360 — Move the cursor: screendump pair with the cursor at two positions after QEMU mouse movement. Proof: `os-build/captures/rk360-cursor-a.png` + `rk360-cursor-b.png`; positions differ.
- RK-361 — Clean movement: the cursor erases/redraws its background correctly (no trail of stale cursors). Proof: RK-360 pair shows no trail; if a trail exists, it is a named defect, not hidden.
- RK-362 — IRQ path: mouse packets arrive on their IRQ without disturbing keyboard IRQ handling in the same boot. Proof: one boot log containing both readkey success and mouse packet lines.
- RK-363 — Button events: left-button down/up decoded into events with a serial line (flag-gated). Proof: boot log lines from a QEMU click.
- RK-364 — Click delivery to the window layer: a click inside a window's bounds is reported with the window id (single-window case first). Proof: serial line `mouse: click win <id>` from a staged click, or the staging limit stated honestly (QEMU click targeting) with the log that exists.
- RK-365 — Focus on click (KF-13): with the S7 two-window skeleton present, clicking the unfocused window raises/focuses it (title-bar colour swap per RK-178). Proof: screendump pair before/after the click, focus visibly switched.
- RK-366 — Click outside any window: no focus change, no panic, event dropped or desktop-noted per a written rule. Proof: rule in MOUSE.md; log or screendump evidence.
- RK-367 — Movement bounds at all four edges: cursor stops at each edge, no wrap, no negative coordinates. Proof: serial cursor-position lines at the four extremes from staged moves.
- RK-368 — Overflow packets: a movement packet with overflow bits set is dropped/clamped per a written rule, cursor does not teleport. Proof: rule in MOUSE.md; staging result or code-inspected label.
- RK-369 — Mouse absent: boot with no PS/2 mouse (QEMU config) → kernel boots normally, `mouse: absent` on serial, keyboard + face unaffected. Proof: boot log with the absent line and a working shell.
- RK-370 — Flag-off purity: with the face off, the mouse init does not change text-boot behaviour or timing claims. Proof: flag-off gate log GREEN 7/7.
- RK-371 — Gate rerun on the S15 tip (face on). Proof: `os-build/logs/RK371-gate.txt` GREEN 7/7.
- RK-372 — Milo gate-1 request post for the S15 tip. Proof: Milo's verdict from his own bus message.
- RK-373 — Fix gate-1 findings from RK-372 as separate commits. Proof: new tip; Milo re-gates.
- RK-374 — Doc close: MOUSE.md final (init, packet format, events, bounds, absent behaviour, known limits). Proof: doc commit; limits list present.
- RK-375 — Close S15 in `os-build/ROWAN_500_STATUS.md` (RK-351..RK-375). Proof: status committed; Pax reads RK-360/RK-365 evidence before merge.

## S16 — Serial, timer & VGA text hardening (branch: rowan/console-hardening)

- RK-376 — Serial port doc: `os-build/drivers/SERIAL.md` — port base, baud/divisor as configured, who writes (panic path, print macros, logs) as the code does it. Proof: doc committed with citations.
- RK-377 — Serial write discipline: confirm the print path cannot interleave mid-line from two tasks (locking as implemented), and document the truth. Proof: doc statement tied to the lock's code location.
- RK-378 — Serial stress: a boot where three programs print concurrently; lines in the log are whole or the interleaving is shown and named. Proof: boot log committed; the result stated either way, not hidden.
- RK-379 — Timer doc: `os-build/drivers/TIMER.md` — PIT/APIC choice as built, frequency constant, tick source for uptime and the scheduler. Proof: doc committed with the constants cited.
- RK-380 — Tick accuracy check: compare kernel uptime over a QEMU run against wall-clock of the Mac lane run (state the method and the drift honestly). Proof: numbers in TIMER.md; method stated.
- RK-381 — Scheduler quantum: document the preemption/quantum behaviour sched.rs actually implements (ticks per slice, or cooperative facts). Proof: doc section with citations — no aspirational claims.
- RK-382 — Sleep primitive audit: does a task sleep/wait primitive exist today? Document what exists (or its absence) as input to S18 — audit only, no new code. Proof: audit section committed.
- RK-383 — VGA text doc: `os-build/drivers/VGA.md` — the vga.rs writer (222 lines): buffer address, colour model, newline/scroll behaviour as built. Proof: doc committed with citations.
- RK-384 — VGA scroll correctness: fill the screen past the last row in a staging boot; the scroll loses exactly the top line(s) per the implementation's rule. Proof: screendump pair or serial-mirrored evidence; rule stated in VGA.md.
- RK-385 — VGA colour pairs: the shell's use of colour (banner vs body) inventoried against vga.rs's palette support. Proof: inventory in VGA.md.
- RK-386 — Panic output path: a forced panic prints on BOTH serial and VGA (or whichever it actually does — document the truth). Proof: forced-panic boot log + screendump if VGA carries it.
- RK-387 — Panic does not hang the logger: the panic print path cannot deadlock on the print lock held by the faulting context — walk the code, document. Proof: doc section (code-inspected label) or the RK-386 staging evidence.
- RK-388 — Double-fault visibility: what a double fault prints today before the machine stops (ties to traps.rs). Proof: doc entry; staging only if an existing mechanism allows it without new risk.
- RK-389 — Early-boot serial: the first serial write happens before the banner (init marker) or the banner is first — document which, from a log. Proof: doc line citing a committed log.
- RK-390 — Log-line discipline pass: every kernel serial line in the shipping path follows the existing prefix style; list any offenders found (no mass rename without Pax's okay). Proof: offender list in SERIAL.md (may be "none").
- RK-391 — Remove or flag-gate any leftover debug prints in interrupts/traps paths. Proof: boot log diff shows only contract lines.
- RK-392 — Interrupt latency note: timer IRQ handler work is bounded (what it does per tick, from the code). Proof: TIMER.md section with citations.
- RK-393 — Spurious IRQ handling: document what happens on an unhandled IRQ line today. Proof: doc entry with citations.
- RK-394 — Gate rerun on the S16 tip. Proof: `os-build/logs/RK394-gate.txt` GREEN 7/7.
- RK-395 — Milo gate-1 request post for the S16 tip. Proof: Milo's verdict from his own bus message.
- RK-396 — Fix gate-1 findings from RK-395 as separate commits. Proof: new tip; Milo re-gates.
- RK-397 — Doc pack review: SERIAL.md, TIMER.md, VGA.md cross-checked against the code by a fresh read (Rowan re-reads his own docs against the tree). Proof: correction commits or a "verified" note per doc in the status file.
- RK-398 — Regression: readkey + attract + shell in one boot on the hardened console. Proof: boot log with all three.
- RK-399 — Regression: the fetch screen still renders correctly after hardening. Proof: boot log fetch section quoted in the status file.
- RK-400 — Close S16 in `os-build/ROWAN_500_STATUS.md` (RK-376..RK-400). Proof: status committed; Pax reads the three driver docs before merge.


## S17 — Memory: allocator, page tables, heap growth (branch: rowan/memory-depth)

- RK-401 — Memory subsystem map: `os-build/MEMORY_MAP.md` — boot memory map parsing (memory.rs), the bitmap FrameAllocator, the 4-level tables, per-task roots, the 512K kernel heap (mem.rs) — as built, with file/line citations. Proof: doc committed; Pax spot-checks three citations.
- RK-402 — Frame accounting invariants: total/used/free frame counts derivable at boot; print them once (`mem: frames total <n> used <n> free <n>`). Proof: line in a boot log; numbers consistent with `mem`'s output.
- RK-403 — Allocator exhaustion behaviour: allocate-until-dry in a staging boot (kernel-side loop or hog-style program) — the failure is a clean refusal, never a corrupt map. Proof: boot log with the refusal and the machine alive after (or the hog killed and the shell answering).
- RK-404 — Free-path correctness: free a set of frames and re-allocate; the same frames are reusable and handed out again. Proof: staging log or a boot-time self-check line (flag-gated) `mem: free-realloc ok`.
- RK-405 — Double-free honesty: what a double-free does today (bitmap already guards it, or not) — document from the code; fix only if it corrupts state, as its own flagged commit. Proof: doc entry; fix commit + staging log if it came to that.
- RK-406 — Page-table walk doc: how a virtual address resolves through the 4 levels in this kernel, and where per-task roots switch (context-switch path in sched.rs/tasks.rs). Proof: doc section with citations.
- RK-407 — Kernel-half mapping invariant: every task's tables map the kernel half identically — verify from the construction code and state it. Proof: doc section (code-inspected label) with citations.
- RK-408 — Guard page audit: stack guard pages — do task stacks have them today? Document the truth; if absent, write the gap into MEMORY_MAP.md as a named gap (building them is a separate Pax call). Proof: gap entry or citation of the guard setup.
- RK-409 — Heap growth decision input: the 512K heap's current headroom (measure peak usage across the gate boot) and a grow/no-grow recommendation with numbers. Proof: measurement in the doc; recommendation is input only — Pax rules on any change.
- RK-410 — Heap pressure staging: if a measurement hook exists, drive heap usage high and record allocator behaviour at the edge. Proof: staging log, or the doc states why it cannot be staged today.
- RK-411 — Fragmentation note: bitmap allocation is first-fit/contiguous as implemented — document the actual policy and its consequence for large contiguous requests. Proof: doc section with citations.
- RK-412 — Largest contiguous block: report the largest free contiguous frame run at shell time (`mem` extension or boot print). Proof: line in a boot log.
- RK-413 — Region parsing edge: a boot memory-map entry of an unusual type (reserved/ACPI) is classified correctly per memory.rs's rules — walk one real QEMU map entry through the code in the doc. Proof: worked example in MEMORY_MAP.md from a committed boot log's map.
- RK-414 — Zero-frame guarantee: freshly allocated frames handed to userspace are zeroed or explicitly NOT zeroed — document the truth (K3's fill zeroes; the general path is stated as-is). Proof: doc entry with citations.
- RK-415 — K3 interplay check: demand fills draw from the same allocator; RK-241's 32-page run's frame counts reconcile with RK-402's accounting. Proof: reconciliation note in the doc using both logs.
- RK-416 — Per-task footprint: frames held by one idle userspace task, measured. Proof: number in the doc from a boot log's before/after-task-start counts.
- RK-417 — Task-exit reclamation re-verified after S17 changes: spawn + exit ×10, frame count returns to baseline (± documented teardown residue). Proof: boot log with the counts.
- RK-418 — Unmap correctness: a task's exit unmaps its user pages without touching the kernel half or other tasks' roots. Proof: second task still runs after the first exits (boot log) + doc citation of the unmap path.
- RK-419 — Gate rerun on the S17 tip. Proof: `os-build/logs/RK419-gate.txt` GREEN 7/7.
- RK-420 — Milo gate-1 request post for the S17 tip. Proof: Milo's verdict from his own bus message.
- RK-421 — Fix gate-1 findings from RK-420 as separate commits. Proof: new tip; Milo re-gates.
- RK-422 — Doc close: MEMORY_MAP.md final, including the named gaps list (guard pages, heap decision state, anything found). Proof: doc commit; gaps list present.
- RK-423 — Regression: K3 happy path still green on the S17 tip (memory changes must not break demand paging). Proof: boot log with the RK-230 line sequence.
- RK-424 — Regression: hog containment (allocate-until-refusal) still ends with a live shell. Proof: boot log.
- RK-425 — Close S17 in `os-build/ROWAN_500_STATUS.md` (RK-401..RK-425). Proof: status committed; Pax reads MEMORY_MAP.md's gaps before merge.

## S18 — Scheduler & tasks: priorities, sleep, exit codes (branch: rowan/sched-depth)

- RK-426 — Scheduler as-built doc: `os-build/SCHED_MAP.md` — the policy sched.rs (748 lines) actually implements: run queue shape, switch triggers, tick role. Proof: doc committed with citations; no aspirational policy claimed.
- RK-427 — Task lifecycle doc: tasks.rs (702 lines) states — created, runnable, running, exited, killed — and every transition's trigger. Proof: state table in SCHED_MAP.md with citations.
- RK-428 — Exit codes, audit: what a task's exit currently records (code? nothing?) — document the truth. Proof: audit section committed.
- RK-429 — Exit codes, build (if RK-428 found none): the exit path records a task-supplied code, readable by the shell's `ps`/status family after exit (dead-task record, bounded count). Proof: boot log — a program exits with code 7 and the record shows 7.
- RK-430 — Exit code from a KILLED task is distinguishable from a clean exit (killed marker, not a fake code). Proof: boot log with the crasher's record vs a clean exit's record.
- RK-431 — Priorities, audit: does any priority notion exist today? Document the truth. Proof: audit section committed.
- RK-432 — Priorities, design input: a minimal two-level scheme (interactive vs batch) as a Pax decision input — design note only, no code. Proof: note in SCHED_MAP.md; Pax rules before any build.
- RK-433 — Priorities, build (only if RK-432 was approved): two-level selection in the scheduler with the ribbon/shell classed interactive. Proof: boot log showing selection order under load; approval cited in the commit.
- RK-434 — Starvation check: a CPU-hog task and the shell in one boot — the shell still answers (policy as built, with priorities if RK-433 landed). Proof: boot log with a shell answer during the hog's run, timing honestly stated.
- RK-435 — Sleep, build (per RK-382's audit): a task can sleep for N ticks via the existing syscall style (user.rs dispatch; NO new number without Pax's ruling — if a number is needed, stop and get the ruling in the plan first). Proof: plan entry for the number ruling + boot log of a program printing, sleeping, printing with tick values ≥ N apart.
- RK-436 — Sleep accuracy: measured sleep duration vs requested ticks over 3 trials. Proof: numbers in SCHED_MAP.md from the logs.
- RK-437 — Wake ordering: two sleeping tasks with different deadlines wake in deadline order. Proof: boot log line order.
- RK-438 — Yield: a voluntary yield path exists or is documented absent; if built, a spinner task yields and a peer runs. Proof: doc/log per the truth.
- RK-439 — Context-switch cost note: ticks spent per switch, measured crudely (switch counter over a fixed window) or stated unmeasured. Proof: number or honest "unmeasured" in SCHED_MAP.md.
- RK-440 — Switch counter: the kernel counts context switches, readable via `status` extension or boot print. Proof: line in a boot log, count increases between two reads.
- RK-441 — Task-count ceiling: how many tasks the current tables hold; boot behaviour at the ceiling is a clean refusal. Proof: doc number + staging log if the fleet can reach it, else code-inspected label.
- RK-442 — Spawn failure honesty: a spawn that cannot allocate (memory or table full) fails with a named error, never a half-task. Proof: doc + staging or code-inspected label.
- RK-443 — Kill path re-verified: killing the CURRENT task vs another task — both paths documented from the code (the isolation kill is the proven one). Proof: doc section with citations.
- RK-444 — Ribbon task citizenship: the S6 ribbon task under the as-built policy — its slice behaviour measured during attract. Proof: log numbers in SCHED_MAP.md.
- RK-445 — Gate rerun on the S18 tip. Proof: `os-build/logs/RK445-gate.txt` GREEN 7/7.
- RK-446 — Milo gate-1 request post for the S18 tip. Proof: Milo's verdict from his own bus message.
- RK-447 — Fix gate-1 findings from RK-446 as separate commits. Proof: new tip; Milo re-gates.
- RK-448 — Doc close: SCHED_MAP.md final (policy, lifecycle, exit codes, sleep, priorities state, ceilings). Proof: doc commit; every mechanism claimed cites code or a log.
- RK-449 — Regression: K3 + K4 programs still run under the S18 scheduler (demand fills, talker/listener exchange). Proof: one boot log with both stories.
- RK-450 — Close S18 in `os-build/ROWAN_500_STATUS.md` (RK-426..RK-450). Proof: status committed; Pax reads SCHED_MAP.md before merge.


## S19 — Userspace ABI & programs, user.rs dispatch only (branch: rowan/abi-programs)

- RK-451 — ABI reference: `os-build/ABI.md` — every live syscall number (0–7 as built), its arguments, returns, and errors, from user.rs's inline dispatch; syscalls.rs is cited only as the frozen historical table, never edited. Proof: doc committed; Pax greps two dispatch entries against it.
- RK-452 — ABI conformance boot: one program per live number exercising its happy path in a single boot (read_key excluded — keyboard staging separate, cited from S14). Proof: boot log with each program's ok line.
- RK-453 — Error-path boot: each live number called with one bad argument (bad pointer, bad length) — the result is the documented error or the caller's kill, never a kernel fault. Proof: boot log; panic count 0.
- RK-454 — Bad-pointer discipline: a userspace pointer into kernel memory passed to a write-style call is refused by validation (RK-283's pattern applied across the ABI). Proof: boot log refusal/kill per the documented contract; kernel alive.
- RK-455 — Length discipline: an over-long length on a buffer call is refused or clamped per ABI.md's stated rule — one rule, documented, enforced. Proof: boot log + doc rule match.
- RK-456 — Program: `echo2` — a userspace program that reads a line via the existing input path and prints it back through the write path (exercises two numbers end to end). Proof: program source + boot log round-trip.
- RK-457 — Program: `ticker` — prints its own tick readings at intervals using S18's sleep (or busy-wait honestly labelled if sleep was not built). Proof: program source + boot log with increasing ticks.
- RK-458 — Program: `memhog-lite` — allocates pages until refusal, prints the refusal, exits cleanly with a code (ties to RK-429). Proof: boot log; shell alive after; frames reclaimed per RK-417's behaviour.
- RK-459 — Program argument passing: document how programs receive arguments today (none, or the actual mechanism) — truth in ABI.md. Proof: doc section with citation.
- RK-460 — Program loading doc: how a program image gets into memory and into its own root (loader path), in ABI.md. Proof: doc section with citations to tasks.rs/memory.rs.
- RK-461 — Program-visible task id: a program can learn its own task id through an existing call or a documented absence — truth in ABI.md; if present, a program prints its id matching `ps`. Proof: doc + boot log if present.
- RK-462 — Exit from anywhere: a program exiting from a nested call depth tears down identically to a top-level exit. Proof: staging program + boot log (records per RK-429/430).
- RK-463 — Fault-in-library-shape: a program that faults inside a helper function (not main) is isolated identically. Proof: boot log kill + shell answer.
- RK-464 — Two instances: the same program image run as two tasks concurrently keeps separate memory (one writes its page, the other's is untouched). Proof: boot log with both checks printed.
- RK-465 — ABI versioning note: ABI.md states the numbers are append-only (a number, once live, never changes meaning) as the standing rule. Proof: rule written in ABI.md; Pax confirms on the bus.
- RK-466 — Reserved numbers 8–15: ABI.md lists them as reserved with no semantics; any proposal for one goes through Pax in writing first. Proof: section present.
- RK-467 — Program size ceiling: the largest program image the loader accepts, from the code, in ABI.md. Proof: doc number with citation.
- RK-468 — Fleet boot with all S19 programs present: nothing in the original claims regresses. Proof: gate GREEN 7/7 + the new programs' lines in the same log.
- RK-469 — Gate rerun (final S19 tip, dedicated run). Proof: `os-build/logs/RK469-gate.txt` GREEN 7/7.
- RK-470 — Milo gate-1 request post for the S19 tip. Proof: Milo's verdict from his own bus message.
- RK-471 — Fix gate-1 findings from RK-470 as separate commits. Proof: new tip; Milo re-gates.
- RK-472 — ABI.md final review pass against user.rs (fresh read, line by line). Proof: correction commits or a verified note in the status file.
- RK-473 — Program sources documented: each S19 program gets a header comment stating which ABI numbers it exercises. Proof: grep of the program sources shows the headers.
- RK-474 — Regression: readkey program (syscall 5) untouched and still proven. Proof: boot log got=3 line on the S19 tip.
- RK-475 — Close S19 in `os-build/ROWAN_500_STATUS.md` (RK-451..RK-475). Proof: status committed; Pax reads ABI.md before merge.

## S20 — Boot resilience, kernel self-tests & subsystem docs (branch: rowan/resilience-docs)

- RK-476 — Panic-path audit: every `panic!`/unwrap/expect reachable in kernel boot and runtime, inventoried by file with a reachability note. Proof: inventory in `os-build/PANIC_AUDIT.md`; counts per file.
- RK-477 — Panic output contract: on panic the kernel prints the location + message to serial and halts (or today's truth) — documented from the RK-386 evidence. Proof: PANIC_AUDIT.md section citing the forced-panic log.
- RK-478 — Boot-time self-test suite, design: a flag-gated `selftest` boot mode running kernel-internal checks (allocator, classifier, IPC core) and printing one `selftest: <name> ok/FAIL` line each. Proof: design section in PANIC_AUDIT.md or its own doc; Pax okays the scope.
- RK-479 — Self-test 1: frame allocator alloc/free/realloc cycle (productises RK-404). Proof: boot log `selftest: frames ok` in selftest mode; absent in normal mode.
- RK-480 — Self-test 2: K3 classifier truth-table spot rows (synthetic error-code/address pairs against a dummy registry). Proof: `selftest: classifier ok` line; the rows listed in the doc.
- RK-481 — Self-test 3: IPC mailbox round-trip (productises RK-286). Proof: `selftest: ipc ok` line.
- RK-482 — Self-test 4: page-table map/unmap/verify cycle on a scratch root (not the running task's). Proof: `selftest: tables ok` line.
- RK-483 — Self-test failure honesty: break one self-test deliberately on a throwaway commit; the boot reports FAIL and does NOT claim the suite passed. Proof: log of the throwaway run committed as evidence; throwaway commit never merges.
- RK-484 — Self-test mode never runs by default: normal gate boot contains zero selftest lines. Proof: gate log check written into the status file.
- RK-485 — Double-fault evidence pack: assemble the existing double-fault log evidence (K3 design-era logs) into `os-build/logs/RK485-doublefault-index.md` with what each shows. Proof: index committed; claims match the logs.
- RK-486 — Triple-fault/reset behaviour: document what the machine does on a triple fault under QEMU (reset loop) and how a reader recognises it in a log. Proof: doc section (evidence-based or labelled analysis).
- RK-487 — Watchdog honesty: no hardware watchdog exists in the current build — stated plainly in the resilience doc, not implied. Proof: statement present in PANIC_AUDIT.md.
- RK-488 — Boot-failure field guide: `os-build/BOOT_FAILURES.md` — symptom → likely layer → first log to read, for every failure mode proven or analysed in S1–S20 (bootloader break, fb absent, fallback, panic, double fault). Proof: guide committed; each entry names its evidence.
- RK-489 — Subsystem doc index: `os-build/KERNEL_DOCS.md` linking every doc this list produced (KERNEL_FACE, K3, K4, ABI, MEMORY_MAP, SCHED_MAP, drivers ×4, PANIC_AUDIT, BOOT_FAILURES) with a one-line truth status each. Proof: index committed; every link resolves to a file on main or the named branch.
- RK-490 — Doc-accuracy sweep: re-read each subsystem doc against the final code; correct drift. Proof: correction commits or per-doc verified notes in the status file.
- RK-491 — Claim audit support: assemble the kernel claim-evidence pack for Milo's audit — the claim sentence decomposed, each clause pointing at its committed log. Proof: pack file committed; Milo's audit is the record.
- RK-492 — Full-fleet endurance boot: 30-minute boot with the ribbon, shell, demand, and IPC programs all live; final status answer at the end. Proof: endurance log with first/last timestamps; panic count 0.
- RK-493 — Endurance memory check: frame counts at endurance start vs end; growth explained or named as a leak with a filed gap. Proof: numbers in the endurance log + status file note.
- RK-494 — Gate rerun on the S20 tip. Proof: `os-build/logs/RK494-gate.txt` GREEN 7/7.
- RK-495 — Selftest-mode gate: a second gate-style run in selftest mode, all `selftest:` lines ok. Proof: `os-build/logs/RK495-selftest.txt`.
- RK-496 — Milo gate-1 request post for the S20 tip. Proof: Milo's verdict from his own bus message.
- RK-497 — Fix gate-1 findings from RK-496 as separate commits. Proof: new tip; Milo re-gates; RK-495 re-run if a self-test changed.
- RK-498 — LAYERS.md final update for L1–L3: as-built status lines after all 20 sections (Pax reviews wording before merge — claims only from artifacts). Proof: doc diff; Pax sign-off on the bus.
- RK-499 — ROWAN_500 closeout report: `os-build/ROWAN_500_CLOSEOUT.md` — per-section done/partial/not-started with artifact references, and every unfinished task listed by ID with its blocker. Proof: closeout committed; no section's state claimed beyond its artifacts.
- RK-500 — Final status sweep: `os-build/ROWAN_500_STATUS.md` complete for RK-001..RK-500 (every line filled or marked blocked with a reason). Proof: status file committed; Pax verifies the count of filled lines against this list.

---

*End of list. 500 tasks, RK-001..RK-500, in 20 sections — 25 per
section except S7 (30: the window layer needed them) and S8 (20);
the close tasks RK-180 and RK-200 state the true ranges.
Every task carries its own proof; a task without its artifact is
not done, whatever the branch says.*
