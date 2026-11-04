# Agent R2-T4 lane: applications, content, data, proof

## Tree changes after this lane file (2026-11-04, Buffy) — read before starting

These are merged into `main` already. Nothing below is a task; it is the map.

- **One messaging system: `board/`.** `relay/` (Nuntius relay + viewer) and
  `os-build/face/board.py` / `board.html` are deleted. `board/board.mjs` runs on
  18935: `GET /rooms/<room>/messages?since=<n>`, `POST {nick,text}`,
  `POST /rooms/<room>/notify`. The dock's Messages tile opens it; the shell bell
  (`notify.js`) polls its `general` room. Do not add a second transport.
- **`index.html` (repo root) is deleted.** It was the app hub; the dock lists
  apps. The site root is `surfaces.html`, and `server/server.mjs` serves it for
  `/`. `bus.html` stays: it is the dashboard page the DSH tests cover.
- **`imperium/index.html` is archived**, not in the product: no dock tile, not
  copied into the image. The tests read it as a fixture — leave the file alone
  and do not wire a tile to it. The three divisions (`trio/vigiles.html`,
  `ignis.html`, `medicus.html`) are the product.
- **Both logo studio pages are deleted** (`logo-studio.html`,
  `design/meta-ascii-logo-studio.html`), and with them the
  `design/agent-budget-dashboard.html` mock. The spinning loop is
  `js/logo-background.js` / `os-build/face/logo-background.js`; the studio-only
  tests were removed with the pages.
- **Shared chat box: `js/site-chat.js`.** `<script src="js/site-chat.js"
  data-room="..." data-label="...">` gives a page the Board rooms (surfaces.html,
  labs/molecules, labs/music3d, labs/science-lab-review, Custos, Officina,
  face/musica.html). On surfaces.html the room follows `#board-<room>`.

Paste this whole file to the agent. Work on branch `agent-r2-t4` in worktree
`/tmp/agent-r2-t4`. Commit there. Do not merge. Do not push. Do not switch any
other worktree's branch.

## Mission

The apps behind the dock are uneven: Nuntius looks like a debug panel,
Officina is a spec sheet over an empty blueprint, Musica is two copies of the
same page, Science is split across a viewer and a report, Aegis is a frozen
snapshot, and Nervus has no face at all. Round 2 makes each one a real app with
real data, honest empty states, and a proof a judge can repeat.

Buffy is changing typography in these pages right now. Do **not** edit
`font-family`, `@font-face`, `vendor/fonts/`, or the type scale. T3 owns the
agent and bus APIs; call them, do not rebuild them.

## Owned paths (only these)

- `labs/` (molecules, music3d, officina, science-lab-review, cycles, hortus, review)
- `design/` except `meta-ascii-logo-studio.html`
- `aegis-page/`
- `bus.html`, `surfaces.html`, `board.html`, and their page scripts
- `nervus/index.html` (new page only; not the runtime)
- `os-build/lanes/R2_T4_REPORT.md` (yours to write)

Do not edit `trio/`, `os-build/face/`, `agents/`, `agent-layer/`, `server/`,
`os-build/iso/`, or `.gitignore`. Request those changes in the report.

## Rules

- **No QEMU.** Prove with the local server, headless Chromium at 1440x900 and
  1366x768, real data files, and unit tests.
- No remote asset URLs. Every font, script, and image must be local.
- No invented rows. If data is missing, say what is missing and how to fill it.
- Call subagents. At least four, one per section, plus one reviewer.
- Every claim needs a command and pasted output.
- Leave no background server running at the end.

## Section A. Nuntius (1-22)

1. Read the current bus page and list every developer-facing string a user can see.
2. Replace the relay setup screen with the app: rooms rail, message pane, composer.
3. Default to the local bus from T3; no Upstash fields on first load.
4. Show a connection state that names the bus URL and port.
5. Add a room list with unread counts and a selected state.
6. Add message history with sender, time, and delivery state.
7. Add a composer that sends on Enter and makes a newline on Shift+Enter.
8. Add optimistic send with a visible failure and retry.
9. Add attachments with a picker, size error, and progress state.
10. Add message search with a result count and a no-results state.
11. Add presence avatars or initials with an offline state.
12. Add an empty room state that says how to send the first message.
13. Add a backend-down state naming the port, never a blank pane.
14. Add keyboard navigation between rooms and a focus ring.
15. Add a message context menu with Copy text and Retry.
16. Make long messages wrap without horizontal scroll at 1366x768.
17. Make the page usable with the sidebar collapsed under 1100 px.
18. Remove the "Broadcast this bus" wording; use plain room language.
19. Add a data-URI favicon so no request 404s.
20. Add a page selftest that renders with a stub bus and exits 0.
21. Capture real, empty, and backend-down screenshots at both sizes.
22. Confirm the page makes zero remote requests.

## Section B. Officina (23-44)

23. Read the recorded runs and list every field the workshop can show.
24. Rebuild the page as a workshop: job queue left, run detail right.
25. Add a job list with status, agent, started, duration, and result.
26. Add filters by status and agent, persisted in the URL.
27. Add a submit form that calls the T3 job API and shows the accepted id.
28. Add a run detail with inputs, variants, pass/fail, and artifacts.
29. Add the proven design numbers from the real runs, labelled with their source.
30. Add a variant table with thermal result, margin, and pass/fail.
31. Add a failure list naming the failed jobs and their measured gap.
32. Add an empty state for a repo with no runs, with the fill command.
33. Add a backend-down state naming port 18940.
34. Remove the blueprint grid from the content area; keep it only as a page edge.
35. Make the layout fill 1440x900 without a 60% empty field.
36. Make the layout work at 1366x768 with the detail pane scrollable.
37. Add keyboard focus and Escape to close the detail pane.
38. Add a copy button for a run id and one for the artifact path.
39. Add a link from a job to the agent that produced it.
40. Add a selftest that renders the page with the real run fixtures.
41. Capture the list, a passing run, a failed run, and the empty state.
42. Confirm every number on screen traces to a file path in the page.
43. Remove any claim the run data does not support.
44. Keep the page read-only where the API is read-only; no fake mutation.

## Section C. Musica (45-60)

45. Compare the two music pages and list every behavioural difference.
46. Choose one page as the app and make the other redirect or be removed.
47. Keep the 3D staff, the two voices, and the transport that already works.
48. Add a track or take list from the real MIDI/session files.
49. Show the selected take's note count, duration, and source file.
50. Add real playback of the selected take, not only the synth preview.
51. Add a visible audio state: playing, stopped, muted, unsupported.
52. Stop the idle animation when audio is stopped; prove the frame count drops.
53. Add a reduced-motion path with the same controls.
54. Add a no-WebGL fallback that still plays audio and says why 3D is off.
55. Make the transport keyboard reachable and labelled.
56. Show an honest empty state when no takes exist, with the folder path.
57. Remove the duplicate page reference from every dock or link source.
58. Add a selftest for the take parser and the transport state.
59. Capture playing and stopped states at 1440x900.
60. Confirm no remote audio or font URL is requested.

## Section D. Science Lab (61-74)

61. Compare the molecule viewer and the reproduction-cycle report; list what each owns.
62. Make one Science Lab landing page that links both as modes.
63. Make the molecule bench the default mode.
64. Add a molecule picker with names and formulas from the real data.
65. Add element filtering that actually filters bonds and atoms.
66. Add atom and bond counts that update with the selection.
67. Add a named no-WebGL state with the 2D fallback where one exists.
68. Turn the cycle report into a detail view, not a separate site.
69. Add a cycle list with phase state and completed counts.
70. Show each claim at its recorded level; never upgrade a level on screen.
71. Add a source-file link for every claim.
72. Add an empty state for a missing cycle directory.
73. Add a selftest for the molecule data and the cycle parser.
74. Capture both modes at 1440x900 and 1366x768.

## Section E. Aegis, Nervus, Boards (75-92)

75. Make the Aegis dashboard refresh from its data files without a rebuild.
76. Show a last-updated timestamp and a stale warning after ten minutes.
77. Keep the KEV and liveness counts derived, not typed in.
78. Add a filter by severity and a result count.
79. Make every row link to its source record.
80. Add an empty state for each panel when its file is missing.
81. Keep Aegis read-only; no scan or write action from the page.
82. Build `nervus/index.html` as a read-only runtime status page.
83. Show dose windows, hosted lane state, and the last run from real files.
84. If a file is missing, name it and the command that produces it.
85. Add Nervus to the dock only when its page returns 200; otherwise leave it out.
86. Fix the two 404s on Boards: `os/lab/records.json` and `gates/delaney/manifest.json`.
87. If the data does not exist, show the missing path and the fill command; never fetch a 404 silently.
88. Add a board index count and a per-board source path.
89. Add a board-level error line naming the file and port.
90. Add a selftest for the board loader with one missing file.
91. Capture Aegis, Nervus, and Boards at 1440x900.
92. Confirm no board fetches off localhost.

## Section F. Proof and handoff (93-100)

93. Run the local server and sweep every owned page for console errors; paste the table.
94. Sweep every owned page for remote requests; paste zero.
95. Sweep every owned page at 1366x768 for overflow; paste the offenders.
96. Run every page selftest and paste the results.
97. Confirm the pages still render with every backend down, naming each port.
98. List every cross-lane request with file:line (fonts, dock, APIs, data).
99. Confirm no server or browser process is left running.
100. Write `os-build/lanes/R2_T4_REPORT.md` with task ticks, proofs, skips, and next three steps.
