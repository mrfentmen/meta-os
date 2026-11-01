# OPENCODE_TASKS_ROUND3.md — Mac-side work, round 3 (boss order 2026-11-01)

216 tasks, NC-001 to NC-216, 18 sections. Written by Pax from the boss's
order: more sections, work on everything, keep OpenCode busy while the
crew lanes run. Work on branch `opencode/mac-tasks`. Per-section proof
files go in `oc-proofs/`; keep a running report at
`oc-proofs/ROUND3_REPORT.md` and update it at every section boundary
(round 2 never wrote its report file — do not repeat that).

## State you are starting from (verified 2026-11-01 ~06:25 EST)

- Main tip: 25e6fca1. Custos on main now includes RW-001 (CT watcher),
  RW-002 (TLS grader), RW-003 (DNS drift), RW-004 (security headers) —
  nine patrol categories, the two newest both yellow.
- Test baselines on main: node 1999 tests / 1943 pass / 56 fail (the 56
  are exactly the known WKWebView set; anything else is new and must be
  reported as new). Custos python 48/48. Officina python 49/49.
- Round 2 landed A, B, C, D, F, H. Round 2 sections G (endurance) and
  I (final sweep) were never done — they are redone and expanded here
  as Sections K and Q.
- The queue-suite Mac failure is diagnosed and the fix is PROVEN:
  `oc-proofs/queue-mac-optional-import.diff` v2 gives 110 passed /
  0 failed on a throwaway copy. It is NOT applied to `server/` and you
  will not apply it there (protected path). Section B verifies it
  further; applying it to main is Pax's step, not yours.
- UTM: the OS image file (about 6 GiB) is still NOT on this Mac.
  Section H is readiness work only until the file exists.
- OpenScreen is NOT installed and the recorder addendum stays removed.
  Do not install OpenScreen, do not record with it, do not re-create
  the addendum. That work happens tonight with the boss.

## Protected paths — NEVER modify, create, or delete

`os/worlds/custos/`, `os/worlds/officina/`, `os/worlds/musica/`,
`os/worlds/science-lab/`, `eval/`, `index.html`, `js/`, `server/`,
`crates/`, `package.json`, anything under `native/` (build and run
only), existing files under `tests/`, `docs/`, `README.md`,
`TASKS_V3.md`, `OPENCODE_TASKS_100.md`, `OPENCODE_NEXT_TASK.md`,
`OPENCODE_TASKS_ROUND2.md`, this file, and the four bus files
(`bus-tools/bus-poll`, `bus-tools/bus-rooms`, `bus-tools/bus-send`,
`tests/test_bus_admin_e2e.py`). MCP wiring is parked by the boss's
order — no MCP tasks in this round, do not start any.

All new code lives only in `labs/`, `hortus-rung3/`, `oc-proofs/`.

## Standing rules

- Proof or it did not happen: every claim carries the command, the
  output file, or the screenshot that proves it.
- First red in a section: write the exact error into the report, move
  to the next task. Never loop on one failure.
- Dispatch is SIMULATED only, always — nothing dials, posts, or
  dispatches to a real service, in any section, ever.
- Live Spark ASSESSMENT calls are allowed ONLY in Section R, under
  its $5 round cap, tracked per call in the report (boss's order
  2026-11-01: only about $5 spent on the key so far, test more).
  Every other section spends $0.
- Fresh unique file names for every piece of footage, always.
- Commit per section on `opencode/mac-tasks`, message naming the
  section and task range.

## Section A — Close round 2 properly (NC-001..NC-012)

- NC-001: Write `oc-proofs/ROUND2_GAPS.md`: the two round-2 sections
  that never landed (G endurance, I final sweep), what each was
  supposed to prove, and where its replacement lives in this round.
- NC-002: Re-run the round-2 Section H review tools test suite on the
  current branch; record the result in the report.
- NC-003: Re-run labs/molecules and labs/music3d validation tests;
  record both results.
- NC-004: Verify every file listed in `oc-proofs/footage/FOOTAGE_INDEX.md`
  still exists on the branch with the same byte size; table the result.
- NC-005: ffprobe every round-2 footage clip; confirm each duration
  matches its index entry within 0.1 s; table the result.
- NC-006: Re-run the rung-3 verification (`hortus-rung3/run.py`) on
  this Mac; confirm the headline numbers match RUNG3_CLOSEOUT.md.
- NC-007: Confirm the solver determinism claim again: run the champion
  coarse case 3 times, diff the outputs, record byte-identical or not.
- NC-008: Audit `oc-proofs/` for any file that claims a result without
  a proof artifact next to it; list offenders in the report.
- NC-009: Write `oc-proofs/BASELINES.md`: the exact test counts you
  measured at round-3 start (node, custos, officina, queue-throwaway).
- NC-010: Check the branch for files over 10 MB; list them with sizes
  (the film clips are expected; anything else is a finding).
- NC-011: Confirm `git status` is clean at section start; if not, list
  what was dirty and why in the report before touching anything.
- NC-012: Section A summary into ROUND3_REPORT.md with all numbers.

## Section B — Queue suite on the Mac, endgame (NC-013..NC-024)

- NC-013: Apply `oc-proofs/queue-mac-optional-import.diff` to a FRESH
  throwaway copy of current main; run the queue suite; record counts.
- NC-014: Same throwaway: run the suite under plain `unittest` too;
  record both runners' counts side by side.
- NC-015: Prove the diff changes nothing where the module exists:
  run the suite in an environment where `dynamic_credentials` IS
  importable (stub it on sys.path); record counts.
- NC-016: Write the same optional-import treatment for the second
  reference the round-2 grep found (`server/queue/spark_gen.py` path
  insertion) as a NEW diff file in oc-proofs. Do not apply it anywhere.
- NC-017: Verify NC-016's diff on a throwaway copy the same way;
  record counts before and after.
- NC-018: Grep the whole repo for other absolute `/opt/muse` or
  sandbox-only paths in Python and JS; table every hit in oc-proofs.
- NC-019: For each NC-018 hit, write one line: breaks on a plain Mac,
  or harmless, and why.
- NC-020: Draft `oc-proofs/queue-fix-final.md`: the two diffs, the
  proof counts, and the exact apply order Pax should use on main.
- NC-021: Confirm the 4 collection-error modules from the diagnosis
  all collect and run under the fixed throwaway; name them.
- NC-022: Record the Mac Python version, pytest version, and node
  version used for every Section B run in the report.
- NC-023: Throwaway copies must be deleted after each proof; verify
  and state that none remain.
- NC-024: Section B summary into the report.

## Section C — Hortus rung 4, preparation only (NC-025..NC-036)

Rung 4 is a physical cross-check and stays the boss's call. This
section prepares everything so the day he says go, nothing is missing.
Nothing here buys, orders, or fabricates anything.

- NC-025: Write `hortus-rung3/RUNG4_PROTOCOL.md`: the bench test
  protocol — heatsink under test, heat source, thermocouple or IR
  measurement points, ambient logging, safety limits.
- NC-026: Add the parts list to the protocol: every physical item the
  bench test needs, with the spec that matters (no prices, no links
  to buy).
- NC-027: Add the measurement log template (CSV header + one example
  row clearly marked EXAMPLE) to `hortus-rung3/`.
- NC-028: Add the pass/fail rule, stated in advance: which simulated
  number the bench result gets compared against, and what agreement
  percentage counts as rung 4 earned. Leave the percentage as a
  marked blank for the boss; do not invent his threshold.
- NC-029: Write the simulation-side prediction sheet: run the solver
  for the exact geometry the protocol names, record predicted watts
  at the protocol's stated h values, in `hortus-rung3/`.
- NC-030: Add an uncertainty budget table to the protocol: grid error,
  h uncertainty, material k spread, each with its measured size from
  the rung-3 work.
- NC-031: Write the commercial-solver comparison plan (which class of
  tool, what geometry file it needs, what output would settle the
  comparison) — plan only, no accounts, no installs.
- NC-032: Add a geometry export: write the champion fin geometry as a
  simple documented text format (dimensions in mm) in `hortus-rung3/`
  so any CAD or solver can consume it later.
- NC-033: Validate NC-032 by re-reading it with a fresh parser in the
  same script run and diffing against the source numbers.
- NC-034: Add the "what would falsify rung 3" paragraph to the
  protocol: the bench outcomes that would prove the solver wrong.
- NC-035: Cross-check the protocol's stated h values against the
  values used in RUNG3_CLOSEOUT.md; fix any mismatch in the protocol
  (not in the closeout).
- NC-036: Section C summary into the report.

## Section D — Scientia cross-checks, labs only (NC-037..NC-048)

The Delaney gate itself is Milo's lane and is not touched here. These
are independent cross-check tools in `labs/`; their results never
count as the gate.

- NC-037: Build `labs/delaney-xcheck/`: a from-scratch runner for the
  Delaney (2004) ESOL equation using only the paper's published
  coefficients, written from the equation, not copied from the gate
  code (which you must not read for this task).
- NC-038: Fetch nothing: use the archived Delaney CSV if it is present
  in your checkout; if absent, record that and stop the section's
  remaining run tasks (still write the runner and its self-test).
- NC-039: Add a `--selfcheck` mode to the runner that verifies its
  descriptor math on 5 hand-computable molecules; all 5 must pass.
- NC-040: Run the xcheck on the archived CSV; record R², RMSE, MAE.
- NC-041: Compare NC-040's numbers against the prep numbers in the
  repo's gate record (R² 0.725 / RMSE 1.099 / MAE 0.844 for the paper
  equation) and table any difference with its likely cause (the known
  one: RDKit Wildman–Crippen LogP vs the paper's Daylight CLOGP).
- NC-042: Verify the archived CSV's sha256 still matches the recorded
  `8c06a76f…f189`; state match or mismatch.
- NC-043: Build `labs/mol-audit/`: re-fetch the 5 round-2 molecule
  JSONs' source values from PubChem (live, keyless) and diff every
  field against `labs/molecules/data/`; table diffs.
- NC-044: For any NC-043 diff, write whether the local file or the
  live value is stale, with the evidence.
- NC-045: Extend the xcheck with a fitted-OLS mode, clearly labeled
  NOT Delaney in every output line it produces.
- NC-046: Add tests for the xcheck runner (descriptor edge cases:
  empty SMILES, salts, charged species) and run them.
- NC-047: Write `labs/delaney-xcheck/README.md`: what it proves, what
  it does not prove, and the sentence "the gate is Milo's; this is a
  cross-check" in the first paragraph.
- NC-048: Section D summary into the report.

## Section E — Musica 3D, expansion (NC-049..NC-060)

All work in `labs/music3d/`. The Musica product pack is Hana's lane
and is not touched; this is the labs viewer growing up.

- NC-049: Add the natural minor scale (A minor) as a second playable
  row, from the same note-to-height data map; no new geometry code.
- NC-050: Add chord stacks: C major, G major, A minor, F major as
  three-note columns that play together, highlight sync kept.
- NC-051: Add a tempo control (60 to 140 BPM); playback timing and
  highlight must stay in sync at both extremes; prove at 60 and 140.
- NC-052: Add a metronome tick option (WebAudio click on the beat),
  off by default.
- NC-053: Screenshot pack: start, mid-chord highlight, octave row,
  minor row — 4 fresh-named stills in `labs/music3d/shots/`.
- NC-054: Record one 15 s clip of the chord sequence playing
  (screenshot-stitched method is fine; say so in the index note).
- NC-055: Extend the validation tests: note-to-height map covers both
  scales and all four chords; no duplicate heights inside a chord.
- NC-056: Verify the amber playing-note color is still #FFBE55
  everywhere it is used; grep and table the hits.
- NC-057: Add a data-only export: the full note map (both scales,
  chords) as one JSON in `labs/music3d/`; validate it parses.
- NC-058: Check the viewer at 390 px width; screenshot; the staff
  must not clip a note.
- NC-059: Measure and record first-render time of the viewer page on
  this Mac (three runs, median).
- NC-060: Section E summary into the report.

## Section F — Molecules, expansion (NC-061..NC-072)

All work in `labs/molecules/`.

- NC-061: Add 5 more compounds from PubChem, same pipeline as round
  2: benzene is done; add toluene, acetone, methanol, urea, and
  caffeine's sibling theobromine. CIDs recorded in SOURCES.md.
- NC-062: For each new compound: ball-and-stick and space-filling
  stills, fresh names, in `labs/molecules/shots/`.
- NC-063: Audit double bonds across ALL compounds now in the viewer:
  every double bond must render as two cylinders; write a check that
  counts them from the data and table data-count vs rendered-count.
- NC-064: Add one ring compound stress case (naphthalene) and verify
  its two fused rings render closed.
- NC-065: Extend the JSON validation tests to all compounds: atom
  counts, bond counts, and valence sanity per compound.
- NC-066: Verify every compound's formula in SOURCES.md against its
  JSON's atom tally; fix SOURCES.md only (data wins).
- NC-067: Add a measure-tool drill: measure 5 known bonds across
  compounds and compare each against the PubChem bond length where
  published; table the deltas.
- NC-068: Add element color legend overlay to the viewer (data-driven
  from the colors already in use; no new palette).
- NC-069: Screenshot: legend open over caffeine, labels dragged —
  one fresh-named still.
- NC-070: Record one 10 s rotation clip of naphthalene
  (screenshot-stitched acceptable; note the method).
- NC-071: Check the viewer with WebGL disabled (fallback message
  must be honest and visible); screenshot the fallback.
- NC-072: Section F summary into the report.

## Section G — Review tools, expansion (NC-073..NC-084)

All work in `labs/review/`. The tools enforce the product's rules:
ID always UNIDENTIFIED, no name field anywhere, purge is real.

- NC-073: Add 6 new sample incidents to the sample set: two yellow,
  two red, two baseline-normal, spread across Vigiles, Ignis,
  Medicus categories from `js/products.js` (read-only reference).
- NC-074: The BOLO renderer must reject a sample record that
  smuggles a `name` field: add the test first, watch it fail if the
  guard is missing, then confirm the guard exists or add it in labs.
- NC-075: Extend the purge drill: purge on a copy with interleaved
  kept and purged records; verify the after-file byte count and that
  reconstruct finds no gaps.
- NC-076: Tier counter fuzz: 200 generated records with known tier
  proportions; the counter must match the hand-computed proportions
  exactly.
- NC-077: Timeline view: add a filter by division; screenshot all
  three divisions filtered, fresh names.
- NC-078: The cannot-do page: add the two new limits proven in round
  2 and 3 work (no live DNS proof in Custos tests; no UTM boot
  without the image) — labs page only, wording plain.
- NC-079: Add a print stylesheet check for the BOLO page: print
  preview screenshot; the word UNIDENTIFIED must be visible.
- NC-080: Verify no sample record contains a real person's name, a
  real address, or a real plate string; grep-based check, table it.
- NC-081: Add a records schema spot-check against `js/schema.js`
  (read-only): every sample record validated; failures listed.
- NC-082: Extend review tests to cover NC-074, NC-075, NC-076, NC-081;
  run the full labs/review suite.
- NC-083: Screenshot pack refresh: bolo, timeline (filtered),
  purge-after, cannot-do — 4 fresh-named stills.
- NC-084: Section G summary into the report.

## Section H — UTM readiness, no image yet (NC-085..NC-096)

The image file is not on this Mac. Everything here makes the boot
check a five-minute job the day it arrives. If the file appears
mid-round, stop and report before booting anything.

- NC-085: Write `oc-proofs/utm/VM_SPEC.md`: the exact UTM settings
  the image needs — x86_64 emulation, a MODERN CPU model (the
  Freebuff SIGILL lesson: qemu64-class CPUs break baked tools),
  RAM, disk attach as the built .img, serial console enabled.
- NC-086: Write a `utmctl` create-and-configure script in
  `oc-proofs/utm/` that builds the VM from VM_SPEC.md but does not
  start it; shellcheck it or dry-parse it and record the result.
- NC-087: Write the boot-check script: waits for the guest, answers
  in order — does ttyS0 give a shell, did DHCP get a lease, does the
  dashboard answer HTTP, what does the updater log say, which
  systemd units failed. It only reports; it fixes nothing.
- NC-088: Test NC-087's script against NO running VM: it must fail
  soft with a clear "no VM" message, not hang. Record the behavior.
- NC-089: Write the firstboot checklist (crew logins, git identity,
  push token location, STOP file location for the loop) as
  `oc-proofs/utm/FIRSTBOOT.md` from the image lane's own docs in the
  repo (read-only).
- NC-090: Verify UTM version and utmctl version on this Mac; record
  both in VM_SPEC.md.
- NC-091: Measure free disk space on this Mac; the image plus a
  working copy needs about 13 GiB; state the headroom number.
- NC-092: Write the image intake step: how the .img gets verified on
  arrival (sha256 against the build record
  `c22df0ae1351e684864ba1c52a6dd2745d307bea0df4aae2323b4d063a7c91c5`)
  before any boot attempt.
- NC-093: Check whether UTM supports a serial log file on this
  version; if yes, add it to VM_SPEC.md (the ttyS0 evidence trail).
- NC-094: Draft the rollback note: how the VM gets deleted and the
  image re-copied if a boot attempt corrupts the working copy;
  golden base stays read-only.
- NC-095: Re-read the round-2 utm-boot-report.md and list in the
  report every claim in it that Section H has now superseded.
- NC-096: Section H summary into the report.

## Section I — Native app, build and behavior only (NC-097..NC-108)

`native/` is protected: build it, run it, measure it, screenshot it.
Never edit a Swift file. Findings go in the report, fixes are not
yours to make.

- NC-097: Clean-clone the repo to a throwaway directory; `swift
  build` there; record wall time and result.
- NC-098: Launch the built app; confirm the web UI loads inside it;
  screenshot, fresh name.
- NC-099: Offline drill: launch with networking disabled at the OS
  level for the app if feasible, or with the backend stopped;
  record exactly what the app shows (honest offline state or not).
- NC-100: Window size matrix: 3 sizes (small, laptop, large);
  screenshot each; note any clipped or overlapping panel.
- NC-101: Camera permission state: record whether the app asks, and
  at what moment (launch vs first wall view). Do not grant or deny
  anything new; report the current state only.
- NC-102: Icon inventory: which icon assets the app bundle uses and
  their sizes; list any missing size the platform expects.
- NC-103: Memory footprint: app resident size idle and with the
  camera wall open; record both numbers.
- NC-104: Cold start timing: 3 launches, median seconds to usable UI.
- NC-105: Check the app against the current main tip (25e6fca1 or
  later): does the bundled web UI match the repo's current index
  build? State how you checked.
- NC-106: Write `oc-proofs/native-app-findings.md`: every defect or
  gap found in this section, each with its proving screenshot name.
- NC-107: Delete the throwaway clone; verify deletion.
- NC-108: Section I summary into the report.

## Section J — Film support, app-side footage (NC-109..NC-124)

The film is a 3-minute platform cut: Meta OS first, then the systems
one by one. These clips feed that cut. Screenshot-stitched clips are
acceptable; every index entry must state the method honestly. No
OpenScreen (tonight, with the boss). Fresh unique names throughout;
all clips into `oc-proofs/footage/` with FOOTAGE_INDEX.md updated.

- NC-109: Vigiles deep-dive clip, 15 s: division panel, a flagged
  record opening, the ID: UNIDENTIFIED card visible.
- NC-110: Ignis deep-dive clip, 15 s: division panel, a smoke (yellow)
  and a flame (red) record side by side.
- NC-111: Medicus deep-dive clip, 15 s: division panel, a
  person-on-ground record and one look-alike record (bench sleeper
  class) side by side.
- NC-112: Tier explainer clip, 10 s: the same scene shown yellow,
  then red, using sample records only.
- NC-113: Custos deep-dive clip, 15 s: the patrol output with all
  nine categories listed (post RW-003/RW-004 state).
- NC-114: Officina surface clip, 10 s: the world pack surface as it
  exists in the app today; if it has no surface, film the pack file
  view and say so in the index (honest absence).
- NC-115: Scientia surface clip, 10 s: same rule as NC-114.
- NC-116: Musica surface clip, 10 s: same rule; if the labs music3d
  viewer is the only surface, film that and label it LABS in the
  index.
- NC-117: Phone-width versions of NC-109 and NC-111 at 390 px, 10 s
  each.
- NC-118: Poster frames: extract one sharp still from each of
  NC-109..NC-117 at its best moment; fresh names; these are Devpost
  gallery candidates.
- NC-119: Write the edit decision list `oc-proofs/footage/EDL_3MIN.md`:
  map every usable clip (rounds 2 and 3) to a slot in the 3-minute
  platform structure (OS first, then Imperium, Custos, Officina,
  Scientia, Musica), each with in/out durations summing to 180 s.
- NC-120: Verify the EDL arithmetic: the slots sum to exactly
  180.0 s; show the sum.
- NC-121: View one frame from every new clip (mid-frame rule);
  replace any black or blank clip and record the replacement.
- NC-122: ffprobe all new clips; duration table into the index.
- NC-123: Confirm no clip shows a real person's name, a real camera
  feed with identifiable people, or anything unlabeled-simulated
  that reads as real. Table the check per clip.
- NC-124: Section J summary into the report.

## Section K — Endurance and budget drills (NC-125..NC-136)

This is round 2's missing Section G, expanded. SIMULATED only. The
dispatch target is the labeled simulated endpoint or a local stub.
Live spend: $0.

- NC-125: 60-minute soak: the patrol-to-dispatch loop against the
  simulated endpoint, synthetic incidents; log action counts and
  any error; the loop's own caps (8 actions / 12 calls / $0.50 per
  incident) must never be exceeded — prove from the log.
- NC-126: Budget-cap trip drill: point the guardrail at a local
  stub with a tiny cap; confirm the refusal fires at the cap and
  the error is the guardrail's own; record the exact refusal text.
- NC-127: Restart drill: kill and restart the stack mid-incident;
  the record log must show no duplicate dispatch for the same
  incident after restart.
- NC-128: Offline drill: network to the model endpoint cut (local
  route only); the system must record the incident as unconfirmed,
  spend $0 more, and say so in its own log.
- NC-129: Backpressure drill: 50 synthetic incidents at once
  against the simulated endpoint; record queue behavior and the
  first failure mode, if any.
- NC-130: Records integrity after NC-125..NC-129: the append-only
  log reconstructs with no gaps; run the reconstruct check and
  record it.
- NC-131: Purge drill on the soak records COPY (never the original):
  close one incident as false positive; its evidence entries purge;
  verify counts before and after.
- NC-132: Clock drill: set the Mac clock display only (do not
  change system time) — instead, feed the loop a record with a
  skewed timestamp and record how the timeline orders it.
- NC-133: Disk-pressure note: measure the records log growth during
  the soak (bytes per incident); state the number.
- NC-134: Memory note: peak resident size of the loop process
  during NC-129; state the number.
- NC-135: Write `oc-proofs/endurance.md`: all drill results, each
  with its log file name.
- NC-136: Section K summary into the report.

## Section L — Performance and repo hygiene (NC-137..NC-148)

Report-only for anything outside `labs/` and `oc-proofs/`. Findings
are reported, never fixed, outside your own directories.

- NC-137: App home load timing on the Mac: 5 loads, median, with
  the method stated.
- NC-138: Camera wall render timing: time to all cards painted,
  3 runs.
- NC-139: Cargo release build timing on a throwaway clone; record
  wall time and the workspace result.
- NC-140: Node suite wall time on this Mac (current branch);
  compare against Pax's sandbox baseline in the report text (about
  33 s at 2026-11-01) and note the difference without explaining
  what you cannot measure.
- NC-141: Repo size audit: the 10 largest files in the repo with
  sizes; the 63 MB `sculpting_a_human_body.glb` in the root is
  expected — confirm its size and that nothing references it, or
  list what does (read-only greps).
- NC-142: Git LFS evaluation, report only: which current files
  would move to LFS under a 10 MB rule, and the total bytes.
- NC-143: Duplicate-file hunt: identical hashes across the repo
  (excluding .git); table any duplicate over 1 MB.
- NC-144: Labs weight check: total size of `labs/` and `oc-proofs/`
  on the branch; list the 5 heaviest artifacts you created.
- NC-145: Footage weight: total MB of all film clips on the branch;
  state it plainly (the boss moves these by hand).
- NC-146: Check the branch for committed `.DS_Store`, editor
  backups, or temp files; list them (report only).
- NC-147: Write `oc-proofs/hygiene.md` with NC-141..NC-146 results.
- NC-148: Section L summary into the report.

## Section M — Safety self-audit (NC-149..NC-160)

Auditing our own tree. Report-only outside your directories.

- NC-149: Secrets sweep: grep the repo (excluding .git) for the
  usual key and token shapes; report counts per pattern, never the
  values. Any real hit is a stop-and-report finding.
- NC-150: Confirm the four excluded bus files are not referenced by
  any file you created in rounds 2 and 3 (grep your own dirs).
- NC-151: Simulated-endpoint assertions: every dispatch call site
  in the repo's demo path must require the simulated flag; list
  the call sites and how each enforces it (read-only).
- NC-152: Verify there is no code path in the repo that dials a
  real emergency number or posts to a real dispatch service;
  state the grep patterns used and the result.
- NC-153: Vendored-license inventory: every vendored library in
  `labs/` (three.js and any other) has its license file present;
  table library, version if stated, license.
- NC-154: Asset-license inventory for footage: every clip in the
  index lists its sources (own render, app capture, sample data);
  flag any clip whose source is unstated.
- NC-155: Check that every screenshot in `labs/` and `oc-proofs/`
  that shows a face-like image is either sample data or a
  detection crop, never an identification; table the check.
- NC-156: Confirm the string "UNIDENTIFIED" appears in the BOLO
  renderer and that no labs code writes a person's name into a
  record; grep proof.
- NC-157: Check your own new files for accidental absolute sandbox
  paths (`/opt/muse`, `/home/hatch`) that would break on the Mac
  or leak layout; fix your own files if found.
- NC-158: Write `oc-proofs/safety-audit.md` with NC-149..NC-157.
- NC-159: If NC-149 found a real secret: stop the round, write
  only "STOPPED: secret finding, see safety-audit" in the report,
  and end. (This task exists so the stop is a procedure, not a
  judgment call.)
- NC-160: Section M summary into the report (or the NC-159 stop).

## Section N — Fresh-reader runbook test (NC-161..NC-170)

`docs/` and `README.md` are protected. You are the fresh reader:
follow them literally on this Mac and log every stumble. The log
feeds the crew's docs work; you do not fix the docs.

- NC-161: From a clean clone, follow the README's run instructions
  word for word. Log every step where the text and reality differ,
  in `oc-proofs/runbook-log.md`, with the step quoted.
- NC-162: Time the full path from clone to first app screen;
  record it.
- NC-163: Follow the README's test instructions; record which
  suites it names and whether each command works as written.
- NC-164: Follow the Spark configuration table in the README;
  record whether each setting exists where the table says (do not
  print any key value; presence and shape only).
- NC-165: Note every place the instructions assume sandbox layout
  (like the `/opt/muse` paths from Section B) as a stumble entry.
- NC-166: Check every relative link in the README from the clone;
  list dead ones.
- NC-167: Check the README's stated test numbers against your
  NC-009 baselines; list any that disagree.
- NC-168: Write the top-5 stumbles summary at the head of the log,
  ranked by how hard they would hit a new reader.
- NC-169: Verify the log contains no credential values (grep your
  own log for key-shaped strings; state the result).
- NC-170: Section N summary into the report.

## Section O — Data-prep tooling, labs (NC-171..NC-184)

New eval datasets are landing on Pax's side (FIRESENSE, AIRTLAB,
CAUCAFall, GMDCSA24, a wildfire set). They are not in this repo.
Build the tooling they will need, in `labs/data-prep/`, tested on
synthetic fixtures you generate. Do not fetch any dataset yourself.

- NC-171: Build a frame extractor: video file in, JPEG frames out
  at a stated fps, deterministic naming (source, timestamp).
- NC-172: Fixture test: generate a 5 s synthetic video (color bars
  with a moving block), extract at 2 fps, assert 10 frames and
  their order.
- NC-173: Add scene-change mode: extract on frame-difference
  threshold instead of fixed fps; fixture must show fewer frames
  on a static scene, more on a busy one.
- NC-174: Build a contact-sheet builder: N frames in, one labeled
  grid image out (file name under each frame).
- NC-175: Fixture test for NC-174 with 12 frames; view the sheet;
  labels must be legible.
- NC-176: Build a perceptual-hash dedupe: near-identical frames
  (resized, recompressed copies) must hash-collide; genuinely
  different frames must not.
- NC-177: Fixture test for NC-176: 6 frames (3 originals, 3 altered
  copies); expect exactly 3 groups.
- NC-178: Add an augmentation detector: flag frames that are
  flips/crops/brightness shifts of another frame in the set, using
  the NC-176 hashes plus flip-invariant comparison.
- NC-179: Fixture test for NC-178 with one flipped copy; it must be
  flagged, and a different scene must not be.
- NC-180: Build a manifest writer: for a folder of frames, emit a
  JSONL manifest (file, source, timestamp, hash, group id) — the
  exact shape an adjudication pass needs.
- NC-181: Round-trip test: manifest a fixture set, delete one
  frame, re-run; the tool must report the gap, not renumber.
- NC-182: Throughput measure: frames per second of NC-171 on the
  fixture, and of NC-176 hashing; record both.
- NC-183: Write `labs/data-prep/README.md`: each tool, its command,
  its fixture, its measured throughput.
- NC-184: Section O summary into the report.

## Section P — Input and accessibility checks (NC-185..NC-194)

Checks only. `index.html`, `js/`, and `styles.css` are protected;
findings go in the report for Hana's lane, fixes are hers.

- NC-185: Keyboard-only pass: drive the app home with keyboard
  alone; list every control that cannot be reached or activated.
- NC-186: Mouse-only pass: same surface, mouse alone; list any
  control that requires the keyboard.
- NC-187: Tab-order map: record the focus order on the home screen
  as a numbered list; flag any jump that skips a visible control.
- NC-188: Focus visibility: screenshot 3 focused states; the focus
  indicator must be visible in each.
- NC-189: Contrast spot-check: sample 10 text/background pairs in
  the app; compute ratios from the actual rendered colors; table
  them against the brand hexes (read-only from `js/products.js`).
- NC-190: Reduced-motion: enable the OS reduced-motion setting;
  record which app animations stop and which do not.
- NC-191: 200% zoom pass at 390 px width: screenshot; list any
  clipped or overlapping elements.
- NC-192: Screen-reader landmarks: list the landmark roles the
  home page exposes (from the DOM, read-only).
- NC-193: Write `oc-proofs/input-a11y.md` with NC-185..NC-192,
  each finding tied to a screenshot or DOM excerpt.
- NC-194: Section P summary into the report.

## Section Q — Final sweep (NC-195..NC-200)

- NC-195: Full suite pass on the final branch state: node, custos,
  officina, labs suites; one table against NC-009 baselines.
- NC-196: Lane audit: list every file this round changed vs main;
  any protected path is a failure — print the list in the report.
- NC-197: Verify `oc-proofs/ROUND3_REPORT.md` contains a summary
  for every section A to R; list any section whose summary is
  missing (including this one, written last).
- NC-198: Total the footage: every clip made this round, seconds
  summed, in the index.
- NC-199: Write the round-3 headline block at the top of the
  report: tasks done, tasks blocked with one-line reasons, total
  live spend (from Section R's ledger; $0 if R was not reached).
- NC-200: STOP. Do not start the boss's end-to-end test, do not
  install OpenScreen, do not begin any new section. The round ends
  here; the report is the deliverable.

## Section R — Live Spark testing (NC-201..NC-216)

Added by the boss's order 2026-11-01: only about $5 is spent on the
API key so far, and more tests mean more output, more fixes, and a
better system. This is the ONLY section allowed live model calls.

Rules for this section, all hard:
- Live calls are ASSESSMENT calls through the repo's existing Spark
  path, using the key from the boss's Mac key file (line 1 only).
  Never print, log, commit, or screenshot the key value.
- Dispatch stays SIMULATED, always. Live model calls never change
  the dispatch rule.
- Round cap for this section: $5 cumulative. Every call's usage is
  recorded in the report as it happens. At the cap, NC-215 fires.
- Frames come only from inside this repo (test footage and fixtures
  already committed). Do not fetch external frames for live passes.

- NC-201: Open the spend ledger in ROUND3_REPORT.md: read the
  guardrail state through the repo tooling and record the starting
  counter (a number, never the key).
- NC-202: Inventory every eval-usable frame inside the repo;
  table counts by division (Vigiles, Ignis, Medicus) and by
  positive vs look-alike where the source labels say.
- NC-203: Live pass 1, Vigiles: 25 repo fight frames through real
  Spark; record raw MATCH / HELD / MISS counts and the pass spend.
- NC-204: Live pass 2, Ignis: 25 repo frames, fire positives plus
  steam/fog look-alikes; same recording.
- NC-205: Live pass 3, Medicus: 25 repo frames, person-down
  positives plus bench/sunbathing/yoga look-alikes; same recording.
- NC-206: Build the adjudication worksheet: every HELD and MISS
  from NC-203..205 gets one line — pre-event frame, genuine miss,
  or borderline — as a WORKSHEET in oc-proofs. Verdicts are not
  yours to change; Pax and Milo adjudicate.
- NC-207: Prompt-mirror live check: run the same 10 frames through
  both prompt builders (the app's and the queue's); diff the
  outputs field by field; table every difference. This is live
  evidence for the crew's prompt-mirror item.
- NC-208: Soak with the real model: Section K's loop shape, 10
  synthetic incidents, real Spark assessments, simulated dispatch;
  the per-incident caps must hold; record spend.
- NC-209: Budget refusal, live path: set a tiny guardrail cap on a
  local copy of the state, run one assessment; record the refusal
  text verbatim and the cents spent reaching it.
- NC-210: Marks audit: collect every "Visible marks:" line from
  the live passes; flag any that assert a mark a human cannot see
  in the frame; the flagged list goes in the worksheet for review.
- NC-211: Schema validity: validate every live output against the
  v2 contract; the invalid count must be 0; table any failure with
  its frame id.
- NC-212: Spend reconciliation: the guardrail counter's movement
  vs the sum of recorded per-pass usage; any drift is stated and
  explained or flagged as unexplained.
- NC-213: Latency table: per-call milliseconds across the live
  passes (median and p95). These numbers are internal until Pax
  approves them for any claim.
- NC-214: Failure museum deposit: the 5 worst frames with their
  outputs into `oc-proofs/failure-museum/`, one-line note each.
- NC-215: STOP RULE: if cumulative round spend reaches $5 at any
  point, stop live work immediately, record where it stopped, and
  finish the round on $0 sections only.
- NC-216: Section R summary into the report, ending with the
  round's TOTAL live spend as a single number.
