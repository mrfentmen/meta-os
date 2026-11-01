# OpenCode task list: 100 tasks for the Mac side of Meta OS

Ordered by the boss 2026-11-01. These tasks are for OpenCode on the
boss's Mac. They cover only what the Mac can do: compile the Rust
code for real, run the native app, click the camera permission, boot
the OS image in UTM, and record real app footage. The crew lanes
(Rowan, Hana, Milo) live in TASKS_V3.md and are not repeated here.

## Standing rules

1. Work in order inside a section. Sections 1 and 2 come first:
   tonight's end to end test (20:00 ET, Nov 1) outranks everything.
2. No fake results. A task is done only when its proof exists: a
   test count, a screenshot, a report file, or a recording. If a
   task fails, write down what failed and move on. Never write that
   something works when it was not run.
3. Commit after each section to a branch named
   opencode/mac-tasks, with the task IDs in the commit message.
   Never force push. Never commit the bus credential files
   (bus-tools/bus-poll, bus-rooms, bus-send,
   tests/test_bus_admin_e2e.py).
4. Dispatch in any test goes only to the simulated endpoint and
   must carry the SIMULATED label. Nothing in this list touches a
   real emergency service.
5. Report at each section boundary: task IDs done, task IDs failed
   with the reason, and the exact test counts. Put the report in
   OPENCODE_TASKS_100_REPORT.md as you go.
6. Baselines from the sandbox build, for comparison: node 1933
   tests, 1877 pass, 56 fail (the known WKWebView set); cargo 1412
   pass, 0 fail; queue python 110 OK; officina 49 OK after the
   bounds widening; worlds packs 9 of 9 OK.

## Section 1: Pull main and prove it on the Mac (OC-001 to OC-010)

- OC-001 Fetch origin and check out the current main tip. Record
  the tip hash in the report.
- OC-002 Run cargo test on the whole workspace. Record pass and
  fail counts next to the 1412 and 0 baseline.
- OC-003 Run the node test suite (npm test). Record totals next to
  the 1933, 1877, 56 baseline. List any failing test that is not
  in the known WKWebView set.
- OC-004 Run the queue python tests. Record the count (110 OK
  expected).
- OC-005 Run the officina python tests. Record the count (49 OK
  expected after the bounds widening).
- OC-006 Run the worlds pack validator. Record the count (9 of 9
  OK expected).
- OC-007 Run the OS loop harness test script. Record the count
  (12 of 12 expected).
- OC-008 Start the web app locally and open it. Confirm the
  manifest and the touch icon load with no 404.
- OC-009 Click the AI Focus button in the running app (it was wired
  by the UI fix list). Confirm it does something visible and take a
  screenshot.
- OC-010 Write the section 1 results into the report, including any
  count that differs from baseline and why.

## Section 2: Native app and tonight's test (OC-011 to OC-025)

- OC-011 Rebuild the native WKWebView app from current main.
- OC-012 Launch the native app and screenshot the first screen.
- OC-013 Trigger the camera flow and click through the macOS
  camera permission prompt. Screenshot the prompt and the result.
- OC-014 Confirm the live camera view renders inside the app.
- OC-015 Run one live assessment on a real camera frame for each of
  Vigiles, Ignis, and Medicus. Save the three result cards.
- OC-016 Stage a flagged scene and run the full chain: patrol,
  review, investigation, record. Screenshot each step.
- OC-017 Confirm the staged flag reaches the simulated dispatch
  endpoint and returns a sim receipt. Screenshot the receipt.
- OC-018 Confirm the record landed in the append only records and
  shows in the records viewer.
- OC-019 Open the map view. Screenshot it with camera markers
  visible.
- OC-020 Open the crew view and the incident view. Confirm the
  evidence, BOLO, and visible marks sections render (crew UI
  evidence merge).
- OC-021 Confirm the yellow and red tiers show the right colors on
  a yellow case and a red case.
- OC-022 Run the click sweep from
  OPENCODE_MAC_PROMPT_3_ADDENDUM.md on the merged code. Record
  every control that does nothing.
- OC-023 Confirm the four formerly dead controls from the UI audit
  now work or are gone: Brief me now, Post N jobs, Acknowledge,
  Resolve.
- OC-024 Restart the app and confirm it comes back clean with no
  lost records.
- OC-025 Write the section 2 results into the report with the
  screenshot file names.

## Section 3: Hortus rung 3 simulation (OC-026 to OC-035)

- OC-026 Read OPENCODE_PROMPT_HORTUS_RUNG3.md and follow it. This
  section is that prompt, tracked here.
- OC-027 Build the thermal simulation scorer (own finite difference
  solver preferred). Deliver the solver code.
- OC-028 Verify the solver on a known closed form case. Report sim
  against analytic, with the percent error.
- OC-029 Score the rung 1 champion geometry (40 fins, 60.0 mm,
  0.745 mm, 1.494 mm base) and state the assumed footprint.
- OC-030 Score the reference geometry (10 fins, 10 mm, 2 mm, 5 mm
  base) under the same assumptions.
- OC-031 Run a grid refinement pass (double the grid once) and
  report how much the champion number moves.
- OC-032 Score the rung 2 calibrated champion (organism 8175
  geometry) for comparison.
- OC-033 State every assumption and the runtime per scoring call.
- OC-034 Write RUNG3_REPORT.md with an honest verdict: rung earned
  or not, and what does not hold up.
- OC-035 If the solver failed, deliver the failed prototype plus an
  honest failure report instead. That counts as done.

## Section 4: Meta Scientia in 3D, chemical compounds (OC-036 to OC-050)

The boss ordered a 3D aspect for Meta Scientia on 2026-11-01: real
chemical compounds in 3D that a user can turn, zoom, and inspect.

- OC-036 Build a small Three.js molecule viewer page that loads a
  compound structure from a file and renders it in 3D. Reuse the
  vendored Three.js pattern already in this repo's film work.
- OC-037 Get real structure data for caffeine, aspirin, and
  glucose from PubChem (3D coordinates where PubChem offers them).
  Save the raw files and cite the source on the page.
- OC-038 Render each compound as ball and stick. Atoms colored by
  element with a legend.
- OC-039 Add a space filling view of the same compounds and a
  toggle between the two views.
- OC-040 Add rotate by drag, zoom by wheel, and a slow auto rotate
  that stops on interaction.
- OC-041 Add atom labels on hover: element name and position in
  the structure.
- OC-042 Add a compound picker with at least the three compounds
  above, loaded from files, no network needed at view time.
- OC-043 Generate 3D coordinates for five Delaney set molecules
  with RDKit (the gate set from the science lab work) and add them
  to the picker. Note on the page that these coordinates are RDKit
  generated, not PubChem records.
- OC-044 Show each compound's formula and molar mass next to the
  3D view, taken from the same data file, never typed by hand.
- OC-045 Place the viewer on the Scientia board surface in the app
  (or as a standalone page linked from it, if the board is not
  ready). Screenshot it inside the app frame.
- OC-046 Record a 10 second clip of a compound rotating with the
  picker being used. Real capture of the real page.
- OC-047 Test the viewer with one malformed structure file. It
  must show an honest error, not a blank page or a fake molecule.
- OC-048 Write the data provenance into a short README next to the
  viewer: which files came from PubChem, which from RDKit.
- OC-049 Confirm the viewer works with the network off (all assets
  local).
- OC-050 Write the section 4 results into the report with
  screenshot and clip file names.

## Section 5: Meta Musica in 3D, music notes (OC-051 to OC-065)

The boss ordered a 3D aspect for Meta Musica on 2026-11-01: music
notes as real 3D objects in a scene the user can move through.

- OC-051 Build a Three.js scene with a 3D staff: five lines as long
  thin boxes in space, extending into the distance.
- OC-052 Build one 3D note model (filled oval head, stem, flag)
  from primitives or an extruded shape. No external model files.
- OC-053 Place a short melody of notes on the staff at the right
  heights for their pitches. Use a real Musica take if one exists
  in the repo; if not, use the C major scale and label it as a
  placeholder melody, not a Musica composition.
- OC-054 Add orbit controls: drag to orbit, wheel to zoom, so the
  user can view the staff from the side, top, and end.
- OC-055 Animate playback: a playhead moves along the staff and
  each note lifts and glows as the playhead reaches it.
- OC-056 Play the matching tones with WebAudio as the playhead
  moves, in sync with the note animation.
- OC-057 Add a tempo control that changes both the audio and the
  playhead speed together.
- OC-058 Add note name labels that can be toggled on and off.
- OC-059 Add a second voice as a row of notes below the first,
  in a different color, playing at the same time.
- OC-060 Give the scene the Musica studio look: dark room, one
  accent color, no clip art feel. Screenshot from three angles.
- OC-061 Place the scene on the Musica studio board surface in the
  app (or as a standalone page linked from it). Screenshot it
  inside the app frame.
- OC-062 Record a 15 second clip of playback with audio. Real
  capture of the real scene.
- OC-063 Add a pause and restart control for the playback.
- OC-064 Confirm the scene runs at a steady frame rate on the Mac
  and note the measured frame rate in the report.
- OC-065 Write the section 5 results into the report, including
  whether a real Musica take was used or the labeled placeholder.

## Section 6: The OS image in UTM (OC-066 to OC-080)

- OC-066 Import metaos-2026-11-01.img into UTM with a modern x86
  CPU model (Freebuff crashes under the default qemu64 model).
  Record the UTM settings used.
- OC-067 Boot the image and screenshot the boot reaching the relay
  target.
- OC-068 List the systemd failed units in the guest. Target: zero.
- OC-069 Test the serial console: does a login shell appear on
  ttyS0? Record exactly what shows. This feeds Rowan's RW-016.
- OC-070 If no shell appears, try the getty drop in settings
  already in the image and record what changes. Do not rebuild the
  image; notes only.
- OC-071 Confirm the guest gets a DHCP address. Record the address
  and the command used.
- OC-072 Open the dashboard from the guest itself and from the Mac
  browser if networking allows. Screenshot both or record why not.
- OC-073 Run the passive updater by hand in the guest against a
  moved origin (a test commit on a scratch branch). Confirm it
  pulls and logs the old and new hashes.
- OC-074 Walk the firstboot prompts as a new user would: crew
  login, GitHub token prompt, git name and email. Record any step
  that confuses or fails.
- OC-075 Confirm node, opencode, and freebuff versions inside the
  guest and record them.
- OC-076 Start one crew agent session inside the guest and have it
  read TASKS_V3.md from the repo. Screenshot it working.
- OC-077 Pull the latest main inside the guest and confirm the
  merged systems are present (Officina, the loop service, the tier gate).
- OC-078 Measure boot time from UTM start to relay target. Record
  the number.
- OC-079 Note how the emulation feels: usable or slow, with one
  concrete example (how long a cargo build or a page load took).
- OC-080 Write the section 6 results into the report, including
  the ttyS0 finding in plain words.

## Section 7: Land the Science Lab branch (OC-081 to OC-090)

- OC-081 Check out the branch pax/science-lab-scaffold (local to
  Pax's VM; ask on the bus if it has not been pushed yet). Run its
  worlds tests and pack validation on the Mac.
- OC-082 Run the node suite on that branch and list the 9 known
  follow up failures by name.
- OC-083 For each follow up failure, write one line: test bug,
  code bug, or stale expectation. Do not fix yet.
- OC-084 Confirm the products picker shows the science lab entry
  and the app still works with four products.
- OC-085 Install RDKit in a venv on the Mac (the sandbox used
  RDKit 2026.09.1) and record the version.
- OC-086 Run the Delaney gate prep runner in selfcheck mode.
  Record the result.
- OC-087 Run the full Delaney prep (1128 rows) and record the
  paper equation numbers next to the sandbox prep numbers (paper
  equation R squared 0.725, RMSE 1.099, MAE 0.844).
- OC-088 Screenshot the science lab pack pages in the app if they
  render.
- OC-089 Write a merge readiness note: what must land before this
  branch can merge without raising the fail count.
- OC-090 Post the section 7 summary to the report and note what
  Milo needs for his blind verifier run (ML-081 to ML-083).

## Section 8: Real app footage for the demo film (OC-091 to OC-100)

- OC-091 Record the patrol loop running in the real app for 30
  seconds. Screen recording, no staging inside the code.
- OC-092 Record a staged flag going through review and
  investigation in the real app.
- OC-093 Record the simulated dispatch receipt arriving.
- OC-094 Record the map view with cameras and a flagged incident.
- OC-095 Record the Scientia 3D compound viewer in use (from
  section 4).
- OC-096 Record the Musica 3D notes playback with audio (from
  section 5).
- OC-097 Record the records viewer showing a real recorded
  incident from the staged run.
- OC-098 Name every clip with a fresh unique file name (never
  reuse a name) and list them in the report with durations.
- OC-099 Check each clip plays end to end (ffprobe plus a viewed
  frame from the middle of each).
- OC-100 Write the final report summary: sections done, sections
  failed and why, and the full list of proof files.
