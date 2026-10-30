# Lane: BUFFY — Volume lane. Runs on Freebuff (GLM).

You own: the material everyone else builds against — synthetic bus histories and fixtures with ground-truth manifests, eval data volume, docs, README upkeep, demo script drafts, regression checklists, and the build journal. Your fixtures are the contract: if a manifest says a history contains a stall, an engine that misses it has a bug, and an engine that invents one has a worse bug. Repetitive build-outs arrive from Pax; when in doubt, ask Pax, do not improvise scope.

**Your tasks: 60** (dependency order; ★ = critical path). Full context, architecture, and every other lane's tasks: MASTER_PLAN.md in the parent folder. Schedule: SCHEDULE.md. Demo: DEMO.md.
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
- **FND-021** [BUFFY] Create tests/fixtures/intel/ directory with fixture format README (JSONL bus exports + jobs list --json dumps)
  - Acceptance: README explains each fixture file; one sample fixture loads in a test
- **FND-022** [BUFFY] Build fixture: quiet morning (40 messages, 3 jobs all done, 4 nicks present) as bus export + jobs dump
  - Acceptance: Fixture validates against the format README schema check script
- **FND-023** [BUFFY] Build fixture: busy build day (480 messages, 22 jobs mixed status, 6 nicks) as bus export + jobs dump
  - Acceptance: Fixture loads via intel ingest in a smoke test; counts match fixture manifest
- **FND-024** [BUFFY] Build fixture: silent stall (worker claims job, heartbeats stop, no progress for 45 min of timestamps)
  - Acceptance: Fixture timestamps prove the gap; manifest documents the expected watchdog verdict
- **FND-025** [BUFFY] Build fixture: dead dependency (job B deps on job A; A blocked with reason, B waits)
  - Acceptance: Manifest states expected alert type; jobs dump parses
- **FND-026** [BUFFY] Build fixture: file collision (two claimed jobs whose files fields overlap on src/app.py)
  - Acceptance: Manifest states the overlapping path; both jobs parse via jobs list --json shape
- **FND-027** [BUFFY] Build fixture: spoof attempt (job with BAD HMAC signature in the dump) for watchdog/dispatch rejection tests
  - Acceptance: verify path returns BAD on the fixture job in a unit test
- **FND-028** [BUFFY] Write fixture generator script tests/fixtures/intel/make_fixture.py that regenerates the synthetic histories deterministically (seeded)
  - Acceptance: Two runs with same seed produce byte-identical fixture files (diff clean)

### BRF
- **BRF-031** [BUFFY] Author eval fixture brief-history A: three-day synthetic build with 5 decisions, 2 blocks, 1 stall, manifest of ground truth
  - Acceptance: Manifest lists every ground-truth fact with message indices
- **BRF-032** [BUFFY] Author eval fixture brief-history B: chaotic day (thread forks, edits, forwards, reactions) with ground-truth manifest
  - Acceptance: Manifest complete; fixture loads via ingest without error
- **BRF-033** [BUFFY] Author eval fixture brief-history C: overnight silence then burst (gap honesty test) with manifest
  - Acceptance: Manifest states the gap window the brief must name
- **BRF-034** [BUFFY] Write hallucination bait fixture: messages that mention jobs that do not exist in the jobs dump
  - Acceptance: Brief eval on bait fixture must not list the fake jobs; result logged
- **BRF-035** [BUFFY] Build a brief scoring helper script intel/evals/score_brief.py that checks mechanical rubric items (budget, sections, blocked verbatim)
  - Acceptance: Script runs on a stored brief + manifest and prints per-check results
- **BRF-036** [BUFFY] Generate 20 paraphrase variants of the same morning snapshot for prompt stability testing
  - Acceptance: Variants stored under intel/evals/variants/ with index file
- **BRF-037** [BUFFY] Write plain-English jargon blocklist (40+ terms) used by Hana's prompt checks
  - Acceptance: Blocklist file exists; scorer flags a brief containing 3 planted terms
- **BRF-038** [BUFFY] Transcribe three real (anonymized, Dale-approved only) historical bus days into fixture format — HELD until Dale approves using real history
  - Acceptance: Either fixtures exist with Dale's recorded approval, or task closed as not used; no real history touched without approval

### DSP
- **DSP-029** [BUFFY] Build dispatch fixture plans: golden plan JSON (4 jobs, diamond deps) + expected jobs list --json after posting
  - Acceptance: Fixture pair stored; integration test compares posted state to expected
- **DSP-030** [BUFFY] Build malformed plan pack: 10 broken JSON/schema variants each labeled with the error it must produce
  - Acceptance: Parser test iterates the pack; all 10 errors match labels
- **DSP-031** [BUFFY] Generate 30 synthetic goals across 6 categories for dispatch volume testing, with rough shape notes
  - Acceptance: Goals file complete; a batch dry-run log shows zero crashes
- **DSP-032** [BUFFY] Write dispatch dry-run batch runner intel/evals/run_dispatch_batch.py (goals in, plan summaries + guard hits out)
  - Acceptance: Runner produces a readable report for the 30-goal batch
- **DSP-033** [BUFFY] Create file-ownership overlap scenario pack (5 overlapping plan variants, expected verdicts)
  - Acceptance: Guard test results match expected verdicts on all 5
- **DSP-034** [BUFFY] Draft demo goal alternates: 2 backup plain-English goals in case the primary demo goal's plan destabilizes
  - Acceptance: Alternates dry-run clean and are saved with the demo script assets
- **DSP-035** [BUFFY] Compile dispatch FAQ from eval failures (why was my plan rejected) for README appendix
  - Acceptance: FAQ covers every guard with a plain one-line fix suggestion
- **DSP-036** [BUFFY] Keep a dispatch regression log: every prompt version x golden set result, dated
  - Acceptance: Log current through the final prompt version before demo freeze

### WDG
- **WDG-040** [BUFFY] Author watchdog fixture: heartbeat-alive-no-progress timeline (progress-stall case) with manifest
  - Acceptance: Manifest states expected alert kind and earliest correct fire time
- **WDG-041** [BUFFY] Author watchdog fixture: lease cliff (heartbeat stops 4 min before lease expiry) with manifest
  - Acceptance: Manifest states warning-then-requeue expectation
- **WDG-042** [BUFFY] Author watchdog fixture: double-claim race attempt (two claims, one winner) — watchdog must NOT alert
  - Acceptance: Negative case passes in Milo's suite
- **WDG-043** [BUFFY] Author watchdog fixture: healthy busy crew (12 jobs, steady progress) — zero critical alerts expected
  - Acceptance: Watchdog over fixture yields zero criticals in tuning run
- **WDG-044** [BUFFY] Generate 7 days of synthetic heartbeat/progress logs for threshold tuning volume
  - Acceptance: Logs generated deterministically; summary stats file included
- **WDG-045** [BUFFY] Write drill narration cue cards for Dale (what to say at each drill moment in the demo)
  - Acceptance: Cue cards saved in demo-assets/ matching DEMO.md shots
- **WDG-046** [BUFFY] Maintain the alert-copy deck: every detector's explanation/fix text in one reviewable file for Dale's approval
  - Acceptance: Deck file complete; Dale approval task references it

### DSH
- **DSH-042** [BUFFY] Write panel content fixtures: example brief (long), example alerts set (all severities), example plan preview — as static JSON for Rowan
  - Acceptance: Fixtures validate against Pax's payload contract
- **DSH-043** [BUFFY] Write empty-state and error-state copy for every panel (plain, short, no jargon)
  - Acceptance: Copy deck approved by Rowan; strings match implementation
- **DSH-044** [BUFFY] Produce dashboard screenshot QA: compare Rowan's renders against the copy deck and fixture data, file mismatches
  - Acceptance: QA notes filed per batch; mismatches become tasks or fixes
- **DSH-045** [BUFFY] Draft viewer help text: a 'What am I looking at?' overlay explaining mission control to a judge in 6 lines
  - Acceptance: Overlay copy in spec; Dale approves wording
- **DSH-046** [BUFFY] Test dashboard on a slow connection profile (throttled) and record behavior notes
  - Acceptance: Notes filed; any panel that never renders gets a task

### INT
- **INT-013** [BUFFY] Maintain the master regression checklist (existing features untouched: rooms, DMs, jobs, MOS flow, viewer panels) run after each integration batch
  - Acceptance: Checklist results logged per batch in intel/evals/regression-log.md
- **INT-014** [BUFFY] Build the demo-day state pack: seeded Redis export/fixtures that recreate the exact demo scenario on any machine ★
  - Acceptance: A fresh checkout + pack reproduces the demo state (verified by Pax run)
- **INT-015** [BUFFY] Write the demo failover card: if live dispatch misbehaves, the exact clicks/commands to the recorded fallback
  - Acceptance: Card printed/saved with DEMO.md; rehearsed once
- **INT-016** [BUFFY] Cross-check every number quoted in submission copy against a measured result (test counts, timings, costs)
  - Acceptance: Numbers sheet in submission-assets/ with source per number
- **INT-017** [BUFFY] Run a fresh-eyes pass: follow ONLY the README to run brief + dispatch + watchdog on fixtures; log every gap
  - Acceptance: Gap log filed; gaps become DOC tasks or fixes before freeze
- **INT-018** [BUFFY] Prepare judge Q&A cheat sheet: 15 likely questions with one-line factual answers (no hype)
  - Acceptance: Sheet reviewed by Pax; every answer traceable to a doc or measurement
- **INT-019** [BUFFY] Keep the build journal: daily dated entries of what landed, per lane, for the submission story
  - Acceptance: Journal current within 24h at all times during the window

### DEM
- **DEM-019** [BUFFY] Write the demo script v1 (Dale's lines, click track, expected screen states per beat) into DEMO.md draft section ★
  - Acceptance: Script v1 complete; Pax timings pass against it
- **DEM-020** [BUFFY] Write the demo script v2 from rehearsal 1 notes (cut dead air, move the brief earlier)
  - Acceptance: v2 diff summary logged; DEMO.md updated
- **DEM-021** [BUFFY] Author judge-facing one-pager (PDF-ready markdown): problem, three features, what is real today, links
  - Acceptance: One-pager in submission-assets/; Dale approves
- **DEM-022** [BUFFY] Write alt text / captions for submission screenshots and video (accessibility + muted autoplay viewing)
  - Acceptance: Captions file covers every asset in the manifest
- **DEM-023** [BUFFY] Prepare the social/announcement draft announcing the submission (Dale posts himself; draft only, nothing auto-posted)
  - Acceptance: Draft saved; no post made by any agent
- **DEM-024** [BUFFY] Compile the credits page: crew, tools, licenses (SAM stretch, audio, fonts if any)
  - Acceptance: Credits in submission-assets/ and repo README appendix

### DOC
- **DOC-001** [BUFFY] Write intel/README.md master structure (overview, quickstart, keys, wire formats, links to sections) on Day 1 so lanes fill sections as they land ★
  - Acceptance: README skeleton committed Day 1 with section owners named
- **DOC-002** [BUFFY] Keep the main muse-relay README's file table updated with intel/ entries and the intel.py CLI row
  - Acceptance: README diff shows intel rows; no existing rows broken
- **DOC-003** [BUFFY] Write the 10-minute quickstart: clone, fake Redis, run a brief, run a dispatch dry-run, fire the kill drill ★
  - Acceptance: Pax runs it cold and times it; gaps fixed
- **DOC-004** [BUFFY] Write architecture explainer (one page, one diagram in ASCII/mermaid): bus, jobs, MOS, intel layer, viewer
  - Acceptance: Explainer in docs/relay-intelligence.md; Pax fact-checks every claim against code
- **DOC-005** [BUFFY] Maintain the glossary (bus, room, claim, lease, brief, alert, plan, drill) in docs for judge-facing clarity
  - Acceptance: Glossary complete; dashboard help overlay reuses it
- **DOC-006** [BUFFY] Write CHANGELOG entries for the hackathon window in repo style
  - Acceptance: CHANGELOG current at submission
- **DOC-007** [BUFFY] Proof pass on all judge-facing text: no em dashes in Dale-facing copy per his standing rule, no invented numbers
  - Acceptance: Scan script output clean; numbers sheet cross-check referenced
- **DOC-008** [BUFFY] Document the SAM 3.1 stretch honestly as stretch in all copy (never described as shipped unless it ships)
  - Acceptance: Copy scan shows stretch labeled everywhere it appears
- **DOC-009** [BUFFY] Write the post-hackathon roadmap note (what v2 would do: multi-room briefs, learned thresholds, richer plans)
  - Acceptance: Roadmap note in docs/; clearly marked future, not current
- **DOC-010** [BUFFY] Archive the build: export the build room history and journal into the hackathon folder at the end
  - Acceptance: Export files exist; archive listed in the final report

### STR
- **STR-004** [BUFFY] Build SAM eval set: 20 bus-shared screenshots with ground-truth visual check labels (build ok / build broken / unclear)
  - Acceptance: Set + labels complete; sources are the crew's own screenshots only

## Meta OS — BUFFY (added 2026-10-22, Dale's OS decision)

Your slice of the Meta OS workstream (build script volume, package lists, docs). Full spec: ../META_OS.md. The OS is the chassis; the Spark critical path in the sections above always wins a scheduling fight. Image content freeze: Nov 2 12:00 ET (SCHEDULE.md).

- **OS-023** [BUFFY] Package rationale pass: document every line of os/packages.txt in os/PACKAGES.md (what it is, why it ships, size)
  - Acceptance: Every manifest line has an entry; no package in the image is unexplained
- **OS-024** [BUFFY] Preseed archive: collect the final preseed.cfg and late_command scripts into os/preseed/ with a comment block explaining each section
  - Acceptance: Archived files match the pipeline inputs byte for byte; a cold reader can follow each block
- **OS-025** [BUFFY] Visual identity set in os/assets/: Plymouth boot splash config, wallpaper, login banner and motd, kiosk icons — Meta OS branding, no stock Debian branding on the boot path
  - Acceptance: Assets present and referenced by the build; the boot test screenshot shows Meta OS identity end to end
- **OS-026** [BUFFY] Boot fixture pack: seed script in os/fixtures/ that loads the standard crew state for image tests (jobs in 4 states, presence for 4 nicks, one stale lease)
  - Acceptance: Seeding a fresh image reproduces exactly the state the boot test and OS-036 self-check assert on
- **OS-027** [BUFFY] os/README.md: build, flash (dd/Etcher), and first-boot instructions a judge can follow cold
  - Acceptance: Pax follows it cold to a booted VM without asking a single question; gaps fixed in the doc, not by word of mouth
- **OS-028** [BUFFY] Spec sync duty: keep the META_OS.md service table and boot order identical to the units as built
  - Acceptance: Spec table matches systemctl list-dependencies relay.target output on the current test image
- **OS-029** [BUFFY] Image size budget sheet os/SIZES.md: record image size per build, flag any growth over 10 percent between builds
  - Acceptance: Sheet current for the last three builds; every flag has a note or a task
- **OS-030** [BUFFY] os/CHANGELOG.md: one entry per produced image (base, pinned commit, package delta, known issues)
  - Acceptance: One entry per image, no gaps, newest first
- **OS-031** [BUFFY] Field kit checklist os/FIELD-KIT.md: bootable USB with the fallback ISO, VM snapshot export, spare cables, printed failover card
  - Acceptance: Checklist written; every physical item confirmed by Pax before demo freeze
- **OS-032** [BUFFY] Build archive index os/builds/INDEX.md: every release candidate image with sha256, date, builder, and build log link
  - Acceptance: Index lists each RC; checksums match the files; links resolve

**Working-system additions (vision upgrade, Dale 2026-10-22) — packages and docs:**

- **OS-063** [BUFFY] Working-system package pass: every packages.txt addition for the gateway, the Muse Code CLI, and driver runtimes documented in os/PACKAGES.md with rationale; sizes into os/SIZES.md
  - Acceptance: Every new manifest line has a PACKAGES.md entry; SIZES.md reflects the grown image
- **OS-064** [BUFFY] Skills loader fixture pack + docs: seed skill folders for image tests, and the loader contract documented as a section of os/README.md (what mounting means, where skills land, how a process opts in)
  - Acceptance: Fixture skills mount in the OS-065 test; a cold reader can mount one from the README alone

**Phase B — post-hackathon daily-driver track [B]:**

- **OS-069** [BUFFY] [B] meta-pkg package flow v1: apt-style install/list/remove for MCP servers (over the gateway) and skill apps (over the skills repos) — meta-pkg concept doc plus working commands
  - Acceptance: meta-pkg install + remove round-trips one MCP server and one skill on a live Meta OS machine; state survives reboot
- **OS-070** [BUFFY] [B] Package catalog generation: a browsable index of installable MCPs and skills generated from awesome-servers + skills-2 (name, one-liner, size, source)
  - Acceptance: Catalog regenerates from source repos with zero hand edits; every entry resolves to a real package

**Depth — the four system services (Dale 2026-10-22; spec: ../META_OS.md, "Depth: the four system services"):**

- **OS-087** [BUFFY] [B] Memory compaction: scheduled compaction of the journaled store — settled decisions pinned, superseded entries folded, full version history retained and restorable
  - Acceptance: A compacted store restores any prior version on demand; the boot brief's settled-decisions line is unchanged across a compaction
- **OS-089** [BUFFY] [B] Artifact retention/dedup: retention policy for the artifact store (age/size rules per job class) plus content-hash dedup so identical outputs are stored once and referenced many times
  - Acceptance: Policy doc committed; a duplicate-artifact fixture run stores one copy; expired artifacts are listed before any deletion, never silently dropped

- **OS-099** [BUFFY] The completion drill, end to end: one real order from Dale's phone, the phone then ignored; mid-job, agents are rotated out and killed (process killed, session ended) — the work still completes through pickup and self-repair, and exactly one done push arrives; includes the machine-off hour: an order queued in the cloud while the machine is down is picked up and worked at boot
  - Acceptance: Drill report filed: the job completed with zero Dale contact after the order; every agent death shows in the journal with a pickup after it; the push count for the whole run is one (done) — and the offline order completed after boot with zero loss, zero duplicates claimed
- **OS-104** [BUFFY] Mind-image versioning + changelog discipline: every image change is a version bump with a changelog entry naming what changed and why (skill revised, instruction tightened, brief field added); no unversioned edits to a bundle any process has launched from
  - Acceptance: Changelog present and complete for the fixture images; an attempted unversioned edit is caught by the OS-105 harness's bundle hash check and fails the run loudly
- **OS-105** [BUFFY] A/B eval harness: a fixed suite of small jobs, runnable against two mind-image versions end to end, recording completion time and acceptance result per job per version, side by side
  - Acceptance: Harness runs the full suite against two fixture versions unattended and emits the comparison table; a tampered or unversioned bundle aborts the run instead of producing numbers
- **OS-113** [BUFFY] Federation drill: two machines, one room — a signed job is posted from machine A, claimed and completed by an agent on machine B, acceptance verified by A's overseer, and the completion closes under the completion contract with exactly one done-push to the order's origin
  - Acceptance: Drill log shows the full path (post on A → claim on B → artifacts deposited → acceptance pass → one done-push) with machine names at each hop; run twice, both green, before image freeze

- **OS-123** [BUFFY] The hands-free drill: Dale posts one order and touches nothing afterwards — no phone, no pokes, no manual starts. A sleeping agent on another machine/runtime is woken by the bell (OS-118/OS-119), completes the job under the completion contract, and exactly one done-push comes back
  - Acceptance: The drill log proves the negative space: zero Dale actions after the order (no session starts, no nudges from him), the wake event precedes the agent's first action, acceptance passes, exactly one done-push total; run twice, both green, before image freeze

- **OS-126** [BUFFY] The plug-pull drill: a job is in flight on the test image; the machine's power is cut mid-work (hard power cut / VM kill — not a shutdown); power is restored and nobody touches anything after the cut. The crew self-relaunches from its enabled services, the lease sweep expires the dead claim, the job resumes from its deposited baton state and completes, and exactly one done-push fires — Milo verifies the lease-sweep and resume evidence (with OS-129) rather than the drill grading itself ★
  - Acceptance: Drill log proves the negative space: zero human touches after the power cut (no logins, no manual service starts, no relaunches); the boot brief's recovered count (OS-127) equals the jobs the sweep released; the resumed job's record shows continuation from deposited progress with no repeated work; exactly one done-push total; run twice, both green, on the final RC image before the image freeze

---
BUFFY total: 82 tasks.
