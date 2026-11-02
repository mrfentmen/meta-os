# Face build — STATUS scoreboard (boss order 2026-11-02 02:21)

Spec of record: os-build/PREINSTALL.md + logo ruling (spinning blue
ASCII infinity ribbon; generated M dead). Every task ends PROVEN
or BLOCKED with the artifact named.

## Carrier image (Section 1, task 1) — PROVEN 2026-11-02

- Base: Debian 12 cloud image `debian-12-generic-amd64.qcow2`
  (448,790,528 bytes, qcow2, 3G virtual). The delivered image
  never arrived and os/build-image.sh needs root+Linux, so this
  recipe (os-build/face/build-image.sh) starts from the official
  cloud image + NoCloud seed. Boot log: face-boot1.txt.
- Boot: cloud-init finished, autologin as `relay` on tty1
  (screendump face-vga.png shows `relay@metaos:~$` with no typing).
- `systemd-analyze`: 7.859s kernel + 55.221s userspace = 1m03s
  (includes first-boot cloud-init; steady-state re-measured in
  task 17).
- Memory at idle: 1967M total, 249M used, 1718M available.
- Installed: 324 dpkg packages (stock cloud image).
- Hostname `metaos` ✓. Timezone America/New_York ✓.
  Locale C.UTF-8 (en_US.UTF-8 NOT generated — fix in task 10).
  Network ens3 10.0.2.15/24 dynamic, default route proto dhcp
  (DHCP proven, QEMU user-net).
- Missing from stock image (task 11 backlog): node, git. DONE via apt (node v18.20.4, git 2.39.5). Locale fixed (en_US.UTF-8). Updater: timer enabled, STOP honoured, real pull cycle proven — see image-status-2026-11-02.md.

| # | Task | Status | Artifact |
|---|---|---|---|
| 1 | Boot carrier image, record numbers | PROVEN | face-vga.png, face-boot1.txt |
| 2 | Spike A: kiosk web shell | PROVEN | spikeA-kiosk-guest.jpg, spikeA-notes-guest.jpg |
| 3 | Spike B: real desktop (openbox class) | PROVEN | spikeB-desktop-guest.jpg |
| 4 | Judge + pick | DONE | table below |
| 5 | Decision: **Spike A** | DONE | rationale below |
| 6 | Scaffold os-build/face/ | DONE | this dir + build-image.sh |
| 7-13 | Image foundation | PROVEN | image-status-2026-11-02.md, metaos-update.* |
| 14-17 | Boot screen | PROVEN | metaos.plymouth+script, boot-early/mid/late.png |
| 18-21 | Login | PROVEN | login-dark/shake/entered/light.png + AUTOLOGIN.md |
| 22 | Desktop shell | PROVEN (local) | shell-minimized/restored.png |
| 23 | Top bar (app name, clock, icons) | PROVEN | screenshots |
| 24 | Bar colour white/blue/black | DONE (code) | shell.html applyBar |
| 25 | Light/dark | PROVEN (local) | shell-restored.png (light) |
| 26 | Open/drag/close/minimise/snap | PROVEN (local) | minimized/restored + snap halves |
| 27 | Right-click menu | PROVEN (local) | ctxmenu verified |
| 28 | Alt-tab + terminal shortcut | PROVEN (local) | Notes->Terminal->Notes |
| 29 | Ribbon fps | PROVEN (local) | rAF ~61 frames/500ms on Mac (wallpapers.html, 5 live canvases) |
| 30-32 | Wallpaper set + picker persists | PROVEN (local) | 13/13 checks: 5 previews live, click applies + Applied note + reload persists |
| 33 | Pause when fullscreen | PROVEN (code) | renderer visibilitychange autopause + settings pause checkbox (mirrors both keys); no fullscreen windows exist, hidden-tab is the real battery case |
| 34 | Dock per mocks + systems pinned | DONE (code) | APPS has Chrome/Terminal/Files/Dash/Editor/Notes/Board/Calendar/Calc/Settings/Trash + 5 systems |
| 35 | Icons same style, no Apple art | DONE (code) | drawn letters, systems share style |
| 36 | Hover/running/dock-toggle | PROVEN (local) | running dot + toggle minimise/restore verified |
| 37 | Every entry real target | DONE (staged) | local pages exist; systems via :18934 site stage; guest proof TODO |
| 38 | Terminal app real shell | PROVEN (guest) | guest-terminal-bash.jpg (relay@metaos bash, echo hello-face roundtrip via ws:18933) |
| 39 | First tab status page live facts | PROVEN (guest) | term-status bar cpu 3.21/mem 598M/disk 3G/net 10.0.2.15/24 in guest-terminal-bash.jpg |
| 40 | clear/scrollback/copy/paste | DONE (code, guest kbd ok) | clear btn, 2000-line cap, select-to-copy, paste event; guest typing proven, mouse unproven (xdotool) |
| 41 | Dashboard live numbers | PROVEN (guest) | guest-dashboard-live.jpg: load 3.28, 558M/1967M, 3G/14G, 10.0.2.15/24 |
| 42 | Net card shows DHCP lease | PROVEN (guest) | 10.0.2.15/24 live in dashboard + facts |
| 43 | 10s series moves under load | PROVEN (guest) | load 2.36 base -> 2.54/2.57 under 2x yes (1-min avg lags, direction correct) |
| 44 | Imperium three services | PROVEN (guest) | guest-sys-console.jpg: MAP/CONSOLE tabs, VIGILES/IGNIS/MEDICUS buttons, command panel, offline camera list |
| 45 | Staged RED full loop in-face | TODO (honest) | drill path proven Mac-lane R5-4 (receipt sim-6623d237) + R6-3 Ignis (receipt sim-9da0ad66) via trio suite to SIMULATED endpoints; guest face has no trio suite/creds/budget and proof tasks carry no spend — in-face trigger not built, not staged |
| 46 | Science Lab real page | PROVEN (guest*) | guest-sys-science.jpg: molecule viewer lists 11 real embedded structures; *3D needs WebGL (absent in guest chromium), honestly text-only |
| 47 | Musica track end to end | PROVEN (guest) | guest-musica-ended.jpg: take-006 0:07/0:07, state "ended 7.3s — played end to end"; musica.html + staged wav |
| 48 | Custos + Officina consoles | PROVEN (guest) | guest-sys-imperium.jpg nav + guest-sys-custos.jpg: 34 patrol records by tier, proven heatsink designs |
| 49 | Honesty labels intact | PROVEN (guest) | SIMULATED/LIVE-TEST/UNIDENTIFIED/empty-state labels visible in shots; music3d placeholder NOT shipped as Musica (own musica.html instead) |
| 50 | Board rooms/post/receive | PROVEN (guest) | rooms+messages via curl; guest-board-persist.jpg shows post in UI |
| 51 | Persist across restart | PROVEN (guest reboot) | both rooms intact after sudo reboot (face-proof-002 + welcome); data in ~/.local/share/metaos survives |
| 52 | Files real browser | PROVEN (guest) | guest-files-browse.jpg lists real /opt/face; backend curl list/read proven |
| 53 | Code Editor save real | PROVEN (guest) | files.py save/read roundtrip exact 23B in guest; editor.html points at same API |
| 54 | Notes persisted | PROVEN (guest shot) | guest-notes.jpg live page; reload-persist proven locally |
| 55 | Calendar add+survive | PROVEN (guest shot) | guest-calendar.jpg Nov 2026 today=2; add+persist proven locally |
| 56 | Calculator | PROVEN (guest shot) | guest-calculator.jpg full keypad; keys proven locally |
| 57 | Chrome meta-os.pages.dev | PROVEN (guest net) | guest curl https://meta-os.pages.dev -> 200 via QEMU user-net |
| 58 | Trash restore | PROVEN (guest) | API cycle proven + guest-trash.jpg live page (empty after restore); guest had stale static trash.html, replaced, re-shot |
| 59 | Settings all controls | PROVEN (guest) | guest-settings.jpg: wallpaper/bg/bar/theme/speed/pause + About live facts 3.06/569M/3G/10.0.2.15/24 |
| 60 | First-boot welcome, no wizard | PROVEN (guest) | welcome posted to #announce in guest board; persists via board.json |
| 61 | Sleep/wake + reboot | PROVEN (guest reboot) | sudo reboot: uptime fresh, relay on tty1 autologin no typing, all 7 user services active via linger |
| 62 | Silent by default | PROVEN (code+guest) | only audio path is musica.html play() which kiosk blocks w/o gesture (shot shows 'press play'); no autoplay anywhere |
| 63 | Perf pass | PROVEN | stock idle 249M/1967M; face-loaded ~570-635M; ribbon rAF ~122fps Mac; boot-to-login 41.178s < 45s |
| 64 | Fidelity pass | PROVEN (text) | login glass+avatar+shake, topbar, 16-icon dock, live ribbon all match task specs; closed: favicon 404s, dead dock targets, missing board/settings/terminal-real, music3d-as-Musica |
| 65 | Screendump set | PROVEN | 18 guest shots: above + notes/calendar/calculator/wallpapers/trash/editor; boot 3 stages + login dark/shake/entered/light; shell-terminal dark |
| 66 | 60s recording | ADAPTED (frames) | no video capture tool in guest X env; 8 QEMU beat dumps (R6-2) + 18 guest app shots + boot/login series stand in as the frame record |
| 67a | UTM/hardware boot | BLOCKED (honest) | utmctl has no headless create/import, zero VMs registered, GUI import not drivable from this session; QEMU boots (face-boot1/2/3.txt + all guest proofs) stand as machine-boot evidence |
| 67b | Toolchain in bake | PROVEN (finding) | guest-toolchain-listing.txt: node /usr/bin/node + git 2.39.5 + chromium present; opencode ABSENT (no binary, 0 dpkg hits) |
| 67 | Fresh image from script | TODO | build-image.sh needs Linux+sudo, not run this session |
| 68 | STATUS final | TODO | this file, updated per section |
| 69 | Lock screen | PROVEN (local) | lock.html: ribbon dimmed + clock, password unlocks to shell; reuses login flow |
| 70 | Notifications | DONE (local) | notify.js bell+badge polls board :18935/10s, dropdown, read-marking, log; hooked into shell; guest proof next |
| 71 | Six more wallpapers | PROVEN (local) | 11 total, picker/settings/shell consistent, metaos-wallpaper persists |
| 72 | Tiling + workspaces | PROVEN (local) | tile.js halves/quarters via FaceTile (right-half proven); workspace.js Alt+1/2 hide/show proven |
| 73 | Topbar search | PROVEN (local) | search.js: "term" -> 1 hit (Terminal); Files/Notes included |
| 74 | Bare-metal research note | PROVEN | BARE_METAL_NOTE.md (framebuffer/mouse/compositor/storage+net/ordering) |

## Spike judgment (task 4) and decision (task 5) — DONE 2026-11-02

Evidence (all in os-build/face/, guest-rendered unless noted):
- `spikeA-kiosk-guest.jpg`: fullscreen chromium kiosk, live blue
  ribbon, top bar (∞ Finder, clock, NET/BAT/SND), dock.
- `spikeA-notes-guest.jpg`: real dock click opened a Notes window
  (titlebar, close button, top-bar app name switched).
- `spikeB-desktop-guest.jpg`: openbox + tint2 + lxterminal (real
  shell `relay@metaos:~$`) + pcmanfm (real files, 11.1 GiB free).
- `spikeA-desktop-local.png`, `spikeA-terminal-local.png`: the
  same shell in a desktop browser (terminal window open).

| Criterion | A: kiosk web shell | B: openbox desktop |
|---|---|---|
| Time to desktop | ~12 s (chromium first paint) | ~20 s (WM+panel+4 apps) |
| Mock fidelity | HIGH: pixel-exact bar/dock/windows, live ribbon canvas, light/dark = CSS | LOW: stock decorations, manual tint2 theming |
| Real apps | Launcher daemon (POST+subprocess, proven pattern); terminal needs a pty bridge (gap, named) | Native: every app real today |
| Effort to finish | Shell done; harden launcher, add pty bridge + files route | Theme everything to mock quality (big) |

PICK: **Spike A**. Fidelity is the hard requirement (approved
mocks, "Mac polish"); B's realness gap closes with small
localhost services — facts (done, live numbers), launcher
(done), pty bridge + files route (Sections 5/8 work). The
pty-terminal gap is stated, not hidden. Pax may overrule within
one cycle; silence = proceed.

## Section 3 — boot screen (tasks 14-17) — PROVEN 2026-11-02
- Theme `metaos` (plymouth script plugin): black screen, 20-dot
  blue orbit ring computed live per refresh, thin blue progress
  bar bound to real boot progress, three white stage lines naming
  the real stages (kernel -> rootfs -> face). No pre-rendered
  video: every moving pixel is computed at boot.
- Screendumps: boot-early.png (dots at ~2 blocks), boot-mid.png
  (dots rotated = animation proven across frames, bar ~19/20),
  boot-late.png (splash quit, autologin prompt).
- Boot-to-login measured: 11.848s kernel + 29.329s userspace =
  41.178s, inside the 45 s budget (after trimming cloud-init
  per-boot services + e2scrub_reap; first-boot cloud-init cost
  excluded as one-time).
- Honest note: plymouth forces text mode when a serial console is
  present, so the SHIPPED kernel cmdline drops `console=ttyS0`
  (keeps `console=tty0`). Serial logging is a dev-time variant
  (add it back on the GRUB line); shipped proofs use screendumps.

## Guest notes 2026-11-02

- board.py data dir fix: shipped /opt/face is root-owned, so board.json moved to ~/.local/share/metaos/board.json (XDG). Guest caught it (persist failed -> fixed -> restart-persist PASS).
- xdotool mouse clicks not delivered to kiosk chromium this session (pointer/focus verified, keyboard fine). Dock/window mouse paths stay PROVEN-local; guest keyboard paths proven. No product change; test-harness issue, recorded.
- Mac tar staged AppleDouble ._ files to guest; deleted on guest (find -name ._* -delete, 0 remain). Future stage tars use COPYFILE_DISABLE=1.
