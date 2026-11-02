# OC1B combined-tree re-proof — serial diff vs the prior proven serial + verdict

Tree: opencode/500 tip 94010c76ee095fa6c6bcfa4405cd56a9695f32d3
(origin/main 3452d244 merged at c110a051; `git status --porcelain` clean
except this section's new proof files; no kernel/ change anywhere
c7aeb162..HEAD).
Image: kernel/target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin
built from this tree by the gate run in
os-build/logs/OC1B-reproof-combined-gate.log,
sha256 cf1d49ddd3d77948ed99c912551021cd777adf7406ae32ca20c08801105fdca2
(11,202,048 bytes). VNC boot serial:
os-build/logs/OC1B-reproof-combined-serial.txt (1086 lines, 25,638 bytes).
Baseline: os-build/logs/WAVE3-combined-serial.txt (381 lines, tip c7aeb162).

Gate on this tree (OC1B-reproof-combined-gate.log): GATE GREEN, 8/8 —
K1 alive, K4 memory, K6 ring 3, K6 clean exit, K6 fault isolation,
readkey spawned, shell answered, status reported live state; exit 0.

## Assertion re-proof (previously-green claims, combined serial lines)

1. Banner + alive: line 1 `META OS 0.1 (K6)`, line 2
   `META OS KERNEL - alive (K1)`. Same as WAVE3 lines 1–2. PROVEN.
2. Memory: line 26 `mem summary: K4 up`; heap 512K lines 23–25
   identical in shape to WAVE3 lines 23–26. PROVEN (gate: ok K4 memory).
3. Ring 3: line 34 `HELLO FROM USERSPACE`, line 35 `user exit code 0`.
   Same as WAVE3 lines 34–35. PROVEN (gate: ok K6 ring 3, ok K6 clean exit).
4. Fault isolation: line 45 `INT user page-fault ... task killed`,
   then line 48 `sleeper: yielded and back` and line 60
   `sleeper: after sleep` — the machine kept working after the kill.
   Same classes as WAVE3 lines 45/48/102. PROVEN (gate: ok fault isolation).
5. Readkey spawned: line 52 `user readkey: entry 0x630000000010`,
   line 53 `readkey: polling syscall 5`. Same as WAVE3 lines 52–53.
   PROVEN (gate: ok readkey spawned).
6. Readkey typed path: lines 999–1056 record the session's own typed
   bytes (scancodes 31/20/30/22/28 …: the `status` + `fetch` keystrokes
   of THIS boot, 13 bytes incl. enters), line 1056
   `readkey: enter seen, done got=13`, line 1057 `user exit code 0`.
   WAVE3 lines 316–331 show got=3 for ITS 3 typed bytes (a,b,ret).
   got=13 vs got=3 is a METHOD difference (13 bytes typed here vs 3
   there), not a behaviour change: entry → poll → got → enter-seen →
   clean exit holds on both trees. PROVEN.
7. Shell + status: line 1060 `STATUS tasks=8 ticks=1114 heap_free_kb=255`
   answering the typed `status` (line 1059 echo). Same shape as WAVE3
   lines 340–341. PROVEN (gate typed help+status: ok shell answered,
   ok status reported live state).
8. Fetch: line 1083 `Uptime: 17s ticks 1750`, line 1084 `Tasks: 8`,
   line 1085 `Mem: frames_free 126430 frames_total 126509
   heap_free 255K heap_total 512K`, line 1086
   `Programs: hello sleeper crasher (ring 3)` — byte-identical mem/tasks
   values to WAVE3 lines 364–367; uptime/ticks differ (timing only).
   Screendump os-build/captures/oc1b-reproof-combined-fetch.png shows
   the ribbon + these rows. PROVEN.
9. Bad syscall refusal: line 61 `user bad syscall 99 refused` (sleeper's
   drill path, same as WAVE3 line 103). PROVEN.
10. Negative counts: `panic` (case-insensitive) count 0 in both serials;
    `loader refused` count 0 in both. PROVEN.
11. Shell screendump: os-build/captures/oc1b-reproof-combined-shell.png
    (720x400, 4,574 bytes) is the text-mode screen at the shell after
    boot (banner fragment + progress lines visible). Pairs the serial.

## Line-class diff (combined vs WAVE3)

- SAME: banner, alive, mem region/map/frames/allocator/probe/heap/Box+Vec/
  stress/summary lines; user hello/sleeper/crasher spawn lines
  byte-identical (sizes 2527624/2798760/2539192, entries
  0x600000000000/0x610000000010/0x620000000110, head bytes identical);
  readkey spawn line matches except size 2799720 vs 2799712 (+8 bytes)
  with identical entry 0x630000000010 and identical head bytes — same
  source rebuilt, size delta only, behavior identical (entry → poll →
  got → enter-seen → exit holds); kill line verbatim; sleeper-survives lines;
  bad-call-refused pair; STATUS/fetch shapes; mem values identical.
- CHANGED (timing only): K3 spin counts, tick values (1114/1750 vs
  2177/2875/4258), uptime (17s vs 28s), progress-counter extents
  (readkey ran longer before keys: to ~98000 vs ~25400 — wall-clock
  scheduling under a loaded Mac, not a kernel change), got counts
  (13 vs 3 — input length, see 6).
- ABSENT BY METHOD (not lost claims): `commands:`/`unknown command`
  lines (WAVE3 lines 333–337: `help` was typed there, never typed
  here — covered by this tree's gate log, which typed help and
  asserts `ok shell answered`); second STATUS with moved ticks
  (WAVE3 lines 340 vs 369–370: one `status` typed here — tick movement
  is proven by the gate's own drive on this tree and by STATUS 1114 vs
  fetch Uptime ticks 1750 advancing within this boot); `mem`/`ps`
  answers (never typed here — program set identical per fetch line
  1086; mem values identical per line 1085).
- NEW: none from the kernel. Longer progress runs only.

## Verdict

NO REGRESSION. Every previously-green assertion re-proves on the
combined tree; every new/missing/changed line class is named above
with its cause (timing, input length, or drive method). No wave-slot
gate applies (all five slots are NO WAVE per
os-build/logs/OC1B-reproof-waves-tree.txt), and per §8's stop rule
there is nothing to stop on: gate GREEN, panic 0, no lost claim line.
