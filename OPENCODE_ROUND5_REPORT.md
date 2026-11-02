# OPENCODE ROUND 5 REPORT — night 1, Mac lane

Branch: `opencode/round5`. Base tip: `134fc7a`.
Standing rules: no source edits outside task scope; errors verbatim + stop; 4 bus files never committed; Spark only if R5-4 needs it, inside caps.

## R5-1 re-prove current main — DONE
- Tip re-proved: `134fc7a` (gate.sh run on the R5 branch, which tracks it).
- `sh os-build/gate.sh` → GATE GREEN, 7/7 (K1 alive, K4 memory,
  K6 ring 3, clean exit, fault isolation, shell answered, STATUS live).
- Committed log `os-build/logs/MERGED-boot-2.txt` (2017 bytes):
  banner `META OS 0.1 (K6)` present, alive line present, K4 summary
  present, all three userspace programs (HELLO, sleeper sleep/wake,
  crasher isolated), `loader refused` count 0, no panic.
  Full run: os-build/logs/gate-run-r5-1.txt.
## R5-2 read_key end to end — PARTIAL (program proven, typed
bytes not yet captured; kernel-lane blocker documented below)
- Delivered: `os-build/userspace/user/src/bin/readkey.rs` (polls
  syscall 5 in a bounded drain-all loop, prints each scancode byte
  (decimal), notes the empty case, yields between passes, exits on
  Enter or bound); `sys_read_key()` wrapper in `user/src/lib.rs`;
  staged at its own base 0x630000000010 (entry verified in ELF +
  boot log); kernel task + spawn + 4th ustack slot; build loops
  (gate.sh + boot-test.sh) build it per-program.
- PROVEN: loads + enters userspace (`user readkey: entry
  0x630000000010`), syscall 5 dispatches (no `bad syscall 5`; empty
  case `readkey: empty` visible in 6+ boots), exits cleanly
  (`readkey done got=N empties=M` + `user exit code 0` when it runs
  to bound).
- Heap fix (REQUIRED, landed): 256 KiB ran dry at the 8th task
  (`memory allocation of 32768 bytes failed`, red screen) — raised
  to 512 KiB in `kernel/src/mem.rs`. The old 256 KiB heap cannot
  hold 8 task stacks. No source beyond this was changed for it.
- NOT YET PROVEN: typed bytes returned by syscall 5. A full day of
  drill runs (10+ boots, HMP-level verification, HMP memory reads
  of the guest ring buffer showing keys never arriving) shows
  typed scancodes never reaching readkey's polls: the console task
  wins every race once readkey has exited, and readkey's own
  polling window (bounded loop, 200+/sec) closes before typed keys
  arrive.
- BLOCKER for the typed-bytes half (kernel lane, Rowan/Pax): with
  readkey ALIVE and spinning, boots intermittently die — EITHER a
  red-screen panic in `exit_task` (`sched.rs:186`
  `unreachable_unchecked`, i.e. a switch that returned) at another
  task's exit, OR a kernel NX-fault storm (`ip 0x202890`, a rodata
  string address, cur=7, starving all IRQs) shortly after readkey
  starts polling. NEITHER happens in the 7-task tree (gate GREEN
  repeatedly, K7 sessions clean). Scheduler-state dumps taken
  inside `exit_task` show consistent books (cur==schedcur,
  marked-Exited-then-schedule) in both green and red boots, so the
  divergence is in CPU reality, not the table — not isolated yet.
  Evidence logs: `os-build/logs/R5-readkey.txt` (polling, empty,
  exits, panics, storm), plus `R5-dbg.txt`, `R5-bisect*.txt`,
  `R5-cur.txt`, `R5-fdbg.txt`, `R5-storm*.txt` from the trail.
## R5-3 final K7 session — DONE
- Refreshed `os-build/logs/K7-boot.txt` (2444 bytes) on current
  main + R5 work: banner `META OS 0.1 (K6)`, alive, all three
  userspace programs, crasher isolated (`task killed`), typed
  `help`/`status`/`mem`/`ps`/`uptime`/bogus via drive.py with
  every real answer (commands list, `tasks 7 ...` + STATUS,
  `mem frames_free ... heap_total 512K`, 7 `ps id ...` rows,
  `uptime 141s ...`, `unknown command` + help re-list).
  0 loader-refused, 0 panic.
- Scope note: 7 tasks in this run (readkey spawn held per R5-2;
  the 7 `ps` rows match). `mem`/`ps`/`uptime` answers come from
  Rowan's merged RW4-1 work — re-run owed if his R-2 surface
  changes (prompt/backspace/read_key not yet in tree: named
  missing, log never fakes them).
## R5-4 Imperium live loop — DONE
- Full end-to-end run on this Mac, all real code: patrol flagged
  (scripted RED assessor: person down x2), review confirmed,
  investigation ran (lenses+neighbours baseline), direct dispatch
  sent the package WITH the picture to the SIMULATED endpoint
  (real HTTP POST to 127.0.0.1:8935/dispatch-simulated served by
  server/queue/queue_service.py; loopback-only enforced by
  crew.check_dispatch_url). No human step, no external endpoint.
- Captured in os-build/logs/R5-imperium/: incident.json (status
  `dispatched-simulated`, full timeline flag..dispatch),
  package-sent.json (byte-identical to what the endpoint
  received: `simulated true`, `dispatch_mode auto`,
  `human_verify false`, picture with flag-frame + face-crop
  refs, destination string names SIMULATED, audit flag true),
  receipt.txt (`sim-6623d237a90b3d9d`, simulated=true),
  drill.log (full transcript).
- Staged feed only (scripted assessor + generated JPEG + injected
  detector), per-incident caps respected, budget guardrail
  untouched. One environment note (not a product defect): the
  queue suite cannot import on this Mac as committed —
  trio_store.py unconditionally imports dynamic_credentials from
  a sandbox-only path (/opt/muse/...); the drill carries the same
  three names as a /tmp-only stub (repo untouched) and runs
  TRIO_STORE=local, which never calls them.
## R5-5 soak — TODO
## R5-6 merge-watch — TODO
## What remains unverified — TODO
