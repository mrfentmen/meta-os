# Meta OS session — how the face owns the screen

Date: 2026-11-03. Files: `os-build/face/kiosk.sh`, `os-build/face/session.sh`.
Image: `/tmp/metaos.ext4` (Ubuntu 24.04 + XFCE, autologin session `metaos`,
user `ubuntu`, browser epiphany 46.5 WebKitGTK).

## How fullscreen is achieved (current code)

1. `session.sh` is the lightdm `metaos` session (`Exec=/opt/face/session.sh`).
   It starts `/opt/face/kiosk.sh` in the background, then `exec startxfce4`.
   XFCE is the floor: if the kiosk exits 1, the user still gets XFCE.
2. `kiosk.sh` starts `face.target` (7 user units: 18900/18931/18932/18933/
   18934/18935/18936), polls `curl -fs http://127.0.0.1:18900/shell.html`
   up to 40x0.5s. If 18900 never answers it writes
   `~/.local/state/metaos/session-fallback` and exits 1 — XFCE stays.
3. On success it launches `epiphany --application-mode
   http://127.0.0.1:18900/login.html` with
   `WEBKIT_DISABLE_COMPOSITING_MODE=1` + `LIBGL_ALWAYS_SOFTWARE=1`.
4. Fullscreen loop (up to 30 tries, 1s apart):
   - `wid=$(wmctrl -l | grep -i epiphany | head -1 | awk '{print $1}')`
   - `wmctrl -i -a <id>` (raise), then
     `wmctrl -i -r <id> -b add,fullscreen` (EWMH fullscreen; under xfwm4
     this is borderless — no separate un-decorate step needed), then
     `wmctrl -i -r <id> -e 0,0,0,1920,1080` to fill the screen.
   - If `wmctrl -b add,fullscreen` exits non-zero, fallback is
     `xdotool windowactivate <id>` + `sleep 0.5` + `xdotool key F11`.
   - Every attempt logs one timestamped line to `/tmp/metaos-kiosk.log`
     with the exact command, its `rc=` and its `out=`. No `2>/dev/null
     || true` on any wmctrl/xdotool step.
5. Panels only while the shell is up: after `fullscreen_ok=1`,
   `xfce4-panel --quit` + `pkill plank` for this session only. No package
   removal, no autostart deletion (`plank.desktop`, `xfce4-panel.xml`,
   `meta-desktop-fix.desktop` untouched), so a fallback boot still has a
   panel. If fullscreen fails, panels are left visible.

## What was tried and failed

- Old `kiosk.sh` did one `sleep 4` + 15x `wmctrl -l` with all wmctrl
  errors silenced (`2>/dev/null || true`), logged only success or total
  failure, had no `xdotool` fallback, and never hid the panel/plank —
  hence the small window in the bottom-left under the XFCE panel.
- `xdotool key F11` without `windowactivate` first was unreliable in the
  harness (key went to the focused terminal); activating the epiphany
  window first fixed it.
- `wmctrl -e 0,0,0,1920,1080` alone (without `-b add,fullscreen`) left
  xfwm4 decorations on; fullscreen state was required for borderless.
- Build bug found while diagnosing `face-unavailable`: `provision.sh
  --root` baked `$ROOT` into unit files (`WorkingDirectory=/mnt/opt/face`,
  `ExecStart=/usr/bin/python3 /mnt/opt/face/*.py`), so 18900 never
  answered on first boot. Fixed in `provision.sh` to write runtime paths
  (`RUNTIME_DST=/opt/face`, `RUNTIME_SITE=/opt/face-site`). The disk image
  units were corrected the same way (`/mnt/opt/face` -> `/opt/face`).
  Evidence: guest `~/.local/state/metaos/session-fallback` contained
  `face-unavailable` (read via debugfs, `/tmp` is tmpfs so the live
  `/tmp/metaos-kiosk.log` is not on disk).
- No desktop screenshot is claimed as proof. A QEMU screendump taken
  during diagnosis (`/tmp/qsnap.png` on the host) showed the pre-fix state:
  XFCE top panel + plank with no shell window — consistent with the
  fallback above, not a fixed state.

## Evidence (`/tmp/metaos-kiosk.log`)

Lines below are from a local harness run of the shipped `kiosk.sh` with
mock `wmctrl`/`xdotool`/`epiphany`/`systemctl` on PATH (the guest log has
the same format; guest `/tmp` does not survive reboot so the harness is
the citable source). Full logs saved alongside this note as
`/tmp/kiosk-success.log` and `/tmp/kiosk-xdotool.log` on the build host.

Success via wmctrl (`/tmp/metaos-kiosk.log`):

```
2026-11-03T11:39:14Z === kiosk start ===
2026-11-03T11:39:14Z probe http://127.0.0.1:18900/shell.html up after 0 tries
2026-11-03T11:39:20Z fullscreen attempt 3: found epiphany window 0x06000001
2026-11-03T11:39:20Z fullscreen attempt 3: wmctrl -i -r 0x06000001 -b add,fullscreen rc=0 out=fake wmctrl -i -r 0x06000001 -b add,fullscreen (call 5)
2026-11-03T11:39:21Z fullscreen attempt 3: SUCCESS fullscreen requested on 0x06000001
2026-11-03T11:39:21Z fullscreen: achieved after 3 attempt(s)
2026-11-03T11:39:21Z panels: xfce4-panel --quit rc=0 out=fake xfce4-panel --quit
2026-11-03T11:39:21Z panels: pkill plank rc=0 out=fake pkill plank
2026-11-03T11:39:21Z === kiosk done ===
```

wmctrl-fails -> xdotool fallback (`/tmp/kiosk-xdotool.log`):

```
2026-11-03T11:39:28Z fullscreen attempt 1: wmctrl -i -r 0x06000001 -b add,fullscreen rc=1 out=fail
2026-11-03T11:39:28Z fullscreen attempt 1: wmctrl fullscreen failed rc=1; trying xdotool F11 fallback
2026-11-03T11:39:28Z fullscreen attempt 1: xdotool windowactivate 0x06000001 rc=0 out=fake xdotool windowactivate 0x06000001
2026-11-03T11:39:29Z fullscreen attempt 1: xdotool key F11 rc=0 out=fake xdotool key F11
2026-11-03T11:39:29Z fullscreen attempt 1: SUCCESS xdotool F11 sent for 0x06000001
```

Fallback preserved (18900 down):

```
2026-11-03T11:39:06Z FALLBACK: face did not answer on 18900; staying in XFCE
2026-11-03T11:39:06Z === kiosk done (fallback) ===
```

with `~/.local/state/metaos/session-fallback` = `face-unavailable` and
panels untouched.
