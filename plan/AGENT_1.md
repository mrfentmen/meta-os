# AGENT 1 — prompt (branch: `agent-1`)

Paste this whole file into one opencode session. It is self-contained.

> **Ignore older prompt files.** `plan/AGENT_PROMPTS_R2.md`, `R3.md`, `R4.md`,
> `os-build/lanes/PROMPTS_4AGENTS_2026-11-03.md` and the `A_/B_/C_/D_*_REPORT.md`
> files are from earlier sessions. They are history, not homework. This file is
> the only brief.

---

## The mission (all four agents share this, word for word)

Meta OS is a Meta-branded desktop built on a Debian/Xubuntu base. The kernel,
theme, session, name and apps are ours; the base is not rewritten and we do not
claim it is.

The apps are built but **not all reachable**. Pages exist on disk that no tile
opens, one page (the messaging app) is not even installed on the image, and the
security engine has no screen at all. Your job is to make **every app we built
reachable, working and proven inside the booted OS**, and to remove the last of
Ubuntu's visible identity. Nothing mocked and nothing claimed that you have not
run.

Read `os-build/APP_INVENTORY.md` before you start. It is the map.

**Rules, all agents:**

- Work on branch `agent-1`. Commit there. **Never** merge to `main` — Buffy
  reviews and merges later.
- Commit only the files listed as yours. Everything else belongs to another
  agent working at the same time, right now, in this same checkout.
- No mock code, no stub handlers, no `TODO: implement`, no fake data to make a
  screenshot look right. If something cannot be done, write why and stop.
- Proven = you ran a command and pasted its output. Reading a file is not proof.
- Do not reboot the whole build repeatedly. One boot at the end to check your
  own work.
- Never commit an API key, token, or password.

---

## You own (and only you)

- `os-build/face/meta-desktop.sh` — the dock and the app entries
- `os-build/face/metaos-update.sh` — the site copy list
- `os-build/iso/payload-theme/icons/**` — icon generation

## Not yours — do not edit, they will appear

| File / area | Owner |
|---|---|
| `bus.html`, `surfaces.html`, `logo-studio.html`, `labs/**`, `design/**` | agent-2 |
| `aegis-page/**` (lands as `/opt/face-site/aegis/`) | agent-3 |
| `os-build/face/about.html`, `os-build/face/session.sh`, `os-build/face/native/meta-app.py` | agent-4 |
| `agents/**`, `kernel/**`, `os-build/identity/**`, `aegis/*.mjs` | nobody — leave alone |

---

## Your task: the dock must open everything

1. **Add these tiles** in `meta-desktop.sh`, each pointing at a page that
   exists (or that another agent is delivering at exactly this path — the
   contracts are fixed, so write them now):

   | Tile | Target |
   |---|---|
   | Boards | `http://127.0.0.1:18934/surfaces.html` |
   | Messages | `http://127.0.0.1:18934/bus.html` |
   | Logo Studio | `http://127.0.0.1:18934/logo-studio.html` |
   | Music 3D | `http://127.0.0.1:18934/labs/music3d/index.html` |
   | 3D Notes | `http://127.0.0.1:18934/design/meta-musica-notes.html` |
   | Agent Budget | `http://127.0.0.1:18934/design/agent-budget-dashboard.html` |
   | Aegis | `http://127.0.0.1:18934/aegis/index.html` |
   | About | `http://127.0.0.1:18900/about.html` |

2. **Generate the icons these need.** `add_app` falls back to a themed icon
   name, and a themed name the theme does not carry draws a **blank white
   tile** — that bug already happened once in this project. Use the existing
   generator (`os-build/iso/payload-theme/icons/generate-icons.py`) and match
   the existing size and style exactly. Needed: `boards`, `messages`, `logo`,
   `music3d`, `notes3d`, `budget`, `about`. The `aegis` icon already exists —
   use it, do not regenerate it.

3. **No two tiles may share one icon**, and every `Icon=` written must be a
   file that exists. Make `add_app` log a named warning when an icon is
   missing instead of silently drawing blank.

4. **`metaos-update.sh` must copy `bus.html` and `labs/science-lab-review`**
   onto the image. `bus.html` is the messaging app and it is currently not on
   the image at all. (`bus.html` itself is agent-2's file to fix — you only
   make sure the copy list includes it.)

5. **Careful with the two Imperium tiles.** Trio and Imperium are the same
   program by design; leave that alone. Do not "clean it up".

6. Keep it offline-safe: `add_app` skips a tile whose binary is missing rather
   than writing a launcher that opens nothing. Preserve that behaviour.

---

## Definition of done

- `sh -n os-build/face/meta-desktop.sh` clean.
- Running it against a throwaway home
  (`meta-desktop.sh --home /tmp/docktest --owner "$(id -u):$(id -g)"`) reports
  the new tile count, and every generated `.dockitem` points at a `.desktop`
  whose `Icon=` is an existing file. Paste the count and the check output.
- One boot, then a screenshot showing the dock with the new tiles and no blank
  squares. Save it under `os-build/captures/`.
- Write `os-build/lanes/AGENT_1_REPORT.md`: tile → page → icon table, what you
  generated, what you could not do and why, the offline output, the screenshot
  path, and anything you think is broken but outside your files.

Commit on `agent-1` with a message that says what changed and why. Do not merge.

---

# TASK QUEUE — 160 tasks, work top to bottom

Do them in order. Tick each one in your report. If a task cannot be done, write
why and move on — do not skip silently and do not fake the outcome. Every task
here is inside your files only.

## A. Baseline before you change anything (1-12)

1. Record the current tile count from `meta-desktop.sh`.
2. Record which of those tiles produced no `.dockitem` and why.
3. List every `Icon=` already written and check each file exists.
4. Screenshot the dock as it is today; name it `dock-before`.
5. Note which tiles are blank white squares in that screenshot.
6. Read `add_app` line by line and write down its skip rules.
7. List every app id already used, so you do not reuse one.
8. Check the dock item numbering (`00-`, `01-`…) for gaps.
9. Confirm plank reads `~/.config/plank/dock1/launchers` in this image.
10. Confirm the stale-item cleanup pass does not delete a valid tile.
11. Record the icon dimensions of three existing icons.
12. Record the icon style (flat, glow, stroke width) of three existing icons.

## B. New tiles, one at a time (13-44)

13. Add the Boards tile → `18934/surfaces.html`.
14. Verify Boards opens a window with that title.
15. Add the Messages tile → `18934/bus.html`.
16. Verify Messages fails *visibly* if agent-2 has not shipped `bus.html` yet.
17. Add the Logo Studio tile → `18934/logo-studio.html`.
18. Verify Logo Studio opens and loads the studio canvas.
19. Add the Music 3D tile → `18934/labs/music3d/index.html`.
20. Verify Music 3D opens without an address bar.
21. Add the 3D Notes tile → `18934/design/meta-musica-notes.html`.
22. Verify 3D Notes is a different page than Music 3D, not a duplicate.
23. Add the Agent Budget tile → `18934/design/agent-budget-dashboard.html`.
24. Verify Agent Budget renders its table.
25. Add the Aegis tile → `18934/aegis/index.html`.
26. Verify the Aegis tile does not show a blank window pre-agent-3.
27. Add the About tile → `18900/about.html`.
28. Verify About reads live values, not a hardcoded string.
29. Check no two new tiles point at the same URL.
30. Check no new tile duplicates an existing tile's purpose.
31. Confirm Trio and Imperium still both open the imperium program.
32. Confirm the Science tile still points at the molecule viewer.
33. Confirm the Calendar tile still points at `calendar.html`.
34. Check every `Exec=` line is quoted so a path with a space cannot split.
35. Check every `Exec=` binary resolves with `command -v` before writing.
36. Verify a tile with a missing binary is skipped, not broken.
37. Print one named warning per skipped tile into the login log.
38. Count final tiles and confirm the dock fits on screen at 1920 wide.
39. Confirm the dock does not overflow at 1366 wide either.
40. Check tile order reads sensibly (system apps first, then product apps).
41. Check no tile is pinned invisible or `NoDisplay=true` by mistake.
42. Re-run the whole block on a throwaway home and diff the output.
43. Confirm a re-run is idempotent: same files, same count, no duplicates.
44. Confirm a second run does not create `01-meta-…(2)` style duplicates.

## C. Icons (45-74)

45. Generate `boards.png` at the existing set's size.
46. Generate `messages.png`.
47. Generate `logo.png`.
48. Generate `music3d.png`.
49. Generate `notes3d.png`.
50. Generate `budget.png`.
51. Generate `about.png`.
52. Confirm `aegis.png` already exists and reuse it.
53. Check each new PNG opens and is not zero bytes.
54. Check each PNG has transparency like its neighbours.
55. Check each icon is legible on the dark dock background.
56. Check each icon is legible if the dock theme falls back to light.
57. Check the icons read as one family beside `files.png` and `notes.png`.
58. Confirm no icon is a letter-in-a-square that duplicates another.
59. Make Messages visually distinct from Agents.
60. Make Boards visibly the Imperium family colour.
61. Make Music 3D and 3D Notes distinguishable at 40 px.
62. Check every new icon at 40 px, the dock's real size.
63. Check every new icon at 64 px for the panel.
64. Fix any icon that becomes mush at 40 px.
65. Add all seven to the icon install list in the theme payload.
66. Verify they land in `/usr/share/icons/metaos/` on the image.
67. Verify `Icon=` writes an absolute path when the PNG exists.
68. Verify the themed-name fallback still works when it does not.
69. Add the missing-icon warning line to `add_app`.
70. Prove the warning fires: delete one icon, re-run, read the log.
71. Restore the icon and confirm the warning stops.
72. Confirm the icon generator is deterministic (same bytes twice).
73. Add a `--check-icons` mode that verifies every tile's icon exists.
74. Run `--check-icons` against the real dock and paste the result.

## D. Site copy list (75-92)

75. Add `bus.html` to the `metaos-update.sh` copy list.
76. Add `labs/science-lab-review` to the copy list.
77. Add `aegis` (the agent-3 directory) to the copy list.
78. Confirm the copy list tolerates a file that does not exist yet.
79. Confirm a missing file logs a line and keeps the previous copy.
80. Confirm the copy never deletes `/opt/face-site` wholesale.
81. Confirm `design/` and `labs/` still copy as directories.
82. Confirm `os/worlds` data still copies (boards need it).
83. Verify `bus.html` arrives at `/opt/face-site/bus.html`.
84. Verify `aegis/index.html` arrives at `/opt/face-site/aegis/index.html`.
85. Verify the wav Musica plays still arrives.
86. Add a `--check-site` mode listing every expected file and whether it landed.
87. Run `--check-site` on the real image and paste the output.
88. Confirm the copy is safe to re-run repeatedly.
89. Confirm no copy step needs root at login.
90. Confirm a copy failure does not abort the whole session script.
91. Log byte counts for each copied file, not just names.
92. Confirm no secret or key file is ever copied by that list.

## E. Failure behaviour (93-112)

93. Stop `face-site` and open each web tile: every one must explain itself.
94. Stop `face-notesd` and open Calendar: it must name port 18937.
95. Stop `metaosd` and open Agents: it must name port 18940.
96. Confirm no tile shows a blank white window in any of those cases.
97. Confirm no tile shows a URL, address bar, or tab strip.
98. Confirm a dead tile still closes with the window close button.
99. Confirm a dead tile does not freeze the dock.
100. Confirm clicking a dead tile twice does not stack ten windows.
101. Add a per-tile timeout so a hung page cannot block the dock.
102. Confirm the timeout message is human readable.
103. Confirm a missing icon never blocks a launch.
104. Confirm a missing page never blocks a launch.
105. Confirm a missing binary never writes a broken `.desktop`.
106. Confirm the stale-cleanup never removes a tile it just wrote.
107. Confirm the cleanup message names the tile it dropped.
108. Confirm a renamed app leaves no orphan `.dockitem`.
109. Confirm a duplicated `.desktop` id cannot appear twice.
110. Confirm the dock survives a logout and login cycle.
111. Confirm the dock survives a fresh home directory.
112. Confirm the dock survives an existing Xubuntu home (upgrade path).

## F. Proof and report (113-160)

113. Run the offline harness once with a clean home.
114. Paste the tile count from that run.
115. Paste every warning from that run.
116. Boot the OS once.
117. Screenshot the dock with all new tiles present.
118. Confirm zero blank squares in that screenshot.
119. Save it as `os-build/captures/dock-after-<date>.png`.
120. Click Boards from the dock and screenshot the window.
121. Click Messages from the dock and screenshot the window.
122. Click Logo Studio and screenshot it.
123. Click Music 3D and screenshot it.
124. Click Agent Budget and screenshot it.
125. Click About and screenshot it.
126. Record which of those opened and which did not.
127. Note honestly if a tile was opened by command instead of by clicking.
128. Confirm each window title matches the tile name.
129. Confirm each window has no address bar.
130. Confirm each window can be closed and reopened.
131. Confirm the dock re-orders nothing after opening five apps.
132. Confirm the dock still shows when a window is fullscreen.
133. Write `os-build/lanes/AGENT_1_REPORT.md`.
134. Put the tile → page → icon table in it.
135. Put the before/after tile counts in it.
136. Put the screenshot paths in it.
137. List every task above you could not complete.
138. Explain each failure in one sentence a non-programmer can read.
139. List anything broken you noticed outside your files (do not fix it).
140. Confirm you edited no file outside your ownership list (`git diff --name-only`).
141. Confirm `sh -n` passes on both scripts you touched.
142. Confirm the repo has no new binary over 2 MB from your work.
143. Confirm no absolute path from your laptop leaked into a script.
144. Confirm no `/Users/` path appears in any committed file.
145. Confirm the scripts run under `sh`, not only `bash`.
146. Commit on `agent-1` only.
147. Write a commit message stating what changed and why.
148. Confirm `git status` is clean except other agents' files.
149. Confirm you did not merge, rebase, or push.
150. Confirm `main` is untouched by you.
151. Re-read your report as if you were the boss, tired, at 2 a.m.
152. Fix anything in the report that assumes knowledge he does not have.
153. Add a one-paragraph summary at the very top of the report.
154. State the single most likely thing to break at the demo.
155. State what you would do next with two more hours.
156. Count the tasks you completed and put the number in the report.
157. Count the tasks you skipped and put the number in the report.
158. Confirm the numbers add up to 160.
159. Save the final report.
160. Stop. Do not start work outside this queue.
