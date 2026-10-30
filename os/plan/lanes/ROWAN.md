# Lane: ROWAN — Dashboard lane. Bus nick: del.

You own: everything a human sees — the four intel panels inside bus.html/index.html, the crew-board.html extensions, demo mode, and every deploy of the viewer to the Cloudflare Pages site behind muse-relay-live.pages.dev. You build against Pax's static payload dev pack from Day 1; you never block on backend lanes. bus.html and index.html are the same file — after every change, diff must be empty.

**Your tasks: 49** (dependency order; ★ = critical path). Full context, architecture, and every other lane's tasks: MASTER_PLAN.md in the parent folder. Schedule: SCHEDULE.md. Demo: DEMO.md.
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

### BRF
- **BRF-042** [ROWAN] Define brief panel payload contract with Hana (fields the viewer receives per brief)
  - Acceptance: Contract listed in dashboard spec; panel renders from a static example payload
- **BRF-043** [ROWAN] Render brief age/staleness in payload examples so the panel design accounts for it from day one
  - Acceptance: Example payloads include fresh and stale briefs; panel mock shows both states

### DSP
- **DSP-037** [ROWAN] Define dispatch box payload: goal in, plan preview out (jobs, files, deps graph summary, budgets), approve action shape ★
  - Acceptance: Payload contract in dashboard spec; static example renders in panel mock
- **DSP-038** [ROWAN] Render plan dependency order as an indented list (no graph library) in the preview mock
  - Acceptance: Mock shows diamond plan in correct topological reading order
- **DSP-039** [ROWAN] Design approval affordance states: idle, planning, plan-ready, posting, posted, rejected — with exact button labels
  - Acceptance: State list in dashboard spec; mock cycles all six states
- **DSP-040** [ROWAN] Ensure dispatch box never implies auto-posting: label copy states a human approves every plan
  - Acceptance: Copy present in mock and spec; Pax reviews wording

### DSH
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

### INT
- **INT-028** [ROWAN] Dashboard integration: all four panels live against the integration environment for a full crew day ★
  - Acceptance: Integration day log with screenshots at start/mid/end
- **INT-029** [ROWAN] Fix the top 5 integration-day dashboard issues before feature freeze (ranked with Pax)
  - Acceptance: Fix list with commit refs in schedule log
- **INT-030** [ROWAN] Verify demo mode on the actual demo machine/browser Dale will present from
  - Acceptance: Verification note names the machine/browser; screenshot saved
- **INT-031** [ROWAN] Confirm Cloudflare Pages deploy rollback path (previous deployment restore) and write it on the failover card
  - Acceptance: Rollback steps written and the previous deployment id recorded before demo day

### DOC
- **DOC-017** [ROWAN] Document dashboard panels in the viewer help (what each panel reads, refresh behavior)
  - Acceptance: Help text shipped in bus.html overlay or docs/
- **DOC-018** [ROWAN] Write the deploy runbook for muse-relay-live (build marker, deploy, verify, rollback)
  - Acceptance: Runbook in docs/; Buffy follows it once successfully

### STR
- **STR-005** [ROWAN] Render SAM visual verdicts in the Brief panel as a Visual checks subsection when data exists
  - Acceptance: Subsection renders from example payload; absent cleanly when no data

## Meta OS — ROWAN (added 2026-10-22, Dale's OS decision)

Your slice of the Meta OS workstream (boot to dashboard experience). Full spec: ../META_OS.md. The OS is the chassis; the Spark critical path in the sections above always wins a scheduling fight. Image content freeze: Nov 2 12:00 ET (SCHEDULE.md).

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

**Working-system additions (vision upgrade, Dale 2026-10-22) — agent processes on the dashboard:**

- **OS-060** [ROWAN] Dashboard agent-process view: live list of driver processes (agent, driver, job, heartbeat age, resource use) in the crew board/dashboard, fed by the same records the supervisor writes
  - Acceptance: Starting/stopping a driver on the test image shows up in the view within one poll cycle; a stale heartbeat renders visibly stale
- **OS-061** [ROWAN] Dashboard tool + app inventory: a panel showing which MCP servers the gateway offers and which skill apps the loader has mounted on this machine
  - Acceptance: Panel matches gateway catalog + loader state on the test image; an unmounted skill does not appear

**Phase B — post-hackathon daily-driver track [B]:**

- **OS-071** [ROWAN] [B] Dale's desktop session: a real login session (beyond the kiosk) whose home screen is mission control — crew board, brief, alerts — the desktop Dale works from
  - Acceptance: Dale logs in and runs a normal working day from the session; kiosk/demo images unaffected

**Depth — the four system services (Dale 2026-10-22; spec: ../META_OS.md, "Depth: the four system services"):**

- **OS-084** [ROWAN] Dashboard capability + artifact views: the crew board shows each process's identity and capability summary, artifact links from job records open the store paths, and a capability refusal renders as a visible banner tied to Milo's alert record
  - Acceptance: On the test image the dashboard lists artifacts for a completed job and the OS-081 refusal shows as a banner within one poll cycle
- **OS-088** [ROWAN] [B] Capability editor in mission control: Dale views and edits per-identity capability grants from the dashboard; every change is journaled with who/when and takes effect at the process's next start
  - Acceptance: A grant edited in the editor is enforced after restart and the change appears in the journal; no edit path bypasses Dale's signed-in action

- **OS-098** [ROWAN] The board explains the silence: the dashboard shows the loop's state at a glance — jobs owned by the queue, the current shift worker per job, repair-ladder actions taken, parked jobs awaiting Dale — so when Dale does look, no pushes reads as work proceeding, not as a dead room
  - Acceptance: Throughout the OS-099 drill, the board matches the journal at every stage: who holds each job, what the ladder did, and what (if anything) waits on Dale
- **OS-107** [ROWAN] Mind images on the board: every running process shows the mind image it carries (name + version) in the agent-process view, and the OS-106 A/B result — times, acceptance, versions — has a board view fit to be the demo's Shot 6c screen
  - Acceptance: During the OS-106 run, the board's per-process versions match the launched bundles, and the A/B view renders the recorded result without hand-built slides
- **OS-111** [ROWAN] Cross-machine presence + board grouping by machine: the crew board groups agents by the machine they run on (machine name as the group header, agents with image version + badge under it), so a two-crew room reads as two crews, not one flat nick list
  - Acceptance: With the OS-113 drill's two machines live, the board shows both machines as groups with the correct agents, versions, and badges under each; a machine dropping off the room greys its whole group without disturbing the other

---
ROWAN total: 63 tasks.
