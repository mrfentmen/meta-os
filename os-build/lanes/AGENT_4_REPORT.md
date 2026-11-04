# AGENT-4 REPORT — 3D, About, agent pipeline, session, boot command

Branch: `agent-4`. No merge. No API key anywhere in this report or commit.

## Summary

Software WebGL works: the Science Lab molecule viewer and Music 3D both draw
real three.js scenes in `meta-app` windows (captures below), so no 3D fix was
needed and none was made. `about.html` is new: it shows live version, identity,
kernel, session and build date read from the machine at login, and it rendered
correctly inside the guest with values matching `/etc/os-release` field for
field. The agent pipeline is real end to end — submit, spawn, recorded run —
but every hosted agent I ran failed loudly within milliseconds on image-side
path/permission bugs, and 7 of 23 registry agents are drafts that refuse with
a reason. The image predates this checkout (its `session.sh` has no GL exports,
its dock script quotes the whole tile command into one word so every surface
tile skips, its registry still marks six research agents as drafts), so several
"repo is correct" findings read as "image is stale" findings. All numbers
below were measured; everything else is marked untested or skipped.

## 1. 3D diagnosis and measurement

### QEMU display backends (tasks 1-2)

```
$ qemu-system-aarch64 -display help
Available display backend types:
none
curses
cocoa
dbus
```

No `gl=on`, no GTK backend. Hardware/virgl 3D is impossible on this host.

### Mesa on the image (tasks 3-5, guest shell)

```
$ ls -l /usr/lib/aarch64-linux-gnu/dri/swrast_dri.so \
        /usr/lib/aarch64-linux-gnu/dri/virtio_gpu_dri.so
lrwxrwxrwx ... swrast_dri.so -> libdril_dri.so
lrwxrwxrwx ... virtio_gpu_dri.so -> libdril_dri.so
$ dpkg -l libgl1-mesa-dri | tail -1
ii  libgl1-mesa-dri:arm64  25.2.8-0ubuntu0.24.04.4  free implementation of the
OpenGL API -- DRI modules
```

### session.sh exports (tasks 6-7)

Repo `os-build/face/session.sh` lines 28-30 export all three variables.
**The image does not have them**: `grep -c LIBGL /opt/face/session.sh` → `0`
(image md5 `1576ce6d37ee4c8c4f51982c6d7a1edb`; baked before the exports
landed). Consequence, verified in-guest: the terminal shell, plank (PID 1616)
and its ancestors all lack the variables (`MARK::::END`,
`grep -a -o LIBGL_ALWAYS_SOFTWARE. /proc/1616/environ` → empty). For every 3D
proof below I exported the identical values by hand in the launching shell
(documented equivalent of what the repo's `session.sh` now does at login).

### WebKit (tasks 8-9)

`meta-app.py` sets `enable-webgl`, `enable-accelerated-2d-canvas`,
`hardware-acceleration-policy=always`, each in try/except. Guest WebKitGTK is
**2.52.6** (`dpkg -l libwebkit2gtk-4.1-0`, plus `WK2.52.6` from a gi version
query). Windows opened and WebGL rendered, so nothing threw.

### The model drew (tasks 10-12, 22)

Reproduce (guest shell; exports needed only because the image predates them):

```
export LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe \
       WEBKIT_DISABLE_DMABUF_RENDERER=1
meta-app --title Science \
  --url http://127.0.0.1:18934/labs/molecules/index.html \
  --width 1180 --height 780 &
```

First-try result: caffeine ball-and-stick, shaded spheres, legend,
`C8H10N4O2 — 194.19 g/mol — embedded JSON (24 atoms, 25 bonds)`.
Capture: `os-build/captures/3d-molecule-science-1180x780-2026-11-03.png`.
No fix was required, so no before/after pair exists — this capture is both.
Reopened in a second boot: rendered again within ~25 s (task 39).

### Measurements (tasks 28-34)

No fps instrumentation exists in the shipped stack (`GALLIUM_HUD=fps` printed
nothing to the terminal; WebKit spawns the GL process with stderr elsewhere),
so fps is **not reported**. Measured instead, all in-guest:

| What | Command | Result |
|---|---|---|
| Load to first render, 1180×780 | wall clock launch→capture | ≤25 s (boot 2), ≤45 s (boot 1) |
| Render cost, 1180×780, caffeine auto-rotating, 24 atoms | `ps -o pid,pcpu,etime -p 3083` | **168 % of one core over 01:51** |
| Render cost, 1920×1040, same scene | `ps -o pid,pcpu,etime -p 3239` | **140 % of one core over 02:10** |
| Static 2D page (About) | same, PID 2093 | **0.0 % over 30:04** |
| Music3D, visibly stopped | same, PID 2883 | **223 % over 04:57** |
| Idle desktop, apps closed, 30 s settle | `cat /proc/loadavg`; `free -m` | load **7.56 7.78 4.12** (residual from minutes of software rendering; instantaneous top then showed Xorg+wallpaper ≈26 %); mem **1035 used / 3905 total** |

`%CPU` here is `ps` lifetime average (400 % = 4 cores). Atom counts read from
the image's own data files (`/opt/face-site/labs/molecules/data/*.json`):
acetone 10, aspirin 21, caffeine 24, ethanol 9, glucose 24, methanol 6,
naphthalene 18, theobromine 21, toluene 15, urea 8, water 3. Default view is
caffeine (24); the heaviest available molecule is glucose (24, tie).

What this means: any live three.js scene costs roughly 1.5–2 cores of llvmpipe
whether the window is 1180 or 1920 wide — the size barely matters, the
renderer does. The old advice ("choppy at 1920×1080, smooth at ~900 px") is
**neither confirmed nor refuted**: I have no fps numbers, only CPU. Visually
both sizes animate (rotation visibly progresses across timed captures) and a
second window does not break the first (Science + Music3D + About + Agents all
drew at once, desktop stayed responsive). Music3D burning 223 % while its own
status line says "Stopped" is a real bug for agent-2's lane (continuous render
loop, task 42 failed with cause).

### Music3D + guard (tasks 35-39)

- `labs/music3d/index.html` draws in `meta-app` the same way (capture
  `3d-music3d-1180x780-2026-11-03.png`). Same stack, same behaviour.
- Guard proven with `.../labs/molecules/index.html?force2d=1`: the page prints
  exactly *"3D unavailable in this browser (no WebGL context). Structures
  cannot be drawn — nothing is faked in their place."* plus the text-only
  structure list (capture `3d-guard-force2d-2026-11-03.png`). Visible, not
  hidden behind a canvas.
- The guard probes `webgl2 || webgl` (page source); the live render took the
  WebGL path, the forced path took the notice. Both directions observed.
- Canvas is crisp at 1920×1040, not stretched or blurry (close-up crop
  inspected). Drag-to-rotate was **not** tested (auto-rotate motion is what's
  proven).

### Five-sentence diagnosis (task 24)

The Mac's QEMU cannot do hardware 3D at all, so the browser inside the OS has
no graphics card to talk to. The OS image does ship Mesa's software 3D driver,
which draws every 3D triangle on the regular processor instead — slower, but
real. The checkout already asks for exactly that in two places: the login
script exports three environment variables, and the app window turns WebGL on.
The booted image predates both changes, so I set the same three variables by
hand and the molecule drew on the first try. Expect it to work and expect it
to cost CPU: roughly one and a half cores per 3D window, at any window size.

## 2. about.html (tasks 51-80)

New file `os-build/face/about.html`, served on 18900 (`curl` → `CODE.200`;
`face-http` is `python3 -m http.server` rooted at `/opt/face`, and
`provision.sh --root` copies `face/.` there, so the page lands on 18900 at the
next build — same mechanism as every other page). Fixed contract for agent-1's
tile: `meta-app --title About --url http://127.0.0.1:18900/about.html`
(repo `meta-desktop.sh` line 265 already references exactly this).

Live values come from `/opt/face/about.json`, written at every login by a new
best-effort step in `session.sh` (my edit): it parses the live
`/etc/os-release`, `uname -r`, the session name (from the xsessions entry when
present, else `Meta OS Desktop`) and the build date (mtime of `/etc/os-release`
— the debrand bake time — falling back to the script's own mtime, then to
`unknown`; never a guess). If the file can't be written the page falls back to
the facts backend (18932, live distro+kernel) and otherwise shows a visible
failure line instead of stale values. A missing/unreadable os-release writes
`{"error": ...}` so the page degrades loudly (proven below).

Guest proof (all inside the booted OS):

- Ran the repo's `session.sh` in a subshell (stub `startxfce4`): `SESSION-RC-0`;
  `/opt/face/about.json` written (guest `/opt/face` is user-writable).
- Side-by-side (capture `about-json-vs-osrelease-2026-11-03.png`):
  json `pretty/metaos/ribbon/1.0/6.8.0-147-generic/Meta OS Desktop/2026-09-06`
  matches os-release `PRETTY_NAME="Meta OS 1.0 (Ribbon)"`, `ID=metaos`,
  `VERSION_CODENAME=ribbon`, `VERSION_ID="1.0"` exactly. Kernel
  `6.8.0-147-generic` is the stock base kernel — claimed as such.
- Liveness (capture `about-liveness-changedos-2026-11-03.png`): with a modified
  copy (`PRETTY_NAME="ChangedOS 1.0 (Ribbon)"`) the regenerated JSON reads
  `"pretty":"ChangedOS 1.0 (Ribbon)"` — the mechanism reads live, nothing is
  hardcoded. (Build date moved to that file's mtime, further proof.)
- Missing file: `{"error":"os-release missing or unreadable at /tmp/nope-file"}`,
  login still exits 0.
- Rendered in `meta-app` (capture `about-page-1180x780-2026-11-03.png`): all
  seven rows, the what-it-is paragraph, "Read live at … (generated on this
  machine …)". Says Meta OS, never Ubuntu (`grep -ci ubuntu` → 0). No
  rewritten-kernel or new-base claim — the paragraph says Debian-family base
  plus stock kernel. No external assets, no URL shown on screen, no
  placeholder text.

Not proven: the failure box visually rendered with both backends down (code
path reviewed, JSON side proven); fit at 900×600 (page is max-width 640 and
short — fits by construction, not captured); the dock tile itself (agent-1's
file; the image predates the tile lines).

## 3. Agent pipeline inside the guest (tasks 81-110)

- `metaosd` running, port **18940** (`proof_session.sh` 9/9 PASS incl.
  `/status` and `/agents`; journal: `metaosd on 127.0.0.1:18940
  state=/home/meta/.local/state/oc2-agent queue=http://127.0.0.1:8935`;
  unit description `metaosd agent API 18940`).
- `/usr/local/bin/meta-ask` exists. `meta-ask --list` in-guest: **16 live,
  7 drafts** (image registry; the repo checkout has 24 entries with 1 draft —
  the image is older).
- Drafts (all 7, each refuses with its reason): imperium-patrol,
  mathematics-researcher, chemistry-researcher, biology-researcher,
  physics-researcher, hypothesis-generator, statistician. (Repo checkout has
  only imperium-patrol as draft — six research agents gained real commands
  since the image baked.)
- Live submit, `watch`: `meta-ask "agent-4 proof run please drain the board
  once" --agent watch` → `job ask-1793742251 is on the board at
  /home/meta/.local/state/oc2-agent/jobs`. Run record (result file):
  **run `watch-mw17tpki`, agent `watch`, finishedAt
  `2026-11-03T21:44:14.597Z`, exit code 1**, ledger
  `runs/watch-mw17tpki/ledger.jsonl`. Job file says `submittedAt
  2026-11-03T21:44:11.538Z` → submit-to-recorded-run **~3 s**. First attempt
  ran as `watch-mw17to0r`, then the relay retried as `watch-mw17tpki` — retries
  are recorded, not hidden.
- The run is real and loud: ledger `spawn` shows the true command
  (`/usr/bin/node /usr/share/metaos/agent/agents/watchman.mjs --once`);
  `stderr.log` shows the true failure: `Error: EACCES: permission denied,
  mkdir '/usr/share/metaos/agent/agents/jobs'` (watchman defaults its root to
  the payload dir, which `meta` cannot write); `stdout.log`:
  `run failed: exit 1 signal null after 82ms`. Nothing canned, nothing silent.
- `officina-faber`: job `ask-1793742535`, runs `mw17zru1` + retry `mw17ztds`,
  both exit 2 in ~13 ms: `python3: can't open file
  '/usr/share/metaos/agent/os/worlds/officina/runtime/design_loop.py'` — the
  `repo:` prefix resolves against the payload dir, and `os/worlds` is not
  there. Same class of image-side bug.
- `research-director` (no-key probe): job `ask-1793742944`, run
  `research-director-mw188jtu`, exit 2 in 13 ms — same missing-file failure
  (`.../os/worlds/science-lab/hosted.py`). The model-key path was never
  reached; it could not have succeeded anyway (key file root-only, no
  network). No key was used, none was written anywhere.
- Refusals, all exact text on screen: draft →
  `submit: statistician has no program yet (draft): no program in this repo;
  ... nothing would run` (RC-1); empty →
  `meta-ask: error: orders are required (or use --list)` (RC-2); duplicate
  (same-second resubmit) → `submit: job already on the board: ask-1793742837`.
  None resembles success.
- Journal: `oc2-watchman.service - MetaOS agent layer: relay watchman (rings
  the bell for named jobs)`; `relay-watchman: watching
  /home/meta/.local/state/oc2-agent/jobs`. Human-readable descriptions.
  (`meta-agent-status`, named in the submit receipt, is **not installed** —
  `command not found`.)
- Agents app (`meta-agents`, screenshot): lists 24 agents with correct
  (draft) marks; order box + Submit present. Its run pane showed no runs at a
  glance; the runs are served by its own backend (`GET /runs` returned
  `research-director-mw188jtu`, 13 ms, exit 2, etc.) and exist as files.
- Scoreboard: 16 live, 7 drafts (named above), 4 jobs accepted
  (watch/proof, officina, research-director, dup-probe first submit),
  0 completed successfully, 6+ failed runs recorded with causes. A judge
  clicking for a minute finds: a desktop, an About page with true facts, 3D
  pages that draw, an Agents app that lists agents and accepts orders — and
  every placed order failing loudly on payload paths/permissions.

## 4. Session resilience (sandbox + guest)

Host sandbox (stub `systemctl`/`plank`/`startxfce4`/`sudo`, `sh -n` clean):
ends in `exec startxfce4` (task 111). `meta-desktop.sh` missing → readable
fallback line, reaches the end (112). `face.target` + `metaosd` + livebg all
failing (stub RC=1) → three readable log lines, still reaches the end
(113-116; the static-wallpaper visual itself not observed). `plank` absent
from PATH → "plank missing — desktop still works, no dock", reaches the end
(117). Missing os-release → `{"error":...}` JSON, exit 0 (66/67). Every
`say()` line carries a UTC timestamp (120); child-command output is captured
raw. One real bug found and fixed: empty `stat` output bypassed the `||`
fallback (`cut` exits 0 on empty input) — now guarded with `-n`.

Guest: log shows this boot's `face.target started`, agent hook
(`oc2-queue/trio/patrol/health/watchman` all started), plank scheduled,
kiosk off — all timestamped, all readable by the owning user (118-121).
Panel + dock + wallpaper are all visible in the first desktop capture before
any app opens (123). Plank starts 2 s after login, after the WM (124);
wallpaper coexists with the WM in every capture (125). Unit descriptions are
human sentences (133). Wallpaper and session are independent units with
`|| say` guards (134). Not tested: second login/logout cleanliness and zombie
check (126-128 — one session only, logout would kill the only shell);
login-to-panel under 8 s (122); "no unit enabled twice" (132).

## 5. show_os.sh (host)

- `sh -n` passes (149). Unknown flag → exit 2 with usage. Missing image →
  `show_os: missing image …` + how to fix (148). Works from any cwd (147).
- Single-VM guard **proven**: with a fake `qemu-system-aarch64 … <image>`
  process present, output was `show_os: a VM is already running on
  <image> — closing it first`, the fake was killed, boot proceeded (137).
- Extraction **proven** standalone (same function): ISO →
  `BOOTDIR/vmlinuz` + `BOOTDIR/initrd.img`, the exact names the boot expects
  (138-139).
- `--persist` is the only writer (`SNAP="snapshot=on"` default; both guest
  boots here left the image untouched) (140).
- Audio: this QEMU has `coreaudio` (probed), so the HDA card is attached; the
  `META_NO_AUDIO=1` and no-backend branches are read-verified, the silent-boot
  path not executed (141).
- `--headless 210` **proven end to end**: killed my interactive VM via the
  guard, booted, `show_os: PASS: framebuffer has 5626 distinct colours
  (desktop drew)`, `show_os: stopped`, exit 0, no QEMU left (136, 143-145).
- Serial path printed before boot (`show_os: serial=/tmp/metaos-show.log
  mode=headless`) (146). Failed-boot log tail **untested** — every boot
  succeeded (142).
- No changes to `show_os.sh` were needed; none made.

## 6. Task table, honesty lists, done

Completed: A 1-18, 20-22, 24-25 (19 skipped: compositor-disable last resort —
nothing broken); B 28-40, 42-49 (26-27 need no fix/commit; 41 drag untested;
44 no fps-baseline; 50 N/A); C 51-64, 66-74, 76-79 (65 proven; 68 at 1180,
900×600 untested; 75 author's assessment; 80 this commit); D 81-97 (minus
queue-port liveness), 100-109 (98-99 stop/restart skipped — relay left
running deliberately); E 111-121, 123-125, 129-131, 133-134 (122, 126-128,
132 skipped); F 136-141, 143-149 (142 skipped); G 151-156 here, 157/159
below. Roughly 110 done, ~15 partial, ~12 skipped with reasons, 3 N/A.

Claims I am NOT making: no fps or "smooth" claim at any size (CPU only); no
model response was ever produced or presented; no key was used, read, or
written; no boot-time or login-time numbers; no second-login/logout
cleanliness; no queue-port (8935) liveness; no drag-rotate test; no 900×600
About capture; no failure-box render capture; no failed-boot log-tail test.

What a judge could ask that this OS cannot answer yet: GPU 3D (software
only, ~1.5 cores/scene); a thinking agent run (key unreadable + no network +
payload path bugs); Messages/Aegis/Boards tiles on the booted image (repo
has the tiles, image predates them; bus.html and the Aegis page are not on
the image); About from the dock (same staleness); SSH or any inbound/guest
network (NIC unmanaged, no netdev in the standard boot); an fps number for
the 3D scenes; why Music3D burns 2+ cores while stopped.

Definition of done: molecule capture + CPU numbers + reproduce command
(§1); about.html values == os-release, side by side (§2 + captures);
run records + 16/7 live/draft with names (§3); this report. `git status`
for this commit shows only agent-4's files (below). No merge, no rebase,
no push. `main` untouched.
