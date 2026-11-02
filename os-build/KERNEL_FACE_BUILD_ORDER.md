# KERNEL FACE BUILD ORDER — the L6 fix

Del's ruling, 2026-11-02: the kernel itself must draw the desktop.
Route 1 is chosen: upgrade the bootloader so the kernel gets a
framebuffer. (Route 2, UEFI GOP taken directly, is the rejected
alternate; Rowan's spike in `os-build/face/KERNEL_FACE.md` found
bootloader 0.9.35 provides NO framebuffer, and Route 1 leads on
paper.) This order turns `os-build/KERNEL_FACE_TASKS.md` into a
sequenced, proof-per-step build list.

## Fences (do not move)

- `kernel/src/` is Rowan's pen. Rowan writes all kernel code here.
- `kernel/src/syscalls.rs` is FROZEN. No edits, and this work
  consumes no new syscall numbers.
- Text boot stays FIRST at every step: banner, alive line, ring-3
  programs, fault isolation, text shell — in that order, before any
  graphics. If a step cannot keep those claims true on the same
  boot, the step is not done, whatever its screendump shows.
- OpenCode 1 (Del's Mac) is the only proof lane: QEMU screendumps,
  serial logs, `os-build/gate.sh`. A claim without a committed
  artifact from that lane is unverified.
- Captures land in `os-build/captures/`; boot logs in
  `os-build/logs/`. Pax reads the log and the screendumps before
  any milestone is marked.

## Milestone 1 tasks

### KF-01 — Bootloader upgrade, spike-and-decide (timeboxed)
- Owner: Rowan.
- Deliverable: a decision record appended to
  `os-build/face/KERNEL_FACE.md`: target bootloader version,
  exactly what breaks (Cargo.lock pin move stated, not hidden),
  and either (a) the PROVEN kernel booting unchanged on the new
  bootloader, or (b) a written failure with the error evidence.
  Timebox: one Mac working session; at most two version attempts
  (the 0.10.9 API-fail and 0.11 std-fail already on record from the
  earlier spike count as attempts — start from that evidence, do
  not re-run them blind).
- Proof: QEMU serial log of the unmodified kernel on the new
  bootloader carrying the K6 banner and the alive line, plus a
  screendump of the text console.
- Fallback if the new bootloader breaks the proven boot: restore
  the 0.9.35 pin (Cargo.toml + Cargo.lock as on main today),
  re-run gate.sh to GREEN 7/7 on the restored stack, file the
  failure evidence in the decision record, and stop. Route
  re-decision (UEFI GOP re-spike) is Pax's call, not a retry loop.

### KF-02 — Gate the upgraded stack before any graphics
- Owner: OpenCode 1.
- Deliverable: full gate run on the KF-01 tree.
- Proof: `os-build/logs/KF02-gate.txt` — gate.sh GREEN 7/7,
  including the readkey line ("readkey: enter seen, done got=3"),
  the fetch screen, bad-syscall-99 refusal, and task-kill
  isolation; panic count 0.

### KF-03 — Framebuffer wiring
- Owner: Rowan.
- Deliverable: `kernel/src/main.rs` declares the existing
  `framebuffer` module and constructs a `Framebuffer` from the
  new BootInfo; on successful init the kernel clears the screen
  to solid blue through the framebuffer and prints one serial
  line: `fb: <width>x<height> pitch <n> fmt <format>`.
  `framebuffer.rs` itself changes only if a real defect is found,
  and any such change is flagged in the commit.
- Proof: screendump `os-build/captures/kf03-blue.png` (solid blue
  frame, no text) + the `fb:` serial line in
  `os-build/logs/KF03-boot.txt` + gate still GREEN 7/7 (KF-02
  rerun).

### KF-04 — Pixel text
- Owner: Rowan.
- Deliverable: text drawn through the framebuffer's glyph path
  (`draw_glyph` already exists in `framebuffer.rs`): the strings
  `META OS` and the K6 banner line drawn at fixed coordinates on
  the blue frame.
- Proof: screendump `os-build/captures/kf04-text.png` with both
  strings legible + serial log line `fbtext: ok`.

### KF-05 — Boot lines re-rendered in graphics
- Owner: Rowan.
- Deliverable: after the text phase completes, the face takes
  over the screen and re-renders the actual boot lines (banner,
  alive line, milestone, program list) as pixel text — same
  words as the serial log of that same boot, not canned strings.
- Proof: screendump `os-build/captures/kf05-bootlines.png` +
  the matching serial log committed beside it; Pax diffs the
  words by eye.

### KF-06 — Kernel-drawn boot screen (blue ribbon)
- Owner: Rowan.
- Deliverable: full-screen graphical boot screen drawn by kernel
  code: dark background, the blue ribbon motif ported from the
  ribbon math in `js/logo-background.js` (same sine family, same
  blue; the pre-rendered ASCII frames in
  `kernel/src/logo_frames.rs` are the shape reference only — the
  pixels are computed at runtime, not blitted from the frames),
  with the boot status line from KF-05 under it.
- Proof: screendump pair `os-build/captures/kf06-ribbon-a.png`
  and `kf06-ribbon-b.png` taken seconds apart, showing the ribbon
  in two different phases, + serial lines logging the frame
  counter value at each capture.

### KF-07 — Ribbon animation as a kernel task; keypress exits
- Owner: Rowan.
- Deliverable: the ribbon animates as a scheduled kernel task
  (frame counter advances on the serial log); any keypress ends
  the attract phase and hands control to the shell phase,
  mirroring the console attract behaviour that exists today.
- Proof: serial log showing the frame counter advancing past
  100, then the keypress-exit line, in
  `os-build/logs/KF07-boot.txt`; gate still GREEN 7/7.

### KF-08 — Graphics failure fallback (safety, before windows)
- Owner: Rowan.
- Deliverable: if framebuffer init fails or is disabled by a
  boot-time flag, the kernel stays on the text console, prints
  `fb: unavailable, staying on text console` plus the reason,
  and the text shell answers normally. The machine never bricks
  on the face.
- Proof: forced-failure boot log
  `os-build/logs/KF08-fallback.txt` showing the fallback line
  followed by a working `status` answer on the text console.

### KF-09 — Window primitives
- Owner: Rowan.
- Deliverable: rectangle/border/title-bar drawing composed from
  `fill_rect` + pixel text: one static window frame (title bar
  with the word `Shell`, body area, border) drawn over the
  ribbon desktop background.
- Proof: screendump `os-build/captures/kf09-window.png`.

### KF-10 — The real shell in a window
- Owner: Rowan.
- Deliverable: the console shell's input/output routed into the
  KF-09 window: keyboard input goes to the shell, shell output
  renders as pixel text inside the window. `status`, `mem`,
  `ps`, `uptime`, `help` answered inside the window with the
  kernel's real values.
- Proof: screendump `os-build/captures/kf10-shell.png` showing
  a typed `status` and its answer inside the window + the same
  run's serial log; the numbers in the window must match the
  serial log of that boot. Gate still GREEN 7/7.

### KF-11 — Milestone 1 proof pack
- Owner: OpenCode 1.
- Deliverable: one cold boot captured end to end and committed:
  serial log + screendump set (text phase, ribbon boot screen,
  shell window with live answers).
- Proof: `os-build/logs/KF11-m1-boot.txt` (panic count 0),
  `os-build/captures/kf11-set/` (the three screendumps), gate
  GREEN 7/7 on the same tree. Pax reads all of it before
  Milestone 1 is marked done.

## Later milestones (labelled; not part of Milestone 1)

### Milestone 2 — pointing and the real desktop

- KF-12 (Rowan): PS/2 mouse: init, packet parsing, cursor drawn
  and moving. Proof: screendump pair with the cursor at two
  positions + serial line logging received packet counts.
- KF-13 (Rowan): click events delivered to the window layer;
  clicking a window raises and focuses it. Proof: screendump
  pair before/after a click, focus visibly switched.
- KF-14 (Rowan): compositor desktop: ribbon background + top bar
  (name, uptime-derived clock) + dock cells drawn; two windows
  overlapping. Proof: screendump set, one per element landed.
- KF-15 (Rowan): dashboard window from real kernel state: cards
  for frames free, heap used, task count, uptime, refreshed
  live. Proof: screendump + serial log of the same boot; card
  values must equal the shell's `status`/`mem`/`ps` answers.
- KF-16 (Rowan): settings window that changes the desktop for
  real: light/dark bar, animation pause. Proof: screendump pair,
  one per mode.

### Milestone 3 — endurance and the honest write-up

- KF-17 (OpenCode 1): soak: face up 30 minutes, ribbon
  animating, shell in its window still answering at the end.
  Proof: committed soak log with first and last timestamps and
  a final `status` answer; panic count 0.
- KF-18 (OpenCode 1): 60-second QEMU recording of the full boot
  into the face. This is a demo asset, not a proof artifact; the
  logs and screendumps above remain the proof.
- KF-19 (Rowan): `os-build/face/KERNEL_FACE.md` final: what
  runs, what each window is, and what is NOT in the bare-metal
  face (no browser, no Linux apps — those live on the carrier
  face; stated plainly).
- KF-20 (OpenCode 1): gate.sh gains the face boot log as a
  second artifact. The text-claim gate is unchanged and is never
  replaced by the face artifact.

## Definition of done — Milestone 1 only

Turn the machine on: the Meta OS kernel boots (text phase intact —
banner, alive line, ring 3, three programs, fault isolation), then
the kernel itself, running its own code with no browser and no
Linux underneath, draws a graphical boot screen (the blue ribbon)
and a desktop holding one window, and inside that window sits the
real shell answering `status`, `mem`, and `ps` with the machine's
actual state, typed on the real keyboard.

Done means: KF-11's committed serial log, the three-screendump
set, and gate GREEN 7/7 all exist for the same tree, and Pax has
read them. Anything less is in progress, whatever a branch claims.

Everything past this — mouse, compositor, dashboard, settings,
soak — is Milestones 2 and 3, not Milestone 1.

## Honest status (2026-11-02)

PROVEN (committed boot logs, read by Pax):
- The bare-metal kernel boots on x86_64 in QEMU, drops to ring 3,
  runs three userspace programs, isolates a fault to one task,
  and serves a text shell (`status`, `mem`, `ps`, `uptime`) that
  reports real machine state. Combined-tree gate GREEN 7/7 at
  c7aeb162; `kernel/src/` is unchanged since that proof, so it
  carries to current main.
- Keyboard input works in the kernel: the combined log shows
  readkey typing a, b, return — "readkey: enter seen, done
  got=3". Bad syscall 99 is refused; panic count 0.
- The console attract screen cycles the pre-rendered ASCII ribbon
  frames from `kernel/src/logo_frames.rs` and exits on keypress —
  in text mode.

CODE-INSPECTED (code read, never run at boot):
- `kernel/src/framebuffer.rs` (576 lines) exists on main with
  `write_pixel`, `fill_rect`, `clear`, `scroll_up_pixels`, and
  `draw_glyph`, plus a pixel-console type with `write_str`. It is
  UNWIRED: nothing constructs it at boot, because the pinned
  bootloader (crate `0.9`, locked at 0.9.35) carries no
  framebuffer in BootInfo.
- The ribbon math reference, `js/logo-background.js`, runs today
  only in the web face.
- `os-build/KERNEL_FACE_TASKS.md` (sections A–H) exists as the
  unordered predecessor of this order.

UNIMPLEMENTED:
- Bootloader upgrade; framebuffer wiring; pixel boot screen;
  ribbon drawn by the kernel; window layer; shell in a window;
  PS/2 mouse; compositor; graphical dashboard; the KF-08
  graphics-failure fallback. The kernel today draws text only
  (VGA text mode).

## Blockers and risks on record

- Two bootloader-upgrade attempts have already failed (bootloader
  0.11: std failure; 0.10.9: API failure; evidence on the
  `opencode/round7` branch). KF-01 starts from that evidence and
  is timeboxed with a hard fallback for exactly this reason: the
  route is chosen on paper, not yet proven on the Mac.
- The kernel compiles and boots only on Del's Mac (the sandbox
  cannot build it). Every proof in this order rides the OpenCode
  1 Mac lane, so Mac-lane availability sets the pace.
- Cargo.lock pin movement on the upgrade can break the proven
  bootimage flow; KF-01/KF-02 exist to catch that before any
  graphics code lands on top of a broken boot.
