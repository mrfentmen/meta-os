# TASKS_V3 — the system-after-system program (Del's order 2026-11-01 03:51)

300 tasks: 100 each for Rowan, Hana, Milo. Buffy is not tasked (boss's word).
Every task is implementation work with a checkable result. No filler, no
mock completions: a task is done when its artefact exists and its stated
check passes, and the branch reports it on the bus.

## Standing rules (all lanes)

1. Everything inside mrfentmen/meta-os. Branches off origin/main (or off your
   own lane branch where stated). The 4 excluded bus files stay untouched.
2. Gate-1 rotation: Milo gate-1s Rowan and Hana; Pax gate-1s Milo. A gate-1
   verdict is written on the bus with what was actually re-run.
3. No merge without Del's word. Land on branches, report, hold.
4. Nothing mocked presented as real. Simulated endpoints labelled SIMULATED
   everywhere they appear. Statuses: VERIFIED / CODE-INSPECTED /
   UNIMPLEMENTED / BLOCKED.
5. Scouting is part of the work: every GitHub/tool candidate you file goes
   into your lane's ADOPTIONS.md with repo URL, licence (verified from the
   repo's LICENSE file, not the sidebar), what it would do for us, and the
   risk note. Unlicensed or copyleft-incompatible finds are filed as
   REJECTED with the reason — that still counts as scouting work done.
6. MCP wiring follows Del's standing directive: keyless servers only, wired
   through the local gateway (~/workspace/mcp-gateway/), each with a skill
   doc under ~/workspace/custom-skills/ and a smoke call proving it answers.
   Paper Search's Sci-Hub fallback stays DISABLED permanently.
7. Report on the bus at every stage boundary, not just at the end. Silence
   reads as stuck.
8. Tonight's 20:00 ET test outranks everything until it is done: Hana's UI
   fixes land by 19:00; nobody destabilises main.

---

## ROWAN — platform, Custos, infrastructure (RW-001 … RW-100)

### Custos stage 2 — more eyes (RW-001…RW-015)
- RW-001 Certificate-transparency watcher: poll CT logs for the owned-domain
  list; a newly issued cert for a watched domain becomes a record.
- RW-002 TLS configuration grader: for each watched host, record protocol
  versions and cipher posture; grade against a stated baseline; yellow on drift.
- RW-003 DNS drift watcher: snapshot watched domains' A/AAAA/MX/TXT records;
  any change is a yellow record with the diff.
- RW-004 Security-headers audit: watched hosts scored on HSTS/CSP/X-Frame and
  friends; missing headers recorded, never auto-fixed.
- RW-005 Subdomain exposure sweep: enumerate subdomains of watched domains
  from CT data; flag ones resolving to unexpected networks.
- RW-006 KEV ageing priority: Custos patrol sorts known-exploited CVEs by
  days-since-listing; anything past 30 days unpatched on a watched host is red.
- RW-007 Patrol scheduler: Custos patrols run on the OS job queue with a
  per-source cadence config; prove a full unattended cycle in records.
- RW-008 Alert dedup: identical findings inside a window collapse into one
  record with a count; prove with a synthetic repeat feed.
- RW-009 False-positive log: every dismissed Custos alert lands in a review
  file with a reason; the patrol reads it and stops re-raising the same class.
- RW-010 Custos records viewer: a read-only page listing patrol records by
  tier and source, fed by the real records file.
- RW-011 Watched-host onboarding: a config file + validator; adding a host
  requires an owner note (whose machine is this) — no silent watch targets.
- RW-012 Liveness history: per-host uptime series from patrol records;
  a 7-day view rendered from real data only.
- RW-013 Custos self-test pack: 10 synthetic incidents (expired cert, KEV hit,
  DNS change…) each proven to land in the right tier.
- RW-014 Escalation drill: one synthetic red finding driven through the full
  chain to the labelled SIMULATED endpoint; receipt filed.
- RW-015 Custos PACK.md truth pass: status, proven/unproven lists updated to
  match what stages 1–2 actually do.

### The OS image + Faber loop (RW-016…RW-040)
- RW-016 ttyS0 root-cause: B-001 — reproduce the no-shell login under QEMU,
  bisect the getty drop-ins, land a fix or a proven dead-end report.
- RW-017 Getty fix verification: after RW-016, a scripted boot that reaches a
  working shell on ttyS0, transcript saved.
- RW-018 DHCP proof: scripted boot that captures the in-guest lease (address,
  gateway, DNS) into the boot log.
- RW-019 Dashboard HTTP proof: scripted boot + curl of the dashboard from the
  guest's own loopback and from the host side; responses saved.
- RW-020 Updater live-pull proof: push a harmless commit to a scratch branch
  target, watch metaos-update pull it in-guest; log lines saved.
- RW-021 UTM handover pack: a one-page checklist for Del's first UTM boot
  (CPU model warning first), shipped next to the image.
- RW-022 Image v2 scoping: evaluate debos (from the resource sweep) against
  our hand-rolled build; written verdict with a reproducible mini-build.
- RW-023 Loop STOP drill: prove the STOP file halts the Faber loop mid-cycle
  and the halt is logged; transcript filed.
- RW-024 Loop rollback drill: feed the loop a task that breaks tests; prove
  reset+clean restores the tree and the failure is logged, not hidden.
- RW-025 Loop cap audit: verify daily cap and per-cycle minute cap actually
  bite; both shown stopping a run in logs.
- RW-026 Loop task format v2: LOOP_TASKS.md gains priority + lane fields;
  the loop reads them; old queue still parses.
- RW-027 Firstboot re-run safety: running firstboot twice changes nothing
  the second time; proven by in-guest diff.
- RW-028 Credential hygiene test: an automated grep of the built image for
  the known secret patterns; must come back clean before any image ships.
- RW-029 Image manifest: every baked binary with version + sha256 in one
  file, generated at build time, verified against the running guest.
- RW-030 Overlay session doc: how a working session runs on a qcow2 overlay
  and rolls back; written from a real session, screenshots or transcripts.
- RW-031 Crew login rotation: the in-guest flow for replacing a crew token
  without rebuilding the image; documented + proven in-guest.
- RW-032 Boot timing baseline: measure cold boot to relay.target across 3
  runs; record the numbers in the image STATUS.
- RW-033 Network failure posture: boot with no network; the OS must degrade
  to local-only and say so on the dashboard; proven in QEMU.
- RW-034 Disk-full posture: fill an overlay to 95%; services must fail
  loudly in logs, not silently corrupt; observed behaviour documented.
- RW-035 Time sync check: guest clock vs host after boot + 1h; drift logged.
- RW-036 Loop bus-post format: the loop's optional bus post becomes a
  compact 3-line status (did / gate / next) — implemented + one real post.
- RW-037 Scratch-space guard: loop refuses to run when free disk < a stated
  floor; refusal logged; threshold in config.
- RW-038 Image rebuild reproducibility: rebuild the image from the build
  script; the toolchain hashes must match the manifest (RW-029).
- RW-039 Guest test-suite run: the repo's node suite executed inside the
  guest; result counts filed next to the sandbox counts for comparison.
- RW-040 Faber PACK/OS docs: os/os/METAOS_LOOP.md updated to the loop as it
  actually behaves after the drills.

### MCP + tooling for the platform (RW-041…RW-060)
- RW-041 Wire Playwright MCP into the gateway; smoke call opens a page and
  returns its title; skill doc written.
- RW-042 Wire arXiv MCP; smoke call returns a real paper record; skill doc.
- RW-043 Gateway health board: one script that pings every wired backend and
  prints alive/dead + latency; run and file the first report.
- RW-044 Gateway config lint: a checker that validates every backend entry
  (command exists, env complete) — catches dead entries before runtime does.
- RW-045 Scout: 5 GitHub candidates for certificate/DNS monitoring tools;
  ADOPTIONS.md entries with licences verified.
- RW-046 Scout: 5 GitHub candidates for log/metric collection on tiny VMs.
- RW-047 Scout: 5 GitHub candidates for secret-scanning pre-commit tools;
  compare against our local secret-hygiene MCP; file the verdict.
- RW-048 Evaluate go2rtc (resource sweep): build a proof that pulls one
  public camera feed through it into the Imperium camera wall format.
- RW-049 Evaluate WebWindow (resource sweep): read the whole shell source;
  written audit (what it does, what it lacks vs our WKWebView app).
- RW-050 Gateway: add per-backend call logging (counts only, no payloads)
  feeding the health board.
- RW-051 Gateway runbook: start/stop/restart + the 5 known sandbox gotchas
  in one page, from AGENTS.md and the gateway README.
- RW-052 Scout: 5 GitHub candidates for git-pull OTA/update daemons;
  confirm or refute the sweep's "none permissively licensed" finding.
- RW-053 Wire the CISA KEV data path as a gateway tool if a keyless MCP
  exists; otherwise document why Custos reads the feed directly.
- RW-054 Backup drill: gateway config + skills backed up to a dated folder;
  restore proven by diffing a fresh checkout.
- RW-055 Scout: 5 GitHub candidates for terminal-sharing/pairing tools for
  the crew's in-guest work.
- RW-056 Toolchain pin file: Node/OpenCode/Freebuff versions + hashes in
  one repo file the image build reads (no hand-copied numbers).
- RW-057 Evaluate Aider (resource sweep): checkpoint-commit behaviour
  compared against the Faber loop's; written verdict for the loop lane.
- RW-058 Gateway: smoke-test script that runs every backend's cheapest call
  and files a dated pass/fail table.
- RW-059 Scout: 5 GitHub candidates for uptime/status page generators.
- RW-060 Connector doc: the gateway's own CONNECTOR-style page so any crew
  agent can wire a new backend without asking Pax.

### Imperium platform support (RW-061…RW-080)
- RW-061 Camera proxy hardening: timeouts + retry caps on the DOT feed
  proxy; a dead feed degrades to a labelled TEST card, never a hang.
- RW-062 Feed health record: every camera feed's last-good timestamp kept;
  the wall shows stale feeds as stale.
- RW-063 Evidence purge job: flagged-incident evidence crops auto-purge on
  false-positive close; the purge is logged; proven by a staged incident.
- RW-064 Dispatch-receiver uptime: the SIMULATED endpoint gets a health
  probe; downtime shows on the crew board, never silently.
- RW-065 Records export: one command exports an incident's full record
  (observations, reviews, dispatch receipt) as a single JSON; proven live.
- RW-066 Patrol budget guard test: the $5 reserve governor proven by a
  synthetic spend run that must stop at the floor.
- RW-067 Queue backpressure: when the Spark queue backs up, patrol sheds
  load in a stated order; behaviour tested, not assumed.
- RW-068 Spark call ledger view: sandbox + Mac ledgers reconciled into one
  read-only totals page for the submission's cost accounting.
- RW-069 Incident replay: a recorded incident replays through the current
  code and must reach the same disposition; drift reported, not hidden.
- RW-070 Map data freshness: the NYC buildings layer gets a generated-on
  stamp + source line in the UI data file.
- RW-071 Camera wall labelling audit: every feed on the wall carries its
  true source label (Caltrans = Los Angeles, DOT = test); grep-proven.
- RW-072 Orchestrator limit tests: the 8-action / 12-call / $0.50 caps each
  proven by a synthetic incident that tries to exceed them.
- RW-073 Review-failure posture: a failed second-look stays UNCONFIRMED and
  spends $0 more; test asserts both halves.
- RW-074 Records append-only proof: a test that tries to mutate a sealed
  record and must fail.
- RW-075 Dispatch payload audit: every field sent to the simulated endpoint
  listed in one doc, checked against the no-real-911 rule line by line.
- RW-076 Spark prompt mirror check: model.mjs and spark_gen.py prompt
  builders byte-diffed in CI-style test; divergence fails loudly.
- RW-077 Timeout posture: a hung Spark call dies at the stated timeout and
  the incident records the timeout as its outcome.
- RW-078 Cost-per-incident report: from the ledger, the real average cost
  of a patrol cycle and of a full flag chain; filed for the README.
- RW-079 Feed failover: primary DOT snapshot source down → secondary used,
  switch logged on the incident record.
- RW-080 Imperium load shed: 50 synthetic simultaneous patrol targets;
  the governor's behaviour recorded and graphed from real timings.

### Rust lane continuation (RW-081…RW-100)
- RW-081 B-series leftover inventory: list every unfinished B01–B07 item
  with its branch state; file as the lane's single source of truth.
- RW-082 Parity harness: one script runs a Rust port and its Python
  original on the same inputs and diffs outputs; wired for one service.
- RW-083 Parity: second service through the harness; diffs filed.
- RW-084 Native-test triage support: for Hana's 38 UPDATE items in Rowan's
  crates, supply the intended-behaviour note each test needs.
- RW-085 WKWebView contract list: every message the web UI sends the native
  shell, enumerated from the JS side; the Rust/native side checked against it.
- RW-086 Cargo workspace hygiene: dead crates and stale features listed;
  removals proposed on a branch, nothing merged.
- RW-087 Build-on-Mac packet: a single zip-able folder + README that lets
  Del compile the workspace in one command and return errors.
- RW-088 Error-return format: Mac compile errors come back in a stated
  template (crate, first error, context) — template written, used once.
- RW-089 Rust worlds parity: the worlds registry in Rust matches
  js/products.js product ids; test asserts the set equality.
- RW-090 Rust queue parity: the queue's tier decisions in Rust match the
  Python orchestrator on Milo's 10 tier scenarios.
- RW-091 Benchmarks: patrol-cycle latency in Rust vs Python on the same
  fixture; numbers filed, no claim beyond the fixture.
- RW-092 Fuzz the contract validator: random malformed assessments must
  all be rejected; crash = finding, filed with the input.
- RW-093 Panic audit: unwrap/expect inventory in the Rust workspace with a
  risk note per site in network-facing code.
- RW-094 Dependency licence sweep: cargo tree licences listed; anything
  non-permissive flagged in ADOPTIONS style.
- RW-095 Rust docs: each crate gets a 5-line purpose header; missing ones
  written from the code, not from memory.
- RW-096 Gate-2 packet: the exact Mac commands + expected outputs for the
  next gate-2 run, rehearsed against the sandbox clone.
- RW-097 Branch archaeology: stale Rowan branches listed with last-commit
  dates; deletion candidates proposed to Del, none deleted unilaterally.
- RW-098 Loop↔Rust bridge scoping: can the Faber loop's test gate call the
  Rust suites selectively? Written scoping with a prototype command.
- RW-099 Incident fixture port: Milo's eval fixtures readable by the Rust
  queue tests; conversion script + one suite using it.
- RW-100 Lane report: a single page — platform state, what is proven, what
  is not — updated at each 25-task boundary.

---

## HANA — interface, Musica, native tests, docs (HN-001 … HN-100)

### The UI wave — tonight's test first (HN-001…HN-025)
- HN-001 Brief me now: wire the button to the real brief backend (Acta's
  on-demand path or the intel brief generator) and flip its gate; clicking
  produces a brief from live data or the button comes out.
- HN-002 Post N jobs: wire to the SIMULATED dispatch endpoint only; the
  button's label or tooltip states simulated; a real post is receipted.
- HN-003 Alert Acknowledge: wire to the alerts store; state persists across
  reload; proven by click + reload.
- HN-004 Alert Resolve: same store, resolve path; resolved alerts leave the
  active list and stay in history.
- HN-005 AI FOCUS on-screen: a visible button in demo mode doing what the
  keyboard path does; both paths tested.
- HN-006 Branding pass: every user-visible "muse-relay" string in the app
  becomes Meta OS / Imperium as appropriate; grep proves zero leftovers.
- HN-007 Manifest + icon: /manifest.webmanifest and /icon-180.png exist and
  are served; the 404s from the audit are gone.
- HN-008 Start screen: first screen is a product start (systems, status,
  enter), not a raw credential form; credentials move behind it.
- HN-009 Alerts panel live data: the panel reads the real alerts store;
  with zero alerts it shows an honest empty state, not harness data.
- HN-010 Plan real data: #intel-plan shows the actual queued plan or states
  plainly that no plan exists yet; the hollow text is gone.
- HN-011 Crew-board live ribbon: the alert ribbon renders from the same
  live store as the app; proven with a raised test alert.
- HN-012 Empty states: every panel in the audit gets a designed empty state
  (what this is, why it's empty, what fills it).
- HN-013 Loading states: every async panel shows a skeleton or spinner
  past 300 ms; no frozen-looking UI during Spark waits.
- HN-014 Error states: a failed fetch shows retry + the real error class;
  tested by killing the local server mid-session.
- HN-015 Keyboard map: every keyboard-only feature gets a visible control
  or a listed shortcut in a help overlay; audit list closed out.
- HN-016 Mobile pass: the app at 390 px wide — no horizontal scroll, tap
  targets ≥ 44 px, the camera wall stacks sanely.
- HN-017 Reduced-motion: prefers-reduced-motion stops the ASCII logo spin
  and camera auto-cycling; setting respected on load.
- HN-018 Contrast pass: text on the dark theme meets WCAG AA against its
  actual backgrounds; measured, listed, fixed where short.
- HN-019 Focus order: full keyboard walk of the main screen follows visual
  order; traps listed and fixed.
- HN-020 The 79-control sweep: re-run the audit's inventory against the
  fixed build; every control marked WORKS / REMOVED with evidence.
- HN-021 Screenshot pack: before/after captures of the 6 changed surfaces
  filed for the submission record.
- HN-022 Demo-mode banner: ?demo=1 shows a persistent "demo data" marker
  wherever demo data can appear; no silent mixing with live data.
- HN-023 Session restore: reload mid-incident restores the incident view
  from records, not from memory state.
- HN-024 Timezone honesty: every timestamp in the UI renders in the
  viewer's timezone with the zone named.
- HN-025 UI fix report: one page — what was dead, what each fix does, what
  remains gated and why — filed with the branch.

### Meta Musica — the studio that never closes (HN-026…HN-055)
- HN-026 Musica pack: os/worlds/musica pack.json + PACK.md in the registry
  format; status spec; validate_pack green.
- HN-027 Registry entry: js/products.js gains musica with honest
  limitations text; parity implications for the Swift mirror noted.
- HN-028 Take-log schema: every composition attempt recorded (prompt,
  seed/params, duration, verdict, reason); schema validated like the lab's.
- HN-029 Composition loop v1: a real loop producing real audio files with
  the tools available in the sandbox; first session of ≥ 10 takes logged.
- HN-030 Keeper rules: the curation bar written as code (length, loudness,
  silence ratio, repetition) — a take passes or fails measurably.
- HN-031 First catalogue: the keepers from HN-029 exported as a catalogue
  file with licences/provenance per track.
- HN-032 Studio board v1: a page showing the live session — now playing,
  queue, take log — reading the real records.
- HN-033 Session persistence: kill and restart the loop; the session
  resumes from records with no lost takes.
- HN-034 Spark assist: structure/lyric prompts through the repo's Spark
  builders under the guardrail; every call recorded in the take log.
- HN-035 Rights log: only own/CC/public-domain material enters the
  catalogue; each track's rights line is filled or the track is rejected.
- HN-036 Loudness normalisation: catalogue tracks normalised to a stated
  LUFS target; before/after measured per track.
- HN-037 Variation engine: the loop must not repeat a near-identical take;
  similarity check (stated method) rejects clones into the reject log.
- HN-038 Genre briefs: three written genre briefs (chipsynth, ambient,
  boom-bap) the loop can be tasked with; one session each, logged.
- HN-039 Listening harness: a blind A/B page (two takes, pick) whose
  results append to the take log as human verdicts.
- HN-040 Overnight run: one unattended 100-take session; catalogue delta
  and reject rate reported honestly.
- HN-041 Studio board v2: catalogue browser + rights column + session
  history, fed by records only.
- HN-042 Failure museum: the reject log rendered as a page — the studio's
  taste is visible in what it throws away.
- HN-043 Prompt library: the prompts that produced keepers, filed as a
  reusable library with their keeper rates.
- HN-044 Duet mode scoping: two loops critiquing each other's takes —
  written scoping only, with the never-grade-your-own-work rule applied.
- HN-045 Musica PACK.md truth pass: status moves only as fast as the
  evidence; proven/unproven lists updated.
- HN-046 Scout: 5 GitHub candidates for open music-generation or
  music-analysis tools; ADOPTIONS.md with licences.
- HN-047 Scout: 5 keyless music APIs/MCPs beyond Audius; smoke-call notes.
- HN-048 Wire one adopted music tool (post-scout, licence-clean) into the
  loop; the integration recorded in the take log format.
- HN-049 Catalogue export: a single downloadable bundle (tracks + catalogue
  + rights) produced by one command.
- HN-050 Session report template: the studio's daily page — takes, keepers,
  rejects, best prompt — generated from records.
- HN-051 Loop budget guard: the composition loop honours a daily Spark
  spend cap from config; cap hit = logged stop, not an error.
- HN-052 Silence audit: a scan proving no catalogue track is silent,
  truncated, or a duplicate file hash.
- HN-053 Board empty states: studio board before any session exists shows
  the honest "no sessions yet" state.
- HN-054 Musica demo cut: a 60-second audio montage of real keepers for
  the platform film, labelled with its source sessions.
- HN-055 Musica gate packet: everything Milo needs to gate-1 the lane in
  one folder: pack, records, catalogue, board URL, test results.

### Scientia + Imperium surfaces (HN-056…HN-070)
- HN-056 Lab board: experiments list reading the lab's records (hypothesis,
  ladder level, status) — no level shown higher than the record's cap.
- HN-057 Hortus run viewer: generations charted from the real run JSONLs
  (best/mean per generation), champion card with its rung label.
- HN-058 Gate status page: the Delaney gate shown as its true state
  (prepared / running / earned) driven by the gate directory's files.
- HN-059 Evidence viewer: flagged-incident evidence crops in the app with
  the ID: UNIDENTIFIED card exactly as specced.
- HN-060 Tier colours audit: yellow/red rendering matches the display
  table for all categories, all three divisions; screenshot-proven.
- HN-061 BOLO card: the recorded-description card rendered from a real
  staged incident record; visible marks only, no name field exists.
- HN-062 Records timeline: an incident's life (patrol → review →
  investigation → dispatch) as one timeline from its record file.
- HN-063 Camera wall source labels: every feed card shows its source +
  LIVE/TEST state in the UI itself, not just in data.
- HN-064 Dispatch receipt view: the sim- receipt shown on the incident
  after a staged dispatch; labelled simulated in the view.
- HN-065 Cost ticker: the incident view shows calls spent and dollars
  spent from the ledger, updating as the chain runs.
- HN-066 Officina board: workshop runs (variants, failures, proven design)
  rendered from Milo's records format.
- HN-067 Custos board: patrol records by tier/source rendered from
  Rowan's records format.
- HN-068 Systems home: one page listing every system with its true status
  chip (live / partial / spec / not built) reading the registry.
- HN-069 Print stylesheet: the incident record prints cleanly for the
  submission appendix.
- HN-070 Surface inventory v2: the control audit re-run across ALL
  surfaces including the new boards; dead count must be zero.

### The 56 native tests (HN-071…HN-085)
- HN-071 Update batch 1: 10 of the 38 UPDATE tests rewritten to the
  WKWebView reality; each keeps its original intent in a comment.
- HN-072 Update batch 2: next 10 UPDATE tests.
- HN-073 Update batch 3: next 10 UPDATE tests.
- HN-074 Update batch 4: final 8 UPDATE tests.
- HN-075 Carve-out doc: the 18 CARVE-OUT tests listed with the reason each
  no longer applies; the doc lives with the test suite.
- HN-076 Carve-out removal: the 18 removed on the branch with the doc;
  suite count changes stated exactly in the commit.
- HN-077 Swift mirror: ProductConfig.swift gains the missing science-lab
  entry mirroring js/products.js (the gap Pax's lane found); parity test
  for that entry passes.
- HN-078 Parity sweep: every product id in js/products.js has a Swift
  mirror or a named exception in the carve-out doc.
- HN-079 Suite hygiene: quarantined/flaky tests listed with evidence;
  no silent skips added.
- HN-080 Mac gate packet: the exact commands for Del to run the native
  suites at gate 2, with expected counts.
- HN-081 Failure naming: suite output groups failures by cause class so
  the next pivot's damage is readable at a glance.
- HN-082 Test data fixtures: the SwiftUI-era fixtures archived to a named
  folder, not deleted — future archaeology stays possible.
- HN-083 README counts fix (branch): the tests section states the real
  suite numbers with the command that produces them.
- HN-084 CI-style script: one command runs node + python + worlds suites
  and prints one totals block; used by every lane's gate packet.
- HN-085 Native lane report: the 56, closed out — updated, carved, or
  escalated — in one page for Del's call on anything left.

### Docs + submission (HN-086…HN-100)
- HN-086 README rewrite: Pax's systems draft merged into the real README
  on a branch; every status claim traced to a file or a gate result.
- HN-087 README contradictions: the 8 items from the draft's list fixed
  or explicitly flagged for Del (config direction-of-truth is his call).
- HN-088 Per-system one-pagers: Imperium, Scientia, Custos, Officina,
  Musica — one page each, honest status header on every page.
- HN-089 Submission screenshots: the 10-shot list for the Devpost page,
  captured from the real build, no staging beyond staged incidents.
- HN-090 Demo script alignment: the film's claims checked line by line
  against the README's claims; mismatches listed and fixed one side or
  the other.
- HN-091 Licence inventory: every vendored library (MapLibre etc.) with
  its licence in one file for the submission.
- HN-092 Attribution page: library-use attributions (older code used as
  named libraries) written per the hackathon's freshness rules.
- HN-093 Changelog: the event-window work summarised from git history —
  generated, then hand-checked.
- HN-094 Glossary: Vigiles/Ignis/Medicus/tiers/ladder/rung terms defined
  once, used everywhere; docs grep-checked for drift.
- HN-095 Docs link check: every internal doc link resolves; broken ones
  fixed or the doc removed.
- HN-096 Scout: 5 GitHub candidates for documentation-site generators
  suitable for the systems one-pagers.
- HN-097 Scout: 5 GitHub candidates for screenshot/visual-regression
  tooling for the surface inventory.
- HN-098 Wire one adopted docs tool (licence-clean) and regenerate the
  one-pagers with it.
- HN-099 Submission checklist: Devpost fields vs our artefacts, one page,
  every gap named with its owner.
- HN-100 Lane report: interface + docs state at each 25-task boundary,
  in the same format as Rowan's and Milo's.

---

## MILO — Officina depth, evals, Scientia verification (ML-001 … ML-100)

### Officina stage 2 completion (ML-001…ML-020)
- ML-001 Fix the forced-airflow drop (Pax gate-1 finding 1): a stated
  forced-air requirement changes the grading conditions; test proves the
  same brief grades differently with and without a fan.
- ML-002 Fan conditions defined honestly: forced-air h values stated with
  their source class (textbook range), labelled as assumptions in the brief.
- ML-003 Widen the improve loop (finding 2): gap and volume moves must
  actually fire; a brief whose best move is a gap change proves it.
- ML-004 Multi-move rounds: a round may combine two compatible moves; the
  decision log records each with its own reason.
- ML-005 Conflict handling: contradictory rough words ("tiny but huge
  airflow, no fan, silent") land in the brief's conflicts list; the design
  proceeds on the stated priority order and says so.
- ML-006 Unknowns policy: when a graded unknown (power, footprint) is
  missing, the brief proceeds on the workshop default AND the exported
  design carries the assumption on its face.
- ML-007 Second artefact class — enclosure: a vented electronics enclosure
  scored by real vent-area/airflow math; its assumptions stated like the
  heatsink's.
- ML-008 Enclosure calibration hunt: find manufacturer data to anchor the
  enclosure scorer, or file it rung 1 with the reason.
- ML-009 Third artefact class — bracket: an L-bracket scored by real
  bending-stress math (stated formulas, stated safety factors).
- ML-010 Bracket held-out gate: the bracket class gets the same
  fresh + held-out verification as the heatsink before anything is proven.
- ML-011 Class registry: artefact classes register with their scorer,
  bounds, and gate; adding a class never edits the loop.
- ML-012 Cross-class brief: one rough-words input that spans two classes
  ("a bracket holding a heatsink") handled as two linked briefs.
- ML-013 Brief export v1: the brief + decision log export as one readable
  document (what was asked, assumed, decided, and why).
- ML-014 Iteration ceiling: the self-building brief stops at a stated
  round cap or when improvement < a stated epsilon; the stop reason logged.
- ML-015 Regression pack: the two gate-1 inputs (Pax's garage text + the
  demo text) become permanent tests with their expected dispositions.
- ML-016 Cost guard: iteration that would use Spark states its budget in
  the brief before spending; zero-Spark paths stay zero.
- ML-017 Brief diff view data: round-by-round brief changes exported as
  structured data for Hana's Officina board.
- ML-018 Workshop status in pack: pack.json runtime parts updated to
  stage-2 truth (intake built, airflow fixed, classes = 3).
- ML-019 Officina test suite: the lane's tests pass from a clean checkout
  via one documented command.
- ML-020 Stage-2 report: what stage 2a promised vs what exists, findings
  closed, findings open — one page on the bus.

### Prior art — patents and products (ML-021…ML-035)
- ML-021 Prior-art protocol: the search method written down (sources,
  query construction from the brief, stop rule) before any searching.
- ML-022 Patent source #1: Google Patents search wired as a documented
  procedure with result capture into the run record.
- ML-023 Patent source #2: USPTO/EPO open search as the second source;
  disagreements between sources are recorded, not averaged away.
- ML-024 Claim chart template: a prior-art hit becomes a row (source,
  what it claims in plain words, overlap with our brief: none/partial/full).
- ML-025 First worked example: the heatsink class gets a full prior-art
  report (≥ 10 sources) filed with its run.
- ML-026 Collision steering proof: one brief visibly changes a design
  decision because of a prior-art hit; the decision log cites the source.
- ML-027 Open-ground note: each report ends with where the search found
  nothing — labelled as absence of evidence, never as proof of novelty.
- ML-028 Honesty label: every report carries "research aid, not a
  patentability opinion, not legal advice" on its face.
- ML-029 Product prior art: existing commercial products for the class
  listed beside the patents (the market is prior art too).
- ML-030 Enclosure prior-art report: full report for the second class.
- ML-031 Bracket prior-art report: full report for the third class.
- ML-032 Search failure log: queries that returned nothing useful are
  kept — the next run doesn't repeat dead searches.
- ML-033 Prior-art freshness: reports carry their search date; a design
  older than a stated window gets a refresh flag.
- ML-034 Scout: 5 GitHub candidates for patent-search APIs/tools;
  ADOPTIONS.md with licences.
- ML-035 Wire one adopted patent tool (licence-clean, keyless) into the
  protocol; smoke search recorded.

### Blueprint pack (ML-036…ML-048)
- ML-036 Schematic renderer: a heatsink's proven params become a
  dimensioned SVG (front + side, all four parameters labelled).
- ML-037 Spec sheet: the same design as a text spec (dimensions,
  material, tolerances stated as assumptions, finish).
- ML-038 Materials list: stock sizes and quantities computed from the
  geometry; waste factor stated.
- ML-039 Feature list: the brief's features rendered as the pack's
  checklist, each traced to stated / assumed / agent-added.
- ML-040 Pack assembly: one command builds the full pack (schematic,
  spec, materials, features, test results, prior-art report, decision log).
- ML-041 Pack for the stage-1 champion: the 240-run's proven design gets
  the first real pack; filed with the run.
- ML-042 Pack for a stage-2 design: a rough-words design gets its pack;
  the assumptions page lists every default the user never stated.
- ML-043 Enclosure schematic: the renderer generalises; second class
  renders dimensioned views.
- ML-044 Readability check: a pack is handed to a fresh agent (or Pax)
  who must restate the design from the pack alone; gaps filed as defects.
- ML-045 Versioning: a redesigned invention increments its pack version;
  old packs stay readable (nothing overwritten).
- ML-046 Pack manifest: every pack carries a manifest with hashes of its
  parts; tampering is detectable.
- ML-047 Build-notes page: what a shop would still need to decide
  (tooling, finish, fasteners) listed as open items, never invented.
- ML-048 Blueprint gate packet: packs + reports in one folder for Pax's
  gate-1 of the stage.

### Workshop memory (ML-049…ML-058)
- ML-049 Playbook format: per class, winning patterns and dead ends in a
  structured file the loop reads at start.
- ML-050 Playbook writer: every proven run appends its lessons (what
  moved the score, what failed the gate) automatically.
- ML-051 Second-run proof: a fresh run on the heatsink class starts from
  the playbook and reaches proven in fewer rounds than the cold run;
  numbers compared honestly.
- ML-052 Dead-end respect: a variant inside a recorded dead-end region is
  skipped with the skip logged (not silently, not re-tested forever).
- ML-053 Playbook for class 2: enclosure playbook seeded from its first
  proven run.
- ML-054 Negative archive view: the failure archive rendered as data for
  Hana's board (counts by failure reason per class).
- ML-055 Memory hygiene: playbook entries carry their run id; an entry
  whose run is invalidated is marked, never silently deleted.
- ML-056 Cross-class lesson: one lesson that transferred between classes,
  documented with both runs as evidence — or an honest "none yet".
- ML-057 Cold-start benchmark: cold vs warm start rounds-to-proven on
  all 3 classes, one table.
- ML-058 Memory report: what the workshop actually remembers, in one
  page, with the file paths.

### Evals — the Imperium grading lane (ML-059…ML-080)
- ML-059 Batch-2 rebuild: the 100 frames rebuilt from the YouTube source
  list (boss's order); frame count and source per frame recorded.
- ML-060 Batch-2 commit: frames + manifest committed (boss's explicit
  order overriding local-only); commit linked on the bus.
- ML-061 Batch-2 scorecard: the rebuilt set re-graded; the scorecard
  compares against the Oct-31 adjudication line by line.
- ML-062 Discrepancy hunt: any frame whose new grade differs from Oct-31
  gets a written cause (model drift, frame mismatch, or original error).
- ML-063 Batch-3 protocol: fresh-frame capture rules (sources, licensing
  note, pre-event frames labelled as such before grading).
- ML-064 Batch-3 capture: ≥ 100 new frames across the three divisions
  under the protocol.
- ML-065 Batch-3 grading: full run with the current build; scorecard in
  the batch-1/2 format.
- ML-066 Look-alike pack: Medicus look-alikes (bench sleeper, sunbather,
  yoga, CPR manikin) expanded to ≥ 10 frames each with sources.
- ML-067 Ignis abstention check: fire-still frames where "indeterminate"
  is the correct answer, graded as their own class.
- ML-068 Vigiles false-altercation watch: the zero-false-altercation
  streak tracked as its own metric across batches.
- ML-069 Per-division confusion report: where the model confuses
  categories, as a matrix from real grades.
- ML-070 Tier-agreement check: graded categories mapped to yellow/red
  under the display-wins table; disagreements listed.
- ML-071 Pre-event labelling: frames before an event starts carry that
  label; the scorecard reports with and without them.
- ML-072 Eval cost ledger: Spark spend per batch from the real ledger;
  cost per graded frame stated.
- ML-073 Eval harness determinism: same frames + same code = same grades,
  proven by a double run diff.
- ML-074 Held-out eval set: a sealed 30-frame set nobody tunes against;
  graded once per release candidate.
- ML-075 Miss museum: every genuine miss across batches in one file with
  the frame, the grade, and the cause class.
- ML-076 Eval README: how a batch is built, graded, and adjudicated —
  writable by a new agent without asking.
- ML-077 Scout: 5 GitHub candidates for eval/benchmark harness tooling;
  ADOPTIONS.md with licences.
- ML-078 Scout: public datasets usable as eval sources (licences checked
  per dataset; anything unclear is rejected in writing).
- ML-079 Batch-4 scoping: the batch that would grade the live flagged
  path if it ever fires — protocol only, no fabricated run.
- ML-080 Eval lane report: batches, scorecards, open discrepancies — one
  page, updated per batch.

### Scientia verification duty (ML-081…ML-092)
- ML-081 Delaney verifier protocol: the blind re-run procedure written
  (inputs: archived CSV + paper equation only; tolerance stated in
  advance in the protocol, before seeing results).
- ML-082 Delaney verifier run: execute the protocol as the independent
  verifier on Pax's runner; verdict filed either way.
- ML-083 Gate record: the formal experiment record for the gate, at the
  ladder level the evidence earns and no higher.
- ML-084 Hortus second target scoping: a second fitness domain for the
  breeding engine (antenna, spring, or gear train) with a data hunt plan.
- ML-085 Second-target data: real reference data for the chosen target
  archived with sources, like the Wakefield set.
- ML-086 Hortus transfer check: the engine runs the second target with
  no code changes beyond the scorer; friction filed honestly.
- ML-087 Wire PubChem MCP into the gateway (chemistry lookups for the
  lab); smoke call returns a real compound record; skill doc.
- ML-088 Wire ChEMBL MCP (build from its repo per the sweep); smoke call
  recorded; skill doc.
- ML-089 Wire Paper Search MCP with the Sci-Hub fallback DISABLED in
  config and proven disabled by a test query.
- ML-090 Literature cross-check: one Scientia claim traced through Paper
  Search + PubMed to its primary source; the chain filed.
- ML-091 Lab records audit: every lab record's ladder level re-checked
  against its evidence; over-claims (if any) corrected in place with a note.
- ML-092 Verifier's handbook: how to verify a lab result, written from
  the Delaney + Hortus experience, for any crew member.

### Gate-1 duty (ML-093…ML-100)
- ML-093 Gate-1 Custos stage 1: Rowan's branch — re-run his self-test
  pack and one live patrol cycle; written verdict on the bus.
- ML-094 Gate-1 Custos stage 2: the RW-013 synthetic incidents re-graded
  independently; verdict.
- ML-095 Gate-1 Musica stage 1: Hana's take log audited (real files,
  keeper rules actually applied); verdict.
- ML-096 Gate-1 Musica board: board numbers traced to records by hand
  on 5 spot checks; verdict.
- ML-097 Gate-1 UI wave: the 79-control sweep evidence re-checked on 10
  spot controls; verdict.
- ML-098 Gate-1 loop drills: Rowan's STOP/rollback drill transcripts
  re-performed in a scratch clone; verdict.
- ML-099 Gate-1 Officina packs: Pax gates Milo; Milo pre-checks his own
  pack against the ML-044 readability rule and files the self-check.
- ML-100 Lane report: Officina + evals + verification state at each
  25-task boundary, same format as the other lanes.
