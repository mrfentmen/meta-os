# Agent R2-T2 lane: native windows, controls, dock behavior

Paste this whole file to the agent. Work on branch `agent-r2-t2` in worktree
`/tmp/agent-r2-t2`. Commit there. Do not merge. Do not push. Do not switch any
other worktree's branch.

## Mission

The OS still behaves like a browser in a frame: apps open as web views with no
window controls of their own, and the only way to close one is the tab strip.
Round 2 gives every app real close, minimise, and maximise controls and makes
the desktop shell behave like a desktop: one window per app, focus, tiling,
alt-tab, notifications, and a dock that tells the truth.

Buffy owns page typography and the trio pages. You own the native shell, the
window chrome, the desktop script, the app entries, and the icons. Do not edit
`trio/`, `design/`, `labs/`, `aegis-page/`, or page CSS.

## Owned paths (only these)

- `os-build/face/native/` (all of it, including `meta-app.py`)
- `os-build/face/meta-desktop.sh`
- `os-build/iso/payload-theme/apps/` except `metaos-imperium.py`
- `os-build/iso/payload-theme/icons/` (generator and generated PNGs)
- `os-build/face/meta-app.desktop` and any new `.desktop` under `os-build/face/`
- `os-build/lanes/R2_T2_REPORT.md` (yours to write)

Request changes to `os-build/face/provision.sh`, `metaos-update.sh`, the panel,
the dock theme, and the session file in your report; T1 owns those paths.

## Rules

- **No QEMU.** Test with the stub backends, headless X if available, static GUI
  traces, and unit tests. Say plainly what only a boot can prove.
- No `sudo`, no `mount`. Do not kill another lane's server.
- Call subagents. At least four, one per section, plus one reviewer.
- Every claim needs a command and pasted output.
- If a control cannot work without a display server here, write the exact test
  a booted guest must run and leave it in the report.

## Section A. Window controls (1-22)

1. Inventory every place a window is created today and name the widget or process.
2. Add visible close, minimise, and maximise controls to the native shell, top right.
3. Make close terminate only that app's window, never the whole session.
4. Make minimise hide the window and keep the process alive; prove it returns on restore.
5. Make maximise toggle between the work area and the previous geometry.
6. Give the close button the hover, active, and disabled states from the theme.
7. Add keyboard shortcuts: Alt+F4 close, Alt+F9 minimise, Alt+F10 maximise.
8. Make Escape close transient dialogs only, never the app.
9. Make the title bar show the app's real title, not the URL or "Epiphany".
10. Add a drag region that moves the window; prove it does not select text.
11. Add edge and corner resize handles with a minimum size per app.
12. Prevent resizing below the documented minimum; prove the clamp.
13. Persist window geometry per app across relaunch.
14. Restore geometry only when the saved rectangle is still on screen.
15. Add double-click on the title bar to maximise and restore.
16. Add a right-click title-bar menu with Close, Minimise, Maximise, Always on top.
17. Make "always on top" real and visible in the title bar.
18. Make the focused window visually distinct from unfocused ones.
19. Make the title bar keyboard reachable with Tab and show a focus ring.
20. Ensure the controls are not covered by the page's own header; prove a 1440x900 capture.
21. Add a test that every native window exposes exactly one close, one minimise, and one maximise control.
22. Remove any code path that closes an app by closing a browser tab.

## Section B. The app shell (23-44)

23. Make `meta-app.py` the only browser-backed host; list every exec that bypasses it.
24. Add a named error screen for a dead backend that includes host, port, and the failing URL.
25. Add a Retry button that re-requests only the failed page.
26. Add a Copy URL button that copies the page's real URL.
27. Add a per-app title and icon passed on the command line; prove the window properties.
28. Enforce a 640x440 minimum with a clear message when the screen is smaller.
29. Persist geometry under one config file per user.
30. Add `--check` modes: binary present, port reachable, page reachable, exit codes documented.
31. Make a missing port exit with a named code, not a traceback.
32. Disable autoplay audio by default; add a visible unmute control where the page needs it.
33. Set the window background to the theme ink so a slow page never flashes white.
34. Disable the browser's download shelf; route downloads to `~/Downloads` and name the path.
35. Disable print-to-PDF from the app shell unless the app asks for it.
36. Remove the URL bar, tab strip, and browser chrome from every hosted app.
37. Make Ctrl+Q quit the app and Ctrl+W close the window; prove both.
38. Add zoom in/out/reset with the app keybindings, clamped to 80-125%.
39. Add find-in-page with Ctrl+F and Esc to close it.
40. Disable developer tools in the shipped build; prove the flag.
41. Add a loading state that appears only after 300 ms, so fast pages do not flash.
42. Add a crash screen that names the process and offers Reload.
43. Make one app instance per app id; a second launch focuses the existing window.
44. Make the shell start with no network and still open a local page.

## Section C. Dock and entries (45-64)

45. List every tile in the dock with its Exec, Icon, and target.
46. Prove every Exec resolves on a staged guest; paste the failures.
47. Give each tile an absolute Exec and Icon path; no bare binary names.
48. Add a `StartupWMClass` per app and prove it matches the shell's window class.
49. Make the dock group windows by app id, not by page title.
50. Add a running indicator that clears when the last window closes.
51. Add a hover label with the app name and a one-line description.
52. Add a right-click menu with New Window, Close, and Pin/Unpin.
53. Make pin/unpin persist and survive a dock restart.
54. Make reordering persist by app id, not index.
55. Remove duplicate tiles for the same app; prove the unique id count.
56. Give every tile a real icon; fail the build when an icon is missing.
57. Draw a fallback icon with the app's initial when the PNG is absent, and name the missing path in the log.
58. Make the dock not autohide during the demo; prove the setting.
59. Make the dock appear exactly once per session; prove the autostart list.
60. Make launcher failures visible: a notification naming the app and the reason.
61. Remove dead tiles whose target no longer exists; list each removal.
62. Make the Imperium and Trio tiles open their own pages, never each other's.
63. Make Science and Musica tiles open the current app pages, not old copies.
64. Add a tile for Nuntius that opens the local bus UI, not a relay setup page.

## Section D. Desktop behavior (65-84)

65. Make Alt+Tab cycle windows with a visible switcher.
66. Make clicking the desktop focus it and clear the window focus.
67. Add two workspaces and a keyboard switch; prove the config.
68. Make window tiling snap left/right with Super+Left/Right.
69. Add a keyboard shortcut list in Settings that matches the real bindings.
70. Make notifications appear top-right, stack, and expire; prove the daemon config.
71. Add a notification when a job finishes, from the agent API.
72. Make the clipboard persist between apps for text only.
73. Add a screenshot tool with full screen and window modes saving to `~/Pictures`.
74. Add a lock-screen action and make unlock return to the same session.
75. Add logout, restart, and shutdown dialogs with Meta wording.
76. Make the logout dialog the only way to end the session from the desktop.
77. Add a clock with seconds and the date, matching the theme font.
78. Add a volume control with a visible mute state.
79. Add a battery/CPU widget that reads real values or says unavailable.
80. Make the panel not cover fullscreen apps; prove the setting.
81. Make the desktop usable at 1366x768 without overlap or clipping.
82. Make the desktop usable at 1920x1080 with the approved spacing.
83. Remove every Ubuntu or Xubuntu label from the desktop menus.
84. Make the desktop start with no terminal window and no browser window open.

## Section E. Proof and handoff (85-100)

85. Write a headless test for the title-bar controls using the stub host.
86. Write a test that a second launch focuses instead of duplicating.
87. Write a test that a dead port shows the named error and Retry works.
88. Capture the title bar at 1440x900 with the three controls visible.
89. Capture a minimised and restored window sequence.
90. Capture the desktop at 1366x768 and 1920x1080.
91. Run every existing desktop test and paste the failures before and after.
92. Run `sh -n` on every shell script you touched.
93. Run `py_compile` on every Python file you touched.
94. Confirm no QEMU process and no stray server was left running.
95. List every file you touched outside owned paths, with the request.
96. Name the controls that still need a booted guest to prove.
97. Write the exact guest commands for the booted proof, ready to paste.
98. Confirm the icons are deterministic by regenerating and diffing.
99. Confirm the shell leaves no temp file in the repo.
100. Write `os-build/lanes/R2_T2_REPORT.md` with task ticks, proofs, skips, and next three steps.
