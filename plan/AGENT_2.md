# AGENT 2 — prompt (branch: `agent-2`)

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

- Work on branch `agent-2`. Commit there. **Never** merge to `main` — Buffy
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

- `bus.html` — **the messaging app** (repo root)
- `surfaces.html` — the Imperium dispatch boards (repo root)
- `logo-studio.html` — the ASCII logo studio (repo root)
- `labs/**` — molecules (3D), music3d (3D), science-lab-review
- `design/**` — custos, officina, musica-notes, scientia-molecules, budget
- `site/index.html`, `js/**`, `vendor/**`, `styles.css`

## Not yours — do not edit, they will appear

| File / area | Owner |
|---|---|
| `os-build/face/meta-desktop.sh`, `metaos-update.sh`, `os-build/iso/payload-theme/icons/**` | agent-1 (it adds your pages to the dock and copies them to the image) |
| `aegis-page/**` | agent-3 |
| `os-build/face/about.html`, `os-build/face/session.sh`, `os-build/face/native/meta-app.py` | agent-4 |
| `agents/**`, `kernel/**`, `os-build/identity/**`, `aegis/*.mjs` | nobody — leave alone |

---

## Your task: every page must survive a dead backend and a small screen

These pages are the product. They are served by `face-site` on **port 18934**
out of `/opt/face-site`, and opened by `meta-app` — a GTK window with no address
bar and no tabs. Two things follow: the page must never show a URL, and it must
never show a blank window.

1. **`bus.html` — the messaging app.** It exists but is **not installed on the
   image**, so the app does not exist inside the OS today. Check that it runs
   with no data (empty bus), with data, and when its backend is down. If it
   fetches anything over the network other than `127.0.0.1`, remove that — this
   OS has no internet in the demo.

2. **`surfaces.html` — the Imperium boards.** Nine city world packs (NYPD,
   FDNY, EMS, MTA, DEP, DOE, hospital, Custos, Officina) with `pack.json` and
   `runs` data under `os/worlds/`. Open every board and make sure it renders.
   A board with a missing pack file must say which pack is missing, not go
   blank.

3. **Every page in your list must pass this bar:** with its backend stopped,
   it prints a visible line naming **what** failed and **which port**, in the
   same house style as `os-build/face/board.html` (which already does this).
   Never `|| true`, never an empty catch, never a silent failure.

4. **No page may leak a URL, a raw port as a "website", or a browser chrome
   element.** They are app windows, not tabs.

5. **3D pages — do not rewrite the scenes.** `labs/molecules` and
   `labs/music3d` use three.js vendored at `vendor/three.min.js` (offline).
   Molecules already has an honest no-WebGL guard around line 230 — keep it.
   Do not remove the guard to make a screenshot look good. Rendering proof is
   agent-4's job; your job is that the page never breaks and always explains
   itself.

6. **`labs/science-lab-review`** must be reachable and consistent with the
   science lab app.

7. Keep every page working at 1180×780 (the default `meta-app` window) — no
   horizontal scrollbars, no content cut off.

---

## Definition of done

- For each page: open it in a local server
  (`python3 -m http.server` from the directory `face-site` mirrors) and paste
  what it shows. Then stop the data source and paste what it shows instead.
- A short table: page → data it needs → behaviour when data is missing.
- One boot, open three of your pages through their dock tiles **if agent-1's
  tiles are merged already**; if not, open them with `meta-app --title X --url
  …` and say that is what you did.
- Write `os-build/lanes/AGENT_2_REPORT.md`: the table, the evidence, the
  screenshots, and anything broken outside your files.

Commit on `agent-2`. Do not merge.

---

# TASK QUEUE — 160 tasks, work top to bottom

Tick each in your report. If one cannot be done, write why and move on. Every
task is inside your pages only.

## A. Baseline (1-10)

1. Serve the tree the way `face-site` does (port 18934, plain `http.server`).
2. Open every page you own and record what it shows today.
3. Record every page that shows a blank body.
4. Record every page that logs a console error.
5. Record every page that makes a request outside `127.0.0.1`.
6. Record every page that shows a URL or a port number as text.
7. Screenshot each page once as the "before" set.
8. List which pages need a backend and which are standalone.
9. List which pages already have a visible failure line and which do not.
10. Note the file size of each page (they must stay small).

## B. `bus.html` — the messaging app (11-34)

11. Read `bus.html` end to end before changing it.
12. Confirm what data it fetches and from which port.
13. Confirm it makes no external request; remove any that exist.
14. Render with no messages: it must say the bus is empty, not go blank.
15. Render with one message.
16. Render with a long thread (100+ items) and check scrolling.
17. Render with unicode and emoji; nothing may be mojibake.
18. Render a message containing `<script>`; it must display as text.
19. Render a message containing `&`, `<`, `>`, quotes; must escape correctly.
20. Render a malformed record; the page must skip it and say so.
21. Use `os-build/round13/nuntius/dom/*.json` fixtures as your test data.
22. Confirm the empty-board fixture matches what the page shows.
23. Confirm the long-thread fixture does not freeze the page.
24. Confirm the unicode fixture renders byte-identically to its source.
25. Confirm the html-escaping fixture renders as text, not markup.
26. Add a visible failure line naming the port when data is unreachable.
27. Confirm the page never shows its own URL.
28. Confirm it fits 1180×780 with no horizontal scroll.
29. Confirm it works at 900×600 too.
30. Confirm keyboard focus reaches the message list.
31. Confirm contrast is readable on the dark theme.
32. Confirm timestamps render in a single consistent format.
33. Confirm long unbroken strings wrap instead of overflowing.
34. Commit and note the before/after behaviour of each case above.

## C. `surfaces.html` — nine Imperium boards (35-62)

35. List the nine world packs it reads.
36. Open NYPD and confirm it renders.
37. Open FDNY.
38. Open EMS.
39. Open MTA.
40. Open DEP.
41. Open DOE.
42. Open hospital.
43. Open Custos.
44. Open Officina.
45. For each of the nine: confirm the pack data actually loads, not a spinner.
46. For each: confirm the run/receipt panel shows real rows.
47. For each: confirm an empty pack says "no runs recorded".
48. For each: confirm a missing `pack.json` names the missing pack.
49. Confirm no board shows a 404 in the UI.
50. Confirm switching boards is instant, no full reload flicker.
51. Confirm the board list is keyboard navigable.
52. Confirm the selected board is visually obvious.
53. Confirm the page works with the backend stopped.
54. Confirm the page works with only one pack present.
55. Confirm the page never shows a localhost URL.
56. Confirm it fits 1180×780.
57. Confirm tables do not overflow their container.
58. Confirm numbers are formatted consistently.
59. Confirm timestamps are consistent across boards.
60. Confirm the page title changes per board, or stays stable on purpose — pick one and be consistent.
61. Confirm no board leaks file paths from the host machine.
62. Commit with the per-board evidence table.

## D. `logo-studio.html` (63-74)

63. Confirm the ASCII studio renders its canvas.
64. Confirm it works offline (no font or script CDN).
65. Confirm the default symbol matches the wallpaper's mark.
66. Confirm export/copy actions do something real, or are clearly disabled.
67. Confirm a long symbol does not break the layout.
68. Confirm the studio fits 1180×780.
69. Confirm no external font request.
70. Confirm the canvas redraws on window resize.
71. Confirm the studio has a visible failure line if a dependency is absent.
72. Confirm it never shows a URL.
73. Confirm the studio's colours match the brand tokens.
74. Commit.

## E. 3D pages (75-98)

75. Open `labs/molecules` and confirm the model draws or explains itself.
76. Keep the no-WebGL guard; do not remove it.
77. Confirm the guard's message is readable by a non-programmer.
78. Confirm the page does not hang while probing WebGL.
79. Confirm the molecule list loads (embedded data works offline).
80. Confirm a molecule with many atoms still rotates.
81. Confirm reset/zoom controls work.
82. Confirm the canvas resizes with the window.
83. Confirm the page is usable at 900×600.
84. Confirm the canvas is not blurry at 1180×780.
85. Open `labs/music3d` and repeat 75-84.
86. Confirm Music 3D does not duplicate the molecule viewer's code path wrongly.
87. Open `design/meta-musica-notes.html` and repeat 75-84.
88. Open `design/meta-scientia-molecules.html` and repeat 75-84.
89. Confirm `vendor/three.min.js` is present and referenced locally in each.
90. Confirm no page falls back to a CDN silently.
91. Confirm each 3D page has a static fallback image or message.
92. Confirm no 3D page blocks the whole page load on WebGL failure.
93. Confirm the 3D pages share one three.js copy, not four.
94. Confirm the shared copy is the same version everywhere.
95. Confirm each page still works if the shared copy is missing (message, not crash).
96. Record frame-rate observations without guessing numbers.
97. Confirm touch/mouse drag works for rotation.
98. Commit with per-page evidence.

## F. `design/` product pages (99-118)

99. Custos watch page: renders, real data or an honest empty state.
100. Custos: failure line when its runs are missing.
101. Officina blueprint page: renders.
102. Officina: failure line when its runs are missing.
103. Agent budget dashboard: renders its table.
104. Agent budget: numbers match the underlying data file.
105. Agent budget: handles an empty data set.
106. Confirm every `design/` page fits 1180×780.
107. Confirm every `design/` page has a consistent header.
108. Confirm every `design/` page uses the same font stack.
109. Confirm no `design/` page loads a remote asset.
110. Confirm no `design/` page shows a URL.
111. Confirm no `design/` page has a broken link to a missing sibling.
112. Fix any link that points at a file that does not exist.
113. Confirm each page states what it is in one line at the top.
114. Confirm each page has a visible empty state, not a blank panel.
115. Confirm each page's failure lines name a port.
116. Confirm each page's colours come from the brand tokens.
117. Confirm each page survives a hard reload.
118. Commit.

## G. `labs/science-lab-review` (119-126)

119. Confirm the page renders its cycle example.
120. Confirm the data it references exists.
121. Confirm missing data produces an explanation, not a blank.
122. Confirm the page is consistent with the Science tile's app.
123. Confirm it fits 1180×780.
124. Confirm no external assets.
125. Confirm it never shows a URL.
126. Commit.

## H. Cross-page rules (127-146)

127. Grep every page you own for `http://` and list every non-localhost hit.
128. Remove or vendor every external hit.
129. Grep for `cdn`, `googleapis`, `unpkg`, `jsdelivr` — must be zero.
130. Grep for `localhost` in visible text — must be zero.
131. Grep for empty `catch {}` blocks and replace with visible failures.
132. Grep for `|| true` around a fetch and remove it.
133. Confirm every page has one shared stylesheet or inline tokens, not five.
134. Confirm every page reads to a tired person in one glance.
135. Confirm every page states failure in the same visual place.
136. Confirm no page relies on a backend being fast.
137. Confirm no page breaks when the window is maximised.
138. Confirm no page breaks when the window is tiny.
139. Confirm no page plays audio without a user action.
140. Confirm no page auto-submits anything.
141. Confirm no page writes to disk.
142. Confirm no page needs a login.
143. Confirm every page works with the network cable unplugged.
144. Confirm every page's JS is under 200 KB unminified.
145. Confirm every page's HTML is under 100 KB.
146. List any page still failing a rule and say why.

## I. Proof and report (147-160)

147. Open three pages through `meta-app --title X --url …` in the booted OS.
148. Screenshot each; save under `os-build/captures/`.
149. Paste the empty/unreachable behaviour for each page you touched.
150. Build the page → data → missing-data table.
151. Write `os-build/lanes/AGENT_2_REPORT.md`.
152. Put a one-paragraph summary at the top.
153. List every task you could not complete, with one-sentence reasons.
154. List anything broken outside your files; do not fix it.
155. Confirm `git diff --name-only` shows only files you own.
156. Confirm you did not merge, rebase or push.
157. Confirm no `/Users/` path leaked into a page.
158. Confirm `main` is untouched by you.
159. Count completed vs skipped and state both numbers.
160. Stop. Do not start work outside this queue.
