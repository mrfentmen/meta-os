# NATIVE 55 DECISION PACK (Wave 3 task 59-66) — analysis only, no changes made

Tip: 2904e743 worktree. Suite: 1965 pass / 55 fail (ℹ lines).
Failing test names: 56 unique lines incl. the "failing tests:"
header; 55 real. Failing FILES: 31, all tests/native-*.

## 59. Reproduction on current main

`npm test` on this tree: 1965 pass, 55 fail. Same shape as the
mac-tasks runs (1947/55 at ab763ac0 — suite grew +18, fails
steady). No newcomer outside the known family: every failing
name is a web-vs-native parity assertion or a native size
snapshot.

## 60. Groups

- 31 size-snapshot files (tests/native-*-size.test.mjs): assert
  pixel/char sizes of native SwiftUI strings (labels, titles,
  notes, settings, still/video panels, statusbar, timeline).
- 13 native behavior parity (announcements, permission states,
  picker labels, sending lines, still/video ready words).
- 5 panel-title gating (PanelHeading per product).
- 2 camera parity (analysis banner, permission wait text).
- 2 latest-panel parity (observable-evidence note, wait-for-first).
- 1 config parity (sampling interval clamps 1-60 like Stepper).
- 1 panel chrome parity (in-panel sending line).

## 61. Update option (change expectations to match native)

The native side moved under Hana's accessibility wave
(VoiceOver announcements, banner wording, three-gate product
titles, panel chrome). For each of the 25 behavior/parity
tests: change the WEB expectation to the new native wording
(web code or test string, per case). For the 31 size files:
re-slice the expected sizes to the current native strings.
Files touched: ~36 test files (31 size + ~5 behavior hosts:
ui.test.mjs, camera.test.mjs, latest-*.test.mjs, native-*
harness). Suite time unchanged (~15 min). Risk: re-blesses
whatever native currently says, including any native bug.

## 62. Carve-out option (mark/skip)

Move the 31 tests/native-*-size.test.mjs out of the default
`npm test` file list (or add `.skip`), and skip the 25
parity subtests (or mark the 5 host files
ui/camera/latest/panel-titles/native-behavior as known-fail).
Coverage lost: all pixel-size regression cover of native
strings + all web-vs-native parity wording checks (the exact
checks that caught the accessibility drift). Files touched:
package.json test list (1 line) + ~5 skip annotations.
Suite time: -~2 min.

## 63. Cost

Update: ~36 files, 1 suite run to confirm (~15 min), keeps
all coverage. Carve-out: ~6 files, 1 suite run (~13 min),
loses the drift-catching coverage until someone re-adds it.

## 64. Pack status

Written, no test or mirror touched (task 65).
