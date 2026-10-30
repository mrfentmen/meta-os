# Lane: HANA — Briefings lane. Bus nick: mute.

You own: the briefing engine — ingestion shaping, prompts, brief formats, budgets, fallback, scheduling, and the eval sets that prove brief quality. You also own the language quality of dispatch: golden goals, adversarial goals, spec and acceptance standards, plan summaries. Your ground rule: a brief never invents a fact. Every claim traces to the snapshot or it does not ship.

**Your tasks: 50** (dependency order; ★ = critical path). Full context, architecture, and every other lane's tasks: MASTER_PLAN.md in the parent folder. Schedule: SCHEDULE.md. Demo: DEMO.md.
## Rules of the road (all lanes)

- Repo: `~/workspace/repos/meta-os` (GitHub Mrfentmen/meta-os). Read `INSTANCES.md` and `README.md` before your first commit.
- Statuses, only these four: VERIFIED / CODE-INSPECTED / UNIMPLEMENTED / BLOCKED. If you say something works, you ran the check.
- NEVER post to the bus without Dale's word. If Dale approves build traffic, it goes in the build room only (see FND-001/GOV-002 in MASTER_PLAN.md). Main bus is read-only for this build unless Dale says otherwise.
- Secrets (Upstash token, job keyring, Spark key) never go on the bus, in a spec, in a commit, or in a fixture. chmod 600 files only.
- Specs and long content never ride bus messages; they live in Redis hashes/files. Bus lines are announcements only.
- Tests: new code gets tests on tests/fake_redis.py patterns. The existing suite (326 test methods at plan time) must stay green; a red suite blocks merges, not just your lane.
- Git workflow: RULED by Dale 2026-10-24 (GOV-003): the build lives in a NEW repo, Mrfentmen/meta-os, with muse-relay merged in as the base layer, and all work happens in the new repo. Crew batches land as single commits on main of meta-os. The inherited relay README's feature-branch and overseer-merge wording describes the relay base's own job flow, not this repo's crew workflow, and does not override the ruling. (INT-012, 2026-10-27.)
- Viewer deploy target: Cloudflare Pages (muse-relay-live). bus.html and index.html are identical files; keep them identical.
- Handoffs: when your output feeds another lane, the handoff is a file + a task id in the build journal, not a chat message that can scroll away.
- Demo freezes: feature freeze Nov 2 21:00 ET, demo freeze Nov 3 21:00 ET. After a freeze, changes need Pax + Dale sign-off.

## Where things live

- Plan: ~/workspace/hackathon/relay-intelligence/MASTER_PLAN.md (full task list, architecture, decisions)
- Schedule: ~/workspace/hackathon/relay-intelligence/SCHEDULE.md
- Demo: ~/workspace/hackathon/relay-intelligence/DEMO.md
- New code: intel/ and intel.py in the meta-os repo; prompts in intel/prompts/; evals in intel/evals/; fixtures in tests/fixtures/intel/

## Your tasks

### FND
- **FND-032** [HANA] Define brief record schema with Pax (fields: room, generated_at, kind morning|onjoin|ondemand, sections, source_window, model, spend_id) ★
  - Acceptance: Schema written in intel/README.md; brief.py validates records against it in a test
- **FND-033** [HANA] Inventory existing text sources for briefs: digest.py output, store.py JSONL, jobs list --json, presence.py, mos capabilities — map each to a brief section in intel/notes/hana-source-map.md
  - Acceptance: Source map covers all five sources with the exact command/function producing each
- **FND-034** [HANA] Set brief length budgets per kind (morning <= 220 words, onjoin <= 150, ondemand <= 300) as constants in intel/brief.py
  - Acceptance: Constants exist; a test fails a generated brief that exceeds budget

### BRF
- **BRF-001** [HANA] Write the morning brief prompt v1 in intel/prompts/brief_morning.md: sections Decisions, In flight, Owners, Blocked and why, Watch items ★
  - Acceptance: Prompt file exists; renders with fixture snapshot without unfilled placeholders
- **BRF-002** [HANA] Write the on-join brief prompt v1 in intel/prompts/brief_onjoin.md: what this crew is building, your likely lane, what is blocked, who to ask ★
  - Acceptance: Prompt renders on busy-build fixture; reading level plain English (no jargon list hits)
- **BRF-003** [HANA] Write the on-demand brief prompt (any room, any window) reusing morning sections with window parameter
  - Acceptance: Same snapshot with two windows yields two different source_window values and non-identical text
- **BRF-004** [HANA] Implement brief.py section extractor: pull decisions (DONE:/BLOCKED:/decision markers + Spark pass) from snapshot into structured section data ★
  - Acceptance: Extractor on busy fixture returns decisions list containing the 3 planted decisions from the manifest
- **BRF-005** [HANA] Implement brief.py blocked extractor: every blocked job with its blocked reason verbatim, never paraphrased away ★
  - Acceptance: Blocked reasons in output match fixture job notes character-for-character
- **BRF-006** [HANA] Implement brief.py owners extractor: claimed jobs mapped claim nick -> title -> last progress age
  - Acceptance: Owners section on busy fixture matches manifest owner table exactly
- **BRF-007** [HANA] Implement brief composer: Spark call with section data, word-budget enforcement, plain-language rewrite pass if over budget ★
  - Acceptance: Composed brief on fixture is within budget and contains all four required sections
- **BRF-008** [HANA] Add brief fallback: if Spark call fails, emit a template brief from extractors alone (no LLM) marked TEMPLATE ★
  - Acceptance: Killing transport in test still yields a readable brief with TEMPLATE marker
- **BRF-009** [HANA] Store every generated brief via intel/store.py with source_window and spend id; add brief.py list/show CLI through intel.py brief --list/--show
  - Acceptance: Generated brief retrievable by id; list shows kind + generated_at
- **BRF-010** [HANA] Post brief announcements to the build room as BRIEF:<id> one-liners (announcement only, full text in Redis) — only after Dale's room/posting decision
  - Acceptance: Announcement line matches frozen wire format in intel/README.md (or held, if Dale has not approved posting)
- **BRF-011** [HANA] Build morning scheduling: timecapsule-style registration so a 08:00 ET brief generates daily during the build window via intel.py brief --morning --room <build room>
  - Acceptance: Dry-run at a fake clock time produces the brief; schedule entry documented in SCHEDULE ops note
- **BRF-012** [HANA] Handle empty-room and new-room briefs: no history yields a short 'nothing yet' brief, never an error or invented content ★
  - Acceptance: Empty fixture produces brief containing 'no activity yet' and zero fabricated job names (checked against manifest)
- **BRF-013** [HANA] Handle trimmed-history honesty: when store window starts mid-story, brief opens with the window it actually covers
  - Acceptance: Brief on truncated fixture states its start point; eval rubric item passes
- **BRF-014** [HANA] Add brief redaction pass: strip anything matching token/key patterns (reuse secret-pattern list from jobs signing docs) before posting or storing ★
  - Acceptance: Fixture with planted fake token yields brief with the token absent and a [redacted] marker
- **BRF-015** [HANA] Write eval rubric intel/evals/brief_rubric.md: 8 checks (all blocked named, owners right, no invented facts, within budget, plain English, window stated, decisions real, alerts linked) ★
  - Acceptance: Rubric file complete; every check is yes/no answerable from a brief + fixture manifest
- **BRF-016** [HANA] Score morning brief on quiet fixture against rubric; log results in intel/evals/log.md
  - Acceptance: Log entry exists with per-check pass/fail and brief id
- **BRF-017** [HANA] Score morning brief on busy fixture against rubric; fix top failure before scoring again
  - Acceptance: Second log entry shows the fixed check passing
- **BRF-018** [HANA] Score on-join brief on busy fixture against rubric (fresh-agent persona: could you start work from this alone?)
  - Acceptance: Log entry records a cold-read verdict by a lane member who did not write the brief
- **BRF-019** [HANA] Tune prompts to v2 from eval failures only (no vibes edits); keep v1 files for diffing
  - Acceptance: v2 prompt files exist; eval log shows which failure each v2 change targets
- **BRF-020** [HANA] Add brief staleness label: briefs older than 2 hours render with age in dashboard payload (generated_at + age_seconds fields)
  - Acceptance: Payload test asserts age_seconds grows with fake clock
- **BRF-021** [HANA] Add multilingual safety: briefs stay English even when bus chatter contains other languages (prompt instruction + eval case)
  - Acceptance: Fixture with mixed-language lines yields English brief in eval run
- **BRF-022** [HANA] Write brief section: Watch items — pull open watchdog alerts into the brief by reference (alert ids + one-line summaries) ★
  - Acceptance: Brief on stall fixture names the stall alert id produced by Milo's watchdog on same fixture
- **BRF-023** [HANA] Cap brief source window (default last 500 messages or 24h, whichever smaller) and record the cap in the brief record
  - Acceptance: Record on busy fixture shows window cap values; ingest respects them in test
- **BRF-024** [HANA] Add intel.py brief --room --since flags for ad hoc windows used in demo rehearsal
  - Acceptance: --since 2h run on fixture produces window-scoped brief
- **BRF-025** [HANA] Draft the exact morning brief Dale sees on demo day (scripted from the demo fixture, hand-checked line by line)
  - Acceptance: Draft saved at hackathon/relay-intelligence/demo-assets/morning-brief-demo.md; every factual claim traces to the demo fixture manifest
- **BRF-026** [HANA] Write failure copy: three canned one-liners for brief unavailable / Spark down / no data, used by dashboard and CLI
  - Acceptance: Copy lives in intel/brief.py constants; tests assert each surfaces in its failure case
- **BRF-027** [HANA] Verify brief generation cost on busy fixture stays inside the per-brief budget cap; log actuals to spend ledger
  - Acceptance: Spend ledger entry for the run is under cap; number recorded in eval log
- **BRF-028** [HANA] Add brief regeneration guard: same room+window requested twice inside 5 min returns the stored brief instead of a new Spark call
  - Acceptance: Second call in test returns identical brief id; spend ledger gains no entry
- **BRF-029** [HANA] Prepare on-join brief trigger: presence of a nick with no prior messages in room triggers an offered (not auto-posted) on-join brief
  - Acceptance: Fixture with new nick yields offer record; no brief generated until invoked
- **BRF-030** [HANA] Document briefing engine in intel/README.md section: inputs, prompts, budgets, fallback, eval pointer
  - Acceptance: README section complete; a cold reader (Buffy) confirms she can run a brief from it alone

### DSP
- **DSP-021** [HANA] Write dispatch goal-elicitation microcopy: the three clarifying questions Spark asks when a goal is too vague (scope, files hint, done definition)
  - Acceptance: Microcopy in prompt file; vague-goal fixture triggers exactly these questions and posts nothing
- **DSP-022** [HANA] Author 12 golden goals with expected plan shapes (job count range, must-own files, must-have deps) in intel/evals/dispatch_golden.md ★
  - Acceptance: Each golden goal dry-runs to a plan inside its expected shape; results logged
- **DSP-023** [HANA] Author 6 adversarial goals (contradictory, file-collision by design, impossible dep, secret-looking content, huge scope, empty) with expected guard behavior
  - Acceptance: Each adversarial goal triggers its documented guard; none posts jobs
- **DSP-024** [HANA] Tune dispatch prompt to v2 from golden/adversarial failures; keep v1 for diff
  - Acceptance: v2 exists; eval log ties each change to a failing case that then passes
- **DSP-025** [HANA] Write plan summary style: one plain-English paragraph per plan for the dashboard (what will happen, in what order, who likely claims)
  - Acceptance: Summary generator produces paragraph covering all jobs in golden plan 1; human check logged
- **DSP-026** [HANA] Define spec-writing standard for generated specs (goal, context, files, steps, out-of-scope) as prompt section
  - Acceptance: Generated specs in golden runs contain all five parts (scorer-checked)
- **DSP-027** [HANA] Define acceptance-line standard: every job gets at least one machine-checkable accept line in mos formats ★
  - Acceptance: Scorer confirms 100% of golden-plan jobs carry >=1 parseable accept line
- **DSP-028** [HANA] Review generated specs for secret leakage and credential-shaped strings; add prompt ban + parser reject
  - Acceptance: Adversarial goal containing a fake key is rejected at parse with secret warning

### INT
- **INT-024** [HANA] Brief integration: briefs generated during e2e runs scored against rubric the same day
  - Acceptance: Scores appended to eval log for e2e brief ids
- **INT-025** [HANA] Verify brief/dashboard consistency: brief panel shows the same brief text the CLI shows for the same id
  - Acceptance: Side-by-side check logged for 3 brief ids
- **INT-026** [HANA] Write the 'known limits' brief section honestly (what briefs cannot see: DM rooms unless polled, trimmed history)
  - Acceptance: Limits text appears in README and submission notes verbatim
- **INT-027** [HANA] Cold-start test: a lane member who skipped a day uses only the morning brief to resume work; log what they missed
  - Acceptance: Cold-start log names gaps; gaps fixed or documented as limits

### DOC
- **DOC-011** [HANA] Write the prompts explainer: how the brief and dispatch prompts work, with v1->v2 change rationale
  - Acceptance: Explainer in intel/prompts/README.md
- **DOC-012** [HANA] Write eval methodology note (fixtures, manifests, rubric, how scores were produced) for judges who ask 'how do you know it works'
  - Acceptance: Note in intel/evals/README.md with links to logs
- **DOC-013** [HANA] Document brief limitations honestly (window caps, template fallback, no DM visibility by default)
  - Acceptance: Limitations section in intel/README.md
- **DOC-014** [HANA] Write example briefs gallery: 3 real generated briefs (quiet, busy, stall) with one-line annotations
  - Acceptance: Gallery in docs/ using fixture outputs only

### STR
- **STR-002** [HANA] Add screenshot digest to brief payload: latest build screenshots shared over the bus listed with timestamps for SAM pass
  - Acceptance: Brief record gains screenshot refs on fixture with --img posts

## Meta OS — HANA (added 2026-10-22, Dale's OS decision)

Your slice of the Meta OS workstream (the boot brief at startup). Full spec: ../META_OS.md. The OS is the chassis; the Spark critical path in the sections above always wins a scheduling fight. Image content freeze: Nov 2 12:00 ET (SCHEDULE.md).

- **OS-048** [HANA] Boot brief spec: the first brief extends the morning brief format with carried-over state — overnight decisions, jobs in flight at shutdown, what the watchdog saw during boot — not a new format
  - Acceptance: Spec section written beside the brief prompts plus one hand-checked example generated from fixture state
- **OS-049** [HANA] systemd unit relay-brief.service: a oneshot after relay-ready that generates the boot brief (Spark, with the BRF-008 template fallback) into the brief store
  - Acceptance: A fresh brief exists within 60s of relay-ready on the test image; the fallback path is proven with Spark blocked
- **OS-050** [HANA] Cold-start honesty rule: the boot brief states its data window (bus history since <ts>, previous session digest) and never implies history the machine does not have
  - Acceptance: The rule is in the prompt and the eval rubric; an empty-history fixture produces a brief that says the window is empty
- **OS-051** [HANA] Previous-session digest: the boot brief opens with a one-line digest of the prior session from store.py JSONL (last brief time, jobs completed, open threads)
  - Acceptance: Digest line present and correct across a reboot in the boot test
- **OS-052** [HANA] Boot brief eval set: three seeded shutdown states (clean, mid-job, post-crash) each scored against the brief rubric
  - Acceptance: Three of three briefs meet the BRF-016 quality bar; any failure is filed as a prompt fix task, not hand-waved

**Working-system additions (vision upgrade, Dale 2026-10-22) — the brief knows the machine:**

- **OS-062** [HANA] Boot brief: drivers + tools + apps line — the boot brief states which agent drivers are available, that the MCP gateway is healthy, and which skill apps are mounted, each in one line from live state
  - Acceptance: Lines present and correct on the test image; with the gateway down the brief says so instead of omitting the line (OS-050 honesty rule)

**Phase B — post-hackathon daily-driver track [B]:**

- **OS-075** [HANA] [B] Dale's daily brief: the morning brief becomes Dale's actual daily brief on the desktop session — overnight crew results, today's queue, what needs his word — format tuned from real use
  - Acceptance: Two weeks of daily briefs generated on the daily machine; format changes from Dale's feedback are in the prompt history

**Depth — the four system services (Dale 2026-10-22; spec: ../META_OS.md, "Depth: the four system services"):**

- **OS-079** [HANA] Brief surfaces memory + budget: the boot brief (and morning brief) opens with settled decisions pulled from the memory service instead of re-deriving them, and carries one spend-vs-budget line per lane from the budget config (OS-085)
  - Acceptance: Brief on fixture state names the planted settled decision verbatim from memory and shows spend vs budget per lane; with the memory service down the brief says so (OS-050 honesty rule)
- **OS-092** [HANA] [B] Memory-aware daily brief depth: the daily brief (OS-075) surfaces long-term memory — decisions aging out, commitments made weeks ago that are due, context a fresh agent would miss — drawn from the memory service, not re-derived from raw history
  - Acceptance: Two weeks into daily use, a brief names one aged commitment correctly from memory with its original date; nothing surfaced that memory does not contain

- **OS-097** [HANA] The two pushes: the done push fires only when the overseer closes a job on passed acceptance checks — "All done" plus the plain-English summary of what was built and what was verified — and the blocked push carries the exact question a parked job is waiting on; no third push type exists ★
  - Acceptance: A completed job produces exactly one push whose summary matches the artifact record; a parked job produces exactly one blocked push naming the decision in plain English; a job closed without passing its checks produces no done push
- **OS-103** [HANA] Environment brief generator: at launch, snapshot the agent's surroundings — repo state, bus state, who is working on what, budget remaining — and render it as the bundle's information layer, in the brief's plain-English standard
  - Acceptance: A generated brief names the repo's current state, the live jobs and their owners, and the lane's budget remaining, all matching the sources at generation time; stale fields are labeled with their age, never silently presented as current
- **OS-117** [HANA] [B] Crew-of-crews brief: the morning brief gains a federation section — what each joined machine's crew did, cross-machine jobs and their state, trust events (joins, refusals) overnight — in the brief's plain-English standard, so Dale reads one brief for every machine he runs
  - Acceptance: A generated brief over a two-machine fixture window names both machines' completions and any trust refusal, matching the room record; a single-machine brief renders the section absent, not empty-padded

- **OS-127** [HANA] Boot recovery report line: the boot brief gains one line — in-flight jobs recovered at this boot: the count, the job titles, and where each resumed from (baton state at which step) — reconciled against the lease sweep so a job that vanished silently can never produce a clean line; the line is also boot checklist item 13 in META_OS.md
  - Acceptance: After an unclean shutdown in the OS-126 drill, the boot brief names the recovered count and it matches the sweep record exactly; after a clean shutdown the line reads zero recovered, plainly; a fixture job whose record is corrupted produces a brief that says recovery was incomplete and names the job (OS-050 honesty rule) instead of a false all-clear

---
HANA total: 63 tasks.
