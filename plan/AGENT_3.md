# AGENT 3 — prompt (branch: `agent-3`)

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

- Work on branch `agent-3`. Commit there. **Never** merge to `main` — Buffy
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

- `aegis-page/**` — a new directory. It lands on the image at
  **`/opt/face-site/aegis/`**, so the app is
  `http://127.0.0.1:18934/aegis/index.html`. **That path is a fixed contract** —
  agent-1 is writing the dock tile against it right now.
- `os-build/aegis/**` — only to ADD a receipt/report file if your work produces
  one. Never rewrite existing receipts.

## Not yours — do not edit, they will appear

| File / area | Owner |
|---|---|
| `os-build/face/meta-desktop.sh`, `metaos-update.sh`, icons | agent-1 (it will add your tile and copy your page) |
| `bus.html`, `surfaces.html`, `logo-studio.html`, `labs/**`, `design/**` | agent-2 |
| `os-build/face/about.html`, `session.sh`, `native/meta-app.py` | agent-4 |
| `aegis/*.mjs` (the engine itself) | nobody — read it, do not change it |
| `agents/**`, `kernel/**`, `os-build/identity/**` | nobody |

---

## Your task: Aegis gets a face

Aegis is a real security engine with **no user interface at all**. A judge
asking "show me the security app" currently gets nothing. That is the single
biggest missing surface in this OS, and it is the easiest to fix, because the
data is already JSON on disk.

**Read first:** `aegis/*.mjs` (what it actually computes), `os-build/AEGIS_SPEC.md`,
and the real data: `os-build/aegis/runs.jsonl`, `findings.jsonl`,
`findings-ledger.jsonl`, `KEV.json`, `LIVENESS.json`, `HISTORY_SCAN.json`,
`DRILL.json`. Copy the house style from `os-build/face/board.html` and
`surfaces.html`.

**Do:**

1. Build `aegis-page/index.html`: a **read-only** dashboard over data that
   already exists. Panels, in this order of value:
   - findings by severity, newest first, with the file that produced them
   - KEV matches (known exploited vulnerabilities) — count and list
   - liveness probe results
   - the last N runs: timestamp, what ran, pass/fail
2. **Never invent a number.** If a JSONL is missing or empty, the panel says
   exactly that — e.g. "no findings recorded — the engine has not run". An empty
   panel that says why is worth more than a plausible fake.
3. Every fetch must have a visible failure line naming the port, like the other
   pages. A blank window is a bug.
4. Ship the data with the page. `face-site` is a plain `http.server` on 18934,
   so the JSONL must be copied next to the page (or the page must read a copy
   you place at `aegis-page/data/`). Say which you chose and why in the report.
5. Write a `--selftest` (small python or node script in `aegis-page/`) that
   proves the page's data path without a browser: it parses every file the page
   reads and fails loudly on a malformed line.
6. If the engine has never actually produced findings on this machine, **say so
   in the report**. A security dashboard over an empty ledger is honest; a
   security dashboard with invented CVEs is fraud and a judge will catch it.

---

## Definition of done

- `aegis-page/index.html` renders from real repo data under
  `python3 -m http.server`; paste the rendered text or a screenshot.
- The "engine has not run / empty ledger" path demonstrated by pointing the page
  at an empty directory.
- `aegis-page/selftest` passes, and fails when you hand it one malformed JSONL
  line. Paste both.
- Write `os-build/lanes/AGENT_3_REPORT.md`: panel → data file → what it shows
  when the file is missing; what is real, what is empty, what a judge would
  still find missing.

Commit on `agent-3`. Do not merge.

---

# TASK QUEUE — 160 tasks, work top to bottom

Tick each in your report. If one cannot be done, write why and move on. Never
invent a finding, a CVE, or a count to fill a panel.

## A. Understand the data before building (1-20)

1. List every JSON and JSONL file under `os-build/aegis/` with sizes.
2. For each, print its top-level shape (keys or record fields).
3. Record how many records each file actually holds today.
4. Note which files are empty and which are non-empty.
5. Read `findings.jsonl` and write down the field names.
6. Read `findings-ledger.jsonl` and note how it differs from `findings.jsonl`.
7. Read `runs.jsonl` and note the fields per run.
8. Read `KEV.json` and note its structure.
9. Read `LIVENESS.json` and note what was probed and when.
10. Read `HISTORY_SCAN.json` and note its scope.
11. Read `DRILL.json` and note what it drills.
12. Read `os-build/AEGIS_SPEC.md` and list the panels it promises.
13. Read `aegis/findings.mjs` and note the severity vocabulary.
14. Read `aegis/kev.mjs` and note how a match is decided.
15. Read `aegis/liveness.mjs` and note what a probe result means.
16. Read `aegis/opsec.mjs` and note whether it produces findings or advice.
17. List which fields are timestamps and their timezone.
18. List which fields are free text and therefore need escaping.
19. Identify the one field a judge would most want to sort by.
20. Write this inventory into your report before writing any HTML.

## B. The page skeleton (21-40)

21. Create `aegis-page/index.html` with the shared house style.
22. Create `aegis-page/data/` and copy exactly the files the page reads.
23. Document in the report why the data is copied, not fetched from disk.
24. Add a header naming the app and the data snapshot time.
25. Add a global "data source" line listing each file and its record count.
26. Add the findings panel shell.
27. Add the KEV panel shell.
28. Add the liveness panel shell.
29. Add the runs panel shell.
30. Add an explicit "nothing recorded" component used by every panel.
31. Add one place where failure text appears, used by all fetches.
32. Confirm the page renders with all four panels empty without errors.
33. Confirm the page renders when `data/` is entirely missing.
34. Confirm the page never shows a file path from the host.
35. Confirm the page never shows a raw URL.
36. Confirm the page fits 1180×780 with all panels.
37. Confirm it scrolls rather than clips when panels are long.
38. Confirm it works at 900×600.
39. Confirm the header says what this app is in one readable line.
40. Commit the skeleton with a screenshot of the empty state.

## C. Findings panel (41-66)

41. Render findings newest first.
42. Render severity as a visible label, not a colour alone.
43. Group by severity with counts at the top.
44. Show total count and per-severity counts.
45. Link each row to the file and line that produced it.
46. Show the timestamp in one consistent format, marked UTC.
47. Truncate long free text with a way to see the whole value.
48. Escape every free-text field; prove it with a `<script>` value.
49. Handle a record with a missing field without crashing.
50. Handle a record with an unknown severity without hiding it.
51. Handle a malformed JSONL line: skip, count it, and say so on screen.
52. Show the malformed-line count next to the total.
53. Handle a completely empty findings file.
54. Handle a findings file that is a single blank line.
55. Sort ties deterministically.
56. Paginate or virtualise beyond 500 rows.
57. Confirm 5,000 rows does not freeze the window.
58. Confirm scrolling 5,000 rows stays smooth.
59. Add a text filter that works on the rendered rows.
60. Confirm the filter cannot break the display.
61. Confirm no row invents a severity or a score.
62. Confirm every row is traceable to a real record.
63. Add a footnote stating the engine's last run time.
64. Confirm no findings means the panel says the engine has not run.
65. Confirm that message is distinct from "ran and found nothing".
66. Commit with the empty, the small and the large case screenshots.

## D. KEV panel (67-86)

67. Render the KEV entries that exist.
68. Show the KEV source and its snapshot date.
69. Show how many entries are in the snapshot.
70. Show how many match this system's findings.
71. If nothing matches, say "no known-exploited matches" and mean it.
72. Never present a CVE id that is not in the data.
73. Handle an empty KEV snapshot.
74. Handle a malformed KEV entry.
75. Confirm the panel distinguishes "not scanned" from "no matches".
76. Confirm the CVE ids render as text, not as links to nowhere.
77. Confirm the panel shows its own record count.
78. Confirm the panel fits its column at 1180 wide.
79. Confirm long CVE lists scroll, not overflow.
80. Confirm sort order is documented on screen.
81. Confirm the panel does not claim coverage it does not have.
82. Add a one-line explanation of what KEV means, in plain words.
83. Confirm that explanation is accurate.
84. Confirm no count is computed from a stale cached copy.
85. Confirm the panel's numbers match a manual count you did with `grep -c`.
86. Commit with the manual count and the rendered count side by side.

## E. Liveness and runs panels (87-110)

87. Render liveness probes with target, time and result.
88. Distinguish "passed", "failed" and "not probed" visually and in words.
89. Show when the last probe ran.
90. Handle an empty liveness file.
91. Handle a probe with no timestamp.
92. Render the runs list newest first.
93. Show per run: what ran, when, and pass/fail.
94. Handle a failed run as visibly failed, not silently absent.
95. Handle an empty runs file.
96. Cap the runs list and say what is capped.
97. Confirm a run id is not invented when it is absent.
98. Confirm the two panels agree with the underlying counts.
99. Confirm both panels survive a single malformed line.
100. Confirm both panels have their own failure line.
101. Confirm timestamps across panels use one format.
102. Confirm timezone is stated once, clearly.
103. Confirm no panel reads a file it did not declare in the header.
104. Confirm the header list matches the files actually read.
105. Confirm the page loads in under two seconds locally.
106. Confirm the page works with JavaScript enabled only (no build step).
107. Confirm the page has no external requests at all.
108. Confirm the page works with the network unplugged.
109. Confirm the page does not write to storage.
110. Commit.

## F. Selftest (111-132)

111. Write `aegis-page/selftest` (python or node, no deps).
112. It must parse every declared data file.
113. It must fail on a missing file.
114. It must fail on one malformed JSONL line.
115. It must print per-file record counts.
116. It must exit non-zero on any failure.
117. Prove the failure path with a deliberately corrupted copy.
118. Prove the success path against real data.
119. Add a `--quiet` mode for CI use.
120. Confirm it runs with no network.
121. Confirm it needs no packages beyond the image's defaults.
122. Confirm it does not read outside `aegis-page/`.
123. Confirm its output is one line per check.
124. Confirm its exit code matches its message.
125. Run it five times; confirm identical output.
126. Time it; it must be under two seconds.
127. Add it to the report with pasted output.
128. Confirm the page's declared files and the selftest's list match exactly.
129. Confirm the selftest catches a field renamed in the data.
130. Confirm the selftest does not silently skip a missing panel.
131. Confirm it prints the data snapshot time.
132. Commit.

## G. Honesty pass (133-148)

133. List every number on the page and where it comes from.
134. Confirm none is computed from an assumption.
135. Confirm none is hardcoded.
136. Confirm the page never says "secure" or "protected".
137. Confirm the page never claims full coverage.
138. Confirm the page states what it does NOT cover.
139. Confirm the app does not pretend to scan on load.
140. Confirm there is no fake progress bar anywhere.
141. Confirm the empty state is more prominent than a zero count.
142. Confirm a judge reading it cannot mistake it for a live scanner.
143. Confirm the wording matches `AEGIS_SPEC.md`.
144. Fix any wording that overstates.
145. Confirm no CVE, hostname or IP is fabricated.
146. Confirm no screenshot in your report has a fabricated row.
147. Write the claims list: what a judge may ask, and the true answer.
148. Commit.

## H. Proof and report (149-160)

149. Serve the page locally and screenshot the empty state.
150. Screenshot the real-data state.
151. Screenshot the malformed-line state.
152. Paste the selftest pass output.
153. Paste the selftest fail output.
154. Confirm the page loads inside the booted OS on 18934 if it is installed.
155. If it is not installed yet, say so plainly instead of implying it works.
156. Write `os-build/lanes/AGENT_3_REPORT.md`.
157. Put a one-paragraph summary at the top.
158. List completed vs skipped counts.
159. Confirm `git diff --name-only` shows only files you own.
160. Stop. Do not merge, do not touch the engine, do not invent data.
