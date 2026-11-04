# Agent T2 lane: application shells and dock wiring

Read this whole file before touching anything. Work on branch `agent-t2`.
Commit there. Do not merge. Do not push.

## Mission

Every dock tile must open a real window that belongs to this OS, and no tile
may open a blank frame, a browser tab, or another tile's page. Your lane owns
the shells that host the pages and the wiring that connects a tile to a page.
The pages themselves belong to T4; the three division apps and the desktop
scripts belong to Buffy.

## Owned paths (only these)

- `os-build/face/native/meta-app.py` and any new file under `os-build/face/native/`
- `os-build/iso/payload-theme/apps/` except `metaos-imperium.py`
- `os-build/face/*.html` except the trio pages (they live in `trio/`)
- `os-build/face/metaos-update.sh` (the copy list only, not the desktop build)
- `os-build/face/provision.sh` (units for the page servers only)
- `os-build/iso/payload-theme/icons/` (drawing code and generated PNGs)
- `os-build/lanes/T2_REPORT.md` (yours to write)

Do not edit `os-build/face/meta-desktop.sh`, `trio/`, `agents/`,
`agent-layer/`, `server/`, or `os-build/identity/`. Those have owners.

## Rules

- No QEMU. Prove with headless Chrome against a local server, and with
  `debugfs` reads of the image.
- Any page you claim works needs a screenshot at 1440x900 with the real
  backend running, or a written reason it cannot render here.
- Never invent a feature you did not build. If a page is static, say static.
- Use subagents. Split the sections across at least three, one section group
  each, then have a fourth read the diffs against this file. A subagent stays
  inside its section's files.

## Section A. Shell behaviour (1-20)

1. Read `meta-app.py` and list every failure path it can take. Paste the list.
2. Make a missing page produce a named error screen, with the path and the port.
3. Make a dead backend produce a named error screen, not a blank white window.
4. Add a reload action and a way to open the page's real URL for debugging.
5. Give every window a title bar that names the app, not the URL.
6. Set a sensible minimum size so no app opens at 200x120.
7. Remember window size per app, and say where it is stored.
8. Make the error screen match the desktop's colours and font.
9. Make sure the shell never shows an address bar, a tab strip, or a context menu with "Back".
10. Confirm the shell does not open external links in a system browser without saying so.
11. Add `--check` to the shell: it takes a URL and reports whether the server answers, without opening a window.
12. Use that in the dock's proof script so a dead tile is caught before boot.
13. Make the shell exit non-zero when the page never loads, so a launcher can see it.
14. Confirm the shell's process does not outlive its window.
15. Confirm closing the window kills the backend it started, and nothing else's.
16. Add a `--list-port` option that prints the port the shell would use.
17. Handle a page that takes more than ten seconds: show progress, not white.
18. Make the WebKit view disable media autoplay except where an app needs audio.
19. Give the view a dark default background so a slow paint is ink, not white.
20. Write down which of these you proved and which you could only read.

## Section B. Dock tiles and entries (21-46)

21. Dump the current tile list from the image's plank folder and paste it.
22. For each tile, name the `.desktop` file, the `Exec`, and the page it opens.
23. Find every tile whose page does not exist in the image. List them.
24. Find every tile whose page exists but its backend port is dead. List them.
25. For each broken tile, fix the entry or request the page from its owner.
26. Make every `Exec=` an absolute path. No bare names that depend on PATH.
27. Make every `Icon=` an absolute path to a PNG that exists.
28. Add `StartupWMClass` where the window manager needs it for grouping.
29. Add `Categories=` that match the app's real function.
30. Add `Comment=` lines that say what the app does, in plain words.
31. Remove any `Comment=` that names another distribution or another agent.
32. Add `Keywords=` so the launcher can find apps by what they do.
33. Make the two terminal tiles and the file manager use the Meta theme, and prove the theme file is read.
34. Confirm no tile launches a browser. Paste the `Exec` of any that still does.
35. Confirm no two tiles point at the same page. Paste the duplicate pairs you found and fixed.
36. Confirm the tile count and the `.desktop` count match. Paste both numbers.
37. Confirm the tile order in plank is the order the desktop script wrote.
38. Remove orphaned `.dockitem` files whose `.desktop` target is gone.
39. Add a check script that lists tiles with a missing program, a missing icon, or a missing page.
40. Run that check on the image and paste the result.
41. Make sure adding one tile needs one line, and document that line.
42. Confirm the dock does not start twice. Paste the process check you used.
43. Confirm the dock survives a session restart without duplicate entries.
44. Confirm the dock's icon size and spacing match the theme's tokens.
45. Check the running indicator draws for an app started from the tile.
46. Write the tile table into your report: id, name, program, page, icon, state.

## Section C. Page servers (47-66)

47. List every local server the desktop depends on, with its port and unit.
48. Prove which ports answer after a session start, from the image's unit files.
49. Make each server log its start line with the port it bound.
50. Make a port conflict fail loudly instead of silently serving another app.
51. Add a readiness check per server that the session can wait on.
52. Make the session wait for the page servers before starting the dock.
53. Cap each server's threads. A demo should not fork a hundred processes.
54. Make each server serve only its own directory. Prove a traversal attempt is refused.
55. Make each server set a no-store header so a changed page is not cached.
56. Confirm no server listens on a public interface. Paste the `ss` or `lsof` output.
57. Make each server handle a missing file with a named 404 page, not a traceback.
58. Make each server's Python not print a traceback to the console on a broken request.
59. Add a shared small module for the servers' common behaviour, if four copies exist.
60. Confirm the servers still work with no network device attached.
61. Confirm no server fetches anything off-localhost at request time.
62. Add a test that starts each server on a scratch port, requests three paths, and reports.
63. Run that test and paste the output.
64. Make the test clean up its processes. Prove no leftover listener.
65. Document, per server, what it serves and who calls it.
66. Record the memory each server uses at idle.

## Section D. App pages you own (67-96)

67. Open every page you own in headless Chrome and list HTTP status plus any console error.
68. Fix every page that throws on load.
69. Fix every page that requests an external host. Paste before and after.
70. Make every page name the port it could not reach, in the page, not the console.
71. Make every list show an empty state that says why it is empty.
72. Make every timestamp format match the desktop's clock.
73. Make every page survive a backend that returns malformed JSON. Paste the test.
74. Make every page survive a backend that returns 500.
75. Make every page survive a backend that hangs, with a timeout and a message.
76. Make every page work at 1366x768 without horizontal scroll.
77. Make every page work at 1920x1080 without stretched text.
78. Make every page use the theme's tokens instead of its own hex values, where the tokens exist.
79. Remove inline styles that duplicate the stylesheet.
80. Make keyboard focus visible on every interactive element you own.
81. Make every button reachable by Tab and activatable by Enter.
82. Check contrast on your pages at the body text size. Fix failures you find.
83. Make every page's title name the app, not the file.
84. Make every page set its favicon to a data URI so no request 404s.
85. Remove any page that duplicates another page's job. List what you removed.
86. Fix the ones with a dead control: a button that does nothing.
87. Make the search fields filter as you type and say how many results.
88. Make every detail panel closeable with Escape.
89. Make every page remember its last filter or view on reload, if it has one.
90. Confirm no page plays audio unprompted.
91. Confirm no page opens a popup.
92. Confirm no page uses a font the image does not ship.
93. Confirm no page depends on a CDN copy of a library. Vendor it or drop it.
94. Add a page-level selftest for the two most complex pages you own.
95. Run both selftests and paste the output.
96. Screenshot every page you own at 1440x900 and store the captures where the report links them.

## Section E. Icons (97-116)

97. List every icon name the dock references and whether a PNG exists.
98. Draw a missing icon in the same stroke weight as its neighbours.
99. Make each icon readable at 44 px. Shrink to 44 and look at it.
100. Keep one visual family: same plate, same corner radius, same stroke weight.
101. Redraw any icon that turns into a blob at dock size.
102. Add a 1x and a 2x render for every icon.
103. Add a contact sheet that shows every icon at 44 and 128 on ink and on paper.
104. Regenerate the contact sheet after each icon change.
105. Make the icon generator deterministic. Run it twice and diff.
106. Remove any icon file with no tile behind it, or name its owner.
107. Confirm no icon is a copy of a trademarked logo. Note provenance per icon.
108. Make thin strokes survive the plate's gradient, or drop the gradient under the glyph.
109. Check every icon on the darkest and the lightest wallpaper.
110. Make the four division tiles' icons distinct at a glance.
111. Keep the shapes distinguishable in greyscale. Paste the greyscale sheet.
112. Add a check that fails when a dock `Icon=` has no file.
113. Run it against the image and paste the output.
114. Document in `icons/SOURCES.md` how each shape was drawn, no external art.
115. Confirm the generated PNGs are committed, not built on the user's machine.
116. Confirmed the accent variants still regenerate after your changes.

## Section F. Native app shells (117-136)

117. List every app in `payload-theme/apps` and what it renders.
118. Make each one show a window title that matches its dock name.
119. Make each one usable with the keyboard alone.
120. Make each one quit with Ctrl+Q and close with Escape where that makes sense.
121. Make each one start in under two seconds or say why it cannot.
122. Make each one fail with a readable message when GTK is missing.
123. Make each one work under a plain X session with no compositor.
124. Confirm none of them opens a terminal window.
125. Confirm none of them writes outside the user's config directory.
126. Confirm none of them needs root.
127. Give each a `--check` mode that prints its dependencies and their state.
128. Run every `--check` and paste the output.
129. Remove dead code paths that reference removed binaries.
130. Make the control gallery show every widget the theme styles. List any missing.
131. Make the monitor app read real values and label the units.
132. Make the welcome app's text true for this image.
133. Confirm no app's text promises a feature the image lacks.
134. Add one screenshot per native app to your captures folder.
135. Document how to add a native app in one paragraph.
136. Note every app that should become native but is still a page.

## Section G. Proof and reporting (137-150)

137. Write `os-build/lanes/T2_REPORT.md` with one section per section letter above.
138. Every claim gets a command and its output.
139. Paste the tile table with a state column: proven, broken, blocked.
140. Paste the console-error sweep for every page you own.
141. Paste the port test results per server.
142. List every file you changed with `git diff --stat`.
143. Confirm no file outside your owned paths appears there.
144. Confirm no QEMU process is running. Paste the check.
145. Name the three tiles most likely to fail on stage, and why.
146. Fix the two cheapest of those three, and say what the third needs.
147. Confirm your commits are on `agent-t2` only. Paste the branch and the log.
148. Confirm `main` is untouched by you.
149. Write the one-paragraph answer to "does every tile open its own real window?"
150. End with the next three tasks you would do with another session.
