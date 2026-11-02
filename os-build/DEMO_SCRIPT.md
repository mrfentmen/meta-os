# DEMO SCRIPT — Meta OS, 3 minutes (H-FP1)

Branch: `hana/demo-script`. Freeze 05:12 EST. Capture pass uses
this script; without it the fallback is claim order with no script.

Rule for every beat: show only what a committed log already shows.
No invented facts. Where the film cannot show a live step, cut to
the committed log line named in the beat — never to a re-typed
claim. The Imperium beat is SIMULATED and stays labelled so on
screen. Total running time: 3:00.

## Beat 1 — Boot (0:00–0:25)

SAY: "This is Meta OS, booting on bare metal hardware in a VM."
SHOW: the boot lines, in order:
`META OS 0.1 (K6)` then `META OS KERNEL - alive (K1)`, then the
memory map lines (`mem map: 15 regions`, `mem frames: 127199
usable total`, `mem heap: 512K total`, `mem summary: K4 up`).
SOURCE: `os-build/logs/R5-soak-final.txt`, `os-build/logs/K6-boot.txt`.
Gate record: `sh os-build/gate.sh` → GATE GREEN, 7/7
(`OPENCODE_ROUND5_REPORT.md`, R5-1).

## Beat 2 — Ring 3 (0:25–0:50)

SAY: "User programs run in ring 3, behind a syscall gate — not in
the kernel."
SHOW: the loader lines for the three programs, with their
separate user addresses (`0x600000000000`, `0x610000000010`,
`0x620000000110`), and the line `HELLO FROM USERSPACE`.
SOURCE: `os-build/logs/R5-soak-final.txt`; ring-3 segments in
`kernel/src/gdt.rs` (user code/data, RPL 3); syscall gate
`int 0x80` DPL 3 in `kernel/src/traps.rs`.

## Beat 3 — Three programs (0:50–1:20)

SAY: "Three user programs: one says hello, one sleeps and wakes,
one crashes on purpose."
SHOW, in order: `HELLO FROM USERSPACE` then `user exit code 0`;
`sleeper: before sleep`, `sleeper: pid 5`, `sleeper: yielded and
back`, `sleeper: after sleep`; `crasher: about to read zero`.
SOURCE: `os-build/logs/R5-soak-final.txt`.

## Beat 4 — Fault isolation (1:20–1:45)

SAY: "The crash kills only the crashing program. Everything else
keeps running."
SHOW: `INT user page-fault addr 0x0000000000000000 err
0x0000000000000004: task killed` — then, right after it, the
sleeper continuing (`sleeper: yielded and back`,
`sleeper: after sleep`) and the kernel still answering.
SOURCE: `os-build/logs/R5-soak-final.txt`. Soak record: the
soak log carries no panic line and exactly one isolated
task-killed fault; the R5-5 soak ran 73 minutes, 0 panics
(`OPENCODE_ROUND5_REPORT.md`, R5-5).

## Beat 5 — Shell reports real state (1:45–2:20)

SAY: "The shell reports live numbers, not fixed text. Watch the
tick count move."
SHOW, typed live: `status` → `tasks 7 ticks 11739 heap_free 287K`
and `STATUS tasks=7 ticks=11739 heap_free_kb=287`; type `status`
again → `tasks 7 ticks 441232 heap_free 287K` (ticks moved,
heap did not — that is the point). Then `mem` →
`mem frames_free 127150 frames_total 127199 heap_free 287K
heap_total 512K`. Then `ps` → seven rows, `ps id 7 state
Running`, the rest `Exited`.
SOURCE: `os-build/logs/R5-soak-final.txt` (same commands, same
answers, typed in R5-3: `help` / `status` / `mem` / `ps` /
`uptime` / bogus, every real answer — `OPENCODE_ROUND5_REPORT.md`,
R5-3). A bad syscall is refused, not run: `user bad syscall 99
refused`.

## Beat 6 — Imperium run, with receipt (2:20–3:00)

ON-SCREEN LABEL, whole beat: SIMULATED. SAY: "This last run is
simulated, end to end — and here is its receipt."
SHOW: the chain `patrol -> review -> investigation -> response`,
then `outcome: dispatched-simulated`,
`incident_id: incident-27e9cfbd46e8078d`,
`package dispatch_mode: auto`, and the receipt close-up:
`receipt_id=sim-6623d237a90b3d9d` with `simulated=true`.
SOURCE: `os-build/logs/R5-imperium/drill.log`,
`os-build/logs/R5-imperium/receipt.txt`,
`os-build/logs/R5-imperium/package-sent.json`,
`os-build/logs/R5-imperium/incident.json`.
SAY, closing: "Boot, ring 3, three programs, one isolated fault,
a shell that reports real state, and a simulated run with a
receipt. That is what runs today."
DO NOT SAY: that the Imperium assessment is a real reading. Its
package summary is stubbed (`stubbed summary: normal activity`,
`package-sent.json`) — the receipt is real, the reading is not.

## If a live step fails on camera

Do not re-shoot a claim. Cut to the committed log line named in
the beat, read it aloud, and move on. The fallback card
(build-out A3) carries the claim-order beats for a full live
failure. If the whole boot fails, the demo is the logs, not a
re-enactment.

## NOT claimed in this demo

- Readkey typed bytes: the readkey program loads, polls syscall 5,
  and reports the empty case, but typed bytes reaching it are NOT
  proven (`OPENCODE_ROUND5_REPORT.md`, R5-2 PARTIAL; Mac boot log
  for the Rowan merge pack still owed). No typing demo.
- The Meta OS face: this demo is the text boot. The kernel face
  (`KERNEL_FACE_TASKS.md`) is a new top target, not a filmed claim.
- Any diagnosis, triage, or treatment wording: Medicus is scene
  awareness only, and no Medicus beat is filmed here.
