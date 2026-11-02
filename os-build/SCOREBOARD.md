# Meta OS scoreboard (Milo's duty, ML-L2-03)

One entry per layer of the seven-layer scheme (`os-build/LAYERS.md`:
L1 Boot, L2 Kernel core, L3 Drivers, L4 System services, L5 Agent
runtime, L6 Shell and apps, L7 Programs). File names, task IDs, and
branch names keep the old digits as stable identifiers; only the layer
numbers in prose follow the 2026-11-01 renumber.

Rules, from the work order: the scoreboard never rounds up. A branch
claim is not an entry until the artifact is checked. Status words are
honest: DESIGNED / DRAFT / WRITTEN / GATED / MERGED / NOT STARTED, and
"standalone rustc clean" is never merged into "kernel-crate compile"
or "booted". Updated on every gate-1 verdict and every Pax merge.
Merges go through Pax only; this branch never merges itself.

v4 base: main 445daf8, verified 2026-11-01 ~17:45 EST via ls-remote
plus a local fetch plus Rowan's 17:42 API-verified pump, all three
agreeing on 445daf8. Main was moving fast during the 17:36-17:38
landing run (eb7653f -> 83ddfb2 -> a4df8cf -> be83e7e -> 445daf8);
v4 is branched off the settled tip 445daf8, not off any mid-run tip.

v5 base: main f496bdb, verified 2026-11-01 ~20:35 EST via fetch of
origin/main in this checkout (branch milo/os-gate, round-4 task doc
MILO_TASKS_ROUND4.md on main). Corrections ordered in
os-build/PAX_12H_RESPONSE.md (P-5) applied below; every number in
v5 was re-checked in this checkout, not inherited from v4.

## L1 — Boot (Rowan)

- Status: MERGED, PROVEN ON MAIN per Pax's merge verification,
  NOT BOOT-REPRODUCED HERE.
- Evidence: Pax hand-combined merge eb7653f (opencode/os-build
  sections E-Q, OS-061..240 + soak) is on main. Live kernel entry =
  OpenCode modular wiring (`kernel/src/main.rs` + gdt.rs, traps.rs,
  sched.rs, user.rs, vga.rs, mem.rs, per `kernel/r5-reference/README.md`
  on main). K1-K6 boot logs are on main (`os-build/logs/K1-boot*.txt`,
  K2-boot.txt, K3-boot.txt, K4-boot.txt, K5-boot.txt, K6-boot.txt);
  the K1 proof string 'META OS KERNEL - alive (K1)' is present in
  K1-boot.txt (checked here, 1 occurrence) and the K6 log carries a
  SeaBIOS header (checked here) = real QEMU output. Pax-verified on
  the combined tree: node fail set = known 56-name baseline,
  custos 125/125, officina 49/49, queue 110/110, hortus 14/14,
  secret scan 0.
- v5 CORRECTION (Mac boot, log named): the kernel compiles and boots
  on the Mac per Buffy's repro log `os-build/logs/K6-repro-main-2026-11-01.txt`
  (on main). Key lines checked in this checkout: `user hello: entry
  0x600000000000`, `user sleeper: entry 0x610000000010`, `user crasher:
  entry 0x620000000110`, `HELLO FROM USERSPACE`, `user exit code 0`,
  `INT user page-fault ... task killed` (fault isolated to one task),
  `sleeper: bad call refused`. The Mac run itself was NOT re-run here;
  the log on main is the evidence, and its key lines are present.
- Unverified: no boot re-run on this VM.

## L2 — Kernel core (Rowan)

- Status: MERGED (modules on main, live entry = modular wiring).
- Evidence: `kernel/src/` on main 445daf8 holds framebuffer.rs,
  gdt.rs, interrupts.rs, main.rs, mem.rs, memory.rs, sched.rs,
  syscalls.rs, tasks.rs, traps.rs, user.rs, vga.rs (checked via
  ls-tree). K2-K6 pieces arrived via the Pax eb7653f merge
  (sections E-Q: OS-061..240 plus the OS-230 soak, 3651 ticks,
  zero gaps, clean shutdown per the opencode/os-build line).
  `rowan/kernel` tip is still 3ea9e70: a request file only
  (`kernel/NEXT_TASKS_REQUEST.md`), no code change. Rowan's next
  block awaits Pax's next Layer 0 assignment; no K7 invented —
  spec milestones end at K6.
- Unverified: kernel-crate compile and any boot NOT re-run here.
  The v3 Q12 wiring caveat now sits under the merged modular
  wiring; whether Q12 itself is closed is Pax's call, not verified
  here.

## L3 — Drivers (Rowan)

- Status: MERGED, with R5 SUPERSEDED (preserved, not deleted).
- Evidence: `kernel/src/interrupts.rs` on main; Rowan's R5 main.rs
  preserved verbatim at `kernel/r5-reference/main.rs` + README
  (checked present), superseded as the live entry by the modular
  wiring per Pax's merge note, not deleted.
- v5 CORRECTION (framebuffer DEAD, not pending): `kernel/src/main.rs`
  declares exactly 9 modules (gdt, interrupts, mem, memory, sched,
  tasks, traps, user, vga — checked here); `framebuffer.rs` and
  `syscalls.rs` are NOT declared. Dead lines, counted here:
  framebuffer.rs 576 + syscalls.rs 484 = 1,060 dead. `main.rs` header
  documents "No pixel framebuffer exists under bootloader 0.9.35".
  The v3 "UNWIRED" note is retired: the framebuffer is DEAD per the
  PAX_12H_RESPONSE.md ruling, wire-or-delete is a 2026-11-02 call,
  and nobody spends tonight on it (kill list: framebuffer, graphics,
  networking, SMP, persistence, package manager, installer,
  cybersecurity program).
- Unverified: any boot, any trap run, any further driver. No K7
  milestone exists: banner ruling is K6 (last PROVEN), K7 only when
  a gate goes green on a new log.

## L4 — System services, Goose (Buffy)

- Status: MERGED via the OpenCode line (Pax eb7653f),
  NOT RE-VERIFIED HERE.
- Evidence: sections K+L (OS-153..180) in the merged line: goose
  services + lobster agents, cross-language MCP call live and 7/7
  goose tests per the commit record. The 148-task work order
  (B-L1-01..148) is still the standing shape.
- v5 CORRECTION (L4 split honestly): the merged set above is SMALL —
  sections K+L only. It is NOT Buffy's corpus: per
  PAX_12H_RESPONSE.md, Buffy's corpus is TYPECHECK-FAILS, and that
  verdict is cited from the response doc, not re-measured here.
  "Buffy standing by" is STALE and retired: Buffy is mid-run —
  `buffy/pax-12h-plan` @ 55bd4aa (the 12-hour plan doc, 20:05 EST)
  and `buffy/layer1-goose-services` @ aa86eb2 are both on the remote
  (checked via ls-remote 2026-11-01 ~20:35 EST).
- Unverified / absent: goose tests NOT re-run here; Mac compile
  and QEMU boot of the merged tree still open (Mac lane).

## L5 — Agent runtime, Lobster (Milo)

- Status: DRAFT (model) + MERGED agent pieces.
- Evidence: agent process model `os-build/layer2/AGENT_PROCESS_MODEL.md`
  on main (merged via Pax 9eadb0a, docs only). Lobster agents in
  sections K+L merged via Pax eb7653f per the commit record
  (see L4). ML-L2-01 still DRAFT: (b) Pax K6-shape review and
  (c) Hana shell-view confirm have NOT arrived as of this entry.
- Unverified / pending: nothing here is built beyond the merged
  pieces until the K6-shape review and shell-view confirm land;
  no agent runtime test re-run here.

## L6 — Shell and apps, Lobster (Hana)

- Status: MERGED pieces + IN BUILD (board shell wiring).
- Evidence: shell spec pack on main (83e6c3a era: shell-spec,
  home-surface, shell-formats md+json, walkthroughs, lane-notes;
  os-shell-formats 7/7 pass). `hana/ui-fix-list` @ 57bee07 gate-1
  GREEN stands (npm 1879, zero regression vs main); its substance
  is in main via Pax's 8-branch merge 55f6881 — no re-gate, no
  merge of the old branch as-is. Ui-wave-2 merged via Pax
  (HN-011..025). Ui-wave-bus merged via Pax (853b721, 54 files);
  its 21 bus/index identity-test failures are known-stale on main
  by design (index.html is now the OS app, not the viewer copy)
  and stay a Del lane call, untouched. Board/ landed on main
  445daf8: board.mjs (zero-dep service, rooms, POST/GET messages,
  NOTIFY, JSONL persistence), board.html viewer, board.test.mjs,
  board/README.md. It mirrors the Nuntius line protocol (relay/)
  with its own code and its own board: notify prefix; relay/ and
  the crew bus are untouched. Board tests re-run HERE: 9/9 pass
  (node --test, this VM); Pax re-ran 9/9 himself. Site: site/
  added 83ddfb2, live at meta-os.pages.dev, repo homepage
  repointed to it.
- NOT done: wiring board into the OS shell UI, public deploy
  (per Pax). Unverified: Swift compile itself is Mac-only, still
  owed. No shell run against real OS state.

## L7 — Programs

- Status: PARTIAL — merged pieces on main, further work PARKED
  under Pax HOLD / OS-first order.
- Evidence: `os/worlds/` on main holds custos, musica, officina
  (plus dep, doe, dsny, ems, fdny, hospital, mta, nypd,
  science-lab). Custos patrol service merged via Pax (RW-003/RW-004
  combines); Pax-verified on the eb7653f tree: custos 125/125.
  Officina stages 1+2a in main, officina 49/49 per Pax's
  verification. Musica pack files on main (Hana HN-026..032 era).
  Parked: no new program branch is landing under the current Pax
  HOLD; Rowan statuses cite Custos parked; Buffy is mid-run (see L4),
  not standing by.
- Unverified: program counts are Pax-verified, NOT re-run here.
  FROZEN lanes (META OPUS, META MERCATUS, META NUMMUS, META ACTA)
  are not OS layers and do not appear here; their parked states
  stand.

## Changelog

- 2026-11-01 ~17:45 EST (v4): refresh on
  `milo/layer2-scoreboard-v4` off main 445daf8, per Pax's
  "SCOREBOARD v4 refresh is yours when ready." Main 1591489 ->
  445daf8: opencode/os-build sections E-Q (OS-061..240 + soak)
  hand-combined via Pax eb7653f; live kernel entry now the
  modular wiring, R5 preserved verbatim at kernel/r5-reference/;
  site/ live at meta-os.pages.dev; board/ Layer 6 messaging board
  landed (tests 9/9 here and by Pax); L4/L5 gain the merged
  goose/lobster sections K+L; L7 moves NOT STARTED -> PARTIAL
  (Custos, Officina, Musica pieces on main, further work parked
  under Pax HOLD). Mac compile + QEMU boot of the merged tree
  still unverified (Mac lane). Merges via Pax only; this branch
  never merges itself.
- 2026-11-01 ~10:50 EST (v3): refresh on the NEW branch
  `milo/layer2-scoreboard-v3` off main 1591489, per Pax's
  rebase request on v2 @ befbe6a. This branch is used instead
  of a force-push: v2 @ befbe6a is left untouched and Pax
  merges v3 instead. Main 5dcb4cc -> 1591489: L3 R5
  interrupts wiring MERGED via Pax (f34b122, gate-1 GREEN,
  NOT boot-proven), framebuffer stays UNWIRED per Pax's call;
  science-lab JS registration follow-up MERGED via Pax
  (1591489, gate-1 GREEN: 7 science fails fixed, targeted
  node subset 130 pass / 6 fail vs pre-merge 125 / 11, zero
  new fails); Rowan next block harden K2-K6, no K7. L1/L2/L4/
  L5/L6/L7 otherwise unchanged. Merges via Pax only; this
  branch never merges itself.
- 2026-11-01 ~10:18 EST (v2): refresh on `milo/layer2-scoreboard`
  off v1 5f48a25, per Pax's standing pick (scoreboard refresh
  still Milo's next pick, restated in the K1-on-main dispatch).
  Main b7b915e -> 5dcb4cc: L1 K1 MERGED and proven on main,
  Q1 answered, R5 unblocked; L2 K4/K5/K6 still MERGED, UNWIRED,
  gate-1 GREEN. No other layer changed. Merges via Pax only;
  this branch never merges itself.
- 2026-11-01 ~10:13 EST (v1): refresh on `milo/layer2-scoreboard`
  off main b7b915e, per Pax's merge-run dispatch (refresh SCOREBOARD
  for today's merges). L1: K1 hand-back branch verified, unmerged.
  L2: K4/K5/K6 all MERGED via Pax and gate-1 GREEN, all UNWIRED.
  L4: Buffy work order now 148 tasks, still no branch. L5: agent
  model now on main, still DRAFT pending Pax review + Hana confirm.
  L6: shell spec pack merged, ui-fix lane closed gated-and-in-main,
  21 stale identity tests flagged for Del's lane call. L3/L7
  unchanged. Merges via Pax only; this branch never merges itself.
- 2026-11-01 ~09:13 EST (v0): scoreboard created on
  `milo/layer2-scoreboard` off main b4783d5. Entries grounded in
  checked artifacts only: main tree b4783d5, remote tips
  (`rowan/kernel` a6b6ca9, `hana/os-shell` de0c385,
  `hana/ui-fix-list` 57bee07, `milo/layer2-agent-process-model`
  da054e3, no `buffy/layer1-goose-services` branch), and Milo gate-1
  verdicts posted to room 1. FROZEN lanes (META OPUS, META MERCATUS,
  META NUMMUS, META ACTA) are not OS layers and do not appear here;
  their parked states stand.
