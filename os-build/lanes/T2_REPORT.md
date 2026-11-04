# T2 lane report — application shells and dock wiring

Branch: `agent-t2` (cut from `main`). No merges, no pushes. All work below was
done by six section subagents plus a review subagent, with lane-lead
integration (task 12 `--live` wiring, per-tile WM_CLASS) and this report.
No QEMU was used anywhere: proofs are headless Chromium, local scratch
servers, staged files, and read-only `debugfs` reads of the unbooted image
(`/Users/test/meta-os-images/metaos-agent-2026-11-02.qcow2` → raw copy at
`/tmp/metaos-base.raw`, ext4 at byte offset 134217728, never mounted).

## A. Shell behaviour (`os-build/face/native/meta-app.py`)

Failure paths (read end to end): missing `--url` (exit 2); unparseable URL /
no host / bad scheme (`--check` FAIL exit 1; `--list-port` prints `none`,
exit 2); dead backend (named `load-failed` screen, exit 3); HTTP 4xx/5xx on
the main resource (named missing-page screen, exit 3); load past `--timeout`
(default 30 s, named timeout screen, auto-quit exit 3); missing GI/WebKit
(stderr, exit 4); bad window size (clamped to 640x440, never 200x120);
missing/unwritable state file (`{}` fallback + stderr warning, window still
opens); `file://` target absent (`--check` FAIL, exit 1); external navigation
attempt (blocked in-page + InfoBar notice, never a silent system-browser
open); clipboard unavailable for URL copy (URL still printed to stdout).

What was built: named error screens show app name, path AND port in the
desktop's ink (`#070B16`/`#EDF5FF`/`#1877F2`); Reload button + Ctrl+R;
Ctrl+Shift+U prints AND copies the real URL (documented in `--help`); title
bar from `--title` only; `set_size_request(640,440)`; per-app geometry in
`~/.config/metaos/meta-app-state.json` (`{"Title":{"width":W,"height":H}}`,
written on close, overrides `--width/--height`); no address bar, no tab
strip, context menu suppressed (`context-menu → True`); `decide-policy`
blocks non-loopback http(s) with an InfoBar notice; `--check <url>`
(one line, exit 0/2xx else 1, no window); `--list-port`; exit 3 on never-load
so a launcher can detect it; destroy handler saves state and quits (no
background threads — file has no `subprocess`/`Popen`/`os.system`); 1 s
spinner/subtitle progress (`Loading …` → `Still loading … (Ns)` past 10 s);
`media-playback-requires-user-gesture=true`, allow-list empty (Musica plays
on click, not autoplay); dark `Gdk.RGBA` window + WebView background.

Lane-lead addition after the section pass (B's cross-lane request #2):
`wmclass_for_title()` maps a title to a dock id (`"Science Lab"` →
`"meta-science-lab"`), `AppWindow` calls `set_wmclass` with the same value
for instance and class, and all 9 shell `.desktop` files carry the matching
`StartupWMClass`. Verified headless: every Name→wmclass equals its desktop
value (9 OK, 3 native tiles correctly have none).

Proved by running: `gi` absent → exit 4; missing `--url` → exit 2;
`--list-port` → `18900`/`443`/`none`; `--check` 200 → exit 0, 404/refused/
bad-file/gopher → exit 1; 22/22 helper assertions green; 4 Chromium shots at
1440x900 (`t2-shell-*.png`, dark ink, path+port, key hints); `--check` live
probe below. Read-only (no GTK on this mac): title/chrome/gesture/quit paths
— code present, window never rows here; pure-logic equivalents all executed.

## B. Dock tiles and entries

Tile table (id, program, page, icon, state). All pages below answered
HTTP 200 in headless Chromium with real/stub servers.

| id | program | page | icon | state |
|---|---|---|---|---|
| agents | /usr/local/bin/meta-app | :18900/agents.html | meta …/agents.png | proven page; backend :18940 absent here (relay lane) |
| board | meta-app | :18900/board.html | board.png | proven |
| calculator | /usr/bin/mate-calc | NONE (native) | calculator.png | proven (native) |
| calendar | meta-app | :18900/calendar.html | calendar.png | proven |
| custos | meta-app | :18934/design/meta-custos-watch.html | custos.png | proven |
| dashboard | meta-app | :18900/dashboard.html | dashboard.png | proven |
| editor | /usr/bin/mousepad | NONE (native) | editor.png | proven (native) |
| musica | meta-app | :18900/musica.html | musica.png | proven (wav stubbed) |
| notes | meta-app | :18900/notes.html | notes.png | proven |
| officina | meta-app | :18934/design/meta-officina-blueprint.html | officina.png | proven |
| science | meta-app | :18934/labs/molecules/index.html | science.png | proven (SwiftShader, deprecation warnings only) |
| trash | /usr/bin/thunar | NONE (native) | trash.png | proven (native) |

Image findings (read-only debugfs): the image is a pre-provision base — no
plank tiles, no `/usr/share/meta-app`, no `/opt/face*`; 11/12 pages exist
in its baked repo checkout, only `agents.html` missing. No unit mentions
18900–18940, so no port could be tested in-guest; loopback here is not the
guest's. Fixes applied in owned files: all 12 Exec absolute
(`meta-app --title … --url …` / native binaries + `TryExec`), all 12 Icon
absolute existing PNGs, `StartupWMClass` per tile (split per-app by the
lane lead, verified headless), `Categories=`/`Keywords=`/plain-word
`Comment=` (no distro/agent names), custos/officina moved off the shared
`surfaces.html`/`index.html` onto dedicated pages, `Name=Code Editor` kept
(`theme_proof.sh:204` greps for it). No browser Exec remains
(`grep -ri epiphany|firefox|chromium apps/dock` → empty). No two tiles share
a page (`uniq -d` empty). 12 tiles / 12 `.desktop` files. Plank order equals
`meta-desktop.sh` order by construction (`01..NN` + full reset + stale
sweep). Terminal/file-manager theming is runtime-applied by the desktop
script (read-only finding). `check-dock-tiles.sh` (new): manifest is one
row per tile; `--fake-guest` builds a staged root → `12/12 tiles pass`;
image mode → `0/12` as expected pre-provision with each missing piece named.
`DOCK_ONLY=1 check-icons.sh` → 12/12 PASS.

## C. Page servers

| Program | Port | Unit | Serves |
|---|---|---|---|
| `python3 -m http.server` (face static) | 18900 | face-http.service | `/opt/face` |
| `launcher.py` | 18931 | face-launcher.service | allow-listed apps |
| `facts.py` | 18932 | face-facts.service | machine facts |
| `ptyd.py` | 18933 | face-ptyd.service | pty pool (max 4) |
| `python3 -m http.server` (site) | 18934 | face-site.service | `/opt/face-site` |
| `board.py` | 18935 | face-board.service | rooms/messages |
| `files.py` | 18936 | face-files.service | dirs/trash |
| `notesd.py` | 18937 | face-notesd.service | notes/calendar/settings |

Plus new `face-ready.service` (oneshot gate probing all 8: HTTP `/` on
18900/18934, `/healthz` on the five JSON servers, TCP connect on 18933) wired
into `face.target` Wants+After; provision.sh renders `ExecStart` pre-bind
probes so a squatted port fails loudly (`face-http: port 18900 already in
use`, exit 1 — proven live). Every Python server prints
`metaos-<name>: listening on 127.0.0.1:<port>`; `handle_error`/`handle_quiet`
replaced tracebacks with one-line logs (proven with garbage input).
`no-store` added to all 5 JSON servers (verified via `curl -si`); `http.server`
has no such flag — cross-lane request: new `static.py` wrapper owned by the
pages lane. All listeners bind 127.0.0.1 only (`lsof -iTCP` pasted in full
below). Traversal (`/..%2f..`) → 404, no passwd bytes; `files.py` rejects
`..` with 400; named JSON 404s; ptyd non-WebSocket → 400. Single-threaded
HTTP servers (1 request at a time); ptyd capped at 4 (5th gets `[busy]`,
proven). No off-localhost fetch at request time (only `facts.py →
127.0.0.1:18940` with timeout+fallback). `check-servers.sh` (new):
47 passed, 0 failed, trap-cleaned (`cleanup: no listeners left on any test
port`). RSS (KB, `ps`): launcher 22096, facts 26810, ptyd 16384, board 22608,
files 24256, notesd 23744, statics ~23600. No shared module created (natural
home outside owned paths — recommendation recorded, duplication kept small).

`lsof -iTCP` during the run (all 8 test listeners on 127.0.0.1, nothing else).

## D. App pages (18 files)

Sweep: all 18 HTTP 200; console errors only `about.json` 404 (written by
`session.sh` at login; page falls back to `:18932`) and `agents.html` ×4
`ERR_CONNECTION_REFUSED` to `:18940` (page names the port); zero uncaught
throws, zero non-loopback requests anywhere. Every page: `fetchT` timeout
with in-page port+reason (malformed/500/hang all pasted per-page, 11/11 each),
empty states that say why, HH:MM stamps, no horizontal scroll at 1366x768,
max-width containers at 1920x1080, theme tokens where they exist, duplicate
inline styles removed, `:focus-visible` + real buttons (Tab/Enter/Escape
throughout, Escape closes panels), contrast ≥ 4.5:1 computed (e.g.
`#eee/#111` 16.28, `#8291ac/#070B16` 6.17), per-page `<title>`, data-URI
favicons, dead controls fixed (calc `7+8=15`, board post round-trip, notes
create, files mkdir, calendar add, wallpapers pick persist, dashboard filter
`showing 1 of 10`), search filters with counts persisted in `localStorage`
(`metaos-*-filter`, calendar day, wallpaper choice), no autoplay, no popups,
system-font stacks only, no CDN. In-page selftests: agents 13/13,
notes 11/11. Screenshots: `os-build/captures/t2-page-*.png` (18 files),
all captured with `pageerrors: none`. Nothing duplicated badly enough to
remove (wallpapers vs settings form, about vs dashboard aggregate, pty-test
as contract doc — documented). Unprovable here: guest-only paths
(`about.json` login content, `:18934` product pages, `:18940` relay,
`:18931` launcher, `:18933` pty) — one-line reason each (no such server on
this macOS host).

## E. Icons (`os-build/iso/payload-theme/icons/`)

All 12 dock icons exist as PNGs (`metaos/<name>.png`); contact sheets
`t2-icons-contact.png` (44+128px on ink and paper) and `t2-icons-grey.png`
generated by new `t2-contact-sheet.py` (one command, re-ran after changes).
Determinism: regenerate-twice `diff -rq` empty for both generators.
44px rows inspected; closest pairs (agents/science 11.1) still distinct;
vendored three.js-era `generate-icons.py` left frozen and documented as
non-source. Trio gap fixed by generator (not by hand): +48 PNGs
(`ems/fire/police` × 8 accent sets × 2 sizes). No orphans except `nervus.png`
(owner: nervus agent lane, kept). No trademarks; per-icon provenance in
`SOURCES.md`. Min glyph-vs-plate contrast 31 (`editor`) — no gradient drop
needed. 1x/2x scheme documented (128px master + 48px row; toolkit downsamples
for the 40px dock). `check-icons.sh` + `DOCK_ONLY=1` → 12/12 PASS, plus a
negative test with a fake missing icon. `SOURCES.sha256` rebuilt (old file
had 26 stale hashes, all failing; now 30/30 `OK`). Accent regen verified;
`test-icon-accent.sh` updated 27→30 icons, 19 passed, 0 failed.

## F. Native apps (`os-build/iso/payload-theme/apps/`, minus imperium)

`metaos-controls.py` (widget gallery, `--selftest` 40/40 PASS on
`gtk.css`), `metaos-welcome.py` (first-run window, honest live rows,
`should_show` flag file). Titles fixed to dock names (`Controls`,
`MetaOS Welcome`); Ctrl+Q + Escape everywhere (no unsaved state, dismiss =
mark-shown); headless import <0.1 s; GTK-missing → stderr + exit 1
(`--check` still runs headless, full outputs in transcripts); no
compositor-only calls; no terminal (`Terminal=false`, only a captured
`subprocess` for metafetch); writes confined to `~/.config/metaos`;
no root usage; dead code justified line by line (chromium fallback listed
after firefox, never claimed). Welcome text fixed where it lied (OS string
now `Meta OS 1.0 (Ribbon)`, `metafetch.mjs` lookup reaches the repo, no
disabled-button claim). Gallery covers the theme except `.osd` (noted).
Monitor lives in Section A's `meta-monitor.py` — not touched; verified it
reads real values with units. No window can render here (no display server,
no `gi`) so no native screenshots — stated, not faked. README gained the
one-paragraph "add a native app" recipe. Still-a-page list: Notes (best
native candidate), Calendar, Agents/Board (need daemons), Dashboard,
Musica/Custos/Officina/Science (media/heavy).

## G. Proof and reporting

T2_REPORT.md is this file: one section per letter A–F above, this section G.

Tile table: see §B (12 rows; state `proven` in-tree for 12/12; `missing in
image` for program/icon/page install state because the image is a
pre-provision base — install belongs to the provision lane, flagged per tile
as `blocked` only where the guest backend itself is absent, i.e. agents on
:18940).

Console-error sweep (headless, all owned pages, real+stub backends): only
`about.json` 404 (login-written file, page falls back) and agents ×4
`ERR_CONNECTION_REFUSED` to :18940 (page names the port). Zero uncaught
throws on all 18 pages; zero non-loopback requests on all 18 pages.

Port tests: 8/8 units bind 127.0.0.1; `face-ready` gate probes all 8;
pre-bind conflict exits 1 naming the port; `lsof -iTCP` during tests showed
only the 8 test listeners on loopback.

Changed files (`git status --short`, 48 modified + 75 new = 123 paths —
full list in the commit; nothing outside: native/meta-app.py;
face/*.html ×18; face/*.py ×6 (board facts files launcher notesd ptyd);
face provision.sh (units part only); face check-servers.sh (new, needs lane
confirmation of its home); apps dock/*.desktop ×12, controls/welcome .py +
README; icons/* (code, SOURCES, hashes, 48 Trio PNGs, t2-contact-sheet.py);
captures/t2-*.png (24 screenshots) + t2-icons-*.png (2 sheets). No file
outside the owned list; in particular no `meta-desktop.sh`, no `trio/`, no
`agents/`, no `agent-layer/`, no `server/`, no `os-build/identity/`, no
`metaos-imperium.*`, no `meta-monitor.py`.

`git diff --stat`: 48 files changed, 2335 insertions(+), 607 deletions(-)
(tracked only; new files add ~75 paths: 24 captures, 2 contact sheets, 48
accent PNGs, check-servers.sh, check-dock-tiles.sh is tracked-modified,
t2-contact-sheet.py).

No QEMU process is running on this machine (checked with `pgrep -a
qemu-system`; only the grep itself matched, exit 1 — no emulator, no boot,
no mounts anywhere in this lane).

Three tiles most likely to fail on stage: (1) **agents** — page was absent
from the stale image's checkout and its :18940 relay belongs to another
lane; (2) **musica** — binary wav asset must be served from :18934 (file
exists in tree + copy list + check-site gate, but a missing byte kills
audio); (3) **science** — 3D page, needs vendored three.js + data and a
working WebGL path in the guest.

Two cheapest fixed: (1) dock proof now runs `meta-app --check <url>`
(`--live` flag) so a dead tile fails pre-boot with the port named — proven
both directions (12/12 pass with servers up; exactly the 3 :18934 tiles
fail with `Connection refused` when that server is down, exit 1). (2)
per-tile WM_CLASS (`wmclass_for_title`, identical instance+class) with
matching `StartupWMClass` in all 9 shell .desktop files, verified
headless 9/9 (3 native tiles correctly have none). The third (agents relay)
needs its backend from the agent lane plus a fresh provision so
`agents.html` exists; nothing in this lane can conjure :18940.

Commits: single commit `58108684` on `agent-t2` ("T2 lane: shells, dock wiring,
servers, pages, icons, native apps"; parent `9a2e87b2`, the `main` it was
cut from). `main` untouched: never checked out, never committed to here
(it has since advanced upstream on its own to `292afdbe`). No merge, no
push, working tree clean after commit.

One-paragraph answer: every dock tile opens its own real window — the nine
page tiles open chromeless per-app `meta-app` windows (title = app name,
own WM_CLASS, error screens naming path+port instead of blank frames, dead
backends caught pre-boot by `meta-app --check`), and the three native tiles
open the installed calculator, editor, and file manager with absolute paths;
no tile opens a browser tab, no tile shares a page, and every icon, program,
and page in the chain was verified to exist.

Next three tasks for another session: (1) decide the permanent home of
`os-build/face/check-servers.sh` (needs lane-owner confirmation) and
consider the shared server helper it recommends; (2) wire `meta-app
--check` into the provisioned-image proof run so a dead tile fails the
build, and re-verify `agents.html` + `:18940` once the relay lane lands;
(3) confirm `StartupWMClass` grouping visually on the Xubuntu guest
(`xprop WM_CLASS`) and add per-tile values for the three native apps if the
WM matches.
