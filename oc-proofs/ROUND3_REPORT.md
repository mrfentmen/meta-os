# Round 3 running report (Mac side)

## Section A — Close round 2 properly (NC-001..NC-012) — DONE

- NC-001: oc-proofs/ROUND2_GAPS.md written (G endurance + I sweep: what each
  was to prove, replacements K and Q).
- NC-002: review tests re-run on this branch: 2/2 pass.
- NC-003: molecules + music3d validation re-run: 6/6 and 3/3 pass.
  Combined labs total: 11/11.
- NC-004: all 7 footage files present, byte sizes tabled (636149, 511369,
  1380909, 200377, 563149, 378359, 1802947).
- NC-005: ffprobe durations match the index exactly (20/20/20/10/15/10/30 s).
- NC-006: verification re-run from pushed code: analytic 181.659 W/m at
  h=55.8; sim 180.139 (0.84%) and 180.916 (0.41%); balance 2e-3 both.
  Matches RUNG3_CLOSEOUT.md.
- NC-007: champion coarse case re-run 3x: byte-identical
  (183.545700 W/m, 9966 iters) — matches round-2 claim.
- NC-008: proof-artifact audit: every labs/oc-proofs path cited in the
  round-1/2 reports exists on disk. Zero offenders. (Soak log still
  growing; excluded from the audit until Section K closes it.)
- NC-009: oc-proofs/BASELINES.md written (node 1999/1943/56 exact,
  cargo 1412/0, custos 48/48, officina 49/49, queue-throwaway 110/110).
- NC-010: files over 10 MB (excluding .git/target/node_modules): exactly
  one, the Swift build cache ModuleCache .swiftmodule (untracked build
  output, expected). All film clips under 2 MB each.
- NC-011: status at section start was NOT clean: OPENCODE_TASKS_100_REPORT.md
  modified (in-progress Section G notes), plus untracked soak artifacts
  (soak-mem.log, nb-076-concurrency.txt) and target/ build output.
  Reason: endurance work in flight; committed at section boundaries only.
- NC-012: this summary.

## Section B — Queue suite on the Mac, endgame (NC-013..NC-024) — DONE

- NC-013: v3 patch in oc-proofs/queue-mac-optional-import.diff (unapplied).
- NC-014: throwaway of origin/main: pytest 110/110; unittest 110 OK.
- NC-015: stub-module run 110/110 — and it caught a real v2 bug (NameError
  on the importable-module path); v3 fixes it, all three legs green.
- NC-016/017: queue-sparkgen-optional-path.diff (conditional PYTHONPATH);
  throwaway with both diffs: 110/110 with and without stub.
- NC-018/019: table in queue-fix-final.md — 2 fixed, rest harmless/clean.
- NC-020: oc-proofs/queue-fix-final.md with apply order + proofs.
- NC-021: the 4 collection-error modules (test_queue, test_crew,
  test_evidence, test_supervisor) all collect and run under the fix.
- NC-022: node v24.21.0, python3 3.9.6, pytest 8.4.2 (in final doc).
- NC-023: throwaway-r3 removed (worktree list verified clean); scratch
  diff trees and stub module deleted.
- NC-024: this summary.

## Section C — Hortus rung 4, preparation only (NC-025..NC-036) — DONE

- NC-025/026/027/028: hortus-rung3/RUNG4_PROTOCOL.md — unit under test,
  parts (specs only), CSV log template with marked EXAMPLE row, pass/fail
  rule with the threshold left BLANK for the boss.
- NC-029: nc-029-prediction-sheet.md — 489.7 / 734.2 / 1025.0 W at h=30 /
  55.9 / 100; k=167→712.6, k=237→814.0 W. Raw log kept.
- NC-030: uncertainty table in the protocol, all sizes measured (grid
  0.4%, stair-step 0.6%, k -3%/+11%, h bracketed, sensors stated).
- NC-031: COMMERCIAL_COMPARE_PLAN.md — plan only, no accounts/installs.
- NC-032/033: champion-fin.txt geometry export; fresh-parser re-read
  diffs IDENTICAL in the same run.
- NC-034: falsifiability paragraph in the protocol (either sign counts;
  profile-shape falsifier included).
- NC-035: h cross-check — protocol central 55.9 matches closeout primary;
  closeout's flat-50 was sensitivity-only and stays there. No mismatch.
- NC-036: this summary.

## Section D — Scientia cross-checks (NC-037..NC-048) — DONE (CSV tasks recorded not-run)

- NC-037 DONE. labs/delaney-xcheck/xcheck.py: Delaney-2004 equation from
  the paper (0.16 -0.63*cLogP -0.0062*MWT +0.066*RB -0.74*AP), from scratch.
  Gate code never read (doesn't exist in this checkout anyway).
- NC-038 DONE as a negative: no archived Delaney CSV anywhere (searched).
  NC-040 (run), NC-041 (compare vs gate 0.725/1.099/0.844), NC-042 (sha256
  check) recorded NOT-RUN, not skipped-silently. Runner + selftest + OLS +
  mol-audit below all proceed.
- NC-039 DONE. --selfcheck 5/5 (benzene hand-verified term by term;
  tolerance 0.05; worst |err| 0.005).
- NC-043/044 DONE. Live PubChem re-fetch of all 5 round-2 structures:
  atom/bond counts, element lists, formulas, weights ALL MATCH. Nothing
  stale on either side.
- NC-045 DONE. --ols mode, every output line labelled "NOT Delaney".
- NC-046 DONE. Edge contract (empty→ValueError, salts/charged compute
  with documented behavior); an empty-SMILES hole found by the contract
  itself and fixed in the runner. Node bridge test 2/2.
- NC-047 DONE. labs/delaney-xcheck/README.md with the gate-is-Milo's
  sentence first.
- NC-048: this summary.

## Section E — Musica 3D, expansion (NC-049..NC-060) — DONE

- NC-049 DONE. A natural minor scale as second playable row (toggle
  Row 2: octave/minor), same NOTE_Y map, no new geometry code.
- NC-050 DONE. Chord stacks C/G/Am/F as three-note columns in a chord
  mode; all three highlight + sound in sync (meta names them).
- NC-051 DONE. Tempo slider now 60–140 BPM; single beatLen() drives
  playhead + tones. Verified playing at 60 and 140 (labels read, no
  errors, highlight tracks).
- NC-052 DONE. Metronome toggle (square-wave click per beat), off by
  default; toggled on without errors.
- NC-053 DONE. 4 fresh shots in labs/music3d/shots/: start, mid-chord
  (amber G major), minor row (A minor playing), octave row.
- NC-054 DONE. oc-proofs/nc-054-chords-15s.mp4 (15.0 s, video + matching
  chord audio; stitched-screenshot method stated).
- NC-055 DONE. Tests extended to 5/5 (minor coverage, chord heights
  distinct, octave 2x).
- NC-056 DONE. Amber #FFBE55 hits: footer text, code comment, PLAYING
  const, update() emissive+color sets. Caught + fixed a real bug where
  only the glow (not the color) changed.
- NC-057 DONE. labs/music3d/note-map.json (scale, minor, chords, order,
  heights) generated from the data module; parses (15/15/4 verified).
- NC-058 DONE. 390 px shot: toolbar wraps, staff + notes visible, no
  note clipped.
- NC-059 DONE. First render: 20/18/18 ms over 3 loads, median 18 ms.
- NC-060: this summary. Plus a real rendering bug found and fixed by the
  chord shots: staff slabs (z -23..+7) occluded every low note from the
  default camera (labels draw through, bodies did not). Slabs moved to
  z -31..-3 behind both rows; chord columns now fully visible. Affected
  all scale shots too — re-shot after the fix.

## Section G (round 2 tail): endurance drills — DONE except offline

- Soak 60 min (:8092, valid-frame held traffic): 12/12 samples, every
  health=200, assess=503, cameras=200, zero errors. RSS 59.8 MB start,
  103.3 MB after camera-proxy warmup (t+2), then 95–99 MB flat for 50
  min; peak 105,008 KB at t+4. No leak trend. Full log:
  oc-proofs/soak-mem.log.
- NB-072: 0 dispatches (no queue, no live model — nothing to dispatch;
  every receipt anywhere this round is sim-; count of receipts: 0).
- NB-073: trip recorded (556 stub calls, exact message + $75.00 figure).
- NB-074 DONE post-soak: killed :8092 (100 MB RSS), restarted, healthy
  in 1 s, held path 503 immediately. Records dir unchanged (220K,
  no crew-data — queue never ran here).
- NB-075: 220K before and after (0 growth; per-day projection at this
  cadence: 0 — the app server is stateless, records only grow when the
  queue runs).
- NB-076: 129 completed iterations, all cameras=200 + assess=503; one
  ~1-min window of localhost-refused mid-run, self-recovered, no crash.
- NB-077: TZ-independent (no wall-clock timestamps in the served API).
- NB-078/079 BLOCKED: no sudo, no fault-injection path. Recorded.

## Section F — Molecules, expansion (NC-061..NC-072) — DONE

- NC-061 DONE. 6 more compounds via the same pipeline (toluene, acetone,
  methanol, urea, theobromine, naphthalene); CIDs in SOURCES.md. Caught
  and fixed a wrong CID on methanol (962→887, PubChem-verified); added a
  cid-consistency test so it cannot regress.
- NC-062 DONE. 12 fresh stills (6 x bs/sf) in labs/molecules/shots/.
- NC-063 DONE. Double-bond audit, observed live: every order-2 bond in
  all 11 compounds renders exactly 2 cylinders (caffeine 4, aspirin 5,
  toluene 3, acetone 1, urea 1, theobromine 4, naphthalene 5; rest 0).
  Table matches data counts exactly.
- NC-064 DONE. Naphthalene face-on: two fused rings render closed.
- NC-065 DONE. Tests 13/13 (11 compounds + meta + cid): counts, bond
  endpoints, CPK membership, valence sanity, cid consistency.
- NC-066 DONE. All 11 formulas rechecked against JSON tallies — match,
  no SOURCES fix needed.
- NC-067 DONE. Measure drill, tool values vs SDF geometry: water O-H
  0.97/0.969, urea C=O 1.23/1.229, naphthalene fused C-C 1.42/1.415.
  Caffeine/ethanol SDF references computed (1.228, 1.514) but tool
  clicks would not land after a view change; marked as reference-only
  (identical pipeline to the three verified).
- NC-068 DONE. Data-driven legend overlay (from the EL color table),
  shot over caffeine with labels.
- NC-069 DONE. nc-069-legend-labels.png.
- NC-070 DONE. oc-proofs/nc-070-naphthalene-10s.mp4 (10.0 s, stitched).
- NC-071 DONE. Honest WebGL fallback added + tested via ?force2d=1:
  message + text list, no blank canvas (shot).
- NC-072: this summary.

## Section G — Review tools, expansion (NC-073..NC-084) — DONE

- NC-073 DONE. 6 new samples (007/008 yellow, 009/010 red, 011/012 normal;
  categories from js/products.js read-only): 12 records total.
- NC-074 DONE. BOLO refuses name-smuggling records (bolo-guard.mjs,
  shared with the page + tests). Before: silently ignored names (code
  inspection); after: loud refusal + test.
- NC-075 DONE. purge-copy.mjs on interleaved kept/purged:
  purged=4, byte counts printed, gaps=false.
- NC-076 DONE. 200-record fuzz, exact 80/70/50 match.
- NC-077 DONE. Division filter on timeline + 3 fresh shots.
- NC-078 DONE. cannot-do gains the 2 proven limits (DNS observational,
  no UTM boot without image).
- NC-079 DONE. @media print stylesheet; CDP-emulated print screenshot
  shows white page, UNIDENTIFIED, no chrome.
- NC-080 DONE. Grep over samples: no real names/addresses/plates.
- NC-081 DONE. All 12 records carry the incident contract (UNIDENTIFIED
  throughout).
- NC-082 DONE. Suite 6/6 (guard, purge, fuzz, contract, tier, schema).
- NC-083 DONE. 4 fresh stills (bolo, timeline, cannot-do, print).
- NC-084: this summary.

## Section H — UTM readiness, no image yet (NC-085..NC-096) — DONE (readiness only)

- NC-085 DONE. oc-proofs/utm/VM_SPEC.md (x86_64, modern CPU not qemu64,
  4 GB RAM, .img attach, serial + log on, shared network).
- NC-086 DONE. oc-proofs/utm/create-vm.sh (builds, never starts;
  dry-parsed OK; honestly stops before inventing utmctl flags).
- NC-087/088 DONE. oc-proofs/utm/boot-check.sh reports-only script;
  against no VM it exits 3 with "no VM named … — nothing to check"
  (verified, no hang).
- NC-089 DONE. oc-proofs/utm/FIRSTBOOT.md from the image lane's own
  docs: token at /etc/metaos/token, STOP-file behavior, 60 s timeout.
- NC-090 DONE. UTM 5.0.8 + utmctl 5.0.8 on this Mac (in VM_SPEC.md).
- NC-091 DONE. 736 GiB free; ~723 GiB headroom past the 13 GiB need.
- NC-092 DONE. Intake procedure with the recorded sha256
  (c22df0ae…7c91c5); golden base chmod 444.
- NC-093 DONE. Serial log file supported on UTM 5.0.8; in the spec.
- NC-094 DONE. Rollback note (delete VM, re-copy golden, re-verify).
- NC-095 DONE. Round-2 report claims superseded: (1) "no image
  anywhere" still true — re-verified whole-disk; (2) UTM "installed"?
  round 2 only assumed it — now verified 5.0.8 present; (3) the ttyS0
  question stays open (needs the boot); everything else in H replaces
  the round-2 note as the current reference.
- NC-096: this summary. If the file appears mid-round: stop and report
  before booting anything (standing order).

## Section I — Native app (NC-097..NC-108) — DONE (2 partials recorded)

- NC-097 DONE. Clean clone + swift build: 38 s, no errors.
- NC-098 PARTIAL. App launched (PID logged), AX window confirmed; web UI
  inside proven by committed round-2 tight crops (same binary path).
  No fresh screenshot (display capture stopped for privacy — see NC-100).
- NC-099 DONE as behavior: dead-backend launch stays up 12 s+, no crash,
  clean quit; web layer refusal state proven headless.
- NC-100 PARTIAL: resize works via AppleScript; only laptop size has
  screenshots (round-2 committed clip). Small/large unverified visually.
- NC-101 DONE: no prompt in 4 launches; TCC unreadable (SIP); needs human.
- NC-102 DONE: zero icon assets (finding #1).
- NC-103 DONE: 126–129 MB idle.
- NC-104 DONE: 1 s window x3 (content follows in seconds).
- NC-105 DONE: UI = localhost server, nothing bundled (source-proven).
- NC-106 DONE. oc-proofs/native-app-findings.md (6 items above).
- NC-107: throwaway clone deleted below.
- NC-108: this summary.

## Section J — Film support (NC-109..NC-124) — DONE

- NC-109/110/111: division deep-dives via labs review pages (timeline
  filtered + BOLO cards), 20/15/20 s.
- NC-112: tier explainer 10 s (yellow 001 then red 003, different scenes —
  stated; no same-scene pair exists in the samples).
- NC-113: Custos terminal 15 s (6 observed categories + SIMULATED
  escalations; task text says nine — observed five event categories plus
  summary/escalation records, tabled).
- NC-114/115: honest absences filmed (pack facts; worlds listing).
- NC-116: labs viewer 10 s, re-shot after catching a stale first cut.
- NC-117: phone 390 px x2, 10 s each.
- NC-118: 10 poster stills, one per clip.
- NC-119/120: EDL_3MIN.md, 12 slots, arithmetic sums to exactly 180.0 s.
- NC-121/122: mid-frames viewed (10/10 good), durations tabled exact.
- NC-123: content check per clip (above); one re-shoot logged.
- NC-124: this summary.

## Section L — Performance and repo hygiene (NC-137..NC-148) — DONE

- NC-137 DONE. App home loads x5: 168/185/187/200/306 ms, median 187 ms
  (headless Chromium, cache-warm navigations).
- NC-138 DONE. Camera-wall time-to-cards x3: 127/130/142 ms
  (selector-wait method, stated).
- NC-139 DONE. Cargo release --workspace on throwaway clone: 28 s wall,
  EXIT 0 (clone deleted after).
- NC-140 DONE. Node suite wall: 2 s on this Mac (1999/1943/56) vs Pax's
  ~33 s sandbox baseline. Difference noted as measured; the sandbox
  number likely includes clone+install or slower hardware — cannot
  measure from here, not explained further.
- NC-141..146 DONE. oc-proofs/hygiene.md: .glb is 2.2 MB not 63 MB and
  referenced only by the task text; LFS buys nothing (max 2.6 MB);
  one dup set (three.min.js x3, deliberate); labs 4.2 / proofs 12 /
  footage 9.4 MB; no junk files.
- NC-147 DONE (hygiene.md). NC-148: this summary.

## Section M — Safety self-audit (NC-149..NC-160) — DONE, no stop

- All sweeps green: 0 secrets, 0 bus refs, dispatch locked to SIMULATED
  by a loopback-checked validator, no emergency dialing anywhere,
  licenses present (one round-1 footnote), footage sourced, no faces,
  UNIDENTIFIED enforced, no personal paths in own files.
- NC-159 not triggered. Full table: oc-proofs/safety-audit.md.
- NC-160: this summary.

## Section O — Data-prep tooling (NC-171..NC-184) — DONE

- NC-171/172 DONE. extract.py + 5 s synthetic fixture → 10 ordered
  frames at 2 fps.
- NC-173 DONE. Scene mode: static 1 frame vs busy 16 (threshold 12).
- NC-174/175 DONE. Contact sheet 4x3, labels viewed legible.
- NC-176/177 DONE. dHash dedupe: 3 wild originals + copies → 3 groups
  (fixture fixed twice: near-identical testsrc frames and flat colors
  collide by design — the tool is honest, the fixture was weak).
- NC-178/179 DONE. Flip flagged, other scene not (plus a real bug
  found: --aug compared unflipped hashes; fixed).
- NC-180/181 DONE. Manifest with content-derived groups; delete +
  re-run reports GAP, no renumber.
- NC-182 DONE. 19.2 fps extract, 120.3 fps hash.
- NC-183 DONE (README). NC-184: this summary. Suite 6/6.
