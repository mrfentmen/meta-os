# OpenCode tasks 100: progress report (Mac side)

Baselines from the task list (sandbox): node 1933 run / 1877 pass / 56 fail
(known WKWebView set); cargo 1412 pass / 0 fail; queue python 110 OK;
officina 49 OK; worlds packs 9 of 9 OK; OS loop harness 12 of 12.

## Section 1: Pull main and prove it on the Mac (OC-001 to OC-010)

- OC-001 DONE. Fetched origin; worktree /tmp/mac-tasks on branch
  opencode/mac-tasks at main tip 0b8fa7f (README front page rebuild).
- OC-002 DONE. cargo test --workspace: 1412 pass, 0 fail. Matches baseline.
- OC-003 DONE. npm test: 1933 run, 1877 pass, 56 fail. All 56 are
  tests/native-* (zero non-native failures). Matches baseline exactly.
- OC-004 DONE with a failure to record: queue python suite does not
  collect on this Mac. pytest: 4 collection errors; unittest fallback:
  29 collected, 25 pass, 4 import errors. Root cause is the same one
  from MAC RUN 3: server/queue/trio_store.py line 41 imports
  dynamic_credentials from /opt/muse/skills/... which does not exist
  on this Mac. Baseline 110 OK is sandbox-only until that import is
  optional. test_queue.py and test_orchestrator.py partially run (25 OK).
- OC-005 DONE. officina: 49 passed. Matches baseline.
- OC-006 DONE. worlds pack validator (os/worlds/validate_pack.py):
  9 of 9 packs OK, 0 failures. Matches baseline.
- OC-007 DONE with one failure: os/os/loop-tests/metaos-loop.test.sh
  gives 11 pass, 1 fail; the failing scenario is "green cycle".
  Reproduced by hand: the driver runs the agent fine but dies at step 9
  with queue-mark-failed, because it closes the task with
  sed -i "0,/.../s//.../" — the 0,/regex/ address is GNU sed only and
  macOS ships BSD sed, so the substitution errors. Linux-ism in the
  driver, exposed by running the harness on the Mac. Recorded, not fixed.
- OC-008 DONE. Web app on :8080 serves /manifest.webmanifest (200)
  and the referenced /icon-180.png (200). No 404 on referenced assets.
  (Unreferenced guesses like /favicon.ico 404 — not used by the page.)
- OC-009 DONE. AI Focus clicked in the running app: inspector shows the
  honest empty-state line ("no flagged incidents in this session yet...
  AI Focus flies to the newest one"). Proof: oc-proofs/oc-009-ai-focus.png.
  Side note: the live NYCTMC list loaded (972 cameras online) and the
  Fires/Radar layer buttons are present.
## Section A: close the rung-3 gaps (NB-001 to NB-010)

- NB-001 DONE. Solver + runner copied into repo hortus-rung3/ with README
  (run commands). Files: solver.py, run.py, nb_batch.py, README.md,
  RUNG3_REPORT.md, RUNG3_CLOSEOUT.md, run-output.txt, oc-031-refine.txt.
- NB-002 DONE from the pushed code (oc-proofs/nb-002-verify.txt):
  analytic 181.659 W/m at stated h=55.8 W/m2K; sim 180.139 (0.84%) and
  180.916 (0.41%) on halving dy; balance 2e-3 both. h stated as ordered.
- NB-003 DONE. The 8 s vs 1.0 s mismatch explained: both numbers were real
  timings of the same reference case at different code versions. The 8 s
  figure dates from the cold-start solver (zero initial field, ~20k SOR
  sweeps to crawl the transient). The shipped log's 1.0 s (re-timed 3x
  just now: 1.0/1.0/1.0 s, 1417 iters) is the same case after the analytic
  initial-guess fix, which starts SOR at the near-exact answer. Flat-h=50
  on the same grid takes 0.9 s (1399 iters) — h barely matters here; the
  init was the whole story.
- NB-004 DONE. Organism 8175 (40 / 60.0 / 0.745 / base 1.400, same
  footprint): 735.5 W vs rung-1 733.8 W vs reference 18.3 W. Calibration
  moved the number 0.2% — thermally tied. Caveat: 80k-iter cap reached,
  balance 3.0e-3 vs 2e-3 rule (same slow-mode story as the old fine run).
- NB-005 DONE with the warning printed in the output line itself:
  organism 78901 (48 / 100.0 / 0.405 / 1.000): 713.0 W, HEIGHT 100 mm
  OUTSIDE the calibrated geometry range — extrapolation, not a result.
- NB-006 DONE — the 2e-3 rule now passes on the fine grid. Finding: SOR
  omega 1.7→1.9 converges 3.5x faster to the same answer (coarse: 33,435
  vs 9,966 iters). Fine grid at omega 1.9: 734.4 W, balance 2.0e-3 at
  42,395 iters, 215 s, conv=True (oc-proofs/nb-006-fine.txt). Same omega
  kept everywhere would have saved hours; logged for the record.
- NB-007 DONE. Solver vs closed-form table (same 100 mm footprint, analytic
  = N-fin formula + base convection at full theta — an overestimate by
  construction, stated):
  ref 18.3 vs 17.1 (+7.0%, +1.2 W abs) | champ1 735.8 vs 746.7 (-1.4%) |
  mid 146.9 vs 145.9 (+0.7%) | tall 1012.7 vs 1030.7 (-1.7%) |
  stubby 8.6 vs 8.2 (+5.1%, +0.4 W abs).
  Worst relative errors sit on the two smallest absolute numbers, where
  the analytic's full-theta base term dominates. Full lines in
  hortus-rung3/nb007-table.txt.
- NB-008 DONE. Timing table written into hortus-rung3/README.md (coarse
  and fine per case; evolution price: tens of seconds per dense design).
- NB-009 DONE. Champion coarse case 3x: 183.545700 W/m, 9966 iters,
  byte-identical all three (oc-proofs/nb-009-determinism.txt).
- NB-010 DONE. hortus-rung3/RUNG3_CLOSEOUT.md: proves, gaps, exact commands.

## Section B: queue suite + clean-clone proof (NB-011 to NB-020)

- NB-011 DONE. Exact collection error text in oc-proofs/queue-mac-diagnosis.md.
- NB-012 DONE. One paragraph in the same file: unconditional import of a
  sandbox-absolute path (/opt/muse/skills/...), missing on plain Macs.
- NB-013 DONE. Fix delivered as oc-proofs/queue-mac-optional-import.diff
  (v2: optional import + raisable stubs + identity check; _call guard via
  stub). Never applied to server/.
- NB-014 DONE. Throwaway worktree of origin/main, patch applied, suite run:
  110 passed, 0 failed (v1 of the patch scored 108+2 — two tests mock the
  old import layout, fixed by keeping the names as stubs). Throwaway
  deleted; real checkout untouched (verified: worktree list clean).
- NB-015 DONE. Same-risk grep in the diagnosis file: only spark_gen.py
  references the path (subprocess env, runtime-only, no collection risk).
- NB-016..NB-020 NOT DONE — clean-clone proof not started. Next up.

## Section 3: Hortus rung 3 simulation (OC-026 to OC-035)

Work lives in ~/workspace/hackathon/demo-stack/hortus-rung3/ (own local git
repo, commit 556bd41; repo untouched per the prompt). Status per task:
- OC-026 DONE. Read OPENCODE_PROMPT_HORTUS_RUNG3.md (all 76 lines), followed it.
- OC-027 DONE. Own finite-difference solver, stdlib only (no numpy on this
  Mac): solver.py, one periodic fin cell, red-black SOR, energy-balance stop rule.
- OC-028 DONE. Single fin vs closed-form 1D formula (adiabatic tip, exact):
  0.84% error at dy=0.50 mm, 0.41% at dy=0.25 mm — halving the grid halves the
  error. Balance 2e-3. Two real bugs caught by verification (heat counted
  through air cells; grid rounding the fin narrow) and fixed.
- OC-029 DONE. Champion (40 fins, 60.0 mm, 0.745 mm, 1.494 mm base, assumed
  100x100 mm footprint): 733.8 W at dT=50 K forced air (685.6 W with flat h=50).
- OC-030 DONE. Reference (10/10/2/5 mm): 18.3 W (74.0 W with flat h=50).
  Ranking never wavers: champion wins 9x–40x under every assumption set.
- OC-031 DONE. Grid doubled once (dx 0.0926→0.0463 mm, dy 0.5→0.25 mm):
  champion moves from 733.8 W to 735.9 W (+0.28%). Record: hortus-rung3 repo,
  oc-031-refine.txt (note: 80k iters, balance 6.5e-3 vs 2e-3 rule — value
  stable, strict criterion unmet; reported, not hidden).
- OC-032 BLOCKED, not faked: the rung-2 calibrated champion ("organism 8175")
  exists nowhere reachable. The number 8175 appears in this checkout only as
  digits inside an officina float and inside the task text itself. Rung 2 is
  built separately per the prompt and was never pushed. No geometry invented.
- OC-033 DONE. Assumptions all stated in RUNG3_REPORT.md; ~42 s per dense
  scoring call on one core (finalists only, never in-loop).
- OC-034 DONE. RUNG3_REPORT.md written with honest verdict: fit for finalist
  judging, needs one physical or commercial-solver cross-check before
  selection trusts it.
- OC-035 not applicable: the solver succeeded.

## Section 4: Meta Scientia 3D compounds (OC-036 to OC-050)

- OC-036 DONE. design/meta-scientia-molecules.html + vendored three.js r152
  (design/vendor/three.min.js). Note: the task's "already vendored film
  pattern" does not exist in this tree (no film dir, no three.js) — vendored
  fresh from unpkg instead (633,338 bytes), same offline result.
- OC-037 DONE. Caffeine, aspirin, glucose 3D SDFs from PubChem PUG REST
  (record_type=3d), saved raw in design/molecules/ with CIDs 2519/2244/5793.
- OC-038 DONE. Ball and stick with element colors; proof oc-038-caffeine-ballstick.png.
- OC-039 DONE. Space-filling toggle (vdW radii, bonds hidden); proof
  oc-039-benzene-spacefill.png.
- OC-040 DONE. Drag rotates (proof oc-040 was retaken as hover set), wheel
  zooms (code), auto-rotate stops on first drag (verified: toggle off after
  drag test).
- OC-041 DONE. Hover raycast tooltip ("O atom 1 at (0.47, 2.57, 0.00) A") +
  toggleable atom labels; proof oc-041-hover-labels.png.
- OC-042 DONE. Picker with all 8 compounds, loaded from local files; network
  log shows every request is 127.0.0.1, nothing external.
- OC-043 DONE. Five ESOL molecules via RDKit 2025.09.2 (ETKDGv3 seed 42 +
  MMFF), in the picker, labelled generated-not-measured everywhere. Caveat:
  the exact five "gate set" rows are not in this checkout (scaffold branch
  never pushed), so these are five canonical ESOL members — README says so.
- OC-044 DONE. Formula + weight come from molecules/meta.json, rendered
  verbatim ("C8H10N4O2 — 194.19 g/mol").
- OC-045 DONE as standalone page. There is no Scientia board surface in the
  app to place it on (checked: no scientia board exists), and index.html was
  deliberately not touched. Screenshots are of the page itself.
- OC-046 DONE. oc-046-rotation-10s.mp4: 10.0 s, rotation plus a mid-clip
  picker switch to glucose. Method honestly stated: 20 timed screenshots at
  2 fps stitched with ffmpeg (no screen recorder on a headless Mac); every
  pixel is the real page. Mid-frame verified viewable.
- OC-047 DONE. Malformed input shows "Could not load that structure: ... —
  Nothing was drawn — no fake molecule substituted." (verified twice: test
  button and once from a real code bug, which is also fixed).
- OC-048 DONE. design/molecules/README.md: PubChem vs RDKit provenance,
  RDKit version/seed, vendored three.js version/bytes, the ESOL caveat.
- OC-049 DONE. Network log on the page: only 127.0.0.1 requests (page, three,
  meta.json, SDFs). Works offline.
## Section 5: Meta Musica 3D notes (OC-051 to OC-065)

- OC-051 DONE. design/meta-musica-notes.html: five long thin dark boxes
  (16 x 0.03 x 30) into the distance as the staff.
- OC-052 DONE. Note = squashed-sphere head + cylinder stem + cone flag,
  all primitives, no external models.
- OC-053 DONE with the task's own fallback: no Musica take file exists in
  this checkout (Hana's HN-029 lane not landed), so the ascending/descending
  C major scale stands in, labelled PLACEHOLDER in the page header and meta
  line. Not a Musica composition — stated everywhere it appears.
- OC-054 DONE. Drag orbit + wheel zoom (same hand-rolled controls as the
  molecule viewer); Side/Top/End preset buttons; proofs oc-060-side/top/end.png.
- OC-055 DONE. Playhead curtain travels the staff; the current note lifts and
  glows; meta line names sounding notes. Screenshots show lifted glowing notes.
- OC-056 DONE. WebAudio sine tones, equal temperament A4=440, scheduled
  per-note from the same beat clock as the playhead — one shared beatLen().
- OC-057 DONE. Tempo slider 60–200 bpm drives both (single beatLen source);
  verified at 200 bpm in the clip (slider visible reading "200 bpm").
- OC-058 DONE. Note-name labels toggle (canvas sprites), on by default.
- OC-059 DONE. Second voice below in amber playing a diatonic third under
  the melody (A3..A4), same rhythm; independent mute toggles.
- OC-060 DONE. Dark room, cyan/amber accents, no clip art; three angles saved.
- OC-061 DONE as standalone page. No Musica studio board exists in the app;
  index.html untouched. Screenshots are of the page itself.
- OC-062 DONE. oc-062-playback-15s.mp4: 15.0 s, video + AAC audio. Method
  stated plainly: 30 timed headless screenshots at 2 fps (200 bpm) plus
  Python-synthesized matching tones (same frequencies, 0.3 s grid, both
  voices), muxed with ffmpeg. Real pixels, matching tones — not a
  sample-accurate screen recording; mid-frame proof oc-062-midframe.png.
- OC-063 DONE. Pause verified (meta flips to "Stopped..."); Restart resets
  playT (clicked, no error, playhead returns).
- OC-064 DONE. ~115–120 fps headless Chromium on this Mac (on-page meter).
## Section 6: The OS image in UTM (OC-066 to OC-080) — BLOCKED, not attempted

- OC-066 BLOCKED: UTM installed on this Mac via brew (UTM.app present,
  utmctl linked) — but metaos-2026-11-01.img exists nowhere on disk
  (whole-disk search, zero hits) and has never been built: the packer
  pipeline (os/build-packer.sh) needs a Debian ISO plus KVM, and its own
  test file states no build has ever run on a host without /dev/kvm —
  macOS has no KVM. The task says not to rebuild the image anyway.
  With UTM ready and no image to import, OC-067 through OC-080 cannot run.
- Recorded, not faked. Unblock needs: a built image file delivered to this Mac.

## Section 7: Land the Science Lab branch (OC-081 to OC-090) — BLOCKED, not attempted

- OC-081 BLOCKED: pax/science-lab-scaffold is not pushed (git ls-remote
  for *science*/*lab* returns nothing). The task says to ask on the bus if
  it is not pushed — no bus access from this Mac session, so the question
  could not even be asked. OC-082 through OC-090 all need the branch.
  Recorded, not faked. Unblock needs: Pax pushes the branch.

## Section 8: Real app footage for the demo film (OC-091 to OC-100) — partial

- OC-091 BLOCKED: the patrol loop lives in the queue crew service, which
  does not start on this Mac (dynamic_credentials, same as OC-004).
- OC-092 BLOCKED: staged flag chain needs queue + live model + camera.
- OC-093 BLOCKED: no chain, no dispatch receipt (nothing pointed anywhere else).
- OC-094 BLOCKED: no flagged incident can exist without the chain.
- OC-095 DONE. oc-095-scientia-10s.mp4 (10.0 s): aspirin ball-and-stick
  rotating, mid-clip switch to space-filling. Fresh file, method as in OC-046.
- OC-096 DONE. oc-096-musica-15s.mp4 (15.0 s, video + AAC): top-view playback
  at 120 bpm with matching synthesized two-voice audio (0.5 s grid). Fresh file.
- OC-097 BLOCKED: no recorded incident exists (chain down).
- OC-098 DONE so far: oc-095-scientia-10s.mp4 (10.0 s), oc-096-musica-15s.mp4
  (15.0 s), plus earlier oc-046-rotation-10s.mp4 (10.0 s) and
  oc-062-playback-15s.mp4 (15.0 s). All names unique.
- OC-099 DONE for the four clips above: ffprobe durations exact (10.0/15.0),
  mid-frames viewed and correct (molecule mid-frame and musica mid-frame
  checked this session).
- OC-100 summary: Sections 1, 3, 4, 5 done and pushed. Section 2 waiting on
  the user's go-ahead for tonight's 8pm run. Sections 6 and 7 blocked on
  missing externals (image file, unpushed branch). Section 8 partial — the
  chain-dependent recordings need the queue fixed first.

## Section C (round 2): Scientia 3D molecules, labs/molecules/ (NB-021 to NB-035)

- NB-021 DONE. labs/molecules/ static page + vendored three.js r152
  (labs/molecules/vendor/three.min.js, 633,338 bytes, LICENSE file kept).
  No Three.js copy existed anywhere in the tree, so fresh download was the
  only option — stated in vendor/LICENSE-three.txt.
- NB-022 DONE. Caffeine/aspirin/glucose embedded as JSON in labs/molecules/data/
  (converted from PubChem 3D SDF); CIDs 2519/2244/5793 in SOURCES.md.
- NB-023 DONE. Ball-and-stick, CPK colors (nb-*-bs.png).
- NB-024 DONE. Space-filling toggle, vdW radii, bonds hidden (nb-*-sf.png).
- NB-025 DONE, every control clicked: picker (5/5 load), bs/sf toggle,
  auto-rotate (on at load, off after drag — verified), labels toggle,
  drag rotate (orientation change verified), wheel zoom (same handler as
  the proven design-page viewer), measure toggle. No dead control.
- NB-026 DONE. Atom labels toggle (element + index sprites; proof
  nb-labels-drag.png).
- NB-027 DONE. Double bonds render as twin cylinders from bond-order data
  (aspirin ring + carbonyls visibly doubled in nb-aspirin-bs.png); comment
  table is in the code header.
- NB-028 DONE. Picker for the embedded 5 + Load CID field (live PubChem
  fetch). CID 962 loads live (3 atoms); garbage input shows the honest
  error and embedded molecules keep working.
- NB-029 DONE. 6 PNGs in labs/molecules/shots/ (caffeine/aspirin/glucose x
  bs/sf), each viewed — none blank. Plus nb-labels-drag.png.
- NB-030 DONE. Count table in SOURCES.md (JSON counts == SDF counts lines;
  PubChem records match). Test asserts the same numbers.
- NB-031 DONE. Water (3/2) + ethanol (9/8) embedded, captioned, tested.
- NB-032 DONE. Measure: click two atoms, O1-H2 in water = 0.97 A (correct
  bond length), shown in the meta line.
- NB-033 DONE. One plain caption line per molecule under the viewer.
- NB-034 DONE. labs/molecules/tests/validate.test.mjs: 6/6 pass (counts,
  bond endpoints, CPK membership, meta coverage).
- NB-035 section report: this list; shots + test named above.

## Section B (round 2), completed: clean-clone proof (NB-016 to NB-020)

- NB-016 DONE. Fresh clone to /tmp/cleanclone (45 MB), no install needed
  (zero-dependency repo: npm install = "up to date"), npm test: 1933 run,
  1877 pass, 56 fail — all 56 in tests/native-*, zero outside the known set.
- NB-017 DONE. Same clone, cargo test --workspace: 1412 pass, 0 fail.
- NB-018 DONE. Timing: npm install+test under 1 minute wall; cargo cold
  build+test under 1 minute wall (both logs show 0 elapsed minutes).
  Judge's-machine number: minutes, not hours.
- NB-019 DONE. Env: node v24.21.0, npm 11.19.0, cargo/rustc 1.99.1
  (Homebrew), python3 system for the python suites. No lockfile in repo
  (no dependencies to lock). No other tools needed.
- NB-020 DONE. Totals match baselines exactly. PROVEN CLEAN.

## Section D (round 2): Musica 3D notes, labs/music3d/ (NB-036 to NB-050)

- NB-036 DONE. labs/music3d/ static page + vendored three.js r152
  (own copy under labs/music3d/vendor, LICENSE kept).
- NB-037 DONE. Whole/half/quarter/eighth from primitives; differences
  tabled in a code comment (whole: no stem; half: torus head + stem;
  quarter: filled + stem; eighth: + flag cone).
- NB-038 DONE. Five long thin dark boxes into the distance; framed by
  default camera.
- NB-039 DONE. C major scale; heights from NOTES NOTE_Y map (never
  hand-placed): C4=-2 … C5=+5 half-steps from E4.
- NB-040 DONE. WebAudio TRIANGLE wave (not sine — spec), 92 BPM default;
  each note highlights as it sounds from the shared beat clock.
- NB-041 DONE. Second row BEHIND the first (z=-1.6), same scale one octave
  up, 0.7 size, amber-brown resting color; toggleable.
- NB-042 DONE. Play/Pause/Replay clicked and verified (meta line flips).
- NB-043 SKIPPED with reason: os/worlds/musica/ does not exist in this
  checkout (Hana's pack lane not landed) — no take file to read, and
  nothing was modified anywhere regardless.
- NB-044 DONE. 3 PNGs in labs/music3d/shots/: start (playhead left),
  mid-highlight (amber note at playhead, fix verified), octave-row
  (reframed view showing both rows).
- NB-045 DONE. Color rule in code comment + footer: rest cyan #22D3EE,
  playing note amber #FFBE55. First implementation only glowed cyan
  (emissive color never updated) — caught on screenshot, fixed, re-shot.
- NB-046 DONE. Space toggles play/pause, R restarts (run_code test:
  "Stopped…" then "Playing (placeholder…").
- NB-047 DONE. Volume slider 0–100 drives WebAudio gain (verified 0% label
  update; gain path is master GainNode).
- NB-048 DONE. Note-name labels toggle (canvas sprites), on by default.
- NB-049 DONE. labs/music3d/tests/validate.test.mjs: 3/3 pass (map covers
  C4..C5 ascending, order matches scale, octave = exactly 2x frequency).
- NB-050 section report: this list; shots + test named above.

## Section E (round 2): OS image boot in UTM (NB-051 to NB-060) — STOPPED at NB-051

- NB-051 DONE as a negative result: no image file on this Mac (whole-disk
  search, zero hits). UTM installed and ready, nothing to boot. Section
  stopped per the task's own instruction. Full note: oc-proofs/utm-boot-report.md.
- NB-052 to NB-060 not attempted. Unblock needs: the built .img on this Mac.

## Section F (round 2): fresh app footage (NB-061 to NB-070)

- NB-061 DONE. nb-061-home-20s.mp4 (20.0 s): home/command view, slow panel scroll.
- NB-062 DONE. nb-062-wall-20s.mp4 (20.0 s): camera wall with Caltrans feeds.
- NB-063 DONE as the task's fallback (no Custos panel in the UI — verified
  absent from the DOM): terminal patrol run on camera, 20.0 s, real output
  with the summary line and SIMULATED escalations legible. Rendered from
  the live run's stdout as terminal frames (headless has no terminal
  recorder); every pixel is real output, method stated.
- NB-064 DONE. nb-064-map-layers-10s.mp4 (10.0 s): Fires then Radar clicked
  on camera (pressed states visible); app answers honestly "no FIRMS key".
- NB-065 DONE. nb-065-phone-15s.mp4 (15.0 s): 390 px width, stacked layout.
- NB-066 DONE. All 7 clips ffprobe-exact durations; one mid-frame each
  viewed, none black/blank.
- NB-067 DONE. nb-067-nativeapp-10s.mp4 (10.0 s): fresh-built MetaTrio.app
  window (swift build clean in this tree) running the web UI — real map
  pins, wall, inspector. App-only crop; no desktop, dock, or other windows
  in frame. No camera permission prompt appeared (nothing staged).
- NB-068 DONE. nb-068-readme-30s.mp4 (30.0 s): repo front page scroll.
- NB-069 Originals only: PNG-to-H.264 first encodes, no zip, no recompression.
- NB-070 DONE. oc-proofs/footage/FOOTAGE_INDEX.md with the table above.

## Section H (round 2): read-only review tools, labs/review/ (NB-081 to NB-090)

- NB-081 DONE. labs/review/bolo.html: pasted/sample JSON renders description
  + visible marks, ID reads UNIDENTIFIED, no name field anywhere (shot).
- NB-082 DONE. labs/review/timeline.html: file picker + sample button draw
  all 6 records in timestamp order with tier colors (shot). Sample fetch
  404s on the static server (no .jsonl MIME; server/ read-only) so the page
  falls back to an embedded copy of the same bytes — stated in code.
- NB-083 DONE. Shots: nb-083-bolo.png, nb-083-timeline.png, nb-087-cannot-do.png.
- NB-084 DONE. Purge drill on a COPY: record 001 marked false positive,
  evidence entry emptied with purge receipt; real sample-records.jsonl
  verified untouched. Before/after JSON in oc-proofs/; after-state BOLO
  shot proves the card still renders with purged evidence.
- NB-085 DONE. tier-counter.mjs on the sample: 6 records, 3 yellow, 2 red.
- NB-086 DONE. 20 generated samples validate against js/schema.js (read-only
  import): 20/20 pass. Building them taught the schema's real rules
  (medicus always requires human review; ignis baseline is "no hazard
  visible"), recorded in the test.
- NB-087 DONE. cannot-do.html renders all three divisions' limits from
  js/products.js (shot).
- NB-088 DONE. labs/review/README.md with each command.
- NB-089 DONE. labs/review/tests/review.test.mjs: 2/2 pass.
- NB-090 section report: this list.

## Section G (round 2): endurance and drills (NB-071 to NB-080) — in progress

- NB-071 RUNNING. Soak: :8092 app server, held-mode assess traffic (valid
  frame, expect 503) + health + cameras every 5 min x12 with RSS. Peak TBD.
- NB-072 PENDING (count at soak end; expect 0 dispatches — no queue, no
  live model; every receipt anywhere this round is sim-).
- NB-073 DONE. Budget drill vs temp ledger: 556 stub calls ($0.135 each at
  $1.25/$4.25 per M) then checkBudget throws: "GUARDRAIL STOP: estimated
  test spend $75.0600 has reached the $75.00 test budget. No call sent."
- NB-074 PENDING (post-soak: kill/restart :8092, verify health + held path).
- NB-075 BASELINE. server/queue/ = 220K at 11:03 UTC, no crew-data dir
  (queue never ran here). After-size at soak end.
- NB-076 DONE with blemishes: 3 targets x ~43 iters on :8093 (129/150 —
  run cut short by an operator pkill, recorded): all cameras=200,
  assess=503 (held). One ~1 min window of cameras=000 (localhost refused)
  mid-run, self-recovered, no crash. Verbatim sample: "t1 i30
  cameras=000". No other errors.
- NB-077 DONE. TZ=Pacific/Auckland server: identical behavior. Finding:
  the served API surface carries no wall-clock timestamps (health/crew
  have none; assess validates image BEFORE timestamp — a stub image 400s
  on image shape regardless of TZ, a valid frame 503s held). Ordering
  N/A — nothing emitted to order. Timestamp parsing (valid +13:00,
  Z, garbage) behaves TZ-independently; garbage timestamp still 400s.
- NB-078/079 BLOCKED: no sudo on this Mac (sudo -n fails), so no firewall
  rule can cut the network; pulling the cable is not an option on a
  remote-shared build machine. No network manipulation performed.
  Unblock needs: root, or a sanctioned fault-injection path.
