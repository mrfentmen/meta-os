# OPENCODE 1 — TASKS WAVE 3 (2026-11-02)

You are OpenCode 1, on Del's Mac. Wave 2 is merged on main
(demo film, kernel proofs, face, carrier, Imperium live).
Wave 3 starts from CURRENT main — main moved a lot since your
branch point: pull fresh. Two big things landed after your
wave-2 base: (a) readkey + W6 are MERGED into the kernel, and
(b) the multi-model integration landed (server/queue/models.py,
judge v2). Your first job is proving the combined tree.

Branch: `opencode/wave3`. NEVER push main. Commit per section.
Status file: `os-build/OPENCODE1_WAVE3_STATUS.md`, updated per
section with proof lines; UNPROVEN items named, never hidden.
Sub-agents: use the Task tool, one sub-agent per independent
cluster, never two editing the same file; YOU verify every
sub-agent result before committing it.
Lane exclusions: no kernel/src writes (Rowan's pen), no
agents/registry.json edits, stay out of os/worlds/science-lab/**
and labs/** (OpenCode 2's lane).
API key rule: the Mac key flakes in and out. Log it once, work
offline items, never idle, never retry-loop.
Spark key for live runs: `~/Desktop/hackathon key.txt`, line 1
only, read into the environment as SPARK_API_KEY; never print
it, never log it, never commit it.

## Section 1 — the combined kernel tree, proven (1-10)

Main's kernel now carries BOTH readkey (419c209 content) and
W6 fetch, hand-combined by Pax and verified byte by byte —
but the combined tree has never booted. That proof is yours.

1. Pull current main into a clean clone; record the tip sha.
2. Run os-build/gate.sh on the clean clone; save the full log.
3. Boot the gate image in QEMU; save serial + screendump.
4. Prove from the serial: banner, alive line, no panic.
5. Prove the userspace set: hello exit 0, sleeper cycle,
   crasher killed, sleeper continues.
6. Prove readkey ON THE COMBINED TREE: `user readkey: entry`,
   polling lines, a typed byte received (sendkey), clean exit.
7. Prove fetch ON THE COMBINED TREE: run `fetch` at the shell;
   serial shows the ribbon + real status lines; screendump saved.
8. Prove the shell on the combined tree: status twice (ticks
   move), mem, ps (task rows incl. readkey when running).
9. Prove bad syscall 99 still refused on the combined tree.
10. Write os-build/logs/WAVE3_KERNEL_PROOF.md: tip sha, gate
    result, the exact serial lines behind 4-9, file paths.
    If any item fails: the failing line, the log, and STOP —
    report it as the section result, do not fix kernel/src.

## Section 2 — soak + stability (11-16)

11. Collect the wave-2 section-19 soak: find its verdict; if
    the run died with the session, say so in the status file.
12. Start a fresh 2h soak on the Section-1 combined-tree image.
13. During the soak, run the userspace pack drills (hello,
    sleeper, crasher, readkey) 10 times; log each run's result.
14. Record panic count and any anomaly with its serial excerpt.
15. At soak end: verdict line (duration, panics, anomalies)
    into os-build/logs/WAVE3_SOAK.md.
16. If the soak is still running at your last section, leave
    the log path + start time in the status file, marked RUNNING.

## Section 3 — model pipeline, live proofs (17-28)

The integration is on main: server/queue/models.py (Spark +
Wonder chat, SAM 3.1 segmentation, Muse Image generation;
voice raises EndpointUnresolvedError — do not touch that seam).
Judge v2: judge.rule_with_model, used by crew.py when
TRIO_JUDGE_MODEL=1. Your job: prove it all live, with receipts.

17. Read server/queue/models.py and os-build/MODEL_INTEGRATION.md.
18. Run the queue suite; confirm 141/141 before live work.
19. With SPARK_API_KEY set: one models.chat_text call to
    muse-wonder-1.0 (tiny prompt); save the receipt line.
20. One models.segment call on a flagged eval frame (use
    test-footage/frames/ignis-fire-1.jpg); save the returned
    region + the receipt line.
21. Compare SAM's region against the Spark reading's region for
    the same frame (run spark_gen or the helper assess); write
    both numbers into the proof file — agreement or not, as-is.
22. One models.generate_image call (a simple prompt); save the
    image under os-build/logs/wave3-model-proofs/ with its real
    format extension; record the receipt line.
23. Full incident with TRIO_JUDGE_MODEL=1: run one Ignis
    incident end to end (staged frame is fine — label it);
    the timeline's review step must carry judge_mode "model".
24. Save that incident's timeline excerpt as proof.
25. Same incident shape with the flag OFF: timeline carries
    judge_mode "deterministic". Both modes proven, side by side.
26. Force one judge fallback: flag on, key withheld for the
    judge call only if you can do it without breaking the run;
    else simulate by an invalid model env — the recorded reasons
    must name the fallback. If you cannot force it cleanly,
    mark UNPROVEN with the reason.
27. Write os-build/logs/WAVE3_MODEL_PROOFS.md: every call, its
    model, its receipt, its artifact path.
28. Total the wave-3 live spend from the receipts; put the
    number in the status file.

## Section 4 — demo, final form (29-38)

The wave-2 film predates the judge. Beat 6 must show the chain
as it now runs: patrol, review, JUDGE, investigation, response.

29. Read os-build/demo/CAPTURE_NOTES.md + DEMO_SCRIPT beat 6.
30. Re-capture beat 6 with TRIO_JUDGE_MODEL=1 (Section 3's
    incident), showing the judge step and the sim- receipt.
31. Rebuild the film at exactly 180.000s with the new beat 6;
    keep every other beat's frames unless one is now wrong.
32. Update CAPTURE_NOTES.md: what changed, what is real,
    scripted, simulated — in those words.
33. Extract t=10 / t=160 frames; check them against their logs.
34. Confirm the film never shows a face still as if the kernel
    drew it, and never calls a staged reading real.
35. ffprobe the final mp4: duration + streams into the status.
36. Write the DEMO RUNBOOK: exact commands to replay the film
    and every live proof in Sections 1-3, in order, for Nov 4.
37. Rehearse the runbook once, top to bottom, timed.
38. Log rehearsal gaps (anything slow, missing, or manual)
    into os-build/logs/WAVE3_REHEARSAL.md.

## Section 5 — carrier image: bake the toolchain (39-48)

Wave-2 finding stands: the face image has node + git +
chromium, but OpenCode is ABSENT. Del's doctrine: the image
ships the crew toolchain. Fix the recipe, prove the boot.

39. Read os-build/face/build-image.sh + wave2-sec4.md.
40. Add the OpenCode binary to the image recipe (pinned
    version, recorded in the recipe header).
41. Add Freebuff the same way, if it installs cleanly in the
    recipe environment; if not, record why, do not force it.
42. Rebuild the image; record size + sha256 in the status file.
43. Boot the rebuilt image headless; save the boot log.
44. Re-run the four standing checks: autologin on tty1, DHCP,
    dashboard HTTP 200 + live facts, updater pull cycle.
45. In the guest: `opencode --version` output saved as proof.
46. In the guest: confirm the kiosk/face still starts.
47. Split the image for transport ONLY if Del asks; by default
    keep parts OUT of git (repo rule) — recipe + hashes in git.
48. Update os-build/face/STATUS.md rows for 39-47.

## Section 6 — Imperium: close the wave-2 gaps (49-58)

49. Read os-build/logs/wave2-sec5.md first. List every item it
    marks unproven, partial, or scripted-only.
50. Work ONLY those gaps, in its order. Skip anything it proves.
51. If the BOLO + false-positive purge proof is among the gaps:
    run it end to end (flag with visible marks -> BOLO built ->
    close as false positive -> evidence purged, purge receipt).
52. If the cleared path is a gap: one incident the review
    clears; timeline + close state as proof.
53. If the inconclusive path is a gap: one incident the judge
    holds inconclusive (flag on, conflicting readings); no
    dispatch spent; proof from the timeline.
54. If the budget governor is a gap: drive an incident to a
    cap; the stop + receipt lines are the proof.
55. For every gap you close: artifact paths into the status.
56. For every gap you cannot close: the blocker, in one line.
57. Re-run the queue suite after any live run that wrote records.
58. Write os-build/logs/WAVE3_IMPERIUM_GAPS.md as the section
    record (gap list from 49, verdict per gap).

## Section 7 — the 55, prepared for Del's call (59-66)

Analysis only. The decision (update the native mirrors vs
carve the tests out) is Del's; your job is to make it one tap.

59. Reproduce the current node baseline on main; confirm the
    failing set is the known 55, name any newcomer.
60. Group the 55 by file and by root cause.
61. For the update option: list exactly which Swift-mirror
    expectations changed and what updating them would assert.
62. For the carve-out option: list exactly which test files
    would move or be marked, and what coverage is lost.
63. Cost each option in files touched + suite time.
64. Write os-build/NATIVE_55_DECISION_PACK.md with 59-63.
65. Do NOT change any test or mirror in this section.
66. Put the pack's one-line summary in the status file.

## Section 8 — README + submission surfaces (67-76)

67. Audit README numbers against the tree: test counts (node
    2,033 / queue 141), line counts, program list. List stale.
68. Fix ONLY the numbers section 67 proves stale, in README,
    one commit, numbers sourced from your own runs.
69. Read the submission checklist (os-build/
    SUBMISSION_CHECKLIST.md if present; else list what's missing).
70. Dry-run every form field against repo facts; record any
    field whose answer is not in the repo as DEL-ONLY.
71. Draft the state snapshot (FREEZE_CERT successor): proven
    claims only, each with its log path — use Milo's claim
    audit when it lands; until then, mark it DRAFT.
72. Confirm the X post draft exists from wave 2; if missing,
    draft it (Del posts it himself — draft only).
73. Confirm the demo film + runbook + snapshot paths all
    resolve on main.
74. Write os-build/logs/WAVE3_SUBMISSION_PREP.md.
75. List every DEL-ONLY item in the status file, short.
76. Nothing goes out under Del's name in this section. Drafts only.

## Section 9 — bootloader/framebuffer: the decision pack (77-84)

Wave 2 executed the spike: bootloader 0.11 std-fail, 0.10.9
API-fail (evidence on opencode/round7). The graphics route
decision is Del's, held for a Mac screendump. Prepare it.

77. Read the spike result on opencode/round7.
78. Produce the screendump evidence Del asked for: current
    text-mode boot screendump at the shell, saved + named.
79. Write the two routes plainly (upgrade bootloader vs
    hand-rolled framebuffer via framebuffer.rs) with what
    each risks and what each proves.
80. Name the smallest first step for each route.
81. Write os-build/GRAPHICS_ROUTE_DECISION_PACK.md.
82. Do NOT start either route.
83. Also record: W6's fetch uses logo_frames frame 0 in text
    mode — the pack should say what fetch becomes under each route.
84. Status-file summary line for the pack.

## Section 10 — userspace + final proofs (85-100)

85. Read the wave-2 userspace findings (quitter unwired;
    hog/talker/listener absent — those three are Buffy's lane,
    leave them).
86. Wire the quitter userspace program into the build, if the
    wiring is userspace-side only (os-build/userspace/**); if
    it needs kernel/src, STOP and record that instead.
87. Boot proof with quitter in the pack: its entry + exit lines.
88. Re-run gate.sh one last time on your final branch tree.
89. Full node suite on your branch tree; record vs baseline.
90. Full queue suite on your branch tree; record vs 141.
91. Cargo check the crates your sections touched, if any.
92. Update WAVE2_PROOF_INDEX's successor: os-build/logs/
    WAVE3_PROOF_INDEX.md — every wave-3 claim -> its log.
93. Sweep your branch for secrets (keys, tokens) before the
    final commit; report the sweep, not the values.
94. Sweep for any file over 1MB you added; justify or remove.
95. Final status file pass: every section, DONE or UNPROVEN
    with its reason — no silent gaps.
96. Final commit on opencode/wave3.
97. Post nothing to main; Pax merges at the checkpoint.
98. If a section finishes early, start the next — never idle.
99. If blocked on Del: write the blocker into the status file
    and keep going on unblocked sections.
100. The last line of the status file: what remains unproven
    in wave 3, in plain words.
