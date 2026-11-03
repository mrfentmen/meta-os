# THE WIRING PLAN — Meta OS 1.0

Agents working inside the image, and the apps running in it.
Written 2026-11-03, after reading both provisioners, both app trees and
the agent layer. This is the order to build in, not a wish list.

---

## 0. The diagnosis (one paragraph)

You are not short of code. You have **three complete things that were never
introduced to each other**:

| Thing | Where | State |
|---|---|---|
| The kiosk desktop + 15 apps + 7 loopback services | `os-build/face/` | 24 tasks PROVEN in a Debian 12 VM, real screenshots |
| The Meta-branded Xubuntu image | `os-build/iso/` | boots, themed, apps missing, no face |
| The agent relay | `agents/` + `agent-layer/` | runs on the host, staged into a rootfs, never proven inside the booted image |

The image you booted was provisioned by `os-build/iso/provision.sh`
(theme, calamares, plymouth, identity, agent-layer). It was **never**
provisioned by `os-build/face/provision.sh`, which is the file that installs
the six backend services and the desktop the apps live in. That is one missing
call, plus the session switch, plus the agent bridge. That is the whole job.

Everything below exists to close three seams:

- **Seam 1 — provisioning**: two provisioners, one image, no shared order.
- **Seam 2 — session**: XFCE + plank currently own the screen; the face shell
  is supposed to.
- **Seam 3 — agent → app**: the relay has no way to show itself on the desktop,
  and the desktop has nothing to ask.

---

## 1. The target picture

One boot, in this order:

```
GRUB -> plymouth (metaos theme) -> lightdm (autologin "meta")
   -> metaos-session.sh            <- NEW: the only thing that starts the desktop
        |-> systemctl --user start metaos-face.target   (7 services)
        |-> wait for http://127.0.0.1:18900/healthz
        |-> launch browser kiosk -> http://127.0.0.1:18900/login.html
             -> shell.html: topbar, dock, windows
```

### The processes and who owns them

| Service | Port | Owns | Exists? |
|---|---|---|---|
| `face-http` | 18900 | serves `/opt/face` (login, shell, 15 app pages) | yes, in `os-build/face/provision.sh` |
| `face-launcher` | 18931 | allow-list native app launcher | yes, allow-list too thin |
| `face-facts` | 18932 | machine facts for the Dashboard | yes |
| `face-ptyd` | 18933 | **real bash** over WebSocket/TCP | yes, one client at a time |
| `face-site` | 18934 | repo-root product pages (ASCII studio, labs) | yes |
| `face-board` | 18935 | board store | yes |
| `face-files` | 18936 | files + trash store | yes |
| `oc2-queue` | 8935 | agent job API | yes, staged, unproven in guest |
| `oc2-patrol` + `.timer` | – | bounded agent cycles | yes, staged |
| `oc2-watchman` | – | runs the jobs | yes, staged |
| `oc2-health` + `.timer` | – | six-row health probe | yes, staged |
| **`metaosd`** | **18940** | **the agent ↔ desktop API** | **NO — one new daemon, ~200 lines** |

`metaosd` is the only new process in the plan. Everything else already has code.

---

## 2. Workstreams

Order matters. W1 unblocks W2 and W4; W3 can run in parallel from hour 0.

### W1 — ONE PROVISIONER (Seam 1)
**Goal:** a single run turns a stock Xubuntu rootfs into the Meta image.

1. `os-build/face/provision.sh` currently needs a live user: `sudo`, `$HOME`,
   `loginctl enable-linger`. Add `--root DIR`: stage to `DIR/opt/face`,
   write the units to `DIR/usr/lib/systemd/user`, and hand-create the
   `.wants` symlinks the way `agent-layer/stage.sh` already does.
2. New `os-build/iso/provision-all.sh` that runs, in this order and stops on
   the first failure:
   ```
   iso/provision.sh <root>              # plymouth, calamares, identity, theme
   iso/../metaos1-base/dexubuntu/apply-in-chroot.sh   # de-Ubuntu the identity
   metaos-brand/brand.sh --root <root>  # wallpaper/panel/dock/theme, 12 checks
   face/provision.sh --root <root>      # the 7 services + 15 apps
   agent-layer/stage.sh <root>          # the relay
   ```
3. Delete the duplicated work: `dexubuntu` and `brand.sh` both write
   `xfce4-desktop.xml`; only one may own it (brand.sh wins, it verifies).

**Gate:** one command, one log, every step exits 0, and
`grep -c '^FAIL' <log>` is 0. No manual fix-ups afterwards.

---

### W2 — ONE SESSION (Seam 2)
**Goal:** the box boots into the Meta desktop, not XFCE with a Meta wallpaper.

1. **Pick the browser first — this is the blocker.** On Ubuntu 24.04 `chromium`
   is snap-only, and the spike used Debian 12 where it was a real apt package.
   Options, in order of preference:
   - `epiphany-browser` (WebKitGTK, plain apt, `--application-mode` kiosk flag)
   - the Google Chrome `.deb` (licensing is fine for your own image, it's not a
     redistribution issue in a private demo)
   - keep snap chromium and pre-warm it at build time (slowest, worst)
2. New `os-build/iso/payload-session/metaos-session.sh`:
   - starts `metaos-face.target`
   - loops on `curl -fs 127.0.0.1:18900/healthz` (10 s cap) then launches kiosk
   - if the health check fails, **fall back to XFCE** and write
     `~/.local/state/metaos/session-fallback` — a broken backend must not leave
     a black screen, which is exactly what wasted an hour tonight.
3. New `os-build/iso/payload-session/metaos-session.desktop` (`X-GNOME-Autostart`
   or a lightdm session file). Remove from autostart: `plank.desktop`,
   `xfce4-panel`, `metaos-welcome.desktop` (it opens over the face).
   Keep them installed as the "Meta Classic" fallback session.
4. `metaos-face.target` — a real systemd **user** target that `Wants=` all seven
   `face-*` units, so the session starts one thing and not seven races.
5. Kill the greeter residue for good: the session, not the greeter, paints the
   screen; autologin stays.

**Gate:** cold boot to `shell.html`, **zero** stray windows, one screenshot at
1920x1080, `systemctl --user list-units 'face-*'` all `active`.

---

### W3 — AGENT LAYER INSIDE THE IMAGE (parallel, hour 0)
**Goal:** the relay runs in the guest, from boot, with no hand-typed command.

1. Add to the package list: `nodejs`, `git`, `python3` (already), `curl`.
   Check the version `agents/*.mjs` needs — it uses top-level `await` and
   `node:` specifiers, so **Node >= 16**; Ubuntu 24.04 ships 18, fine.
2. `agent-layer/stage.sh` already writes `/usr/share/metaos/agent` + units +
   `/etc/skel/.config/oc2-agent/env` + the login autostart. Verify it survives
   `--root` (it does) and that `OC2_CHECKOUT` points at the payload, not the
   repo.
3. **The key.** `SPARK_API_KEY` must never be in the image. Two honest choices:
   - demo path: `/etc/metaos/agent.env` root-owned 0600, shipped blank, filled
     in the VM before recording; the login hook imports it into the user manager.
   - clean path: prompt on first login. Slower to demo, correct for a release.
4. `meta-agent-login.sh` must run **before** the face starts, so
   `meta-agent-status` has state on first paint.
5. `journalctl --user -b` must show the queue start line and one patrol cycle.

**Gate:** reboot, touch nothing, and
`journalctl --user -b -u oc2-queue -u oc2-patrol` shows queue start + at least
one completed cycle. `meta-agent-status` prints a heartbeat.

---

### W4 — THE BRIDGE YOU CAN SEE (Seam 3)
**Goal:** from the desktop, give an agent a job and watch it happen. This is the
demo. Without it you have a themed Linux with a web desktop.

1. **New file `os-build/iso/payload-agent/metaosd.mjs`** — loopback only,
   `127.0.0.1:18940`, zero dependencies, stdlib `http`:
   ```
   GET  /agents            registry.json entries + halted flags
   GET  /jobs              the board (pending/running/done/failed)
   GET  /ledger?run=<id>   one run's JSONL, tail N
   GET  /status            meta-agent-status --json passthrough
   POST /jobs              {agent, orders} -> agents/submit.mjs
   POST /halt              {agent} -> touch state/stop/<agent>.STOP
   ```
   Rules to keep it from becoming a second brain: it holds **no policy**, it
   shells out to the existing `agents/submit.mjs` and `meta-agent-status`,
   and it refuses a non-loopback peer.
2. The Desktop's **Meta Agent Status** window (already in the dock) gets three
   live columns: *who can take work* (agents), *on the board* (jobs),
   *what just happened* (ledger tail). One button: **Give this to an agent.**
3. `meta-ask` lands in the guest PATH so the Terminal window can submit work
   the same way a person would.
4. Every app that shows agent state must label LIVE vs RECORD, as the current
   `face/README.md` already promises. No faked rows in a demo.

**Gate:** in the browser, submit "sweep the tree for stray licenses" to `watch`;
the board shows pending → running → done; the ledger tail shows the run's
events; the receipt file exists on disk at `~/.local/state/oc2-agent/runs/`.

---

### W5 — PROOF (last hour, non-negotiable)
1. `os-build/tools/proof_session.sh` — curls all 8 endpoints, checks each app
   page returns 200, runs one job, prints a PASS/FAIL table. One command, one
   exit code. This is what you show instead of describing.
2. `os-build/WIRING_PLAN.md` (this file) links the gate artifacts as they land.
3. Demo video beats, in §5.

---

## 3. The clock

Assume 10 usable hours. Blocks are 60–90 minutes, each ending at a gate.

| Hr | Track A (session/apps) | Track B (agents) | Gate at the end |
|---|---|---|---|
| 0–1 | W1: `face/provision.sh --root`, `provision-all.sh` | W3: packages + stage.sh verify | one command builds the image |
| 1–2 | Browser decision + `metaos-face.target` | key file + login hook ordering | 7 units exist and start by hand |
| 2–3 | `metaos-session.sh` + fallback | `oc2-queue` answering 8935 in guest | **boot lands in the face** |
| 3–4 | dock → real services wired, 11 apps | patrol cycle in journal | every dock icon opens something |
| 4–5 | ptyd multi-client (W4 prerequisite) | `metaosd` skeleton + `/status` | Terminal is a real bash |
| 5–6 | Agent Status window: agents + jobs | `POST /jobs` → `submit.mjs` | job appears on the board |
| 6–7 | halt button, ledger tail | end-to-end: job runs, result lands | **the demo works once** |
| 7–8 | polish: no stray windows, autologin, time-to-desktop | ledger receipt written | clean cold boot |
| 8–9 | `proof_session.sh` | run it twice to prove idempotence | PASS table |
| 9–10 | record the video | — | file exists |

**If you are behind at hour 4,** cut in this order: `face-site` product pages →
`face-board` → `face-facts` → the Musica/Science windows. **Never cut** ptyd,
the queue, the Agent Status window, or the proof script — those four are the
claim.

---

## 4. Landmines (all hit already, all known)

1. **Chromium is snap-only on 24.04.** The spike was Debian. Decide the browser
   before you build, or you build twice.
2. **`file://` vs `http://`.** Every app fetches absolute
   `http://127.0.0.1:1893X` URLs, and the shell must be served from 18900, not
   opened from disk. Serving the shell off `file://` is the fastest way to make
   "all my apps are broken" true.
3. **Lightdm uid leak.** `/var/lib/lightdm` owned by uid 501 (a container leak)
   makes the greeter fail to write its Xauthority, which kills X, which gives
   "Display output is not active". `chown` it in the provisioner, every build.
4. **No journal on the rootfs** → every hard kill corrupts ext4, then `e2fsck`.
   Always `system_powerdown`, never `kill`. Put a journal in the builder.
5. **`ptyd.py` serves one client.** An agent and the Terminal window will
   collide. Rise to N sessions (or a small pool) before the demo.
6. **`face/provision.sh` is not rootfs-safe yet** (`$HOME`, `sudo`, linger).
   That is W1 step 1 and it blocks everything else.
7. **Two `xfce4-desktop.xml` writers** (`dexubuntu`, `brand.sh`) — last writer
   wins and the loser's verify fails confusingly.
8. **XFCE panel + plank fight the face for the screen.** Two compositors-worth
   of window owners on one root window is how you get "a box in the corner".
9. **Empty `SPARK_API_KEY` → patrol pauses deliberately.** That is correct
   behaviour, not a bug; it will look like "agents don't work" in a demo.
10. **Calamares has never installed this image.** Do not promise an installer in
    the video; promise the live session.

---

## 5. The demo script (3 minutes, 7 beats)

1. Power on. Plymouth Meta splash → desktop. **Say the boot time.**
2. Terminal window: `uname -a`, `cat /etc/os-release` → `MetaOS 1.0`. Real bash,
   over `ptyd`.
3. Files: browse a real directory, open a file in the editor, save it,
   reboot-proof it.
4. Dashboard: LIVE rows light up; RECORD rows say RECORD.
5. Agent Status: show the three columns, then **give an agent a job**.
6. Watch pending → running → done. Open the ledger tail. Show the receipt file.
7. `meta-agent-status` in the Terminal — the same truth the GUI showed.

The closing line that is actually true: *"This is a Linux distribution whose
desktop, apps and agent relay are Meta's. Not a macOS clone, not a kernel
rewrite — a Meta-coded OS that boots."*

---

## 6. Definition of done ("fully Meta")

Eight checks, each with an artifact:

1. `cat /etc/os-release` → `MetaOS 1.0`, `ID=metaos`, no Ubuntu/Xubuntu string
   anywhere in `os-release`/`lsb-release`/`issue`.
2. No xubuntu package or asset dir on disk.
3. Cold boot to the Meta desktop; no greeter residue, no patch script needed.
4. Every dock icon opens a window backed by a real service.
5. Terminal is a real shell in the guest.
6. `oc2-queue` answers on boot with no typed command.
7. A job submitted from the GUI runs and leaves a receipt.
8. `proof_session.sh` exits 0, twice in a row.

---

## 7. Not in scope — say it out loud

- This is not a macOS clone. No Quartz, no Metal, no Cocoa. It is a Linux
  distribution with a Meta-coded session and a Meta-coded agent relay.
- The kernel lane (`kernel/`, K1–K6) is real and separate; this image runs
  Linux's kernel. Do not blend the two claims in the video.
- The installer (Calamares) is untested against this image; the live session is
  the deliverable.
- `face/` at the repo root is the design reference, not the shipped shell. The
  shipped shell is `os-build/face/`. One of them has to lose its vote.
