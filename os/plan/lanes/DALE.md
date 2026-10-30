# Lane: DALE — The boss. Direction, approvals, final demo delivery.

Your list is short on purpose: decisions and approvals only. Everything else has a lane. The build cannot start posting, dispatching, or using real history until your GOV decisions land — they are Day 1, hour 1 items.

**Your tasks: 15** (dependency order; ★ = critical path). Full context, architecture, and every other lane's tasks: MASTER_PLAN.md in the parent folder. Schedule: SCHEDULE.md. Demo: DEMO.md.
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
- **FND-001** [DALE] Decide build room name and bus posting rule for the hackathon build (proposed room: build-relay-intel; main bus stays untouched until you say so) ★
  - Acceptance: Decision recorded in MASTER_PLAN.md decisions log; every lane file updated to match

### DEM
- **DEM-025** [DALE] Approve the demo scenario and the exact goal sentence Dale will type live ★
  - Acceptance: Approval recorded in DEMO.md header
- **DEM-026** [DALE] Pick narration takes (Milo provides two per segment)
  - Acceptance: Picks recorded in the audio take log
- **DEM-027** [DALE] Approve all judge-facing copy: one-pager, submission description, 60-second summary ★
  - Acceptance: Approvals recorded per document
- **DEM-028** [DALE] Deliver the final demo / submit the entry in the official system before the deadline ★
  - Acceptance: Submission confirmation captured (screenshot or confirmation id) in submission-assets/

### GOV
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

## Meta OS — DALE (added 2026-10-22, Dale's OS decision)

Your slice of the Meta OS workstream (name, hardware, checkpoint calls). Full spec: ../META_OS.md. The OS is the chassis; the Spark critical path in the sections above always wins a scheduling fight. Image content freeze: Nov 2 12:00 ET (SCHEDULE.md).

- **OS-001** [DALE] Ratify the name — **Meta OS**, Dale's call 2026-10-22 (built for Meta agents on Meta's models; renamed from the early-draft working name) — and approve the two-layer positioning (Meta OS the machine, Relay Intelligence the mind) for all copy, README, and the boot screen ★
  - Acceptance: Decision recorded in the MASTER_PLAN decisions log; the name is used consistently in META_OS.md, os/README.md, and Rowan's boot screen (OS-045)
- **OS-002** [DALE] Pick the demo hardware target: name the physical demo laptop (existing machine or named spare) and confirm the VM image as the secondary target ★
  - Acceptance: Hardware named in META_OS.md demo targets; nobody builds for an unspecified machine
- **OS-003** [DALE] Set the post-freeze exception rule for the image: what may still change after image content freeze (proposed: Spark-layer payload files only; base, packages, and units frozen solid)
  - Acceptance: Rule written into SCHEDULE.md at the freeze line; Pax enforces it at the freeze gate and logs any exception
- **OS-004** [DALE] Rule the Nov 1 checkpoint go/no-go: the Meta OS cold boot opens the demo, or the dashboard on a normal machine opens it ★
  - Acceptance: Decision recorded in the build journal and DEMO.md updated to the chosen opening before demo freeze

**Phase B — post-hackathon daily-driver calls [B]:**

- **OS-076** [DALE] [B] Daily-driver go/no-go: after the OS-074 soak report, rule whether Meta OS becomes Dale's everyday machine, and name what must work first if the answer is not yet
  - Acceptance: Decision recorded; if conditional, the blocking items exist as tasks with owners
- **OS-077** [DALE] [B] Post-hackathon Meta OS posture: rule whether Meta OS images/releases go public or stay private; read together with GOV-010 (intel/ repo posture)
  - Acceptance: Decision recorded in the decisions log; release docs match the ruling

**Depth — the four system services (Dale 2026-10-22; spec: ../META_OS.md, "Depth: the four system services"):**

- **OS-082** [DALE] Approve the capability policy defaults: the standing rules as OS policy — no bus posting without Dale's word, no spend or network reach beyond grant, file writes confined to owned paths — as the shipped default capability set ★
  - Acceptance: Defaults recorded in the decisions log with date; the shipped capability files match the approved set exactly

- **OS-100** [DALE] Contract acceptance, live: Dale gives one real order from his phone and puts the phone down; he touches nothing until it rings — blocked (only if a decision is genuinely his) or done
  - Acceptance: Dale confirms the crew finished without him, the done summary matched what was actually built and verified, and any blocked push he received asked a question that was really his to answer; any failure becomes a fix task before the image freeze, not a demo-day surprise
- **OS-108** [DALE] Launch-bundle contents policy: Dale approves what may enter a mind image — which instruction files count as constitution, which skill sources are trusted, what never enters (secrets live in firstboot env files, OS-012, never inside an image)
  - Acceptance: Policy recorded in the decisions log; the OS-101 example bundle and the OS-102 loader both conform — a bundle containing a non-approved source is refused at assembly
- **OS-115** [DALE] Federation policy decision: Dale rules the standing posture — default closed (no foreign crew trusted until he adds one) — and the demo room's posture for the gated federation beat (DEMO.md): which second machine joins, under what trust list, in which room
  - Acceptance: Policy recorded in the decisions log; OS-110's defaults and OS-112's fixture trust lists match the ruling; if the demo beat's machine is not named, the beat stays gated off and the demo runs exactly as scripted without it

- **OS-124** [DALE] Wake budget policy: Dale rules the wake budgets — max wakes per hour per agent, quiet hours if any, which agents are bell-only vs bell+sweep — wired to the budget service (OS-085) so waking is a managed resource like spend, not an accident
  - Acceptance: Policy recorded in the decisions log; OS-118/OS-119/OS-121 defaults match the ruling; a fixture agent at its wake cap stays asleep with the held job visible on the board as waiting-on-wake-budget, not lost

- **OS-131** [DALE] Cadence policy decision: Dale approves the external crew's wake cadence — the sweep interval and the burn ceiling — as policy under the OS-124 wake budgets, with the OS-085 cadence burn report on the table when he rules. Proposed default put to him: event wake primary where a runtime supports it; timer sweep every 30 minutes while an agent holds claimed or open work, relaxing to every 2 hours when it holds none; cadence burn printed per agent per day in the brief's budget line; sweep wakes capped by the OS-124 per-agent wake budget, so the cadence can never outspend the waking policy
  - Acceptance: Policy recorded in the decisions log (interval(s), ceiling, event-first rule); OS-130's kit defaults and the in-image sweep defaults match the ruling; the first week of cadence burn reports exists and Dale has seen the number his cadence actually costs

---
DALE total: 27 tasks.
