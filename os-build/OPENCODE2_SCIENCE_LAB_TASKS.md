# OpenCode 2 — Science Lab: 100 tasks

You are the SECOND OpenCode terminal on the boss's Mac. Your whole lane
is **Meta Science Lab** (system two of Meta OS). OpenCode 1 is running
in parallel on the rest of the codebase — stay inside your territory
and there will be no collisions.

## Rules (read first, they bind every task)

- Branch: `opencode2/science-lab`, off current main. NEVER push to
  main. Pax merges your branch at checkpoints.
- Territory: `os/worlds/science-lab/**`, `labs/**`, new tests under
  `tests/science-lab/**`, and your status file. NOT face/, NOT
  kernel/, NOT agents/ (Buffy owns agent hosting; the 13 lab agents
  are already in agents/registry.json — you give them lab-local job
  definitions inside the science-lab tree, you do not edit the
  registry).
- USE SUB-AGENTS. Fan out with the Task tool: one sub-agent per
  independent task or small cluster, never two sub-agents editing the
  same file, and you personally verify every sub-agent result before
  committing it. Parallel where it is safe, serial where files touch.
- Commit per section (10 tasks). After each section, update
  `os-build/OPENCODE2_SCIENCE_STATUS.md`: section, what landed, test
  output line, what is still UNIMPLEMENTED.
- Source of truth: the boss's own LABORATORY design text (in
  `os/worlds/science-lab/` — pack.json, PACK.md — and the upload it
  came from). Six systems: Research Intelligence, Scientific
  Reasoning, Computational Lab, Discovery Engine, Independent
  Verification, Knowledge Repository. Evidence ladder levels 0–6.
  Experiment records carry hashes and seeds.
- HONESTY, hard rules: the discovery cycle's phases 1–7 are sourced;
  steps 9/10 are human-gated in the source. No verified text for a
  step 8 exists — where the source is silent, write the gap into the
  code as an explicit UNIMPLEMENTED marker. Never invent a step,
  a result, or an evidence level. A claim displays at the level its
  record holds, never higher.
- The brain is the Muse Spark endpoint, same as the rest of Meta OS
  (helper: custom.meta-model-api spark_call pattern; the Mac key file
  stays on the Mac, line 1 only, never printed or committed). Where a
  job can be deterministic, make it deterministic — model calls only
  where judgement is the job.
- Deadline: Wed Nov 4, 9:00 PM ET. A working end-to-end lab cycle
  (Section 10) beats breadth. If time squeezes, finish sections in
  order and say so in the status file.

## Section 1 — Foundations (1–10)

1. Audit `os/worlds/science-lab/` against the LABORATORY text: every
   named component → present / stub / missing list in the status file.
2. Lab-local agent job definitions for all 13 registered agents
   (director, literature, analyst, mathematics, chemistry, biology,
   physics, hypothesis, computational, statistician, critic,
   verifier, archivist), one file per agent under `agents/` in the
   science-lab tree.
3. Evidence ladder data model: levels 0–6 as a typed record with the
   promotion rules (what evidence moves a claim up one level).
4. Ladder guard: code refuses to render or export a claim above its
   recorded level; test both directions.
5. Experiment record schema: question, method, code hash, data hash,
   seed, environment, result, evidence level, agent, timestamps.
6. Append-only experiment ledger (JSONL) with a reader that verifies
   the hash chain.
7. Cycle state record schema: cycle id, phase, inputs, outputs,
   gate state (open / human-gated / blocked-on-source).
8. Lab config: endpoint, per-agent budget caps, cycle action caps —
   hitting a cap stops the run and writes the receipt.
9. Lab CLI skeleton: `cycle start|status`, `experiment list|show`,
   `ladder show <claim>` — real commands over the real records.
10. Section tests: schemas round-trip, ledger chain verifies, ladder
    guard blocks an over-level export.

## Section 2 — Research Intelligence (11–20)

11. Literature job: given a question, the literature-researcher
    produces a sourced brief (title, source, what it actually shows).
12. Source record schema: citation, retrieval date, licence/access
    note, one-line claim it supports.
13. Brief assembler: brief = claims each pinned to a source record;
    unpinned claims are dropped, and the drop is logged.
14. Prior-result finder: locate the published computational result
    the first reproduction test will target; record why it qualifies
    (inputs available, result checkable, no paywall on the method).
15. Department shelves: biology / chemistry / physics-math /
    materials source collections as data files.
16. Contradiction check: two sources disagreeing on a claim → the
    claim is marked contested, never silently resolved.
17. Literature budget guard: per-cycle source and call caps, receipt
    on stop.
18. Research Intelligence status record per cycle (sources read,
    claims pinned, claims dropped, contested list).
19. Tests: unpinned claim dropped; contested claim marked; caps stop
    the job with a receipt.
20. Worked example: one real question run end-to-end, records in the
    ledger, output in the status file.

## Section 3 — Scientific Reasoning (21–30)

21. Hypothesis record: statement, what would falsify it, predicted
    measurable outcome, linked source claims.
22. Hypothesis-generator job: from a brief, produce ranked hypotheses
    with falsifiers; no falsifier → rejected, logged.
23. Scientific-analyst job: decomposes a hypothesis into the smallest
    checkable computations.
24. Mathematics-researcher job: checks the decomposition's math
    (units, identities, edge cases) deterministically where possible.
25. Statistician job: pre-registers the analysis — test, threshold,
    sample rule — BEFORE results exist; the registration is hashed
    into the ledger.
26. Scientific-critic job: attacks the plan (confounds, leakage,
    cherry-picking); critic output is a required record, not advice.
27. Reasoning chain record: brief → hypotheses → decomposition →
    pre-registration → critique, hash-linked in order.
28. Gate: a cycle cannot enter the Computational Lab without a
    complete reasoning chain; test the refusal.
29. Tests: falsifier-less hypothesis rejected; pre-registration hash
    precedes any result record; missing critique blocks the gate.
30. Worked example: the reproduction target's full reasoning chain,
    committed as records.

## Section 4 — Computational Lab (31–40)

31. Experiment runner: executes a registered plan in a clean temp
    dir, captures code hash, data hash, seed, stdout, exit code.
32. Determinism check: same plan + same seed twice → identical result
    hash, or the difference is recorded and the claim capped.
33. Department runners: one real small computation per department
    (bio, chem, physics-math, materials) wired to the same record
    schema.
34. Sandbox rule: experiments touch only their temp dir and declared
    inputs; a runner that reaches outside fails loudly.
35. Failure records: a crashed experiment is a result (exit code,
    stderr tail), never a silent retry.
36. Result record writer: outcome vs the pre-registered prediction,
    stated as match / no-match / indeterminate — no adjectives.
37. Compute budget: per-experiment wall-clock and call caps, receipt
    on stop.
38. Re-run command: reproduce any past experiment from its record
    alone (hashes + seed), producing a comparison record.
39. Tests: determinism check passes on a seeded computation; crash
    recorded; out-of-sandbox attempt refused.
40. The reproduction experiment, first full run, records committed.

## Section 5 — Discovery Engine: the cycle (41–50)

41. Cycle phases 1–7 implemented as a state machine over the cycle
    record, one transition = one ledger entry with its reason.
42. Phase gates: each phase names its required input records; a
    missing input blocks the transition and says which.
43. Human gates at the sourced positions (phases 9/10 per the design
    text): the cycle parks, writes a gate record, and resumes only
    on an explicit human decision record.
44. The source gap: where the cycle's source text is silent, the
    state machine carries an explicit UNIMPLEMENTED marker and the
    cycle routes around it or parks — never invents a step.
45. Cycle driver CLI: start, advance, status, park, resume.
46. Cycle budget: total actions and spend per cycle, receipt on stop.
47. Cycle recovery: kill the driver mid-phase, restart, the cycle
    resumes from its records with no duplicated phase.
48. Tests: gate refusal, human-gate park/resume, recovery resume,
    budget stop.
49. One full cycle on the reproduction target through phases 1–7,
    records committed.
50. Cycle report generator: the cycle's records → one readable page
    (claims with their ladder levels, nothing above level).

## Section 6 — Independent Verification (51–60)

51. Verifier isolation: the independent-verifier gets the plan and
    the inputs, never the generator's reasoning or the result.
52. Blind re-run: verifier re-executes from the experiment record
    alone, in a clean dir.
53. Comparison record: original vs verifier hashes and outcomes —
    agree / disagree / indeterminate, with the diff stated plainly.
54. Disagreement path: a disagree verdict caps the claim's ladder
    level and opens a dispute record; it never edits the original.
55. Verifier rotation: the verifying agent is never the agent that
    produced the result (enforced in code, tested).
56. Knowledge Repository write gate: only verifier-agreed results
    enter as confirmed; everything else enters as unconfirmed with
    its level, or not at all.
57. Repository schema: claims, experiments, cycles, sources —
    queryable by level, department, agent, date.
58. Repository reader CLI: show a claim's full provenance chain back
    to sources.
59. Tests: verifier cannot see generator reasoning (fixture proves
    it); disagree caps the level; unconfirmed write carries its cap.
60. The reproduction result through full verification, records
    committed either way the verdict lands.

## Section 7 — Hortus, the breeding engine (61–70)

61. Hortus interface audit: what the existing Hortus runtime exposes,
    written into the status file from the code, not the docs.
62. Breeding candidates as experiment variants: a variant is a plan
    delta with its own seed and record.
63. Variant generator job (hypothesis-generator + Hortus): propose
    variants of a plan, each with its falsifier intact.
64. Variant runner: variants execute through the Computational Lab
    path — same records, same budgets, no side door.
65. Selection record: which variant survived, the measured criterion,
    the pre-registered threshold — selection after results only
    against the registered rule.
66. Lineage record: parent plan → variants → survivor, hash-linked.
67. Dead-end preservation: failed variants stay in the Repository as
    negative results at their true level.
68. Tests: variant without falsifier rejected; selection against an
    unregistered rule refused; lineage chain verifies.
69. One breeding round on the reproduction experiment, records
    committed.
70. Hortus status: what the breeding engine can and cannot do today,
    one honest paragraph in the status file.

## Section 8 — The controlled MCP gateway (71–80)

71. Gateway allowlist: the lab's agents may call only named tools
    (the boss's own MCP servers: openalex, archive-org, open-library,
    gbif, wikidata, wikisource, ietf, federal-register, osv).
72. Call record: agent, tool, arguments hash, result hash, cost,
    timestamp — every call, no exceptions.
73. Gateway refusal: a non-allowlisted tool call fails and the
    refusal is recorded.
74. Per-agent tool scopes: literature may search; the runner may not
    browse; scopes enforced in the gateway, tested per agent.
75. Result quarantine: gateway results enter records as unconfirmed
    sources until pinned by the literature job's rules.
76. Gateway budget: calls per cycle capped, receipt on stop.
77. Offline mode: the cycle runs its deterministic parts with the
    gateway closed, and says so in its records.
78. Tests: refusal recorded; scope violation refused; quarantine
    respected.
79. Worked example: one literature pass through the real gateway,
    call records committed.
80. Gateway README inside the science-lab tree: tools, scopes, rules.

## Section 9 — Outputs the OS can show (81–90)

81. Lab session record export: the cycle's public record (claims +
    levels + verdicts) as one JSON the face can read.
82. Evidence-level display data: per claim, level, colour band, and
    the one-line basis — generated from records, never hand-written.
83. Review page data under `labs/`: the reproduction cycle rendered
    from its records (static, regenerated by command).
84. Molecule/specimen data check: the existing science-lab specimen
    records validate against the lab's source-record schema.
85. Department summary records: per department — cycles run, claims
    by level, disputes open.
86. Export honesty test: no exported artefact states a claim above
    its recorded level (automated scan of the exports).
87. Session archive: a finished cycle's full record bundle, hashed,
    one command to produce.
88. Status board data: counts only (cycles, experiments, claims by
    level) as JSON for any surface to read.
89. Regeneration drill: delete the exports, regenerate from records,
    byte-compare.
90. Section sign-off in the status file: every output named, its
    source records named.

## Section 10 — The demo cycle and the truth pass (91–100)

91. Full dress rehearsal: one complete cycle, fresh question in the
    reproduction's department, start to Repository write.
92. Timing record: wall-clock and model spend for the rehearsal,
    recorded honestly.
93. Failure drill: break one input mid-cycle; the cycle's behaviour
    is recorded (park, refuse, or fail loudly — never fake success).
94. Test sweep: the whole `tests/science-lab/` suite green from a
    clean checkout of your branch; output line in the status file.
95. Existing suites untouched: hortus tests and the agent tests still
    pass with your branch merged-ready (run them, record lines).
96. Claim audit of your own lane: every claim in your docs and
    exports → its record; anything unbacked is cut or levelled down.
97. SCIENCE_LAB_STATUS.md in the science-lab tree: built / stub /
    unimplemented per component, no adjectives without records.
98. README section for the lab in the science-lab tree: what it is,
    how a cycle runs, where the records live.
99. Branch tidy: status file complete through section 10, commits
    per section, branch ready for Pax's checkpoint merge.
100. Final line in the status file: what the Science Lab can do
     today, in one sentence, that every record behind it supports.
