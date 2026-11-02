# Wave 2 Section 3 (tasks 21-30) — face verification (2026-11-02, tip 2904e743 worktree /tmp/wave2)

Scope: `os-build/face/` on disk vs `git ls-files` (all files below are committed unless noted). Spec: `OPENCODE1_TASKS_WAVE2.md` Sec 3 + `/tmp/wave2/OPENCODE_FACE_BUILD.md`.

## Task verdicts
- 21 (FACE_BUILD s6+ w/ screenshot each): FAIL. Code exists for S3/S4/S5-part/S6/S7/S8-part/S9/S12-part; committed screenshots exist only for S3-boot, S4-login, S5-spikes. No section-landing screenshot for S6, S7, S8, S9, S10, S11, S12, S13, S14.
- 22 (login flow: boot log + 3 shots boot->login->desktop): PARTIAL. Boot log `os-build/logs/face-boot1.txt` (committed) is serial-console to getty autologin, not face kiosk. Login has 5 shots (`login-dark.png`, `login-light.png`, `login-entered.png`, `login-shake.png`, `login-local.png` — note: first 4 are JPEG bytes under `.png` names). Desktop-in-guest `spikeA-kiosk-guest.jpg` exists, but no single committed boot->login->desktop sequence (log + 3 tied shots) in carrier image. `face-vga-autologin.png` = console `relay@metaos`, not graphical login.
- 23 (wallpapers live, shot each): PARTIAL. `wallpapers.html` implements 5 live canvas previews (ribbon-blue/dark/light, comet-dense, wave-slow), click-to-apply to localStorage only. Zero `wallpaper-*.png` committed anywhere. No fps measurement, no picker screenshot.
- 24 (dock apps per-app verdicts): FAIL as a set — no verdict list in `STATUS.md`, no per-app screenshots except Notes. See table.
- 25 (systems w/ real records, placeholders flagged): FAIL. Dock has Imperium/Science/Musica/Custos/Officina (no Aegis, no Nervus entries); all point at repo-root `surfaces.html`/`index.html`/`logo-studio.html`, not face-local pages. No system-app screenshot in `face/`; no placeholder-flag list in `STATUS.md`.
- 26 (board persists across reboot): FAIL. No `board*.html` in `face/`; `STATUS.md` rows 50-51 = TODO; zero board screenshots/logs.
- 27 (settings every control applies + survives reload): PARTIAL. `settings.html` (bar/theme/speed/pause -> localStorage, note says "Reopen the shell to apply" = not instant). No About/version/hash/facts section (FACE_BUILD 59). No apply/persist proof, no screenshot.
- 28 (dashboard LIVE vs RECORD labelled): PARTIAL. `dashboard.html` + `facts.py` (`/facts` live cpu/mem/disk/net, 2s refresh) is LIVE-capable and proven over HTTP in `image-status-2026-11-02.md`; but no RECORD/LIVE card separation in the page, no 10s load-move series, no dashboard-open screenshot in `face/`.
- 29 (perf: boot-to-desktop time, >2s apps named): FAIL. Only number is first-boot `7.859s kernel + 55.221s userspace` (cloud-init included, in `STATUS.md` + image-status). No boot-to-desktop (kiosk) timing, no per-app open timing, no fps under window.
- 30 (status file current per app): FAIL. `face/STATUS.md` scoreboard still TODO for rows 14-17 through 65-68; only spike judgment (tasks 1-5) filled in.

## Sections lacking committed screenshots (in `face/`)
- HAVE: S3 boot (`boot-early.png`, `boot-mid.png`, `boot-late.png`, `boot-theme-live.png` — but stored in `face/`, spec said `os-build/captures/`); S4 login (5 shots above); S5 shell spikes (`spikeA-desktop-local.png`, `spikeA-kiosk-guest.jpg`, `spikeA-terminal-local.png`, `spikeB-desktop-guest.jpg`, `face-vga-autologin.png`).
- LACK: S6 wallpapers (0 shots); S7 dock (0); S8 terminal-real (0; only local echo-term shot); S9 dashboard-open (0 in `face/`); S10 systems (0 in `face/`); S11 board (0, no app); S12 everyday — except `spikeA-notes-guest.jpg` (Notes open in guest), Files/Editor/Calendar/Calculator/Settings/Trash have 0 open-shots; S13/S14 proof pack (no dark/light desktop pair in `face/`, no Settings/picker shots, no 60s recording). NOTE: `os-build/captures/face-web/` (committed) has `desktop-apps.png`, `desktop-dark.png`, `desktop-light.png`, `login.png` — web captures, not `face/`-dir artifacts, untied to any Sec-3 claim.

## Per-app verdicts (task 24: Terminal Files Dashboard Editor Notes Calendar Calculator Settings Trash)
- Terminal: STUB. `shell.html` kind=term = local echo box (typing appends, Enter = newline, no shell). Real shell only via `ptyd.py` raw-TCP 127.0.0.1:18933 + `pty-test.html` contract page (browser cannot use raw TCP;_HELLO no WS bridge). `launcher.py` ALLOW includes `lxterminal` (native behind browser, unproven from face shot).
- Files: NATIVE-ONLY, no face page. No `files.html`; dock kind=launch `pcmanfm`. Only evidence is Spike B `spikeB-desktop-guest.jpg` (openbox+pcmanfm native), not Spike A face.
- Dashboard: LIVE-CAPABLE, unproven visually. `dashboard.html` fetches `/facts` (`facts.py`); HTTP 200 + live numbers proven in image-status log, but no open-window screenshot in `face/`, no refresh/move series.
- Editor (Code Editor): MISSING face page. No `editor.html`; dock kind=launch `mousepad`. No screenshot, no save/diff proof.
- Notes: OPENS, persistence UNPROVEN. `notes.html` (localStorage `metaos-notes`); `spikeA-notes-guest.jpg` proves guest open + top-bar rename. Reboot survival not proven (browser profile, not a disk file).
- Calendar: UNWIRED. `calendar.html` exists (localStorage `metaos-calendar`, prompt() add, working month grid) but dock maps Calendar -> launch `orage`, NOT `calendar.html`. No screenshot.
- Calculator: UNWIRED. `calculator.html` exists (working ops, keyboard incl Backspace/neg/%) but dock maps Calculator -> launch `galculator`, NOT `calculator.html`. No screenshot.
- Settings: PARTIAL. `settings.html` writes localStorage (bar/theme/speed/paused); shell requires reopen; no instant-apply, no reload/reboot proof, no About/machine-facts block, no screenshot.
- Trash: PLACEHOLDER (self-declared). `trash.html` text: "reads the real trash dir when served from the image; in this static preview it lists what the face build stages" + "(empty in this preview ...)". No screenshot, no delete->trash->restore proof.

## Placeholder flags
- Declared: `trash.html` (preview text); `pty-test.html` ("honest scaffolding: browsers cannot do raw TCP"); login demo ("any non-empty password", `login-README.txt` + card hint); `AUTOLOGIN.md` documents demo autologin switch, OFF in shipped image.
- Undeclared (functionally placeholder): shell Terminal echo box (looks like a shell, runs nothing); Notes/Calendar/Calculator/Settings localStorage-only (per-browser, reboot/disk persistence unproven, not labelled); dock Calendar/Calculator entries bypass the face pages for native `orage`/`galculator`; systems dock targets resolve outside `face/` with no record-wiring proof; `STATUS.md` TODO rows hide all of the above (no per-app failure list as task 24 requires).
