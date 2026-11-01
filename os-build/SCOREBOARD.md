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

## L1 — Boot (Rowan)

- Status: MERGED, PROVEN ON MAIN, NOT BOOT-REPRODUCED HERE.
- Evidence: K1 hand-back MERGED via Pax to main 5dcb4cc
  (b343df9 lockfile + logs + report, 8431a79 static
  relocation-model, 5dcb4cc entry_point BootInfo shared ref;
  proof string untouched). All 4 boot logs on main
  (`os-build/logs/K1-boot*.txt`) contain
  'META OS KERNEL - alive (K1)', no panic, SeaBIOS header =
  real QEMU output per Pax's pre-merge verification. Q1
  ANSWERED: `kernel/Cargo.lock` (bootloader 0.9.35) is now on
  main. Rowan R5 wiring UNBLOCKED per Pax's dispatch — wire
  against main now, one module per commit onto the proven
  tree. `opencode/os-build` has since advanced to d8f043e
  (Section B subject line only, not verified here, unmerged,
  OpenCode lane — monitor only).
- Unverified: QEMU boot NOT re-run on this VM (Mac-built
  image) and the kernel crate NOT compiled here — the merge
  is Pax-verified, not reproduced here. `kernel/src/main.rs`
  on main is still K1-only; K2-K6 modules remain unwired.

## L2 — Kernel core (Rowan)

- Status: PARTIAL — merged pieces unwired, nothing booted.
- Evidence: K2 framebuffer console (`kernel/src/framebuffer.rs`,
  576 lines) merged 6c29370, Milo gate-1 GREEN (standalone rustc
  1.99.1 clean, 0 warnings, NOT wired into main.rs, NOT a
  kernel-crate compile or boot verdict). K4 memory module
  (`kernel/src/memory.rs`, 979 lines: bitmap frame allocator,
  page-table mapper, heap) MERGED via Pax (main 83e6c3a era, Pax
  merge-everything run), Milo gate-1 GREEN (same standalone-rustc
  caveat). K5 task scheduler skeleton (`kernel/src/tasks.rs`,
  UNWIRED) MERGED via Pax, Milo gate-1 GREEN 09:25 (standalone
  rustc clean, own host harness ALL PASS). K6 syscall module
  (`kernel/src/syscalls.rs`, 484 lines, UNWIRED, six-call dispatch)
  MERGED via Pax as 4bf2367, Milo gate-1 GREEN 09:40 (standalone
  rustc clean, own host harness ALL PASS, main.rs untouched).
  `kernel/src/` on main 5dcb4cc now holds framebuffer.rs,
  interrupts.rs, main.rs, memory.rs, syscalls.rs, tasks.rs.
  `rowan/kernel` tip is still 3ea9e70: a request file only
  (`kernel/NEXT_TASKS_REQUEST.md`), no code change; Layer 0 queue
  empty, no K7 invented (spec milestones end at K6).
- Unverified: kernel-crate compile, any boot, R5 wiring (now
  UNBLOCKED on the K1 merge per Pax; Q12 wiring facts in
  MAC_QUESTIONS still open as a caveat for K6 wiring).

## L3 — Drivers (Rowan)

- Status: PARTIAL — one driver merged, unwired.
- Evidence: K3 interrupts (`kernel/src/interrupts.rs`, 493 lines:
  IDT, PIC remap/EOI, PIT channel 0, PS/2 keyboard ring buffer)
  merged 6c29370, Milo gate-1 GREEN (standalone rustc clean,
  core only, no alloc, NOT wired into main.rs).
- Unverified: kernel-crate compile, any boot, any further driver.

## L4 — System services, Goose (Buffy)

- Status: DESIGNED, NOT BUILT.
- Evidence: K6 service shape DESIGNED on main
  (`os-build/layer1/K6_SERVICE_SHAPE.md`, 91dbbf5; Goose facts
  verified against goose-mcp 1.1.0, syscall v0 draft, Q1/Q5/Q9 left
  OPEN). Work order expanded to 78 tasks on main (b4783d5, boss order
  2026-11-01 ~09:12), then to 148 tasks (B-L1-01..148, Pax expansion
  round 2, main 166e4420; branch `buffy/layer1-goose-services` only,
  never main, Pax merges).
- Unverified / absent: still no `buffy/layer1-goose-services` branch
  on the remote (only `buffy/research` @ 41e4b4c), no Goose service
  source, no compile. Standing gap tasks in the work order wait on
  K6/Layer 3 landings.

## L5 — Agent runtime, Lobster (Milo)

- Status: DRAFT.
- Evidence: agent process model `os-build/layer2/AGENT_PROCESS_MODEL.md`
  on `milo/layer2-agent-process-model` @ da054e3 (identity, lifecycle,
  Layer 4-services-only capabilities, audit-trail records; Lobster
  section grounded in a live lobster-mcp 1.1.0 check on this VM).
  DESIGNED step (a) done. The model is now also ON MAIN (merged via
  Pax 9eadb0a together with scoreboard v0, docs only).
- Unverified / pending: (b) Pax K6-shape review, (c) Hana shell-view
  confirm — neither arrived as of this entry. Nothing here is built
  until K6 exists (K6 syscalls are now on main but UNWIRED).

## L6 — Shell and apps, Lobster (Hana)

- Status: SPEC-ONLY, with fixes queued.
- Evidence: shell spec pack MERGED via Pax (83e6c3a: shell-spec,
  home-surface, shell-formats md+json, walkthroughs, lane-notes;
  os-shell-formats 7/7 pass). `hana/ui-fix-list` @ 57bee07 gate-1
  GREEN stands (npm 1879, zero regression vs main); Pax's 10:08 call
  CLOSED the item as gated-and-in-main — no re-gate, no merge of
  the old branch as-is (its substance is byte-identical on main,
  main has moved ahead). HN-077 Swift mirror merged 78f9a4f
  (Milo gate-1 GREEN: 2107 tests, 2044 pass, 63 fail, 0 new
  failures, 3 mirror tests pass). Ui-wave-bus merged via Pax
  (853b721, 54 files); its 21 bus/index identity-test failures are
  known-stale on main by design (index.html is now the OS app, not
  the viewer copy) and stay a Del lane call, untouched. Hana is
  awaiting Pax's next dispatch (HANA_LAYER2_TASKS.md), no new lane
  started.
- Unverified: Swift compile itself is Mac-only, still owed. No shell
  runs against real OS state (none exists yet).

## L7 — Programs

- Status: NOT STARTED.
- Evidence: no work order, branch, or artifact on main or the remote
  as of this entry.
- Unverified: everything.

## Changelog

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
