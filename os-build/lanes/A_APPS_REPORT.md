# Lane A (apps) report — 2026-11-03

Scope: `os-build/face/*` except `agents.html`; APPS array only in `shell.html`.
Image: `/tmp/metaos.ext4`, written via `provision.sh --root` inside a
privileged `ubuntu:24.04` container (macOS cannot mount ext4). No QEMU boot
was done or required for these items; nothing below claims a boot.

## A1. Web tile replaces remote Chrome — PROVEN

What changed: new `os-build/face/start.html` (Meta wordmark, 17 app tiles,
real local services list, loopback only); `shell.html` APPS[0] is now
`{ id: "web", name: "Web", kind: "url", target: "start.html" }`.
Shell window-manager code untouched.

Command (repo):

```
grep -rhoE "https?://[^\"' >]+" *.html *.js | grep -v "127.0.0.1" | sort -u
```

Output excerpt: empty (no external URL in any face page or script;
`start.html` references only relative pages and `http://127.0.0.1:18934`).

File staged to image (`start.html` md5 `19f9f8f8…`, MATCH — see table).
Verdict: PROVEN.

## A2. File-backed notes via notesd :18937 — PROVEN

What changed: new `os-build/face/notesd.py` (stdlib, port 18937);
`POST /notes` writes `$XDG_DATA_HOME/metaos/notes/<id>.json` plus a
readable `~/Notes/<id>.md` mirror; `GET /notes` lists. `notes.html`
rewritten to use it; localStorage stays only as offline cache and the
status line says "cached" (`Showing cached …`) whenever the cache is read.

Commands (daemons on loopback, temp HOME):

```
curl -X POST http://127.0.0.1:18937/notes -H 'Content-Type: application/json' \
  --data '{"text":"persist-check"}'
# → {"ok": true, "note": {"id": "1793707086673-1195", ...}}
kill <notesd>; restart notesd; curl http://127.0.0.1:18937/notes
# → notes: [('1793707086673-1195', 'persist-check')]
ls ~/Notes/
# → 1793707086673-1195.md
```

Output excerpt: note present after daemon restart; `.md` mirror exists with
the text. `notesd.py --selftest`: 11/11 ok, PASS. `app_proof.sh` 6/6
against image code (see Proof). Verdict: PROVEN.

## A3. Calendar persists as ~/Notes/calendar.ics — PROVEN

What changed: same daemon; `POST /events`, `POST /events/delete`,
`GET /export`, `POST /import`; every mutation rewrites
`~/Notes/calendar.ics` (VCALENDAR/VEVENT, DTSTART/DTEND all-day,
RFC-5545 escaping). `calendar.html` has import/export buttons and shows the
file path (`Calendar file: …/calendar.ics …`).

Commands:

```
curl -X POST …/events --data '{"date":"2026-11-10","text":"dentist; 10am, bring card"}'
python3 - calendar.ics <<'EOF'   # parses file back, counts VEVENTs
```

Output excerpt:

```
VEVENT count: 2
DTSTART lines: ['DTSTART;VALUE=DATE:20261110', 'DTSTART;VALUE=DATE:20261111']
DTEND lines: ['DTEND;VALUE=DATE:20261111', 'DTEND;VALUE=DATE:20261112']
ICS CHECK PASS
```

Escaping verified (`dentist\; 10am\, bring card`); import round-trip added 1
event back. Verdict: PROVEN.

## A4. Settings persist through the daemon — INSTALLED

What changed: `notesd.py` `GET /settings` + `POST /settings` against
`~/.config/metaos/settings.json`; `settings.html` writes localStorage (kept
for instant paint) AND the daemon, and restores daemon values on load;
`search.js` (loaded by `shell.html`, whose edits are limited to the APPS
array) re-applies theme/bar/wallpaper from `:18937/settings` on shell boot.

Commands (ran):

```
curl -X POST http://127.0.0.1:18937/settings … \
  --data '{"metaos-theme":"light","metaos-bar":"blue","metaos-wallpaper":"comet-dense"}'
# → {"ok": true, "settings": {"metaos-theme": "light", …}}
curl http://127.0.0.1:18937/settings
cat ~/.config/metaos/settings.json
# → {"metaos-bar": "blue", "metaos-theme": "light", "metaos-wallpaper": "comet-dense"}
```

Daemon round-trip PROVEN by the commands above. The acceptance's final
step — delete the epiphany profile, reload, watch theme/bar/wallpaper come
back — was NOT run (no browser/epiphany on the build host), so the item
verdict is INSTALLED, not PROVEN. Shell-restore snippet is staged in image
`search.js` (md5 MATCH) and `node --check` clean.

## A5. Dashboard shows only live numbers — PROVEN

What changed: `facts.py` adds `distro` (/etc/os-release),
`kernel` (uname), `uptime` (/proc/uptime), `disk_free`, `packages`
(dpkg status count), `agents` (live `GET :18940/agents` count). Old keys
`cpu/mem/disk/net` kept (proof_session + terminal poll depend on them).
`dashboard.html` builds one card per key only from a successful fetch and
prints `backend unreachable on 18932` on failure. No hardcoded values.

Command (daemons from IMAGE paths in container):

```
curl -s http://127.0.0.1:18932/facts | python3 -m json.tool
```

Output excerpt:

```
{"cpu": "load 0.24", "mem": "942M / 7934M", "disk": "32G / 910G",
 "disk_free": "832G free of 910G", "net": "?",
 "distro": "Ubuntu 24.04.5 LTS", "kernel": "7.0.14-linuxkit",
 "uptime": "38m", "packages": "127", "agents": "23"}
```

`agents: 23` was read live from the chrooted image `metaosd`. Verdict: PROVEN.

## A6. Editor + Files + Trash as one system — PROVEN

What changed: `files.py` adds `GET /home` (real `$HOME`, no hardcoded
user); `files.html` Notes/Home quick buttons resolve against it and
`?path=` deep-links `~/Notes`; `editor.html` "Notes" link points at
`~/Notes` via `GET /home`. `trash.html` already renders each entry's
original path out of its `.trashinfo` (unchanged). Editor already saves
through `files.py`.

Acceptance ran as `app_proof.sh` rows 4–6 against image code (see Proof):
trash the `.md` → restore → md5-identical (`52407c29…` both sides);
edit-save new text → read matches. Verdict: PROVEN (data flow; window
clicks were not driven — no browser on host).

## A7. Top-bar search over apps, notes, files — INSTALLED

What changed: `search.js` indexes all 17 dock apps, live notes from
`GET :18937/notes` (offline cache fallback), and files via `:18936/list`
including `~/Notes` filenames from `GET :18936/home`; Enter runs the top
result through the window manager (`toggleApp`/`openWindow`); failures
return `[]` → `No matches`. Loopback only — no external network calls.

Ran: `node --check search.js` clean; search-apps/notes/files logic
reviewed; live `:18937`/`:18936` queries exercised by the same code paths
in A2/A6. Not run: typing + Enter inside a real shell window (no browser
on host). Verdict: INSTALLED.

## A8. Musica wav is real in the image — PROVEN

No file change needed: `musica.html` already points at
`http://127.0.0.1:18934/os/worlds/musica/sessions/hn029-chipsynth/normalized/take-006.wav`.

Command (python http.server rooted at the IMAGE's `/opt/face-site`):

```
curl -o /tmp/take.wav -w "http %{http_code} bytes %{size_download}" \
  http://127.0.0.1:18934/os/worlds/musica/sessions/hn029-chipsynth/normalized/take-006.wav
```

Output excerpt: `http 200 bytes 320798`; image holds
`take-006.wav` 320798 bytes (`ubuntu ubuntu`, pre-existing stage).
Never a 404. Verdict: PROVEN.

## A9. Four 18934 iframes return 200 in-image — PROVEN

No dock-target change needed: all four pages exist in the image and the
anchor exists.

Commands (same image-rooted server):

```
for p in surfaces.html labs/molecules/index.html index.html logo-studio.html; do
  curl -o /dev/null -w "%{http_code}" http://127.0.0.1:18934/$p; done
grep -c "board-custos" /mnt/d/opt/face-site/surfaces.html
```

Output excerpt: `200 200 200 200`, anchor count `3`. Verdict: PROVEN.

## A10. Provisioning carries the new daemon — PROVEN

What changed: `provision.sh` writes `face-notesd.service`,
adds it to `face.target` Wants/After, hand-makes the enable link in
`--root` mode, stages/verify-lists `start.html notesd.py notes.html
calendar.html settings.html dashboard.html search.js app_proof.sh`,
kills `notesd.py` in live-mode cleanup, and live-checks
`:18937/notes|/settings|/events`. Header now says eight backends.

Command: `sh /repo/os-build/face/provision.sh --root /mnt/d` (container).

Output excerpt:

```
unit face-notesd: OK
face start.html: OK
face notesd.py: OK
face app_proof.sh: OK
face.target enabled: OK
```

The `:18937` live rows were verified by direct curl in the container
(A4/A5 evidence). `proof_session.sh` still 9/9 (see Proof). Verdict: PROVEN.

## Proof

`bash /opt/face/proof_session.sh` (IMAGE copy, daemons from IMAGE paths,
metaosd via image node in chroot) — still 9/9:

```
18900  /shell.html        200              200            PASS
18931  POST /launch       403 refusal      403            PASS   refusal expected
18932  /facts             200              200            PASS
18933  TCP connect        connect          open           PASS
18934  /index.html        200              200            PASS
18935  /rooms             200              200            PASS
18936  /trash             200              200            PASS
18940  /status            200              200            PASS
18940  /agents            200              200            PASS
PASS=9 FAIL=0 / proof_session: PASS (9/9)
```

New `os-build/face/app_proof.sh` (IMAGE copy, same daemons):

```
PASS 1 write-note (id=1793707193120-2899)
PASS 2 read-back
PASS 3 md-mirror (/tmp/guesthome/Notes/1793707193120-2899.md)
PASS 4 trash (name=1793707193120-2899.md)
PASS 5 restore-identical (md5=52407c29fbb0dddca350fb0f783e4807)
PASS 6 edit-save-read
PASS=6 FAIL=0 / app_proof: PASS (6/6)
```

`app_proof.sh` has no `|| true`; exits 1 on any failure; cleans up its
proof note and file. (The `|| true` hits in `provision.sh` are pre-existing
best-effort cleanup/link lines, none around a proof assertion.)

md5 repo vs image (`md5sum` repo file vs `md5sum /mnt/d/opt/face/file`):

| file | repo md5 | image md5 | |
|---|---|---|---|
| shell.html | e3696e0a…33a8 | e3696e0a…33a8 | MATCH |
| start.html | 19f9f8f8…809d | 19f9f8f8…809d | MATCH |
| notes.html | 880a027b…c8c | 880a027b…c8c | MATCH |
| calendar.html | 4dfef324…41be | 4dfef324…41be | MATCH |
| settings.html | 5d1517f4…9040c | 5d1517f4…9040c | MATCH |
| dashboard.html | 8833a8b9…ded8e | 8833a8b9…ded8e | MATCH |
| files.html | cff4a0a6…e51a | cff4a0a6…e51a | MATCH |
| editor.html | 63b0f381…5415 | 63b0f381…5415 | MATCH |
| search.js | 103cbf35…5384 | 103cbf35…5384 | MATCH |
| notesd.py | 3d019e1d…04c4 | 3d019e1d…04c4 | MATCH |
| facts.py | 188f36ae…1d92 | 188f36ae…1d92 | MATCH |
| files.py | 5d77ee93…4db3e | 5d77ee93…4db3e | MATCH |
| app_proof.sh | 4f0d2e9e…be03 | 4f0d2e9e…be03 | MATCH |
| APP_MATRIX.md | 11f72801…aa78 | 11f72801…aa78 | MATCH |
| proof_session.sh (tools/ vs image) | f69bc6d3…38ec | f69bc6d3…38ec | MATCH |
| provision.sh | d5d9ff2c…0930f | 48ee86d1…c289dd | DIFF, explained below |

`provision.sh` DIFF is a parallel lane's later insertion, not mine: both
copies contain all my notesd/start.html/18937 sections (verified by grep);
the repo copy additionally has `§1a2 native desktop programs` and `§1a3
plank dock theme` (payload-theme-adjacent, outside my lane), added after my
`--root` staging run. I did not re-stage another lane's work. Unchanged
owned-adjacent files also MATCH (tile.js, workspace.js, board.py,
launcher.py, ptyd.py, trash.html, musica.html).

## Honest limits

- No QEMU boot; no epiphany. Items needing a real browser (A4 profile-wipe
  reload, A7 Enter-in-window-manager, dock clicks generally) are marked
  INSTALLED with the mechanism staged, not PROVEN.
- `e2fsck -n -f` on the image reports 78 pre-existing `has filetype set`
  entries in system dirs (`/root/.local`, `/usr/share/doc`,
  `/var/lib/systemd`) — build artifacts, none under `/opt/face` or my unit
  files. Final ro-mount spot check md5-matched; image unmounted cleanly.
- Mid-session the two `http.server` daemons wedged (accepted, empty reply)
  while stdlib daemons stayed healthy; killed and restarted them, then
  re-ran proof_session 9/9. Cause not root-caused; guest systemd units are
  `Restart=on-failure` so a wedged static server restarts on boot path.
- The shared repo tree shows other lanes' parallel edits (e.g. launcher.py,
  board.html); I touched only my lane's files.
