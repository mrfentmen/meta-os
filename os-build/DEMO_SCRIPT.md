# DEMO_SCRIPT — Meta OS, 3-minute submission video (Hana, build-out A1)

Status: SCRIPT ONLY. No render in this task. Capture (OpenCode, R6-2)
films exactly what this script names. If a shot's named file is not
in hand at capture time, that beat is cut to its named static capture
— never to a typed-up lookalike.

## The claim, in order

The adopted claim sentence, clause by clause, is the running order.
Every clause is spoken only over the evidence named for it:

> Meta OS boots on x86_64 in QEMU, drops to ring 3, runs three
> userspace programs, isolates a fault to one task, and gives you a
> shell that reports the machine's real state — reproduced from a
> clean checkout by one command, every claim backed by a committed
> boot log.

## Timed script

### 0:00–0:25 — Boot (claim clause 1)

- On screen: `os-build/logs/MERGED-boot-2.txt`, opening lines, or
  the QEMU capture of the same boot if OpenCode supplies it.
- Lines shown, verbatim from that log:
  - `META OS 0.1 (K6)`
  - `META OS KERNEL - alive (K1)`
  - `mem summary: K4 up`
- Said: "Meta OS boots on x86_64 in QEMU. This is the boot log, not
  a retype — the lines on screen are the machine's own lines."

### 0:25–0:55 — Ring 3, three userspace programs (clauses 2–3)

- On screen: the same log, the three program blocks in order.
- Lines shown, verbatim:
  - `HELLO FROM USERSPACE` / `user exit code 0`
  - `sleeper: before sleep` / `sleeper: pid 5`
  - `crasher: about to read zero`
- Said: "It drops to ring 3 and runs three userspace programs:
  hello, sleeper, and crasher. Three programs, named in the log."

### 0:55–1:15 — Fault isolated to one task (clause 4)

- On screen: the same log, immediately after the crasher block.
- Lines shown, verbatim:
  - `INT user page-fault addr 0x0000000000000000 err 0x0000000000000004: task killed`
  - `sleeper: yielded and back`
  - `sleeper: after sleep`
  - `user bad syscall 99 refused` / `sleeper: bad call refused`
- Said: "The crasher faults, and only the crasher dies. The sleeper
  keeps going, wakes, and finishes. A bad syscall is refused, not
  obeyed."

### 1:15–1:40 — The shell reports the machine's real state (clause 5)

- On screen: the same log, the shell block at the end.
- Lines shown, verbatim:
  - `help`
  - `commands: status help uptime mem ps`
  - `status`
  - `tasks 7 ticks 897 heap_free 31K`
  - `STATUS tasks=7 ticks=897 heap_free_kb=31`
- Said: "And here is the shell, reporting the machine's real state.
  Read the numbers on screen — they are this run's numbers. Do not
  retype them as if they were every run's numbers."
- Note for the narrator: the ticks and heap figures above are the
  values in `MERGED-boot-2.txt`. If the capture uses a newer boot
  log, read that log's values instead. Never quote this script's
  numbers over a different log.

### 1:40–2:10 — The services shell (30 seconds, from DEMO_30S)

- On screen: `os-build/layer1/captures/demo-3-shell-session.txt`,
  in order, exactly as captured:
  - `meta> help`
  - `commands: help echo pwd cd ls cat cp rm mkdir ps uptime log audit time exit`
  - `no pipes, no redirection, no globs, no variables`
  - `meta> ls` → `etc/` / `motd`
  - `meta> cat /etc/hostname` → `meta-os`
  - `meta> ps` → `logd  stopped  restarts=0` / `net  stopped  restarts=0` / `supervisor  stopped  restarts=0`
  - `meta> cat nope` → `cat: notfound`
  - `meta> ls | grep x` → `unsupported: pipes/redirection are not built`
  - `meta> frobnicate` → `unknown command: frobnicate`
- Said: "This is the services layer: twenty-five services, no heap,
  no threads, no libc — written in a language called Goose. The
  shell talks to the real filesystem service, not a mock. Refusals
  matter more than features: a missing file is an error, and a pipe
  is refused instead of quietly becoming a filename."
- Numbers for this beat, from `os-build/layer1/DEMO_FACTS.md` only:
  33 service programs build and run on this machine, 1253 checks
  passing; 17 services need no kernel call at all, 8 need a syscall
  the freeze does not have; the corpus typechecks as 39 ok, 0 failed.
- Honesty line, spoken in this beat, word for word: "The services
  layer, running on this machine. These are host processes against
  a substituted syscall surface — the kernel does not start them
  yet."

### 2:10–2:40 — Imperium: patrol, flag, investigation, dispatch

- On screen: `os-build/logs/R5-imperium/receipt.txt` and
  `os-build/logs/R5-imperium/package-sent.json`, with the
  SIMULATED label visible for the whole beat.
- Lines shown, verbatim from the receipt:
  - `receipt_id=sim-6623d237a90b3d9d`
  - `simulated=true`
  - `== patrol -> review -> investigation -> response ==`
  - `outcome: dispatched-simulated`
  - `incident_id: incident-27e9cfbd46e8078d`
  - `package dispatch_mode: auto`
  - `package simulated: True`
  - `picture.frame: evidence/incident-27e9cfbd46e8078d/flag-frame-cam-a-d0966c.jpg`
- Said: "On RED, the agent sends the package itself, picture
  included. The receipt says simulated, and so does the screen.
  No real emergency service is contacted by this system."
- Do not show a dispatch without the SIMULATED label. Do not say
  "dispatched" without "simulated" in the same sentence.

### 2:40–3:00 — Close: the claim, and what is simulated

- On screen: the claim sentence, then the "what is simulated"
  line, both as text over the receipt close-up.
- Said: "Meta OS boots, drops to ring 3, runs three userspace
  programs, isolates a fault to one task, and gives you a shell
  that reports the machine's real state. The services layer runs
  on this machine, not yet under the kernel. Dispatch in this film
  is simulated. Every claim in this film has a log behind it, and
  the logs are named on screen."
- Board beat, conditional: if a board window capture is in hand at
  capture time, it replaces the last 10 seconds (room list, one
  post, scroll — named capture only). If no board capture is in
  hand, the receipt close-up holds for the full 20 seconds and no
  board claim is spoken. A missing board shot is a cut, not a
  claim.

## Capture rules (binding on the film, not just the script)

1. No line on screen that is not in a file named above.
2. No number that is not in `os-build/layer1/DEMO_FACTS.md` or in
   the named log shown at that moment.
3. SIMULATED stays on screen for every Imperium dispatch frame.
4. If a live step fails on camera, cut to the named static capture
   for that beat. The fallback card (build-out A3) names those cuts
   beat by beat; this script does not invent a second set.
5. Do not say, in any beat:
   - "The OS runs these services." (Host processes, see 1:40 beat.)
   - "The kernel starts them." (Nothing starts them yet.)
   - "The network stack works." (In-memory link only, no NIC, no wire.)
   - "The filesystem persists." (RAM backend; a reboot starts from zero.)

## Sources, and what each one proves

- `os-build/logs/MERGED-boot-2.txt` — boot banner, three userspace
  programs, fault killed to one task, sleeper continuing, shell
  `status` line. The claim-order evidence for beats 0:00–1:40.
- `os-build/layer1/captures/demo-3-shell-session.txt` — the services
  shell session, 25 checks, pass=25 fail=0. The exact lines for
  beat 1:40–2:10.
- `os-build/layer1/captures/demo-1-supervisor-under-load.txt` — ten
  services, restart policies, crash budget. Cutaway if the shell
  beat needs a second screen; first 10 lines only, as in DEMO_30S.
- `os-build/layer1/DEMO_FACTS.md` — the only numbers the narrator
  may quote for the services layer, each with its generating
  command. If a number here disagrees with a report, this file wins.
- `os-build/logs/R5-imperium/receipt.txt` and
  `os-build/logs/R5-imperium/package-sent.json` — Imperium dispatch,
  receipt `sim-6623d237a90b3d9d`, simulated throughout.
- `os-build/shell-spec.md` — the shell surface the 1:15 beat
  demonstrates (status, help, uptime, mem, ps).
- `os-build/layer1/DEMO_30S.md` and `os-build/layer1/DEMO_SHELL.md` —
  the 30-second services segment and the two-shell alignment note
  this script follows. Where this script and DEMO_30S differ on a
  captured line (notably `cat nope`), the capture file wins.

## Companions (build-out A2–A5, following this script)

- A2 shot list: one row per beat above, beat → exact screen/log.
- A3 fallback card: the static capture for each beat if live fails.
- A4 on-screen text set: every caption in the film, spelled, checked.
- A5 receipt close-up spec: which receipt fields the camera shows
  (the fields listed in the 2:10 beat, no others, unless A5 adds
  them with a source).
