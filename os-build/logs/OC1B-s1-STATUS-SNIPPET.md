# OC1B-s1 STATUS SNIPPET (opencode/500-s1) — for coordinator merge into OPENCODE1_500_STATUS.md

Do NOT edit OPENCODE1_500_STATUS.md from this lane. Copy the blocks below.

## BASELINE VERDICT (§1, OC1B-001..OC1B-025) — tree 3452d244 (origin/main tip, fresh clone /tmp/oc500-baseline)

- tip sha: 3452d244663f4ad87e51bfe2f0dd3902f90ae087 (proof: os-build/logs/OC1B-baseline-tip.txt)
- gate run 1: GATE GREEN 8/8, wall-clock 95s (proof: os-build/logs/OC1B-baseline-gate.log)
- gate run 2: GATE GREEN 8/8, wall-clock 32s (proof: os-build/logs/OC1B-baseline-gate2.log)
- panic count: 0 in both serials; loader-refused count: 0 in both (proofs: gate logs + os-build/logs/OC1B-baseline-serial.txt + os-build/logs/OC1B-baseline-gate2-serial.txt)
- per-assertion state (run1 / run2): alive SAME-ok/ok; mem-summary-K4 SAME-ok/ok;
  HELLO-FROM-USERSPACE SAME-ok/ok; exit-0 SAME-ok/ok; task-killed SAME-ok/ok;
  readkey-entry SAME-ok/ok; commands-status-help SAME-ok/ok; STATUS-tasks SAME-ok/ok.
  OC1B-017 verdict: every assertion SAME across the two runs, both GREEN.
- OC1B-023: no baseline assertion failed. No failure block. Kernel-dependent
  claims are NOT stopped by this lane.
- OC1B-024 supersede note: this baseline re-verifies wave-3 §1-era claims on
  current main; wave-3 §2 soak and §8 numbers stay open until §7/§18 here close them.
- OC1B-021 cleanliness: the baseline clone is clean after all runs
  (`git status` clean at close; mid-run suite artifacts from OC1B-429/430
  were restored/removed, every line explained in the commit).
- wave-3 serial diff: no lost claim line, no regression
  (proof: os-build/logs/OC1B-baseline-diff.md).
- bootimage: 11202048 bytes, sha256 4d0cfaa0e7a8d7b4980eaee0141f3a6fbb5729efe751ee0e6bde1cc02d94c7c
  (proof: os-build/logs/OC1B-baseline-image.txt).
- userspace: hello/sleeper/crasher/readkey present with sizes
  (proof: os-build/logs/OC1B-baseline-userspace.txt).
- interactive: shell screendump + fetch screendump + typed drive session
  (STATUS ticks 27556 -> 27653 move; mem/ps rows; `sleeper: bad call refused`)
  (proofs: os-build/captures/oc1b-baseline-shell.png,
  os-build/captures/oc1b-baseline-fetch.png, os-build/logs/OC1B-baseline-drive.txt).

## README VERDICT (§18, OC1B-426..OC1B-450) — tree 3452d244 (INTERIM — fixes pending)

Final per-number verdicts land here at the §18 commit. Interim findings:
STALE: node 2016/55 (actual 2015/56, newcomer R11-282 os-docs index gap),
rust 2186 (workspace does not build: intel E0063, 0 run; excl-intel 1851/0),
queue skip (296 pass, 0 skip), kernel lines (5984 vs "about 5,800"),
Goose 33/1253 vs cited record 59/2715, services count 25 vs 24 manifest rows.
UNVERIFIABLE-AS-STATED: OS-side 122,000 (method unstated; reconstructions
119k-139k), batch-2 100/42/46 numbers (no eval log; in-repo audit agrees),
musica "4 of 4" (no such suite in tree; actual node musica suite 39/39 pass),
model endpoint history (no receipts in tree; re-proven live in §9).
VERIFIED: worlds 12/12, officina 49, science 163/163, hortus 14,
loop 11/12 (green cycle fails), 19 crates, 28 agents, bootloader 0.9.35,
framebuffer 576 lines, ignis 17 categories, $75 guardrail, relay 8787,
officina gate 14/14, EVAL4 80/20/0 + 5/5 + 0/8, live DOT reading,
all README links (200s), gate 7/7 lineage, 73-min R5-5 record,
2-hour soak still PENDING, kernel 13 files, ps/mem/status/fetch serial claims.
