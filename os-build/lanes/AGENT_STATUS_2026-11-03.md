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

### agent-2 / agent-4 — nothing to review yet

No commits. Their work is in the shared tree as uncommitted changes, and agent-4
has a QEMU up (serial `/tmp/agent4-ser.sock`, monitor `/tmp/agent4-mon.sock`,
repo mounted read-only through virtfs), so it is mid-proof. Do not touch
`/tmp/metaos.ext4` or start a second VM while that is alive.

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
