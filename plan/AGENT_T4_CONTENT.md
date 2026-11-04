# Agent T4 lane: worlds, labs, content and demo proof

Read this whole file before touching anything. Work on branch `agent-t4`.
Commit there. Do not merge. Do not push.

## Mission

The apps exist but several of them render empty because their data is missing,
their 3D library is the wrong copy, or a world file is not on the image. Your
lane makes the content real: the science lab, the music scenes, the dispatch
boards, the security dashboard, and the captures a judge will look at.

## Owned paths (only these)

- `os/worlds/`
- `labs/`
- `design/` except the pages attributed to another owner in its header
- `aegis-page/`
- `js/` and `vendor/`
- `surfaces.html`, `board.html`, `bus.html` (content, not the dock wiring)
- `os-build/captures/`
- `os-build/DEMO.md`, `os-build/HACKATHON.md` (append-only corrections)
- `os-build/lanes/T4_REPORT.md` (yours to write)

Do not edit `os-build/face/`, `trio/`, `agents/`, `agent-layer/`,
`server/`, or `os-build/identity/`. Those have owners.

## Rules

- No QEMU. No paid API calls.
- Every page you claim renders needs a headless screenshot at 1440x900 and a
  note on what data it loaded.
- A page with no data must say so in the page, not in the console.
- Call subagents. You must use the subagent tool (Task) for the sections
  below, at least three of them, and you must not do the work yourself in one
  pass. A subagent stays in its section's files. A fourth subagent reads the
  diffs against this file at the end.

## Section A. What the data looks like (1-16)

1. List every world under `os/worlds` with its size and its file count.
2. For each, name the file the dashboard reads first and whether it parses.
3. Find every world that is referenced by a page but missing on disk.
4. Find every world that exists but no page reads. List them.
5. Count the records in each world's run file and paste the counts.
6. Check every JSON file under `os/worlds` parses. Paste the failures.
7. Check every JSON file has the fields its page expects. Write the mapping.
8. Find duplicated world data between two directories. Name the copies.
9. Measure the total size of what the image needs from `os/worlds`.
10. Decide what ships and what gets generated. Write the rule.
11. Record the decision table with sizes.
12. Trim anything over the size you can justify, and say what you dropped.
13. Confirm the trimmed set still renders every page you own.
14. Write a small script that validates every world file against its schema.
15. Run it and paste the summary.
16. Add it to the tree checks so a broken world fails early.

## Section B. Dispatch boards (17-40)

17. Open the boards page and list every board it offers.
18. For each board, name its pack file and whether it loads.
19. Fix every pack file that fails to parse.
20. Make every board show its record count and its last update time.
21. Make a board with no records say so, with the pack name it looked for.
22. Make a board's filter survive a reload.
23. Make a board's detail panel show the source file of each record.
24. Make a malformed record skip visibly, with the line number.
25. Make the board's timestamps match the desktop clock format.
26. Remove any board that has no data and no owner. List what you removed.
27. Make the board page load in under one second with 500 records.
28. Measure it and paste the number.
29. Make the board work at 1366x768.
30. Make the board's empty state name the command that would fill it.
31. Add one screenshot per board.
32. Confirm no board fetches anything off-localhost.
33. Confirm no board page throws on load with the backend down.
34. Make the surfaces page link every board that exists, and only those.
35. Remove dead links from the surfaces page. List them.
36. Make the surfaces page say what each surface is for, in one line.
37. Check the board's keyboard navigation. Fix what is unreachable.
38. Make the board's search match case and accents sensibly.
39. Add a selftest for the board's record parser with real and malformed input.
40. Run it and paste the output.

## Section C. Science lab and 3D (41-68)

41. Open the molecule lab and list every rendering path it can take.
42. Confirm which copy of three.js each 3D page loads. List the paths.
43. Remove duplicate library copies. Keep one and repoint every page.
44. Prove the repointed pages still render.
45. Make every 3D page fall back to a 2D view when WebGL is unavailable, with a message.
46. Prove the fallback by forcing it with a query parameter.
47. Make the fallback say why it is showing 2D.
48. Make the molecule lab load a real structure by default, not an empty canvas.
49. Name the structure file and its source.
50. Make the lab show atom count, bond count and formula for the loaded structure.
51. Make the lab's rotation stop when the tab is hidden, and measure the CPU saved.
52. Measure CPU with the scene idle and paste the number.
53. Reduce idle CPU if it is above 10 percent, and say how.
54. Make the lab's controls keyboard reachable.
55. Make the lab's canvas resize without stretching.
56. Make the lab's labels readable at 1366x768.
57. Remove any 3D page that has no data and no owner. List them.
58. Make the science review page's viewport meta correct.
59. Make the review page's table scroll inside its card, not the page.
60. Make every lab page's footer name its data source.
61. Confirm no lab page loads a font or a shader from a CDN.
62. Confirm every shader or asset path resolves in the image.
63. Add a check that fails when a 3D page references a missing asset.
64. Run it and paste the result.
65. Screenshot the lab with a loaded structure.
66. Screenshot the lab in fallback mode.
67. Record the frame time or say you could not measure it.
68. Document how to add a structure in one paragraph.

## Section D. Music (69-88)

69. Open every music page and list what each one does.
70. Confirm which pages play audio and which only draw.
71. Fix the page that burns CPU while stopped. Prove the fix with a before and after.
72. Make the notes scene stop rendering when the audio is stopped.
73. Make the synth fallback work without WebGL. Prove it with a forced 2D run.
74. Make every music page show the loaded track name and length.
75. Make a missing track fail with the path it looked for.
76. Make the transport controls keyboard reachable.
77. Make the volume control persist across pages.
78. Make the 3D notes page and the 2D notes page show the same data.
79. Remove the page that duplicates the other if they are the same job. Say which.
80. Make every music page's empty state say how to load a file.
81. Confirm no page autoplays audio on load.
82. Confirm no page blocks the UI while a track loads.
83. Add one screenshot per music page.
84. Record the audio file sizes the image ships.
85. Trim any audio over the size you can justify.
86. Make the music page work at 1366x768.
87. Confirm the music page's canvas does not fight the window manager for focus.
88. Write the music section with the CPU numbers and the file paths.

## Section E. Security dashboard and messages (89-112)

89. Read the Aegis page and list every panel with its data file.
90. Confirm every data file exists on the image path the page reads.
91. Make a missing data file name itself in the panel.
92. Make the findings list sort newest first and show the count.
93. Make the KEV panel state how many entries it checked and how many matched.
94. Make the liveness panel state how many hosts answered.
95. Make every panel's empty state explain the absence, not apologise.
96. Remove any panel that shows a number it cannot source. List them.
97. Make the page render with 5000 rows without freezing, or cap it and say so.
98. Make the page's timestamps match the desktop clock.
99. Add the page's selftest to the tree checks.
100. Run the selftest and paste it.
101. Screenshot the page with real data.
102. Screenshot the page with data missing.
103. Read the messages page and list its data source.
104. Make a malformed message skip visibly with its line.
105. Make the messages page's empty state name the queue.
106. Remove the external push worker references if any remain. Prove with a grep.
107. Make the messages page's timestamps consistent.
108. Make the messages page's keyboard focus visible.
109. Confirm no page requests a remote push service.
110. Add one screenshot of the messages page with at least three entries.
111. Make both pages work at 1366x768.
112. Confirm both pages make no external request. Paste the sweep.

## Section F. Demo proof and docs (113-138)

113. Read `DEMO.md` and list every beat with its command.
114. Run every command that does not need a boot. Paste what each printed.
115. Mark the beats that cannot run on this machine, and why.
116. Correct every claim in `DEMO.md` that the tree no longer supports.
117. Add a beat zero: sync the image, then prove the tree matches.
118. Add a beat for the three division apps with the page paths.
119. Add a beat for one agent job end to end, if T3 lands it. Otherwise say pending.
120. Replace the placeholder screenshots with real captures from this tree.
121. Make every capture's filename say the date and the size.
122. Remove captures that show a screen the tree no longer produces.
123. Make `HACKATHON.md` list only claims with evidence links.
124. Cut any claim a judge could disprove in one click.
125. Add the honest limits section: what is not done.
126. Write the one-page status for the user: real, thin, missing.
127. Check every number in your docs against the tree and fix drift.
128. Make the docs say which branch each feature lives on.
129. Add a screenshot index with one line per image and what it proves.
130. Confirm no doc claims a boot you did not do.
131. Confirm no doc claims a test you did not run.
132. Confirm no doc names an agent's work as done when the branch is unmerged.
133. Make the doc's commands copy-pasteable from the repo root.
134. Test three of them verbatim and paste the output.
135. Make the docs list the ports and what answers on each.
136. Make the docs list the demo's fallback if the network is down.
137. Record the ISO build state honestly: tree-only, no master.
138. Write the final summary with the three things most likely to break on stage.

## Section G. Proof and reporting (139-150)

139. Write `os-build/lanes/T4_REPORT.md` with one section per letter above.
140. Every claim gets a command and its output.
141. Paste the console-error sweep for every page you own.
142. Paste the external-request sweep.
143. List every file you changed with `git diff --stat`.
144. Confirm no file outside your owned paths appears there.
145. Confirm no QEMU process is running. Paste the check.
146. Confirm your commits are on `agent-t4` only. Paste the branch and the log.
147. Confirm `main` is untouched by you.
148. List every capture you added with the path and what it proves.
149. List the cross-lane requests with file, line and owner.
150. End with the next three tasks you would do with another session.
