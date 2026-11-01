# Native-test prep — WKWebView-red 56: UPDATE vs CARVE-OUT

Prep branch only, NO merge. This tees up the boss's update-vs-carve-out
call as one decision. Baseline measured 2026-11-01 on origin/main
(0da81e8) in this sandbox: **1875 tests, 1819 pass, 56 fail**.
All 56 fails are the pre-existing WKWebView-red native tests: they
assert SwiftUI source in `native/Sources/MetaTrio/Views/ContentView.swift`
(and siblings) that the OpenCode d18932b6 rewrite replaced with a
WKWebView shell (`CommandWebView` + the `PanelHeading` helper only).

## The rule

- **UPDATE** — the test's intent still exists in current sources
  (almost always the web UI: `index.html`, `js/`, `styles.css`).
  Rewrite the assertion to match current sources: strip the dead Swift
  check, keep the live web check.
- **CARVE-OUT** — the test asserts SwiftUI behaviour that no longer
  exists anywhere. Delete the test.

Web-contract spot checks done for this classification: `.note` is
13px muted, `.panel h2` is 15px/700, `.product-badge` is
13px/700/0.04em, `.product-department` 13px muted, `.product-tagline`
14px, `.footer` 13px muted, both camera-facing labels live in
`index.html`, and the facing-preference note lives on in the web
"About camera facing" note. Stripped files must still be run to confirm
green — this doc classifies, it does not rewrite.

## Totals

- **UPDATE: 38** (30 file-level + 8 named)
- **CARVE-OUT: 18** (1 file-level + 17 named)

## File-level entries (31)

These fail as whole files: a top-level Swift slice/assert throws at
load, so the web-contract test inside never runs either.

| # | File | Verdict | One-line reason |
|---|------|---------|-----------------|
| 1 | tests/native-analysis-active-size.test.mjs | UPDATE | Strip the Swift banner tests; the web #analysis-active .note 13px contract still matches. |
| 2 | tests/native-camera-facing-note-size.test.mjs | UPDATE | Strip the Swift note-font tests; the web .note 13px contract still matches. |
| 3 | tests/native-camera-guidance-size.test.mjs | UPDATE | Strip the Swift note-font tests; the web .note 13px contract still matches. |
| 4 | tests/native-camera-state-size.test.mjs | UPDATE | Strip the Swift state-line tests; the web camera-state .note contract still matches. |
| 5 | tests/native-footer-size.test.mjs | UPDATE | Strip the Swift disclaimer-font tests; web .footer 13px muted + disclaimer words still match. |
| 6 | tests/native-header-flame-chip-size.test.mjs | UPDATE | Strip the Swift chip tests; web .product-badge 13px/700/0.04em still matches. |
| 7 | tests/native-header-identity-size.test.mjs | UPDATE | Strip the Swift department/tagline tests; web .product-department 13px + .product-tagline 14px still match. |
| 8 | tests/native-header-limitations-corners.test.mjs | CARVE-OUT | All 3 tests assert the deleted HeaderView limitations-box clip/overlay; no web counterpart exists. |
| 9 | tests/native-header-limitations-size.test.mjs | UPDATE | Strip the Swift notice-font tests; the web limitations .note contract still matches. |
| 10 | tests/native-header-product-label-size.test.mjs | UPDATE | Strip the Swift picker tests; the web label 13px muted still matches. |
| 11 | tests/native-ignis-header.test.mjs | UPDATE | Strip the Swift flame-chip/limitations tests; the web Ignis red-gradient test still matches. |
| 12 | tests/native-ignis-latest-note-size.test.mjs | UPDATE | Strip the Swift note-font tests; the web .note contract still matches. |
| 13 | tests/native-ignis-latest-title.test.mjs | UPDATE | Strip the Swift PanelHeading tests; web .panel h2 15px/700 still matches. |
| 14 | tests/native-ignis-ops-console-body.test.mjs | UPDATE | Strip the Swift AssessmentView tests; the web OPS-CONSOLE-3 subhead + mono-block frame still match. |
| 15 | tests/native-ignis-ops-console-status.test.mjs | UPDATE | Strip the Swift state-line tests; the web OPS-CONSOLE-3 status rule still matches. |
| 16 | tests/native-input-panel-title-size.test.mjs | UPDATE | Strip the Swift PanelHeading tests; web .panel h2 15px/700 still matches. |
| 17 | tests/native-latest-placeholder.test.mjs | UPDATE | Strip the Swift placeholder-font tests; web #latest-assessment mono-block 13px still matches. |
| 18 | tests/native-medicus-ops-console-body.test.mjs | UPDATE | Strip the Swift tests; the web Medicus subhead + mono-block frame still match. |
| 19 | tests/native-medicus-ops-console-status.test.mjs | UPDATE | Strip the Swift state-line tests; the web Medicus status rule still matches. |
| 20 | tests/native-settings-categories-size.test.mjs | UPDATE | Strip the Swift tests; the web .note contract still matches. |
| 21 | tests/native-settings-label-size.test.mjs | UPDATE | Strip the Swift label tests; the web labels 13px muted still match. |
| 22 | tests/native-settings-note-size.test.mjs | UPDATE | Strip the Swift note tests; the web .note contract still matches. |
| 23 | tests/native-settings-title-size.test.mjs | UPDATE | Strip the Swift PanelHeading/GroupBox tests; web panel h2 15px bold still matches. |
| 24 | tests/native-statusbar-size.test.mjs | UPDATE | Strip the Swift status-bar tests; web status 13px / note 13px / mono 12.5px still match. |
| 25 | tests/native-stepper-label-size.test.mjs | UPDATE | Strip the Swift Stepper label tests; the web label rule 13px muted still matches. |
| 26 | tests/native-still-image-intro-size.test.mjs | UPDATE | Strip the Swift intro-font tests; web .note contract + intro words still match. |
| 27 | tests/native-still-image-state-size.test.mjs | UPDATE | Strip the Swift state-line tests; the web state .note contract still matches. |
| 28 | tests/native-video-intro-size.test.mjs | UPDATE | Strip the Swift intro-font tests; web .note contract + intro words still match. |
| 29 | tests/native-video-state-size.test.mjs | UPDATE | Strip the Swift state-line tests; the web state .note contract still matches. |
| 30 | tests/native-vigiles-ops-console-body.test.mjs | UPDATE | Strip the Swift tests; the web OPS-CONSOLE-6 subhead + mono-block frame still match. |
| 31 | tests/native-vigiles-ops-console-status.test.mjs | UPDATE | Strip the Swift state-line tests; the web OPS-CONSOLE-6 status rule still matches. |

## Named tests (25)

| # | Test (file:line) | Verdict | One-line reason |
|---|------------------|---------|-----------------|
| 32 | native: startAnalysis announces the banner's own words (analysis-active-announcement:80) | CARVE-OUT | Asserts the deleted Swift banner label + announcement call. |
| 33 | native: Start stays disabled while permission is requested (camera-start-pending:107) | CARVE-OUT | Asserts Swift .disabled on the deleted Start control. |
| 34 | native: camera state still rides the preview accessibilityValue (camera-state-live-region:46) | CARVE-OUT | Asserts Swift preview accessibilityValue, deleted with the camera panel. |
| 35 | native: Stop stays enabled while permission is requested (camera-stop-pending:102) | CARVE-OUT | Asserts Swift .disabled on the deleted Stop control. |
| 36 | native: picker offers both facings with the web picker's labels (native-camera-facing:62) | UPDATE | Drop the Swift service/Picker checks; the web page still carries both facing labels word for word. |
| 37 | native: picker says plainly that a facing is a preference (native-camera-facing:73) | UPDATE | Re-point at the web "About camera facing" note, which still says a facing is a preference, not a requirement. |
| 38 | native: the announced words are exactly the state text the panel shows (native-camera-failure-announcement:67) | CARVE-OUT | Asserts deleted Swift panel failure texts + announcement call. |
| 39 | native: the Assess buttons still gate on the flag (native-clear-assessing:82) | CARVE-OUT | Asserts Swift .disabled gates on the deleted Assess buttons (the web parity test in the same file still passes). |
| 40 | native panel titles: all five use PanelHeading gated on Ignis (native-ignis-ops-console-headings:90) | CARVE-OUT | Asserts PanelHeading composition in deleted panels. |
| 41 | native panel titles: Latest and Timeline keep their header traits (native-ignis-ops-console-headings:112) | CARVE-OUT | Same, header traits on deleted panels. |
| 42 | native panel titles: Settings stays a GroupBox label, camera panel untouched (native-ignis-ops-console-headings:145) | CARVE-OUT | Same, GroupBox label on the deleted Settings panel. |
| 43 | native: a successfully chosen still image announces the panel's own ready words (native-input-ready-announcement:64) | CARVE-OUT | Asserts deleted Swift chooseStillImage announcement + panel ready text. |
| 44 | native: a successfully chosen video announces the panel's own ready words (native-input-ready-announcement:79) | CARVE-OUT | Same for the deleted video path. |
| 45 | native: a mid-run interval change announces the banner's own words (native-interval-change-announcement:71) | CARVE-OUT | Asserts deleted Swift banner label + didSet announcement. |
| 46 | logo: console wires the loop behind the panels and the panel into the left column (native-logo-color:100) | CARVE-OUT | Asserts LogoLoopView/LogoColorPanel composition in deleted ContentView. |
| 47 | native panel titles: all five use PanelHeading gated on Medicus (native-medicus-ops-console-headings:98) | CARVE-OUT | Asserts PanelHeading composition in deleted panels. |
| 48 | native panel titles: all five use PanelHeading gated on Vigiles (native-vigiles-ops-console-headings:98) | CARVE-OUT | Same as Medicus, Vigiles panels. |
| 49 | native: each panel shows its sending line while its assessing flag is true (panel-assessing-line-clear:88) | CARVE-OUT | Asserts Swift sending lines in deleted panels (web sending lines are covered by passing web tests). |
| 50 | native: the still-image button is already gated on nil image or assessing (still-image-assess-button:84) | CARVE-OUT | Asserts Swift .disabled gate on the deleted button (the web guard is covered by the passing web test in the same file). |
| 51 | camera: web Start says it is waiting for camera permission, matching the native camera (ui:842) | UPDATE | Drop the Swift tail assertion; all web Start/pending assertions target current js/app.js. |
| 52 | latest: web panel waits for the first assessment, matching the native panel (ui:863) | UPDATE | Drop the Swift tail assertion; all web waiting-line assertions target current js/app.js. |
| 53 | panels: still-image and video panels show an in-panel sending note while assessing, matching the native panels (ui:929) | UPDATE | Drop the Swift tail assertion; all web sending-note assertions target current index.html + js/app.js. |
| 54 | camera: web shows an analysis-active banner while sampling, matching the native camera panel (ui:957) | UPDATE | Drop the Swift tail assertion; all web banner assertions target current index.html + js/app.js. |
| 55 | latest: native panel carries the observable-evidence note, matching the web panel (ui:1106) | UPDATE | Drop the Swift rightColumn assertion; the web note assertion targets current index.html. |
| 56 | config: web sampling interval clamps to 1–60 like the native Stepper, instead of silently falling back (ui:1207) | UPDATE | Drop the Swift Stepper assertion; all web clamp assertions target current js/app.js. |

## Boundaries kept

No merge to main. No face-identification work. No bus-tools paths
in any push. No mock work presented as done. Milo gates this branch
on arrival; the update-vs-carve-out decision itself stays the boss's.
