# Wave 2 Section 3 (tasks 21-30) — face verification (2026-11-02, freshly merged build in /tmp/wave2/os-build/face)

## Login flow shots
- `login.html`: demo login, any non-empty password -> `shell.html`; empty -> shake animation. Hint text declares demo.
- Shots present (5): `login-dark.png`, `login-light.png`, `login-entered.png`, `login-shake.png` (all 1280x720 JPEG bytes under `.png` names — mislabeled extension), `login-local.png` (true PNG 1200x741).
- `lock.html` + `guest-lock.jpg` (24 KB): dimmed ribbon + M card + password. Lock/unlock proven locally per STATUS.
- Boot->login->desktop chain: `boot-early/mid/late.png`, login set above, desktop `guest-desktop-full.jpg` (112 KB) + `guest-desktop-dock.jpg` (79 KB). No single 3-shot carrier sequence, but all stages shot.

## Wallpaper set count
- `wallpapers.html` W array = **11 ids**: ribbon-blue/dark/light, comet-dense, wave-slow, ribbon-frost, ribbon-midnight, ribbon-ghost, comet-sparse, comet-pale, wave-fast. Click-to-apply -> localStorage `metaos-wallpaper`, reload persists, live canvas previews.
- `settings.html` wallpaper `<select>` lists same 11. `shell.html` WALLPAPERS map has same 11. Consistent.
- `guest-wallpapers.jpg` (40 KB) present.

## Per-app verdicts (Terminal Files Dashboard Editor Notes Calendar Calculator Settings Trash)
- Terminal: REAL (ws bridge). `shell.html` kind=term -> `buildTerminal` -> ws `127.0.0.1:18933` (`ptyd.py`, 11 KB) + live facts status bar (`:18932`). `guest-terminal-bash.jpg` (75 KB, echo roundtrip + status cpu/mem/disk/net) + `guest-terminal-connected.jpg` (74 KB, [connected]).
- Files: REAL. `files.html` -> `files.py :18936` (list/read/save/mkdir/trash). `guest-files-browse.jpg` (81 KB, /opt/face listing).
- Dashboard: LIVE. `dashboard.html` fetches `:18932/facts` every 2s, 4 cards + stamp. `guest-dashboard-live.jpg` (34 KB: load 3.28, 558M/1967M, 3G/14G, 10.0.2.15/24). `facts.py` stdlib, /proc+shutil.
- Editor: REAL. `editor.html` -> same `:18936` read/save API, `?path=` deep link from Files. `guest-editor.jpg` (33 KB). STATUS claims 23B save/read roundtrip in guest.
- Notes: OPENS, browser-only persist. `notes.html` (595 B) localStorage `metaos-notes`. `guest-notes.jpg` (28 KB). No disk persistence (by design, labelled "saved in this browser").
- Calendar: OPENS, browser-only persist. `calendar.html` month grid + prompt() add, localStorage, today highlight. `guest-calendar.jpg` (34 KB, Nov 2026 today=2).
- Calculator: OPENS, local. `calculator.html` full keypad (C/neg/%/ops), keyboard support. `guest-calculator.jpg` (38 KB).
- Settings: REAL controls + live facts. `settings.html`: wallpaper(11)/bg/bar/theme/speed/pause -> localStorage (+ legacy bridge keys), About facts from `:18932` + Refresh, Apply/Reset. `guest-settings.jpg` (53 KB: facts 3.06/569M/3G/10.0.2.15/24). Note says "Reopen the shell to apply" for some keys; change events also save live.
- Trash: REAL. `trash.html` -> `:18936` trash/restore/delete/empty, `~/.local/share/Trash/files`. `guest-trash.jpg` (27 KB, empty after restore per STATUS API cycle).

## Systems dock entries
- Dock = 16 entries: 11 apps (Chrome/Terminal/Files/Dash/Editor/Notes/Board/Calendar/Calc/Settings/Trash) + sep + 5 systems (Imperium/Science/Musica/Custos/Officina). No Aegis/Nervus entries.
- Targets: Imperium `127.0.0.1:18934/surfaces.html`, Science `.../labs/molecules/index.html`, Musica `musica.html` (face-local), Custos `surfaces.html#board-custos`, Officina `.../index.html`. Systems served outside face dir (repo root services), Musica local.
- Shots: `guest-sys-imperium.jpg` (65 KB), `guest-sys-console.jpg` (61 KB, MAP/CONSOLE VIGILES/IGNIS/MEDICUS), `guest-sys-science.jpg` (48 KB, 11 structures, WebGL absent noted), `guest-sys-custos.jpg` (84 KB, 34 patrol records), `guest-musica-ended.jpg` (45 KB, take-006 0:07 end-to-end), `guest-logo-studio.jpg`, `guest-red-receipt.jpg` (SIMULATED receipt posted to board).

## Board persist
- `board.html` (rooms + polled log + post form) -> `board.py :18935`, JSON persist to `~/.local/share/metaos/board.json` (XDG, falls back to file dir). Survives restart by design.
- `guest-board-persist.jpg` (29 KB) + STATUS: rooms+messages via curl, both rooms intact after `sudo reboot` (face-proof-002 + welcome). PASS.

## Settings controls (recap)
- 6 controls (wallpaper select 11, bg color, bar, theme, speed range, pause checkbox) + Apply/Reset + About live facts + Refresh. All write localStorage; facts poll 2s. Guest shot proves live values. PASS.

## Dashboard live (recap)
- Labelled "live, this machine", 2s refresh of cpu/mem/disk/net from facts.py. Guest shot shows real numbers; STATUS: 10s series moves under load (2.36 -> 2.54/2.57). DHCP lease 10.0.2.15/24 shown. No RECORD/LIVE card split — single live view. PASS as live.

## Gaps / honesty notes
- 4 login `*.png` are JPEG bytes (rename or re-encode).
- Notes/Calendar/localStorage-only persistence is per-browser, not disk; labelled in-page for Notes ("saved in this browser"), not for Calendar.
- `login-README.txt` (demo password) + `AUTOLOGIN.md` + `BARE_METAL_NOTE.md` present; STATUS scoreboard rows 21-30 all PROVEN except 66 (frames-not-video), 67a (UTM BLOCKED), 68 TODO.
