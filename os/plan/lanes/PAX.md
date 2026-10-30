# Lane: PAX — Coordinator / integrator. Bus nick: pax.

You own: intel core + Spark client, jobs.py extensions, the dispatch engine, all integration and QA gates, the demo build and rehearsal, and the submission package. You are the only lane that merges the whole picture: if two lanes disagree on a payload or format, you freeze the decision in intel/README.md and tell both lanes. You run hackathon/check.sh before every integration batch and you personally run all three watchdog drills before rehearsal week.

**Your tasks: 77** (dependency order; ★ = critical path). Full context, architecture, and every other lane's tasks: MASTER_PLAN.md in the parent folder. Schedule: SCHEDULE.md. Demo: DEMO.md.
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
- **FND-002** [PAX] Create the build room and post nothing until Dale's room decision lands; verify room appears in roomdir via a local poll with a throwaway nick only if Dale approves ★
  - Acceptance: roomdir listing or written hold recorded; zero unauthorized bus posts
- **FND-003** [PAX] Create intel/ package skeleton in muse-relay (intel/__init__.py, intel/spark_client.py, intel/ingest.py, intel/brief.py, intel/dispatch.py, intel/watchdog.py, intel/alerts.py, intel/store.py) with py_compile clean ★
  - Acceptance: python3 -m py_compile intel/*.py exits 0; package imports with no side effects
- **FND-004** [PAX] Define intel Redis key layout in intel/store.py: muse-bus:intel:brief:<room>:<ts>, muse-bus:intel:alert:<id>, muse-bus:intel:dispatch:<id>, muse-bus:intel:wd:<nick> — document in module docstring ★
  - Acceptance: Docstring lists every key, type, TTL; tests/test_intel_store.py round-trips each key on fake_redis
- **FND-005** [PAX] Build Spark client interface in intel/spark_client.py: complete(prompt, system=, max_tokens=) with pluggable transport (HTTP transport + FakeTransport for tests) ★
  - Acceptance: FakeTransport returns canned text in tests; HTTP transport reads endpoint/key from env only, never prints them
- **FND-006** [PAX] Add Spark client retry policy: 2 retries with backoff on 429/5xx, hard timeout, total budget cap per call logged to stderr
  - Acceptance: Unit tests simulate 429 then 200 and permanent 500; budget cap stops third call in test
- **FND-007** [PAX] Add Spark spend ledger: every call appends {ts, lane_feature, tokens_in, tokens_out, est_cost} to muse-bus:intel:spend list
  - Acceptance: Ledger entry appears after a FakeTransport call in test; running total readable via intel/store.py helper
- **FND-008** [PAX] Extend jobs.py job hash with files field (comma-separated owned paths) on post: --files flag, stored, shown by jobs.py show ★
  - Acceptance: jobs.py post --files a.py,b.py then show prints files: a.py,b.py; existing tests still pass
- **FND-009** [PAX] Extend jobs.py with deps field: --deps 3,7 on post, stored on hash, shown by show; posting with a nonexistent dep id warns loudly but succeeds ★
  - Acceptance: show prints deps; warning text asserted in tests/test_jobs.py additions
- **FND-010** [PAX] Extend jobs.py with attempts/max_attempts: attempts starts 0, requeue increments attempts, requeue refuses when attempts >= max_attempts and marks job failed-final ★
  - Acceptance: Test: max_attempts=2 job requeued twice, third requeue refused with clear error
- **FND-011** [PAX] Add last_progress_at and last_heartbeat_at fields updated by jobs.py progress and heartbeat commands ★
  - Acceptance: After progress call, show prints fresh last_progress_at; test asserts value changes
- **FND-012** [PAX] Make jobs.py sweep report dependency-dead candidates: claimed/open job whose dep is blocked past threshold gets flagged in sweep output (no state change yet)
  - Acceptance: Sweep output lists the candidate job id in a fixture scenario; no hash mutation asserted
- **FND-013** [PAX] Add jobs.py list --json output (id, title, status, claim, files, deps, attempts, lease_until, last_progress_at) for dashboard and watchdog consumption ★
  - Acceptance: --json parses with json.loads in test; fields match spec exactly
- **FND-014** [PAX] Add read-only intel snapshot API in intel/ingest.py: snapshot(room) returns {messages, jobs, presence, caps} dict from Redis + local store ★
  - Acceptance: Snapshot of fixture room returns all four sections with correct counts
- **FND-015** [PAX] Wire absolute message cursor reading into ingest: use store.py JSONL where present, fall back to bus list LRANGE paging like digest.py (PAGE=1000)
  - Acceptance: Ingest of 1,500-message fixture returns all 1,500 in order, none duplicated
- **FND-016** [PAX] Add intel CLI entry intel.py with subcommands brief, dispatch, watch, alerts, snapshot mirroring repo CLI style (argparse, RELAY_ERROR on failure, exit codes 0/2) ★
  - Acceptance: intel.py --help lists all five; bad subcommand exits 2 with usage
- **FND-017** [PAX] Add MUSE_RELAY_INTEL_* env config block to relay_common.py (model id, endpoint, budget caps, room default) with safe defaults
  - Acceptance: Config loads with zero env set; each override tested; no secret has a default value
- **FND-018** [PAX] Write tests/test_intel_store.py and tests/test_intel_snapshot.py on tests/fake_redis.py + tests/helpers.py patterns ★
  - Acceptance: Both files pass under python3 -m unittest discover tests; zero network access
- **FND-019** [PAX] Add CI-style local gate script hackathon/check.sh: py_compile all, full unittest suite, dash scan on new docs
  - Acceptance: check.sh exits 0 on clean tree and nonzero when a test is deliberately broken (verified once, then reverted)
- **FND-020** [PAX] Freeze the intel wire formats: BRIEF:, ALERT:, DISPATCH: announcement line shapes documented in intel/README.md before lanes build against them ★
  - Acceptance: intel/README.md contains exact line shapes with examples; Hana, Milo, Rowan sign off in lane notes

### BRF
- **BRF-039** [PAX] Review Hana's brief record schema against dashboard payload needs with Rowan; freeze by end of Day 2 ★
  - Acceptance: Freeze note in intel/README.md with date; dashboard mock uses the frozen fields
- **BRF-040** [PAX] Verify brief fallback path end to end on the live-shape stack (fake Redis + FakeTransport failure injection)
  - Acceptance: Fallback brief produced and stored; status CODE-INSPECTED notes plus test output recorded
- **BRF-041** [PAX] Sign off brief eval results before demo lock: rubric pass rate recorded in MASTER_PLAN progress notes
  - Acceptance: Pass rate written down with brief ids; failures either fixed or listed as known limits

### DSP
- **DSP-001** [PAX] Write dispatch prompt v1 in intel/prompts/dispatch.md: goal text -> job drafts [{title, spec, files, deps, max_attempts, accept lines in mos/acceptance.py formats}] ★
  - Acceptance: Prompt renders with a sample goal; output schema documented beside it
- **DSP-002** [PAX] Implement dispatch plan parser: validate Spark JSON strictly (schema, accept lines parse via mos/acceptance.parse_accept, files non-empty per job) ★
  - Acceptance: Parser rejects 6 malformed fixture plans with specific errors; accepts the golden plan
- **DSP-003** [PAX] Implement file-overlap guard: two jobs in one plan owning the same path is a hard error unless spec marks it shared-sequential with a dep between them ★
  - Acceptance: Golden overlap plan rejected; shared-sequential variant accepted only with dep present
- **DSP-004** [PAX] Implement dependency graph check: deps reference plan-local keys, graph is acyclic, every dep resolves to a real job after posting order is computed ★
  - Acceptance: Cycle fixture rejected with the cycle named; diamond fixture accepted with topological order printed
- **DSP-005** [PAX] Implement attempt-budget defaults: default max_attempts 3, clamp 1..5, per-job override honored from plan
  - Acceptance: Plan with max_attempts 99 is clamped and the clamp is reported in the plan summary
- **DSP-006** [PAX] Implement dispatch dry-run: intel.py dispatch --goal '...' --dry-run prints the full plan (titles, files, deps, budgets, accept) and posts nothing ★
  - Acceptance: Dry-run on demo goal prints plan; jobs list before/after identical
- **DSP-007** [PAX] Implement plan approval gate: posting requires --approve flag or interactive y/N; dashboard path requires Dale's signed-in action (no auto-post ever) ★
  - Acceptance: Posting without approval flag posts zero jobs in test; with flag posts the plan
- **DSP-008** [PAX] Implement plan poster: posts jobs via jobs.py main() in topological order, mapping plan keys to real job ids, storing dispatch record in muse-bus:intel:dispatch:<id> ★
  - Acceptance: Posted plan of 4 jobs yields 4 real ids with deps rewritten to real ids; record retrievable
- **DSP-009** [PAX] Sign every dispatched job with jobs.py HMAC signing (--secret-file keyring) when a keyring is configured; refuse to post unsigned in crew mode ★
  - Acceptance: Posted job verifies OK via jobs.py verify; unsigned-mode warning is loud and logged
- **DSP-010** [PAX] Announce posted plans to the build room as DISPATCH:<id> -> N jobs (only under Dale's posting rule)
  - Acceptance: Announcement matches frozen wire format; held when posting not approved
- **DSP-011** [PAX] Implement dispatch undo: intel.py dispatch --undo <id> requeues/cancels unclaimed jobs from a plan, leaves claimed jobs untouched and reports them
  - Acceptance: Undo on fixture plan cancels exactly the unclaimed jobs; claimed job ids listed in report
- **DSP-012** [PAX] Wire dispatch into mos/overseer.dispatch where possible: reuse capability matching so plan jobs carry req= caps when the goal names skills
  - Acceptance: Plan job with req=python shows caps in posted job announcement path (or documented gap if overseer API cannot carry it)
- **DSP-013** [PAX] Add goal-size guardrails: plans over 12 jobs or touching over 40 files require a second confirmation and are split-suggested
  - Acceptance: 13-job plan triggers the guard message in dry-run and approval flow
- **DSP-014** [PAX] Add dispatch spend + latency logging to the spend ledger with dispatch id
  - Acceptance: Ledger entry exists per posted plan in integration test
- **DSP-015** [PAX] Build the demo goal script: the exact plain-English goal Dale types in the demo, tuned until the plan it yields is stable across 5 runs ★
  - Acceptance: 5 consecutive dry-runs yield plans with identical job count and file ownership (diff report saved)
- **DSP-016** [PAX] Implement plan diff view: intel.py dispatch --show <id> prints plan as posted vs current job states (done/claimed/open per job)
  - Acceptance: Show on a half-finished fixture plan matches jobs list state exactly
- **DSP-017** [PAX] Handle Spark dispatch failure: malformed JSON twice in a row falls back to a single-job plan containing the raw goal as spec, clearly marked FALLBACK ★
  - Acceptance: Failure-injection test yields one fallback job and a loud warning; nothing malformed posted
- **DSP-018** [PAX] Add dispatch templates for recurring shapes (add-endpoint, fix-bug, write-tests, docs-pass) as prompt hints, not hard code
  - Acceptance: Template names appear in prompt file; a goal matching each shape yields sane plans in dry-run tests
- **DSP-019** [PAX] Verify dispatched jobs are claimable by mos/worker.py loop unchanged (worker claims, heartbeats, completes one plan job end to end on fake Redis) ★
  - Acceptance: Integration test: worker completes a dispatched job; acceptance verification runs via mos/overseer.verify_done
- **DSP-020** [PAX] Write dispatch section of intel/README.md: flow, guards, signing, undo, fallback
  - Acceptance: Cold reader (Milo) posts a dry-run plan from the README alone

### WDG
- **WDG-035** [PAX] Review detector thresholds with Milo against real lease defaults (jobs.py LEASE_DEFAULT 1800s) so alerts fire before leases die, not after ★
  - Acceptance: Threshold table shows alert lead time vs 30-min lease; signed off in tuning doc
- **WDG-036** [PAX] Verify watchdog never mutates job state in v1 (alerts only; sweep/requeue stay human or mos tick actions) ★
  - Acceptance: Code-inspection note + a test asserting job hashes identical before/after a tick
- **WDG-037** [PAX] Integrate alerts into brief payload (Hana) and dashboard payload (Rowan) via the shared alert record — one source of truth ★
  - Acceptance: Same alert id appears in brief, dashboard payload, and intel.py alerts output in integration test
- **WDG-038** [PAX] Run all three drills end to end personally before rehearsal week and log results
  - Acceptance: Drill log in hackathon/relay-intelligence/DRILL_LOG.md with dates and outcomes
- **WDG-039** [PAX] Confirm watchdog loop cost: one tick's Redis command count measured and written down (Upstash free-tier budget is a real constraint)
  - Acceptance: Command count per tick recorded in README with the polling cadence math

### DSH
- **DSH-037** [PAX] Provide Rowan a static payload dev pack: example JSON for brief, plan preview, alerts feed, crew board — generated from real fixtures ★
  - Acceptance: Dev pack in repo under intel/examples/; Rowan builds mocks without waiting on live services
- **DSH-038** [PAX] Define the viewer's write path for dispatch approve (how a browser action becomes a signed jobs post) or rule it out and make dashboard dispatch request-only (human runs intel.py) — decide and document by Day 3 ★
  - Acceptance: Decision + rationale in DASHBOARD_SPEC.md; implementation matches the decision
- **DSH-039** [PAX] Review every dashboard deploy batch before it goes to muse-relay-live (diff read + smoke checklist result)
  - Acceptance: Review notes exist per deploy in the schedule log
- **DSH-040** [PAX] Verify dashboard against the real bus shape with Dale-approved read-only viewing during integration (no test posts to main bus)
  - Acceptance: Integration notes record what was viewed; zero posts made
- **DSH-041** [PAX] Own the demo-mode risk: if ?demo=1 layout breaks on demo day, fallback is the normal view — rehearse both
  - Acceptance: Rehearsal log shows one full run in normal view

### INT
- **INT-001** [PAX] Stand up the integration environment: dedicated test Redis namespace via MUSE_RELAY_JOBNS/MUSE_RELAY_CAPNS overrides + separate build room, documented in intel/README.md ★
  - Acceptance: A second crew member reproduces the environment from the README alone
- **INT-002** [PAX] End-to-end test 1: goal -> dispatch dry-run -> approve -> post -> worker claims -> done -> brief reports it (full loop on fixtures) ★
  - Acceptance: Scripted run passes; transcript saved to intel/evals/e2e1.log
- **INT-003** [PAX] End-to-end test 2: worker dies mid-job -> watchdog alert -> sweep requeue -> second worker finishes -> alert auto-resolves ★
  - Acceptance: Scripted run passes; each transition asserted
- **INT-004** [PAX] End-to-end test 3: on-join brief for a fresh nick contains the drill's blocked item and the active alert
  - Acceptance: Brief content assertions pass against drill state
- **INT-005** [PAX] Run the full existing test suite (326 test methods at grounding) plus all new intel tests; no regressions allowed before any merge batch ★
  - Acceptance: Suite output recorded per batch; regressions block the batch (noted in log)
- **INT-006** [PAX] Load check: 2,000-message room + 200 jobs snapshot, brief, and watchdog tick timings recorded
  - Acceptance: Timings table in intel/evals/load.md; no operation exceeds its documented budget
- **INT-007** [PAX] Cost check: project Spark spend for demo day (briefs + dispatch + polish) from ledger rates; confirm inside the $150 API credit with headroom
  - Acceptance: Projection written in SUBMISSION notes; headroom stated as a number
- **INT-008** [PAX] Failure drill: Spark endpoint down for all features — briefs fall back, dispatch falls back, watchdog templates hold, dashboard shows honest states ★
  - Acceptance: Drill log shows every fallback engaged; nothing crashes
- **INT-009** [PAX] Failure drill: Redis read-only/outage — every intel command fails loudly with RELAY_ERROR and exit 2, never a traceback to the user
  - Acceptance: Drill log per command
- **INT-010** [PAX] Failure drill: spoofed dispatch (BAD signature) — claim refused, REJECTED alert visible, watchdog notes unsigned/spoof job
  - Acceptance: Drill passes using Buffy's spoof fixture
- **INT-011** [PAX] Security pass: grep the whole intel diff for secrets, tokens, and the job secret file path contents; confirm nothing sensitive committed ★
  - Acceptance: Grep output clean; .gitignore covers keyring/env files
- **INT-012** [PAX] Reconcile the git workflow conflict: README says feature branches + overseer merge, Dale's crew rule says push straight to main — follow Dale's recorded decision (GOV task) exactly and note it in every lane file ★
  - Acceptance: Lane files and this plan state one workflow; no lane works to the other rule

### DEM
- **DEM-001** [PAX] Lock the demo scenario: one plain-English goal, a 5-job plan, one staged silent failure (worker kill), watchdog catch, requeue, finish, closing brief ★
  - Acceptance: Scenario written in DEMO.md and approved by Dale (see DALE lane)
- **DEM-002** [PAX] Rehearse the demo end to end three times on separate days; log timings and every stumble ★
  - Acceptance: Three rehearsal entries in DRILL_LOG.md with total runtimes
- **DEM-003** [PAX] Record the full demo as a fallback video (screen capture of a clean rehearsal run) before demo freeze ★
  - Acceptance: Video file in submission-assets/; plays start to finish
- **DEM-004** [PAX] Prepare the submission package checklist from the hackathon's actual requirements (form fields, video limits, repo links) once published by organizers ★
  - Acceptance: Checklist in SUBMISSION.md with each requirement sourced; unknown fields marked pending organizer info
- **DEM-005** [PAX] Assemble final submission: repo link (muse-relay, main, green tests), live viewer link, video, written description from approved copy ★
  - Acceptance: Package assembled in submission-assets/ with a manifest; Pax verifies every link live
- **DEM-006** [PAX] Run the demo-day checklist: tokens present, credits balance checked, watchdog running, dashboard deployed, fallback video local ★
  - Acceptance: Checklist signed off in writing before the demo slot
- **DEM-007** [PAX] Freeze plan: feature freeze Nov 2 21:00 ET, demo freeze Nov 3 21:00 ET — enforce, log exceptions with Dale approval only ★
  - Acceptance: Freeze log exists; any exception names Dale's approval
- **DEM-008** [PAX] Prepare the 60-second verbal summary Dale can give cold (what it is, why it matters, what is live) from approved copy
  - Acceptance: Summary card in demo-assets/; Dale approves wording
- **DEM-009** [PAX] Post-demo: write the results/lessons note into the repo (what shipped, what is UNIMPLEMENTED, honest limits) within 24h of the demo
  - Acceptance: Note committed; statuses use VERIFIED / CODE-INSPECTED / UNIMPLEMENTED / BLOCKED only
- **DEM-010** [PAX] Verify the live viewer and repo are presentable to judges at submission time (no test junk in the demo room, README current)
  - Acceptance: Final check logged with screenshots

### DOC
- **DOC-015** [PAX] Fact-check every doc claim against the code before submission (the Pax verification pass) ★
  - Acceptance: Checklist signed in SUBMISSION.md; false claims fixed or removed
- **DOC-016** [PAX] Update INSTANCES.md with the intel layer note for future instances (what intel is, where the docs live)
  - Acceptance: INSTANCES.md diff is additive and accurate

### STR
- **STR-001** [PAX] Gate the stretch: verify core (brief, dispatch, watchdog, dashboard) statuses are VERIFIED before any STR task starts
  - Acceptance: Gate note written with per-feature status

## Meta OS — PAX (added 2026-10-22, Dale's OS decision)

Your slice of the Meta OS workstream (image pipeline, services, boot). Full spec: ../META_OS.md. The OS is the chassis; the Spark critical path in the sections above always wins a scheduling fight. Image content freeze: Nov 2 12:00 ET (SCHEDULE.md).

- **OS-005** [PAX] Freeze the base: Debian 12 (bookworm) amd64 as the single base; record the exact image/ISO source and sha256 in os/BASE.md ★
  - Acceptance: Checksum recorded and verified; no second base anywhere in the os/ tree
- **OS-006** [PAX] Lay down the os/ tree in muse-relay: os/build-image.sh, os/preseed.cfg, os/packages.txt, os/services/, os/firstboot/, os/README.md
  - Acceptance: Tree exists; shellcheck clean on every script in it
- **OS-007** [PAX] Build the primary pipeline: a scripted Packer + QEMU unattended build that produces metaos-<date>.img + .sha256 from a clean checkout in one command ★
  - Acceptance: One command on the build box yields a bootable image plus checksum; a second run reproduces the same package set
- **OS-008** [PAX] Build the fallback pipeline: a live-build configuration in os/live-build/ producing a bootable ISO of the same package and service set
  - Acceptance: ISO builds and boots to the crew session in QEMU; every divergence from the primary image documented in os/BASE.md
- **OS-009** [PAX] Unattended install via preseed: single relay user, autologin to the crew session, zero installer prompts, UTC + en_US, single-partition layout plus swapfile
  - Acceptance: Unattended QEMU install completes with zero prompts in the recorded run
- **OS-010** [PAX] Pin the package manifest: os/packages.txt lists the full set (python3 + venv, redis client tools, chromium, fonts, openssh-server present but disabled by default, qemu guest agent) with versions
  - Acceptance: Manifest diffed against the built image's dpkg -l output; zero unpinned extras
- **OS-011** [PAX] Bake the stack into the image: clone muse-relay at a pinned commit into /opt/relay, create its venv, install requirements at build time
  - Acceptance: /opt/relay on the image matches the pinned commit hash; intel/ package present and importable
- **OS-012** [PAX] Secrets rule for the image: ship NO credentials in the image; firstboot generates the local job-signing keyring (chmod 600) and prompts once for the Spark key and Upstash token, stored in env files chmod 600 ★
  - Acceptance: A strings/grep sweep of the built image finds no token or key material; the firstboot prompt flow verified end to end in a scratch VM
- **OS-013** [PAX] systemd unit relay-bus.service: runs the bus-side processes (presence/watch/store stack) as the relay user, Restart=on-failure, After=network-online.target
  - Acceptance: Unit enabled in the image; kill test restarts it; journalctl shows a clean start order
- **OS-014** [PAX] systemd unit relay-jobs.service: the jobs.py queue service loop with a lease sweep on start, ordered after relay-bus.service
  - Acceptance: A job posted before shutdown is announced and claimable after boot
- **OS-015** [PAX] systemd unit relay-overseer.service: mos/overseer.py tick loop as a service, Wants/After relay-bus + relay-jobs
  - Acceptance: The overseer claims and acceptance-verifies a fixture job end to end on the booted image
- **OS-016** [PAX] Boot target relay.target grouping bus, jobs, overseer, workers, watchdog, brief, and dashboard units, plus a oneshot relay-ready check that writes the boot-complete marker only when every unit is active
  - Acceptance: systemctl reaches relay.target; the marker file appears only with all units active (proven by disabling one unit)
- **OS-017** [PAX] Worker fleet units: relay-worker@.service template instantiating the mos/worker.py loop per nick, per-instance env file
  - Acceptance: Two instances run side by side on the booted image and claim disjoint jobs in the boot test
- **OS-018** [PAX] Boot performance budget: measure power-on to dashboard-ready, set the budget (target 90s or less on the demo hardware), and cut the top blockers from systemd-analyze blame ★
  - Acceptance: Three timed boots recorded in os/BOOT-TIMES.md; median within budget or each blocker filed as its own task
- **OS-019** [PAX] QEMU boot test harness os/test-boot.sh: boots the image headless, waits for the relay-ready marker via the guest agent, screenshots the dashboard
  - Acceptance: Harness exits 0 on a good image and nonzero on a deliberately broken one (one unit disabled)
- **OS-020** [PAX] Image versioning: every build stamps /etc/metaos-version (pinned commit, build date, image name) for the boot screen and support
  - Acceptance: Version shown on the boot screen in the boot test matches the build stamp exactly
- **OS-021** [PAX] Update path: metaos-update script pulls a git bundle of muse-relay + intel updates, applies it, and restarts relay.target; rollback is the previous bundle
  - Acceptance: Update from image N to N+1 on a scratch VM lands with all services active again; rollback path written in os/README.md
- **OS-022** [PAX] Recovery entry: a rescue boot option that starts the base system without relay.target, for demo-day recovery
  - Acceptance: Rescue entry boots to a shell on the test image; the normal entry is unaffected

**Working-system additions (vision upgrade, Dale 2026-10-22) — drivers, MCP service, skills loader:**

- **OS-053** [PAX] Agent-driver adapter contract: os/drivers/CONTRACT.md defines the driver interface — start(job_spec) against a signed spec, stop(), heartbeat() in bus progress format, artifacts + status record out — plus a stub driver and a written conformance checklist any future driver must pass ★
  - Acceptance: Contract + checklist committed; the stub driver passes every checklist item on the test image
- **OS-054** [PAX] Muse Code driver: implement the contract against Meta's Muse Code CLI — a claimed job spec launches Muse Code as a managed child process, progress streams as heartbeats, changed files + logs return as the artifact record ★
  - Acceptance: Driver passes the OS-053 conformance checklist; one fixture job completes end to end through the driver on the test image
- **OS-055** [PAX] Driver demo proof: a Spark-dispatched job (DSP pipeline) is claimed by the overseer, handed to the Muse Code driver, executed, and its artifacts + DONE land back in the queue — the OS-055 run is the demo beat's evidence ★
  - Acceptance: Full loop green on the frozen demo image with the state pack; timings recorded for DEMO.md
- **OS-058** [PAX] MCP gateway daemon unit: relay-mcp-gateway.service runs Dale's MCP gateway (~/workspace/mcp-gateway) as a system daemon under relay.target; every agent process on the machine reaches the tool estate through the gateway's one local endpoint
  - Acceptance: Unit active at boot on the test image; a crew worker and a driver process both call a gateway tool through the local endpoint
- **OS-059** [PAX] Gateway bake: the gateway stack is baked beside /opt/relay at a pinned state with its server catalog available on the image; zero secrets baked (keys enter via the OS-012 firstboot env only)
  - Acceptance: Image sweep (OS-012) finds no gateway credential material; gateway serves its catalog offline on the test image
- **OS-065** [PAX] Skills loader: mounts skills-2 collection folders into an agent process's launch environment, the way an OS loads apps — a process started on Meta OS begins with its skills already available ★
  - Acceptance: A driver process launched with a mounted skill shows the skill active in its first action; an unmounted control run does not
- **OS-066** [PAX] Working-system integration QA: one recorded end-to-end run on the image — boot → brief lists drivers/tools/apps → dispatch a job → Muse Code driver executes → watchdog watches the process → dashboard shows it — added to the boot test checklist
  - Acceptance: Run recorded green on an RC image; any failure files a fix task in the owning lane, not a workaround

**Phase B — post-hackathon daily-driver track [B]:**

- **OS-067** [PAX] [B] OpenCode driver: implement the OS-053 contract against OpenCode
  - Acceptance: Driver passes the OS-053 conformance checklist; a fixture job completes through it
- **OS-068** [PAX] [B] Freebuff/GLM driver: implement the OS-053 contract against the Freebuff agent, so Buffy runs as an OS-managed process instead of a hand-tended session
  - Acceptance: Driver passes the conformance checklist; a full Freebuff session runs start-to-finish under the supervisor with heartbeats in the bus record
- **OS-072** [PAX] [B] Image update channel: metaos-update grows into a channel — check, stage, apply at reboot, roll back — with a written update policy
  - Acceptance: A staged update applies at reboot on the daily machine and rolls back cleanly on demand; policy doc committed
- **OS-073** [PAX] [B] Hardening pass for a machine holding real keys: firewall defaults, key-only SSH, systemd sandboxing on crew units, the OS-012 secrets sweep re-run under the daily-driver threat model
  - Acceptance: Hardening checklist green; an external port scan of the daily machine shows only intended listeners

**Depth — the four system services (Dale 2026-10-22; spec: ../META_OS.md, "Depth: the four system services"):**

- **OS-078** [PAX] Memory service (minimal): a journaled, versioned OS-level store — per-agent memory + shared crew memory — mounted into every agent process at start (home-directory model); the service runs in the image under relay.target ★
  - Acceptance: A process restarted on the test image reads back its own prior memory entries and the shared crew entries; every write is journaled with a version stamp
- **OS-080** [PAX] Identity + capability files: every crew and driver process runs as a named identity with an explicit capability file (files it may write, bus posting on/off, spend on/off, network on/off), loaded at process start and enforced by the OS layer, not by prompt text ★
  - Acceptance: Capability files exist for every crew identity on the test image; a process launched with a capability removed cannot perform that action even when its job spec asks for it
- **OS-083** [PAX] Workspace/artifact store (minimal): a git-backed versioned shared filesystem in the image; dispatched jobs deposit work products there and reference them by path in the job record instead of pasting through chat ★
  - Acceptance: A driver-executed job's outputs land in the store with a version history; the job record carries artifact paths, and the files open from those paths on the test image
- **OS-086** [PAX] [B] Memory scoping depth: per-agent vs shared scoping enforced by the memory service — a process reads shared crew memory and its own, never another agent's private memory
  - Acceptance: Cross-agent private read attempt is refused and logged on the daily machine; shared reads unaffected
- **OS-090** [PAX] [B] Budget priority classes: lanes/jobs carry priority classes; when budget contention hits, high-priority work claims budget first and low-priority work waits instead of starving randomly
  - Acceptance: Contention fixture: the high-priority job completes inside budget while the low-priority job waits with its state visible, not failed

- **OS-093** [PAX] The order door: Dale's one plain-English order — sent from his phone, from anywhere — lands on the cloud bus and becomes a signed job set owned by the queue the moment it arrives; `relay-uplink.service` under relay.target holds the machine's side of that connection (reconnect/backoff; health in the boot checklist + boot brief) so an order always has somewhere to land ★
  - Acceptance: An order sent from a phone, with no further contact from Dale, dispatches and work starts on the machine; kill the machine's network mid-flight and the uplink recovers unaided without losing the order
- **OS-094** [PAX] Jobs belong to the queue: a job's full state — spec, progress, artifacts (via the OS-083 store) — lives in the queue and the store, never only inside an agent session; any worker can resume a job from its deposited progress instead of restarting it from zero
  - Acceptance: Kill a worker mid-job and end its session entirely: on lease expiry a different worker resumes the job from deposited progress and completes it; nothing about the job existed only in the dead session
- **OS-101** [PAX] Mind-image bundle format: the bundle spec — constitution (AGENTS.md-equivalent standing instructions + identity), selected skills, memory mount reference (OS-078), capability grant (OS-080), MCP tool grants, environment brief slot — as one versioned, inspectable artifact with a version stamp and changelog pointer ★
  - Acceptance: Format doc + one hand-built example bundle committed; the bundle parses, names its version, and every layer resolves to a real source (instruction file, skill folder, memory mount, grant, gateway tools, brief)
- **OS-102** [PAX] Loader integration: process launch assembles and mounts the mind image — this EXTENDS the OS-065 skills loader (skills become one layer of the assembly) rather than duplicating it; crew workers and driver processes alike launch from an image, none hand-assembled ★
  - Acceptance: A worker and a driver process both launch from bundles on the test image; the launched process's effective instructions/skills/memory/grants match its bundle exactly; OS-065's fixtures still pass through the new path
- **OS-109** [PAX] [B] Image revision loop tooling: eval results propose the next image as a diff — which layer changes, on what evidence from OS-105/OS-106 numbers — for Dale's approval before any revised image ships; the loop that makes the crew faster by versioned iteration, with evidence, as routine maintenance
  - Acceptance: From one real A/B result, the tooling produces a reviewable image diff tied to the measured defect; nothing auto-applies — an approved diff becomes the next version under OS-104 discipline
- **OS-110** [PAX] `meta join` + firstboot room config: one command (and a firstboot prompt step beside OS-012) takes a room address + key into the chmod-600 env files, announces the machine on the room — machine name, crew nicks, each agent's mind-image version and capability badge — and starts claiming per local trust settings ★
  - Acceptance: A fresh test image joins the fixture room with the command alone; the announcement appears in the room naming machine, nicks, image versions, and badges; the room key appears nowhere in the image, the bus record, or any log
- **OS-116** [PAX] [B] Local Wi-Fi fast lane: machines on the same network discover each other automatically (mDNS-style local discovery) and sync claims + artifact movement directly — lower latency, and the room keeps working locally through an internet drop, reconciling to the cloud record when it returns; the cloud bus stays the single source of truth, the lane is transport only
  - Acceptance: Two machines on one LAN discover each other with zero configuration; a job hands off over the local lane measurably faster than the cloud path; with the WAN unplugged mid-job the room keeps working and reconciles to the cloud record on reconnect with no duplicate claims and no lost jobs

- **OS-118** [PAX] The watchman: `relay-watchman`, a small resident CLI program inside the OS (`relay-watchman.service` under relay.target, a unit in the service map with the same standing as the other units — not an agent, not a dashboard feature; the pattern exists in muse-relay's watch.py/poll.py listeners) that watches the job queue for work addressed to its machine's agents, watches those agents' heartbeats once working, rings the bell for sleepers, and works the self-repair ladder's mechanical rungs on its machine (OS-095: nudge, restart, reassign via the OS-125 baton pass) — detection reads job claims/leases, never a bus message counter, so the seen-counter drift failure mode is designed out rather than patched ★
  - Acceptance: On the test image the watchman notices a newly posted job for a local agent within one poll cycle and emits a wake event naming job + agent; a worker whose heartbeat goes stale draws the ladder's nudge from the watchman on the same watch cycle; replaying or skipping bus messages changes nothing (detection provably reads job state, not message counts); the watchman makes no model calls and holds no session of its own
- **OS-120** [PAX] [B] PC agent wake shim: the same bell for agents living outside the image on Dale's PC — a small local watchman script on the PC rings and starts the local agent's session with the job as its brief, so a PC-resident crew member joins the never-stops loop without a Meta OS install
  - Acceptance: With the shim running on the PC and its agent fully stopped, a posted job wakes the agent and work starts with no action from Dale; with the shim stopped, the job waits untouched (no phantom claims) until the OS-121 sweep or a crew member picks it up per the ladder

- **OS-128** [PAX] Disk-state audit test: with the crew mid-work on the test image, kill every session and every process — workers, sessions, dashboard, all of it — without touching the store (queue, job records, memory service, journal). Then inventory what the store alone can answer: every job's spec, progress, baton state, artifacts, and settled decisions must be fully reconstructable by a cold reader who never met the dead sessions ★
  - Acceptance: The audit walks every in-flight job and reconstructs its complete state from the store with zero items answerable only from a dead session's memory; any item that fails is filed as a named leak (which layer kept session-local truth) with a fix task in the owning lane before the image freeze — the audit passes only when the leak list is empty
- **OS-130** [PAX] [B] External crew cadence kit: the recovery pattern for agents living outside the image — one documented kit any agent runtime can adopt: a scheduled sweep entry per agent (wake, re-register standing watches from disk, sweep the queue, work or sleep), an event-hook registration where the runtime supports a bus-arrival trigger, and the restart rule (the first wake after any restart re-registers from disk before claiming) — written for the runtimes the crew actually lives on (Muse instances, Dale's PC), not as abstract documentation
  - Acceptance: The kit is adopted by at least one real external agent end to end: its runtime is restarted (not just its session), the first scheduled wake re-registers its watches from disk, it sweeps and resumes its queue position with zero Dale contact; the kit doc names per-runtime what persists (crons/jobs on disk) vs what dies (sessions) in one table a cold reader can apply to a new runtime

---
PAX total: 122 tasks.
