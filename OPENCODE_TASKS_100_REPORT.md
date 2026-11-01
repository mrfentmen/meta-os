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
- OC-010 this section of the report.

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
