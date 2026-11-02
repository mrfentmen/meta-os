# OpenCode 1 — Wave 2: 100 tasks across the codebase

You finished your first list. This is wave 2. A SECOND OpenCode
terminal is now running beside you on the Science Lab only — stay
out of `os/worlds/science-lab/**` and `labs/**`, that lane is his.

## Rules (read first, they bind every task)

- Branch: `opencode/wave2`, off current main. NEVER push to main.
  Pax merges your branch at checkpoints.
- USE SUB-AGENTS. Fan out with the Task tool: one sub-agent per
  independent task or small cluster, never two sub-agents editing
  the same file, and you personally verify every sub-agent result
  before committing it.
- Commit per section (10 tasks). After each section, update
  `os-build/OPENCODE1_WAVE2_STATUS.md`: section, what landed, proof
  lines, what is still UNPROVEN.
- Do not write `kernel/src/**` (Rowan's pen) and do not edit
  `agents/registry.json`. You COMPILE and BOOT Rowan's work and
  report the logs — that proof duty is yours and it is not optional.
- Honesty, hard rules: a claim is only what its committed log or
  test output shows. SIMULATED stays labelled SIMULATED everywhere.
  The Imperium readings in the live-loop proofs are scripted unless
  a real camera frame went through the real assessor — say which.
- The API key on this Mac flaps in and out (provider side, known).
  When it drops: log it ONCE in the status file, work the offline
  tasks, never idle and never retry-loop.
- Deadline: Wed Nov 4, 9:00 PM ET. Sections 1–2 are the submission's
  missing pieces — they outrank everything below them.

## Section 1 — The demo film, R6-2 (1–10)

1. Re-read DEMO_SCRIPT.md and SHOT_LIST.md on main; list every beat's
   required capture and its committed-log fallback.
2. Boot capture: banner, alive line, mem output — screen recording
   plus the raw boot log saved beside it.
3. Ring-3 capture: loader lines, per-program addresses, HELLO FROM
   USERSPACE.
4. Three-programs capture: hello exit 0, sleeper cycling, crasher
   line, all in one take.
5. Fault-isolation capture: page fault, task killed, sleeper still
   cycling after it.
6. Shell capture: status twice with ticks moving, mem, ps rows, bad
   syscall 99 refused.
7. Imperium capture: the full chain on screen — patrol, review,
   judge, dispatch — ending on the SIMULATED receipt close-up.
8. Assemble the 3:00 cut per DEMO_SCRIPT.md timings; every beat
   matched to its log; a beat that fails twice cuts to its log line,
   never a re-shot claim.
9. Export the film (mp4) plus a stills set, into `os-build/demo/`
   on your branch, with a CAPTURE_NOTES.md: what is real, what is
   scripted, what is simulated — in those words.
10. Film self-check: watch the cut end to end; list any frame that
    shows something the logs do not back; fix or cut it.

## Section 2 — Kernel proof duty (11–20)

11. Readkey gate run: gate.sh on Rowan's 419c209 pack, full boot
    log to `os-build/logs/` — `user readkey: entry`, 8 tasks, no
    panic. This log is what Pax merges readkey on.
12. Two-reader proof (R-FP3): the readkey boot evidence shows both
    readers behaving; log committed either way the result lands.
13. W6 gate-2 boot: Rowan's kernel-twin fetch screen (9de854d) booted,
    screendump + log committed — this is Pax's W6 merge evidence.
14. Clean-clone gate: fresh clone of main, gate.sh 7/7, the run's
    output committed as PROOF-<tip>.md under `os-build/logs/`.
15. Current-build screendumps: console, panic path, shell — replace
    the K2-era shots as the current set, named by build tip.
16. Bootloader/framebuffer spike, executed: on a scratch branch,
    attempt the bootloader move from Rowan's spike doc; result is a
    screendump of the kernel drawing, or the exact failure — both
    are deliverables, a shrug is not.
17. Userspace pack proofs: hog (containment line), talker/listener
    (IPC evidence), quitter — one boot log each.
18. ABI checker run against the booted build; output committed.
19. Two-hour QEMU soak on current main: 0 panic is the pass line;
    the log tail and the verdict committed.
20. Kernel proof index: one page listing every proof, its log, its
    build tip — so a judge can check any claim in one click.

## Section 3 — The face, long tail (21–30)

21. OPENCODE_FACE_BUILD.md sections 6+: work the remaining sections
    in order; each lands with its own screenshot.
22. Login flow end-to-end in the carrier image: boot → login →
    desktop, recorded as a boot log + three screenshots.
23. Wallpaper set: every wallpaper renders live (the blue ribbon
    renderer, no static swaps); a screenshot per wallpaper.
24. Every dock app opens and does its real thing: Terminal, Files,
    Dashboard, Code Editor, Notes, Calendar, Calculator, Settings,
    Trash — a per-app verdict list, failures named.
25. The systems from the dock: Imperium, Science Lab, Officina,
    Musica, Aegis, Nervus windows open with their real records
    behind them; any window running on placeholder data is flagged
    in the status file, not hidden.
26. Board window: posts persist across a reboot of the image.
27. Settings: every control applies and survives a reload — tested
    control by control, list in the status file.
28. Dashboard: LIVE cards show live machine facts; RECORD cards are
    labelled records; the two never mix on one card.
29. Face performance pass: boot-to-desktop time measured and
    recorded; any app taking >2s to open is named.
30. Face status file brought current: built / stub / unimplemented
    per app, matching what the screenshots show.

## Section 4 — The carrier image (31–40)

31. UTM boot attempt on this Mac: the face image under UTM
    (Emulate), result recorded either way — boots, or the exact
    failure point.
32. The four standing image checks re-run on the current build:
    autologin, DHCP, dashboard HTTP 200 + live facts, updater pull
    cycle. One log per check.
33. Toolchain bake check: Node, OpenCode, Freebuff present in the
    image and runnable — version lines committed. (This settles an
    open question; if a tool is absent, say absent.)
34. Image size and build time recorded for the current recipe.
35. Firstboot on a fresh image: the crew toolchain's passive
    git-pull updater pulls main and the face shows the new tip.
36. Image failure table: every way the image has failed to boot,
    each with its cause or marked unknown.
37. A second machine shape: boot the image with different RAM/CPU
    counts; record what changes.
38. Dashboard facts endpoint under load: 100 requests, error count
    recorded.
39. Image STATUS.md rewritten from this section's evidence only.
40. The image recipe re-run from clean: same result, or the
    difference named.

## Section 5 — Imperium, live (41–50)

41. Medicus live loop: the third service's end-to-end run (the
    Vigiles and Ignis loops are proven; Medicus is not) —
    assess → review → judge → SIMULATED dispatch to the hospital
    route, receipt + picture committed.
42. Judge-in-the-chain proof: one run per service where the judge's
    ruling is the reason the package moved — the timeline record
    shows `judged_by: imperium-judge` and its reasons.
43. Cleared path proof: a second reading that clears the incident —
    nothing dispatches, the record shows why.
44. Inconclusive path proof: garbage or split readings → the judge
    rules inconclusive, nothing dispatches, record shows why.
45. Yellow path proof: a small sign is recorded and shown, and the
    chain stops there — no review, no dispatch.
46. Eval frames through the live stack: five frames from the
    committed eval pack run through the real server path (not the
    helper alone); outcomes compared to EVAL4.
47. Evidence/bolo proof: a flagged incident produces its BOLO
    record from visible marks only, card reads ID: UNIDENTIFIED.
48. False-positive close: the same incident closed as a false alarm
    — evidence auto-purged, the purge recorded.
49. Budget proof: the patrol governor stops at its cap and writes
    the receipt; the incident timeline shows the stop.
50. Imperium proof index updated: every loop claim → its log,
    receipt, or record.

## Section 6 — Services and agents on the host (51–60)

51. Host the registry loops with real commands where Buffy's Round
    11 has landed them; anything still on a placeholder command is
    listed, not worked around.
52. Watchman on Nuntius: a job posted to the in-repo relay starts
    its agent briefed — the drill from the agent-layer spec, run
    and recorded.
53. Timer sweep fallback: with the relay silent, the sweep starts
    the same job; record shows which path fired.
54. Baton across loops: a job started by one loop is continued by
    another from its baton, zero duplicated file changes — the
    spec's proof, run for real.
55. Budget-kill drill on a hosted loop: cap hit, run stops, receipt
    written, record complete.
56. STOP-file drill: a STOP file halts the loop gracefully with the
    reason recorded.
57. Supervisor restart drill: kill a hosted service; the supervisor's
    restart behaviour matches its record (or the record is corrected).
58. Goose services smoke: every service in `services/` starts,
    answers its health call, stops — one table, failures named.
59. Agent ledger audit: one day of ledger entries re-read; every
    run has brief, outcome, and receipt — gaps named.
60. Section verdicts written into the wave-2 status file.

## Section 7 — Musica, Officina, Aegis, Nervus (61–70)

61. Musica: a full keeper session overnight-style run — session
    record, chips rendered, nothing silently dropped.
62. Musica studio window data: the face window reads the real
    session records; a fresh session appears without a rebuild.
63. Officina faber loop: one verbal-description intake run through
    the loop to a design record; the iteration trail is complete.
64. Officina 2a gate re-run on current main: PASS line recorded
    (the gate is simulated-scores-only; keep its label).
65. Aegis first real sweep support: run Buffy's sweep tooling on
    this Mac if her Round 11 has landed it; findings records
    reviewed, counts only — never a secret value.
66. Aegis OPSEC checklist run over the submission materials draft:
    findings listed for Pax; nothing edited without his merge call.
67. Nervus host prep verification: the model inspector runs against
    a local model directory and produces its record — no model is
    modified, per the spec.
68. Nervus reduction planner: a plan produced for one local model,
    before/after evaluation steps named, nothing executed on the
    model itself.
69. Hands-Free services drill: an order intake → brief → approval
    inbox round trip through Buffy's services, recorded.
70. Per-system status lines updated from this section's evidence.

## Section 8 — Codebase health (71–80)

71. Cargo check across `crates/`: one clean run or the failing
    crates named with their first error each.
72. Cargo tests across `crates/`: totals per crate, failures named.
73. Python suites: queue, custos, hortus, officina — each run, each
    result line recorded.
74. Node suite on current main: totals recorded against the known
    baseline (2,020 tests / 55 known fails at wave start).
75. The 55: a written split — which fails are the native-mirror set
    awaiting the boss's update-vs-carve-out call, which are not.
    Analysis only; do not carve anything out on your own call.
76. For every non-native fail in that split: a fix on your branch
    with its test going green, or a written reason it is not fixable
    in this wave.
77. README number audit: every count the README states (tests,
    lines, services) checked against the tree; corrections proposed
    in the status file for Pax to land.
78. Dead-link audit: every link in README.md and the site resolves;
    failures listed.
79. Repo hygiene: files in the root that belong elsewhere, listed
    with a proposed home each — list only, no moves.
80. check_all / contract checkers run on current main; outputs
    recorded.

## Section 9 — Site and submission surfaces (81–90)

81. Site (meta-os.pages.dev source): every claim on the page checked
    against a record; unbacked claims flagged for Pax.
82. Site screenshots refreshed from the current face build.
83. GitHub profile surfaces: the repo's About, topics, and social
    preview fields — proposed text in the status file (the boss
    sets them; you draft).
84. SUBMISSION_REHEARSAL.md executed: the full submission walked
    through as if it were Nov 4 — every missing field or asset
    listed.
85. Demo-day runbook: machine setup, image, film, fallbacks — one
    page a tired human can follow at 8 PM.
86. X post draft for the Most Viral run: text + which film cut it
    points at (the boss posts it; you draft).
87. Claim-audit support pack for Milo's audit: every public claim
    (README, site, film, forms draft) → its proof pointer, one
    table.
88. FREEZE_CERT converted: the submission-day state snapshot drafted
    from current evidence, ready for Pax + Milo to finalize.
89. Forms dry-run: the hackathon submission form filled in draft
    from the rehearsal — every answer sourced, gaps named.
90. Asset inventory: film, stills, logs, snapshot, forms draft —
    one checklist with locations.

## Section 10 — Final proofs (91–100)

91. Clean-clone gate on your merged-ready branch: 7/7 or the
    failures named.
92. Full node suite on your branch: totals vs baseline, no new
    fails unaccounted.
93. Full Python suites on your branch: all result lines recorded.
94. Cargo check + tests on your branch: totals recorded.
95. A fresh QEMU boot of the kernel from your branch's tree: alive
    line, no panic, log committed.
96. The face image rebuilt from your branch's recipe boots to the
    desktop: log + screenshot.
97. One Imperium loop (any service) run from your branch's tree,
    receipt committed.
98. Status file complete through section 10: every section's proof
    lines present or its gap stated.
99. Branch tidy: commits per section, no stray files, ready for
    Pax's checkpoint merges.
100. Final line in the status file: what is PROVEN that was not
     proven when this wave started, one sentence per item, each
     pointing at its log.
