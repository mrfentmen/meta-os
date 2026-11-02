# BOND — TASK LIST WAVE 2 (2026-11-02)

Bond = the second Buffy, on the 8GB Mac. Verification lane. Light work only:
one heavy thing at a time, `cargo -j1` if cargo is unavoidable, no full-repo
builds, no kernel writes (kernel/src is Rowan's pen), no pushes to main.
Branch: `bond/wave2`. Commit per section. Pax merges at checkpoints.
If a step needs a credential you do not have, mark it BLOCKED in the status
file and keep going — never idle, never invent a result.

Status file: `os-build/BOND_WAVE2_STATUS.md` — one line per section as you
finish it: section, what ran, pass/fail counts, evidence file paths.

## Section 1 — Program proof ledger (the README and the judges need this)

For EACH program below: find its tests or demo path, run it on this machine,
record the result in `os-build/PROGRAM_PROOF_LEDGER.md` (one row per program:
name, what you ran, exact command, pass/fail counts, date, evidence path).
Never write a result you did not run.

1. Imperium queue suite (python, tests/queue-python).
2. Imperium node tests for js/products.js + js/schema.js only.
3. Science Lab python tests under os/tests (hortus pattern).
4. Officina python tests (the officina suite the 2a gate runs).
5. Musica node tests (musica files only).
6. Aegis node modules: run each aegis/*.mjs self-check that exists.
7. Nervus: confirm no code claims a model was modified; list what exists.
8. Agent runtime tests: tests/agents-runtime.test.mjs.
9. Watchman tests.
10. Baton + bridge tests.
11. Gym tests.
12. Board tests (board/).
13. Nuntius relay tests (relay/).
14. Face: open face/index.html over a local server, list which windows open.
15. Federation test file (tests/federation-notice.test.mjs).
16. UI-fix audit test file.
17. Goose services: run services/run-goose-tests.sh if present; else count
    services with tests and record the count only.
18. Kernel: READ-ONLY — list kernel/src files + line counts into the ledger.
19. Crates: list the 18 crates + which have tests (grep counts only).
20. Write the ledger summary: programs with proof / programs without.

## Section 2 — Second clean gate (independent verification)

21. Fresh clone of main into a clean directory.
22. Run os-build/gate.sh; save the full log as evidence.
23. Record: 7/7 or the exact failing step, in the status file.
24. Re-run the node test files that Section 1 flagged as failing; confirm
    the same set fails (baseline stability) — list any NEW failure by name.
25. Re-run the python queue suite in the clean clone.
26. Compare Section 1 counts vs clean-clone counts; write differences.
27. Check README test numbers against your measured numbers; list stale ones.
28. Check README program list against the repo tree; list missing programs.
29. Check os-build/PROGRAM_PROOF_LEDGER.md rows all carry evidence paths.
30. Post the gate result summary to the status file.

## Section 3 — Model integration verification (offline first)

Context: the Meta Model API account serves muse-spark-1.3, muse-wonder-1.0,
sam-3.1, muse-image-1.0, muse-voice-transcribe-1.0 (verified by Pax probe
2026-11-2). Pax is landing the integration code on main. Your job: verify
its artifacts, never fake a call.

31. Find the model pipeline code Pax lands (search for model ids in repo).
32. For each model id used in code, confirm it matches the served list above.
33. Find pipeline receipt/log artifacts; confirm each parses as JSON.
34. Confirm every receipt names its model id and timestamp.
35. Confirm any SAM 3.1 output artifact is a mask/segmentation record, and
    that no code claims SAM did language reasoning.
36. Confirm any Muse Image artifact is labelled as generated art.
37. Confirm any Voice Transcribe artifact keeps the raw audio reference.
38. Confirm spend figures in receipts are labelled estimates.
39. IF `~/Desktop/hackathon key.txt` exists on this machine: one smoke call
    to muse-wonder-1.0 (tiny prompt), save the raw response as evidence.
40. Same condition: one smoke call to sam-3.1 on a test frame from the repo,
    save the raw response shape (no interpretation) as evidence.
41. Same condition: one tiny muse-image-1.0 call, save the artifact path.
42. Same condition: one tiny muse-voice-transcribe-1.0 call on a repo audio
    file if one exists; if none exists, mark BLOCKED-no-audio.
43. If the key file does NOT exist: mark 39-42 BLOCKED-no-key and continue.
44. Write `os-build/MODEL_INTEGRATION_EVIDENCE.md` from 31-43.
45. List every place code mentions a model the account does not serve.

## Section 4 — Science + Officina execution support (reproduction lane)

OpenCode 2 is building real Science Lab cycles and real Officina builds.
Science counts a result when an INDEPENDENT re-run agrees. That is you.

46. Read os-build/OPENCODE2_SCIENCE_STATUS.md if it exists; list its claims.
47. For the first completed science cycle: find its ledger + result files.
48. Re-run the same computation from its recorded inputs (seed/hash given).
49. Compare outputs; write MATCH or DIFFER with the differing fields.
50. Check the cycle's evidence-ladder level never exceeds its proof.
51. Check the falsifier + pre-registration hash exist BEFORE the result
    timestamp in the ledger order.
52. For Officina: find the first completed build's blueprint pack.
53. Re-run the Officina 2a gate script against it; record pass/fail.
54. Check every dimension in the pack is inside the widened bounds.
55. Write `os-build/REPRODUCTION_REPORT.md` covering 46-54.
56. List any claim in either lane with no artifact behind it.

## Section 5 — Face + image checks (light)

57. In the clean clone, serve face/ locally; screenshot the desktop.
58. Screenshot the Science Lab window.
59. Screenshot the Officina window.
60. Note which dock entries open a window and which do nothing (list only).
61. If UTM is installed: boot the carrier image, record autologin yes/no.
62. If UTM is installed: record whether the dashboard answers HTTP.
63. If no UTM: mark 61-62 BLOCKED-no-utm and continue.
64. Save screenshots under os-build/bond-evidence/ with dated names.

## Section 6 — Docs accuracy audit

65. Read README.md top to bottom; list every number (tests, lines, counts).
66. Verify each number against the repo or your Section 1-2 measurements.
67. List every program named in README that has no directory or code.
68. List every directory that looks like a program but is not in README.
69. Check the systems line (Imperium, Science Lab, Officina, Musica, Aegis,
    Nervus) against the tree; Custos must appear only as retired.
70. Write `os-build/README_AUDIT_BOND.md` with 65-69 as findings.
71. Check os-build/MODEL_INTEGRATION.md claims against Section 3 evidence.
72. Flag any sentence anywhere in os-build/ that claims a boot, a run, or a
    model call with no log or receipt behind it (list file + line).

## Section 7 — Kernel-adjacent reading records (READ-ONLY)

73. Read kernel/src/mem.rs; write a 10-line plain summary of the heap setup.
74. Read kernel/src/user.rs dispatch; list the syscall numbers actually used.
75. Confirm syscalls.rs is untouched by anyone but Rowan (git log on file).
76. Read os-build/KERNEL_BUILDOUT_SPEC.md; list K-items marked done.
77. For each done K-item, name the boot log that proves it (or NONE).
78. Write `os-build/BOND_KERNEL_READING.md` with 73-77.

## Rules

- Statuses only: VERIFIED (you ran it), CODE-INSPECTED (you read it),
  UNIMPLEMENTED, BLOCKED (name the blocker).
- A result without an evidence path does not count.
- Never edit kernel/src, never push main, never run two heavy jobs at once.
- When all sections are done, start again at Section 2 on the new main.
