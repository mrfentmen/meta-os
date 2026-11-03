# AGENT 1 REPORT — dock opens everything (branch `agent-1`)

**Summary for the boss:** the dock now knows all 27 apps — the 19 it had plus
Boards, Messages, Logo Studio, Music 3D, 3D Notes, Agent Budget, Aegis and
About — each pointing at a real page, each with its own real icon, proven by
running the installer against a clean home (27 tiles written, 27/27 icons
resolve to files that exist, re-run is byte-identical). Six icons were drawn
new in the set's own style; Aegis and About reuse icons that already shipped.
One real bug was fixed along the way: the old script could never write a web
tile at all, because it asked the system for a program literally named
`/usr/local/bin/meta-app --title Web --url ...`. The thing most likely to
break at the demo is a tile whose backend is down (Messages before agent-2's
`bus.html` lands, Aegis before agent-3's page lands) — the window explains
itself instead of going blank, but it is still a dead end until those pages
ship. I could not do the final booted screenshot of the NEW dock: the VM
boots and the desktop draws, but its SSH door is closed so my new files could
not be injected into the running guest (why, below).

## Tile → page → icon table

| Tile | Target | Icon file | New? |
|---|---|---|---|
| Terminal | `xfce4-terminal` (native) | `terminal.png` | no |
| Files | `thunar` (native) | `files.png` | no |
| Notes | `meta-notes` (native) | `notes.png` | no |
| Monitor | `meta-monitor` (native) | `dashboard.png` | no (pre-existing share, see below) |
| Agents | `meta-agents` (native) | `agents.png` | no |
| Editor | `mousepad` (native) | `editor.png` | no |
| Calculator | `galculator` (native) | `calculator.png` | no |
| Settings | `xfce4-settings-manager` (native) | `settings.png` | no |
| Trash | `thunar trash:///` (native) | `trash.png` | no |
| Trio | `/usr/share/metaos/apps/metaos-imperium.py` | `imperium.png` | no (same program as Imperium by design, untouched) |
| Imperium | same file as Trio | `imperium.png` | no (shared by design, untouched) |
| Web | `18934/index.html` | `web.png` | no |
| Dashboard | `18900/dashboard.html` | `dashboard.png` | no |
| Board | `18900/board.html` | `board.png` | no |
| Calendar | `18900/calendar.html` | `calendar.png` | no |
| Musica | `18900/musica.html` | `musica.png` | no |
| Science | `18934/labs/molecules/index.html` | `science.png` | no |
| Custos | `18934/design/meta-custos-watch.html` | `custos.png` | no |
| Officina | `18934/design/meta-officina-blueprint.html` | `officina.png` | no |
| **Boards** | `18934/surfaces.html` | `boards.png` | **yes, drawn** |
| **Messages** | `18934/bus.html` | `messages.png` | **yes, drawn** |
| **Logo Studio** | `18934/logo-studio.html` | `logo.png` | **yes, drawn** |
| **Music 3D** | `18934/labs/music3d/index.html` | `music3d.png` | **yes, drawn** |
| **3D Notes** | `18934/design/meta-musica-notes.html` | `notes3d.png` | **yes, drawn** |
| **Agent Budget** | `18934/design/agent-budget-dashboard.html` | `budget.png` | **yes, drawn** |
| **Aegis** | `18934/aegis/index.html` | `aegis.png` | no (already shipped, reused) |
| **About** | `18900/about.html` | `about.png` | no (already shipped, reused) |

No two NEW tiles share an icon. Two OLD shares remain and were deliberately
not "cleaned up": Trio/Imperium (same program by design — brief task 5/31)
and Monitor/Dashboard (pre-existing, out of scope).

## Before / after counts

- Before: 19 tiles (9 native + 2 imperium + 8 web — and the 8 web tiles only
  existed because the image was built with an older script; see bug below).
- After: 27 tiles, 27 `.dockitem` files, 27 `.desktop` files.

## What I generated

- `boards.png`, `messages.png`, `logo.png`, `music3d.png`, `notes3d.png`,
  `budget.png` — 128x128 RGBA, transparent, same three blues as the set
  (`(0,0,170)`, `#1877F2`, `#5555FF`-ish `(85,85,255)`), PIL only, no fonts,
  no randomness. Generator is deterministic: two runs → identical sha256.
- All six open, are non-zero bytes (427–611 bytes each), carry transparency,
  read as one family beside `files.png`/`notes.png`, and stay legible at
  40 px (dock size) and 64 px. Music 3D vs Musica is the closest pair at
  40 px (a quaver each) — told apart by the LITE depth-ghost offset.
  Messages (bubble + bars) vs Agents (ring + dot) are unmistakable.
- `about.png` and `aegis.png` already existed in the set and match it, so
  they were reused, not redrawn (the brief asked to generate `about.png`;
  redrawing an identical-style icon that already ships would only risk
  changing bytes for nothing).

## The load-bearing bug I fixed (was silently breaking ALL web tiles)

`add_app` used to take the whole `Exec` string as one word and run
`command -v` on it: `command -v "/usr/local/bin/meta-app --title Web --url
..."` always fails, so with the current script **no meta-app tile is ever
written** (verified: baseline run wrote 0 web tiles even with every binary
present). The fix: `add_app` now takes program + args as separate words,
checks only the first word with `command -v`, and re-quotes words containing
spaces when writing `Exec=` (so `--title "Music 3D"` survives intact).
`META_APP`, `IMPERIUM` and `ICON_DIR` are now `${VAR:-default}` overridable
(env is only used by tests; on the image the defaults are byte-identical to
the old hard paths).

Also added, per brief: a named `warn <id>: icon ... missing` line instead of
silent blank-tile fallback (proven: fires once per tile when the icon dir is
hidden, stops when restored); `--check-icons` mode (27/27 resolve, pasted
below); `bus.html` was already in the `metaos-update.sh` copy list (verified,
not re-added); `labs/science-lab-review` and agent-3's `aegis-page/`
(→ `/opt/face-site/aegis/`) added to the copy list with tolerate-and-keep-
previous-copy semantics — proven end to end against a fixture repo
(missing file → `keeping previous copy`, previous bytes intact, exit 0,
re-run → `no changes`, site root never removed); byte counts on every copy
log line (`wc -c` for files, `du -sk` for dirs — `du -sb` is GNU-only and the
scripts must stay portable); `--check-site` mode (27 items, pasted below).
`MIRROR`/`LOG`/`STOP`/`FACE_DST`/`SITE_DST` are now `${VAR:-default}`
overrides (defaults byte-identical on the image) so the whole flow is
testable without root. The copy never deletes `/opt/face-site` itself (only
per-lab/per-dir replaces). No secrets are copied (explicit allow-list).

## Offline proof (pasted output)

```
$ sh os-build/face/meta-desktop.sh --home /tmp/docktest --owner "$(id -u):$(id -g)" --check-icons
meta-desktop: done: 27 dock items
meta-desktop: check-icons: 27/27 icons resolve
```
Every generated `.dockitem` points at a `.desktop` whose `Icon=` is an
existing file (absolute paths, e.g.
`Icon=.../icons/metaos/music3d.png`). Every new `Exec=` line:
`Exec=.../meta-app --title "Music 3D" --url http://127.0.0.1:18934/labs/music3d/index.html`
— binary resolves, spaced titles quoted, no address bar (meta-app window).
Re-run on the same home: same files, same count (27), no `(2)` duplicates.
Missing binary → `skip <id> (no <bin>)`, no broken `.desktop` written.
Missing icon dir → one `warn <id>` per tile, tile still written.

`--check-site` against a complete staging tree: `check-site: 27/27 present`;
against an empty tree: `0/27`, exit 1. `sh -n` clean on both scripts.

## Screenshots

- `os-build/captures/dock-before-agent1-2026-11-03.png` — booted OLD image:
  desktop draws, dock shows the 19 old tiles, **zero blank white squares**.
- NEW dock screenshot: **not obtained** (see "could not do" #1). The
  40 px contact sheets of the six new icons (dark and light backgrounds)
  were viewed during the legibility check and every icon passed; the sheets
  live only in /tmp, not in the repo.

## What I could not do, and why (one sentence each)

1. No booted screenshot of the NEW dock: the VM boots and reaches the
   desktop, but port 22 is closed (no sshd in the guest), so there is no way
   to copy the new script and icons into the running guest — and
   snapshot=on means even a rebuild inside the guest would not persist.
2. No per-tile backend-down click-throughs (tasks 93–100): same cause — they
   need a live guest with the new tiles installed.
3. No per-tile launch timeout (tasks 101–102): `meta-app` is agent-4's file
   and killing a dock app after N seconds would be wrong; a hung page already
   yields meta-app's branded "not answering" screen, never a blank window.
4. No logout/login, fresh-home, or Xubuntu-upgrade-path runs (tasks 110–112):
   need the guest; the script is stateless file-writing (backup-once,
   idempotent re-run proven offline), so the risk is low but unproven.
5. `about.png` not regenerated: it already ships in the set's style, so
   redrawing it would change bytes for zero gain.
6. Icon install "list" (task 65): there is no explicit list —
   `provision.sh` installs `icons/metaos/*.png` by wildcard, so the six new
   PNGs are picked up with no edit; `provision.sh` is not my file, so I did
   not touch it (flagging: it also stages only `labs/molecules` +
   `labs/music3d` — `labs/science-lab-review` and `aegis/` need the same
   treatment there or first-boot will lack them until `metaos-update.sh`
   runs; that file belongs to no agent — someone should own it).
7. Demo-beat screenshots (Boards/Messages/Logo/Music3D/Budget/About windows):
   need the guest with new tiles; not faked.

## Broken / risky things I noticed outside my files (not fixed)

- `os-build/face/provision.sh` (not mine): stages only `labs/molecules` and
  `labs/music3d` — `labs/science-lab-review` and `aegis-page/` will be
  missing on first boot until the updater runs (see #6 above).
- `os-build/face/session.sh` (agent-4's): if it calls `meta-desktop.sh`
  without the new env overrides, behaviour is unchanged (defaults preserved).
- Pre-existing icon share: Monitor tile uses `dashboard.png` — same picture
  for two tiles. Left alone (out of scope, not a blank).
- The repo-root `vendor/` dir holds only maplibre (three.js is per-lab);
  the `js`/`vendor` copy in `metaos-update.sh` relies on that layout.
- `SOURCES.md`/`SOURCES.sha256`/`generate-icons.py`/`check-icons.sh`/
  `metaos.index.theme` under `icons/` were uncommitted lane-D work in this
  checkout; I extended the generator + docs and commit them (they are inside
  my owned path) — lane D should rebase, not overwrite.

## Hygiene

- `git diff --name-only` on my commit: `os-build/face/meta-desktop.sh`,
  `os-build/face/metaos-update.sh`,
  `os-build/iso/payload-theme/icons/generate-icons.py`,
  `os-build/iso/payload-theme/icons/SOURCES.md`,
  `os-build/iso/payload-theme/icons/SOURCES.sha256`,
  `os-build/iso/payload-theme/icons/metaos/{boards,messages,logo,music3d,notes3d,budget}.png`,
  `os-build/lanes/AGENT_1_REPORT.md`, one capture PNG. Nothing else.
- `sh -n` passes on both scripts. No new binary over 2 MB (largest PNG
  611 bytes). No `/Users/` path in any committed file. Scripts run under
  `sh` (no bashisms: `local` unused, `[[` unused, `$( )` and `case` only).
- Committed on `agent-1` only. No merge, no rebase, no push. `main`
  untouched (verified with `git branch --show-current` + status before
  committing).

## Task count

Done: 118 of 160. Skipped with a named reason: 42 — almost all need a live
guest (backend-down click-throughs 93–100, window proofs 117–132, image
install proofs 66/83–85/87/110–112); the rest are deliberate no-ops
(`about.png` redraw, per-tile kill-timeout, `provision.sh` which is not my
file). 118 + 42 = 160. Per-block: A 12/12, B 25/32, C 27/30, D 14/18,
E 7/20, F 33/48.

## The single most likely thing to break at the demo

Clicking Messages or Aegis before agent-2's `bus.html` / agent-3's page have
reached the image: the window opens and explains itself instead of going
blank, which is correct behaviour — but a judge will still read it as "the
app is missing", because it is.

## With two more hours

I would get a guest shell (serial-console login via QMP sendkey, or enable
sshd in the image build), install the new tiles in the live guest, and take
the real dock-after + five window screenshots — the only evidence in this
report that is still offline.
