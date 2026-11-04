# T4 REPORT — worlds, labs, content and demo proof (agent-t4)

Branch `agent-t4`, worktree `/tmp/agent-t4`. No merge, no push. No QEMU
(`pgrep -f qemu-system` exit 1 before and after). No paid API calls. Built by
five section subagents; diff reviewed against the brief; this report assembled
last.

## A. Worlds data (os/worlds, 112M, 295 files, 12 worlds)

`du -sh os/worlds` → 112M: science-lab 94M (93M `hortus/records` hunts),
musica 17M (10M session wavs + 6.4M export zip), officina 304K, custos 148K,
8 spec packs 16–40K. Page-read minimum is 565K. Entry files: custos
`runs/patrol-001.jsonl` (11 rows), officina 9 run JSONs, musica
`hn029-chipsynth/session.json`, science-lab `records/exports/board.json`,
each world's `pack.json` — all parse. Referenced-but-missing: none (23/23
fetched paths exist). On-disk-but-unread: musica sessions/exports bundle,
all of science-lab, custos proofs/states, officina runtime. All 85 JSON +
21 JSONL parse, 0 failures. Duplicates: `musica/gate-packet/` byte-copies
canonical files (sha256-identical catalogues) — frozen submission packet,
not touched. Rule: ship pack contract + fetched entries + generators;
hunts/wavs/zips/proofs are generate-or-omit. Trimmed: nothing (only
trimmable weight is other lanes' evidence — cross-lane decision, not taken).
New `os/worlds/validate_worlds.py` (stdlib): clean run
`OK 106 files (76 json, 21 jsonl, 9 session files, 12 packs)` exit 0;
negative test on scratch copy fails correctly, original byte-identical.
Wiring request (verify_tree.sh owner): file `os-build/tools/verify_tree.sh`,
anchor `before # --- output`, command `python3 os/worlds/validate_worlds.py`.

## B. Dispatch boards (surfaces.html +491, board.html untouched)

13 boards offered (Lab, Hortus, Gate, Evidence/BOLO/Timeline/Receipt, Costs,
Officina, Custos, Systems, Tiers/Cameras + 8 dispatch boards). Loads:
Officina 9/9, Custos 34 patrol (+20 proof = 54 shown), Systems 10/10 packs;
Lab/Gate/Costs rooms show NAMED empty states (`os/lab/records.json`,
`gates/delaney/manifest.json`, `server/queue/spark_guardrail_state.json`,
`/api/crew/status` — data owners, not parse errors). Every board: record
count + last-update (`54 records · updated 11/1/2026, 6:58:23 AM · from 4
files`), empty states name pack + fill command (e.g. officina
`design_loop.py 20 7 …/overnight-run-002.json`), filters persist via
`localStorage dispatch-filter-<pack>` (verified reload), detail panel shows
source file + line + full JSON, malformed rows skip with file:line (0 live,
selftest proves path), timestamps `toLocaleString()` desktop-clock. Removed:
none (every pack declares owner agents in pack.json — nick lists captured).
Perf: internal 500-record parse+render figure from section work was not externally reproducible (parser lives in an IIFE; no handle from outside). Re-measured headless: selftest section — parser over real+malformed input plus render, 9/9 pass — visible within 66 ms of navigation start. Page renders its 54 live records with zero errors. 1366×768 screenshot OK.
12 captures (9 boards + selftest + layout + degraded). 118 requests, **0
off-localhost**; backend-down run (11 routes aborted): named empty states,
PAGEERRORS none. Nav 23↔23, dead links []. Keyboard: native
inputs/selects/buttons, logical tab order, no traps. Search
case+accent-insensitive (`norm()` NFD strip; `café→cafe` asserted). Inline
selftest **9/9 passed** (`dispatch-selftest: 9/9 passed.`).

## C. Science lab + 3D

One three.js copy in tree: `vendor/three.min.js` (633,338 B, r152 UMD) —
nothing to dedupe (unified 2026-11-03); all four 3D pages load it
(molecules:52, scientia:57, music3d:52, musica-notes:51), zero pageerrors.
`?force2d`/`?no3d` fallback with WHY on molecules + scientia (forced vs
genuine messages), 2D SVG schematic from validated data (24 circles/25
lines for caffeine). Default loads `labs/molecules/data/caffeine.json`
(PubChem CID 2519): `C8H10N4O2 — 194.19 g/mol — 24 atoms, 25 bonds`.
Visibility guard: hidden 0 frames/2s vs visible 104/2s (measured). Canvas
`tabindex=0 role=application`, arrows rotate, +/− zoom; resize keeps aspect
(1366×461 a=2.96, 1440×540 a=2.67); labels readable at 1366×768. Removed:
none (11 compounds + 8 SDF entries, all with data). Review pages: viewport
meta fixed (bolo/timeline/cannot-do), no tables exist (grep 0), footers name
sources. No CDN (grep + request log `EXT_REQS: []`). New
`labs/check_assets.py`: `OK: 6 pages, all local assets resolve, no CDN tag
assets.` exit 0; node suites molecules 13/13 + review 6/6 (music notes-data module 5/5). Frame time (rAF deltas, headless Chromium, 59 frames, evaluate loop): molecules **17.37 ms avg / 25 ms max**. Scientia not re-measured here; section figure retained as section-measured. How-to-add-a-structure:
new `labs/molecules/README.md` (SDF→data/<id>.json + meta.json + CAPTIONS,
verify with node tests + check_assets, formulas from PubChem).

## D. Music

labs/music3d (3D lab, triangle synth) + design/meta-musica-notes.html (3D
design ref, sine synth); both draw AND play. **CPU fix**: rAF ran while
stopped (stopped/3s: labs 109, design 146 frames) → loop now runs only while
playing && visible + one settling frame: stopped total **1 frame** each,
post-pause probe flat, playing 127–185/3.5s. `?force2d`/`?no3d` audio-only
fallback proven (oscillators scheduled 3+4, 0 errors, 0 pre-gesture
AudioContext). Tracks: labs "C major scale, mixed values" 15 notes/26
beats/~17.0s@92bpm; design equal-beats 15/15/7.5s@120bpm; missing `?track=`
fails with path + how-to. Volume shared key `musica.volume` (set 37 →
reload → 37, both pages). Pitch sequences byte-identical both pages; kept
both (lab vs design-reference, different jobs). No autoplay (0 media
elements, 4 gesture-gated resumes), async load only, activeElement BODY on
load. In-scope audio: none (pure synth, nothing to trim); face take-006.wav
316K read-only (12 takes). 5 captures.

## E. Aegis + messages

Panels: findings `data/findings.jsonl` (10, newest-first, counts by
severity), KEV `data/KEV.json` (catalog 1766 entries; findings checked 0 — no CVE ids; matched 0), liveness `data/LIVENESS.json` (169 probes: 168 LIVE + 1
UNREACHABLE), runs `data/runs.jsonl` (47). Missing files name themselves;
empty states explain, zero apologies; removed panels: none (every number
sourced). 5000-row full timing not re-measured headless (renderer is page-scoped like the board parser); 500-row cap with stated note verified in code. No-freeze claim rests on the cap, not a timing number. Timestamps
`YYYY-MM-DD HH:MM:SS UTC` (fmt(), footer "All times UTC"). Selftest
`aegis-page/selftest` +§6 → **SELFTEST PASS** exit 0; wiring request
(verify_tree owner): file `aegis-page/selftest`, anchor exit code, command
`./aegis-page/selftest --quiet`. Missing-data + real-data screenshots taken
(file restored, `git status` clean of the deletion). bus.html: localStorage
Upstash-REST source, malformed rows `.msg.skipped` with line, empty state
names queue, no push-worker code (only removal comment), `HH:MM:SS` rows,
`:focus-visible` 2px outline added (activeElement=#compose verified). Zero
http(s) URLs both pages; 28 headless requests all 127.0.0.1. 1366×768 both.

## F. Demo proof + docs

DEMO.md/HACKATHON.md append-only (+101/+103, 0 deletions): beats run
(notesd selftest 11/11 PASS; boot/click/guest beats marked cannot-run with
why), stale claims corrected (captures, dock 27→30, sums, 43→44 calls,
18→25 checks), beat zero + division beats + agent-job PENDING, screenshot
audit (board PNGs are this lane's, listed below; 5 theme mockups + cursor suspects for theme lane, cited
files verified present, 2 cited captures MISSING), HACKATHON evidence-link
gaps + one-click-disprovables + limits + real/thin/missing status, 3 doc
commands tested verbatim. Ports table (read-only): 18900/18931/18932/18933/
18934/18935/18936/18937 files verified, answering unverified without boot;
18940 source NOT FOUND in tree; 8935 queue file verified. Host squatters on
18932–18937 (404s) flagged. ISO: tree-only, no master. Stage-breakers:
stale numbers read aloud; port squatters/missing 18940; no fresh boot proof
since sibling edits.

## G. Proof and reporting

Console sweep (playwright, 1440×900, local server, 17 page-loads): 16 pages
0 errors 0 external; surfaces.html 11×404 only —
`os/lab/records.json`, `gates/delaney/manifest.json`,
`server/queue/spark_guardrail_state.json`, `/api/crew/status`,
`os/worlds/*/runs/` dirs — every one named in-page by an empty state.
External sweep: 0 off-localhost requests across all pages (grep confirms 0
http(s) URLs in owned pages; bus manifest/icon links root-relative local).
`git diff --stat`: 13 files, +1170/−47, all inside owned paths (verified by
path filter — empty outside). No QEMU (pgrep exit 1). Commits on `agent-t4`
only (this report + code, single commit below); `main` untouched by this lane: local `main` tip belongs to other lanes' commits; this lane has made zero commits anywhere yet (single commit below, on `agent-t4` only; verified post-commit with `git show --stat HEAD`).

Captures added (os-build/captures/, 33 PNGs, dated+sized, one line each):
- `aegis-missing-1366x768-2026-11-04.png`: security dashboard
- `aegis-real-1366x768-2026-11-04.png`: security dashboard
- `aegis-real-1440x900-2026-11-04.png`: security dashboard
- `board-custos-1440x900-2026-11-04.png`: dispatch board render
- `board-degraded-backend-down-1440x900-2026-11-04.png`: dispatch board render
- `board-dep-1440x900-2026-11-04.png`: dispatch board render
- `board-doe-1440x900-2026-11-04.png`: dispatch board render
- `board-ems-1440x900-2026-11-04.png`: dispatch board render
- `board-fdny-1440x900-2026-11-04.png`: dispatch board render
- `board-hospital-1440x900-2026-11-04.png`: dispatch board render
- `board-layout-1366x768-2026-11-04.png`: dispatch board render
- `board-mta-1440x900-2026-11-04.png`: dispatch board render
- `board-nypd-1440x900-2026-11-04.png`: dispatch board render
- `board-officina-1440x900-2026-11-04.png`: dispatch board render
- `board-selftest-1440x900-2026-11-04.png`: dispatch board render
- `bus-focus-1366x768-2026-11-04.png`: messages board
- `bus-msgs-1366x768-2026-11-04.png`: messages board
- `bus-msgs-1440x900-2026-11-04.png`: messages board
- `lab-molecule-1440x900-2026-11-04.png`: lab/review render or fallback
- `lab-molecule-fallback-1440x900-2026-11-04.png`: lab/review render or fallback
- `lab-molecule-labels-1366x768-2026-11-04.png`: lab/review render or fallback
- `lab-review-bolo-1366x768-2026-11-04.png`: lab/review render or fallback
- `lab-review-cannotdo-1366x768-2026-11-04.png`: lab/review render or fallback
- `lab-review-timeline-1366x768-2026-11-04.png`: lab/review render or fallback
- `lab-science-review-1366x768-2026-11-04.png`: lab/review render or fallback
- `lab-scientia-1440x900-2026-11-04.png`: lab/review render or fallback
- `lab-scientia-fallback-1440x900-2026-11-04.png`: lab/review render or fallback
- `lab-scientia-labels-1366x768-2026-11-04.png`: lab/review render or fallback
- `music-force2d-1440x900-2026-11-04.png`: music page render or fallback
- `music3d-labs-1366x768-2026-11-04.png`: 3D notes lab
- `music3d-labs-1440x900-2026-11-04.png`: 3D notes lab
- `musica-design-1366x768-2026-11-04.png`: design music reference
- `musica-design-1440x900-2026-11-04.png`: design music reference

Cross-lane requests: (1) verify_tree owner — wire `python3
os/worlds/validate_worlds.py` (anchor before `# --- output`) and
`./aegis-page/selftest --quiet` (anchor exit code). (2) Confirm root
`board.html`: create it or drop from scope (only `board/board.html` exists,
other lane). (3) Missing data files for Section A owners:
`os/lab/records.json`, `gates/delaney/manifest.json`,
`server/queue/spark_guardrail_state.json`. (4) dsny board unassigned (spec
pack, no dispatch board). (5) face lane: `musica.html:36` autoplay attempt
vs no-autoplay rule. (6) Theme-lane mockups/cursor/dock-three-languages captures unreferenced.

Next three tasks with another session: (1) re-run `proof_boot.sh` + guest
`proof_session.sh` on the demo machine after these edits and replace the two
missing cited captures; (2) fill the three missing data files (or confirm
their owners' empty-state contract) to clear the 11 surfaces 404s; (3) land
the two verify_tree wirings and re-run the tree gate green.
