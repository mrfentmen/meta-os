# The four agent lanes — what actually landed

Written 2026-11-03 ~16:10 EST by the reviewing lane. Every claim below has the
command that produced it. Where a check could not run, it says blocked, not pass.

## Branches at review time

| branch | head | commits ahead of main | state |
|---|---|---|---|
| `main` | `0513ed18` | — | has agent-1 and agent-3 merged |
| `agent-1` | `5ecd1360` | 0 after merge | **merged** (tiles, icons, reports) |
| `agent-2` | `f1cf5487` | 0 | **nothing committed yet** |
| `agent-3` | `276ea5b1` | 0 after merge | **merged** (aegis-page + report) |
| `agent-4` | `f1cf5487` | 0 | **nothing committed yet**, live QEMU running |

```
for b in main agent-1 agent-2 agent-3 agent-4; do
  printf "%-8s %s %s\n" "$b" "$(git rev-parse --short $b)" "$(git log -1 --format=%s $b)"
done
```

**One thing to know about the four lanes:** all four agents worked in the same
checkout (`~/Desktop/meta-os`), not in separate git worktrees, and that checkout
was sitting on `agent-1`. So `git status` there showed 125 modified files from
several lanes at once, and any `git add -A` in that tree would mix them. agent-1
and agent-3 escaped because they committed scoped paths; the rest is still
loose in the working tree. Merges were done from a separate worktree
(`/tmp/wt_main`) so nothing in the shared tree was disturbed.

## Merge order taken

1. `agent-1` `52b00701` — Ubuntu-identity cleanup (`rename_user.sh`, greeter
   drop-in, `UBUNTU_INVENTORY.md`, `HACKATHON.md`). 4 files, fast-forward.
2. `agent-3` `276ea5b1` — `aegis-page/` + `AGENT_3_REPORT.md`. Disjoint from (1),
   merged `--no-ff` clean, 0 conflicts. main `5dbf8740`.
3. `agent-1` `4d91419b` — 8 new tiles, 6 new icons, `metaos-update.sh` site copy,
   `AGENT_1_REPORT.md`. Clean. main `082a6f02`.
4. My two fixes on top (see below), then `agent-1` again → main `0513ed18`.
5. My source-tracking and vendor commits, then `agent-1` again → `4e17a7cd`.
6. `agent-2` `c03f13a1` — pages + shared three.js, 0 conflicts (the deletion of
   the per-page vendor copies only merges cleanly *because* the root
   `vendor/three.min.js` was already in main).

**What the image is running right now is older than all of this.** Mounted
read-only while agent-4's VM was up: `/opt/face/meta-desktop.sh` has **19**
tiles (repo: 27), `/usr/share/icons/metaos` has **22** icons (repo: 26), there
is no `/opt/face-site/aegis`, and `session.sh` has no plank guard. Its
`/etc/os-release` is correct (`Meta OS 1.0 (Ribbon)`, `ID=metaos`) and
`/opt/face-site/bus.html` plus `notesd.py` and the three native apps are there.
So the guest needs one re-provision run before the demo shows the 27-tile dock,
the six new icons, Aegis and the single-dock fix.

After every merge: `git status --porcelain` empty, every tracked `*.json` parses
(`bad_json=0`), every tracked `*.sh` passes `sh -n`/`bash -n` by its own shebang
(122 scripts, 0 failures), every tracked `*.py` compiles, every `*.mjs` passes
`node --check`.

## Verdicts

### agent-1 — accepted, with one real hole closed

27 tiles in `meta-desktop.sh`; the 25 distinct icon names all resolve; the 8 new
tiles' page paths all exist in the tree; `metaos-update.sh` copies `aegis-page/`
to `/opt/face-site/aegis/`.

The hole: **20 of the 26 icon PNGs were never committed.** They existed only in
the working tree, so a fresh clone would have built a dock where 20 of 27 tiles
fall back to a blank pixel, and nothing would have said why. Committed in
`e7e2b028` + `5ecd1360`; `git ls-files …/icons/metaos | wc -l` is now 26 and
`shasum -a 256 -c SOURCES.sha256` gives 26 OK.

Also corrected: `SOURCES.sha256` was a **bare filename list** while `SOURCES.md`
said it was a per-file sha256 manifest. It is a real manifest now (that is why
`shasum -c` works above), and the doc says the repo-vs-image re-hash is still a
manual step.

### agent-3 — accepted

`python3 aegis-page/selftest` → `SELFTEST PASS`, 18 checks, from the branch:

```
10 findings (info=2, low=4, medium=4) | KEV catalog v2026.10.30, 1766 entries,
checked=0 flagged=0 unchecked=0 rows=0 | 169 liveness probes (168 LIVE, 1
UNREACHABLE) | 47 run records | newest 2026-11-03T12:05:43.572Z
```

The KEV zero is honest, not hidden: it means no CVE id existed in any finding to
check, and the page says "no known-exploited matches — and nothing was
checkable. Not scanned is not the same as clean." No external URLs
(`grep -c 'https\?://' aegis-page/index.html` → 0), no fabricated CVE, every
panel has a visible missing-file line naming the port. Its own report says the
page is not installed on the image yet — that is the one claim that is still
true and still a gap.

### agent-2 — merged after review

`c03f13a1` — 13 pages, `AGENT_2_REPORT.md`, 13 screenshots. What I checked
myself: no off-localhost automatic request anywhere (only user-initiated
anchors and the explicit "Load CID" PubChem fetch), the shared
`vendor/three.min.js` is present and answers 200, and all four 3D pages run the
real path on the merged tree (`Caffeine — C8H10N4O2 … 24 atoms, 25 bonds`,
`Stopped. Press Play.`). Its failure lines name the port in the house style and
it removed the phone-push feature that called an external worker. Accepted.

### agent-4 — still running, nothing to review

No commit. Its QEMU is alive (serial `/tmp/agent4-ser.sock`, monitor
`/tmp/agent4-mon.sock`, repo mounted read-only through virtfs). Do not touch
`/tmp/metaos.ext4` or start a second VM while that is alive. I did borrow one
`screendump` from its monitor for `captures/dock-live-…T2109Z.png` — read-only,
no input sent to the guest.

## What I fixed myself (files nobody was editing at the time)

- **Three 3D pages could go blank.** `labs/music3d/index.html`,
  `design/meta-musica-notes.html`, `design/meta-scientia-molecules.html` built a
  `THREE.WebGLRenderer` without asking whether this machine has a WebGL context.
  In the VM that throws and leaves an empty canvas with no explanation. All three
  now do what `labs/molecules` already did: probe, and if there is no context,
  say so in the status line and leave the rest of the page working. Proven with
  headless Chrome: `?force2d=1` prints the line on all three, and without the
  flag they still render real structures (e.g. `Caffeine — C8H10N4O2 — 194.19
  g/mol — embedded JSON (24 atoms, 25 bonds)`).
- **Two docks were possible.** `/etc/xdg/autostart/plank.desktop` is installed in
  the image and `session.sh` also started plank two seconds after login. It now
  waits up to 5 s for an existing plank and starts one only if nothing did.
  Tested both ways with a stub `plank`+`pgrep`: running plank → no second start
  (log says so), no plank → plank starts.

## Still loose

- agent-2 and agent-4 have not committed; their lanes need the same review
  before anything else merges.
- Nothing was installed on `/tmp/metaos.ext4` by me tonight (agent-4 holds it).
  So: Aegis tile, Messages tile and the 20 icons are in the tree, and **not
  proven on the guest**.
- Messages (`bus.html`) needs a relay REST URL + token before it is a messenger;
  offline it is a configure screen that says `Status: not connected`.
- No boot, screenshot or port proof was run from this lane tonight.

## Second pass — what the working tree was hiding

After the merges I checked the tree the image is actually built from, and found
that shipping source had never been committed at all:

- `os-build/face/notesd.py` — the service behind Notes, Calendar and Settings
  (port 18937). Untracked.
- `os-build/face/native/meta-notes.py`, `meta-monitor.py`, `meta-agents.py` —
  three of the dock's native apps. Untracked.
- `os-build/face/start.html`, `kiosk.sh`, `app_proof.sh`, `metaos-face.desktop`,
  `metaos-livebg.service`, `about.html`, `agents.html`, `APP_MATRIX.md`,
  `SESSION.md` — untracked.
- The image got all of them because the build copies the working tree. A clone
  would have produced a desktop with no notes service and no Notes/Monitor/
  Agents windows, and `provision.sh` would have FAILed two of its own checks
  (`face start.html`, `face notesd.py`).

All of that is committed now (`178d5752`), and a root-mode `provision.sh` run
against a throwaway root ends with every check OK, including the new
`site aegis/index.html: OK`.

Also committed on its own: `vendor/three.min.js` (`3ba5c6b0`). agent-2 is
consolidating the four per-page copies into that one file and has repointed the
pages at `../../vendor/…`. The new file was untracked, so a clone would have
404ed three.js and every 3D page would have shown the "3D unavailable" line.
Tested after committing: all four pages run the real 3D path again
(`Caffeine — C8H10N4O2 … 24 atoms, 25 bonds`, `Stopped. Press Play.`).

**Still uncommitted in the shared tree (agent-2's lane):** the page repoints and
the deletion of the per-page `vendor/three.min.js` + `LICENSE-three.txt` files,
plus `bus.html` and `surfaces.html` rewrites. That is a coherent change set and
should be committed as one by whoever owns that lane — do not merge the deletion
without the repoint, and do not merge the repoint without the root vendor file
(now in main).

**Still untracked, deliberately:** `os-build/captures/*` except the two
referenced frames, `runs/`, `memory/`, `os-build/handsfree/*`, the drill data,
`os-build/aegis` receipts. Those are generated; committing them is a decision
for the owner, not a fix.
