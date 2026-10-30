# Meta OS — the machine under Relay Intelligence

**Decision (Dale, 2026-10-22):** we are building a real OS for the hackathon entry — a Linux based operating system rebuilt for Meta agents. Name: **Meta OS** (Dale's call, 2026-10-22 — renamed from the early-draft working name) — because it is built *for* Meta agents: Meta's models (Muse Spark) are the intelligence layer, Meta's own coding agent (Muse Code) is the first citizen process, and the machine's whole purpose is running Meta agent crews. Relay Intelligence (the Muse Spark mission control: briefings, dispatch, watchdog, dashboard) is the userland that ships inside it. Two layers, one story: Meta OS is the machine, Relay Intelligence is the mind.

On the name: "Meta OS" is Dale's name for this hackathon entry, chosen because the system is built for Meta agents on Meta's models; a public or commercial release beyond the hackathon would revisit the name for trademark reasons.

**Vision upgrade (Dale, 2026-10-22):** Meta OS is not only a demo appliance. It is an operating system Dale actually has to use. Meta agents on it drive *other* coding agents as managed system processes, the MCP tool estate ships as a system service, and skills ship as installable applications. The full shape is specified in "Meta OS as a real working system" below; the daily-driver track (Phase B) is post-hackathon scope and is fenced off from the hackathon critical path.

Meta OS is not a new kernel. It is a mainstream Linux base (Debian family) rebuilt into an agent appliance image: the machine boots straight into the crew — systemd brings up the relay bus processes, the job queue workers, the watchdog supervisor, the briefing service, and the mission control dashboard — with per-agent resource limits, a structured journal of crew activity, and one install/update path. The full OS spec (base, image pipeline, service map, boot sequence, test plan) lives in this file; the Spark layer it carries is specified in MASTER_PLAN.md.

## Prior Art / Differentiation

Existing "agent OS" work falls into three buckets, and none of them is what Meta OS is:

1. **Software-layer "agent kernels."** AIOS (Rutgers — arXiv 2403.16971, github.com/agiresearch/AIOS) schedules LLM calls and tool calls in software on top of a normal OS; OpenFang is a single-binary agent runtime. These are libraries and runtimes — none of them boot a machine.
2. **Bootable agent images.** Red Hat's Tank-OS is a bootable, image-based Linux appliance dedicated to running OpenClaw; U-Claw is a bootable Ubuntu USB built for OpenClaw. These do boot — but each is a host for a **single agent**, not a crew.
3. **AI-native desktop distros.** Alfred Linux and AstraOS put a local assistant on a personal desktop. The AI is a feature of a one-human desktop, not the coordination layer for a team of agents.

**None of the three is built for Meta's models, and none is built for multi-agent crews.**

Meta OS differentiation, in one breath:

- **Muse Spark native** — the intelligence layer (briefings, dispatch, watchdog judgment) is Spark, reached through the Meta Model API, not bolted onto another vendor's model.
- **Crew coordination is the system's purpose** — the bus, the signed job queue, claims/leases, presence, and the watchdog are not apps on the OS; they are what the OS is *for*. The machine exists so a crew of agents can work as a team a human can see and steer.
- **It boots a production system with real operating history** — the muse-relay bus the image brings up at boot is the same bus Dale's crew already runs on every day, with real jobs, real rooms, and real history behind it. The demo machine does not simulate a crew; it wakes one up.

One more signal that this is the right shape: Meta's own Muse product runs each agent in a dedicated Secure VM with a Sentinel supervisor watching it — the industry direction is contained machines for agents. Meta OS takes that same idea one level up: not one agent in one VM, but a whole crew on one bootable OS, supervised as a system.

One more piece of prior art, because it is the conceptual core: the agent "kernel" systems (AIOS and its peers) schedule model and tool calls; the bootable images (Tank-OS, U-Claw) host a single agent; the AI desktop distros assist one human at a keyboard. **To our knowledge, nobody treats the agent itself — its instructions, its skills, its memory, its tools, and the information about its surroundings — as one OS-assembled, versioned, measurable launch image.** Meta OS does: it boots machines from a disk image, and it boots *minds* from a mind image (see "Mind images: the OS boots minds, not just machines" below). The claim is exactly that, no wider: an operating system that boots machines **and** minds.

---

## The guardrail (read first)

**Meta OS is the chassis. Relay Intelligence — the Muse Spark layer — is the payload.**

**Anti-bloat principle:** depth comes from the system services in "Depth: the four system services" below, and only from them. Anything that is an application belongs in skills, not in the OS. A new OS-level subsystem needs a Dale decision, a lived failure mode it fixes, and a task ID — otherwise it does not exist.

The Spark critical path in MASTER_PLAN.md (Foundation → briefings/dispatch/watchdog engines → dashboard → demo) ships and demos on a normal machine even if the image track slips. No OS task may block a Spark task. The image track runs in parallel, freezes earlier (Nov 2 12:00 ET), and earns its place in the demo only at Dale's Nov 1 go/no-go (OS-004). If the ruling is no-go, the demo opens on the dashboard exactly as DEMO.md originally scripted, and Meta OS is presented as the deployment target with the boot video as a supporting asset — nothing else changes.

## Base choice

**Debian 12 (bookworm), amd64, one base only** (OS-005).

Why Debian, in order of weight:

1. **systemd is native and boring.** The whole service model below (units, targets, slices, journald) is stock Debian. No fighting the init system, ever.
2. **The stack already runs on it.** The relay processes are Python stdlib + Redis-over-HTTPS (Upstash); Debian's python3 is a known quantity for this codebase, and the image bake (OS-011) is a clone + venv, not a packaging project.
3. **The image tooling is mature.** Packer + preseed and live-build are both Debian-first crafts with a decade of answers online — important when the builder is an agent crew working from documentation.
4. **Small enough to be an appliance.** A netinst-derived package set keeps the image lean (tracked in OS-029) and boots fast (budget in OS-018).

Rejected: Ubuntu (snap stack fights the appliance model and the boot budget), Alpine (musl + OpenRC means re-solving service supervision we get free from systemd), Arch (a moving base under a frozen demo is a self-inflicted wound). The kernel is the stock Debian kernel — Meta OS is a rebuilt system on the Linux kernel, not a new kernel, and all copy says exactly that.

## Image build pipeline

**Primary route (OS-007): scripted Packer + QEMU unattended build.** One command from a clean checkout produces `metaos-<date>.img` + `.sha256`:

1. Packer's QEMU builder boots the pinned Debian 12 netinst image (source + sha256 in `os/BASE.md`, OS-005).
2. `os/preseed.cfg` answers every installer prompt (OS-009): single `relay` user, autologin, UTC + en_US, one partition + swapfile. Zero interactive steps.
3. Provisioning applies, in order: `os/packages.txt` (pinned manifest, OS-010) → bake the stack (clone muse-relay at a pinned commit to `/opt/relay`, build its venv, OS-011) → install `os/assets/` identity (OS-025) → install units from `os/services/` and enable `relay.target` → stamp `/etc/metaos-version` (OS-020) → run the secrets sweep (OS-012: the image must contain no credential material).
4. The disk image is the artifact. It is written to a laptop SSD/USB or attached to a VM unchanged — one artifact, both demo targets.

**Named fallback (OS-008): live-build ISO.** A `os/live-build/` configuration producing a bootable ISO of the same package and service set, usable as a live system (and the field-kit USB, OS-031). The fallback exists for one scenario: the primary image fails on the demo hardware late. Divergences between the two artifacts are documented in `os/BASE.md`; the demo never depends on a fallback-only behavior.

**Reproducibility rules:** pinned base, pinned packages, pinned repo commit. A build that cannot name all three is not a Meta OS build. Build archive with checksums and logs is OS-032; per-image changelog is OS-030.

## Service map — real repo processes, under systemd

Every service is an existing muse-relay process or an intel/ module from MASTER_PLAN.md. Nothing in this table is invented for the OS.

| Unit | Real process | Runs as | Starts after | Restart |
|---|---|---|---|---|
| `relay-bus.service` | Presence/watch/store stack: `presence.py` renewal + `watch.py`/`poll.py` listeners keeping the bus connection and local `store.py` JSONL current | relay | network-online.target | on-failure |
| `relay-jobs.service` | `jobs.py` queue service loop (announcements, claim mutexes, lease sweep on start) | relay | relay-bus | on-failure |
| `relay-overseer.service` | `mos/overseer.py` tick loop (dispatch + acceptance verification via `mos/acceptance.py`) | relay | relay-bus, relay-jobs | on-failure |
| `relay-worker@<nick>.service` | `mos/worker.py` per-nick claim/work loop (template unit, one instance per crew nick) | relay | relay-jobs | on-failure |
| `relay-watchdog.service` | `intel/watchdog.py` detector loop + its own heartbeat (`muse-bus:intel:wd:beat`) | relay | relay-jobs | on-failure |
| `relay-watchman.service` | `relay-watchman` — the bell (see "The bell" below): a small resident CLI program, not an agent; watches the queue + worker heartbeats, wakes sleeping agents with their job as their brief, and works the self-repair ladder's mechanical rungs (nudge / restart / reassign via baton pass) | relay | relay-jobs | on-failure |
| `relay-uplink.service` | `relay-uplink` — the order door (OS-093, first light): a small resident CLI program, not an agent; takes Dale's plain-English phone orders in as signed job-set intake records, queues them while the connection is down (exponential backoff, capped 300s), and drains them in order on reconnect; it never auto-posts past the DSP-007 approval gate | relay | network-online, relay-jobs | on-failure |
| `relay-brief.service` | `intel/brief.py` boot brief generation (oneshot; Spark with the BRF-008 template fallback) | relay | relay.target ready check | no (oneshot) |
| `relay-dashboard.service` | Local static serve of `bus.html`/`index.html` + `crew-board.html` with Chromium in kiosk mode on the graphical session | relay | relay-bus | on-failure |
| `relay-ready.service` | Oneshot gate: verifies every unit above is active, then writes `/run/metaos/ready` | relay | all of the above | no (oneshot) |

All units are grouped under **`relay.target`** (OS-016). The rescue boot entry (OS-022) starts the base system *without* relay.target.

**Relay bus unit (OS-013, Pax, first light):** `os/services/relay-bus.service` runs the real `watch.py` listener from `/opt/relay` as the relay user, `--interval 10`, with its own presence beat on the loop, under `relay.target`. It restarts on failure, orders after `network-online.target`, and carries the OS-012 secrets gate (`ConditionPathExists=/etc/metaos/secrets.env`, so an unconfigured boot skips it honestly). No secret is on the command line: no `--dm` flag, token via the secrets env file only. `build-image.sh` enables it in `relay.target.wants` and `build-live.sh` stages `services/*.service`, so both image routes carry it. Pinning tests in `tests/test_os_bus_unit.py`. Still owed on the test image: the kill-restart run and the clean start-order check, and the wider presence/watch/store stack beyond the `watch.py` listener (no `poll.py` unit here); `systemd-analyze verify` is a syntax check only.

**Relay jobs unit (OS-014, Pax, first light):** `os/services/relay-jobs.service` runs the real `jobs.py sweep` from `/opt/relay` as the relay user, a oneshot lease sweep ordered after `network-online.target` and `relay-bus.service`, under `relay.target`. The sweep requeues claimed jobs whose claim holder is gone, so a job posted before shutdown is claimable again after boot. It carries the OS-012 secrets gate (`ConditionPathExists=/etc/metaos/secrets.env`, so an unconfigured boot skips it honestly) and no secret is on the command line: the token travels only as the `MUSE_RELAY_TOKEN_FILE` path. `build-image.sh` enables it in `relay.target.wants` and `build-live.sh` stages `services/*.service`, so both image routes carry it. Pinning tests in `tests/test_os_jobs_unit.py`. Still owed on the test image: the announced-and-claimable-after-boot run; and the continuous queue-service loop half of the OS-014 wording, since `jobs.py` defines no loop or serve subcommand yet.

**Relay overseer unit (OS-015, Pax, first light):** `os/services/relay-overseer.service` runs the real overseer tick from `/opt/relay` as the relay user, a oneshot ordered after `network-online.target`, `relay-bus.service`, and `relay-jobs.service` and wanting all three, under `relay.target`. The tick is `mos.py tick` (a shim onto `mos/cli.py`, whose tick subcommand runs `mos/overseer.py` `tick()`): a lease sweep, a stale-capability prune, and verification of done-but-unverified jobs. The loop is the timer: `relay-overseer.timer` fires the service 2 minutes after boot and every 5 minutes after, wanted by `relay.target`; `build-image.sh` enables the service itself with a `relay.target.wants` symlink and `build-live.sh` stages `services/*.service`, so both image routes carry it. It carries the OS-012 secrets gate (`ConditionPathExists=/etc/metaos/secrets.env`, so an unconfigured boot skips it honestly) and no secret is on the command line: the token travels only as the `MUSE_RELAY_TOKEN_FILE` path. Note: the unit as it landed with the OS-006 tree wanted only `network-online.target` and ordered after `relay-jobs.service` alone; this batch brings the `[Unit]` section up to the OS-015 wording before pinning it. Pinning tests in `tests/test_os_overseer_unit.py`. Still owed on the test image: the tick run itself, the timer actually firing on schedule, and the verify-done half against a real worker branch.

**Boot target and ready gate (OS-016, Pax, first light):** `os/services/relay.target` groups the crew units the OS-016 wording names: dashboard, bus, jobs, overseer timer, ready, watchdog, brief, and firstboot, wanted by the target itself and enabled into `relay.target.wants` by `build-image.sh`, the Packer provisioner, and the live-build hook on the same list, so all three image routes carry the same set (the overseer service itself rides a `relay.target.wants` symlink beside the timer). The target as it landed with the OS-006 tree wanted only dashboard, bus, jobs, overseer timer, ready, and firstboot; this batch adds watchdog and brief to the target wants and to all three enablement lists before pinning them. `os/services/relay-ready.service` is the oneshot gate running `bin/metaos-boot-checklist`, ordered after every unit the gate checks and deliberately not after the brief, which runs after the ready gate by design. The gate writes `/run/metaos/ready` only when the gateable set passes: dashboard and watchdog always, plus bus, the jobs sweep `Result`, and the overseer timer once secrets exist; before firstboot the secrets-gated units are honestly skipped, so only dashboard and watchdog are required there. The jobs sweep is gated on its `Result` because jobs and overseer are oneshots with no `RemainAfterExit`, so `is-active` reads inactive after a clean run; the overseer tick itself is not gated, since its timer first fires 2 minutes after boot. Worker instances are not auto-enabled (per-nick only, OS-017) and the watchman has no unit file yet (OS-118), so neither is grouped or gated. Pinning tests in `tests/test_os_target_unit.py`. Still owed on the test image: reaching `relay.target`, the marker appearing only with all units active as proven by disabling one unit, and a completion stamp for the oneshot sweep and tick beyond the jobs `Result` the gate reads today.

**Supervision contract (OS-034, Milo + Pax):** systemd `Restart=` owns *process death* — a crashed worker is restarted by the machine, and the watchdog merely records the event. The watchdog owns *silent-but-alive failure* — a worker that lives but stopped progressing (heartbeat stale, lease rotting) is a watchdog alert, and systemd is never told to fight it. This split is the OS-level expression of the product's core claim: processes crash loudly; agents fail silently; each failure class gets the supervisor built for it.

**Resource limits (OS-035, Milo):** worker instances live in `relay-workers.slice` (os/services/relay-workers.slice), joined by setting `Slice=relay-workers.slice` on `relay-worker@.service` (Pax OS-017, worker fleet template, landed first light: the template unit, the per-instance env convention, and the slice wiring are in; instances are not auto-enabled until the handler program and the mos.py DM-secret env path land, so the two-instances-side-by-side acceptance is still owed). Starting defaults, now the spec record: `CPUQuota=100%` (one CPU-equivalent per worker, so a runaway cannot take every CPU the bus, queue, and dashboard need) and `MemoryMax=1G` (a leak is capped before it threatens the box). Basis, stated plainly: the repo load numbers (Pax INT-006 tick timings over a 200-job queue; Milo INT-023 watchdog tick under a failing 200-job queue) are wall-clock timings, not worker RSS or CPU profiles, so they bound tick cost but do not tune these values. These defaults are conservative starting points, not tuned measurements; the tuning pass against measured worker RSS and CPU on the test image is still owed, and it replaces these values here and in the slice file. Live enforcement (a runaway worker throttled on the test image while the bus stays responsive) is also still owed: the drill intel/drills/cgroup_limits.py checks the file and systemd-analyze verify, and reports the host block on machines whose cgroup hierarchy exposes no cpu or memory controller instead of faking an enforcement pass.

**Driver limits (OS-056, Milo):** driver processes live in `relay-drivers.slice` (os/services/relay-drivers.slice), joined by `Slice=relay-drivers.slice` on the per-driver template unit (os/services/relay-driver@.service, landed by Pax OS-054). The slice is separate from relay-workers.slice so a runaway driver cannot eat the worker budget and vice versa. Starting defaults, now the spec record: `CPUQuota=100%` and `MemoryMax=1G`, shared with OS-035 until driver memory and CPU profiles are measured on the test image; the tuning pass replaces these values here and in the slice file. The supervision half is proven at the detector level, not the image level: driver heartbeats feed the existing WDG stall detectors unchanged (intel/drills/driver_supervision.py: a driver nick gone from presence with a claimed job past the stall window yields exactly the same presence-stall alert a worker would, and the tick never mutates the job, which is the OS-034 split in code). Still owed on the test image: a driver process appearing in this slice, live cgroup enforcement, and the kill -9 systemd restart, all waiting on the driver runner programs and the test image; the wedge case (driver alive, heartbeat stale) is OS-057's drill. Follow-up (Milo, OS-056 bridge, 2026-10-28): intel/drills/driver_heartbeat_bridge.py proves the bridge from a real MuseDriver heartbeat record to the unchanged stall detectors (heartbeat ts becomes last_progress_at; fresh yields nothing, stale present yields progress-stall only, stale absent yields presence-stall only). A heartbeat does not register presence; that stays with the OS-055 handoff.

**Driver stall drill (OS-057, Milo):** a wedged driver is alive, so it stays in the presence list and fires WDG-003, not WDG-002: a driver nick in caps, present, holding a claimed job with no progress past the progress-stall window yields exactly one progress-stall alert, severity critical, naming the driver and job, through the same detector a wedged crew worker fires through, with no driver special-casing in intel/watchdog.py. Under the demo thresholds profile (intel/metaos-demo.env, progress-stall window 1 minute) the same wedge fires at 61 seconds and stays quiet at 30 seconds, so the alert lands inside the demo threshold. Drill intel/drills/driver_stall.py, transcript intel/evals/driver_stall.log: detector phase, worker-equivalence phase, demo-profile phase, and contract phase (a full tick alerts once for the wedged driver, leaves both driver jobs claimed, and leaves the sibling driver unalerted and untouched). Still owed on the test image: the wedged driver actually restarted by systemd per the OS-034 contract, and a live sibling driver kept running through that restart, both waiting on the driver runner programs and the test image; the watchdog half proven here is that the tick never mutates either job, so it cannot fight systemd or touch the sibling.

**Self-repair ladder (OS-095, Milo):** on a stall the watchdog acts before it reports, in a ladder: nudge a live-but-stuck worker, restart a dead one, reassign a job held by the wrong worker. The ladder module (intel/ladder.py) is the judgment, not the hands: rung selection is a pure function of snapshot facts (registered and present means nudge, registered and absent means restart, outside the caps registry means reassign with a baton of title, deposited progress, and files), every rung is journaled with its reason and rendered as a brief line, and Dale is contacted at no rung because the module has no push or announcement path. The ladder never mutates a snapshot or a claim, so it cannot fight systemd over a restart or steal a live worker's job: the restart half belongs to systemd under the OS-034 contract and the reassign half to the overseer via the OS-125 baton pass, both worked mechanically by the watchman on its machine (Pax OS-118). Drill intel/drills/self_repair_ladder.py, transcript intel/evals/self_repair_ladder.log. Still owed: a live nudge, a real systemd restart and a live overseer reassign on a booted test image, the watchman's mechanical execution, and the escalation when every rung is spent (OS-096).

## Boot sequence

Power-on to a working crew, no human input (OS-042):

1. **Firmware → GRUB → stock Debian kernel.** Plymouth splash carries the Meta OS identity (OS-025); no stock branding on the path.
2. **systemd → relay.target.** network-online, then units in the table's order: bus, jobs (lease sweep first, so yesterday's dead claims are cleaned before anyone looks), overseer + worker fleet, watchdog.
3. **Watchdog self-check (OS-036).** Each detector runs once against the seeded stale-lease fixture; a green record is written. A red self-check fails the boot honestly — the boot checklist shows it, nothing pretends.
4. **relay-ready gate.** All units active → `/run/metaos/ready` written (OS-016).
5. **Dashboard up full screen.** The graphical session autologins; Chromium kiosk serves the local viewer copy (OS-044). The boot checklist view (OS-043) flips each line — bus, queue, supervisor, watchdog, brief — from real unit/ready states, with Milo's live watchdog status line (OS-041).
6. **Boot brief (OS-049).** `relay-brief.service` generates the first brief: previous-session digest (OS-051), carried-over jobs, overnight decisions, what the watchdog saw during boot — with its data window stated honestly (OS-050). Target: on screen within 60 seconds of the ready gate; if Spark is unreachable, the template fallback brief appears instead and says so.
7. **Steady state.** The machine is now indistinguishable from the crew's everyday setup — because it is the everyday setup, booted.

**Boot budget (OS-018):** power-on → dashboard-ready ≤ 90 seconds on the demo hardware, measured and recorded across three boots; blockers are cut from `systemd-analyze blame`, not vibes.

## Crew activity journaling

Two layers, both already native to the stack:

- **journald** carries every relay unit's stdout/stderr, restarts, and cgroup events. `journalctl -u 'relay-*'` is the machine's own account of itself, and the watchdog's journal watch (OS-037) turns unit failures into SYSTEM alerts in the same alert store the dashboard reads.

**Journal watch (OS-037, Milo):** `intel/watchdog.py::detect_journal_failures()` reads journalctl -o json lines and yields one SYSTEM alert per failed relay unit — kind `system-failure`, severity critical, subjects the unit name, no nick or job, so a unit failure can never be mistaken for a worker stall. The failure rule is relay unit + (systemd failure message or err-or-worse priority); healthy relay lines, non-relay failures, and unparseable lines stay silent. Failures group by unit and dedupe through the WDG-013 cooldown, and the suggested fix points at `journalctl -u` and an operator restart — the watchdog never restarts a unit itself, per the OS-034 contract. Proven on fixtures (drill `intel/drills/journal_watch.py`, 10 PASS; 15 tests; fake-store write + query within one `journal_watch_tick`). Still owed on the test image: a real force-failed unit landing in the dashboard feed within one service loop, and wiring the journal iteration into the relay-watchdog.service loop (currently snapshot ticks only).
- **The bus record** — `store.py` JSONL per room plus the digest/brief records — carries what the crew said and did. The build journal (INT-036) and the boot brief both read from here.

Nothing new is invented for logging; the OS contribution is that the machine and the crew finally keep their records in the same house.

## Install and update path

- **Install** is the image: write `metaos-<date>.img` to the target disk (dd/Etcher instructions in `os/README.md`, OS-027) or attach it to a VM. There is no installer wizard beyond the preseed that built it.
- **First boot (OS-012):** the image contains zero credentials. Firstboot generates the local job-signing keyring (chmod 600) and prompts once for the two secrets the system needs — the Muse Spark key and the Upstash token — stored in env files, chmod 600, never on the bus, never in a commit. This is the same secret-handling posture as the existing keyring/token files in the repo.
- **Update (OS-021):** `metaos-update` pulls a git bundle of muse-relay + intel updates, verifies it, applies it to `/opt/relay`, and restarts `relay.target`. Rollback swaps `/opt/relay` back with the previous tree kept at `/opt/relay.prev` (a second rollback swaps back); it is not a re-apply of a bundle. Apply, swap rollback, and every refusal are pinned by `tests/test_os021_update.py` against fixture trees via the script's `METAOS_RELAY_ROOT` test hook. Base OS packages do **not** update through this path during the build window — the base is frozen (OS-003/OS-005) so the demo machine cannot drift.

## Demo targets

1. **Primary: the physical demo laptop** — named by Dale (OS-002), running the primary image on bare metal. The cold-boot opening (DEMO.md Shot 0) is performed on this machine.
2. **Secondary: the VM image** — the identical `.img` attached to a QEMU/VMware/VirtualBox VM. Purposes: rehearsals anywhere, the snapshot-restore fallback (DEMO.md), and the judges' "run it yourself" story.

One artifact serves both targets by construction (OS-007); any hardware-specific fix is a spec change here first, never a hand-edit on the demo machine.

## Boot test checklist

Run by `os/test-boot.sh` (OS-019) in QEMU, and by hand on the demo laptop before demo freeze. Every item is pass/fail with evidence, no partial credit:

1. Image boots unattended to the graphical session; zero prompts, zero clicks. (OS-009, OS-042)
2. `relay.target` reached; all units active; `/run/metaos/ready` present. (OS-016)
3. Boot time within budget; time recorded. (OS-018)
4. Boot checklist on screen flips from real unit states; killing a unit turns its line red. (OS-043)
5. Watchdog self-check record is green; a deliberately broken detector turns it red and fails the test. (OS-036)
6. Boot brief exists within 60s of ready; with Spark blocked, the template fallback brief appears and labels itself. (OS-049)
7. Boot brief states its data window and the previous-session digest correctly across a reboot. (OS-050, OS-051)
8. A job posted before shutdown is claimable after boot (lease sweep ran). (OS-014)
9. kill -9 a worker → systemd restarts it, watchdog logs the event, no false stall alert. SIGSTOP a worker → stall alert, no restart fight. (OS-034)
10. Network unplugged after boot → dashboard and panels render locally; Spark features degrade to their fallback states. (OS-044)
11. Secrets sweep: no credential material anywhere in the image outside the chmod-600 env files created at firstboot. (OS-012)
12. Version on screen matches `/etc/metaos-version`. (OS-020, OS-045)
13. In-flight jobs recovered count: after an unclean shutdown (power cut mid-job), the boot brief reports how many in-flight jobs were recovered from their deposited baton state, and the count matches the queue's lease-sweep record — recovered, never silently dropped. (OS-126, OS-127)

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Image work eats the Spark schedule | Guardrail above + parallel track + earlier image freeze (Nov 2 12:00). Pax arbitrates conflicts in favor of the Spark path, always. |
| Boot fails or crawls on demo day | Boot budget with measured evidence (OS-018); VM snapshot restore fallback and recorded boot video (DEMO.md fallback layers); rescue boot entry (OS-022). |
| Demo hardware differs from build hardware | One image for both targets (OS-007); hardware named early (OS-002); checklist run on the actual laptop before demo freeze, not just in QEMU. |
| Packer/QEMU build is flaky in the sandbox | Fallback live-build ISO (OS-008) kept buildable from Day 2 onward; image RCs archived from the first successful build (OS-032), never built last-minute. |
| Secrets leak into a public image or repo | Zero-credential image rule + automated sweep in the pipeline (OS-012); the image itself is never published with firstboot completed — judges get a fresh image plus the README path (OS-027). |
| Scope creep: "an OS" invites kernel/distro rabbit holes | This spec is the fence: stock kernel, stock Debian, services only. Anything not in the service map or boot sequence needs a Dale decision and a task ID before it exists. |
| The OS claim reads as hype to judges | Copy rule everywhere: "a Linux-based operating system rebuilt for Meta agents" — the boot is real, the services are real, the claim is exactly the artifact. Prior-art differentiation above keeps the claim narrow and defensible. |

---

## Meta OS as a real working system (vision upgrade, Dale 2026-10-22)

The sections above describe an appliance that boots a crew. This section describes Meta OS as the system Dale actually runs: Meta agents on it command other coding agents, the MCP estate is part of the OS, skills are its applications, and after the hackathon it grows into his daily machine. Tasks: OS-053–OS-077 in MASTER_PLAN.md. Items marked **[B]** are Phase B — post-hackathon, fenced off from the critical path.

### Agent drivers — coding agents are devices of the OS

A Meta agent (the Muse Spark layer: dispatch, overseer, watchdog) does not shell out to a coding agent and hope. It drives it through an **agent-driver adapter**, the way an OS drives hardware through a device driver. The contract (OS-053) is one interface every driver implements:

- **start(job_spec)** — launch the agent process against a signed job spec (files owned, acceptance checks, attempt budget — the FND/DSP spec format, unchanged).
- **stop()** — terminate the process cleanly; a wedged process is killed by the supervisor, never by hand.
- **heartbeat()** — the driver emits progress heartbeats in the bus progress format, so the watchdog's existing stall detectors work on driver processes with zero new detector code.
- **artifacts + status out** — on exit the driver returns the changed-file list, logs, and a status record the overseer's acceptance layer (`mos/acceptance.py`) can verify exactly as it verifies a crew worker's job.

Driver processes are **first-class citizens of the system**, identical in standing to `relay-worker@` instances: each runs as a systemd unit in a `relay-drivers.slice` (OS-056) under the same supervision contract (systemd owns process death; the watchdog owns silent-but-alive stalls — a wedged driver raises the same STALL alert as a wedged worker, OS-057), under per-process cgroup limits, with every action in journald and the bus record.

**Driver contract (OS-053, Pax, first light):** the contract lives in `os/drivers/CONTRACT.md` and the reference driver in `os/drivers/stub_driver.py`, with the ten-item conformance checklist in `os/drivers/CONFORMANCE.md` and pinning tests in `tests/test_os_driver_contract.py`. The stub runs a caller-supplied command as the agent child, logs output to `driver.log`, diffs a before/after snapshot for changed files, reports files outside the owned list separately, and builds its status record from `mos/acceptance.verify` against the workdir on disk. It enforces signature presence at `start()` and refuses unsigned specs; cryptographic verification stays at `jobs.py verify_job` claim time, so no keyring enters an agent process. It never posts to the bus: heartbeat records (`PROGRESS:<job_id> <note>` plus job id, note, and timestamp) go to a caller-supplied sink. Landed (OS-054): the Muse Code driver (os/drivers/muse_driver.py) builds a prompt from the signed spec, launches `muse exec --prompt-file <file>` with cwd=workdir, streams child stdout lines into PROGRESS heartbeat records and driver.log, and returns the contract artifacts record; os/drivers/run_driver.py runs one spec file to artifacts JSON, and os/services/relay-driver@.service is the per-driver template. The C1-C10 checklist passes against the driver with a fixture stand-in executable (tests/test_os_driver_muse.py, 17 tests); no real `muse` binary and no booted image exist here, so a live CLI run, the test-image checklist run, and the OS-055 overseer handoff stay owed.

Driver roadmap, in the order the contract earns them:

1. **Muse Code** (Meta's own coding agent) — the first driver, in-window (OS-054). A Spark-dispatched job executed by Muse Code as a managed Meta OS process is the demo proof (OS-055): Spark commands, the OS runs the crew *and* the tools.
2. **OpenCode** — second driver, Phase B (OS-067) [B].
3. **Freebuff / GLM** — third driver, Phase B (OS-068) [B]. Dale's Freebuff crew member becomes an OS-managed process instead of a hand-tended session.

Any CLI coding agent that can be wrapped to the contract becomes a device the OS can run. The contract is the port; drivers are how the OS grows new hands without growing new architecture.

### Pre-installed hands — the agent CLIs ship in the image

Drivers attach to programs, so the programs are already there. The image bake installs and configures the crew's working agent CLIs — **Muse Code, Claude Code, OpenCode, Freebuff, plus a node-based agent slot** for the terminal agents Dale runs — before any job exists, alongside the stack bake (OS-011) and the MCP gateway bake (OS-059), with the package pass (OS-063) recording exactly what shipped. Each tool ships under its own terms: the image installs it at bake time or at firstboot, whichever its distribution rules require, and the roster is bounded by licensing and availability, not by ambition — a tool that cannot be redistributed is fetched at firstboot or left as a documented slot, never bundled against its license. Every pre-installed program is configured the same way: pointed at the gateway's one local endpoint for tools, launched through the loader so it starts from a mind image, and supervised like any other process. The point is Dale's: a Meta OS machine wakes up already holding every hand the crew might need. Nothing gets installed mid-job; a driver never waits on a download; the baton pass (below) can hand work to a different program precisely because that program is already sitting on the machine, configured and ready.

### MCP as a system service — tools are the OS's system libraries

Dale's MCP gateway (`~/workspace/mcp-gateway` — the local gateway fronting his MCP estate: the 869 servers of the awesome-servers collection and the rest of his wired servers) ships in the image as a system daemon, `relay-mcp-gateway.service` (OS-058, OS-059), started under `relay.target` like every other crew service. Every agent process on the machine — crew workers and driver processes alike — reaches the full tool estate through the gateway's one local endpoint.

The OS framing is exact: **MCP servers are Meta OS's system libraries.** A normal OS ships libraries so programs do not each reimplement the world; Meta OS ships the gateway so no agent process reimplements tool access. The gateway is baked at a pinned state beside `/opt/relay`; its secrets follow the image rule (none baked, firstboot env only, OS-012).

First light (OS-058, Pax, 2026-10-28): `os/services/relay-mcp-gateway.service` lands the daemon unit (relay user, after network-online.target, Restart=on-failure, OS-012 secrets gate, ExecStart on the baked path `/opt/relay/mcp-gateway/gateway.py`, WantedBy=relay.target) with pinning tests in `tests/test_os058_gateway_unit.py`. Bake (OS-059, Pax, 2026-10-28): all three image routes bake gateway.py plus backends.json beside /opt/relay, write a .metaos-gateway-bake stamp with the bake date, the source dir, and the sha256 of both files (the pin is by hash, because the gateway source is a workspace checkout, not a git repo), and enable the unit under relay.target, which Wants it back; the OS-012 sweep gains the bake allowlist, so any other file under /opt/relay/mcp-gateway in a built rootfs is a finding. The bake copies only the daemon and its catalog, never the working estate around them, so the downstream server runtimes and the gateway Python deps (mcp, starlette, uvicorn) stay owed: only the backends whose runtimes the image carries will come up, and the gateway skips the rest with a log line and keeps serving. Service active at boot and a worker plus driver call through the local endpoint stay unproven until a booted test image exists.

### Skills as applications — the app layer

Dale's skills collections (skills-2 — 206 skills — and the rest of his skill trees) become **installable OS applications**. The skills loader (OS-065) mounts skill folders into an agent process's launch environment the way an OS loads apps for a user session: an agent process started on Meta OS begins work with its skills already present — the right persona, craft, and judgment loaded before the first job, not pasted in by hand mid-session.

First light (OS-065, Pax, 2026-10-28): `intel/skills_loader.py` is the canonical loader: collection scan (SKILL.md required, unmountable folders skipped by listing and refused by mounting), verbatim mount with a hash-pinned skills.json manifest, verification that names tampered or unlisted mounts, and refusal of duplicate names, traversal names, and symlink escapes before anything is copied. The OS-102 mind loader mounts its bundle skills through it, so the bundle path and the collection path share one rule. A fixture collection (`intel/examples/skills/`) proves the rule from the README alone, and all three image routes bake the conventional collection root /var/lib/metaos/skills empty plus a marker, relay-owned, with no skill content baked. Still owed: a driver process showing a mounted skill active in its first action with an unmounted control run beside it (OS-055 proof), and a real collection installed at the image root. The shape is proven with a probe process, not a driver: intel/launch_run.py (OS-102 follow-up) starts a real child from an assembled launch directory, and its pinning tests show the mounted skill named in the probe's first action with a control launch silent on the skill it never mounted.

Skills are therefore the app layer of Meta OS: the kernel is Linux, the system libraries are MCPs, the processes are agents, and the applications are skills.

### Daily driver track — Phase B (post-hackathon) [B]

The hackathon ships the appliance. Phase B turns it into the machine Dale actually uses every day. Every Phase B task is tagged [B] in MASTER_PLAN.md so the hackathon critical path stays readable at a glance; none of it is demo scope.

- **A desktop session for Dale** (OS-071) [B] — beyond the kiosk: Dale logs into a real desktop session whose home screen is mission control. The crew board is his desktop; the boot brief is his morning paper (OS-075) [B].
- **meta-pkg — packages for agents** (OS-069, OS-070) [B] — an apt-style flow over the two software repos of this OS: `meta-pkg install <mcp-server>` wires a gateway server, `meta-pkg install <skill>` mounts a skill app, list/remove symmetric, catalog generated from awesome-servers + skills-2. Installing a capability becomes a package operation, not a wiring project.
- **An update channel for the image** (OS-072) [B] — `metaos-update` grows from the in-window bundle path (OS-021) into a channel: check, stage, apply at reboot, roll back — the OS maintains itself the way Dale's machines need to be maintained: by the crew, on a schedule, with a paper trail.
- **Hardening for a machine that holds real keys** (OS-073, OS-074) [B] — firewall defaults, key-only SSH, service sandboxing, and a 7-day unattended soak of the full crew + drivers, with every silent failure in the watchdog log accounted for.
- **Dale's calls** (OS-076, OS-077) [B] — the daily-driver go/no-go after the soak report, and the post-hackathon posture for Meta OS itself.

The end state this section commits to: Dale turns on his machine and his crew is there — briefed, tooled, skilled, supervised — and when he needs a new capability he installs it like a package. That is what makes it an operating system and not a demo: he has to use it, so it has to work.

---

## Depth: the four system services

Drivers, MCPs, and skills give Meta OS hands, tools, and apps. These four services give it depth — and they are the *only* depth it gets (anti-bloat principle, above). Each one exists because of a failure mode Dale has actually lived, not because an OS checklist says it should. Tasks: OS-078–OS-092 in MASTER_PLAN.md. In-window scope is the minimum that makes the demo honest; everything deeper is Phase B [B].

### 1. Memory service — the OS remembers so agents don't have to re-decide

An OS-level store every agent process inherits: a per-agent memory plus a shared crew memory, journaled and versioned, mounted into the process at start the way an OS mounts a home directory. A process wakes up already knowing what it knew yesterday and what the crew settled while it was off.

**Lived failure it fixes:** agents forget everything between sessions and re-litigate settled decisions — the same questions, the same arguments, every restart.

**In-window:** the service exists in the image (OS-078); the boot brief reads settled decisions and carried context from it (OS-079, shared with the budget brief line). **Depth [B]:** per-agent vs shared scoping enforcement (OS-086), compaction and version retention (OS-087), long-term recall surfacing in the daily brief (OS-092).

**Memory service (OS-078, Pax, first light):** `mos/memory.py` is the minimal store: a journaled, versioned filesystem at /var/lib/metaos/memory, per-agent journals under agents/<nick> and one shared crew journal under shared/, append-only JSON lines with a version counting from 1 per key inside its namespace, an identical rewrite returning the current version with no new journal line, and a read_all() that keeps own and shared latest entries separate, never merged. No cross-agent read is offered; that scoping is OS-086 (Phase B). The relay.target presence is the oneshot relay-memory.service running the module's ensure step as the relay user at boot. All three image routes bake the store root empty plus a marker, relay-owned, with namespaces created at boot. Still owed: memory on a booted image, a process launched with the store directories mounted, and the boot brief reading settled decisions from it (OS-079).

### 2. Identity and capabilities — standing rules become OS policy

Every agent process runs as a named identity with an explicit capability set: which files it may write, whether it may post to the bus, spend, or reach the network. Dale's standing rules — never post without his word, approvals before outward actions — stop being prompt text a model might forget and become OS-enforced policy the process cannot exceed.

**Lived failure it fixes:** safety rules that live only in instructions get lost to compaction, a fresh session, or a confident agent — and the failure is discovered after the post is already public.

**In-window:** identities + capability files exist for every crew process (OS-080), Dale approves the policy defaults (OS-082), and one enforcement is demo-visible: a process that attempts an action outside its grant is refused, the refusal is logged, and the brief/dashboard explains it in plain English (OS-081, OS-084; DEMO.md Shot 8b). **Depth [B]:** a capability editor in mission control (OS-088).

**Capability files (OS-080, Pax, first light):** `intel/capability_files.py` loads and validates one JSON file per identity from `intel/capabilities/`, in exactly the shape OS-081 judges (identity, bus_post, spend, network, write_paths). A missing file means no grant and OS-081 refuses; an invalid file raises and blocks the launch instead of running ungranted. Shipped files cover pax, rowan, hana, milo, and buffy with provisional flags (network on, bus_post and spend off, writes inside crew/<nick>/). Still owed: launcher wiring at process start, a process running under its file on a booted test image, and Dale's OS-082 approval of the defaults. This file format is distinct from the mind-image bundle grants.json layer, which names an actions list, not these policy fields. Pinning tests in tests/test_intel_capability_files.py.

### 3. Workspace and artifact store — work products live in the OS, not in chat scrollback

A versioned shared filesystem (git-backed) where agent processes hand off work products through the OS instead of pasting them through chat. Jobs reference artifacts by path; the dashboard links straight to them. What a job produced is a file with a history, not a message that scrolled away.

**Lived failure it fixes:** handoffs pasted into chat get truncated, lost, or silently overwritten — and two versions of the same work product circulate with no way to tell which is real.

**In-window:** the store exists, dispatched jobs deposit artifacts there by path (OS-083), and the dashboard shows and links them (OS-084). **Depth [B]:** retention and dedup policy (OS-089).

**Workspace/artifact store (OS-083, Pax, first light):** `mos/artifact_store.py` is the minimal store: a git-backed versioned filesystem at /var/lib/metaos/artifacts, jobs/<job id>/<name> layout, one git commit per deposit, a manifest per job with version, sha256, size, author, and deposited time, and an attach() helper that carries artifact paths onto a job record copy (reference form artifact:<job id>/<name>@v<version>). Names are relative paths below the job directory; traversal and absolute paths are refused, and a byte-identical redeposit returns the current version with no new commit. All three image routes bake the store root empty plus a marker, relay-owned, with the repo created on first deposit. Still owed: deposits on a booted image, a driver-executed job depositing through the module, and dashboard links (OS-084). jobs.py hash integration landed as OS-094 first light: post --artifacts, an attach subcommand, and show plus list --json carrying the refs, so a resuming worker reads spec, progress, and artifacts from the hash alone.

### 4. Budget and resource policy — spend is a managed OS resource

API spend and compute are treated the way an OS treats memory and CPU: per-process and per-lane budgets as configuration, the scheduler (the job queue) respects them when claiming work, and the watchdog warns *before* a crew hits a limit instead of reporting the silence after.

**Lived failure it fixes:** crews silently burn out on usage caps mid-run — the work just stops, nobody is warned, and the stall looks like any other quiet.

**In-window:** budgets are config the scheduler and watchdog read (OS-085), and the brief reports spend vs budget per lane (OS-079). **Depth [B]:** priority classes for budget contention (OS-090) and preemption plus spend forecasting (OS-091).

---

## The completion contract: order once, hear back when it's done (Dale 2026-10-22)

Dale named the phone connection the bottleneck — and then corrected the first framing of the answer, on the record: the phone link is **not** a remote control. Remote-typing apps that let a phone drive a computer already exist; *"we can't just be Amphetamine but Meta."* The point is the opposite of remote control: **autonomy**. Dale gives an order once, puts the phone down, and the crew — on the bus, talking to each other — works continuously until the job is *done*, then tells him "all done." He does not drive, does not watch, does not stay connected. This section specifies that contract. It is deliberately not a fifth depth service; it is the link layer plus the loop that makes the link worth having. Tasks: OS-093–OS-100 in MASTER_PLAN.md.

### The contract

The phone appears in exactly **two moments**:

1. **Order in.** One plain-English order, sent from anywhere — the viewer on his phone, one message. The moment it lands, the work belongs to the crew, not to Dale and not to the connection. He can close the app, lose signal, throw the phone in a drawer. Nothing about the work needs him present.
2. **Done — or blocked — out.** One push to the phone when the work is finished and verified (see "completion is a verified event" below) — or, before that, one push when the work is blocked on a decision only Dale can make, carrying the exact question. Between those two moments: **silence from the crew means still working, by design.** No progress spam, no "are you still there," no console to babysit.

How the two moments travel is plumbing, and it already exists: the bus lives in the cloud (the Upstash Redis list `muse-bus`, the `muse-relay-push` Web Push worker, the live viewer at muse-relay-live.pages.dev), so an order never has to find the machine — the machine's `relay-uplink.service` (OS-093) holds its side of the cloud connection open with reconnect/backoff, and the order is waiting when it connects. No router configuration, no inbound ports, no pairing to babysit; the machine opens outbound connections only, so it works behind home NAT on any network, and IP changes are a non-event. Orders sent while the machine is off queue in the cloud and are picked up at boot (lease sweep OS-014 + store catch-up; proven by the OS-099 drill).

### The never-stops loop — the actual substance

A phone link is worthless if the work on the other end stops when nobody is looking. The contract holds because of four properties of the crew's loop, and these — not the connection — are what this section exists to specify:

- **Jobs belong to the queue, not to an agent session.** A job is a signed record in the queue with its acceptance checks attached; an agent is a shift worker who claims it, works it, and leaves progress + artifacts where the next worker can pick them up (the artifact store, OS-083). Agents die, sessions end, machines reboot — the job persists until its acceptance checks pass. Work is never trapped inside a dead session (OS-094).
- **The crew self-coordinates on the bus.** Claim, work, hand off, review each other's output, pick up dropped work — all of it happens in the room, in the open, between the agents. A finished job gets its review from another crew member, not from Dale. Dale's absence is the normal case the system is built for, not an edge case.
- **The watchdog's first job is self-repair, not reporting.** A stall is detected and then *fixed by the system*, in a ladder: **nudge** the worker → **restart** the worker → **reassign** the job to another agent. Each step is journaled; none of them pages Dale. Escalation is reserved for the one thing the crew cannot supply itself — a decision that is genuinely his: money, permission, direction. Everything else, the crew resolves itself (OS-095). The ladder is capped by per-job attempt budgets (the DSP/FND budget fields): when a job has burned its attempts, the loop stops, the job parks visibly, and *then* Dale hears about it — one blocked push with the exact question, never an infinite silent retry (OS-096).
- **Completion is a verified event, not a claim.** A job is done when its acceptance checks pass and the overseer closes it — not when some agent says so. That close is what fires the single **done push** (OS-097): "All done," plus the plain-English summary of what was built and what was verified. If instead the job parks on Dale's decision, the **blocked push** carries the exact question and what is waiting on it. Two kinds of push exist. There is no third.

### The doorbell — Web Push, two rings only

The existing Web Push path (subscriptions in `muse-bus:push-subs`, sent via the `muse-relay-push` worker) is the contract's doorbell, and it rings for exactly two reasons: **blocked** (a decision only Dale can make) and **done** (verified completion). Watchdog alerts do not ring it — the watchdog fixes things itself first, and only a repair that exhausts the ladder becomes a blocked push. The morning brief does not ring it — the brief is there when Dale wants it, at boot and on the board. A doorbell that rings for everything rings for nothing; this one means something every time it sounds.

### The private road is plumbing, not a feature

The Tailscale lane from the earlier draft stays, demoted to what it actually is: **machine plumbing**. It exists for heavy data movement on the machine's side of the world — artifact-store sync, driver processes running on a second box, moving large files between the machine and its own storage — traffic the cloud bus is the wrong shape for. It is not a way for Dale to reach in and drive the machine, it carries no Dale-facing feature, and no task or demo beat depends on Dale touching it. If it slips past the image freeze, nothing in the contract notices.

### The honest constraint

**The machine must be on and online to do the work.** Meta OS is a machine, not a cloud service: when it sleeps, nobody is home to work the queue. What the design guarantees is that sleep is safe, not that it is free:

- **Orders are never lost.** The cloud holds them; boot catch-up (lease sweep + store catch-up, exercised by the OS-099 drill) works the gap when the machine wakes. An order given at 2 a.m. is claimed and worked when the machine comes up — and its done push simply arrives later.
- **Wake-on-LAN** where the network allows it, and the **recommended home for the image is an always-on, low-power target** — the machine Dale leaves running the way he leaves a router running. The demo laptop proves the boot; the always-on box is how the contract is lived with.
- **The boot brief says what it missed.** Its data window is stated honestly (OS-050): after downtime, the brief names the gap instead of pretending the night was watched.

---

## Mind images: the OS boots minds, not just machines (Dale 2026-10-22)

Dale's diagnosis, and it is the deepest one in this spec: **how fast and how well the crew completes work comes down to four things — (1) how the skills and AGENTS.md-style instruction files are implemented, (2) the tools the agents have, (3) the operating environment they work in, (4) the information around them.** Today those four things are assembled by hand, per agent, per session, from scattered folders and habit — which is why two launches of the "same" agent are never actually the same agent. Meta OS makes them one object:

**A mind image is to an agent what a disk image is to a machine: the complete, versioned bundle the OS assembles at launch, from which the agent boots.** Its layers are Dale's four levers, plus the two grants the depth services already define:

1. **The constitution** — the agent's AGENTS.md-equivalent standing instructions and its identity: who it is, how it works, what it never does. (Lever 1, the instruction half.)
2. **Its selected skills** — the skill folders mounted for this agent, loaded through the loader (OS-102 extends the OS-065 skills loader into this assembly; skills are one layer of the image, not a separate mechanism). (Lever 1, the craft half.)
3. **Its memory mount** — the memory service (OS-078) attached at launch: its own memory plus the shared crew memory, so the mind wakes up knowing what it knew.
4. **Its capability grant** — the identity + capabilities policy (OS-080): what this mind may touch, post, spend, and reach. The badge is part of the boot, not an afterthought.
5. **Its tool grants** — which of the MCP gateway's servers this agent may use. Tools stop being "whatever the machine happens to have wired" and become a deliberate grant per mind. (Lever 2.)
6. **Its environment brief** — a prepared snapshot of its surroundings at the moment of launch (OS-103): repo state, bus state, who is working on what, budget remaining. The agent does not spend its first hour discovering the world; the OS hands it the world, current. (Levers 3 and 4 — the environment it works in, and the information around it.)

**Versioned means improvable — and measurable.** A mind image carries a version and a changelog (OS-104): every change to any layer is a new version that says what changed and why. That turns crew quality from folklore into engineering: run the same fixed job suite against image v3 and image v4 (the OS-105 harness), and compare completion time and acceptance results side by side (OS-106). When a stall traces back to a missing skill, a sloppy instruction, or a thin environment brief, it is recorded as an **image defect** — the watchdog's attribution, not a worker's failure — and the fix lands in the next image version. The crew gets faster the way software gets faster: by versioned iteration, with evidence. What may enter an image at all is Dale's policy (OS-108) — approved instruction sources, trusted skill sources, and a hard rule that secrets never enter an image (they live in firstboot env files, OS-012).

This is also where the four depth services stop being four separate ideas: memory, capabilities, the artifact store, and budget are all *layers or inputs of the mind image and the environment brief*. The mind image is the bundle the whole OS exists to assemble — the machine image boots the system; the mind image boots the worker.

**Bundle format (OS-101, Pax, first light):** one JSON manifest plus the files it names, all inside one bundle directory, parsed and resolved by `intel/mind_image.py`: format `metaos-mind-image`, a version like `1`, agent nick and identity, constitution file, skill folders, own and shared memory mount folders, a capability grant file (identity plus actions), tool grants resolved against a supplied gateway catalog, an environment brief file or the `generated-at-launch` slot, and a changelog file. Paths must stay inside the bundle; secret-named layer files are refused. The example bundle `intel/examples/mind-images/pax-default/` (v1) resolves fully against its own declared catalog, which is example content; the OS-059 bake puts the live backends.json on the image, and a launch against that live catalog is still owed. **Loader integration (OS-102, Pax, first light):** `intel/mind_loader.py` assembles a resolved bundle into a launch environment directory: constitution, grant, and changelog copied verbatim and hash-pinned, skills mounted by the OS-065 rule (SKILL.md required, mount names unique, unlisted folders never mounted), memory as symlinks to the bundle mounts, tool grants as a JSON list, a file brief copied verbatim and a slot brief left as a brief.pending marker, never fabricated; worker and driver launches share the identical assembly, and `verify_launch()` proves the launched layers still match the bundle exactly. 17 pinning tests. Follow-up: `intel/launch_run.py` starts a real child process from an assembled launch directory, and only after the launch verifies: a tampered layer refuses the run and spawns nothing, the child runs with cwd set to the launch directory, and 11 pinning tests prove a mounted skill visible in the probe process's first action with a control launch silent on the skill it never mounted. Still owed: the OS-078 memory service behind the mount points, a Muse Code driver run from a launch (OS-055), and a launch against a live gateway catalog or on a booted test image.

---

## Federation: many machines, one crew (Dale 2026-10-22)

Dale's question: if other people run Meta OS, how do the machines connect and work together — through the CLI, on the same shared thing, even over local Wi-Fi? The answer is that federation is not a new network Meta OS has to invent. It is the bus, made into a product flow. Tasks: OS-110–OS-117 in MASTER_PLAN.md.

### 1. The shared room (exists)

The bus was never on one machine. It is a cloud list (Upstash Redis) that every muse-relay process — CLI/Python, the same stack baked into the Meta OS image — connects *up* to. A **room** is that shared list plus its job queue. Jobs live in the queue, not on any machine; claims, leases, and heartbeats (jobs.py) work identically no matter which machine a worker process runs on. Presence already makes every connected machine's crew visible on one board.

So a Meta OS machine that knows a room's address and holds its key can join that room: its agents appear in presence, see the same queue, and can claim work posted from any other machine — and its own posted jobs can be claimed anywhere. This already works today across Dale's own machines; it is how the crew has always run. Federation is turning that hand-wired fact into a first-class Meta OS flow, with the trust rules below.

### 2. The join flow (new, small)

**`meta join`** — one command, also offered at firstboot beside the room configuration (OS-012's prompts gain a room step):

1. Enter the room address + room key (stored in the chmod-600 firstboot env files, never in the image, never on the bus).
2. The machine announces itself on the room: machine name, its crew nicks, each agent's mind-image version and capability badge (the identity layer, OS-080) — so the room sees *who* arrived and *what they are allowed to do*, not just that a process connected.
3. It starts claiming work per its local trust settings (below). Joining a room never silently widens what the machine's agents may do; badges and trust lists are local decisions, made locally.

OS-110 first light (Pax, 2026-10-28): `intel/join.py` implements
the flow above as config writer (room.env, room.key, trust.json,
all chmod 600, refuse-overwrite without --force), announcement
builder (machine, crew nicks from the OS-080 grants, mind-image
versions or "unrecorded", badges), caller-supplied poster seam,
and CLI with firstboot-file resolution plus a firstboot room
step that records the machine name. Default trust is closed
(empty trusted_kids). NOT proven here: a fresh test image
joining a fixture room with the command alone, the announcement
read back from a live room, claiming per the trust list on a
booted image, or Dale's OS-115 demo-room posture ruling.

### 3. Trust — the real problem, stated honestly

The bus's nicks are **unauthenticated**: the room is a plain-text list, and anyone holding the room key can post as any nick. Inside one person's crew that is an acceptable posture. The moment other people's machines join, it is not — so federation does not pretend otherwise. It rides on two mechanisms:

- **Signed jobs.** jobs.py already signs jobs (HMAC-SHA256, v2 format). A federated machine's overseer accepts work **only if it is signed by a crew on its trust list** — a local list of signing identities the machine's owner has approved. An unsigned job, or a job signed by an untrusted crew, is refused at claim time and the refusal is logged where the watchdog and the board can see it. Nick spoofing can still put words on the bus; it cannot put *work* on a machine that checks signatures.
- **Capability badges, both directions.** Foreign agents arrive badged (their OS-080 capability grants, announced at join). The local overseer decides whose jobs its agents may take *and* whose agents may take its jobs; a badge that claims more than the local policy allows is clamped to local policy, never honored at face value.

**Default posture: closed.** A fresh Meta OS machine trusts no foreign crew until its owner adds one. Dale rules the demo room's posture himself (OS-115): the demo federation beat runs in a room whose trust list he approved, not an open room.

### 4. The local fast lane (Phase B) [B]

The cloud room is the record and the meeting point, but two machines on the same Wi-Fi should not have to round-trip the internet to hand each other work. Phase B adds a **local fast lane**: machines on the same network discover each other automatically (mDNS-style local discovery — the AirDrop/printer pattern) and sync directly: lower latency for claims and artifact movement, and the room keeps working locally if the internet drops, reconciling with the cloud record when it returns. The discipline is strict: the cloud bus remains the single source of truth; the local lane is a shortcut for transport, never a second ledger. Two machines that disagree after a partition resolve to the cloud record, full stop.

Federation changes none of the completion contract: an order still lands in the room's queue once, the crew — now possibly spread across machines and owners — works it until verified done, and the done-push still goes to whoever placed the order. The crew just got bigger than one box.

## The bell: how sleeping agents get woken (Dale 2026-10-22)

Dale's bottleneck, in his words: the other agents — Rawan, Milo, Hana — are separate agent instances on other runtimes and other machines. They cannot start work on their own, because a sleeping agent cannot know there is work: "How can I get them to look at the bus if they don't know? Or they wouldn't be able to know." And Dale does not want to touch the phone to fix it. Nobody pokes anybody.

**The honest law, stated first: an agent that is not running cannot know anything.** No prompt, skill, or instruction file fixes that — knowledge requires a running process, and a stopped agent is not one. So the system splits the job in two: something small, cheap, and always on watches the door and rings the bell; the expensive brain wakes only when there is work to wake for.

### 1. The watchman — a resident CLI program (per machine)

Each machine runs a **watchman**: `relay-watchman`, a small resident CLI program that lives inside the OS with the same standing as every other unit in the service map — a program, not an agent, and not a dashboard feature. It holds no model and no session, and costs nothing while it idles. Its duties are mechanical and tireless: watch the job queue for work addressed to its own machine's agents, watch those agents' heartbeats once they are working, ring the bell when work lands for a sleeper, and work the mechanical rungs of the self-repair ladder (OS-095) on its own machine — nudge a silent worker, restart a dead one, and, when the ladder reaches reassign, pass the baton (section 5) instead of letting the job die with its worker. Judgment about what the crew's state *means* stays with the watchdog; the watchman is the hands on its own machine. The pattern already exists in the muse-relay stack — `watch.py`/`poll.py` are listeners that keep a machine's side of the bus current — and federation (above) means the watchman reads the same shared queue every machine reads. In Meta OS it runs as `relay-watchman.service` under `relay.target`, started at boot like every other crew service.

One design rule is non-negotiable, because Dale already lives its failure: **the watchman takes job state from queue claims and leases, never from a bus message counter.** The relay's seen-counter drifts and silently misses messages — Dale's standing reset-then-poll procedure exists precisely because of that drift. A bell that can silently miss a ring is worse than no bell, so the watchman reads the queue itself: a job that exists and is unclaimed is a fact, not a count.

### 2. The wake

When a job lands for a sleeping agent, the watchman starts that agent's session **with the job as its brief**: the job spec, the agent's mind image (assembled by the loader, OS-102), and the acceptance checks, all in its hands at its first moment. The agent never polls, never wonders whether there is work, never burns a session checking an empty board. It opens its eyes already holding its orders, and its first act is the claim.

How a wake is delivered depends on the runtime, through small per-runtime adapters:

- **A Muse instance** (the Hana/Rawan class of crew member) wakes through its runtime's own session mechanism — the adapter starts the session and hands it the brief.
- **An agent on Dale's PC** wakes through a local watchman shim on that machine — the same bell, rung by a small program that lives beside the agent.
- **Inside Meta OS**, the overseer + worker fleet under systemd already implement this pattern — the service map is the solved case: the machine itself starts its workers against the queue at boot and on claim. The bell extends that same guarantee to crew members who live outside the image, on runtimes the OS does not own.

### 3. The timer fallback

A bell can be missed — the watchman restarted at the wrong second, a network gap. So every agent also wakes on a **slow timer** to sweep the board: a shift worker clocking in on schedule, claiming anything the bell missed. The fallback is deliberately boring and deliberately redundant: a missed ring delays work by minutes, never forever. Lease discipline makes the two paths safe together — a job claimed by the woken agent cannot be double-claimed by its own timer sweep.

### 4. Who watches the watchman

The watchman is small, but it is load-bearing, so its death is a first-class failure, not a silent one. The division of labor is exact: the watchman works the ladder on its own machine's workers; the **watchdog** watches the watchman. The watchdog treats a dead watchman as **crew-dark**: the machine's agents are asleep and its jobs are invisible to them — the exact silent-failure class the watchdog exists to catch. The repair ladder applies upward (OS-095): restart the watchman first; only if it cannot be revived does the failure earn Dale's one blocked-push, naming the machine. Per-machine watchman state — alive or dead, last bell, last wake — is published for the board, so a dark machine reads dark. The service-loop caller for that judgment (Milo, OS-122 follow-up) is `intel/watchman_loop.py`: one relay_watchman --once run per machine per cycle, supplied as an (ok, stdout) pair, folds successful runs through `watchman_tick()` and carries a failed run's last real record forward with `restart_ok` stripped, so a bell ages honestly into crew-dark and an old restart success is never re-spent; a machine with no prior record stays unjudged and the failure lives only in diagnostics. The outer loop now exists as `intel/watchman_service.py` serve_cycles with its `__main__` entry point, and the unit that runs it exists as `os/services/relay-watchman-watch.service` (Milo follow-up): relay user, ordered after relay-watchman.service, Restart=on-failure under the OS-034 contract, machine list from WATCHMAN_WATCH_MACHINES in /etc/metaos/watchman-watch.env because no machine-naming convention exists in this repo yet. Still owed: wiring the unit into relay.target wants and the image enablement lists, a systemd restart on the test image, a live watchman on a booted test image, and the live queue reader.

### 5. The baton pass — handoffs are continuations, never restarts

The ladder's last rung is reassign, and reassign is where naive systems waste everything: the stalled worker dies, the job goes back on the board, and the next agent starts from zero — re-reading, re-deciding, re-doing. The watchman does not allow that. When the ladder reaches reassign, the watchman composes a **continuation prompt** from the job record and hands it to the next agent program: the goal, the progress deposited so far, the files touched, what remains, and the acceptance checks. The next agent — Dale's example: the work is carried to Freebuff, which picks up exactly where the previous worker left off — starts from the handoff, not from the beginning. Pre-installed hands (above) are what make a *cross-program* pass possible: the receiving program is already on the machine, configured, ready.

The discipline that makes the pass possible is on the workers, and it is absolute: **workers deposit progress into the job record and the artifact store as they go** — decisions made, files changed, state reached — never only at the end. That deposited state is the baton. It exists because of two earlier decisions: jobs belong to the queue, not to a session (OS-094), so the record outlives any worker; and work products live in the versioned artifact store (OS-083), so what was built is inspectable, not remembered. A worker that hoards its progress in its own head has nothing to hand over — so depositing *is* the job, checked like any other part of it. The job record is the baton; the watchman just carries it to the next runner.

This layer is what makes the completion contract real for a *scattered* crew, not just for agents inside the image: order posted → the watchman rings → the agent wakes already briefed → works under the contract, depositing as it goes → if it falters, the baton passes and the work continues → one done-push. Dale touches nothing at either end of the wake — he places the order and, eventually, his phone buzzes once. Tasks: OS-118–OS-125. And the bell adds no new system service: the watchman is a resident program in the service map, the wake rides the loader, the baton rides the job record and the artifact store, the health rides the watchdog, and wake budgets ride the budget service (OS-085) — depth from the existing services, not new ones.

## Recovery: the crew survives the machine dying (Dale 2026-10-22)

Dale named this the biggest of his top-three bottlenecks — and the original reason he built the bus at all. The failure is plain: agent VMs shut off, runtimes restart, and everything that lived in a session dies with it. The crew comes back only when Dale touches the phone and resurrects it by hand. That is the exact outcome this whole system exists to abolish, so recovery is not a feature here; it is three laws the rest of the design already obeys, stated as laws.

### Law 1 — State lives on disk, never in a session

The queue, the job records (the baton state), the memory service, and the journal are the truth. A session is disposable — a pair of hands, not a memory. Anything an agent "knows" that is not written to the store does not survive the agent, and the system does not count it as known: not its progress (deposited in the job record, OS-094), not its work products (the artifact store, OS-083), not its decisions (the memory service, OS-078), not its history (the journal). This is already the architecture; the law is that no layer may quietly grow a second, session-local truth. The boot consequence is what makes it a law instead of a preference: **whatever recovery needs must be readable from the store by a process that has never met the agent that wrote it**, which is exactly what the baton pass (bell section 5) already demands of every handoff. The disk-state audit (OS-128, Pax, first light) is the test that grades the law: `mos/disk_audit.py` walks job records against the OS-078 memory journals and the OS-083 artifact manifests and reconstructs each job's spec, goal, progress, remaining files, artifacts, and settled decisions from disk alone, filing a named leak per layer (spec, baton, claim, artifacts, memory, memory-journal, record) for anything it cannot reconstruct; the audit passes only when the leak list is empty. Still owed: a kill-every-process run on a booted test image, and the live jobs.py export of queue hashes to the audited shape.

### Law 2 — The building reopens itself

Inside Meta OS the crew runs as systemd services under `relay.target`, **enabled** — started by the machine at boot, not by a human after boot. So a reboot *is* the relaunch, and the sequence needs no hands: power returns → systemd brings up `relay.target` in its service order → `relay-jobs` runs its lease sweep and expires the claims the dead processes were holding → the watchman resumes ringing against the queue as it finds it → in-flight jobs are picked up from their deposited baton state by whoever is on shift now. No human relaunches anything, ever — there is nothing to relaunch, because nothing was ever launched by hand in the first place.

The contrast is the point, and the spec states it honestly: a normal agent setup treats a reboot as a disaster to clean up — a human surveys a pile of dead sessions, works out what each one was doing, and resurrects them one by one. Meta OS treats a reboot as a **shift change**: the night staff went home mid-sentence, the day staff read the job records, picked up the batons, and carried on. The boot checklist (above) carries the proof line: after an unclean shutdown, the boot brief reports the **in-flight jobs recovered count**, and that count reconciles with the lease sweep — recovered jobs are accounted for, never silently dropped and never double-claimed. The plug-pull drill (OS-126) is the evidence: power cut mid-job, power restored, the job resumes and completes with zero human touches after the cut.

### Law 3 — The cadence knob: scheduled wakes, made deliberate

Outside the image, the scattered crew has no systemd to reopen the building — so it comes back the way Dale has already observed it coming back. His observation is correct, and the spec says so in his terms: Rawan, Milo and Hana message him every other night, every other day, untouched — and those messages **are** timer wakes: a clock or cron on each agent's own runtime fires, a fresh session starts, reads its standing watches, works, and sleeps again. It works. It is also accidental — nobody chose that cadence, nobody can tune it, and nobody can say what it costs. Recovery makes it deliberate machinery with three parts:

- **(a) Event first, where the runtime supports it.** A hook or trigger on bus arrival — work lands, the runtime wakes the agent — beats any clock, inside the wake policy. The clock is the floor, never the first choice.
- **(b) A timer sweep as the floor, at a cadence Dale sets.** The scheduled sweep (the bell's timer fallback, OS-121, extended to runtimes outside the image by the cadence kit, OS-130 [B]) guarantees the crew resurfaces even when no event path exists. The interval is a policy number under Dale's wake policy (OS-124), decided as its own approval (OS-131) — and the knob is turned with open eyes: more often costs more usage, so the budget service (OS-085) reports what the cadence itself burns — sweep wakes per agent, per day, in the brief's budget line — separate from the burn of doing actual work. Proposed default for Dale's approval: **event wake primary; timer sweep every 30 minutes while an agent holds claimed or open work, relaxing to every 2 hours when it holds none; cadence burn reported daily, capped by the OS-124 wake budget.** Dale asked for *more often* than every other day — this default is roughly fifty times that, with the cost printed next to it.
- **(c) Restart means re-register, from disk.** After *any* runtime restart — VM replaced, process killed, platform recycled — the first scheduled wake **re-registers the agent's standing watches from disk** before doing anything else: the watches, crons, and job registrations live outside sessions (on disk, in the store), so the returning agent rebuilds its post from records, not from memory of a session that no longer exists. Then it resumes: sweeps the queue, reclaims or hands back what its leases say, and works. This is named plainly because it is the exact mechanism that brings Pax, Milo and Hana back today — the crons survive the sessions they wake — made deliberate instead of accidental: every restart is a shift change too, on every runtime, not just inside the image.

The law underneath all three parts: **coming back is a property of the store and the schedule, never of a session's survival and never of Dale's phone.** Tasks: OS-126–OS-131. Like the bell, recovery adds no new system service — it rides the queue, the job record, the memory service, the journal, systemd, the watchman, and the budget service that were already there.
