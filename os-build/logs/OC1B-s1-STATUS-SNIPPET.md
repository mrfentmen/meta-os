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

## README VERDICT (§18, OC1B-426..OC1B-450) — tree 3452d244 (FINAL)

Checklist with per-row verdicts: os-build/logs/OC1B-readme-checklist.md (46 rows marked).
Fix commit: 01f8c264 (README.md only, 9 lines; proof + re-runs + badge check:
os-build/logs/OC1B-readme-fixes.md; post-fix npm re-run:
os-build/logs/OC1B-readme-node-rerun.txt = 2071/2015/56).

- Baseline verdict block: tip sha 3452d244663f4ad87e51bfe2f0dd3902f90ae087,
  gate GREEN 8/8 twice (95s, 32s), panic 0 both serials, every assertion SAME
  across runs (alive, mem K4, HELLO, exit 0, task-killed + sleeper continues,
  readkey entry, commands, STATUS). No failures; kernel lanes NOT stopped.
  Wave-3 diff: no lost claim, no regression. Bootimage 11202048 B /
  sha256 4d0cfaa0…. Clone clean at close.
- README per-number verdicts (FINAL): STALE-FIXED: node row + badge
  (2015/56; newcomer R11-282 docs-index gap named), queue row (0 skip),
  rust workspace row + badge + built-with row (does not build, intel E0063;
  excl-intel 1851 pass / 0 fail / 88 suites), intel row (0 run),
  kernel lines (5984 -> "about 6,000", 2 places), node-failures paragraph.
  STALE-NAMED-NOT-FIXED (needs §16 re-run or Pax ruling, not a number edit):
  Goose 33 programs / 1,253 checks receipt block (cited record now says
  59 drivers / 2,715 assertions), services count 25 (24 manifest rows vs
  37 source dirs). UNVERIFIABLE-AS-STATED (named, never padded): OS-side
  ~122,000 (method unstated; 119k-139k reconstructions), batch-2
  100/42/46/0 + 6.4s (no eval log; in-repo audit agrees), musica "4 of 4"
  (no such suite; actual node musica suite 39/39 pass), model endpoint
  history (no receipts in tree; §9 re-proves live). VERIFIED: worlds 12/12,
  officina 49 + gate 14/14, science 163/163, hortus 14, loop 11/12,
  19 crates, 28 agents, bootloader 0.9.35, framebuffer 576, ignis 17,
  $75 guardrail, relay 8787, EVAL4 80/20/0 + 5/5 + 0/8, live DOT reading,
  all README links 200, gate 7/7 lineage, 73-min R5-5 record, 2-hour soak
  still PENDING, kernel 13 files, all serial claims.
- Fences kept: no main push, no opencode/500 commit, no kernel/src edit
  (diff empty), no face/web work, baseline runs in /tmp/oc500-baseline only,
  every proof committed. Mac key never needed, never touched.
