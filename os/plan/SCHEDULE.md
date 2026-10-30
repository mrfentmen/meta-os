# Relay Intelligence — SCHEDULE (Oct 26 → Nov 4, 2026, all times ET)

Build window: **Mon Oct 26 12:00 PM → Wed Nov 4 9:00 PM**. Fully remote.
Freezes: **image content freeze Nov 2 12:00** (Meta OS base + services; after it, only Spark-layer payload files may change, and only under the OS-003 exception rule), **feature freeze Nov 2 21:00**, **demo freeze Nov 3 21:00**. ★ = critical path.
Task ids reference MASTER_PLAN.md. Lanes: PAX (coordinate/integrate), ROWAN (dashboard), HANA (briefings), MILO (watchdog + audio), BUFFY (volume/docs), DALE (decisions).

---

## Day 1 — Mon Oct 26 (kickoff, groundwork)

**Hour 1 (12:00–13:00) — DALE decisions, all blocking:**
- GOV-001 Spark access confirmed ★ | GOV-002 bus posting rule + real-history rule ★ | GOV-003 git workflow ruling ★ | GOV-004 roster confirmed
- Meta OS, same hour: OS-001 name + positioning approved ★ | OS-002 demo hardware named ★ | OS-003 image freeze exception rule set (these three unblock the OS track; the full OS day-by-day is the Meta OS track section below)

**Lands today:**
- PAX: FND-002 room created (or hold recorded), FND-003 intel/ skeleton ★, FND-004 key layout ★, FND-005 Spark client + FakeTransport ★, FND-016 wire formats frozen ★
- HANA: BRF FND tasks — brief record schema (FND-032) ★, source map (FND-033), length budgets (FND-034); morning prompt v1 started (BRF-001)
- MILO: FND-029 watchdog keys with Pax ★, FND-030 thresholds module, FND-031 reuse audit
- ROWAN: DSH-001 dashboard spec ★ (panels, sources, no-build-step constraint)
- BUFFY: DOC-001 intel/README skeleton ★, FND fixtures 020–023 started (format README + quiet + busy fixtures)
- Integration point 13:00: decisions unblock every lane; nobody builds on an unmade decision.
- End of day gate: Pax runs skeleton py_compile + existing suite; journal entry (BUFFY INT-036 habit starts today).

## Day 2 — Tue Oct 27 (engines, part 1)

- PAX: FND-008/009/010 jobs.py files + deps + attempts ★, FND-011 progress timestamps, FND-013 snapshot API ★, FND-015 intel.py CLI ★, DSP-001 dispatch prompt v1 ★
- HANA: BRF-001/002/003 prompts v1 ★, BRF-004/005/006 extractors ★
- MILO: WDG-001 watchdog loop ★, WDG-002 presence-stall ★, WDG-010 alert writer ★, WDG-013 dedupe
- ROWAN: DSH-002 panel skeleton ★, payload dev pack received from Pax (DSH-037) ★, crew board fixtures rendering
- BUFFY: FND-024/025/026 stall + dead-dep + collision fixtures, BRF eval histories A/B (BRF-031/032)
- Integration point (EOD): snapshot → Hana extractors and snapshot → Milo detectors both run on the busy fixture. **Brief record schema freeze (BRF-041, Pax+Hana+Rowan).**

## Day 3 — Wed Oct 28 (engines, part 2)

- PAX: DSP-002 parser ★, DSP-003 overlap guard ★, DSP-004 dep graph ★, DSP-006 dry-run ★, DSP-007 approval gate ★; DSH-038 viewer write-path decision ★ (with Rowan)
- HANA: BRF-007 composer ★, BRF-008 template fallback ★, BRF-009 brief storage/CLI, BRF-013 redaction ★
- MILO: WDG-003 progress-stall, WDG-005 dead-dependency ★, WDG-007 file-collision ★, WDG-011 explanation templates ★
- ROWAN: DSH-003/004/005 crew board panel ★, DSH-007 brief panel ★
- BUFFY: DSP fixtures (DSP-028/029 golden + malformed packs), WDG fixtures (WDG-041–044)
- Integration point (EOD): first end-to-end dry run on fixtures — goal → plan preview (no posting), snapshot → brief (template fallback path), stall fixture → alert record.

## Day 4 — Thu Oct 29 (posting, watching, faces)

- PAX: DSP-008 plan poster ★, DSP-009 signing ★, DSP-019 worker claims a dispatched job end to end ★, FND-012 jobs --json ★ (dashboard unblocked)
- HANA: BRF-012 morning scheduling, BRF-016/017 rubric scoring rounds, BRF-022 Watch items (needs Milo alerts live on fixtures)
- MILO: WDG-014 lifecycle, WDG-016 self-heartbeat ★, WDG-019 detector test suite ★, WDG-020 kill drill harness ★
- ROWAN: DSH-010/011 dispatch panel + approval states ★, DSH-013 alerts feed ★, DSH-015 all-quiet/watchdog-silent states ★, DSH-023/024 crew-board Files/Deps/Attempts ★
- BUFFY: BRF-033 gap fixture, BRF-034 hallucination bait, DSP batch runner (DSP-031), INT-033 demo-day state pack started
- Integration point (EOD): signed plan posts to the integration namespace; a real mos worker claims and completes one job; watchdog watches the same state. **First full loop (INT-013) rehearsed informally.**

## Day 5 — Fri Oct 30 (hardening + dashboard completion)

- PAX: DSP-011 undo, DSP-013 guardrails, DSP-017 fallback plan, INT-018 full-suite gate routine starts (every batch)
- HANA: BRF-019 prompts v2 from eval failures, BRF-027 spend check, DSP-021–027 dispatch language set (golden + adversarial) ★
- MILO: WDG-021/022 collision + dead-dep drills, WDG-027 threshold tuning table ★, WDG-028 brief status line for Hana
- ROWAN: DSH-017 mobile pass ★, DSH-027 first muse-relay-live deploy of the dashboard ★, DSH-026 bus/index identity check ★
- BUFFY: DOC-003 quickstart, DOC-004 architecture explainer, INT-032 regression checklist live
- Integration point (EOD): dashboard live on the Pages URL against integration data; Dale sees the first real mission-control screen.

## Day 6 — Sat Oct 31 (integration day)

- ALL: INT workstream focus. PAX: INT-013 E2E-1 ★, INT-014 E2E-2 (worker dies → alert → requeue → finish) ★, INT-019 load check
- ROWAN: DSH-034 integration-day panels live all day, fixes begin
- HANA: INT-029/030 brief scoring + brief/dashboard consistency on E2E briefs
- MILO: INT-025 alert id consistency across brief + dashboard + CLI ★, INT-026 drill tournament (all three drills back to back)
- BUFFY: INT-035 numbers sheet started, INT-034 failover card draft
- Integration point (EOD): **core feature status review** — each of briefings/dispatch/watchdog/dashboard marked VERIFIED / CODE-INSPECTED / UNIMPLEMENTED / BLOCKED with evidence. This review feeds tomorrow's stretch decision.

## Day 7 — Sun Nov 1 (checkpoint + catch-up)

- **12:00 checkpoint with DALE: GOV-007 stretch go/no-go on SAM 3.1** — only if core is VERIFIED at yesterday's review. Default answer if core is not VERIFIED: no-go, stretch tasks (STR-001–005) stay UNIMPLEMENTED and are described as stretch in all copy.
- **Same checkpoint: OS-004 Meta OS go/no-go ★** — Dale rules whether the Meta OS cold boot opens the demo. Evidence on the table: the Day 6 boot test (full checklist, META_OS.md) and the OS-018 boot times on the actual demo laptop. Default if the boot is not boring by then: no-go — the demo opens on the dashboard per the original DEMO.md, the boot video becomes a supporting asset, and nothing else in demo week changes.
- Morning: HANA cold-start test (INT-031); MILO threshold lock (INT-027); PAX cost projection (INT-020) — demo day must fit the $150 API credit with headroom.
- Afternoon: failure drills — INT-021 Spark down ★, INT-022 Redis outage, INT-023 spoofed dispatch.
- BUFFY: DOC-002 README file table, INT-037 judge Q&A sheet; ROWAN: DSH-035 fix top-5 integration issues.
- Slack in this day is intentional: anything that slipped from Days 2–6 lands here, not in demo week.

## Day 8 — Mon Nov 2 (demo build + FEATURE FREEZE 21:00)

- PAX: DEM-001 demo scenario lock ★ (with Dale DEM-025 approval), DEM-008 60-second summary card
- MILO: DEM-011 staged silent-failure worker ★, DEM-012 catch-time measurement, DEM-013 demo thresholds profile; narration takes recorded (WDG-030/031, DEM-014)
- HANA: BRF-025 demo morning brief draft (hand-checked) ★
- ROWAN: DSH-028 demo mode (?demo=1) ★, DSH-030 submission screenshots
- BUFFY: DEM-019 demo script v1 ★, DEM-021 one-pager draft, cue cards (WDG-045)
- **21:00 FEATURE FREEZE (DEM-007).** After this: bugfixes only, Pax + Dale sign-off, logged.

## Day 9 — Tue Nov 3 (rehearsals + DEMO FREEZE 21:00)

- Rehearsal 1 (morning): full demo run, timed, stumbles logged (DEM-002).
- BUFFY: DEM-020 script v2 from rehearsal 1 notes.
- Rehearsal 2 (afternoon): full run on the actual demo machine/browser (DSH-036 verified), one run in normal view as fallback (DSH-041).
- PAX: DEM-003 fallback video recorded from the cleanest run ★; DEM-006 demo-day checklist drafted.
- MILO: DEM-015 caption voiceover, narration final mix into fallback video.
- **21:00 DEMO FREEZE.** Demo state pack (INT-033) is the demo. Nothing about the demo changes after this except by Dale's direct order.

## Day 10 — Wed Nov 4 (submission day)

- Morning: PAX DEM-006 checklist executed (tokens, credit balance, watchdog running, dashboard deployed, fallback video local); DEM-010 final presentability check (clean demo room, README current, links live).
- PAX: DEM-004 submission package assembled per organizer requirements (checklist in SUBMISSION.md; fields confirmed against the official form — anything unpublished by organizers is marked pending, never guessed).
- BUFFY: captions/credits final (DEM-022/023); HANA/MILO/ROWAN: standby for judge questions in their lanes.
- **DALE: DEM-028 — deliver the demo / submit the entry before 9:00 PM ET** (after GOV-009 package approval).
- After submission: PAX DEM-009 results/lessons note within 24h; BUFFY DOC-010 archive (room export + journal).

## Standing cadence (every day)

- Morning brief — generated by our own product once BRF-012 lands (dogfood; before that, Pax posts a manual one in the journal).
- Pax integration batch gate: check.sh + full suite + regression checklist before anything merges (INT-018).
- Buffy build journal updated daily (INT-036).
- Deploys: Rowan deploys viewer batches to muse-relay-live as they land, Pax reviews each batch (DSH-039).
- Dale decisions: same-day turnaround on GOV items keeps lanes unblocked; anything undecided at EOD is called out in the journal by name.

---

## Meta OS track (parallel, Oct 26 → Nov 4)

Runs beside the main schedule above and never in front of it: if a day forces a choice, the Spark work wins and the OS item slips right (Pax arbitrates). Spec: META_OS.md. Owners: PAX (pipeline/services/boot), BUFFY (build volume/docs), MILO (supervisor/watchdog service), ROWAN (boot experience), HANA (boot brief), DALE (OS-001–004).

- **Day 1 — Mon Oct 26:** DALE OS-001/002/003 in Hour 1 (above). PAX: OS-005 base frozen + checksum, OS-006 os/ tree laid down. BUFFY: OS-023 package rationale started against the draft manifest.
- **Day 2 — Tue Oct 27:** PAX: OS-007 primary pipeline first light (Packer + QEMU, preseed OS-009) — an ugly bootable image by EOD beats a beautiful plan; OS-010 manifest pinned. BUFFY: OS-024 preseed archive from Pax's working files.
- **Day 3 — Wed Oct 28:** PAX: OS-008 fallback live-build ISO builds (kept buildable from here on, never allowed to rot); OS-011 stack bake at a pinned commit; OS-012 secrets rule + firstboot prompts. ROWAN: OS-045 identity requirements to Buffy for the asset set.
- **Day 4 — Thu Oct 29:** PAX: OS-013/014/015 service units (bus, jobs, overseer) live on the test image; OS-016 relay.target + ready gate. MILO: OS-033 watchdog unit beside them. **Working-system layer starts (vision upgrade): PAX OS-053 driver contract + stub, OS-054 Muse Code driver first light; MILO OS-056 driver supervision design against the contract. Depth layer starts (four system services, minimal in-window only): DALE OS-082 capability policy defaults approved Hour 1 style; PAX OS-080 identity + capability files for crew processes; MILO OS-085 budget config drafted beside the thresholds.** **Completion contract starts (META_OS.md, "The completion contract"): PAX OS-093 the order door (uplink service — an order from Dale's phone lands on the queue) live beside the service units; MILO OS-095 self-repair ladder design against the watchdog detectors.** **Mind images start: PAX OS-101 bundle format drafted; DALE OS-108 launch-bundle contents policy approved.** **Federation minimum starts (META_OS.md, "Federation: many machines, one crew"): DALE OS-115 federation policy ruled (default closed + demo room posture) beside the other Day 4 policy approvals; PAX OS-110 `meta join` + firstboot room config first light; MILO OS-112 trust-list enforcement design against the jobs.py v2 signing.** **Wake layer starts (META_OS.md, "The bell: how sleeping agents get woken"): DALE OS-124 wake budget policy ruled beside the other Day 4 policy approvals; PAX OS-118 the watchman (relay-watchman, a resident CLI program in the OS) first light beside the service units (queue claims/leases as its source of truth, never the message counter); MILO OS-119 Muse wake adapter design against the watchman's bell.**
- **Day 5 — Fri Oct 30:** PAX: OS-017 worker fleet units. MILO: OS-034 restart-ownership drills (kill -9 vs SIGSTOP) + OS-035 cgroup slice tuned from INT-019 numbers. BUFFY: OS-025 visual identity baked; OS-026 fixture seed script. **Working system: PAX OS-058/059 MCP gateway daemon unit + bake (gateway live on the test image), OS-065 skills loader mounting fixture skills; BUFFY OS-063 package pass for the new stack. Depth layer: PAX OS-078 memory service (minimal) mounted at process start and OS-083 artifact store (minimal) live on the test image.** **Completion contract: PAX OS-094 queue-owned persistent jobs on the test image; MILO OS-096 attempt budgets + escalation gate wired to the ladder.** **Mind images: PAX OS-102 loader integration (extends the OS-065 skills loader into full image assembly); HANA OS-103 environment brief generator feeding the bundle.** **Wake layer: MILO OS-119 wake adapter proven on a sleeping fixture agent — bell rings, session starts with the job in hand, first bus action is the claim.**
- **Day 6 — Sat Oct 31 (integration day):** ROWAN: OS-042/043/044 boot experience complete on the image (autologin kiosk, live boot checklist, local viewer). HANA: OS-048/049 boot brief spec + relay-brief.service generating on the image. MILO: OS-036 self-check + OS-037 journal watch. **Working system integration: PAX OS-055 driver demo proof (Spark dispatch → Muse Code driver executes) + OS-066 full working-system QA run; MILO OS-057 driver stall drill; ROWAN OS-060/061 agent-process view + tool/app inventory live; HANA OS-062 boot brief lists drivers/tools/apps; BUFFY OS-064 loader fixtures + docs. Depth layer integration: MILO OS-081 capability refusal drill green (the Shot 8b evidence); HANA OS-079 boot brief surfaces memory settled-decisions + spend-vs-budget lines; ROWAN OS-084 capability + artifact views live; MILO OS-085 budget warning proven on the fixture lane.** **EOD: full boot test checklist run (META_OS.md) on the VM AND the demo laptop — this evidence feeds tomorrow's OS-004 ruling.** PAX: OS-019 harness green on the same build; OS-032 first RC archived. **Completion contract integration: HANA OS-097 the two pushes (done / blocked) firing from real job closes and parks; ROWAN OS-098 the board explains the silence live; BUFFY OS-099 the completion drill (order once, agents killed mid-job, exactly one done push; plus the machine-off hour); DALE OS-100 contract acceptance on his real phone — the contract is in the image ahead of the Day 8 freeze.** **Mind images proof: BUFFY OS-104 versioning discipline + OS-105 A/B harness; MILO OS-106 the measured A/B run — one comparison result in hand for the demo; ROWAN OS-107 mind-image versions + the A/B result on the board.** **Federation integration: MILO OS-112 enforcement live on the test image + OS-114 trust negative test green; ROWAN OS-111 board grouping by machine live; BUFFY OS-113 two-machine federation drill (post on A, claim + complete on B, one done-push) run twice green — the federation minimum is in the image ahead of the Day 8 freeze.** **Wake layer integration: MILO OS-122 dead-watchman drill (crew-dark flagged in one cycle, restart revives it, no Dale push; the unfixable kill earns exactly one blocked-push) + OS-125 the baton pass proven (worker killed mid-job, the next agent continues from the job record with no repeated work; the cross-program pass is the stretch line); BUFFY OS-123 the hands-free drill (Dale orders once and touches nothing — a sleeping agent on another runtime wakes by the bell, completes, exactly one done-push) run twice green — the bell is in the image ahead of the Day 8 freeze.** **Recovery layer integration (META_OS.md, "Recovery: the crew survives the machine dying"): DALE OS-131 cadence policy ruled (sweep interval + burn ceiling under OS-124, proposed default on the table) beside the day's other policy approvals; PAX OS-128 disk-state audit (kill every session, store untouched, zero job knowledge lost — leak list empty); BUFFY OS-126 the plug-pull drill on the RC image (job in flight, power cut mid-work, power restored, crew self-relaunches, job resumes from baton state and completes, exactly one done-push, zero human touches after the cut) with MILO OS-129 verifying the lease sweep + watchman resume independently and HANA OS-127 the boot brief's in-flight-recovered line reconciling with the sweep — the strongest reliability evidence the demo has, in hand ahead of the Day 8 freeze.**
- **Day 7 — Sun Nov 1 (checkpoint):** **12:00 — DALE OS-004 go/no-go** (see Day 7 above). HANA: OS-050/051/052 cold-start honesty, prior-session digest, boot brief evals. MILO: OS-040 power-cut drill (3 hard kills, clean recovery) + OS-041 status line final. PAX: OS-018 boot budget measured on the demo laptop (3 timed boots).
- **Day 8 — Mon Nov 2:** BUFFY: OS-027 README cold-read test with Pax, OS-028 spec sync against the frozen image, OS-029/030 size sheet + changelog current. PAX: OS-020 version stamp verified, OS-021 update path proven N→N+1 on a scratch VM, OS-022 rescue entry tested. **12:00 IMAGE CONTENT FREEZE** — base, packages, and units frozen solid; after this only Spark-layer payload files move, under the OS-003 rule, until the 21:00 feature freeze. MILO: OS-038 demo thresholds drop-in on the frozen demo image.
- **Day 9 — Tue Nov 3:** The OS appears only inside the rehearsals: Shot 0 (cold boot) is rehearsed with the rest of the demo IF OS-004 ruled go; otherwise the laptop boots before the house opens and Shot 0 is the recorded boot video. BUFFY: OS-031 field kit packed and confirmed (fallback ISO USB, VM snapshot export, failover card). MILO: OS-039 boot audio mixed into the fallback cut. **21:00 demo freeze covers the image too — the demo image is the image.**
- **Day 10 — Wed Nov 4:** Demo-day checklist gains three OS lines: demo laptop on the frozen image (checksum matches OS-032 index), VM snapshot staged on the same machine, fallback ISO USB in the field kit. If the boot misbehaves in the room: snapshot restore first, recorded boot second, debug never (DEMO.md fallback layers).

**Standing OS cadence:** every image build gets a changelog entry (OS-030), a size line (OS-029), and an archive entry (OS-032) the same day — an unarchived build does not exist. Boot test harness runs on every RC, not just the last one.

---

## Phase B — Meta OS daily-driver track (POST-hackathon, starts after Nov 4) [B]

Not day-bound and never demo scope: this is Dale's "I actually have to use it" track (META_OS.md, "Daily driver track"). Order below is the working sequence, paced by real use, not by a deadline.

- **Drivers widen:** PAX OS-067 OpenCode driver, then OS-068 Freebuff/GLM driver — every coding agent Dale uses becomes an OS-managed process passing the OS-053 conformance checklist.
- **Packages:** BUFFY OS-069 meta-pkg v1 (install/list/remove MCPs + skills) and OS-070 the generated package catalog — new capabilities arrive as package installs.
- **Dale's session:** ROWAN OS-071 desktop session with mission control as the home screen; HANA OS-075 the daily brief tuned from two weeks of real use.
- **The OS maintains itself:** PAX OS-072 image update channel (check/stage/apply-at-reboot/rollback) + OS-073 hardening pass for a machine holding real keys.
- **Proof it can be lived on:** MILO OS-074 seven-day unattended soak of crew + drivers, report reviewed end to end.
- **Dale's calls:** OS-076 daily-driver go/no-go after the soak report; OS-077 Meta OS public/private posture (with GOV-010).
- **Machine plumbing + the revision loop [B]:** the tailnet lane serves machine-side data movement only (artifact-store sync, second-box driver processes) — plumbing under the completion contract, never a Dale-facing remote control; PAX OS-109 mind-image revision tooling (eval evidence → proposed image diff → Dale approves) turns the A/B loop into routine maintenance.
- **Depth services mature [B]:** PAX OS-086 memory scoping + OS-090 budget priority classes; BUFFY OS-087 memory compaction + OS-089 artifact retention/dedup; ROWAN OS-088 capability editor in mission control; MILO OS-091 budget preemption + forecasting; HANA OS-092 memory-aware daily brief depth. These are the only depth additions — anything else belongs in skills, not the OS (META_OS.md anti-bloat principle).
- **Federation grows [B]:** PAX OS-116 local Wi-Fi fast lane (mDNS-style discovery, direct sync, cloud bus stays the single record); HANA OS-117 crew-of-crews brief section — one morning brief across every joined machine.
- **The bell widens [B]:** PAX OS-120 PC agent wake shim (the bell for agents living outside the image on Dale's PC); MILO OS-121 timer fallback sweep (the clock-in safety net under the bell, so a missed ring delays work by minutes, never forever).
- **Recovery leaves the image [B]:** PAX OS-130 external crew cadence kit — the scheduled sweep + restart re-registration pattern productized for agents on other runtimes, at the cadence Dale approved in OS-131 (policy in-window, kit after the freeze); the crew outside the image resurfaces on schedule and survives its own runtimes' restarts the same way the image survives a reboot.

## Ops note — morning brief schedule (BRF-011, Hana, 2026-10-26)

- Command: `python3 intel.py brief --morning --room <room>` generates
  and stores a morning brief; add `--dry-run` to build it without
  storing, and `--now <unix ts>` to run it at a fake clock time.
- Cadence TODAY (2026-10-26, Dale's order): run TODAY, not
  tomorrow morning. `python3 intel.py brief --morning --room <room>`
  with no `--now` runs at the current time, today. The 08:00 ET
  daily cadence is NOT the today plan — do not wait for the
  next 08:00 ET. `intel.brief.morning_brief_today` is the
  today entry point; `next_morning_run` is kept only for a
  later daily schedule, not for today.
- A morning brief is a template brief (BRF-008) until a Spark
  client is passed to the composer (BRF-007); it never posts to
  the bus — posting is BRF-010 and stays held until Dale approves
  a build room and posting.
