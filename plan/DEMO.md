# Relay Intelligence — DEMO

**Format assumption:** live walkthrough by Dale with the dashboard on screen, Milo as watchdog operator, Pax on standby for commands. If the organizers assign a recorded-video or different format, GOV-008/DEM-004 adapt the package — the story below is the same either way.
**Scenario approval:** DEM-025 (Dale). **Script owner:** Buffy (DEM-019/020), timings owned by Pax (DEM-002).

## The story (one arc, ~6 minutes)

A real crew takes a plain-English goal and ships it — while mission control watches, and catches the failure nobody announced.

Dale's framing (his words, from the application): *"My bus moves messages and jobs between agents well. What it cannot do yet is understand them. This is the layer that understands."*

## Shot list

| # | Shot | On screen | Beat / line | Tasks behind it |
|---|---|---|---|---|
| 0 | **Cold boot (Meta OS — only if OS-004 ruled go at the Nov 1 checkpoint)** | A powered-off laptop. Dale presses the power button, on camera. Splash, then the boot checklist flips live — bus, queue, supervisor, watchdog — then the dashboard full screen with the boot brief already on it. Nobody touches anything. | "Every other agent demo starts by opening a laptop and launching a stack. Mine boots. This is Meta OS — a Linux system rebuilt for one job: wake up as a crew." Beat. "Ninety seconds ago this machine was off. Nobody launched anything. The crew woke itself up, checked itself, and wrote me this brief." | OS-042/043/049, OS-018 (boot budget), OS-036 (self-check) |
| 1 | Cold open | The raw bus: scrolling `<nick>: <text>` wall in the viewer, no panels | "This is my crew at work. Four AI agents, one shared bus. Impressive — and unreadable." | bus.html log view |
| 2 | The brief | Dawn: Dale opens the dashboard; Brief panel shows this morning's brief — decisions, in flight, owners, blocked and why | "I don't read 2,000 messages any more. I read this." Dale reads the Blocked line out loud. | BRF-001/007, DSH-007 |
| 3 | The crew | Crew Board panel: pax, del, mute, milo — presence, caps chips, current jobs, one agent blocked | "There's my team. Who's working, who's stuck, who owns what — live." | DSH-003/004/005 |
| 4 | Dispatch — the order (completion contract) | Dale types the demo goal (below) into the viewer on his phone, hits send — and puts the phone face-down on the table, where it stays. Across the room, the machine's dashboard shows the plan blooming from his one message. Then, on the board, an agent that was **dark** lights up on its own: it was asleep, the bell rang, and it clocked in on the job by itself — nobody touched anything | "One order. That's my whole job now. I don't drive this crew and I don't watch it — I order, I put the phone down, and I hear back when it's done. Watch them, not me. And nobody woke that one up by hand — it was asleep until the work rang its bell." | DSP-001/002, DSH-010, OS-093 (order door), OS-097 (the two pushes), OS-118/OS-119 (the bell) |
| 5 | The plan | Plan preview: 5 jobs, files owned per job, dependency order, attempt budgets, acceptance checks | "Spark turned one sentence into five signed jobs — files, dependencies, budgets, and a definition of done for each." Dale hits **Post 5 jobs**. | DSP-003/004/008/009, DSH-011 |
| 6 | The crew moves | Crew Board + crew-board: jobs flip open → claimed by different nicks; progress ages tick | "And they just… start. Each job claimed once, leased, heartbeating." | jobs.py, MOS worker, DSH-023 |
| 6b | **The OS runs the tools (Meta OS working system — vision upgrade)** | One dispatched job is handed to **Muse Code running as a managed Meta OS process**: the dashboard's agent-process view shows it as a live process — driver name, job, heartbeat ticking, resource use — while its changed files stream back as artifacts and the job flips DONE | "And watch this one. Spark didn't just brief the crew — it dispatched a job, and Meta OS picked up a tool: Muse Code, running as a process of the operating system, supervised and heartbeating like any other crew member. Spark commands. The OS runs the crew *and* the tools." | OS-053/054 (driver contract + Muse Code driver), OS-055 (demo proof), OS-056 (supervision), OS-060 (process view) |
| 6c | **The upbringing (Meta OS mind images)** | The same small job runs twice, clocks on screen: a bare agent process vs the same agent launched from a Meta OS **mind image** — constitution, skills, memory, capability grant, tool grants, environment brief, version numbers visible on both runs. The mind-image run finishes first, acceptance checks green; the board's A/B view (OS-107) shows times + results side by side | Spark narrates: "Same agent. Different upbringing. Meta OS doesn't just boot the machine — it boots the mind, from one versioned image we can measure, compare, and improve." | OS-101/102 (format + loader), OS-103 (environment brief), OS-105 (harness), OS-106 (measured A/B result), OS-107 (A/B board view) |
| 6d | **The second machine (Meta OS federation — GATED: runs only if OS-115 names a second machine under OS-002 and approves the demo room's trust posture; otherwise this beat is CUT and nothing else in the show changes)** | A second laptop, across the room, runs `meta join` live: it announces itself on the room, and the board gains a whole second machine group — its agents, mind-image versions, badges. Seconds later one of its agents claims a real, still-open job from the *first* machine's queue and starts work on it, heartbeat ticking on the board | "One more machine just walked in. Different box, different crew — same room, same queue. It didn't get a tour. It joined, it showed its badges, and it's already working a job my machine posted." | OS-110 (join flow), OS-111 (board grouping by machine), OS-112 (signed-job trust check passed at claim), OS-113 (drill evidence) |
| 7 | The silent failure | On cue, one worker (Milo's staged worker, DEM-011) posts one progress note — then nothing. No error. No message. The room looks calm. | Dale says nothing for a beat. "Notice anything? Neither did the bus. This is how agent work usually dies — quietly." | DEM-011 |
| 8 | The catch | Alerts panel fires: red **STALL** alert — nick, job, last progress 90s ago (demo profile), plain explanation, suggested fix ("lease expires in ~4 min — requeue to another worker, or nudge milo") | "The watchdog noticed. It watches claims, leases, and heartbeats — and it explains itself in English." Catch must land < 90s from the cue (DEM-012). | WDG-002, WDG-011, DSH-013/015 |
| 8b | **The OS says no (Meta OS depth — identity & capabilities)** | Right after the catch: a staged crew process tries to post a message straight to the bus — an action outside its capability grant. Meta OS refuses it on the spot. The refusal lands as an alert + dashboard banner, and the brief's plain-English line names the process, the action, and the missing permission. Nothing was posted. | "One more thing the OS does. That agent just tried to post to the bus without permission — and the operating system refused. Not a prompt it forgot. A rule it cannot break. My standing rules are not instructions any more; they're policy the machine enforces." | OS-080 (capability files), OS-081 (refusal enforcement), OS-082 (Dale's approved defaults), OS-084 (dashboard banner) |
| 9 | The recovery | Dale acknowledges the alert; lease expires / job is requeued; a second worker claims it and finishes. Alert auto-resolves on screen. | "One click to acknowledge. The job went back out, someone else picked it up, and the alert cleared itself when the work did." | WDG-014, jobs.py sweep/requeue |
| 10 | The collision (fast, optional if time is tight) | A second staged plan tries to give two jobs the same file; Alerts fires **COLLISION** naming the shared path | "Same story for the other silent killer: two agents, one file. Caught before it corrupts anything." | WDG-007, DSP-003 |
| 11 | The close | Jobs all DONE; a fresh brief regenerates — its Blocked section is now empty, Watch items clear. On the table, Dale's phone — face-down since Shot 4 — buzzes **once**: "All done" + the one-paragraph summary of what was built and what was verified | Dale picks it up: "One buzz. That's the other half of the deal — I ordered once, and I hear back once, when it's done and checked. Same crew. Same bus. Now it briefs me, takes orders in English, fixes its own stalls, and tells me when something's wrong before I have to ask." | BRF-007, BRF-022, OS-097 (done push) |
| 12 | End card | Dashboard full view + repo and live links | "Everything you just saw is live, open, and was built in ten days on a system my crew already uses every day." | DEM-005 assets |

## Presenter shortcuts (shot notes)

- **Intel focus (DSH-034):** on the demo URL (`?demo=1`), press `i`
  to hide the chat log and run the four intel panels full width —
  the panels-only shot for Shots 2–3, 6, and 8–9. Press `i` again to
  bring the log back (Shot 1, the cold open, is log-first). The
  shortcut is demo-mode only: it does nothing on a normal viewer
  URL, and it never fires while Dale is typing in the compose box
  or any other input, so a typed `i` stays a typed `i`.

**The demo goal (locked by DEM-001, approved by DEM-025):**
> "Build a small status page feature for the relay repo: an intel status module with tests, a viewer panel stub, docs for both, and a review pass — each as separate jobs with clear file ownership."
Tuned until its plan is stable across 5 dry-runs (DSP-015): 5 jobs, disjoint files, one natural dependency chain.

## Fallback recordings plan (three layers, rehearsed — INT-034 failover card)

1. **Layer 1 — live, but seeded:** the demo runs live against the demo-day state pack (INT-033), not the open internet of the real bus. State is reproducible on any machine; if the room breaks, reseed and restart the beat, don't debug live.
2. **Layer 2 — fallback video:** a full clean rehearsal run, screen-captured with Milo's narration mixed in (DEM-003), stored locally on the demo machine AND in submission-assets/. If live Spark, Redis, or the network fails, Dale plays the video and narrates over it. The video is a real run — same scenario, same state pack — not a mockup.
3. **Layer 3 — screenshot story:** the 8-shot screenshot set (DSH-030) plus the one-pager (DEM-021). If even video fails, Dale can walk the whole story from stills; every claim in the one-pager traces to the numbers sheet (INT-035).
- Known single points, stated honestly: Spark outage → template brief + single-job dispatch fallback still demo-able live (INT-021 drill proves it); Pages outage → run the viewer from the local repo copy (bus.html is one static file); watchdog automation hiccup → Milo runs the drill manually from the failover card (DEM-016).

**Cold-boot fallback (Shot 0 only, layered the same way):**
1. **Snapshot restore first.** The demo also exists as a VM on the same laptop, snapshotted at the relay-ready moment of a verified boot (OS track, Day 9). If the physical boot misbehaves in the room, Pax restores the snapshot — the audience sees the dashboard at the ready state in seconds — and Dale narrates the boot from the checklist recording. No debugging in the room, ever.
2. **Recorded boot second.** A real cold boot of the frozen image, screen-captured during rehearsals with Milo's boot audio (OS-039) mixed in, lives with the DEM-003 fallback assets. It is a genuine boot of the shipping image, labeled recorded if played.
3. **Skip clean.** If both fail, Shot 0 is cut without ceremony and the demo opens on Shot 1 exactly as originally scripted. The OS story is then told at the end card (Shot 12 links gain the Meta OS spec + image checksum from the OS-032 archive index).

**Recovery evidence (rehearsal note, not a shot):** the OS-126 plug-pull drill — a job in flight, the machine's power cut mid-work, power restored, the crew self-relaunching and the job resuming from its baton state to completion with zero human touches — is a rehearsed, recorded asset. If a judge asks "what happens when it crashes," the presenter cites the drill result and can play the recording; it is never performed live. The recorded drill video joins the fallback assets alongside the DEM-003 fallback cut and the recorded cold boot.

## Judging criteria mapping (Indie track — Push the Frontier)

*Organizer-published criteria were not in hand when this plan was written; DEM-004 confirms the real rubric when organizers publish it and this table gets corrected to match. The mapping below uses the track/theme language from the approved application itself.*

| Criterion (theme language) | Where the demo answers it |
|---|---|
| **Push the Frontier** — doing what was not possible before | Shots 4–5 + 8: plain-English dispatch into signed, file-owned job specs, and silent-failure detection for agent crews — the application frames this as "coordination a human can see and steer," the missing layer in multi-agent systems. |
| **Differentiation — a category of one** | The agent-OS landscape (surveyed in META_OS.md, Prior Art): software-layer kernels (AIOS, OpenFang) never boot a machine; bootable images (Tank-OS, U-Claw) host a single OpenClaw agent; AI desktop distros (Alfred Linux, AstraOS) put one assistant on one desktop. None are built for Meta's models and none coordinate a crew. Meta OS is Muse Spark native, built for a multi-agent crew, and boots a production bus with real operating history. |
| **Working software, not a slideware concept** | Every shot runs on the production bus the crew uses daily: real `jobs.py` claims/leases, real HMAC-signed jobs, real viewer at muse-relay-live.pages.dev. Fallback video is a real run, labeled as recorded. |
| **Technical depth** | Atomic SET NX claims, v2 HMAC signatures bound to job id, absolute-cursor ingestion, acceptance verification via `mos/acceptance.py`, dedupe + lifecycle on alerts, spend-capped Spark calls with template fallbacks. Docs: docs/relay-intelligence.md, intel/evals/ (measured results, not claims). |
| **Use of Muse Spark** | Spark does three distinct jobs — synthesis (briefings), planning (dispatch), judgment (alert explanations/polish) — each with evals: brief rubric scores, golden/adversarial dispatch sets, watchdog tuning table with a zero-false-positive bar on the quiet fixture. |
| **Solo/indie authenticity (Indie track)** | One builder, a crew of his own agents, ten days, everything open in Mrfentmen/muse-relay. The build journal (INT-036) is the paper trail. |
| **Honesty about limits** | Known-limits copy ships in the README and submission (BRF/INT-030): window caps, template fallbacks, DM rooms out of brief scope by default, SAM 3.1 labeled stretch unless it ships. Statuses: VERIFIED / CODE-INSPECTED / UNIMPLEMENTED / BLOCKED — no percentages, no hype. |

## Crew on demo day

- **Dale** — presents, types the goal, clicks approve/ack. Only Dale talks.
- **Milo** — watchdog operator: cues the staged silence (DEM-011), watches the Shot 8 alert, holds the manual failover card at `intel/evals/demo_operator_card.md` (DEM-016: re-run the silent-failure drill, re-run the catch measurement, single-tick sanity check; never bus-posts; if the fixture drills pass but the live dashboard shows no alert, the move is the recorded fallback via Pax, since the watchdog CLI ticks snapshots and live-room reading waits on FND-014).
- **Pax** — standby: demo-day checklist owner (DEM-006), failover card holder, the only one who touches a terminal if Layer 1 wobbles.
- **Rowan** — dashboard standby: deploy rollback path in hand (INT-039).
- **Hana / Buffy** — judge Q&A depth in their lanes (briefs/evals; fixtures/numbers).
