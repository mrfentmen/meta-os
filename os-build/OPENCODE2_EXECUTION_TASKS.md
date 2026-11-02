# OPENCODE 2 — EXECUTION TASKS (Science Lab + Officina)

Del's order 2026-11-02: OpenCode 2 works the programs —
Science Lab and Officina (the blueprints-and-buildings one) —
and has them ACTUALLY BUILD AND DO SCIENCE, so the proof is
real runs, not specs. Your first task list built the Science
Lab foundations. This list executes.

Branch: `opencode2/execution` (after step 1). NEVER push main.
Commit per section. Status file:
`os-build/OPENCODE2_EXECUTION_STATUS.md`, one block per section:
what ran, artifacts, verdicts. UNPROVEN items named, never hidden.
Sub-agents: Task tool, one per independent cluster, never two
editing the same file; YOU verify every sub-agent result.
Territory: os/worlds/science-lab/**, labs/**, os/worlds/
officina/** if present, officina code wherever it lives in the
tree (find it; do not fork it), tests/science-lab/**,
tests/officina/** if present.
Lane exclusions: kernel/src (Rowan), server/queue (Pax's
integration lane), agents/registry.json (Pax merges registry
changes — propose them in the status file instead).
API key rule: the Mac key flakes. Log once, work offline items,
never idle, never retry-loop. For live model calls:
`~/Desktop/hackathon key.txt` line 1 only, into the environment
as SPARK_API_KEY; never print, log, or commit it. The model
client patterns are in server/queue/models.py and
os-build/MODEL_INTEGRATION.md — mirror them, do not depend on
the sandbox helper.

## Section 0 — land your finished work (1-4)

1. Your wave-1 science-lab work is finished locally but NO
   opencode2 branch exists on GitHub yet. Push it to
   `opencode2/science-lab` now, exactly as it stands.
2. Record in the status file: the branch tip sha + which
   wave-1 sections are complete, partial, or unproven.
3. Start `opencode2/execution` from current main (pull fresh;
   main moved: models.py + judge v2 + wave-2 all landed).
4. Re-run your wave-1 test suites on this base; record counts.

## Section 1 — Science: one real cycle, end to end (5-20)

Pick the reproduction target first: a published COMPUTATIONAL
result you can re-derive from data in the repo or a cited
public source. The Delaney cross-check data under labs/ is one
candidate; a small published benchmark is another. Name the
target, its source, and its expected value BEFORE running.

5. Write the cycle record: question, target result, source.
6. Name the falsifier: the observation that would kill the
   claim. No falsifier, no cycle — pick a different target.
7. Pre-register: hash the experiment plan (inputs, method,
   expected value, tolerance) and commit the hash BEFORE any
   result exists. The commit order is the proof.
8. Build the run: deterministic where possible; seed recorded.
9. Run it. Save raw outputs, untouched.
10. Score against the pre-registered expectation: MATCH or
    DIFFER, with the differing fields named.
11. Critic pass (mandatory): a separate call or agent argues
    the result is wrong; record its strongest objection.
12. Answer the objection with evidence or concede it in the
    record. No silent dismissals.
13. Independent verification: re-run from the recorded inputs
    in a clean directory; outputs must match bit-for-bit or
    the difference is explained in the record.
14. Assign the evidence-ladder level (0-6) the cycle EARNED —
    exports and summaries may never state a level above it.
15. Write the ledger entry: hashes, seeds, timestamps, level.
16. If the cycle FAILED to reproduce: that is a result. Record
    it as a failed reproduction with the same completeness.
17. Save the cycle pack under labs/cycles/cycle-001/ (plan,
    prereg hash, inputs, raw outputs, critic, verification).
18. One-paragraph plain summary of what the science showed.
19. List what a second pair of eyes should check (Bond's lane
    will reproduce this cycle from your pack).
20. Status block for the section.

## Section 2 — Science: second cycle, different domain (21-30)

21. Pick a second target in a DIFFERENT department than
    cycle 1 (chemistry if 1 was physics-shaped, etc.).
22. Falsifier + pre-registration hash committed first, again.
23. Run, score, critic, verify — the full Section-1 discipline.
24. Compare the two cycles: what the lab's machinery did the
    same, what had to change per domain.
25. If cycle 2 needs a tool the lab lacks: build the smallest
    version, in territory, with a test.
26. Ladder level for cycle 2, earned not hoped.
27. Cycle pack under labs/cycles/cycle-002/.
28. Plain summary paragraph.
29. Update the lab's experiment ledger with both cycles.
30. Status block.

## Section 3 — the lab thinks with the models (31-40)

Wire the Meta models into the lab's real work (not demos):
director/reasoning = Muse Spark, figure reading = Muse
Wonder (multimodal), image segmentation = SAM 3.1.

31. Director call: Spark plans cycle 3's approach from the
    question; save prompt + reply + receipt (model, usage).
32. Run cycle 3 under that plan (full discipline: falsifier,
    prereg, critic, verify — compressed is not allowed).
33. Wonder call: give Wonder a figure/plot from a cycle's
    outputs; its reading goes in the record, checked against
    the numbers by you — agreement or difference, as-is.
34. SAM call: segment one specimen/molecule image from the
    labs tree; the box/mask record joins the cycle pack.
35. Critic via a SECOND model (Wonder if the director was
    Spark): its objection recorded like any critic's.
36. Every model call's receipt saved under the cycle pack —
    Bond verifies these exist and parse.
37. State, per call, what the model changed about the work.
    A call that changed nothing gets said so.
38. Cycle 3 pack + ladder level.
39. Total model spend for the section, from receipts.
40. Status block.

## Section 4 — Hortus: a real breeding run (41-48)

41. Read the Hortus code + its tests; run the suite first.
42. Define one breeding run: population, mutation rule,
    fitness measure — all recorded before the run.
43. Run at least 5 generations; log every generation's best
    + mean fitness to the run record.
44. Keep the run deterministic (seed recorded) so Bond can
    reproduce it exactly.
45. Report the fitness curve honestly — flat is a result.
46. Save the run pack under labs/hortus/runs/run-001/.
47. Name what the breeding actually selected for, in one line.
48. Status block.

## Section 5 — Officina: build the missing stages (49-62)

Officina today: the faber loop exists, stage 2a (rough-words
intake + self-building brief) passes its 14/14 gate on main.
Stages 2b-2d are UNBUILT. Build them, smallest real versions.

49. Find the Officina code; run its existing suite + the 2a
    gate script; record the baseline.
50. 2b prior-art step: given a brief, search the sources
    available to you (repo + public web via your tools) and
    produce a prior-art note. It is a research aid — the words
    "patentability opinion" must never appear as its claim.
51. Test 2b on one brief; the note names its sources.
52. 2c blueprint pack export: from a 2a brief, emit the pack —
    dimensions, materials, steps — every dimension inside the
    widened bounds (FIN_HEIGHT_MM 80, BASE_THICKNESS_MM 12
    lineage; read the current bounds from the code).
53. Test 2c: a checker that rejects an out-of-bounds pack.
54. 2d workshop memory: packs + outcomes append to a workshop
    record the next brief can read; oldest entries never
    silently dropped (append-only, like the lab ledger).
55. Test 2d: two sequential briefs; the second's record shows
    the first's entry was readable.
56. Muse Image concept render for one pack: labelled
    GENERATED in the pack and in the filename. A concept —
    never presented as a measurement or a photo.
57. Receipts for any model calls saved with the pack.
58. Full Officina suite + 2a gate re-run: all green, counts
    recorded.
59. If a stage cannot be built honestly in scope: mark it
    UNIMPLEMENTED with the blocker, do not fake it.
60. Status block per stage (2b / 2c / 2d separately).
61. Propose (do not make) any registry/README changes in the
    status file for Pax.
62. Section record: os-build/logs/OC2_OFFICINA_STAGES.md.

## Section 6 — Officina: one real build, words to pack (63-72)

63. Take ONE verbal brief (write it the way a person would
    say it — a thing to build, rough words, no numbers given).
64. Run it through 2a: the self-built brief, saved.
65. Run 2b: the prior-art note, saved.
66. Run 2c: the blueprint pack, bounds-checked, saved.
67. Run the faber loop on the pack if it takes packs as input;
    if it does not, record that gap instead of forcing it.
68. The pack + brief + note land in workshop memory (2d).
69. Independent check: re-run the bounds checker on the pack
    from a clean directory; verdict recorded.
70. Plain summary: what Officina would build from those words.
71. Pack under labs/officina/builds/build-001/ (or the
    territory equivalent — name the path in the status).
72. Status block.

## Section 7 — the proof pack + truth pass (73-84)

73. Assemble os-build/logs/OC2_EXECUTION_PROOF_INDEX.md:
    every claim in this list -> its artifact path.
74. Truth pass over your own status file: every DONE has an
    artifact; anything else is relabelled UNPROVEN.
75. Truth pass over cycle summaries: no summary states a
    ladder level above its cycle's recorded level.
76. Truth pass over Officina: no pack claims a dimension
    outside bounds; the concept render is labelled everywhere.
77. Sweep the branch for secrets before the final commit.
78. Sweep for files over 1MB you added; justify or remove.
79. Full science-lab + officina suites on the final tree.
80. Final status pass: sections DONE or UNPROVEN, no gaps.
81. Final commit on opencode2/execution.
82. Post nothing to main; Pax merges at the checkpoint.
83. If blocked on Del: write it in the status, keep going.
84. Last status line: what remains unproven, in plain words.
