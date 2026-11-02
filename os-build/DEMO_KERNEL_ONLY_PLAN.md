# DEMO PLAN — KERNEL ONLY (Del's ruling, 2026-11-02)

The demo shows the real operating system. Three minutes, 180
seconds, every shot from our kernel or from a committed record.
This plan supersedes the beat-6 of `os-build/DEMO_SCRIPT.md` and
the film built from it (`os-build/demo/demo-3min.mp4`).

## BANNED — read first

- No face. No web page. No browser shots. No carrier desktop.
- Nothing that calls a web page the OS, anywhere, in any frame.
- No staged readings presented as real. No re-typed claims:
  every number on screen comes from a committed log or a live
  run captured that day.
- No diagnosis, cause, severity, or treatment language.
  Medicus is scene awareness only and has no beat in this film.
- Dispatch, if shown at all, goes only to the labelled
  SIMULATED loopback endpoint. Never to a real 911 service.

## What changed from the old script, said plainly

The old beat 6 showed the R5 staged run: the receipt was real,
the reading was scripted. That beat is RETIRED. Beat 7 below
replaces it with the real live-camera reading committed on
2026-11-02. One old caution is also lifted: DEMO_SCRIPT said
readkey was not claimed — the wave-3 combined-tree proof
(2026-11-02) supersedes that; typed keys reaching userspace
are now proven and get their own beat (Beat 4).

## The beats — 180 seconds total

### Beat 1 — Boot (0:00–0:22, 22s)

SHOT: QEMU on the Mac, serial terminal held large. The boot
runs in order: `META OS 0.1 (K6)`, `META OS KERNEL - alive
(K1)`, then the memory lines. (Early banner lines scroll off
the 25-line VGA screen — the serial terminal is the shot, as
in the R6-2 capture.)
SOURCE: `os-build/logs/WAVE3-combined-serial.txt` lines 1–3;
gate record `os-build/logs/WAVE3-combined-gate.log` (GATE
GREEN 7/7 on tree c7aeb162) and `os-build/logs/
WAVE3_KERNEL_PROOF.md` items 1–4 (panic count 0).
FALLBACK: screendump `os-build/logs/WAVE3-w3_s1.jpg` on
screen, cut to serial lines 1–2, read them aloud.
SAY: "This is Meta OS — our own kernel, booting on bare
metal in QEMU."

### Beat 2 — Ring 3, three programs (0:22–0:47, 25s)

SHOT: serial, loader lines with separate user addresses,
then `HELLO FROM USERSPACE` and `user exit code 0`, then
`sleeper: before sleep`, `sleeper: pid 5`.
SOURCE: `os-build/logs/WAVE3-combined-serial.txt` lines
34–41 (sleeper entry `0x610000000010` at line 39); loader
addresses for all programs in `os-build/logs/
R5-soak-final.txt` (DEMO_SCRIPT beats 2–3).
FALLBACK: the R5-soak-final.txt loader and hello lines, in
order, as stills.
SAY: "Programs run in ring 3, behind a syscall gate: one
says hello, one sleeps and wakes, one crashes on purpose."

### Beat 3 — Fault isolation (0:47–1:10, 23s)

SHOT: serial close-up, the fault line, then the sleeper
continuing after it, then the refusal: `INT user page-fault
addr 0x0000000000000000 err 0x0000000000000004: task
killed` → `sleeper: yielded and back` → `sleeper: after
sleep` → `user bad syscall 99 refused`.
SOURCE: `os-build/logs/WAVE3-combined-serial.txt` lines
45, 48, 102–104; proof summary WAVE3_KERNEL_PROOF.md
items 5 and 9. Soak context: the R5-5 soak ran 73 minutes,
0 panics (`OPENCODE_ROUND5_REPORT.md`, R5-5).
FALLBACK: the same four serial lines as a still, read in
order.
SAY: "The crasher dies alone. The sleeper keeps running —
and a bad syscall is refused, not run."

### Beat 4 — Readkey: real keys reach userspace (1:10–1:32, 22s)

SHOT: serial close-up during the readkey poll. Keys a, b,
Enter are sent live; the log answers `readkey got 30`,
`readkey got 158`, `readkey got 28`, then `readkey: enter
seen, done got=3`, then a clean `user exit code 0`.
SOURCE: `os-build/logs/WAVE3-combined-serial.txt` line 53
(`readkey: polling syscall 5`) and lines 317–331;
WAVE3_KERNEL_PROOF.md item 6.
FALLBACK: serial lines 317–331 as a still — the got=3 line
is the claim, show exactly that line.
SAY: "Real keys, typed live, reach a userspace program
through syscall 5."

### Beat 5 — The shell reports real state (1:32–2:00, 28s)

SHOT: typed live in the shell. `status` → `STATUS tasks=8
ticks=2177 heap_free_kb=255`; `status` again → `STATUS
tasks=8 ticks=4258 heap_free_kb=255` (ticks moved, heap did
not — that is the point). Then `mem`, then `ps`: eight
rows, id 7 `Running`, the rest `Exited`.
SOURCE: `os-build/logs/WAVE3-combined-serial.txt` lines
339–341, 368–381; screendumps `os-build/logs/
WAVE3-w3_s1.jpg` and `WAVE3-w3_s2.jpg`.
FALLBACK: the two screendumps, then serial lines 341 and
370 side by side so the tick change is visible.
SAY: "The shell reports the machine as it is. Watch the
tick count move between the two status calls."

### Beat 6 — Fetch: the kernel's own calling card (2:00–2:18, 18s)

SHOT: type `fetch`. The kernel draws its ribbon in ASCII
and prints its own state: `Mrfentmen@metaos`, `OS: Meta OS
0.1 (K6) x86_64`, `Host: bare-metal Rust kernel (no_std)`,
`Uptime: 28s ticks 2875`, `Tasks: 8`, `Mem: frames_free
126430 frames_total 126509 heap_free 255K heap_total 512K`,
`Programs: hello sleeper crasher (ring 3)`. This is a
text-mode screen the kernel itself produces — not a web
page, and the plan labels it as text mode on the day if
anyone asks.
SOURCE: `os-build/logs/WAVE3-combined-serial.txt` lines
343–367; screendump `os-build/logs/WAVE3-w3_fetch.jpg`;
WAVE3_KERNEL_PROOF.md item 7.
FALLBACK: WAVE3-w3_fetch.jpg full screen.
SAY: "Even the calling card is drawn from live state —
eight tasks, real memory numbers."

### Beat 7 — Imperium: a real camera, a real reading (2:18–2:44, 26s)

SHOT, three cuts. (a) A Mac terminal running the pipeline:
`python3 server/queue/livecams.py --assess-one --area
Brooklyn` (egress is normal on the Mac) or, if the live
fetch fails that day, the committed record — never a
re-typed summary. (b) The frame itself, full screen:
`server/queue/livecam_records/live-frame.jpg` — Bay Pkwy
@ 78 St (Kings Hwy), Brooklyn, a live NYC DOT traffic
camera still, on-image caption 11/02/2026 10:05:33 AM,
sha256 recorded in the reading file. (c) The reading,
scrolled in the terminal from `server/queue/
livecam_records/live-reading.json`: product `vigiles`,
category "normal activity", the street description (yellow
buses, white truck and van, crosswalk, storefronts), the
stated uncertainties, `requires_human_review: true`, model
`muse-spark-1.3`.
SOURCE: `server/queue/livecam_records/live-frame.jpg` +
`live-reading.json` (committed 2026-11-02, a859aaa /
965abf3); pipeline shape `os-build/LIVE_CAMS.md`; the
patrol→review→judge chain is `server/queue/crew.py`,
shown as terminal/log output only.
DISPATCH, honest shape: this frame flags nothing, so
nothing is dispatched — the film says so. No flagged live
incident exists on record, and the plan invents none. If a
capture-day run ever flags one, its dispatch may be shown
only as the labelled simulated loopback receipt (format
example only: `os-build/logs/R5-imperium/receipt.txt`,
`receipt_id=sim-6623d237a90b3d9d`, `simulated=true` — that
receipt belongs to the retired staged run and is never
presented as this run's).
FALLBACK: the committed frame + reading, exactly as above.
That is the primary source, not a downgrade.
SAY (the honest line, mandatory, word for word in the
film): "This reading is real — a live Brooklyn traffic
camera, read by Muse Spark. Nothing is flagged, so
nothing is sent. When something is flagged, dispatch goes
to a simulated endpoint, labelled simulated — never to a
real 911."

### Beat 8 — Close (2:44–3:00, 16s)

SHOT: back in QEMU. Type `status` once more — ticks have
moved again — and hold on `ps` with id 7 still `Running`.
SOURCE: same tree as Beats 1–6; fallback serial lines
370 and 380 from WAVE3-combined-serial.txt.
SAY, closing: "Boot, ring 3, three programs, one isolated
fault, a keyboard, a shell that tells the truth, and a
real camera read by a real model. That is what runs
today."

Timings: 22 + 25 + 23 + 22 + 28 + 18 + 26 + 16 = 180s.

## Conditional beats — only if the proof exists at capture time

CONDITIONAL A — K3 / K4 (inserts before Beat 8, taking its
time from the Beat 5 and Beat 6 holds; the film never runs
past 180s). Include ONLY if a named gate log is committed
by capture time: for K3, a boot log showing the demand
fault served, the crasher contained, and the
outside-region negative, in one boot with no panic; for
K4, a boot log showing the talker/listener pair exchanging
a message through the mailbox. STATUS AT PLAN TIME: these
logs do not exist. The K3 build has landed and passed a
code gate only (no boot log); K4 is a reviewed design, not
built. If the logs are absent, the beats are absent — no
placeholder, no narration about them.

BONUS B — Kernel-drawn graphics (KF milestone 1). Include
ONLY if the KF-11 proof pack exists for one tree: the
committed serial log, the three-screendump set, and gate
GREEN 7/7, read by Pax. If real, it replaces the last 5
seconds of Beat 1: the kernel itself drawing its boot
screen. STATUS AT PLAN TIME: does not exist (KF-01 not yet
run). Conditional, never required, never promised in the
narration.

## Proofs that do not exist yet — named honestly

- K3 demand-paging boot/gate log: does NOT exist.
- K4 IPC boot log: does NOT exist (design only).
- KF milestone-1 graphical proof pack: does NOT exist.
- A flagged live-camera incident and a simulated dispatch
  receipt from a live frame: do NOT exist. The only
  dispatch receipt on record is the retired staged run's.
- The 2-hour soak verdict: still pending. The only soak
  number this film may use is the R5-5 record: 73 minutes,
  0 panics.
- A capture-day live Imperium run on the Mac: not yet
  captured. The committed 2026-11-02 reading exists and
  carries Beat 7 either way.
- Fresh screendumps at the capture tree: the wave-3 set is
  at c7aeb162 and kernel/src has not changed since, but
  OpenCode 1 re-captures fresh (below) rather than reusing.

## What OpenCode 1 must capture on the Mac, in order

1. Gate first: `sh os-build/gate.sh` on the capture tree →
   `os-build/demo/demo-capture/gate.log`. Must read GATE
   GREEN 7/7. If not, stop — no filming on a red tree.
2. One QEMU+VNC boot, serial saved whole →
   `os-build/demo/demo-capture/serial-full.txt`.
   Screendumps during that same boot:
   `cap-b1-boot.png`, `cap-b2-programs.png`,
   `cap-b3-fault.png`, `cap-b5-status1.png`,
   `cap-b5-status2.png`, `cap-b5-ps.png`,
   `cap-b6-fetch.png`. During the readkey poll window,
   send keys a, b, Enter (Beat 4); type `fetch` live
   (Beat 6); type `status` / `mem` / `ps` live (Beat 5).
3. Conditional captures, only if the gates in the
   conditional section have landed: `cap-k3-gate.log`,
   `cap-k4-ipc.png`, `cap-kf1-boot.png`. Absence is
   recorded in the notes, not worked around.
4. Imperium: terminal capture of `python3 server/queue/
   livecams.py --assess-one --area Brooklyn` →
   `os-build/demo/demo-capture/cap-b7-livecam-terminal.txt`,
   with the fresh frame and reading saved by the tool
   itself. If the fetch fails, film the committed
   2026-11-02 pair and write the failure in the notes.
5. Assemble to exactly 180.000s →
   `os-build/demo/demo-kernel-only.mp4` (fresh name; never
   overwrite demo-3min.mp4). Update `os-build/demo/
   CAPTURE_NOTES.md` with the real / scripted / simulated
   split for this cut.
6. Push everything on the capture branch for Pax to
   verify against this plan before anything is called
   done.
