# INTEGRATION — what is wired, and what is only installed

State of `/tmp/metaos.ext4` (16 GB, user `ubuntu`) as of 2026-11-03.
"Installed" means the file is on the disk and syntax-checks. "Proven" means it
was seen working. Nothing here is called proven without a boot behind it, and
the image is currently **off**.

## The chain, link by link

| # | Link | File / unit | State |
|---|---|---|---|
| 1 | power → desktop | lightdm autologin `ubuntu`, session `metaos` | installed |
| 2 | session entry | `/usr/share/xsessions/metaos.desktop` → `/opt/face/session.sh` | installed |
| 3 | session → XFCE | `session.sh` runs `startxfce4` (the fallback floor) | installed |
| 4 | session → kiosk | `session.sh` starts `kiosk.sh` in the background | installed |
| 5 | kiosk → backends | `systemctl --user start face.target` (7 services) | installed |
| 6 | backends alive | 18900 http, 18931 launcher, 18932 facts, 18933 pty, 18934 site, 18935 board, 18936 files | installed |
| 7 | kiosk → wallpaper | `metaos-livebg.service` → `meta-live.py`, 240 frames @60 fps | installed |
| 8 | wallpaper → screen | `_pin_to_screen()` sizes the window to the root window and refits on the screen's `size-changed`/`monitors-changed`; each frame is re-cut to the widget's allocation (`cover_metrics`), so a resize cannot leave the art in a corner. No timer: a 1 s re-assert froze the window at the pre-resize size | installed |
| 9 | kiosk → shell | epiphany `--application-mode` on 18900, then `wmctrl` fullscreen | installed |
| 10 | shell → desktop | `shell.html`: top bar, 16-app dock, window manager | installed |
| 11 | desktop → agents | `metaosd.service` on 18940; `agents.html` reads it | installed |
| 12 | agents → queue | `oc2-queue` on 8935 → `queue_service.py` | installed |
| 13 | queue → work | `oc2-watchman` runs `agents/watchman.mjs` | installed |
| 14 | shell → agents | `/usr/local/bin/meta-ask` (12 live agents listed) | works (dry-run) |

## Fixed tonight, with the reason

- **The image had no apps** because `os-build/iso/provision.sh` never ran
  `os-build/face/provision.sh`. The face and its seven services were absent
  from `/opt`. Now staged: `/opt/face` (16 app pages, 6 python daemons).
- **`face/provision.sh` could not run against a disk** — it needed `$HOME`,
  `sudo`, `loginctl`. It now takes `--root DIR`, and root mode verifies files
  instead of live ports.
- **The wallpaper was "small"** for two independent reasons: `meta-ascii.png`
  holds its art in the middle 30% of the canvas, and xfdesktop had no
  `image-style`, so it drew at native size. Both fixed: style 5 everywhere,
  and the animated set is the wallpaper now.
- **The spinning logo was inset like a plane** because `meta-live.py` used
  `win.maximize()`, which honours panel struts. It now sets monitor geometry
  directly.
- **The shell opened as a small empty window** because it was launched before
  a window manager existed, and `wmctrl` had nothing to fullscreen. `kiosk.sh`
  now waits for `xfwm4`.
- **XDG autostart silently did nothing.** The kiosk is now started by the
  session script itself, and the wallpaper by a systemd user unit. Autostart
  copies were removed so there is one owner per thing.
- **Three `default.target.wants` links were missing and one was bogus**
  (`face.service`). All ten now resolve.
- **`meta-ask` was documented and never implemented.** It exists, lists 12
  live agents from `registry.json`, and refuses an unknown or halted agent.
- **`meta-desktop-fix` overwrote the user's wallpaper at every login.** It now
  sets only the zoom style.

## Offline proof, 2026-11-03 11:44 (no VM booted)

Every backend was started inside a chroot on the mounted disk and hit over
loopback. This proves the code, the paths, the ports and the payload — it does
not prove systemd started them or that X drew anything.

```
18900/shell.html       200
18900/agents.html      200
18932/facts            200
18935/rooms            200
18936/trash            200
18940/status           200
18940/agents           200
---
PASS 7/7
agents in registry: 23
```

`metaosd` reports `stateDirExists: true`, `agentDirFound: true`, and a queue
URL of `http://127.0.0.1:8935`. Two registry paths were wrong before this test
and are the reason it first answered `no registry.json`: both `metaosd` and
`meta-ask` looked at `/usr/share/metaos/agent` while `stage.sh` puts the node
runtime at `/usr/share/metaos/agent/agents`. Fixed in both.

## Three bugs the offline proof found (all fixed)

1. **`metaosd` and `meta-ask` looked for `registry.json` one level too high.**
   `stage.sh` puts the node runtime at `/usr/share/metaos/agent/agents`, the
   payload root is `/usr/share/metaos/agent`. Both now search the `agents/`
   subdir first, and the API reports 23 agents.
2. **The staged payload had no `package.json`**, so node treated
   `js/products.js` (real ESM) as CommonJS and `queue_service.py` died on
   startup with `Named export 'PRODUCTS' not found`. Fix:
   `/usr/share/metaos/agent/package.json` with `"type": "module"`.
   With it the queue answers `/health` 200 and loads 4 products.
3. **`meta-ask` and `metaosd` were posting agent orders to port 8935.**
   That service is the **Trio assessment queue**: it validates a
   `trio-assessment v1` envelope and refused the job with
   `400 refused job: not a trio-assessment v1 envelope` — correct behaviour.
   The real path is `agents/submit.mjs --root <state> --agent <n> --orders`
   which writes `<id>.job.json`, and `watchman.mjs` polls exactly those files.
   Both now use `submit.mjs` and fall back to 8935 only if it is absent.

Proven end to end offline, no VM:

```
$ meta-ask "sweep the tree for stray licenses" --agent watch
queued for watch
{ "id": "job-mw0miafm", "agent": "watch",
  "orders": "sweep the tree for stray licenses",
  "lane": "job board drain — one watchman pass per run" }
```

The test job was deleted afterwards so the watchman does not run it on boot.
The board is empty.

## What is NOT proven, and the one command for each

1. Boot lands in the shell fullscreen — `cat /tmp/metaos-kiosk.log` and look
   for `fullscreen on window`.
2. `xfwm4 present after N tries` — if N is 40, the WM never started.
3. Wallpaper fills — it must be `image-style 5` on the monitor in use:
   `xfconf-query -c xfce4-desktop -p /backdrop/screen0/<monitor>/workspace0/image-style`
4. Backends answer — `for p in 18900 18931 18932 18933 18934 18935 18936; do curl -s -o /dev/null -w "$p %{http_code}\n" http://127.0.0.1:$p/ ; done`
5. Agents run — `journalctl --user -b -u oc2-queue` must show a start line,
   and `meta-ask --list` must print without a "no registry" error.
6. A job completes — submit from the Agents window, then
   `~/.local/state/oc2-agent/runs/<id>/ledger.jsonl` must have events.

## The next three hours of work, in order

1. **Boot once.** Nothing below matters if the chain stops at 6 or 9.
2. **Whatever the boot log says is next.** `/tmp/metaos-kiosk.log` and
   `journalctl --user -b` name the broken link; do not guess past them.
3. **Then the queue.** `oc2-queue` has never been observed answering inside
   this image. Until it does, the Agents window can only show "unreachable".
