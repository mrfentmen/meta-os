# Relay Intelligence — MASTER PLAN

**Product:** Relay Intelligence — a Muse Spark powered mission control for agent crews, built on the existing muse-relay bus — shipped inside **Meta OS**, a Debian-based operating system rebuilt for Meta agents. Two layers, one story: Meta OS is the machine, Relay Intelligence is the mind (decision: Dale, 2026-10-22; spec: META_OS.md).
**Event:** Meta Global AI Developer Hackathon — Indie track, Push the Frontier theme. Status: APPROVED (2026-10-22).
**Build window:** Mon Oct 26, 2026 12:00 PM ET → Wed Nov 4, 2026 9:00 PM ET (fully remote).
**Total tasks: 432** across 6 lanes (301 Relay Intelligence + 131 Meta OS). ★ = critical path. [B] = Phase B (post-hackathon daily-driver track, fenced off the critical path).

## What we are building (exactly what the approved application promised)

1. **Briefings** — Spark reads bus history + job queue + presence and writes plain-English briefs (decisions, in flight, owners, blocked and why): a morning brief and an on-join brief.
2. **Dispatch** — a plain-English goal becomes structured job specs (files owned, dependencies, attempt budgets, machine-checkable acceptance), signed with the existing HMAC job signing, and posted to the existing job queue after a human approval gate.
3. **Watchdog** — watches claims, leases, and heartbeats; flags silent failures (stalled worker, dead dependency, two agents on the same files) with a plain explanation and a suggested fix.
4. **Dashboard** — all of it inside the existing live viewer: crew board, brief panel, dispatch box, alert feed.
5. **Meta OS** — the machine it all ships in, and the system Dale actually uses: a bootable Debian-based image whose systemd brings up the bus, the job queue, the mos overseer and workers, the watchdog, the briefing service, and the dashboard at power-on, with per-agent cgroup limits, a crew journal, and one install/update path. The crew is not launched; it is woken. On top of the appliance: Meta agents drive other coding agents as managed system processes (agent drivers), the MCP gateway ships as a system service (tools are the OS's system libraries), and skills ship as installable applications (OS-053–OS-066 in-window; the Phase B daily-driver track OS-067–OS-077 is post-hackathon). Depth comes from exactly four OS-level system services — memory, identity/capabilities, workspace/artifact store, budget/resource policy (OS-078–OS-092; spec in META_OS.md, "Depth: the four system services") — and nothing else: anything that is an application belongs in skills, not in the OS. Dale's phone touches the system exactly twice — one plain-English order in, one push out when the work is verified done or blocked on a decision only he can make (the completion contract, OS-093–OS-100; spec in META_OS.md, "The completion contract: order once, hear back when it's done"; Dale named the phone connection the bottleneck and rejected the remote-control framing, 2026-10-22). And every agent process launches from a versioned mind image — constitution, skills, memory, capability grant, tool grants, environment brief (OS-101–OS-109; spec in META_OS.md, "Mind images: the OS boots minds, not just machines"). And machines federate: any Meta OS box with a room's address + key joins the same bus room and the same queue via `meta join`, so agents on any connected machine can claim work posted from any other — gated by signed jobs and trust lists, default closed (OS-110–OS-117; spec in META_OS.md, "Federation: many machines, one crew"). And sleeping agents get woken, not poked: a tiny always-on watchman program on each machine watches the queue and rings the bell, starting each agent with its job already in its hands — and if a worker falters, the watchman passes the baton (a continuation prompt built from the job record) to the next agent program instead of restarting the job from zero — Dale touches nothing (OS-118–OS-125; spec in META_OS.md, "The bell: how sleeping agents get woken"). And the crew survives the machine dying — Dale's biggest bottleneck and the original reason he built the bus: state lives on disk, never in a session; the services are enabled, so a reboot IS the relaunch (lease sweep, watchman resumes, in-flight jobs picked up from baton state — a shift change, not a resurrection); and outside the image, scheduled wakes are the deliberate cadence — event-first where the runtime supports it, a timer sweep as the floor at the interval Dale sets under his wake policy, with the cadence's own burn reported by the budget service, and every restart re-registering the agent's standing watches from disk (OS-126–OS-131; spec in META_OS.md, "Recovery: the crew survives the machine dying"). (Workstream OS-001–OS-131; spec in META_OS.md, "Meta OS as a real working system".)
Stretch, gated on core being VERIFIED: SAM 3.1 reading build screenshots shared over the bus, visual checks joining the brief.

## Architecture (grounded in the real repo, verified 2026-10-22)

Repo: `~/workspace/repos/muse-relay` (GitHub `Mrfentmen/muse-relay`). The bus stays dumb transport; Relay Intelligence is a new `intel/` package beside the existing orchestration layer, exactly the way `mos/` sits on `jobs.py` today.

**Existing systems we build on (verified in code):**
- Transport: Upstash Redis lists; default list `muse-bus`, rooms `muse-bus:room:<name>` (`relay_common.bus_key/clean_room`). Plain-text `<nick>: <text>` protocol, trimmed to newest 500 per list.
- Presence: heartbeat keys `muse-bus:presence:<nick>` (120s TTL) + status keys, renewed by `send.py`/`poll.py`/`watch.py`; nick claims `muse-bus:nickclaim:<nick>`; capability registry `mos/capabilities.py` (`muse-bus:cap:<nick>`, 15-min stale prune).
- Job queue: `jobs.py` (774 lines) — job hashes under `muse-bus:job:<id>`, spec at `:<id>:spec`, atomic claim mutex `:<id>:claim` (SET NX, 30-min default lease), HMAC-SHA256 v2 signed jobs with keyring file, wire announcements JOB:/CLAIM:/PROGRESS:/DONE:/BLOCKED:/REQUEUE:. **Gaps the Foundation workstream closes: no structured `files`, `deps`, or `attempts/max_attempts` fields exist yet** (they live as prose in specs today), and no `last_progress_at/last_heartbeat_at` fields.
- MOS: `mos/overseer.py` (dispatch + tick + acceptance verification), `mos/worker.py` (DM poll/claim loop), `mos/acceptance.py` (file-exists / tests-pass / command-ok / contains checks). Dispatch reuses these instead of reinventing them.
- Ingestion sources: `digest.py` (Redis arithmetic, LRANGE paging), `store.py` (local per-room JSONL with timestamps), `export.py`. Briefings read through one snapshot function (FND-013).
- Viewer: `bus.html` — **identical to `index.html`** (3,267 lines; repo invariant, `_redirects` maps / → /bus.html). Panels plug in via the existing IIFE pattern (`U.panel`, `H.connect`, `H.poll`, `snapshot()`), beside the existing Tasks/Polls/Karma/Chess panels. Deployed as the Cloudflare Pages site behind https://muse-relay-live.pages.dev.
- Job board: `crew-board.html` (730 lines) already renders the job namespace in four columns; Dashboard extends it with Files/Deps/Attempts instead of building a second board.
- Tests: 23 test files, 326 test methods at grounding, on `tests/fake_redis.py` + `tests/helpers.py`. All intel tests follow the same pattern — no network, no live Redis in unit tests.

**New code (all in `intel/` + `intel.py` CLI):**
- `intel/spark_client.py` — one Spark gateway: pluggable transport (HTTP from env config; FakeTransport for tests), retries, per-call budget caps, spend ledger at `muse-bus:intel:spend`.
- `intel/ingest.py` — snapshot(room) → a dict of messages, jobs, presence, caps.
- `intel/brief.py` + `intel/prompts/` — briefing engine (Hana's lane).
- `intel/dispatch.py` — plan parse/validate/post (Pax's lane, Hana's prompts/evals).
- `intel/watchdog.py` + `intel/thresholds.py` — detectors (Milo's lane).
- `intel/store.py` — intel Redis records: `muse-bus:intel:brief:<room>:<ts>`, `muse-bus:intel:alert:<id>`, `muse-bus:intel:dispatch:<id>`, watchdog beat `muse-bus:intel:wd:beat`.
- Dashboard panels inside `bus.html`/`index.html` + `crew-board.html` extensions (Rowan's lane), consuming the same records the CLI writes — one source of truth per feature.

**Hard rules baked into every lane file:**
- Statuses only: VERIFIED / CODE-INSPECTED / UNIMPLEMENTED / BLOCKED.
- Never post to the bus without Dale's word. Build traffic goes to the build room only if Dale approves it (GOV-002 / FND-001). No real bus history in fixtures without Dale's approval (BRF task, held).
- Secrets never on the bus, never in specs, never in commits. Job signing keyring and Spark credentials live in env/files with chmod 600, exactly like the existing token file.
- Watchdog v1 never mutates job state. It alerts; humans (or mos tick) act.
- Dispatch never auto-posts. Every plan passes a human approval gate.
- Git workflow conflict resolved (INT-012, 2026-10-27): GOV-003 ruled 2026-10-24 that the build lives in a NEW repo, Mrfentmen/meta-os, with muse-relay merged in as the base layer; crew batches land as single commits on main of meta-os. Every lane file now carries the ruled note; the relay README's branch wording describes the base's own job flow only.


**The Meta OS layer (added 2026-10-22, Dale's decision):**
- Base: Debian 12 (bookworm) amd64, one base only (OS-005). The image is an appliance: it exists to run the crew, nothing else.
- Build: scripted Packer + QEMU unattended install from `os/` in the repo is the primary pipeline (OS-007); a live-build ISO is the named fallback (OS-008). Every image is reproducible from a clean checkout in one command, stamped at /etc/metaos-version (OS-020), and ships with zero credentials — secrets enter once, at firstboot (OS-012).
- Services are the repo's real processes under systemd, under the `relay.target` boot target: relay-bus (presence/watch/store stack) → relay-jobs (`jobs.py` queue + lease sweep) → relay-overseer (`mos/overseer.py`) + relay-worker@ fleet (`mos/worker.py` per nick) → relay-watchdog (`intel/watchdog.py`, also the supervisor of last resort for silent stalls) → relay-brief (oneshot boot brief) → dashboard kiosk (local `bus.html` full screen). Boot order and the full service map live in META_OS.md.
- Agent-native system rules: per-worker cgroup limits (relay-workers.slice, OS-035), crew activity in journald plus the existing store.py JSONL, one update path (`metaos-update`, OS-021), one rescue boot entry (OS-022).
- Working-system layer (vision upgrade, Dale 2026-10-22; spec in META_OS.md): an agent-driver contract makes any CLI coding agent a managed OS process (first driver: Muse Code, OS-053–OS-057); the MCP gateway runs as the `relay-mcp-gateway.service` daemon so tools act as system libraries for every agent process (OS-058–OS-059); a skills loader mounts Dale's skills collections as installable applications at process launch (OS-065). Depth layer (Dale 2026-10-22: "more depth than just MCPs and skills — and not too much, cause it will just be bloat"): exactly four system services — memory service, identity + capabilities, workspace/artifact store, budget/resource policy (OS-078–OS-092; minimal in-window, depth in Phase B). Phase B [B] extends this post-hackathon: OpenCode + Freebuff drivers, meta-pkg package flow, Dale's desktop session, image update channel, hardening, and the four services' depth. Completion contract (Dale 2026-10-22: the phone connection is the bottleneck, and the answer is autonomy, not remote control): Dale orders once from his phone and hears back once — done, verified — or once when a decision only he can make blocks the work; between those moments the queue owns the jobs, the crew self-coordinates on the cloud bus, and the watchdog self-repairs before it reports (OS-093–OS-100; spec in META_OS.md, "The completion contract"). Mind images (Dale 2026-10-22): how fast and how well the crew works comes down to its instructions, its tools, its environment, and the information around it — so Meta OS assembles all four into one versioned, measurable launch bundle and boots minds the way it boots machines (OS-101–OS-109; spec in META_OS.md, "Mind images"). Wake layer (Dale 2026-10-22: a sleeping agent cannot know there is work — "how can I get them to look at the bus if they don't know?" — and Dale pokes nobody): the watchman, a per-machine resident CLI program, reads the queue (claims/leases, never the drift-prone message counter), rings the bell, and the agent wakes already briefed; a timer sweep is the fallback, the watchdog guards the watchman, and a reassignment is a baton pass — a continuation prompt from the job record handed to the next agent program, never a restart from zero (OS-118–OS-125; spec in META_OS.md, "The bell"). Recovery layer (Dale 2026-10-22: the biggest of his top-three bottlenecks, and the original reason he built the bus — VMs shut off, sessions die, and the crew only returns when he touches the phone): three laws — state lives on disk, never in a session (queue, job records, memory service, journal are the truth; a session is disposable); the building reopens itself (crew services are systemd-enabled under relay.target, so power returning is the relaunch: lease sweep expires dead claims, the watchman resumes, in-flight jobs resume from baton state — a reboot is a shift change, proven by the OS-126 plug-pull drill and reported by the boot brief's in-flight-recovered count, OS-127); and the cadence knob for the crew outside the image (Dale's observation is correct: the every-other-day messages from Rawan, Milo and Hana ARE timer wakes on their runtimes — made deliberate: event-first where supported, a timer sweep as the floor at the interval Dale approves in OS-131 under the OS-124 wake policy, cadence burn reported by the OS-085 budget service, and after any runtime restart the first wake re-registers the agent's standing watches from disk and resumes — OS-130 [B] kit; spec in META_OS.md, "Recovery").
- Guardrail: Meta OS is the chassis, Relay Intelligence is the payload. The Spark critical path (FND→engines→dashboard→demo) ships and demos on a normal machine even if the image track slips; Dale rules the boot's place in the demo at the Nov 1 checkpoint (OS-004).

## Lane summary

| Lane | Owner | Tasks | Owns |
|---|---|---|---|
| PAX | Coordination, Foundation, Dispatch engine, Integration/QA, demo + submission, Meta OS image pipeline + services, agent drivers | 122 |
| ROWAN | Dashboard: viewer panels + crew-board, viewer deploys, Meta OS boot-to-dashboard experience, agent process views | 63 |
| HANA | Briefings engine, prompts, evals, dispatch language quality, the Meta OS boot brief | 63 |
| MILO | Watchdog detectors + drills, demo audio/narration, Meta OS supervisor/watchdog service + driver supervision | 75 |
| BUFFY | Fixtures, eval data volume, docs, demo scripts, regression, Meta OS build volume + package docs | 82 |
| DALE | Decisions and approvals only — few, decisive | 27 |
| **TOTAL** | | **432** |

## Phases

- **Phase 0 — Groundwork (Oct 26):** decisions (GOV), room, intel skeleton, wire formats frozen (FND-016), fixtures started.
- **Phase 1 — Engines (Oct 27–29):** briefings, dispatch, watchdog built against fixtures in parallel lanes.
- **Phase 2 — Faces (Oct 29–31):** dashboard panels on frozen payloads; crew-board extensions; first deploys.
- **Phase 3 — Integration (Oct 31–Nov 2):** end-to-end loops, drills tournament, load + cost checks, failure drills. Nov 1 checkpoint: Dale's stretch go/no-go (GOV-007) AND the Meta OS demo go/no-go (OS-004).
- **Meta OS track (parallel, Oct 26–Nov 2):** image pipeline and services land beside Phases 0–3 without blocking them; **image content freeze Nov 2 12:00 ET** (before the Nov 3 demo freeze), exceptions only under OS-003. Detail: SCHEDULE.md Meta OS track; spec: META_OS.md.
- **Phase 4 — Demo lock (Nov 2–3):** feature freeze Nov 2 21:00 ET, rehearsals, fallback video, demo freeze Nov 3 21:00 ET.
- **Phase 5 — Submission (Nov 4):** final package, Dale delivers/submits before 9:00 PM ET.

## Dale decisions parked (do not invent answers)

- **GOV-001** Confirm Spark access: which Muse Spark endpoint/key the build uses and that the $150 hackathon API credit is attached to it — **RULED by Del 2026-10-24, refined the same day: do NOT burn the $150 credit key on the build; it would be gone within a day and then unavailable when testing actually needs it. SAVE the key. If it is used at all, use at most HALF the credit ($75) for build/testing, and keep the other half ($75) reserved for the presentation and for making sure the OS actually works at the end. Which endpoint/key the day-to-day build uses instead is still unspecified — do not invent one. **UPDATE RULED by Del 2026-10-26 ~16:32 EDT: FakeTransport is REJECTED for the build — no mock or fake code anywhere in the Meta OS / Relay Intelligence build; the Spark transport must be REAL. This supersedes the FND-005 fallback ("if unconfirmed, build proceeds on FakeTransport") and every task whose acceptance leans on FakeTransport (FND-005, FND-007, BRF-040, BRF polish toggle) — those tasks are reworked to the real transport. Real Spark access is now a HARD BLOCKER: the endpoint/key is still unnamed, the $150 credit claim link was still "coming soon" at the last portal check (2026-10-26 ~03:14 EDT), and claiming requires his card on the Meta Model API account. The $75 build/testing + $75 reserved budget rule still stands.** **FINAL RULED by Dale 2026-10-28: the blocker is resolved — real Spark access exists. Daily build/model usage runs on Muse Spark 1.3 Contributor (real Meta Model API traffic on the cheapest tier, quoted by Dale at ~$0.10 per 1M tokens in and ~$0.20 per 1M tokens out), switched by env through the existing MUSE_RELAY_INTEL_MODEL / MUSE_RELAY_INTEL_ENDPOINT / MUSE_RELAY_INTEL_API_KEY config block — a real provider swap, never FakeTransport (that ban stands). The $150 credit is preserved for demo week and the final verification use. Every unattended invocation runs with MUSE_RELAY_INTEL_BUDGET_CAP_USD and MUSE_RELAY_INTEL_PER_CALL_USD set; no unattended loop runs uncapped. Evals stay scored on the tier actually demoed, so prompt tuning and demo never split into two models by accident.
- **GOV-002** Decide bus posting rule for the build (build room only vs main bus) and whether any real bus history may be used in fixtures — **RULED by Del 2026-10-24: the bus does not get touched unless we need to fix it, or need to upgrade it because the build is making a literal operating system on it. **Fixtures question RULED by Del 2026-10-26 ~16:32 EDT: no fake bus history — he does not approve fabricated history; fixtures use REAL bus history (read-only use; the no-touch posting rule above still stands).**
- **GOV-003** Decide git workflow for this build: repo README says feature branches + overseer merge; your standing crew rule elsewhere is push straight to main — pick one for muse-relay this build — **RULED by Del 2026-10-24, superseding the either/or: make a NEW repo and merge muse-relay into the new repo; work from the new repo, with the relay as the base and Meta OS built on top of it there.**
- **GOV-004** Approve the crew roster and lanes (Pax coordinate/integrate, Rowan dashboard, Hana briefings, Milo watchdog + audio, Buffy volume/docs) or reassign — **RULED by Del 2026-10-24: roster CONFIRMED as proposed. Added by Del: every crew member has their own Buffy and their own OpenCode — each agent uses their own OpenCode, their own agents, and their own Buffys.**
- **GOV-005** Approve alert copy deck (every watchdog explanation + suggested fix wording) before demo freeze
- **GOV-006** Approve dashboard help overlay copy ('What am I looking at?')
- **GOV-007** Decide the stretch call on SAM 3.1 screenshot reading: only if core is VERIFIED by Nov 1 checkpoint — go or no-go
- **GOV-008** Pick the demo time slot / presentation format once organizers publish options
- **GOV-009** Approve final submission package before Pax submits anything anywhere
- **GOV-010** Decide post-hackathon repo posture: intel/ stays public on muse-relay main, or splits to its own repo
- **GOV-011** (Meta OS) Name DECIDED by Dale 2026-10-22: **Meta OS** — built for Meta agents on Meta's models (renamed from the early-draft working name). Remaining approvals: the two-layer positioning (OS-001) — still open. The demo hardware target (OS-002) was RULED by Del 2026-10-24: "The demo hardware is called Meta OS."
- **GOV-012** (Meta OS) Rule the Nov 1 OS go/no-go (OS-004): cold boot opens the demo, or it does not

## Complete task list

★ = critical path. Every task has exactly one lane owner.

### FOUNDATION — bus / queue / protocol extensions + intel core (34 tasks)

- **FND-001** [DALE] Decide build room name and bus posting rule for the hackathon build (proposed room: build-relay-intel; main bus stays untouched until you say so) ★
  - Acceptance: Decision recorded in MASTER_PLAN.md decisions log; every lane file updated to match
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
- **FND-029** [MILO] Define watchdog state keys with Pax: muse-bus:intel:wd:<nick> hash (last_seen, last_progress, claimed_jobs) and alert dedupe key shape ★
  - Acceptance: Key shapes written into intel/store.py docstring; Milo and Pax both reference the same names in code
- **FND-030** [MILO] Specify lease/progress thresholds as config constants (stall = no progress AND no heartbeat for N minutes; default 10) in one shared module intel/thresholds.py
  - Acceptance: thresholds.py exists with named constants + comments; watchdog and tests import from it only
- **FND-031** [MILO] Audit jobs.py sweep + mos/overseer.py tick for reusable lease-expiry logic; write findings to intel/notes/milo-reuse-audit.md
  - Acceptance: Notes file names exact functions reused vs rewritten, with file:line references
- **FND-032** [HANA] Define brief record schema with Pax (fields: room, generated_at, kind morning|onjoin|ondemand, sections, source_window, model, spend_id) ★
  - Acceptance: Schema written in intel/README.md; brief.py validates records against it in a test
- **FND-033** [HANA] Inventory existing text sources for briefs: digest.py output, store.py JSONL, jobs list --json, presence.py, mos capabilities — map each to a brief section in intel/notes/hana-source-map.md
  - Acceptance: Source map covers all five sources with the exact command/function producing each
- **FND-034** [HANA] Set brief length budgets per kind (morning <= 220 words, onjoin <= 150, ondemand <= 300) as constants in intel/brief.py
  - Acceptance: Constants exist; a test fails a generated brief that exceeds budget

### BRIEFINGS (43 tasks)

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
- **BRF-039** [PAX] Review Hana's brief record schema against dashboard payload needs with Rowan; freeze by end of Day 2 ★
  - Acceptance: Freeze note in intel/README.md with date; dashboard mock uses the frozen fields
- **BRF-040** [PAX] Verify brief fallback path end to end on the live-shape stack (fake Redis + FakeTransport failure injection)
  - Acceptance: Fallback brief produced and stored; status CODE-INSPECTED notes plus test output recorded
- **BRF-041** [PAX] Sign off brief eval results before demo lock: rubric pass rate recorded in MASTER_PLAN progress notes
  - Acceptance: Pass rate written down with brief ids; failures either fixed or listed as known limits
- **BRF-042** [ROWAN] Define brief panel payload contract with Hana (fields the viewer receives per brief)
  - Acceptance: Contract listed in dashboard spec; panel renders from a static example payload
- **BRF-043** [ROWAN] Render brief age/staleness in payload examples so the panel design accounts for it from day one
  - Acceptance: Example payloads include fresh and stale briefs; panel mock shows both states

### DISPATCH (40 tasks)

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
- **DSP-037** [ROWAN] Define dispatch box payload: goal in, plan preview out (jobs, files, deps graph summary, budgets), approve action shape ★
  - Acceptance: Payload contract in dashboard spec; static example renders in panel mock
- **DSP-038** [ROWAN] Render plan dependency order as an indented list (no graph library) in the preview mock
  - Acceptance: Mock shows diamond plan in correct topological reading order
- **DSP-039** [ROWAN] Design approval affordance states: idle, planning, plan-ready, posting, posted, rejected — with exact button labels
  - Acceptance: State list in dashboard spec; mock cycles all six states
- **DSP-040** [ROWAN] Ensure dispatch box never implies auto-posting: label copy states a human approves every plan
  - Acceptance: Copy present in mock and spec; Pax reviews wording

### WATCHDOG (46 tasks)

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

### DASHBOARD (46 tasks)

- **DSH-001** [ROWAN] Write the dashboard spec hackathon/relay-intelligence/DASHBOARD_SPEC.md: panels (Crew Board, Brief, Dispatch, Alerts), data sources per panel, refresh cadence, no-build-step constraint (bus.html is one static file) ★
  - Acceptance: Spec reviewed by Pax; every panel names its exact Redis keys or payload source
- **DSH-002** [ROWAN] Extend bus.html via its existing plugin pattern (U.panel, H.connect, H.poll, snapshot()) — add intel panel module skeleton intelPanel with empty states ★
  - Acceptance: Panel appears in bus.html panels aside on the live-shape page; existing panels unaffected (manual + test crewboard signing tests pass)
- **DSH-003** [ROWAN] Crew Board panel: render presence (muse-bus:presence:*) with nick, status text, host from nick claims, last-seen age ★
  - Acceptance: Panel on fixture data shows all fixture nicks with ages ticking
- **DSH-004** [ROWAN] Crew Board panel: per-agent current job (from jobs list --json equivalent reads) with title, progress age, lease countdown ★
  - Acceptance: Fixture agent mid-job renders with countdown decreasing on refresh
- **DSH-005** [ROWAN] Crew Board panel: capability chips per agent from muse-bus:cap:<nick> (caps + roles)
  - Acceptance: Chips match caps fixture exactly; stale agents (cap record older than 15 min) render dimmed
- **DSH-006** [ROWAN] Crew Board panel: idle/working/blocked visual states keyed to job status and watchdog state per agent
  - Acceptance: All three states demonstrated with fixture data and screenshotted for the plan record
- **DSH-007** [ROWAN] Brief panel: render latest brief per room (sections, generated_at, age, TEMPLATE marker when fallback) ★
  - Acceptance: Panel renders morning fixture brief with all sections; stale brief shows age label
- **DSH-008** [ROWAN] Brief panel: brief history dropdown (last 7 briefs) with kind labels morning/onjoin/ondemand
  - Acceptance: History list matches store records in fixture
- **DSH-009** [ROWAN] Brief panel: 'Brief me now' button producing an on-demand brief request through the viewer's existing send path — disabled until Dale's posting rule allows viewer posts; ship read-only otherwise ★
  - Acceptance: Button state matches Dale decision; no code path posts without the decision
- **DSH-010** [ROWAN] Dispatch panel: goal input + Plan button rendering PAX's plan-preview payload (jobs, files, deps order, budgets) ★
  - Acceptance: Preview renders the golden diamond plan readably on desktop and phone widths
- **DSH-011** [ROWAN] Dispatch panel: approve/reject buttons wired to the dispatch approval shape; approve requires the human confirm step (native confirm + explicit 'Post N jobs' label) ★
  - Acceptance: Approve flow in mock posts nothing; real wiring gated behind Pax integration task
- **DSH-012** [ROWAN] Dispatch panel: posted-plan tracker — after posting, panel lists real job ids with live status pulled from job reads
  - Acceptance: Tracker on posted fixture plan matches jobs list output
- **DSH-013** [ROWAN] Alerts panel: live alert feed (severity color per Milo's mapping, kind, subjects, age, explanation, suggested fix) ★
  - Acceptance: Feed renders all fixture alerts with correct colors and text
- **DSH-014** [ROWAN] Alerts panel: ack/resolve buttons calling the alert lifecycle endpoints/shapes from intel store contract
  - Acceptance: Ack on a fixture alert persists and re-renders as acknowledged
- **DSH-015** [ROWAN] Alerts panel: empty state ('All quiet — watchdog alive, last tick HH:MM:SS') driven by watchdog beat key, plus a red 'watchdog silent' state if beat is stale ★
  - Acceptance: Both states rendered from fixture beat keys (fresh vs expired)
- **DSH-016** [ROWAN] Header strip: mission-control summary line (agents online, jobs open/claimed/done today, critical alerts count) above panels
  - Acceptance: Counts match fixture totals exactly
- **DSH-017** [ROWAN] Mobile pass: panels stack cleanly at 390px wide (iPhone), dispatch box usable one-handed ★
  - Acceptance: Screenshot at 390px saved; no horizontal scroll; tap targets >= 40px
- **DSH-018** [ROWAN] Dark-theme consistency: all new UI uses bus.html's existing palette (#0d1117/#161b22/#30363d, GitHub-dark accents) — no new color scheme
  - Acceptance: Visual diff review vs existing panels; no off-palette hex values in new CSS
- **DSH-019** [ROWAN] Accessibility pass: severity never carried by color alone (icon + text label), buttons labeled, contrast checked
  - Acceptance: Each alert shows text severity; contrast notes in spec
- **DSH-020** [ROWAN] Performance pass: panel polling reuses bus.html's existing poll cycle (no extra timers); job reads paged/capped
  - Acceptance: Network view in test shows no new interval timers; render of 200-job fixture stays responsive
- **DSH-021** [ROWAN] Error states per panel: Redis unreachable, token missing, empty room — each panel fails independently with a plain message
  - Acceptance: Killing one data source degrades only its panel in fixture test
- **DSH-022** [ROWAN] Add dashboard deep links: #intel/brief/<id> and #intel/alert/<id> hash routes scroll to and highlight the item
  - Acceptance: Links from a brief's Watch items land on the alert card highlighted
- **DSH-023** [ROWAN] Extend crew-board.html: add Files and Deps columns to job cards using the new jobs.py fields ★
  - Acceptance: Cards show files/deps when present, unchanged when absent (old jobs)
- **DSH-024** [ROWAN] Extend crew-board.html: add Attempts badge (attempts/max) turning amber at max-1 and red at max
  - Acceptance: Badge states verified against fixture jobs at 0, max-1, max
- **DSH-025** [ROWAN] Extend crew-board.html: alert ribbon — jobs with open critical alerts get a ribbon linking to the alert
  - Acceptance: Ribbon appears exactly on fixture jobs with critical alerts
- **DSH-026** [ROWAN] Keep index.html and bus.html identical (repo invariant: they are the same file) — every dashboard change applied to both or via the repo's existing sync approach ★
  - Acceptance: diff bus.html index.html is empty after changes
- **DSH-027** [ROWAN] Deploy viewer to Cloudflare Pages project muse-relay-live after each merged dashboard batch; verify production URL serves the new build (check a marker string) ★
  - Acceptance: Live URL fetch contains the build marker; deploy logged with date + commit
- **DSH-028** [ROWAN] Add a demo mode toggle (?demo=1) that enlarges type, hides token/setup chrome, and pins the four intel panels open ★
  - Acceptance: Demo URL renders presentation layout; normal URL unchanged
- **DSH-029** [ROWAN] Write dashboard smoke checklist (10 manual checks) and run it before every deploy
  - Acceptance: Checklist file in repo docs/; run results logged per deploy
- **DSH-030** [ROWAN] Screenshot set for submission: crew board busy, brief panel, dispatch preview, alert firing — at desktop and phone sizes
  - Acceptance: 8 screenshots saved under hackathon/relay-intelligence/submission-assets/
- **DSH-031** [ROWAN] Handle long brief text: collapsible sections in Brief panel, default open for Blocked
  - Acceptance: Long fixture brief renders without breaking panel layout
- **DSH-032** [ROWAN] Add sparkline-free 'today' counters (jobs done today, briefs generated, alerts fired/resolved) from intel store records
  - Acceptance: Counters match fixture record counts
- **DSH-033** [ROWAN] Ensure the viewer stays read-only-safe: with a read-only token pasted, all intel panels still render (writes degrade to disabled buttons with explanation)
  - Acceptance: Read-only walkthrough logged; no panel throws
- **DSH-034** [ROWAN] Add keyboard shortcut: 'i' toggles intel panels focus mode for the demo (hide chat log, panels full width)
  - Acceptance: Shortcut works in demo mode; documented in DEMO.md shot notes
- **DSH-035** [ROWAN] Cross-browser check: dashboard in Chrome + Safari (iOS) rendering of all four panels
  - Acceptance: Check results logged; any Safari-only bug filed as its own task before demo freeze
- **DSH-036** [ROWAN] Freeze dashboard feature set at demo freeze; after freeze only bugfixes with Pax sign-off
  - Acceptance: Freeze noted in SCHEDULE log; post-freeze changes list exists (empty or signed)
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

### INTEGRATION / QA (31 tasks)

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
- **INT-020** [MILO] Watchdog integration: alerts visible in brief (Hana) and dashboard (Rowan) with identical ids and severities in the e2e runs ★
  - Acceptance: E2E log shows id match across all three surfaces
- **INT-021** [MILO] Drill tournament: run kill/collision/dead-dep drills back to back in one session, timed, as the demo will do
  - Acceptance: Combined drill log under 6 minutes wall time
- **INT-022** [MILO] Threshold final tune after integration fixtures grow: rerun tuning table, lock thresholds for demo
  - Acceptance: Locked values committed to thresholds.py with a comment citing the tuning doc
- **INT-023** [MILO] Verify watchdog behavior during the load check (200 jobs) — no alert storms, dedupe holds
  - Acceptance: Alert count for the load scenario recorded and sane (dedupe proven)
- **INT-024** [HANA] Brief integration: briefs generated during e2e runs scored against rubric the same day
  - Acceptance: Scores appended to eval log for e2e brief ids
- **INT-025** [HANA] Verify brief/dashboard consistency: brief panel shows the same brief text the CLI shows for the same id
  - Acceptance: Side-by-side check logged for 3 brief ids
- **INT-026** [HANA] Write the 'known limits' brief section honestly (what briefs cannot see: DM rooms unless polled, trimmed history)
  - Acceptance: Limits text appears in README and submission notes verbatim
- **INT-027** [HANA] Cold-start test: a lane member who skipped a day uses only the morning brief to resume work; log what they missed
  - Acceptance: Cold-start log names gaps; gaps fixed or documented as limits
- **INT-028** [ROWAN] Dashboard integration: all four panels live against the integration environment for a full crew day ★
  - Acceptance: Integration day log with screenshots at start/mid/end
- **INT-029** [ROWAN] Fix the top 5 integration-day dashboard issues before feature freeze (ranked with Pax)
  - Acceptance: Fix list with commit refs in schedule log
- **INT-030** [ROWAN] Verify demo mode on the actual demo machine/browser Dale will present from
  - Acceptance: Verification note names the machine/browser; screenshot saved
- **INT-031** [ROWAN] Confirm Cloudflare Pages deploy rollback path (previous deployment restore) and write it on the failover card
  - Acceptance: Rollback steps written and the previous deployment id recorded before demo day

### DEMO / SUBMISSION (28 tasks)

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
- **DEM-025** [DALE] Approve the demo scenario and the exact goal sentence Dale will type live ★
  - Acceptance: Approval recorded in DEMO.md header
- **DEM-026** [DALE] Pick narration takes (Milo provides two per segment)
  - Acceptance: Picks recorded in the audio take log
- **DEM-027** [DALE] Approve all judge-facing copy: one-pager, submission description, 60-second summary ★
  - Acceptance: Approvals recorded per document
- **DEM-028** [DALE] Deliver the final demo / submit the entry in the official system before the deadline ★
  - Acceptance: Submission confirmation captured (screenshot or confirmation id) in submission-assets/

### DOCS (18 tasks)

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
- **DOC-011** [HANA] Write the prompts explainer: how the brief and dispatch prompts work, with v1->v2 change rationale
  - Acceptance: Explainer in intel/prompts/README.md
- **DOC-012** [HANA] Write eval methodology note (fixtures, manifests, rubric, how scores were produced) for judges who ask 'how do you know it works'
  - Acceptance: Note in intel/evals/README.md with links to logs
- **DOC-013** [HANA] Document brief limitations honestly (window caps, template fallback, no DM visibility by default)
  - Acceptance: Limitations section in intel/README.md
- **DOC-014** [HANA] Write example briefs gallery: 3 real generated briefs (quiet, busy, stall) with one-line annotations
  - Acceptance: Gallery in docs/ using fixture outputs only
- **DOC-015** [PAX] Fact-check every doc claim against the code before submission (the Pax verification pass) ★
  - Acceptance: Checklist signed in SUBMISSION.md; false claims fixed or removed
- **DOC-016** [PAX] Update INSTANCES.md with the intel layer note for future instances (what intel is, where the docs live)
  - Acceptance: INSTANCES.md diff is additive and accurate
- **DOC-017** [ROWAN] Document dashboard panels in the viewer help (what each panel reads, refresh behavior)
  - Acceptance: Help text shipped in bus.html overlay or docs/
- **DOC-018** [ROWAN] Write the deploy runbook for muse-relay-live (build marker, deploy, verify, rollback)
  - Acceptance: Runbook in docs/; Buffy follows it once successfully

### GOVERNANCE — Dale decisions (10 tasks)

- **GOV-001** [DALE] Confirm Spark access: which Muse Spark endpoint/key the build uses and that the $150 hackathon API credit is attached to it ★
  - Acceptance: Access path confirmed in writing to Pax before Day 1 build starts; if unconfirmed, build proceeds on FakeTransport and this stays BLOCKED
- **GOV-002** [DALE] Decide bus posting rule for the build (build room only vs main bus) and whether any real bus history may be used in fixtures ★
  - Acceptance: Decision recorded; Hana's held fixture task follows it
- **GOV-003** [DALE] Decide git workflow for this build: repo README says feature branches + overseer merge; your standing crew rule elsewhere is push straight to main — pick one for muse-relay this build ★
  - Acceptance: One workflow recorded and copied into every lane file
- **GOV-004** [DALE] Approve the crew roster and lanes (Pax coordinate/integrate, Rowan dashboard, Hana briefings, Milo watchdog + audio, Buffy volume/docs) or reassign ★
  - Acceptance: Roster confirmed or edits recorded in MASTER_PLAN.md
- **GOV-005** [DALE] Approve alert copy deck (every watchdog explanation + suggested fix wording) before demo freeze
  - Acceptance: Deck marked approved with date
- **GOV-006** [DALE] Approve dashboard help overlay copy ('What am I looking at?')
  - Acceptance: Approval recorded in the copy deck
- **GOV-007** [DALE] Decide the stretch call on SAM 3.1 screenshot reading: only if core is VERIFIED by Nov 1 checkpoint — go or no-go
  - Acceptance: Decision recorded at the Nov 1 checkpoint with the core status it was based on
- **GOV-008** [DALE] Pick the demo time slot / presentation format once organizers publish options
  - Acceptance: Slot recorded in SCHEDULE.md demo day plan
- **GOV-009** [DALE] Approve final submission package before Pax submits anything anywhere ★
  - Acceptance: Approval recorded in SUBMISSION.md
- **GOV-010** [DALE] Decide post-hackathon repo posture: intel/ stays public on muse-relay main, or splits to its own repo
  - Acceptance: Decision recorded in the post-demo note

### STRETCH — SAM 3.1 visual checks (gated) (5 tasks)

- **STR-001** [PAX] Gate the stretch: verify core (brief, dispatch, watchdog, dashboard) statuses are VERIFIED before any STR task starts
  - Acceptance: Gate note written with per-feature status
- **STR-002** [HANA] Add screenshot digest to brief payload: latest build screenshots shared over the bus listed with timestamps for SAM pass
  - Acceptance: Brief record gains screenshot refs on fixture with --img posts
- **STR-003** [MILO] Feed watchdog drill screenshots (dashboard states) into the SAM evaluation set as known-good/known-bad pairs
  - Acceptance: Pairs saved with labels in intel/evals/sam/
- **STR-004** [BUFFY] Build SAM eval set: 20 bus-shared screenshots with ground-truth visual check labels (build ok / build broken / unclear)
  - Acceptance: Set + labels complete; sources are the crew's own screenshots only
- **STR-005** [ROWAN] Render SAM visual verdicts in the Brief panel as a Visual checks subsection when data exists
  - Acceptance: Subsection renders from example payload; absent cleanly when no data


### META OS — the operating system workstream (125 tasks)

The chassis under everything above: a Debian-based image that boots straight into the crew — and, per Dale's 2026-10-22 vision upgrade, a real working system: agent drivers, the MCP gateway as a system service, skills as applications, exactly four depth services (memory, identity/capabilities, workspace/artifacts, budget), and a Phase B daily-driver track. Full spec in META_OS.md. The OS track is parallel to the Spark critical path, never in front of it — if the image slips, Relay Intelligence still ships and demos on a normal machine (guardrail, META_OS.md). Tasks tagged [B] = Phase B (post-hackathon); they never gate the demo or the submission.

- **OS-001** [DALE] Ratify the name — **Meta OS**, Dale's call 2026-10-22 (built for Meta agents on Meta's models; renamed from the early-draft working name) — and approve the two-layer positioning (Meta OS the machine, Relay Intelligence the mind) for all copy, README, and the boot screen ★
  - Acceptance: Decision recorded in the MASTER_PLAN decisions log; the name is used consistently in META_OS.md, os/README.md, and Rowan's boot screen (OS-045)
- **OS-002** [DALE] Pick the demo hardware target: name the physical demo laptop (existing machine or named spare) and confirm the VM image as the secondary target ★
  - Acceptance: Hardware named in META_OS.md demo targets; nobody builds for an unspecified machine
- **OS-003** [DALE] Set the post-freeze exception rule for the image: what may still change after image content freeze (proposed: Spark-layer payload files only; base, packages, and units frozen solid)
  - Acceptance: Rule written into SCHEDULE.md at the freeze line; Pax enforces it at the freeze gate and logs any exception
- **OS-004** [DALE] Rule the Nov 1 checkpoint go/no-go: the Meta OS cold boot opens the demo, or the dashboard on a normal machine opens it ★
  - Acceptance: Decision recorded in the build journal and DEMO.md updated to the chosen opening before demo freeze
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
- **OS-042** [ROWAN] Boot experience: the graphical session autologins and lands on the mission-control dashboard full screen (Chromium kiosk on the local viewer) with zero clicks ★
  - Acceptance: Power-on reaches the dashboard untouched in the boot test recording
- **OS-043** [ROWAN] Boot checklist view: while services start, the dashboard shell shows bus, queue, supervisor, watchdog, and brief flipping live as units report ready
  - Acceptance: Checklist is driven by real unit/ready states, never a timer; a failed unit shows red on its own line
- **OS-044** [ROWAN] Local viewer rule: on the OS the dashboard is served from the image's local bus.html/index.html plus crew-board.html, not the Pages URL, panels identical
  - Acceptance: Network unplugged after boot: dashboard and panels still render locally; Spark-backed features degrade to the INT-021 states, nothing hangs
- **OS-045** [ROWAN] Identity on screen: Meta OS name, image version from /etc/metaos-version (OS-020), and the crew roster on the boot and landing views
  - Acceptance: On-screen version matches the stamp; no stock OS branding visible anywhere in the boot path
- **OS-046** [ROWAN] Display resilience: the kiosk is supervised and relaunches after a Chromium crash or resolution change, never a black screen at demo time
  - Acceptance: Killing Chromium in test brings the dashboard back within 15s
- **OS-047** [ROWAN] Demo mode default on the demo image: the kiosk boots straight into the DSH-028 demo mode profile; non-demo images unaffected
  - Acceptance: Demo image boots into demo mode; a stock image from the same pipeline does not
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

#### Meta OS as a working system — drivers, MCP service, skills loader (OS-053–OS-066, in-window)

The vision upgrade (Dale, 2026-10-22; spec: META_OS.md, "Meta OS as a real working system"). In-window scope is deliberately narrow: one driver contract, one working driver (Muse Code), the gateway daemon, the skills loader, and the integration proof. Everything wider is Phase B below.

- **OS-053** [PAX] Agent-driver adapter contract: os/drivers/CONTRACT.md defines the driver interface — start(job_spec) against a signed spec, stop(), heartbeat() in bus progress format, artifacts + status record out — plus a stub driver and a written conformance checklist any future driver must pass ★
  - Acceptance: Contract + checklist committed; the stub driver passes every checklist item on the test image
- **OS-054** [PAX] Muse Code driver: implement the contract against Meta's Muse Code CLI — a claimed job spec launches Muse Code as a managed child process, progress streams as heartbeats, changed files + logs return as the artifact record ★
  - Acceptance: Driver passes the OS-053 conformance checklist; one fixture job completes end to end through the driver on the test image
- **OS-055** [PAX] Driver demo proof: a Spark-dispatched job (DSP pipeline) is claimed by the overseer, handed to the Muse Code driver, executed, and its artifacts + DONE land back in the queue — the OS-055 run is the demo beat's evidence ★
  - Acceptance: Full loop green on the frozen demo image with the state pack; timings recorded for DEMO.md
- **OS-056** [MILO] Driver supervision integration: driver processes run as systemd units in a relay-drivers.slice under the OS-034 contract (systemd owns process death; the watchdog owns silent stalls); driver heartbeats feed the existing WDG stall detectors unchanged
  - Acceptance: A driver process appears in the slice on the test image; kill -9 restarts per contract with a watchdog event note and no false stall alert
- **OS-057** [MILO] Driver stall drill: wedge a driver process (alive, heartbeat stale); the watchdog raises the same STALL alert as for a crew worker and the driver is restarted per contract without touching other drivers
  - Acceptance: Drill logged: STALL alert inside the demo threshold, clean restart, sibling driver undisturbed
- **OS-058** [PAX] MCP gateway daemon unit: relay-mcp-gateway.service runs Dale's MCP gateway (~/workspace/mcp-gateway) as a system daemon under relay.target; every agent process on the machine reaches the tool estate through the gateway's one local endpoint
  - Acceptance: Unit active at boot on the test image; a crew worker and a driver process both call a gateway tool through the local endpoint
- **OS-059** [PAX] Gateway bake: the gateway stack is baked beside /opt/relay at a pinned state with its server catalog available on the image; zero secrets baked (keys enter via the OS-012 firstboot env only)
  - Acceptance: Image sweep (OS-012) finds no gateway credential material; gateway serves its catalog offline on the test image
- **OS-060** [ROWAN] Dashboard agent-process view: live list of driver processes (agent, driver, job, heartbeat age, resource use) in the crew board/dashboard, fed by the same records the supervisor writes
  - Acceptance: Starting/stopping a driver on the test image shows up in the view within one poll cycle; a stale heartbeat renders visibly stale
- **OS-061** [ROWAN] Dashboard tool + app inventory: a panel showing which MCP servers the gateway offers and which skill apps the loader has mounted on this machine
  - Acceptance: Panel matches gateway catalog + loader state on the test image; an unmounted skill does not appear
- **OS-062** [HANA] Boot brief: drivers + tools + apps line — the boot brief states which agent drivers are available, that the MCP gateway is healthy, and which skill apps are mounted, each in one line from live state
  - Acceptance: Lines present and correct on the test image; with the gateway down the brief says so instead of omitting the line (OS-050 honesty rule)
- **OS-063** [BUFFY] Working-system package pass: every packages.txt addition for the gateway, the Muse Code CLI, and driver runtimes documented in os/PACKAGES.md with rationale; sizes into os/SIZES.md
  - Acceptance: Every new manifest line has a PACKAGES.md entry; SIZES.md reflects the grown image
- **OS-064** [BUFFY] Skills loader fixture pack + docs: seed skill folders for image tests, and the loader contract documented as a section of os/README.md (what mounting means, where skills land, how a process opts in)
  - Acceptance: Fixture skills mount in the OS-065 test; a cold reader can mount one from the README alone
- **OS-065** [PAX] Skills loader: mounts skills-2 collection folders into an agent process's launch environment, the way an OS loads apps — a process started on Meta OS begins with its skills already available ★
  - Acceptance: A driver process launched with a mounted skill shows the skill active in its first action; an unmounted control run does not
- **OS-066** [PAX] Working-system integration QA: one recorded end-to-end run on the image — boot → brief lists drivers/tools/apps → dispatch a job → Muse Code driver executes → watchdog watches the process → dashboard shows it — added to the boot test checklist
  - Acceptance: Run recorded green on an RC image; any failure files a fix task in the owning lane, not a workaround

#### Depth — the four system services (OS-078–OS-092; minimal in-window, depth in Phase B)

Dale's call (2026-10-22): "more depth than just MCPs and skills — and not too much, cause it will just be bloat." Exactly four OS-level services, each fixing a lived failure (spec: META_OS.md, "Depth: the four system services"). No other subsystems get added. In-window tasks are the minimum for an honest demo; the depth itself is tagged [B].

- **OS-078** [PAX] Memory service (minimal): a journaled, versioned OS-level store — per-agent memory + shared crew memory — mounted into every agent process at start (home-directory model); the service runs in the image under relay.target ★
  - Acceptance: A process restarted on the test image reads back its own prior memory entries and the shared crew entries; every write is journaled with a version stamp
- **OS-079** [HANA] Brief surfaces memory + budget: the boot brief (and morning brief) opens with settled decisions pulled from the memory service instead of re-deriving them, and carries one spend-vs-budget line per lane from the budget config (OS-085)
  - Acceptance: Brief on fixture state names the planted settled decision verbatim from memory and shows spend vs budget per lane; with the memory service down the brief says so (OS-050 honesty rule)
- **OS-080** [PAX] Identity + capability files: every crew and driver process runs as a named identity with an explicit capability file (files it may write, bus posting on/off, spend on/off, network on/off), loaded at process start and enforced by the OS layer, not by prompt text ★
  - Acceptance: Capability files exist for every crew identity on the test image; a process launched with a capability removed cannot perform that action even when its job spec asks for it
- **OS-081** [MILO] Capability refusal enforcement (the demo path): an action attempted outside a process's grant is refused by the OS, the refusal is written as an alert record with a plain-English explanation, and the watchdog surfaces it like any other alert ★
  - Acceptance: Drill on the test image: a staged process attempts a bus post outside its grant → refused, alert record exists, explanation names the identity, the action, and the missing capability (DEMO.md Shot 8b evidence)
- **OS-082** [DALE] Approve the capability policy defaults: the standing rules as OS policy — no bus posting without Dale's word, no spend or network reach beyond grant, file writes confined to owned paths — as the shipped default capability set ★
  - Acceptance: Defaults recorded in the decisions log with date; the shipped capability files match the approved set exactly
- **OS-083** [PAX] Workspace/artifact store (minimal): a git-backed versioned shared filesystem in the image; dispatched jobs deposit work products there and reference them by path in the job record instead of pasting through chat ★
  - Acceptance: A driver-executed job's outputs land in the store with a version history; the job record carries artifact paths, and the files open from those paths on the test image
- **OS-084** [ROWAN] Dashboard capability + artifact views: the crew board shows each process's identity and capability summary, artifact links from job records open the store paths, and a capability refusal renders as a visible banner tied to Milo's alert record
  - Acceptance: On the test image the dashboard lists artifacts for a completed job and the OS-081 refusal shows as a banner within one poll cycle
- **OS-085** [MILO] Budget config + pre-limit warnings: per-process and per-lane API/compute budgets as config the job queue reads before claiming (a lane at cap does not claim new Spark work) and the watchdog warns at a threshold before the cap, not after the silence
  - Acceptance: Fixture lane driven to its warning threshold produces a budget warning alert; at cap, the queue holds new claims for that lane and the hold is visible in the brief's budget line (OS-079)
- **OS-086** [PAX] [B] Memory scoping depth: per-agent vs shared scoping enforced by the memory service — a process reads shared crew memory and its own, never another agent's private memory
  - Acceptance: Cross-agent private read attempt is refused and logged on the daily machine; shared reads unaffected
- **OS-087** [BUFFY] [B] Memory compaction: scheduled compaction of the journaled store — settled decisions pinned, superseded entries folded, full version history retained and restorable
  - Acceptance: A compacted store restores any prior version on demand; the boot brief's settled-decisions line is unchanged across a compaction
- **OS-088** [ROWAN] [B] Capability editor in mission control: Dale views and edits per-identity capability grants from the dashboard; every change is journaled with who/when and takes effect at the process's next start
  - Acceptance: A grant edited in the editor is enforced after restart and the change appears in the journal; no edit path bypasses Dale's signed-in action
- **OS-089** [BUFFY] [B] Artifact retention/dedup: retention policy for the artifact store (age/size rules per job class) plus content-hash dedup so identical outputs are stored once and referenced many times
  - Acceptance: Policy doc committed; a duplicate-artifact fixture run stores one copy; expired artifacts are listed before any deletion, never silently dropped
- **OS-090** [PAX] [B] Budget priority classes: lanes/jobs carry priority classes; when budget contention hits, high-priority work claims budget first and low-priority work waits instead of starving randomly
  - Acceptance: Contention fixture: the high-priority job completes inside budget while the low-priority job waits with its state visible, not failed
- **OS-091** [MILO] [B] Budget preemption + forecasting: the watchdog can preempt (pause, not kill) low-priority spenders approaching a cap, and projects end-of-day spend from the ledger rate so Dale sees a breach coming hours ahead
  - Acceptance: Forecast line appears in the daily brief with a stated confidence basis; a preempted job resumes cleanly when budget frees
- **OS-092** [HANA] [B] Memory-aware daily brief depth: the daily brief (OS-075) surfaces long-term memory — decisions aging out, commitments made weeks ago that are due, context a fresh agent would miss — drawn from the memory service, not re-derived from raw history
  - Acceptance: Two weeks into daily use, a brief names one aged commitment correctly from memory with its original date; nothing surfaced that memory does not contain

#### The completion contract — order once, hear back when it's done (OS-093–OS-100, in-window)

Dale's bottleneck (2026-10-22) was the phone connection — and his correction the same night sets this workstream: NOT a remote control (remote-typing apps already do that — "we can't just be Amphetamine but Meta"), but autonomy. The completion contract (spec: META_OS.md, "The completion contract: order once, hear back when it's done"): Dale's phone appears exactly twice — one plain-English order in, one push out when the work is verified done or blocked on a decision only he can make. In between, the queue owns the work, the crew self-coordinates on the bus, and the watchdog repairs before it reports; silence from the crew means still working, by design. All eight tasks are in-window on the OS track before the image freeze; the tailnet survives only as machine plumbing (artifact/data movement on the machine's side) and carries no Dale-facing feature and no task.

- **OS-093** [PAX] The order door: Dale's one plain-English order — sent from his phone, from anywhere — lands on the cloud bus and becomes a signed job set owned by the queue the moment it arrives; `relay-uplink.service` under relay.target holds the machine's side of that connection (reconnect/backoff; health in the boot checklist + boot brief) so an order always has somewhere to land ★
  - Acceptance: An order sent from a phone, with no further contact from Dale, dispatches and work starts on the machine; kill the machine's network mid-flight and the uplink recovers unaided without losing the order
- **OS-094** [PAX] Jobs belong to the queue: a job's full state — spec, progress, artifacts (via the OS-083 store) — lives in the queue and the store, never only inside an agent session; any worker can resume a job from its deposited progress instead of restarting it from zero
  - Acceptance: Kill a worker mid-job and end its session entirely: on lease expiry a different worker resumes the job from deposited progress and completes it; nothing about the job existed only in the dead session
- **OS-095** [MILO] The self-repair ladder: on a stall, the watchdog acts before it reports — nudge the worker, then restart the worker, then reassign the job to another agent — each rung journaled with its reason; Dale is contacted at no rung
  - Acceptance: Three staged stalls (unresponsive worker, dead worker, job held by the wrong worker) are each resolved by the correct rung with zero Dale contact; every ladder action appears in the journal and the next brief
- **OS-096** [MILO] Attempt budgets + the escalation gate: every job carries an attempt budget spanning all repair rungs; an exhausted budget — or a blocker that is genuinely Dale's call (money, permission, direction) — parks the job visibly and fires the one blocked push (OS-097); nothing retries forever, and nothing escalates that the crew can settle itself
  - Acceptance: A deliberately impossible job burns exactly its budget, parks, and escalates exactly once — no loop, no duplicate pushes; a crew-fixable blocker in the same drill is resolved with zero escalation
- **OS-097** [HANA] The two pushes: the done push fires only when the overseer closes a job on passed acceptance checks — "All done" plus the plain-English summary of what was built and what was verified — and the blocked push carries the exact question a parked job is waiting on; no third push type exists ★
  - Acceptance: A completed job produces exactly one push whose summary matches the artifact record; a parked job produces exactly one blocked push naming the decision in plain English; a job closed without passing its checks produces no done push
- **OS-098** [ROWAN] The board explains the silence: the dashboard shows the loop's state at a glance — jobs owned by the queue, the current shift worker per job, repair-ladder actions taken, parked jobs awaiting Dale — so when Dale does look, no pushes reads as work proceeding, not as a dead room
  - Acceptance: Throughout the OS-099 drill, the board matches the journal at every stage: who holds each job, what the ladder did, and what (if anything) waits on Dale
- **OS-099** [BUFFY] The completion drill, end to end: one real order from Dale's phone, the phone then ignored; mid-job, agents are rotated out and killed (process killed, session ended) — the work still completes through pickup and self-repair, and exactly one done push arrives; includes the machine-off hour: an order queued in the cloud while the machine is down is picked up and worked at boot
  - Acceptance: Drill report filed: the job completed with zero Dale contact after the order; every agent death shows in the journal with a pickup after it; the push count for the whole run is one (done) — and the offline order completed after boot with zero loss, zero duplicates claimed
- **OS-100** [DALE] Contract acceptance, live: Dale gives one real order from his phone and puts the phone down; he touches nothing until it rings — blocked (only if a decision is genuinely his) or done
  - Acceptance: Dale confirms the crew finished without him, the done summary matched what was actually built and verified, and any blocked push he received asked a question that was really his to answer; any failure becomes a fix task before the image freeze, not a demo-day surprise

#### Mind images — the OS boots minds, not just machines (OS-101–OS-109; format + loader + environment brief + one A/B result in-window)

Dale's lever (2026-10-22): how fast and how well the crew completes work comes down to (1) how its instruction files and skills are implemented, (2) the tools it has, (3) the operating environment it works in, (4) the information around it. Meta OS's answer is the **mind image** (spec: META_OS.md, "Mind images: the OS boots minds, not just machines"): one versioned bundle the OS assembles at process launch — constitution (the agent's AGENTS.md-equivalent standing instructions + identity), selected skills, memory mount (OS-078), capability grant (OS-080), tool grants via the MCP gateway, and an environment brief (a launch-time snapshot: repo state, bus state, who is working on what, budget remaining). Dale's four levers are the image's layers. Because the bundle is versioned, it is improvable and measurable: same job, two image versions, compare time and acceptance. In-window minimum: the format, the loader, the environment brief, and ONE A/B comparison result (the DEMO.md Shot 6c proof).

- **OS-101** [PAX] Mind-image bundle format: the bundle spec — constitution (AGENTS.md-equivalent standing instructions + identity), selected skills, memory mount reference (OS-078), capability grant (OS-080), MCP tool grants, environment brief slot — as one versioned, inspectable artifact with a version stamp and changelog pointer ★
  - Acceptance: Format doc + one hand-built example bundle committed; the bundle parses, names its version, and every layer resolves to a real source (instruction file, skill folder, memory mount, grant, gateway tools, brief)
- **OS-102** [PAX] Loader integration: process launch assembles and mounts the mind image — this EXTENDS the OS-065 skills loader (skills become one layer of the assembly) rather than duplicating it; crew workers and driver processes alike launch from an image, none hand-assembled ★
  - Acceptance: A worker and a driver process both launch from bundles on the test image; the launched process's effective instructions/skills/memory/grants match its bundle exactly; OS-065's fixtures still pass through the new path
- **OS-103** [HANA] Environment brief generator: at launch, snapshot the agent's surroundings — repo state, bus state, who is working on what, budget remaining — and render it as the bundle's information layer, in the brief's plain-English standard
  - Acceptance: A generated brief names the repo's current state, the live jobs and their owners, and the lane's budget remaining, all matching the sources at generation time; stale fields are labeled with their age, never silently presented as current
- **OS-104** [BUFFY] Mind-image versioning + changelog discipline: every image change is a version bump with a changelog entry naming what changed and why (skill revised, instruction tightened, brief field added); no unversioned edits to a bundle any process has launched from
  - Acceptance: Changelog present and complete for the fixture images; an attempted unversioned edit is caught by the OS-105 harness's bundle hash check and fails the run loudly
- **OS-105** [BUFFY] A/B eval harness: a fixed suite of small jobs, runnable against two mind-image versions end to end, recording completion time and acceptance result per job per version, side by side
  - Acceptance: Harness runs the full suite against two fixture versions unattended and emits the comparison table; a tampered or unversioned bundle aborts the run instead of producing numbers
- **OS-106** [MILO] The measured A/B run + image-defect attribution: execute the OS-105 harness for the demo's one comparison (bare launch vs mind image) under watchdog measurement, and tag stall patterns attributable to the image — missing skill, bad instruction, thin environment brief — as image defects feeding the revision loop, not as worker failures
  - Acceptance: One A/B result in hand: same jobs, both versions, times + acceptance outcomes recorded; at least one observed stall in the runs is correctly attributed (image defect vs worker failure) with the journal evidence named
- **OS-107** [ROWAN] Mind images on the board: every running process shows the mind image it carries (name + version) in the agent-process view, and the OS-106 A/B result — times, acceptance, versions — has a board view fit to be the demo's Shot 6c screen
  - Acceptance: During the OS-106 run, the board's per-process versions match the launched bundles, and the A/B view renders the recorded result without hand-built slides
- **OS-108** [DALE] Launch-bundle contents policy: Dale approves what may enter a mind image — which instruction files count as constitution, which skill sources are trusted, what never enters (secrets live in firstboot env files, OS-012, never inside an image)
  - Acceptance: Policy recorded in the decisions log; the OS-101 example bundle and the OS-102 loader both conform — a bundle containing a non-approved source is refused at assembly
- **OS-109** [PAX] [B] Image revision loop tooling: eval results propose the next image as a diff — which layer changes, on what evidence from OS-105/OS-106 numbers — for Dale's approval before any revised image ships; the loop that makes the crew faster by versioned iteration, with evidence, as routine maintenance
  - Acceptance: From one real A/B result, the tooling produces a reviewable image diff tied to the measured defect; nothing auto-applies — an approved diff becomes the next version under OS-104 discipline

#### Federation — many machines, one crew (OS-110–OS-117; minimum in-window, fast lane Phase B)

Dale's question (2026-10-22): if other people run Meta OS, how do the machines connect and work together — through the CLI, on the same shared thing, even over local Wi-Fi? The mechanism is the bus, productized (spec: META_OS.md, "Federation: many machines, one crew"). The room already lives in the cloud (Upstash Redis) and the relay stack is CLI/Python on every machine, so any Meta OS box with the room address + room key joins the same room and the same job queue — jobs live in the queue, not on a machine, so an agent on any connected machine can claim work posted from any other, and presence puts every machine's crew on one board. The genuinely new work is small: the join flow, cross-machine presence, and trust. Trust is stated honestly: bus nicks are unauthenticated, so federation rides on (a) signed jobs (the HMAC-SHA256 v2 signing already in jobs.py) — a machine accepts work only from crews on its local trust list — and (b) capability badges (OS-080) clamped to local policy in both directions. Default posture: closed. In-window minimum: join flow, presence/grouping, trust enforcement, the two-machine drill. The local Wi-Fi fast lane is Phase B [B].

- **OS-110** [PAX] `meta join` + firstboot room config: one command (and a firstboot prompt step beside OS-012) takes a room address + key into the chmod-600 env files, announces the machine on the room — machine name, crew nicks, each agent's mind-image version and capability badge — and starts claiming per local trust settings ★
  - Acceptance: A fresh test image joins the fixture room with the command alone; the announcement appears in the room naming machine, nicks, image versions, and badges; the room key appears nowhere in the image, the bus record, or any log
- **OS-111** [ROWAN] Cross-machine presence + board grouping by machine: the crew board groups agents by the machine they run on (machine name as the group header, agents with image version + badge under it), so a two-crew room reads as two crews, not one flat nick list
  - Acceptance: With the OS-113 drill's two machines live, the board shows both machines as groups with the correct agents, versions, and badges under each; a machine dropping off the room greys its whole group without disturbing the other
- **OS-112** [MILO] Signed-job trust list enforcement in the overseer: the overseer verifies a job's HMAC-SHA256 v2 signature against the local trust list before any local agent may claim it, and clamps the posting crew's badge claims to local policy; refusal is a logged, board-visible event, never a silent skip ★
  - Acceptance: A job signed by a trusted crew is claimable; the same job unsigned or signed by an untrusted key is refused at claim time with the refusal in the job record and the watchdog's log; the trust list itself lives only in the local chmod-600 config
- **OS-113** [BUFFY] Federation drill: two machines, one room — a signed job is posted from machine A, claimed and completed by an agent on machine B, acceptance verified by A's overseer, and the completion closes under the completion contract with exactly one done-push to the order's origin
  - Acceptance: Drill log shows the full path (post on A → claim on B → artifacts deposited → acceptance pass → one done-push) with machine names at each hop; run twice, both green, before image freeze
- **OS-114** [MILO] Trust negative test: an untrusted machine joins the fixture room and posts a job (and re-posts it under a spoofed crew nick); both attempts are refused by the trusted machine's overseer, logged, and surfaced — words on the bus, no work exchanged
  - Acceptance: Zero claims of the hostile jobs by any trusted agent across the test window; both refusals appear in the log with the reason (untrusted signer / signature absent) and the drill leaves the fixture room clean
- **OS-115** [DALE] Federation policy decision: Dale rules the standing posture — default closed (no foreign crew trusted until he adds one) — and the demo room's posture for the gated federation beat (DEMO.md): which second machine joins, under what trust list, in which room
  - Acceptance: Policy recorded in the decisions log; OS-110's defaults and OS-112's fixture trust lists match the ruling; if the demo beat's machine is not named, the beat stays gated off and the demo runs exactly as scripted without it
- **OS-116** [PAX] [B] Local Wi-Fi fast lane: machines on the same network discover each other automatically (mDNS-style local discovery) and sync claims + artifact movement directly — lower latency, and the room keeps working locally through an internet drop, reconciling to the cloud record when it returns; the cloud bus stays the single source of truth, the lane is transport only
  - Acceptance: Two machines on one LAN discover each other with zero configuration; a job hands off over the local lane measurably faster than the cloud path; with the WAN unplugged mid-job the room keeps working and reconciles to the cloud record on reconnect with no duplicate claims and no lost jobs
- **OS-117** [HANA] [B] Crew-of-crews brief: the morning brief gains a federation section — what each joined machine's crew did, cross-machine jobs and their state, trust events (joins, refusals) overnight — in the brief's plain-English standard, so Dale reads one brief for every machine he runs
  - Acceptance: A generated brief over a two-machine fixture window names both machines' completions and any trust refusal, matching the room record; a single-machine brief renders the section absent, not empty-padded

#### The wake layer — the bell that rings sleeping agents (OS-118–OS-125; watchman + Muse wake + baton + drill in-window, PC shim + sweep Phase B)

Dale's bottleneck (2026-10-22): Rawan, Milo, and Hana are separate agent instances on other runtimes and other machines, and a sleeping agent cannot know there is work — "How can I get them to look at the bus if they don't know? They wouldn't be able to know." Dale does not want to touch the phone: nobody pokes anybody. The honest law comes first (spec: META_OS.md, "The bell: how sleeping agents get woken"): an agent that is not running cannot know anything, so something small, cheap, and always on watches the door and rings the bell; the expensive brain wakes only when there is work. That something is the **watchman** — `relay-watchman`, a small resident CLI program inside the OS (a unit in the service map, not an agent, not a dashboard feature) — which reads the job queue, claims and leases as its source of truth, never the bus message counter whose drift Dale already lives with, watches worker heartbeats, and works the self-repair ladder's mechanical rungs on its machine (OS-095). The wake starts the agent's session with the job as its brief (spec, mind image, acceptance checks, assembled by the OS-102 loader): the agent never polls, it opens its eyes already holding its orders. And when the ladder reaches reassign, the job is never restarted from zero: workers deposit progress into the job record and the artifact store as they go (the baton state, OS-094/OS-083), and the watchman composes a continuation prompt from that record — goal, deposited progress, files touched, what remains, acceptance checks — and hands it to the next agent program, which picks up where the previous worker left off (OS-125). In-window: the watchman, the Muse wake adapter, watchman health, the baton pass (same-program continuation proven; the cross-program pass is the stretch line), and the hands-free drill. The PC wake shim and the timer sweep are Phase B [B] — marked honestly: the in-window drill proves the bell on a Muse runtime; the scattered crew's other runtimes join through the shim after the freeze pressure is off.

- **OS-118** [PAX] The watchman: `relay-watchman`, a small resident CLI program inside the OS (`relay-watchman.service` under relay.target, a unit in the service map with the same standing as the other units — not an agent, not a dashboard feature; the pattern exists in muse-relay's watch.py/poll.py listeners) that watches the job queue for work addressed to its machine's agents, watches those agents' heartbeats once working, rings the bell for sleepers, and works the self-repair ladder's mechanical rungs on its machine (OS-095: nudge, restart, reassign via the OS-125 baton pass) — detection reads job claims/leases, never a bus message counter, so the seen-counter drift failure mode is designed out rather than patched ★
  - Acceptance: On the test image the watchman notices a newly posted job for a local agent within one poll cycle and emits a wake event naming job + agent; a worker whose heartbeat goes stale draws the ladder's nudge from the watchman on the same watch cycle; replaying or skipping bus messages changes nothing (detection provably reads job state, not message counts); the watchman makes no model calls and holds no session of its own
- **OS-119** [MILO] Muse wake adapter: when the bell rings for a sleeping Muse instance (the Hana/Rawan class of runtime), the adapter starts the agent's session through its runtime's session mechanism with the job already in its hands — spec, mind image via the OS-102 loader, acceptance checks — so the agent's first act is the job, never a poll ★
  - Acceptance: A sleeping fixture agent, given a posted job and zero human contact, wakes, claims, and starts work with the bundle in place — its first bus action is the claim/progress on that job, not a status check; a job addressed to a different agent does not wake it
- **OS-120** [PAX] [B] PC agent wake shim: the same bell for agents living outside the image on Dale's PC — a small local watchman script on the PC rings and starts the local agent's session with the job as its brief, so a PC-resident crew member joins the never-stops loop without a Meta OS install
  - Acceptance: With the shim running on the PC and its agent fully stopped, a posted job wakes the agent and work starts with no action from Dale; with the shim stopped, the job waits untouched (no phantom claims) until the OS-121 sweep or a crew member picks it up per the ladder
- **OS-121** [MILO] [B] Timer fallback sweep: every agent runtime also wakes on a slow timer to sweep the board and claim anything the bell missed — shift-worker clock-in as the safety net under the bell, so a missed wake delays work by minutes, never forever
  - Acceptance: With the watchman deliberately disabled, a posted job is still claimed within one sweep interval by the timer path alone; with the watchman healthy, sweeps produce zero duplicate claims (lease discipline holds across both paths)
- **OS-122** [MILO] Who watches the watchman: the watchdog treats a dead watchman as a first-class failure — crew-dark: the machine's agents asleep, its jobs invisible to them — attempts the self-repair (restart the watchman) per the OS-095 ladder, and only if the watchman cannot be revived does it earn Dale's blocked-push; per-machine watchman state (alive/dead, last bell, last wake) is published for the board's machine groups (OS-111)
  - Acceptance: Kill the watchman on the fixture machine: the watchdog flags crew-dark within one detector cycle, the restart revives it, and no Dale push fires; kill it beyond the restart's power and exactly one blocked-push fires naming the machine; the board's group for that machine reads watchman-dead while it lasts
- **OS-123** [BUFFY] The hands-free drill: Dale posts one order and touches nothing afterwards — no phone, no pokes, no manual starts. A sleeping agent on another machine/runtime is woken by the bell (OS-118/OS-119), completes the job under the completion contract, and exactly one done-push comes back
  - Acceptance: The drill log proves the negative space: zero Dale actions after the order (no session starts, no nudges from him), the wake event precedes the agent's first action, acceptance passes, exactly one done-push total; run twice, both green, before image freeze
- **OS-124** [DALE] Wake budget policy: Dale rules the wake budgets — max wakes per hour per agent, quiet hours if any, which agents are bell-only vs bell+sweep — wired to the budget service (OS-085) so waking is a managed resource like spend, not an accident
  - Acceptance: Policy recorded in the decisions log; OS-118/OS-119/OS-121 defaults match the ruling; a fixture agent at its wake cap stays asleep with the held job visible on the board as waiting-on-wake-budget, not lost
- **OS-125** [MILO] The baton pass: when the ladder reaches reassign, the watchman does not restart the job from zero — it composes a continuation prompt from the job record (goal, the progress the worker deposited as it went, files touched, what remains, acceptance checks — the baton state OS-094 and OS-083 make possible) and hands it to the next agent program, which picks up exactly where the previous worker left off; workers deposit progress as they go, or there is no baton to pass
  - Acceptance: Drill: a worker is killed mid-job; the watchman passes the baton and the job completes with no repeated work — the record shows the deposited progress, zero duplicated file changes, and a continuation prompt that names what remains instead of restating the whole job. In-window the continuation is proven same-program; the cross-program pass (e.g. Muse → Freebuff, possible because both are pre-installed in the image) is the named stretch line — run before freeze if the drivers allow, honestly reported either way

#### Recovery — the crew survives the machine dying (OS-126–OS-131; inside-image recovery in-window, external cadence kit Phase B, cadence policy in-window)

Dale's framing (2026-10-22): this is the biggest of his top-three bottlenecks and the original reason he built the bus. The failure: agent VMs shut off, runtimes restart, sessions and everything in them die — and the crew only comes back when Dale touches the phone. His own observation names the mechanism that already half-works: Rawan, Milo and Hana DO message him untouched, every other night or day — a clock/cron on their side wakes them — and he wants it more often, and reliable across shutdowns. The spec (META_OS.md, "Recovery: the crew survives the machine dying") builds on three laws. **(1) State lives on disk, never in a session:** the queue, job records (baton state), memory service, and journal are the truth; a session is disposable, and anything not written to the store is not counted as known. **(2) The building reopens itself:** the crew runs as systemd services under relay.target, enabled, not started by hand — so a reboot IS the relaunch: power returns → services start → the jobs.py lease sweep expires dead claims → the watchman resumes ringing → in-flight jobs are picked up from their deposited baton state. No human relaunches anything, ever. The honest contrast: a normal machine leaves a pile of dead sessions for a human to resurrect; Meta OS treats a reboot as a shift change. The boot checklist gains the proof line — the boot brief reports the in-flight jobs recovered count. **(3) The cadence knob:** outside the image, agents come back via scheduled wakes — Dale is right that his crew's stray messages are timer wakes — made deliberate: event-first where the runtime supports a hook on bus arrival, a timer sweep as the floor at the interval Dale sets under the OS-124 wake policy, the budget service (OS-085) reporting the cadence's own burn so the knob turns with open eyes, and after ANY runtime restart the first scheduled wake re-registers the agent's standing watches from disk (crons/jobs persist outside sessions; sessions don't) and resumes — the exact mechanism that brings Pax, Milo and Hana back today, named and made deliberate instead of accidental. Phasing, stated honestly: inside-image recovery is in-window (the plug-pull drill is the strongest reliability evidence the demo has, scheduled before the image freeze); the external cadence kit is Phase B [B], but the cadence POLICY decision is in-window, because Dale asked for more frequent messages now.

- **OS-126** [BUFFY] The plug-pull drill: a job is in flight on the test image; the machine's power is cut mid-work (hard power cut / VM kill — not a shutdown); power is restored and nobody touches anything after the cut. The crew self-relaunches from its enabled services, the lease sweep expires the dead claim, the job resumes from its deposited baton state and completes, and exactly one done-push fires — Milo verifies the lease-sweep and resume evidence (with OS-129) rather than the drill grading itself ★
  - Acceptance: Drill log proves the negative space: zero human touches after the power cut (no logins, no manual service starts, no relaunches); the boot brief's recovered count (OS-127) equals the jobs the sweep released; the resumed job's record shows continuation from deposited progress with no repeated work; exactly one done-push total; run twice, both green, on the final RC image before the image freeze
- **OS-127** [HANA] Boot recovery report line: the boot brief gains one line — in-flight jobs recovered at this boot: the count, the job titles, and where each resumed from (baton state at which step) — reconciled against the lease sweep so a job that vanished silently can never produce a clean line; the line is also boot checklist item 13 in META_OS.md
  - Acceptance: After an unclean shutdown in the OS-126 drill, the boot brief names the recovered count and it matches the sweep record exactly; after a clean shutdown the line reads zero recovered, plainly; a fixture job whose record is corrupted produces a brief that says recovery was incomplete and names the job (OS-050 honesty rule) instead of a false all-clear
- **OS-128** [PAX] Disk-state audit test: with the crew mid-work on the test image, kill every session and every process — workers, sessions, dashboard, all of it — without touching the store (queue, job records, memory service, journal). Then inventory what the store alone can answer: every job's spec, progress, baton state, artifacts, and settled decisions must be fully reconstructable by a cold reader who never met the dead sessions ★
  - Acceptance: The audit walks every in-flight job and reconstructs its complete state from the store with zero items answerable only from a dead session's memory; any item that fails is filed as a named leak (which layer kept session-local truth) with a fix task in the owning lane before the image freeze — the audit passes only when the leak list is empty
- **OS-129** [MILO] Watchman state after reboot: the watchman itself survives the machine dying — at boot it rebuilds its picture purely from queue claims and leases (never a stored message counter, so no stale-counter gap and no missed ring across the reboot boundary), resumes ringing for work that landed while the machine was down, and its first post-boot cycle reconciles with the lease sweep; OS-129 also carries the verification half of the OS-126 drill (lease-sweep timing and resume evidence, independently checked)
  - Acceptance: Across the OS-126 power cuts, the watchman's first post-boot cycle rings for every job that arrived during downtime and none are double-rung or missed (drill log, claims read before/after); a deliberately corrupted stored counter value changes nothing in the watchman's behaviour, proving it never reads one; Milo's verification note on the drill is filed separately from Buffy's run log
- **OS-130** [PAX] [B] External crew cadence kit: the recovery pattern for agents living outside the image — one documented kit any agent runtime can adopt: a scheduled sweep entry per agent (wake, re-register standing watches from disk, sweep the queue, work or sleep), an event-hook registration where the runtime supports a bus-arrival trigger, and the restart rule (the first wake after any restart re-registers from disk before claiming) — written for the runtimes the crew actually lives on (Muse instances, Dale's PC), not as abstract documentation
  - Acceptance: The kit is adopted by at least one real external agent end to end: its runtime is restarted (not just its session), the first scheduled wake re-registers its watches from disk, it sweeps and resumes its queue position with zero Dale contact; the kit doc names per-runtime what persists (crons/jobs on disk) vs what dies (sessions) in one table a cold reader can apply to a new runtime
- **OS-131** [DALE] Cadence policy decision: Dale approves the external crew's wake cadence — the sweep interval and the burn ceiling — as policy under the OS-124 wake budgets, with the OS-085 cadence burn report on the table when he rules. Proposed default put to him: event wake primary where a runtime supports it; timer sweep every 30 minutes while an agent holds claimed or open work, relaxing to every 2 hours when it holds none; cadence burn printed per agent per day in the brief's budget line; sweep wakes capped by the OS-124 per-agent wake budget, so the cadence can never outspend the waking policy
  - Acceptance: Policy recorded in the decisions log (interval(s), ceiling, event-first rule); OS-130's kit defaults and the in-image sweep defaults match the ruling; the first week of cadence burn reports exists and Dale has seen the number his cadence actually costs

#### Phase B — the daily driver track (OS-067–OS-077, POST-hackathon) [B]

Fenced off from the hackathon: these start after Nov 4 and never gate the demo or the submission. Spec: META_OS.md, "Daily driver track".

- **OS-067** [PAX] [B] OpenCode driver: implement the OS-053 contract against OpenCode
  - Acceptance: Driver passes the OS-053 conformance checklist; a fixture job completes through it
- **OS-068** [PAX] [B] Freebuff/GLM driver: implement the OS-053 contract against the Freebuff agent, so Buffy runs as an OS-managed process instead of a hand-tended session
  - Acceptance: Driver passes the conformance checklist; a full Freebuff session runs start-to-finish under the supervisor with heartbeats in the bus record
- **OS-069** [BUFFY] [B] meta-pkg package flow v1: apt-style install/list/remove for MCP servers (over the gateway) and skill apps (over the skills repos) — meta-pkg concept doc plus working commands
  - Acceptance: meta-pkg install + remove round-trips one MCP server and one skill on a live Meta OS machine; state survives reboot
- **OS-070** [BUFFY] [B] Package catalog generation: a browsable index of installable MCPs and skills generated from awesome-servers + skills-2 (name, one-liner, size, source)
  - Acceptance: Catalog regenerates from source repos with zero hand edits; every entry resolves to a real package
- **OS-071** [ROWAN] [B] Dale's desktop session: a real login session (beyond the kiosk) whose home screen is mission control — crew board, brief, alerts — the desktop Dale works from
  - Acceptance: Dale logs in and runs a normal working day from the session; kiosk/demo images unaffected
- **OS-072** [PAX] [B] Image update channel: metaos-update grows into a channel — check, stage, apply at reboot, roll back — with a written update policy
  - Acceptance: A staged update applies at reboot on the daily machine and rolls back cleanly on demand; policy doc committed
- **OS-073** [PAX] [B] Hardening pass for a machine holding real keys: firewall defaults, key-only SSH, systemd sandboxing on crew units, the OS-012 secrets sweep re-run under the daily-driver threat model
  - Acceptance: Hardening checklist green; an external port scan of the daily machine shows only intended listeners
- **OS-074** [MILO] [B] Seven-day soak: the full crew + all drivers run unattended on Meta OS for 7 days; the watchdog journal is reviewed end to end
  - Acceptance: Soak report filed: every silent failure in the log has an alert or a filed bug; zero unexplained gaps
- **OS-075** [HANA] [B] Dale's daily brief: the morning brief becomes Dale's actual daily brief on the desktop session — overnight crew results, today's queue, what needs his word — format tuned from real use
  - Acceptance: Two weeks of daily briefs generated on the daily machine; format changes from Dale's feedback are in the prompt history
- **OS-076** [DALE] [B] Daily-driver go/no-go: after the OS-074 soak report, rule whether Meta OS becomes Dale's everyday machine, and name what must work first if the answer is not yet
  - Acceptance: Decision recorded; if conditional, the blocking items exist as tasks with owners
- **OS-077** [DALE] [B] Post-hackathon Meta OS posture: rule whether Meta OS images/releases go public or stay private; read together with GOV-010 (intel/ repo posture)
  - Acceptance: Decision recorded in the decisions log; release docs match the ruling

---
Total: 432 tasks. Per lane: PAX 122, ROWAN 63, HANA 63, MILO 75, BUFFY 82, DALE 27.
