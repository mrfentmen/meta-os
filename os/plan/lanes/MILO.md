# Lane: MILO — Watchdog lane. (Also the crew's voice/audio owner.)

You own: the watchdog — heartbeat/lease monitoring, stall detection, dead-dependency detection, file-collision detection, alert records, explanations, and the three drills (kill-a-worker, collision, dead-dep). You also own all demo audio: narration takes, timing, fallback track, stingers. Watchdog v1 alerts only — it never touches job state.

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
- **FND-029** [MILO] Define watchdog state keys with Pax: muse-bus:intel:wd:<nick> hash (last_seen, last_progress, claimed_jobs) and alert dedupe key shape ★
  - Acceptance: Key shapes written into intel/store.py docstring; Milo and Pax both reference the same names in code
- **FND-030** [MILO] Specify lease/progress thresholds as config constants (stall = no progress AND no heartbeat for N minutes; default 10) in one shared module intel/thresholds.py
  - Acceptance: thresholds.py exists with named constants + comments; watchdog and tests import from it only
- **FND-031** [MILO] Audit jobs.py sweep + mos/overseer.py tick for reusable lease-expiry logic; write findings to intel/notes/milo-reuse-audit.md
  - Acceptance: Notes file names exact functions reused vs rewritten, with file:line references

### WDG
- **WDG-001** [MILO] Implement watchdog main loop intel/watchdog.py: tick(room) reads snapshot, evaluates detectors, writes alerts, announces per rules; --once and --loop modes ★
  - Acceptance: --once on quiet fixture writes zero alerts and exits 0
- **WDG-002** [MILO] Implement presence-stall detector: nick in caps registry but presence key gone > threshold while holding a claimed job ★
  - Acceptance: Stall fixture produces exactly one stall alert naming nick, job, last progress age
- **WDG-003** [MILO] Implement progress-stall detector: claimed job with heartbeat alive but no progress note beyond threshold (worker alive, work stuck) ★
  - Acceptance: Fixture with heartbeats-but-no-progress yields progress-stall alert distinct from presence-stall
- **WDG-004** [MILO] Implement lease-risk detector: claimed job whose lease expires within 5 min and no heartbeat in last 2 min gets a warning alert before expiry
  - Acceptance: Fixture near expiry yields warning; after jobs.py sweep requeues it, alert auto-resolves
- **WDG-005** [MILO] Implement dead-dependency detector: open job whose dep is blocked longer than threshold, or whose dep is failed-final ★
  - Acceptance: Dead-dep fixture yields one alert naming both job ids and the blocking reason verbatim
- **WDG-006** [MILO] Implement dependency-cycle/missing detector for posted jobs: dep id that does not exist in the index
  - Acceptance: Fixture with dangling dep yields missing-dep alert (catches bad posts early)
- **WDG-007** [MILO] Implement file-collision detector: two claimed jobs with overlapping files fields, or a claimed job overlapping a done-but-unmerged branch's files when branch data present ★
  - Acceptance: Collision fixture yields one alert naming the shared path and both jobs
- **WDG-008** [MILO] Implement attempt-exhaustion detector: job at max_attempts-1 requeues gets a heads-up alert; at max gets failed-final alert
  - Acceptance: Fixture walk produces both alerts at the right attempts counts
- **WDG-009** [MILO] Implement silent-room detector (informational): build room with claimed jobs but zero messages for threshold during work hours — likely everyone stuck or heads-down; label INFO never ALERT
  - Acceptance: Fixture yields INFO record only; dashboard severity mapping test passes
- **WDG-010** [MILO] Implement alert record writer via intel/store.py: {id, kind, severity, room, subjects, explanation, suggested_fix, created_at, resolved_at, dedupe_key} ★
  - Acceptance: Records round-trip; required fields validated in tests/test_intel_watchdog.py
- **WDG-011** [MILO] Write explanation templates per detector: plain-English one-liner + suggested fix, filled from alert subjects (no LLM needed for v1) ★
  - Acceptance: Each detector's fixture alert carries a filled explanation and fix; snapshot review by Hana for plain English
- **WDG-012** [MILO] Add optional Spark polish pass: when enabled, Spark rewrites explanation for clarity; template text retained if Spark fails or budget is tight
  - Acceptance: Toggle off = template text; toggle on with FakeTransport = polished text; failure keeps template
- **WDG-013** [MILO] Implement dedupe: same dedupe_key inside cooldown (default 30 min) updates last_seen instead of creating a new alert ★
  - Acceptance: Two ticks on stall fixture yield one alert with last_seen advanced
- **WDG-014** [MILO] Implement alert lifecycle: open -> acknowledged (intel.py alerts --ack <id>) -> resolved (auto when condition clears, or --resolve) ★
  - Acceptance: Lifecycle test walks all transitions; auto-resolve fires when fixture condition clears
- **WDG-015** [MILO] Announce new critical alerts to the build room as ALERT:<id> one-liners under Dale's posting rule; warnings accumulate silently for the brief/dashboard
  - Acceptance: Critical fixture produces one announcement line in frozen format (or held per Dale rule); warning produces none
- **WDG-016** [MILO] Implement watchdog self-heartbeat: muse-bus:intel:wd:beat key with TTL so the dashboard can show 'watchdog alive' honestly ★
  - Acceptance: Beat key exists after a tick in test; dashboard payload includes watchdog_age_seconds
- **WDG-017** [MILO] Implement tick budget guard: a tick over N jobs/messages paginates like digest.py and never loads unbounded history
  - Acceptance: 1,500-message fixture tick completes with bounded memory pattern (paged reads asserted in code review + test runtime sane)
- **WDG-018** [MILO] Add detector config in intel/thresholds.py (all thresholds named, env-overridable)
  - Acceptance: Changing env threshold changes detector behavior in a test
- **WDG-019** [MILO] Write tests/test_intel_watchdog.py covering every detector's positive and negative case on fake_redis fixtures ★
  - Acceptance: All detectors have both cases; suite passes
- **WDG-020** [MILO] Build the kill-a-worker drill harness: script starts a fake worker, claims a job, stops heartbeats mid-job, runs watchdog, asserts alert + sweep requeue (used live in demo) ★
  - Acceptance: Drill passes unattended on fixtures; drill script saved at intel/drills/kill_worker.py
- **WDG-021** [MILO] Build the collision drill: two fake workers claim overlapping-files jobs; assert collision alert before either finishes
  - Acceptance: Drill passes; saved at intel/drills/collision.py
- **WDG-022** [MILO] Build the dead-dep drill: post A and B(deps A), block A, age the clock, assert dead-dep alert text names A's reason
  - Acceptance: Drill passes; saved at intel/drills/dead_dep.py
- **WDG-023** [MILO] Add alert history query: intel.py alerts --room --since --kind filters for briefs and dashboard backfill
  - Acceptance: Query on fixture alert set returns exactly the filtered subset
- **WDG-024** [MILO] Add severity mapping: stall/dead-dep/collision = critical, lease-risk/attempt = warning, silent-room = info; mapping table in intel/README.md ★
  - Acceptance: Mapping table published; dashboard colors keyed to it (Rowan confirms)
- **WDG-025** [MILO] Handle watchdog edge: job claimed by a nick that was never in caps registry (walk-on worker) — track from jobs data alone, no crash
  - Acceptance: Fixture with unknown claimer yields tracking record and stall detection still works
- **WDG-026** [MILO] Handle clock skew: all ages computed from Redis server time where available, documented assumption otherwise
  - Acceptance: Ages in tests use injected clock; assumption written in README
- **WDG-027** [MILO] Tune thresholds against Buffy's synthetic histories: run watchdog over all fixtures, tabulate false positives/negatives in intel/evals/watchdog_tuning.md ★
  - Acceptance: Tuning table covers every fixture; zero false positives on quiet fixture is required to pass
- **WDG-028** [MILO] Add watchdog status line for the morning brief: counts by severity + top alert, as a store record Hana consumes ★
  - Acceptance: Brief on stall fixture includes watchdog counts matching alert store
- **WDG-029** [MILO] Write watchdog section of intel/README.md: detectors, thresholds, lifecycle, drills
  - Acceptance: Cold reader (Rowan) runs the kill drill from README alone
- **WDG-030** [MILO] Record demo narration audio: watchdog segment voiceover (the 'silent failure' story) in Milo's voice lane, two takes
  - Acceptance: Files saved at hackathon/relay-intelligence/demo-assets/audio/ with take log
- **WDG-031** [MILO] Record demo narration audio: opening 20-second product framing voiceover, two takes
  - Acceptance: Files saved with take log; Dale picks take at rehearsal
- **WDG-032** [MILO] Sync narration timing to DEMO.md shot list (each clip mapped to a shot number, lengths noted)
  - Acceptance: Timing sheet in demo-assets/audio/ maps clip -> shot -> seconds
- **WDG-033** [MILO] Prepare fallback narration: full-demo voiceover track in case live narration fails on the day
  - Acceptance: Single mixed track exported; length within demo slot
- **WDG-034** [MILO] Prepare audio stingers: subtle alert sound + success sound for demo transitions (original or CC0 only, license noted)
  - Acceptance: Two files with license note in demo-assets/audio/LICENSES.md

### INT
- **INT-020** [MILO] Watchdog integration: alerts visible in brief (Hana) and dashboard (Rowan) with identical ids and severities in the e2e runs ★
  - Acceptance: E2E log shows id match across all three surfaces
- **INT-021** [MILO] Drill tournament: run kill/collision/dead-dep drills back to back in one session, timed, as the demo will do
  - Acceptance: Combined drill log under 6 minutes wall time
- **INT-022** [MILO] Threshold final tune after integration fixtures grow: rerun tuning table, lock thresholds for demo
  - Acceptance: Locked values committed to thresholds.py with a comment citing the tuning doc
- **INT-023** [MILO] Verify watchdog behavior during the load check (200 jobs) — no alert storms, dedupe holds
  - Acceptance: Alert count for the load scenario recorded and sane (dedupe proven)

### DEM
- **DEM-011** [MILO] Stage the silent-failure moment: scripted worker that claims the demo job, posts one progress note, then goes silent on cue ★
  - Acceptance: Drill runs to cue in rehearsal; timing on the cue card
- **DEM-012** [MILO] Time the watchdog catch: from silence cue to alert on dashboard must be under 90 seconds in demo configuration (demo thresholds profile) ★
  - Acceptance: Measured catch time recorded across 3 rehearsals
- **DEM-013** [MILO] Prepare the demo thresholds profile (shortened stall windows) as a config, clearly separate from production defaults
  - Acceptance: Profile file exists; production thresholds.py untouched
- **DEM-014** [MILO] Narration final mix: combine picked takes, level-check against screen capture audio
  - Acceptance: Mixed track exported and synced in the fallback video
- **DEM-015** [MILO] Record a 15-second 'what you are seeing' caption voiceover for the watchdog moment for the fallback video
  - Acceptance: Clip saved and placed in the fallback edit
- **DEM-016** [MILO] Stand by during the live demo as watchdog operator: watch the alert fire, be ready to run the drill manually if automation hiccups
  - Acceptance: Operator role written in DEMO.md crew list; manual commands on the failover card
- **DEM-017** [MILO] Prepare ambient crew audio bed (very low, royalty-free/CC0, license noted) for the fallback video
  - Acceptance: File + license note in demo-assets/audio/
- **DEM-018** [MILO] Verify all audio plays clean on the demo machine speakers and on headphones
  - Acceptance: Listening check logged with the demo machine named

### STR
- **STR-003** [MILO] Feed watchdog drill screenshots (dashboard states) into the SAM evaluation set as known-good/known-bad pairs
  - Acceptance: Pairs saved with labels in intel/evals/sam/

## Meta OS — MILO (added 2026-10-22, Dale's OS decision)

Your slice of the Meta OS workstream (supervisor / watchdog service integration). Full spec: ../META_OS.md. The OS is the chassis; the Spark critical path in the sections above always wins a scheduling fight. Image content freeze: Nov 2 12:00 ET (SCHEDULE.md).

- **OS-033** [MILO] systemd unit relay-watchdog.service: the intel/watchdog.py loop as a system service ordered after relay-jobs, emitting its own heartbeat to muse-bus:intel:wd:beat ★
  - Acceptance: Service active at boot; beat key renews; stopping the unit makes the dashboard show the watchdog-silent state
- **OS-034** [MILO] Restart ownership contract with Pax: systemd Restart owns process death; the watchdog owns silent-but-alive stalls; neither double-acts on the other's case
  - Acceptance: Drill log shows both cases: kill -9 a worker gets a systemd restart plus a watchdog event note and NO false stall alert; SIGSTOP a worker gets a stall alert and no restart fight
- **OS-035** [MILO] Per-agent resource limits: a relay-workers.slice with MemoryMax and CPUQuota defaults on relay-worker@ instances, tuned from the INT-019 load numbers
  - Acceptance: A runaway fixture worker is throttled by its cgroup while the bus stays responsive; final limits recorded in META_OS.md
- **OS-036** [MILO] Watchdog boot self-check: at relay-ready the watchdog runs each detector once against the seeded fixture (OS-026 stale lease) and writes a green self-check record
  - Acceptance: Self-check record exists after every boot test; breaking a detector fails the boot test
- **OS-037** [MILO] Journal watch: the watchdog tails journald for relay unit failures and raises a SYSTEM alert record, distinct from job alerts
  - Acceptance: Force-failing a unit produces a SYSTEM alert in the alert store and the dashboard feed within one watchdog loop
- **OS-038** [MILO] Demo thresholds profile: metaos-demo.env loaded by a unit drop-in on the demo image, separate from production thresholds, no code edits
  - Acceptance: Drop-in switches the stall windows on the demo image; the production profile still passes the INT drills untouched
- **OS-039** [MILO] Boot audio: a short sting plus one voice line for the boot moment of the demo, stored in submission-assets/
  - Acceptance: Audio plays over the boot shot in the DEM-003 fallback cut without clipping the narration
- **OS-040** [MILO] Power-cut drill: hard-kill the VM mid-job three times; on reboot leases expire, jobs requeue, and the boot brief reports the interruption
  - Acceptance: Three of three runs recover with zero manual fixes; drill logged with timings
- **OS-041** [MILO] Watchdog status line for the boot screen: one line of live health (units up, workers alive, last alert) exposed for Rowan's boot checklist
  - Acceptance: Line renders from live data on the test image and goes stale within 30s of a unit being killed

**Working-system additions (vision upgrade, Dale 2026-10-22) — driver supervision:**

- **OS-056** [MILO] Driver supervision integration: driver processes run as systemd units in a relay-drivers.slice under the OS-034 contract (systemd owns process death; the watchdog owns silent stalls); driver heartbeats feed the existing WDG stall detectors unchanged
  - Acceptance: A driver process appears in the slice on the test image; kill -9 restarts per contract with a watchdog event note and no false stall alert
- **OS-057** [MILO] Driver stall drill: wedge a driver process (alive, heartbeat stale); the watchdog raises the same STALL alert as for a crew worker and the driver is restarted per contract without touching other drivers
  - Acceptance: Drill logged: STALL alert inside the demo threshold, clean restart, sibling driver undisturbed

**Phase B — post-hackathon daily-driver track [B]:**

- **OS-074** [MILO] [B] Seven-day soak: the full crew + all drivers run unattended on Meta OS for 7 days; the watchdog journal is reviewed end to end
  - Acceptance: Soak report filed: every silent failure in the log has an alert or a filed bug; zero unexplained gaps

**Depth — the four system services (Dale 2026-10-22; spec: ../META_OS.md, "Depth: the four system services"):**

- **OS-081** [MILO] Capability refusal enforcement (the demo path): an action attempted outside a process's grant is refused by the OS, the refusal is written as an alert record with a plain-English explanation, and the watchdog surfaces it like any other alert ★
  - Acceptance: Drill on the test image: a staged process attempts a bus post outside its grant → refused, alert record exists, explanation names the identity, the action, and the missing capability (DEMO.md Shot 8b evidence)
- **OS-085** [MILO] Budget config + pre-limit warnings: per-process and per-lane API/compute budgets as config the job queue reads before claiming (a lane at cap does not claim new Spark work) and the watchdog warns at a threshold before the cap, not after the silence
  - Acceptance: Fixture lane driven to its warning threshold produces a budget warning alert; at cap, the queue holds new claims for that lane and the hold is visible in the brief's budget line (OS-079)
- **OS-091** [MILO] [B] Budget preemption + forecasting: the watchdog can preempt (pause, not kill) low-priority spenders approaching a cap, and projects end-of-day spend from the ledger rate so Dale sees a breach coming hours ahead
  - Acceptance: Forecast line appears in the daily brief with a stated confidence basis; a preempted job resumes cleanly when budget frees

- **OS-095** [MILO] The self-repair ladder: on a stall, the watchdog acts before it reports — nudge the worker, then restart the worker, then reassign the job to another agent — each rung journaled with its reason; Dale is contacted at no rung
  - Acceptance: Three staged stalls (unresponsive worker, dead worker, job held by the wrong worker) are each resolved by the correct rung with zero Dale contact; every ladder action appears in the journal and the next brief
- **OS-096** [MILO] Attempt budgets + the escalation gate: every job carries an attempt budget spanning all repair rungs; an exhausted budget — or a blocker that is genuinely Dale's call (money, permission, direction) — parks the job visibly and fires the one blocked push (OS-097); nothing retries forever, and nothing escalates that the crew can settle itself
  - Acceptance: A deliberately impossible job burns exactly its budget, parks, and escalates exactly once — no loop, no duplicate pushes; a crew-fixable blocker in the same drill is resolved with zero escalation
- **OS-106** [MILO] The measured A/B run + image-defect attribution: execute the OS-105 harness for the demo's one comparison (bare launch vs mind image) under watchdog measurement, and tag stall patterns attributable to the image — missing skill, bad instruction, thin environment brief — as image defects feeding the revision loop, not as worker failures
  - Acceptance: One A/B result in hand: same jobs, both versions, times + acceptance outcomes recorded; at least one observed stall in the runs is correctly attributed (image defect vs worker failure) with the journal evidence named
- **OS-112** [MILO] Signed-job trust list enforcement in the overseer: the overseer verifies a job's HMAC-SHA256 v2 signature against the local trust list before any local agent may claim it, and clamps the posting crew's badge claims to local policy; refusal is a logged, board-visible event, never a silent skip ★
  - Acceptance: A job signed by a trusted crew is claimable; the same job unsigned or signed by an untrusted key is refused at claim time with the refusal in the job record and the watchdog's log; the trust list itself lives only in the local chmod-600 config
- **OS-114** [MILO] Trust negative test: an untrusted machine joins the fixture room and posts a job (and re-posts it under a spoofed crew nick); both attempts are refused by the trusted machine's overseer, logged, and surfaced — words on the bus, no work exchanged
  - Acceptance: Zero claims of the hostile jobs by any trusted agent across the test window; both refusals appear in the log with the reason (untrusted signer / signature absent) and the drill leaves the fixture room clean

- **OS-119** [MILO] Muse wake adapter: when the bell rings for a sleeping Muse instance (the Hana/Rawan class of runtime), the adapter starts the agent's session through its runtime's session mechanism with the job already in its hands — spec, mind image via the OS-102 loader, acceptance checks — so the agent's first act is the job, never a poll ★
  - Acceptance: A sleeping fixture agent, given a posted job and zero human contact, wakes, claims, and starts work with the bundle in place — its first bus action is the claim/progress on that job, not a status check; a job addressed to a different agent does not wake it
- **OS-121** [MILO] [B] Timer fallback sweep: every agent runtime also wakes on a slow timer to sweep the board and claim anything the bell missed — shift-worker clock-in as the safety net under the bell, so a missed wake delays work by minutes, never forever
  - Acceptance: With the watchman deliberately disabled, a posted job is still claimed within one sweep interval by the timer path alone; with the watchman healthy, sweeps produce zero duplicate claims (lease discipline holds across both paths)
- **OS-122** [MILO] Who watches the watchman: the watchdog treats a dead watchman as a first-class failure — crew-dark: the machine's agents asleep, its jobs invisible to them — attempts the self-repair (restart the watchman) per the OS-095 ladder, and only if the watchman cannot be revived does it earn Dale's blocked-push; per-machine watchman state (alive/dead, last bell, last wake) is published for the board's machine groups (OS-111)
  - Acceptance: Kill the watchman on the fixture machine: the watchdog flags crew-dark within one detector cycle, the restart revives it, and no Dale push fires; kill it beyond the restart's power and exactly one blocked-push fires naming the machine; the board's group for that machine reads watchman-dead while it lasts
- **OS-125** [MILO] The baton pass: when the ladder reaches reassign, the watchman does not restart the job from zero — it composes a continuation prompt from the job record (goal, the progress the worker deposited as it went, files touched, what remains, acceptance checks — the baton state OS-094 and OS-083 make possible) and hands it to the next agent program, which picks up exactly where the previous worker left off; workers deposit progress as they go, or there is no baton to pass
  - Acceptance: Drill: a worker is killed mid-job; the watchman passes the baton and the job completes with no repeated work — the record shows the deposited progress, zero duplicated file changes, and a continuation prompt that names what remains instead of restating the whole job. In-window the continuation is proven same-program; the cross-program pass (e.g. Muse → Freebuff, possible because both are pre-installed in the image) is the named stretch line — run before freeze if the drivers allow, honestly reported either way

- **OS-129** [MILO] Watchman state after reboot: the watchman itself survives the machine dying — at boot it rebuilds its picture purely from queue claims and leases (never a stored message counter, so no stale-counter gap and no missed ring across the reboot boundary), resumes ringing for work that landed while the machine was down, and its first post-boot cycle reconciles with the lease sweep; OS-129 also carries the verification half of the OS-126 drill (lease-sweep timing and resume evidence, independently checked)
  - Acceptance: Across the OS-126 power cuts, the watchman's first post-boot cycle rings for every job that arrived during downtime and none are double-rung or missed (drill log, claims read before/after); a deliberately corrupted stored counter value changes nothing in the watchman's behaviour, proving it never reads one; Milo's verification note on the drill is filed separately from Buffy's run log

---
MILO total: 75 tasks.
