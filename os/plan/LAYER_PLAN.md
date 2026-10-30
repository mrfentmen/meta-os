# Meta OS — Layer Plan

_Written 2026-10-24 at Del's order ("start writing down the layer plans for this... heavily detailed on everything that we're doing"). This document is the layer-by-layer build plan for Meta OS: what each layer is, what goes in it, what it depends on, and how it is verified. It sits under MASTER_PLAN.md (task list) and META_OS.md (spec); where they disagree, MASTER_PLAN.md wins until the plan is amended._

## Rulings baked into this plan (Del, 2026-10-24)

1. **New repo.** The build does NOT happen in the muse-relay repo. A new repo is created, muse-relay is merged into it as the base, and all work happens in the new repo: relay at the bottom, Meta OS built on top of it there. (GOV-003, ruled)
2. **Bus untouched.** The live muse-relay bus does not get touched — except a fix it needs, or an upgrade needed because the OS is being built on it. (GOV-002, ruled)
3. **The $150 credit key is saved, not burned.** Day-to-day build work does not run on the hackathon credit key. If the key is used at all: at most half ($75) for build/testing, the other half ($75) reserved for the presentation and the final "does the OS actually work" verification. (GOV-001, ruled and refined)
4. **Roster confirmed.** Pax coordinates and integrates; Rowan: dashboard; Hana: briefings; Milo: watchdog + audio; Buffy: volume/docs. Every crew member has their own Buffy (Freebuff) and their own OpenCode — each agent uses their own OpenCode, their own agents, and their own Buffys. (GOV-004, ruled)
5. **Demo hardware.** The demo hardware is called **Meta OS**. (OS-002, ruled in Del's words)

## The stack at a glance

Meta OS is a stack of ten layers. Each layer only talks to the layer under it. Nothing skips a layer.

| Layer | Name | What it is |
|---|---|---|
| L0 | Hardware | The physical machines the OS runs on |
| L1 | Boot | Firmware, GRUB, splash — power button to kernel |
| L2 | Kernel | The stock Debian Linux kernel — never modified, never custom |
| L3 | Base system | Debian 12, users, packages, firstboot secrets |
| L4 | Supervision | systemd, `relay.target`, slices, journald |
| L5 | Relay core | The bus, the job queue, the overseer, the worker fleet (merged from muse-relay) |
| L6 | OS system services | The four depth services: memory, identity/capabilities, workspace store, budget |
| L7 | Platform services | MCP gateway daemon, watchdog, watchman (the bell), brief service, dashboard, uplink/push |
| L8 | The mind | Relay Intelligence: the Muse Spark layer — briefings, dispatch, acceptance — launched from mind images, bound by the completion contract |
| L9 | Hands and apps | Agent drivers (coding agents as managed processes) and skills (installable applications) |

One line version: **the kernel is Linux, the system libraries are MCPs, the processes are agents, the applications are skills.**

---

## L0 — Hardware

**What runs Meta OS:**

- **Primary target: the demo laptop, called Meta OS.** Bare metal. The primary disk image is installed on it and the demo's cold boot (DEMO.md Shot 0) is performed on this machine. One artifact, no special build for it.
- **Secondary target: a VM on Del's own PC.** The identical `.img` attached to a QEMU / VMware / VirtualBox virtual machine. Used for rehearsals, for testing without touching the demo laptop, and as the snapshot-restore fallback on demo day.
- **Field target: any spare amd64 PC or laptop** that can boot from USB, using the live-build ISO fallback. This is the emergency path: if the demo laptop dies, any 64-bit machine becomes a Meta OS machine from a USB stick.
- **Phase B target [post-hackathon]: an always-on, low-power box** on Del's network — the machine that stays up like a router so the completion contract is lived with daily. Not demo scope.

**Hardware requirements (any target):** amd64/x86-64 CPU, enough RAM for the worker fleet under its cgroup caps (limits tuned in L4), one disk or USB device the image can be written to, network access (the bus and Spark are reached over the internet; the machine makes outbound connections only — no router configuration, no inbound ports).

**What L0 does NOT include:** no custom hardware, no second machine requirement for the demo. Federation (many machines, one crew) is a capability of L5/L7, not a hardware dependency; Del names any second machine separately if he wants that demo beat.

## L1 — Boot

**Job:** power button → kernel, with zero human input and zero stock branding on the path.

- Firmware (UEFI/BIOS) → **GRUB** → kernel. One normal entry, plus one **rescue entry** that boots the base system *without* `relay.target` (for a machine whose crew services are broken but whose OS is fine).
- **Plymouth splash** carries the Meta OS identity from the first frame. No Debian branding on the boot path.
- No prompts, no clicks, no login typing: the graphical session autologins as the `relay` user.
- **Verification:** boot test checklist items 1–3 (unattended boot, boot budget ≤ 90 seconds power-on → dashboard-ready on the demo hardware, measured across three boots).

## L2 — Kernel

**The kernel is the stock Debian 12 kernel. Full stop.**

- We do not build a kernel, patch a kernel, or configure a custom kernel. "Kernel level" for Meta OS means the OS is a real bootable system built on the Linux kernel — take root Linux and rebuild the system on it for Meta agents. All copy says exactly this: *"a Linux-based operating system rebuilt for Meta agents."*
- The kernel's job in the stack: hardware drivers, process isolation, cgroup resource control (which L4 uses to cap each agent), namespaces, networking. Everything the upper layers need from a kernel, the stock kernel already does.
- Kernel updates ride the frozen base: during the build window the base does not update through the OS update path, so the demo machine cannot drift.
- **How Del "runs the kernel": he doesn't, separately.** The kernel is inside the image. Turning the machine on runs it. There is no kernel step in any instructions for Del — see "How Del runs Meta OS" below.

## L3 — Base system

**Job:** a lean, pinned, reproducible Debian the rest of the stack can trust.

- **Debian 12 (bookworm), amd64, one base only.** Rejected and not revisited: Ubuntu (snap stack fights the appliance model), Alpine (musl + OpenRC re-solves supervision systemd gives free), Arch (a moving base under a frozen demo).
- **Package set:** netinst-derived, pinned in `os/packages.txt`. Lean on purpose — appliance, not desktop (the desktop session is Phase B).
- **Users:** a single `relay` user, autologin, UTC + en_US, one partition + swapfile, all set by `os/preseed.cfg` at image build time — there is no installer wizard for Del to click through, ever.
- **Secrets: none in the image.** The image ships with zero credential material, enforced by an automated secrets sweep in the build pipeline. **First boot** generates the local job-signing keyring (chmod 600) and prompts exactly once for the two secrets the system needs — the Muse Spark key and the Upstash bus token — stored in env files, chmod 600, never on the bus, never in a commit.
- **Version stamp:** `/etc/metaos-version`, shown on screen; what the screen says and what the file says must match (boot checklist item 12).
- **Verification:** secrets sweep (checklist item 11), reproducibility rule — a build that cannot name its pinned base, pinned packages, and pinned repo commit is not a Meta OS build.

## L4 — Supervision (systemd)

**Job:** the machine supervises the crew the way an OS supervises processes — because that is literally what happens.

- All crew services are **systemd units grouped under `relay.target`**. Enabling the target is what makes a reboot a relaunch: state on disk + services enabled = the building reopens itself.
- **The supervision contract (the split that matters):**
  - **systemd owns process death.** A crashed worker is restarted by the machine (`Restart=on-failure`). Nobody pages a human for a crash.
  - **The watchdog (L7) owns silent-but-alive failure.** A worker that lives but stopped progressing — stale heartbeat, rotting lease — is a watchdog case. systemd is never told to fight it.
- **Resource limits:** worker instances live in a `relay-workers.slice`, driver processes in a `relay-drivers.slice`, each with `MemoryMax` / `CPUQuota`. One runaway agent gets throttled or OOM-killed by its cgroup while the bus, queue, and dashboard stay responsive.
- **Journaling:** journald carries every unit's output, restarts, and cgroup events. `journalctl -u 'relay-*'` is the machine's own account of itself; the watchdog reads the journal and turns unit failures into alerts in the same store the dashboard reads.
- **Ready gate:** a oneshot unit verifies every crew unit is active and writes `/run/metaos/ready`. The boot checklist on the dashboard flips from these real states — if a unit is down, its line is red, on screen, honestly.
- **Verification:** boot checklist items 2, 4, 9 (target reached; killing a unit turns its line red; kill -9 → restart + logged, SIGSTOP → stall alert, no restart fight).

## L5 — Relay core (the base merged into the new repo)

**Job:** the existing, production muse-relay machinery — imported unchanged as the foundation, per ruling 1 and ruling 2.

- **What comes in from muse-relay:** the bus client stack (presence renewal, watch/poll listeners, local JSONL store), `jobs.py` (the queue: atomic claims, 30-minute leases, HMAC-SHA256 signed jobs), `mos/overseer.py` (dispatch + acceptance), `mos/worker.py` (per-nick claim/work loop), `mos/acceptance.py` (verification), the live viewer (`bus.html` / `index.html`).
- **As systemd units (L4 runs them):** `relay-bus`, `relay-jobs` (lease sweep on start, so dead claims are cleaned before anyone looks), `relay-overseer`, `relay-worker@<nick>` (one instance per crew nick).
- **The bus rule in force (ruling 2):** the live cloud bus (Upstash) is the room and the source of truth, and it is not modified by the build — fixes and OS-required upgrades only, on Del's word. Build traffic follows the same discipline as always: never post to the bus without Del's explicit word.
- **Trust, stated honestly:** bus nicks are unauthenticated — anyone can post as any nick. The system's answer is at this layer: signed jobs (HMAC v2) so work orders are verifiable even though names are not, plus the identity service in L6. Default federation posture is CLOSED.
- **Verification:** the repo's existing test baseline (326 test methods at plan time) must stay green in the new repo; a job posted before shutdown is claimable after boot (checklist item 8).

## L6 — The four OS system services (the depth layer)

**Rule (Del's, binding): exactly four.** A new OS subsystem requires Del's decision, a lived failure it fixes, and a task ID. Applications belong in skills (L9), not here.

### 6.1 Memory service
- **What:** an OS-level store every agent process inherits — per-agent memory + shared crew memory, journaled and versioned, mounted into the process at launch like a home directory. An agent wakes up knowing what it knew yesterday and what the crew settled while it was off.
- **Fixes:** agents forgetting everything between sessions and re-litigating settled decisions every restart.
- **In-window:** the service exists in the image; the boot brief reads settled decisions and carried context from it. Deeper scoping/compaction is Phase B.

### 6.2 Identity and capabilities
- **What:** every agent process runs as a named identity with an explicit capability grant: which files it may write, whether it may post to the bus, spend, or reach the network. Del's standing rules stop being prompt text and become OS-enforced policy.
- **Fixes:** rules that live only in instructions get lost to compaction or a fresh session — discovered after the post is already public.
- **In-window:** identity + capability files for every crew process, policy defaults approved by Del, and one demo-visible enforcement (DEMO.md Shot 8b, "The OS says no"): a process that tries an action outside its grant is refused, the refusal is logged, and the dashboard explains it in plain English.

### 6.3 Workspace and artifact store
- **What:** a versioned, git-backed shared filesystem where jobs deposit work products. Jobs reference artifacts by path; the dashboard links straight to them. A work product is a file with history, not a chat message that scrolled away.
- **Fixes:** handoffs pasted into chat getting truncated, lost, or silently overwritten, with two versions circulating and no way to tell which is real.

### 6.4 Budget and resource policy
- **What:** API spend and compute treated as OS resources: per-process and per-lane budgets as configuration, the queue respects them when claiming work, and the watchdog warns *before* a lane hits its limit.
- **Fixes:** crews silently burning out on usage caps mid-run — the work just stops and the stall looks like any other quiet.
- **The credit rule lives here (ruling 3):** the budget service is what enforces the $150 key discipline — the credit key is reserved, its build/testing draw is capped at half, and the presentation half is not spendable by build work. The brief reports spend vs budget per lane.

## L7 — Platform services

**Job:** the always-on machinery that makes the crew reachable, observable, and wakeable.

- **MCP gateway daemon (`relay-mcp-gateway.service`).** Del's MCP gateway ships in the image as a system service, baked at a pinned state beside `/opt/relay`. Every agent process — crew workers and driven coding agents alike — reaches the whole tool estate (the 869-server collection and the rest of his wired servers) through the gateway's one local endpoint. MCP servers are this OS's system libraries: no process reimplements tool access. Gateway secrets follow the image rule: none baked, firstboot env only.
- **Watchdog (`relay-watchdog.service`).** The intel watchdog loop + its own heartbeat. Detects silent failure (stale heartbeats, rotting leases, wedged drivers), reads the journal for unit failures, and works the self-repair ladder first — nudge → restart → reassign — escalating only genuine Del decisions (money, permission, direction). Attempt budgets cap the ladder so nothing loops forever.
- **The watchman — the bell (`relay-watchman.service`).** A small resident program, deliberately NOT an agent. It watches the *queue* (claims and leases are the truth — never the drifting message counter) and rings sleeping agents awake **with the job as their brief**. On a reassignment it performs the **baton pass**: it composes a continuation prompt from the job record (progress the last worker deposited) so the next program continues the work instead of restarting it — proven by drill: zero duplicated file changes when a job moves from one program to another.
- **Brief service (`relay-brief.service`, oneshot).** Generates the boot brief: previous-session digest, carried-over jobs, overnight decisions, what the watchdog saw — with its data window stated honestly. On screen within 60 seconds of the ready gate; if Spark is unreachable, the template fallback brief appears and labels itself.
- **Dashboard (`relay-dashboard.service`).** The live viewer + crew board, served locally, Chromium kiosk full screen: boot checklist, bus, queue state, jobs and their shift workers, parked jobs waiting on Del, watchdog status line, artifact links. Renders locally even with the network unplugged; Spark features degrade to their labeled fallbacks.
- **Uplink + doorbell.** The machine holds its side of the cloud bus connection open (outbound only, reconnect/backoff). Web Push is the doorbell and it rings for exactly two reasons: **done** (verified completion) and **blocked** (a decision only Del can make). Nothing else pushes. Tailscale, if used at all, is machine plumbing for heavy data movement — not a Del-facing feature, nothing depends on Del touching it.

## L8 — The mind (Relay Intelligence, the Muse Spark layer)

**Job:** the intelligence the OS exists to run. Meta OS is the machine; Relay Intelligence is the mind inside it.

- **Briefings:** plain-English summaries of crew state, generated from the bus/queue record — the boot brief and the on-demand brief read from the same engines.
- **Dispatch:** a plain-English order from Del becomes signed jobs in the L5 queue, with files owned, acceptance checks, and attempt budgets attached. Dispatch writes jobs; it does not babysit them.
- **Acceptance:** completion is a verified event, not a claim. A job is done when its acceptance checks pass and the overseer closes it. That close is the only thing that fires the done push.
- **Mind images — how every agent in L9 starts.** Each agent launches from one versioned bundle: constitution + skills + memory mount (L6.1) + capability grant (L6.2) + MCP tool grants (L7 gateway) + environment brief. Versioned means improvable and measurable: the A/B harness runs the same job suite against a bare agent vs a mind-image agent and reports the difference. "Same agent. Different upbringing."
- **The completion contract binds this layer:** Del orders ONCE in plain English; the crew self-coordinates on the bus and works until verified done; then ONE push — "All done" + the verified summary. Silence means still working. Jobs belong to the queue, never to a session. The watchdog self-repairs first; only money, permission, or direction questions ever reach Del.
- **Spark access discipline (ruling 3):** this layer is the credit key's only consumer, and it treats the key as reserved funds: day-to-day build work does not run on it (the build runs on the crew's own access — each agent's own OpenCode/Buffy per ruling 4); the key's testing half is capped at $75; the presentation half ($75) is untouchable until demo verification and the presentation itself. (Which endpoint the Spark layer points at for the demo is set when the key is attached at firstboot — L3.)

## L9 — Hands and apps

**Job:** the work gets done by real coding agents, driven as managed processes, carrying loaded skills.

### Agent drivers — coding agents are devices of the OS
A Meta agent does not shell out to a coding agent and hope. It drives it through an **agent-driver adapter** — one contract every driver implements:

- **start(job_spec)** — launch the agent process against a signed job spec.
- **stop()** — clean termination; a wedged process is killed by the supervisor, never by hand.
- **heartbeat()** — progress heartbeats in the bus progress format, so the watchdog's existing stall detectors work on driver processes with zero new detector code.
- **artifacts + status out** — on exit, the changed-file list, logs, and a status record the acceptance layer verifies exactly as it verifies a crew worker's job.

Driver processes are first-class: systemd units in `relay-drivers.slice`, same supervision contract, same cgroup limits, everything in journald and the bus record.

**Driver order:** Muse (Meta's own — first, in-window; a Spark-dispatched job executed by Muse as a managed process is the demo proof) → OpenCode (Phase B per the original roadmap) → Freebuff/GLM (Phase B). **Per ruling 4, the crew's own working setup is already this:** every crew member has their own OpenCode and their own Buffy and uses them for their lane work during the build.

**Pre-installed hands:** the image bake installs and configures the crew's agent CLIs — Muse, OpenCode, Freebuff, plus a node-based agent slot — before any job exists. Nothing is installed mid-job; a driver never waits on a download; the baton pass can hand work to a different program precisely because that program is already on the machine, configured, pointed at the gateway's one endpoint, and launched through the loader so it starts from a mind image. A tool that cannot be redistributed under its license is fetched at firstboot or left as a documented slot — never bundled against its license.

### Skills as applications
Del's skill collections (skills-2 — 206 skills — and the rest of his trees) are **installable OS applications**. The skills loader mounts skill folders into an agent process's launch environment: a process started on Meta OS begins with its persona, craft, and judgment already loaded — not pasted in by hand mid-session. Phase B grows this into `meta-pkg`: installing a capability (an MCP server, a skill) becomes a package operation.

---

## Cross-cutting: federation

Many machines, one crew. Any Meta OS box with the room's address + key joins the same bus room and the same queue via `meta join` at firstboot. Agents on any connected machine can claim work posted from any other. Trust is the honest weak point and is handled at L5/L6: signed jobs + capability badges, default posture CLOSED. The second-machine demo beat exists only if Del names a second machine and rules the federation policy — otherwise federation ships as capability, not demo.

## Cross-cutting: recovery — the crew survives the machine dying

Three laws, enforced by L3/L4/L5 together:

1. **State lives on disk, never in a session.** Job records, baton state, memory store, artifact store — all files. A session is a shift, not a life.
2. **The building reopens itself.** Services are enabled under systemd; a reboot is a shift change: lease sweep, watchman resumes, in-flight jobs picked up from their deposited baton state. Proven by the plug-pull drill before freeze: job in flight, power cut, crew reforms and finishes, one done push, zero human touches.
3. **The cadence knob.** Outside the image, scheduled wakes are deliberate: event wake primary, a timer sweep as the floor while holding work, slower when idle — each agent's burn printed per day and capped by its wake budget (L6.4 enforces). Every restart re-registers an agent's standing watches from disk.

## The build pipeline (how the image is made)

One command from a clean checkout of the **new repo** produces `metaos-<date>.img` + `.sha256`:

1. **Packer + QEMU** boots the pinned Debian 12 netinst image (source + checksum recorded in `os/BASE.md`).
2. **`os/preseed.cfg`** answers every installer prompt: single `relay` user, autologin, UTC + en_US, one partition + swapfile. Zero interactive steps.
3. **Provisioning, in order:** pinned packages (`os/packages.txt`) → bake the stack (the new repo's relay + intel code at a pinned commit to `/opt/relay`, venv built) → bake the MCP gateway at a pinned state → install the pre-installed agent CLIs (L9) → install Meta OS identity assets → install the units from `os/services/` and enable `relay.target` → stamp `/etc/metaos-version` → **secrets sweep** (the build fails if any credential material is in the image).
4. **The disk image is the artifact.** Written to the demo laptop's disk or attached to a VM, unchanged — one artifact, both targets.
5. **Fallback kept buildable from Day 2:** a live-build ISO of the same package and service set (the field-kit USB). Divergences documented in `os/BASE.md`; the demo never depends on a fallback-only behavior.
6. **Reproducibility:** pinned base, pinned packages, pinned repo commit, archived builds with checksums and logs, a changelog per image. A build that cannot name all three pins is not a Meta OS build.

**Freezes:** image content freeze **Nov 2, 12:00 ET**; feature freeze Nov 2, 21:00; demo freeze Nov 3, 21:00. **OS go/no-go: Nov 1, 12:00 ET — Del's call, default NO-GO** if the cold boot is not boring-reliable. If no-go: the demo opens on the dashboard as originally scripted and Meta OS presents as the deployment target with the boot video as a supporting asset. The Spark layer ships either way — the chassis never takes the cargo down with it.

**Updates after install:** `metaos-update` pulls a verified git bundle of relay + intel updates, applies it to `/opt/relay`, restarts `relay.target`; rollback is re-applying the previous bundle. Base OS packages do not update through this path during the build window.

---

## How Del runs Meta OS (the direct answer)

### How do I run the kernel?
You don't — not as a step. The kernel is inside the image, the same way the kernel is inside your phone. **You turn the machine on, the kernel boots, systemd starts the crew, the dashboard comes up.** There is no kernel command, no kernel screen, nothing for you to launch or manage. If anyone ever has to "run the kernel" manually, the build failed, not you.

### Where can I run it?
Four places, in the order you'll actually use them:

1. **The demo laptop (called Meta OS) — the real one.** The image is written to its disk once. After that: power button. It boots unattended into the crew and the dashboard, full screen. This is the machine the demo's cold boot happens on, and the machine you use it on afterward.
2. **A virtual machine on your own PC — the practice one.** The same image file, attached to a VM (QEMU, VirtualBox, or VMware — your pick, the image doesn't care). Identical system, zero risk to the demo laptop. This is where rehearsals happen and where the demo-day snapshot fallback lives: if anything misbehaves, restore the snapshot and the crew is back exactly as it was.
3. **Any spare 64-bit PC or laptop with a USB stick — the emergency one.** Boot the live ISO from USB and that machine is a Meta OS machine. Nothing to install.
4. **An always-on box at home — the later one (Phase B).** The same image on a small machine that stays on like a router, so the crew is home working the queue even when the laptop is closed. Not needed for the demo.

### What do I actually do, start to finish?
1. **Once, at first boot:** the machine asks for two secrets — the Spark key and the bus token. You enter them once. They live on that machine only, never in the image, never in the repo.
2. **Every day after:** press power. Wait ~90 seconds. The dashboard is up, the boot brief is on screen — what the crew did, what's carried over, what the watchdog saw.
3. **To give an order:** from your phone, one plain-English message. Then put the phone down. The machine does not need you connected, watching, or even awake.
4. **To hear back:** your phone buzzes exactly once — "All done" with the summary, or one blocked message with the exact decision it needs from you. Silence in between means still working.
5. **If the machine dies or you kill the power:** turn it back on. The crew reforms from what's on disk and picks its jobs back up. Nothing is lost because nothing lived in a session.
6. **If the crew itself is ever broken:** reboot and pick the rescue entry — the base OS comes up without the crew, so the machine is never a brick.

### What it needs from you, total
- The machine on and online when you want work done (orders sent while it's off wait in the cloud and are picked up at boot — never lost, just later).
- The two firstboot secrets, once.
- Your rulings when a push says "blocked" — money, permission, direction. Nothing else is ever asked.

---

## Still open (Del's calls, not invented here)

- **Day-to-day Spark access** for the build: the credit key is reserved per ruling 3; which access the build burns instead has not been named.
- **OS-001** — two-layer positioning approval (Meta OS the machine, Relay Intelligence the mind) for copy, README, boot screen.
- **OS-003** — the post-freeze exception rule (proposed: Spark-layer payload files only after the Nov 2 freeze; base, packages, units frozen solid).
- **Federation policy + second machine** — only if Del wants the second-machine demo beat.

_Verified against META_OS.md and MASTER_PLAN.md on 2026-10-24. Unverified: nothing in this document has been built yet — it is a plan. Build status lives in MASTER_PLAN.md._
