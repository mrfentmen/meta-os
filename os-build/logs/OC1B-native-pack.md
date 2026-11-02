# OC1B-415/416/417/418/421/422 — decision-pack working papers

Tree 94010c76. No test file and no Swift mirror modified in this lane
(OC1B-421 attestation at the bottom). Classification base is
docs/NATIVE_TEST_PREP.md (38 UPDATE / 18 CARVE-OUT over 56 entries, measured
on 0da81e8); adjustments for this tree are listed under OC1B-418.

## OC1B-415 UPDATE option: what each group asserts, and what it would assert instead

UPDATE = strip the dead Swift slice, keep the live web check. Applies to 38
of the 55 native-mirror failures (30 file-level + 8 named). Per group:

- G1 (0 failures — nothing to update; 83/83 green proves the web contracts
  under these files already hold without Swift).
- G2 (6 file-level): each file loads a Swift slice (chip/department/tagline/
  notice/label/flame-gradient assertions on removed HeaderView/Ignis header)
  then checks a live web contract that still matches today: .product-badge
  13px/700/0.04em, .product-department 13px + .product-tagline 14px,
  limitations .note, picker label 13px muted, Ignis red-gradient. Updating =
  delete the Swift block, keep the web block (6 files).
- G3 (6 file-level): Swift AssessmentView/BodyStatus slices; the live OPS-CONSOLE
  subhead + mono-block frame + status rules still match in the web consoles
  (vigiles OPS-CONSOLE-6, ignis OPS-CONSOLE-3, medicus). Update = strip Swift,
  keep web (6 files).
- G4 (5 of 6 file-level): footer/settings/statusbar Swift font slices; live web
  contracts (.footer 13px muted + disclaimer words, .note 13px, status 13px /
  note 13px / mono 12.5px, settings labels 13px muted, panel h2 15px bold).
  Update = strip Swift, keep web (5 files).
- G5 (3 file-level + 2 named): Swift note/state-line slices; live web camera-state
  .note, guidance .note, facing-note .note contracts still match. Named:
  facing :62/:73 — drop the Swift service/Picker checks, re-point at the web
  facing labels + the web "About camera facing" note (both live in index.html).
  Update = 3 files + 2 tests.
- G6 (5 file-level): Swift placeholder/intro/state slices; live web mono-block
  13px + intro-words contracts still match. Update = 5 files.
- G7 (5 file-level): Swift banner/panel/heading/Stepper-label slices; live web
  #analysis-active .note 13px, panel h2 15px/700, label 13px muted contracts
  still match. Update = 5 files.
- SUPP (6 named ui.*): each ui parity test already asserts live web wiring that
  passes (the failure is the trailing Swift-tail match): web Start wait text +
  pending flag, waiting-for-first-assessment line, in-panel sending notes,
  analysis-active banner, observable-evidence note, clamp-to-1..60 wiring.
  Update = delete the Swift tail assertion in each of the 6 tests (js/app.js +
  index.html assertions stay). NOTE ui:872 additionally needs its web regex
  widened for the added optional `frameImage = null` third parameter of
  renderLatest — still UPDATE (one-regex widening, no behavior change; the
  waiting-line behavior it guards is intact, see OC1B-422).

UPDATE total: 36 files (30 whole-file + 6 ui tests' tails) + 2 G5 named tests
= 38 failure-units, matching PREP's 38.

## OC1B-416 CARVE-OUT option: what would be deleted, and what coverage is lost

CARVE-OUT = the test asserts SwiftUI behaviour with no counterpart anywhere.
17 failures on this tree (1 file-level + 16 named; PREP's 18th was the removed
logo test, see OC1B-418):

- G2 (1 file-level): native-header-limitations-corners — all 3 tests assert the
  deleted HeaderView limitations-box clip/overlay; no web counterpart exists.
  Deleting the file loses nothing the web suite covers.
- G3 (5 named): ignis-headings :90/:112/:145 (PanelHeading composition in
  deleted panels), medicus-headings :98, vigiles-headings :98. The web panel
  headings are covered by passing web tests; the composition assertions have
  no live target.
- G5 (1 named): camera-failure-announcement :67 (deleted panel failure texts +
  announcement call). Web failure paths are covered by passing web tests.
- G7 (4 named): input-ready :64/:79 (deleted choose still/video announcement),
  interval-change :71 (deleted banner didSet announcement), clear-assessing :82
  (Swift .disabled gates on deleted Assess buttons; the web guard is covered
  by the passing web test in the same file).
- SUPP (6 named): analysis-active-announcement :80, camera-start-pending :107,
  camera-state-live-region :46, camera-stop-pending :102 (deleted Swift
  banner/permission-state assertions), panel-assessing-line-clear :88
  (Swift sending lines in deleted panels; web sending lines covered by passing
  web tests), still-image-assess-button :84 (Swift .disabled gate on the
  deleted button; web guard covered by the passing web test in the same file).

Coverage lost per file: nothing the green suite does not already cover on
the web side — each entry above names the passing web test carrying the live
contract. The loss is SwiftUI-structure coverage, which has no live target
since the rewrite.

## OC1B-417 costs (measured, not estimated)

- Full node suite on this Mac: 3.4s wall (OC1B-native-baseline.txt). Group
  runs: G1 1s, G2/G3/G4/G6/G7 0s each, G5 1s, SUPP 0s — per-group re-verification
  after either option costs seconds, not minutes.
- UPDATE touches 36 test files + 2 named tests (test files only; no Swift
  source changes — the Swift is already rewritten). Mechanical: delete dead
  slices/tails, widen 1 web regex (ui:872).
- CARVE-OUT touches ~11 files (1 whole-file deletion + 16 named-test deletions
  across 10 files). Smaller diff, larger coverage-concept loss (SwiftUI
  structure assertions gone — but with no live target, nothing running loses
  a guard).
- R11-282 is outside both options: its fix is a one-line docs-index update
  (name OC1B-soak-wave2-tail.txt — and any other new *.txt — in
  os-build/layer1/BOOTLOG_INDEX.md), a docs edit this lane does not perform.

## OC1B-418 disagreements with docs/NATIVE_TEST_PREP.md

1. PREP entry 46 (logo CARVE-OUT, "console wires the loop...") no longer
   exists: Pax merge 5df78e5f removed the logo color section tree-wide (boss
   order; "baseline minus deleted color test, no new fails"). PREP's 56th
   entry is gone with it.
2. PREP predates the R11-282 failure (round-11 test landed after PREP's
   measurement): unclassified there; classified here as docs-index drift,
   neither UPDATE nor CARVE-OUT.
3. ui:872 (PREP entry 52, UPDATE): the web regex needs widening too
   (renderLatest gained `frameImage = null`), not just Swift-tail deletion.
   Verdict unchanged (UPDATE), scope one regex wider.
4. tests/native-camera-live-tracking.test.mjs is absent from the npm test
   script (verified: not in package.json) so PREP never classified it; it
   fails standalone in the same Swift-removal class (Label("CAMERA LIVE")
   gone from ContentView.swift). If it enters the suite, it is UPDATE-class
   (web .camera-indicator contract it checks is live in styles.css).

Adjusted totals for THIS tree: UPDATE 38 / CARVE-OUT 17 over the 55
native-mirror failures + 1 docs-index newcomer outside both options.

## OC1B-421 no-edit attestation

`git diff --stat -- tests/ native/` on this worktree is empty (no output;
exit 0): no test file and no Swift mirror modified in this lane. (Suite runs
append to os-build ledgers/runs dirs; those side-effects were reverted and
are not part of any commit.)

## OC1B-422 regression-candidate review: NONE

Method: for each of the 24 named failures, identified the exact failing
assertion line from the full-run output and confirmed the assertions before
it in the same test (all live web/index.html/js/app.js checks) passed —
every named failure dies on a removed-SwiftUI tail match or a stale
exact-text match. The 6 ui parity tests fail on Swift-tail matches after
their web assertions pass. The one web-side stale match (ui:872 line 875,
renderLatest signature) breaks on an added optional parameter, not a
behavior change; the guarded waiting-line wiring is intact in js/app.js.
Conclusion: no failing native test asserts behaviour the WKWebView app still
has. No live-app regression is hiding in the stale set. R11-282 is
docs-index drift, not app behaviour.
