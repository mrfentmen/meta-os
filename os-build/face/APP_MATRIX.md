# Face app → backend matrix (AGENT 3 audit)

Source: `os-build/face/*.html` fetch/WebSocket URLs vs `os-build/face/*.py` handlers.
Checked 2026-11-03. Final state is after AGENT 3 fixes listed below.
`PROVEN` = handler exists in `*.py` (or static server) AND page shows
`backend unreachable on <port>` instead of blank content.
`BROKEN` = no handler, wrong URL, or blank-window path (all fixed unless noted).

Static servers (no `.py` handler, `provision.sh` units):
- `:18900` = `python3 -m http.server 18900` in `$DST` — serves all `*.html`.
- `:18934` = `python3 -m http.server 18934` in `$SITE_DST` — serves repo-root
  product pages staged by `provision.sh:49-97`
  (`index.html`, `surfaces.html`, `logo-studio.html`, `js/app.js`,
  `labs/molecules/index.html`, `labs/music3d/index.html`,
  `os/worlds/*/pack.json`, musica wav, officina/custos runs).

| dock app | page target | fetch / WS | port | handler | verdict | notes |
|---|---|---|---|---|---|---|
| web | `start.html` (local start page) | none external; links to `*.html` + `127.0.0.1:18934` | — | static `face-http` | PROVEN | Was BROKEN (A1): `APPS[0]` pointed at `https://meta-os.pages.dev`, blank offline. Now `start.html`: Meta wordmark, 17 app tiles, real local services list. `grep -E https?://` over `*.html,*.js` shows only `127.0.0.1`. |
| terminal | built-in `buildTerminal()` | `ws://<host>:18933/` + `http://<host>:18932/facts` | 18933 / 18932 | `ptyd.py:handle()` WS branch + `_pump_ws()` / `facts.py:do_GET /facts` | PROVEN (fixed) | Was BROKEN: single-client `LOCK` → second client got `[busy]`/503, agent+Terminal collided. Now `POOL=Semaphore(4)`, same wire protocol (handshake bytes, frame format, `[busy]` only when pool full). `onclose`/`onerror` show `backend unreachable on 18933`; facts span shows `backend unreachable on 18932`. Selftests: `--selftest`, `--selftest-ws`, `--selftest-pool` all PASS. |
| files | `files.html` | `GET /list`, `POST /trash`, `POST /mkdir`, `GET /home` | 18936 | `files.py:do_GET /list`, `do_POST /trash`, `do_POST /mkdir`, `do_GET /home` | PROVEN (fixed) | `load`/`trash` already had unreachable; `mkdir` had no `.catch` → added `backend unreachable on 18936`. Notes/Home quick buttons resolve against the real `$HOME` from `GET /home`; `?path=` deep-link opens `~/Notes` (A6). |
| dashboard | `dashboard.html` | `GET /facts` | 18932 | `facts.py:do_GET /facts` (distro, kernel, uptime, mem, disk_free, packages, agents) | PROVEN | Cards render only from a successful fetch (A5); stamp shows `backend unreachable on 18932` on failure. No hardcoded values. |
| editor | `editor.html` | `GET /read`, `POST /save`, `GET /home` | 18936 | `files.py:do_GET /read`, `do_POST /save`, `do_GET /home` | PROVEN | Both paths show `backend unreachable on 18936`. Saves through `files.py` into `$HOME`; "Notes" link points at `~/Notes` via `GET /home` (A6). |
| notes | `notes.html` | `GET /notes`, `POST /notes`, `POST /notes/delete` | 18937 | `notesd.py` notes store | PROVEN | Was localStorage-only (A2). Now persists to `$XDG_DATA_HOME/metaos/notes/<id>.json` + `~/Notes/<id>.md` mirror. localStorage stays only as offline cache and the status line says "cached" whenever it is read. |
| agents | `agents.html` | `GET /status`, `GET /agents`, `GET /jobs`, `POST /jobs`, `POST /halt` | 18940 | agent relay (out of scope, not touched) | PROVEN* | Page already distinguished empty relay; extended to `backend unreachable on 18940` on every catch. Relay itself untouched per task. |
| board | `board.html` | `GET /rooms`, `GET /messages`, `POST /post` | 18935 | `board.py:do_GET /rooms`, `do_GET /messages`, `do_POST /post` | PROVEN (fixed) | Was BROKEN: `poll().catch(()=>{})` swallowed errors, `loadRooms` had no catch, no status element → blank window. Added `#status` + `unreachable()` → `backend unreachable on 18935`; added catches on rooms/messages/post. |
| calendar | `calendar.html` | `GET /events`, `POST /events`, `POST /events/delete`, `GET /export`, `POST /import` | 18937 | `notesd.py` events store + `calendar.ics` writer | PROVEN | Was localStorage-only (A3). Events persist as `~/Notes/calendar.ics` (VCALENDAR/VEVENT, DTSTART/DTEND, RFC-5545 escaping), rewritten on every change; import/export buttons in UI; file path shown. |
| calc | `calculator.html` | none (pure JS) | — | none needed | PROVEN | No backend; `Error` on div-by-zero, never blank. |
| settings | `settings.html` | `GET /facts` + `GET /settings`, `POST /settings` | 18932 / 18937 | `facts.py:do_GET /facts`, `notesd.py` settings store | PROVEN | Stamp shows `backend unreachable on 18932`. Settings persist (A4) through the daemon to `~/.config/metaos/settings.json` (`GET /settings`); shell keeps its localStorage read for instant paint and `search.js` restores daemon values on boot, so theme/bar/wallpaper survive an epiphany profile wipe. |
| trash | `trash.html` | `GET /trash`, `POST /restore`, `POST /delete`, `POST /empty` | 18936 | `files.py:do_GET /trash`, `do_POST /restore`, `do_POST /delete`, `do_POST /empty` | PROVEN (fixed) | Was BROKEN: `/empty` had no `.catch` → silent stuck on `Loading...`. Added catch → `backend unreachable on 18936`. All paths now show it. |
| imperium | `http://127.0.0.1:18934/surfaces.html` | iframe + wav/js fetches inside page | 18934 | static `face-site` http.server | PROVEN | File exists in repo (`surfaces.html`); staged by `provision.sh`. Shell fallback shows `backend unreachable on 18934` if probe fails. |
| science | `http://127.0.0.1:18934/labs/molecules/index.html` | iframe | 18934 | static `face-site` | PROVEN | `labs/molecules/index.html` exists; staged. Same shell fallback. |
| musica | `musica.html` → `http://127.0.0.1:18934/os/worlds/musica/.../take-006.wav` | `<audio src>` | 18934 | static `face-site` wav | PROVEN | `take-006.wav` exists in repo; `provision.sh:79-83` stages it. `error` → `backend unreachable on 18934`. |
| custos | `http://127.0.0.1:18934/surfaces.html#board-custos` | iframe | 18934 | static `face-site` | PROVEN | Anchor in `surfaces.html`; same fallback. |
| officina | `http://127.0.0.1:18934/index.html` | iframe | 18934 | static `face-site` | PROVEN | `index.html` exists; same fallback. |
| shell aux | `search.js` | `GET :18936/list`, `/list?path=`, `/read` (bounded), `GET :18936/home`, `GET :18937/notes` | 18936 / 18937 | `files.py`, `notesd.py` | PROVEN | 17 apps + live notes (daemon with offline cache) + `~/Notes` filenames. Failure returns `[]` → `No matches`, never blank. Enter opens the top result in the window manager. No external network calls (loopback only). Also restores theme/bar/wallpaper from `:18937/settings` on shell boot. |
| shell aux | `notify.js` | `GET :18935/messages?room=general` | 18935 | `board.py:do_GET /messages` | PROVEN | Failure logs + keeps `No messages yet.` dropdown; never blank. |
| launcher (no dock button) | `shell.html:launchBackend()` | `POST /launch`, `GET /apps`, `OPTIONS /launch` | 18931 | `launcher.py:H.do_POST /launch`, `do_GET /apps`, `do_OPTIONS` | PROVEN (fixed) | Was BROKEN twice: (1) `shell.html` fetched relative `/launch` → `:18900` static server 404; fixed to `http://<host>:18931/launch`. (2) No `OPTIONS`/CORS preflight + no `GET`; added both. |

## launcher allow-list: Debian spike → Xubuntu 24.04.5 (honest mapping)

Verified against `/private/tmp/xubuntu-base.iso` `casper/filesystem.manifest`
(1876 lines, Xubuntu 24.04.5 Noble, hash `4ed869eb…` per `BASE_FACTS.md`).
Live `/tmp/metaos.ext4` could not be mounted for a direct check because
QEMU (`qemu-system-aarch64 … -drive file=/tmp/metaos.ext4`) was running;
mounting a live root read-write would corrupt it. Mapping below is from the
base manifest, which is what the carrier image is built from.

| Debian spike `ALLOW` (absent) | Xubuntu 24.04.5 reality | new `ALLOW` | evidence |
|---|---|---|---|
| `pcmanfm` | absent (LXDE) | `thunar` (`["thunar"]`) | `thunar 4.18.8-1build3` present; `pcmanfm` absent |
| `lxterminal` | absent (LXDE) | `xfce4-terminal` (`["xfce4-terminal"]`) | `xfce4-terminal 1.1.3-1build1` present; `lxterminal` absent |
| `mousepad` | present | `mousepad` kept | `mousepad 0.6.1-1build2` present |
| `orage` | absent (deprecated); no standalone calendar in base | `thunderbird` (`["thunderbird"]`) | `orage` absent, `gnome-calendar` absent; `thunderbird 2:1snap1-0ubuntu3` + `snap:thunderbird` present and ships calendar. Web `calendar.html` remains the primary calendar; native entry is calendar-capable. |
| `galculator` | absent | `mate-calc` (`["mate-calc"]`) | `galculator`, `gnome-calculator` absent; `mate-calc 1.26.0-1build2` present |
| `chromium` | absent as deb | `firefox` (`["firefox","--new-window","about:blank"]`) | `chromium` absent; `firefox 1:1snap1-0ubuntu5` + `snap:firefox` present (default Xubuntu browser). `kiosk.sh` `epiphany` is also absent from base. |

Old Debian names now correctly return `403 not allowed`; new names launch
on the guest (`500 not installed` on Mac dev host is expected — binary
absent here, present in Xubuntu guest).

## ptyd pool (same wire protocol)

- `LOCK = threading.Lock()` → `POOL = threading.Semaphore(MAX_SESSIONS=4)`.
- `handle()`: `POOL.acquire(blocking=False)`; `503 busy` / `[busy]` only when
  all 4 slots are held; `POOL.release()` in the same `finally` as before.
- No change to: handshake (`Sec-WebSocket-Accept`), frame encode/decode,
  `pre` bytes for raw TCP, `80x24` winsize, `--selftest` / `--selftest-ws`.
- New `--selftest-pool` (2 concurrent raw clients, both must see echo,
  neither may see `[busy]`) PASS.

## never-blank windows

Every backend-dependent page now contains the literal
`backend unreachable on <port>` in its error path (verified by grep):
`dashboard 18932`, `settings 18932`, `shell terminal 18932+18933`,
`board 18935`, `files/editor/trash 18936`, `musica 18934`,
`agents 18940`, `shell url fallback` (port extracted from target),
`shell launch` (`backend unreachable on 18931`).
`shell.html` window manager (drag/min/close/alt-tab) and `APPS` order were
not changed; only the `url` branch gained a hidden fallback div + `no-cors`
probe, and `launchBackend` URL was fixed.

## install

Changed files are installed to `/opt/face` on `/tmp/metaos.ext4`
(QEMU down at install time — see `provision.sh --root` / mount log in task
report). `provision.sh --root <mnt>` file list verified after copy.
