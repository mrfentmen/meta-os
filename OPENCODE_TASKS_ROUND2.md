# OpenCode tasks round 2: 100 new tasks (NB-001 to NB-100)

Boss order 2026-11-01: OpenCode finished the last job in minutes, so here
is a full round of 100. New features and tests only. The crew (Rowan,
Hana, Milo) has its own lanes in TASKS_V3.md. This round must not cross
their paths: do not redo their work and do not write over their files.

The 8 PM end to end test is still skipped. It runs later tonight on the
boss's word only. Nothing in this round stages an incident or runs the
click sweep.

## Protected paths: never modify these

- os/worlds/custos/ (Rowan)
- os/worlds/officina/ (Milo)
- os/worlds/musica/ (Hana)
- os/worlds/science-lab/ (Pax, held)
- eval/ (Milo)
- index.html, js/, server/, crates/, package.json (platform and UI crew)
- Native Swift sources (native test call is still open)
- tests/ existing files, docs/, README.md, TASKS_V3.md,
  OPENCODE_TASKS_100.md, OPENCODE_NEXT_TASK.md, bus-tools/
- The 4 excluded bus files, as always: bus-tools/bus-poll,
  bus-tools/bus-rooms, bus-tools/bus-send, tests/test_bus_admin_e2e.py

## Allowed paths

All new code lives in new folders only: labs/, hortus-rung3/,
oc-proofs/. Reports go in oc-proofs/. Branch: opencode/mac-tasks.
One section report per section, named in each section. Update
oc-proofs/ROUND2_REPORT.md as you finish each section: one line per
section, done or not done, with the proof file names.

## Standing rules

- Proof or it did not happen: every claim carries the command and its
  real output, or a screenshot that was actually viewed.
- On the first red result in a section, finish that section's report
  with the exact error text and move to the next section. Do not patch
  around crew code, ever. A fix inside your own labs/ or hortus-rung3/
  code is fine and gets logged.
- Dispatch, if anything triggers it, goes to the SIMULATED endpoint
  only. No real Spark API calls in this round: expected live spend is 0.
- Fresh unique file names for every capture. The boss's app caches by
  name, so a reused name shows him the old file.

## Section A: close the rung-3 gaps (NB-001 to NB-010)

- NB-001 Push the rung-3 solver code (run.py, solver.py, whatever it
  needs) into hortus-rung3/ on opencode/mac-tasks, with a README that
  gives the exact run commands.
- NB-002 Re-run the verification case from the pushed code. Record
  simulation vs analytic and the error. This time state the h value
  used, in the report (it was missing last time).
- NB-003 Fix the runtime mismatch from the last report (report said
  about 8 seconds, the log said 1.0). Time both runs properly and
  explain the difference in one paragraph.
- NB-004 Score the rung-2 champion, organism 8175: 40 fins, 60.0 mm
  height, 0.745 mm fin thickness, 1.400 mm base, assumed footprint
  100 by 100 mm (state the assumption). Report its simulated watts
  next to the rung-1 champion's 733.8 W and the reference's 18.3 W.
- NB-005 Score the wide-genome champion, organism 78901: 48 fins,
  100.0 mm height, 0.405 mm thickness, 1.000 mm base, same assumed
  footprint. Its height is outside the calibrated geometry range; say
  so in the output, do not hide it.
- NB-006 Re-run the rung-1 champion on the fine grid with the balance
  rule tightened until the 2e-3 rule passes, or report exactly why it
  cannot pass. Last time it landed at 6.5e-3.
- NB-007 Solver vs closed-form check on 5 geometries, one table:
  (a) 10 fins, 10 mm, 2.0 mm, 5.0 mm base (the reference);
  (b) 40, 60, 0.745, 1.494 (rung-1 champion);
  (c) 20, 30, 1.0, 2.0; (d) 60, 100, 0.4, 1.0; (e) 5, 20, 3.0, 8.0.
  Same footprint assumption throughout, stated once.
- NB-008 Measure solver seconds per call at coarse and fine grid.
  Write both numbers into hortus-rung3/README.md. (Any future
  evolution run needs this price before it starts.)
- NB-009 Determinism check: run the champion case 3 times and byte
  compare the outputs. Report identical or not.
- NB-010 Write hortus-rung3/RUNG3_CLOSEOUT.md: what rung 3 now proves,
  what it still does not (no real heatsink has been measured; that is
  rung 4 and a boss decision), and the exact commands to reproduce
  everything in this section.

## Section B: the queue suite on the Mac, and a clean-clone proof (NB-011 to NB-020)

Context: on the Mac the queue python suite does not even collect
(dynamic_credentials import failure, 4 collection errors, 0 run). The
sandbox runs it green at 110. Diagnose only: server/ is protected, so
the fix is delivered as a patch file, never applied by you.

- NB-011 Reproduce the collection failure and put the exact error text
  in oc-proofs/queue-mac-diagnosis.md.
- NB-012 Find the root cause in one paragraph: where that module lives
  in the sandbox layout vs a plain Mac checkout, and why the import
  breaks. Name the exact file and line that imports it.
- NB-013 Write the proposed fix as a .diff file in oc-proofs/. Do not
  apply it to server/.
- NB-014 Prove the patch on a throwaway copy of the repo in /tmp:
  apply it there, run the queue suite, report the count (expected
  110 OK). The throwaway copy is deleted after; the real checkout is
  untouched.
- NB-015 Grep the whole repo for the same import pattern. List every
  other suite at the same risk, or state there are none.
- NB-016 Clean-clone proof, node: fresh clone in a new folder, install
  from the lockfile, run npm test. Report totals (expected 1933 run,
  1877 pass, 56 fail, all 56 the known native set).
- NB-017 Clean-clone proof, cargo: same clone, cargo test
  --workspace. Report totals (expected 1412 pass, 0 fail).
- NB-018 Time the whole clean-clone proof end to end, minutes per
  suite, in oc-proofs/clean-clone-proof.md. This is the number a
  judge's machine would need.
- NB-019 List every environment assumption the clean clone needed
  (tools and versions) in the same file.
- NB-020 If any clean-clone total differs, the difference is the
  headline of the section report, with exact counts. If all match,
  close the section with the words PROVEN CLEAN.

## Section C: Scientia 3D chemical compounds, labs/molecules/ (NB-021 to NB-035)

New feature, boss's 3D direction: a molecule viewer that runs as a
static page, real structures, real data. All files stay in
labs/molecules/. Nothing here touches Hana's or Milo's Scientia work:
this is a viewer prototype, not the lab pack and not the Delaney gate.

- NB-021 Scaffold labs/molecules/ as a static page with no build step.
  Use a vendored Three.js: if the repo already carries a copy, use it
  and say where; if you download one, record the version and keep its
  license file next to it.
- NB-022 Embed real structures for caffeine, aspirin, and glucose as
  JSON in labs/molecules/data/. Source: PubChem. Record each CID in
  labs/molecules/SOURCES.md.
- NB-023 Ball-and-stick renderer, CPK element colors.
- NB-024 Space-filling mode (van der Waals radii) as a toggle next to
  ball-and-stick.
- NB-025 Controls: drag rotate, scroll zoom, auto-rotate toggle. Click
  test every control and record the result.
- NB-026 Atom labels toggle (element symbols).
- NB-027 Double bonds drawn as two cylinders, from the bond data, not
  faked.
- NB-028 Molecule picker for the embedded set, plus a load-by-CID
  field that fetches from PubChem at runtime. Online only: a failed
  fetch shows a plain error and the embedded molecules keep working
  offline.
- NB-029 Screenshot proof: one PNG per molecule per mode, 6 PNGs,
  into labs/molecules/shots/. View each one; a black or blank frame
  fails the task.
- NB-030 Print each molecule's atom and bond counts from your JSON
  and check them against PubChem's stated counts. Table in
  SOURCES.md.
- NB-031 Add water and ethanol the same way (PubChem, recorded). The
  smallest useful teaching pair.
- NB-032 Measure tool: click any two atoms, show the distance in
  angstroms.
- NB-033 One plain caption line per molecule under the viewer: what it
  is, in plain words, no hype.
- NB-034 Tests in labs/molecules/tests/: a node test that validates
  the embedded JSON (atom counts, every bond points at real atoms,
  every element is in the CPK table). Run it, report the result.
- NB-035 Section report in oc-proofs/: the 6 screenshot names, the
  count-check table result, the test result.

## Section D: Musica 3D music notes, labs/music3d/ (NB-036 to NB-050)

New feature, boss's 3D direction: notes you can see in 3D and hear.
All files stay in labs/music3d/. Hana owns the Musica pack and the
composition loop in os/worlds/musica/; this is a viewer and player
prototype and never writes there (one read-only task, NB-043, and it
is optional by design).

- NB-036 Scaffold labs/music3d/ as a static page. Same Three.js
  approach as Section C.
- NB-037 Note models from primitives: whole, half, quarter, eighth.
  Write the differences (head fill, stem, flag) as a comment table in
  the code.
- NB-038 A 3D staff: five long thin lines, camera framed on it.
- NB-039 Place a C major scale on the staff. Note height comes from a
  note-to-height data map, never from hand-placed magic numbers.
- NB-040 Playback: WebAudio, triangle wave. Each note sounds as it
  highlights in 3D. Tempo 92 BPM.
- NB-041 A second row behind the first: the same scale one octave up,
  smaller. This is the depth shot; screenshot it in NB-044.
- NB-042 Play, pause, and replay buttons. Click test each one and
  record the result.
- NB-043 Optional and read-only: if os/worlds/musica/ holds a take
  file whose format is obvious, place its notes too. If the format is
  not obvious, skip and write exactly why in the report. Modify
  nothing in that folder either way.
- NB-044 Screenshot proof: 3 PNGs (start, mid-playback highlight,
  octave row) into labs/music3d/shots/. View each one.
- NB-045 Color rule: notes in one accent color; the playing note
  turns amber #FFBE55 (the film accent). State the rule in a comment.
- NB-046 Keyboard: space toggles play, R restarts. Test both keys and
  record.
- NB-047 Volume slider that really changes gain. Test at zero, half,
  and full; record.
- NB-048 Note-name labels under each note, toggleable.
- NB-049 Tests in labs/music3d/tests/: validate the note-to-height
  map covers C4 to C5 and the playback order matches the scale data.
  Run, report.
- NB-050 Section report in oc-proofs/: screenshot names, control and
  key test results, the NB-043 outcome (done or skipped, and why).

## Section E: OS image boot check in UTM, report only (NB-051 to NB-060)

Rowan owns building the image. This section only boots the existing
image on the boss's Mac and reports what is true. Never rebuild it,
never modify it. The image file is metaos-2026-11-01.img (about
6.0 GiB, built 2026-11-01 02:19 EST in the sandbox).

- NB-051 If you do not have the image file, say that first in the
  section report and stop the section. If you have it: import it into
  UTM as an x86_64 machine, 4 GB RAM, CPU model set to a modern one,
  not qemu64 (a crew program crashes on qemu64).
- NB-052 Boot it. Record the time from start to the login prompt.
  Screenshot the console.
- NB-053 The open question (Rowan's RW-016): does a working shell
  open on the serial console, ttyS0? Report exactly what happens,
  keystroke by keystroke if it fails.
- NB-054 Does the guest get an IP address (DHCP)? Print it, or print
  the failure.
- NB-055 If it has an IP: open the dashboard over HTTP from the host
  browser. Screenshot it, or record the exact failure.
- NB-056 If a shell is reachable: read the passive updater's log and
  report its last run result. No shell means that is the blocker;
  write it and stop this thread of the section.
- NB-057 In-guest versions, if reachable: node, opencode, freebuff.
  Report each, or why not reachable.
- NB-058 Count failed systemd units in the guest, if reachable. The
  sandbox QEMU check saw 0; say whether the Mac agrees.
- NB-059 Shut the VM down cleanly. Record the section's total wall
  time.
- NB-060 Write oc-proofs/utm-boot-report.md with every result and
  screenshot names. Anything unproven is written as unproven.

## Section F: fresh app footage for the film (NB-061 to NB-070)

No code changes in this section. The film needs real footage of the
current build. Fresh unique file names on every clip: the boss's app
caches by name, so a reused name shows him the old clip. Clips go in
oc-proofs/footage/.

- NB-061 The merged app home screen, 20 seconds, slow move across the
  panels.
- NB-062 The camera wall view, 20 seconds, cameras visible.
- NB-063 Custos: if the UI shows a Custos panel, record it for 20
  seconds. If not, record a Custos patrol run in the terminal
  instead, 20 seconds, summary line visible at the end.
- NB-064 The map view: click the Fires layer button and the Radar
  layer button once each, on camera.
- NB-065 The app at phone width (390 px in the browser), 15 seconds.
- NB-066 For every clip so far: ffprobe the duration and pull one
  frame as a PNG. View the frame. A black or blank frame fails that
  clip; re-record it once, and if it fails again, report it.
- NB-067 The native app window opening to the web UI. Launch is
  allowed for footage only. No staged incident. If the camera
  permission prompt appears, stop the clip there and note it.
- NB-068 The GitHub repo front page (the README), 30 seconds,
  scrolling slowly. This is the film's repo shot.
- NB-069 Deliver originals: no zip, no recompression.
- NB-070 Write oc-proofs/footage/FOOTAGE_INDEX.md: file name,
  duration, what it shows, frame-check result, for every clip.

## Section G: endurance and budget drills (NB-071 to NB-080)

The local server only, dispatch pointed at the SIMULATED endpoint,
no real API key use. These drills test the running system, they do
not change it: any change you think it needs goes in the report as a
proposal, never as an edit.

- NB-071 Soak: run the server 60 minutes, patrol on its normal
  cadence, SIMULATED dispatch only. Log memory every 5 minutes.
  Report the peak.
- NB-072 During the soak, count dispatches. Every one must carry a
  sim- receipt. Print the count and one sample receipt id.
- NB-073 Budget drill: point the transport at a local stub (never
  the real API) and feed responses until the budget cap logic trips.
  Record the exact trip message and the dollar figure it names.
- NB-074 Restart drill: kill and restart the server mid-patrol. The
  records must come back clean: run the records check the codebase
  offers (reconstruct or its equivalent) and report the result.
- NB-075 Disk growth: records folder size before and after the soak.
  Project the per-day growth at that cadence. Show the math.
- NB-076 Concurrency: 3 patrol targets at once for 10 minutes.
  Report any error verbatim.
- NB-077 Clock check: start the server with a different TZ value and
  confirm its timestamps still parse and order correctly. Report.
- NB-078 Offline drill: cut the server's network for 5 minutes
  mid-patrol (firewall rule or cable, your call). It must fail safe:
  no crash loop, errors logged. Quote the log lines.
- NB-079 Recovery: restore the network. Patrol must resume without a
  server restart. Report the time to resume.
- NB-080 Write oc-proofs/endurance-report.md with every number. A
  crash, a corrupt record, or a non-simulated dispatch is the
  headline of the report, never buried.

## Section H: read-only review tools, labs/review/ (NB-081 to NB-090)

Small tools that read the product's own outputs and draw them.
Read-only against the repo: js/schema.js and js/products.js may be
imported or read, never edited. Sample data is your own, and every
sample is labeled SIMULATED.

- NB-081 BOLO card renderer: a static page in labs/review/ that takes
  a pasted incident JSON and renders the BOLO card by the product
  rules: description and visible marks only, and the ID line reads
  UNIDENTIFIED. There is no name field, anywhere. Ship a sample
  SIMULATED incident JSON with it.
- NB-082 Records timeline: a page that loads a records JSONL file
  (file picker) and draws the steps in order (patrol, review,
  investigate, record, dispatch) with timestamps.
- NB-083 Test both pages on the sample data. One screenshot each
  into labs/review/shots/. View them.
- NB-084 Purge drill, on a copy of the sample data only: mark the
  sample incident a false positive and show its evidence entry gone
  from the copy. Screenshot before and after. Real records are never
  touched; this section has no real records.
- NB-085 Tier counter: a small script that reads a records JSONL and
  prints counts by tier (yellow, red) and division. Test it on
  sample data you build with exactly 3 yellow and 2 red, and say so
  in the test.
- NB-086 Contract spot-check: validate 20 sample assessments (your
  own generated samples, labeled) against the repo's js/schema.js,
  read-only. Report the pass count.
- NB-087 A "what this system cannot do" page: a static page listing,
  in plain words, the limits from the product data (no face naming,
  dispatch is simulated only, Medicus reads scenes and never
  diagnoses, plus the rest the data states). Screenshot it.
- NB-088 Every labs/review/ tool runs by opening the page or with one
  node command. Write labs/review/README.md with each command.
- NB-089 Tests for the tier counter (NB-085) in labs/review/tests/,
  using the known-count sample. Run, report.
- NB-090 Section report in oc-proofs/: screenshot names, test
  results, the NB-086 pass count.

## Section I: final sweep and handover (NB-091 to NB-100)

- NB-091 Re-run every labs test from Sections C, D, and H in one
  pass. One results table.
- NB-092 Re-run the repo baselines on the Mac one last time: cargo
  and node. Totals must read 1412 pass 0 fail and 1933 run, 1877
  pass, 56 known fails, or the difference is the headline of the
  final report.
- NB-093 Prove the round stayed in its lanes: print the full list of
  files changed on opencode/mac-tasks vs main into the final report.
  Any protected path in that list is a failure: stop and say which
  file and why.
- NB-094 Confirm none of the 4 excluded bus files were committed.
  Show the check.
- NB-095 Confirm no real dispatch happened this round: every receipt
  in your own reports is a sim- receipt. State the count you found.
- NB-096 State the round's total live API spend. Expected: 0 calls,
  $0. If any happened, list each with its cost estimate.
- NB-097 Write the final oc-proofs/ROUND2_REPORT.md: per section,
  done or not done, one line each, proof files named.
- NB-098 Commit everything and push opencode/mac-tasks. The final
  report names the hash of the last code commit before the report
  commit itself.
- NB-099 Write oc-proofs/ROUND2_PLAIN.md: one page for a
  non-technical reader. What was added, what was proven, what is
  still not proven. Plain words.
- NB-100 Stop. Do not start the 8 PM end to end test. It runs later
  tonight, on the boss's word only.
