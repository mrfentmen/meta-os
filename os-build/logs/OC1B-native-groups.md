# OC1B-405/406/414 — failure groups and sum check

Tree 94010c76, baseline 2071 tests / 2015 pass / 56 fail (OC1B-native-baseline.txt).

## OC1B-405 per-file counts

31 whole-file failures (file loads, Swift slice throws, 0 of its tests run):

G2 header/ignis-header (6): native-header-flame-chip-size, native-header-identity-size,
  native-header-limitations-corners, native-header-limitations-size,
  native-header-product-label-size, native-ignis-header
G3 ops-console body/status (6): native-ignis-ops-console-body, native-ignis-ops-console-status,
  native-medicus-ops-console-body, native-medicus-ops-console-status,
  native-vigiles-ops-console-body, native-vigiles-ops-console-status
G4 settings/statusbar/footer (6): native-footer-size, native-settings-categories-size,
  native-settings-label-size, native-settings-note-size, native-settings-title-size,
  native-statusbar-size
G5 camera/capture (3): native-camera-facing-note-size, native-camera-guidance-size,
  native-camera-state-size
G6 timeline/latest/still-image/video (5): native-latest-placeholder,
  native-still-image-intro-size, native-still-image-state-size,
  native-video-intro-size, native-video-state-size
G7 leftovers (5): native-analysis-active-size, native-ignis-latest-note-size,
  native-ignis-latest-title-size, native-input-panel-title-size,
  native-stepper-label-size
G1 ignis-assessment (0): all 21 files green — no failures in this group.

24 named native-mirror failures (single stale assertions; host files keep passing siblings):

G3 (5): native-ignis-ops-console-headings :90/:112/:145,
  native-medicus-ops-console-headings :98, native-vigiles-ops-console-headings :98
G5 (3): native-camera-facing :62/:73, native-camera-failure-announcement :67
G7 (4): native-input-ready-announcement :64/:79, native-interval-change-announcement :71,
  native-clear-assessing :82
supplementary non-native hosts (12): ui.test.mjs :851/:872/:938/:966/:1115/:1216 (6),
  analysis-active-announcement :80, camera-start-pending :107, camera-state-live-region :46,
  camera-stop-pending :102, panel-assessing-line-clear :88, still-image-assess-button :84
  (1 each; R11-282 excluded here, counted separately).

## OC1B-406 per-surface counts (removed SwiftUI surface each failure asserts)

All 55 native-mirror failures assert text in Swift sources removed by the
WKWebView rewrite (OpenCode d18932b6; ContentView.swift is now CommandWebView
+ PanelHeading only):
- Deleted ContentView.swift panels/labels/states (banner, camera permission
  texts, facing picker, Assess-button .disabled gates, sending lines,
  Stepper 1...60, rightColumn note): 31 file-level + 13 named = 44
- Deleted PanelHeading composition in deleted panels (Ignis/Medics/Vigiles
  headings + Latest/Timeline traits + Settings GroupBox): 5 named
- Deleted AssessmentView.swift console treatments (ops-console body/status): 6 file-level
- Non-surface newcomer (docs-index drift, no SwiftUI surface): R11-282 = 1

Total: 44 + 5 + 6 + 1 = 56. No failing test asserts a surface the WKWebView
app still ships (regression-candidate review in OC1B-native-pack.md: none).

## OC1B-414 sum check: group runs close to the baseline set exactly

Group runs (node --test per file list, OC1B-native-g{1..7}.txt + OC1B-native-supp.txt):

  G1 ignis-assessment-*: 83 tests, 83 pass, 0 fail
  G2 header + ignis-header: 6 tests, 0 pass, 6 fail (all 6 whole-file)
  G3 ops-console: 31 tests, 20 pass, 11 fail (6 whole-file + 5 named)
  G4 settings/statusbar/footer: 6 tests, 0 pass, 6 fail (all whole-file)
  G5 camera + capture: 20 tests, 13 pass, 7 fail — see note below
  G6 timeline/latest/still-image/video: 28 tests, 23 pass, 5 fail
  G7 logo/input/interval/request/sampler/stepper + 10 leftovers: 78 tests, 69 pass, 9 fail
  SUPP 8 non-native hosts: 150 tests, 137 pass, 13 fail (12 named native + R11-282)

Reconciliation to the 56 baseline failures:
  0 + 6 + 11 + 6 + (7-1) + 5 + 9 + 13 = 56.
The G5 minus-one: tests/native-camera-live-tracking.test.mjs fails standalone
(load-time blockAfter on the removed Label("CAMERA LIVE")) but is NOT in the
npm test script (verified absent from package.json), so it is not one of the
56; its standalone failure is the same Swift-removal class, noted for the
pack (UPDATE-class if it ever enters the suite). No failure lost,
none double-counted: every baseline failure appears in exactly one group run.
