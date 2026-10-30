# Meta OS - os/ tree (OS-006)

The operating-system layer of the repo, laid down by OS-006 on
2026-10-27 by porting the proven image lane into this repo. The lane
scripts are the ones that produced the image that booted in QEMU on
2026-10-26; the only changes in the port are the layout mapping and
the payload source (this repo itself, not a hardcoded checkout path).

## Files

| Path | What it is |
| ---- | ---------- |
| `build-all.sh` | Pre-step: debootstrap a Debian 12 rootfs into `work/rootfs`, then runs `build-image.sh`. Needs privileges (tmpfs mount) and a Debian mirror; see the notes in the script. |
| `build-image.sh` | Assembly: rootfs plus this repo as payload into a raw UEFI `.img` plus `.sha256` in this directory. |
| `build-packer.sh` | Primary pipeline, one command (OS-007): Packer plus QEMU unattended build from `packer/metaos.pkr.hcl` into `metaos-<date>.img` plus `.sha256`. UNPROVEN: no build run yet, see below. |
| `packer/metaos.pkr.hcl` | Packer template (OS-007): qemu builder, bookworm netinst ISO, build preseed over HTTP, OS glue provisioners. |
| `build-live.sh` | Fallback pipeline, one command (OS-008): live-build ISO from `live-build/` into `metaos-<date>.iso` plus `.sha256`. UNPROVEN: no build run yet, see below. |
| `live-build/` | Live-build config (OS-008): `auto/config` (bookworm amd64, iso-hybrid, live session only), package list, services hook. Units are staged from `services/` at build time, never copied into this tree. |
| `preseed.cfg` | Unattended-install answers for the spec Packer route (OS-009). Unproven: see below. |
| `packages.txt` | Package manifest (OS-010, first light): frozen name set. Unpinned versions: see below. |
| `BASE.md` | Base freeze (OS-005): Debian 12 bookworm amd64, one base only, with verification evidence and checksum limits. |
| `services/` | systemd units and `relay.target` (8 ported units) plus `relay-brief.service` (Hana, OS-049) plus `relay-watchman.service` (OS-118) plus `relay-uplink.service` (OS-093) plus `relay-mcp-gateway.service` (OS-058). |
| `watchman/` | `relay_watchman.py`: the resident bell (OS-118, first light). |
| `uplink/` | `relay_uplink.py`: the order door (OS-093, first light). |
| `firstboot/` | `metaos-firstboot`: first-boot secrets prompt (OS-012). Zero credentials ship in the image. |
| `bin/` | `metaos-boot-checklist` and `metaos-update` (image tools). |
| `grub-early.cfg` | Early GRUB config embedded in the EFI binary by `build-image.sh`. |
| `README-FIRSTBOOT.md` | First-boot behavior, boot entries, updates (ported with the lane). |

## Base freeze (OS-005)

`BASE.md` freezes the single base: Debian 12 bookworm amd64, sourced
by the debootstrap call in `build-all.sh`. The debootstrap route
downloads no ISO, so no ISO checksum is claimed for the base; the
per-image `.sha256` artifact belongs to OS-007. The lane hash
mismatch flag from OS-006 stands unchanged.

## Primary pipeline (OS-007, first light)

`build-packer.sh` plus `packer/metaos.pkr.hcl` are the spec primary
pipeline: one command from a clean checkout resolves the current
bookworm netinst ISO from the cdimage listing, generates a random
per-build relay password and a build preseed (the committed
`preseed.cfg` with only its locked password line replaced), runs
`packer validate` then `packer build`, and renames the raw output
to `metaos-<date>.img` with its `.sha256` beside it. The template
verifies the ISO against the publisher SHA256SUMS file at build
time; no ISO version or hash is pinned in this repo. Provisioners
install the same units, tools, autologin drop-ins, and
`/etc/metaos-version` stamp as `build-image.sh`. Payload bake is
OS-011, so a Packer image boots with the crew units waiting on
firstboot exactly as their guards say.

UNPROVEN, stated plainly: no Packer build has run from this
template. The sandbox has no packer, no qemu, and no `/dev/kvm`,
so `packer validate` has not run either. Until a build host runs
`build-packer.sh` end to end and the image boots (OS-019 harness),
this pipeline is template plus wrapper plus structural tests, not
a proven build. Second-run package reproducibility is unproven
until two builds are compared. The build password is random per
build, never written to the repo, and discarded by the wrapper
trap; locking it at image level is OS-012 follow-up.

## Fallback pipeline (OS-008, first light)

`build-live.sh` plus `live-build/` are the spec fallback pipeline:
one command from a clean checkout, run as root, stages the OS
glue (units, target, firstboot program, tools) from this repo's
own `services/`, `firstboot/`, and `bin/` into
`live-build/config/includes.chroot/`, runs `lb clean`, `lb
config`, `lb build`, and renames the output to
`metaos-<date>.iso` with its `.sha256` beside it. The live-build
config pins bookworm amd64 and an iso-hybrid binary image; the
package list is the `packages.txt` set as real Debian package
names plus the spec extras. The staged includes are removed by
the wrapper trap on exit, so the repo never carries a second
copy of a unit: `services/` stays the single source of truth,
and the hook enables exactly the units `build-image.sh` wires
into `relay.target.wants`.

UNPROVEN, stated plainly: no live-build run has happened from
this config. The sandbox has no lb binary, so `lb config` has
not run either. Until a build host runs `build-live.sh` end to
end and the ISO boots in QEMU to the crew session, this
pipeline is config plus wrapper plus structural tests, not a
proven build. The ISO-to-primary divergences are documented in
`BASE.md`, and the demo never depends on a fallback-only
behavior.

## Stack bake at a pinned commit (OS-011, first light)

`build-image.sh` is the route that bakes the stack: it refuses a
dirty checkout, captures the checkout HEAD as PINNED_COMMIT, and
stamps it into the image in two places:
`/opt/relay/.metaos-source-commit` (the sha alone) and the second
line of `/etc/metaos-version` (`source-commit <sha>`). The payload
copy still excludes `.git`, and the empty local commit in
`/opt/relay/.git` exists only so `metaos-update` sees a git tree;
it carries no source history and is not the pinned record. The
pinned record is the stamp file, and a built image is checked by
comparing that stamp against the checkout it was built from.

Venv and requirements: there is no venv step and no pip install
step in this bake, because the stack has no third party
dependencies to install. Every import in the payload resolves to
the Python standard library or to another first party module in
this repo, and no requirements file exists here. If a
requirements file lands, the bake must gain a venv plus install
step before it can claim OS-011 complete; until then that step is
owed, not claimed.

UNPROVEN, stated plainly: no build has run from this change, so
no built image has yet carried the stamp. The check that
`/opt/relay` on a built image matches its pinned commit is owed
to a build host run, as is the boot that proves the stamped image
runs. The Packer route (OS-007) does not bake `/opt/relay` yet:
its provisioners install units and scripts only, so the pinned
commit stamp does not reach a Packer image; closing that gap is
owed alongside the first Packer build, not claimed here. The
live-build route (OS-008) likewise carries no payload stamp yet.

## Package manifest (OS-010, first light)

`packages.txt` freezes the image package name set: the 11 proven
debootstrap packages plus the spec set as real Debian names:
python3-venv (the spec's python3 plus venv) and the five spec
extras (redis-tools, chromium, fonts-dejavu, openssh-server,
qemu-guest-agent). The live-build package list carries exactly
the same set; the two files are pinned to each other by
tests/test_os_manifest.py, so one route can no longer silently
install a different set. openssh-server stays present but
disabled by default.

UNPROVEN, stated plainly: no version is recorded anywhere in
this repo, because no built image's package list has been
diffed against this manifest yet. The OS-010 pin step, owed to
a build host run, records each installed version from a built
image's dpkg -l output and flags any installed package outside
this set. Until that diff lands, this manifest is a frozen name
list, not a pinned manifest, and the second-run reproducibility
claim of OS-007 stays unproven with it.

## Secrets rule (OS-012, first light)

The image ships zero credentials. `firstboot/metaos-firstboot`
collects them once, on the console, on the machine itself: the
Upstash REST URL, the bus token (hidden input), and an optional
Muse Spark key (blank means agent transport only). It also
generates the local job-signing keyring from `/dev/urandom`.
Every file lands under `/etc/metaos` with chmod 600 (umask 077
for the whole write), and the `metaos-firstboot.service` unit
runs only while `/etc/metaos/secrets.env` does not exist yet,
so a machine that already finished setup never prompts again.
The console prompts time out, so an unattended boot never
wedges here; setup can be finished later with
`sudo metaos-firstboot`.

`bin/metaos-secrets-sweep` is the gate that proves the rule
for a built rootfs: it flags any file under `etc/metaos/`, any
file named `token`, `job-secret`, or `secrets.env` under
`etc/`, `root/`, `home/`, or `opt/`, and any literal value
for `MUSE_RELAY_URL`, `META_MODEL_API_KEY`, or
`UPSTASH_TOKEN`, or a keyring-format `default:<hex>` line.
Variable expansions do not count, so the firstboot program
itself sweeps clean. The sweep is deliberately not a general
secret scanner: the repo payload carries adversarial eval
fixtures with planted fake keys, and flagging those would fail
every build on purpose. `build-image.sh` runs the sweep after
the GRUB config and before the filesystem image step, so a
leaking rootfs fails the build instead of shipping.
tests/test_os_secrets.py pins all of it: the program, the
unit, the build wiring, and the sweep's own clean and
finding behavior on fixture rootfs dirs.

UNPROVEN, stated plainly: no sweep has run against a real
built rootfs yet (the sandbox has no built image), and the
firstboot prompt flow has not run on a scratch VM, so the
prompt wording, the timeout paths, and the service starts
after setup are written from the script, not from a run. The
first build host run either sweeps clean or fails before
assembly, and the first scratch VM run still owes the
prompt-flow proof.

## Boot test harness (OS-019, first light)

`test-boot.sh` boots a built image headless in QEMU and checks
the boot instead of claiming it. It launches with a snapshot
overlay by default (the image under test is never modified),
no network device, a monitor socket, a serial log, and a
guest-agent channel (qemu-guest-agent is in the OS-010 package
set). It waits up to `--timeout` seconds (default 600) for
`/run/metaos/ready` through the guest agent, reads
`/etc/metaos-version` from the guest and prints it verbatim,
then screenshots the dashboard through the monitor socket
(`screendump`, PPM only) and exits 0 only when every check
passes. Any failed check exits nonzero with the serial tail
attached, and the QEMU process is killed on exit.

The harness automates META_OS.md checklist items 1 (boots
unattended), 2 (relay.target plus ready marker), and the
evidence half of 12 (the version stamp, printed for a human
to match against the screenshot; no OCR step is claimed).
Items 3-11 and 13 stay manual: they need hands on a booted
image (kill a unit, cut power, read the brief), and a PASS
here does not claim them.

UNPROVEN, stated plainly: no QEMU run has happened from this
script. The sandbox has no qemu-system-x86_64 binary and no
test image has been booted by it yet, so the launch flags,
the guest-agent handshake, and the monitor screendump are
written from the QEMU interface contract, not from a run.
The first run on a build host may find flag drift; fix the
script, not the report, when it does. A non-empty PPM is
evidence to open, not proof the dashboard rendered; the
human check on the screenshot is part of the procedure until
a render check lands.

## Relay bus unit (OS-013, first light)

`services/relay-bus.service` is the unit that keeps the local bus
side current on a Meta OS machine: it runs the real `watch.py`
listener from `/opt/relay` as the relay user, with `--interval 10`,
under `relay.target`. The listener beats presence on its own loop
(`presence_beat` in `watch.py`), so the bus side stays current
without a second process. The unit restarts on failure
(`Restart=on-failure`, `RestartSec=5`), orders after
`network-online.target`, and belongs to `relay.target`
(`PartOf` plus `WantedBy`). The OS-012 secrets gate applies:
`ConditionPathExists=/etc/metaos/secrets.env` means systemd skips
the unit until firstboot has written the secrets file, and the
boot continues honestly unconfigured instead of failing. No
secret ever lands on the unit command line: the unit passes no
`--dm` flag, and the token travels via the secrets env file only.
Both image routes carry the unit: `build-image.sh` enables it
with a `relay.target.wants` symlink, and `build-live.sh` stages
`services/*.service`.

UNPROVEN, stated plainly: the kill-restart run and the clean
start-order check in the acceptance are owed on the test image.
`systemd-analyze verify` on the unit is a syntax check only and
reports no error naming `relay-bus.service` (only pre-existing
host-unit warnings). The service-map row names the wider
presence/watch/store stack; this unit covers the `watch.py`
listener and its presence beat, and `poll.py` listeners are not
unitized here. The pinning tests live in
`tests/test_os_bus_unit.py`.

## Relay jobs unit (OS-014, first light)

`services/relay-jobs.service` is the unit that runs the jobs.py
queue pass at boot: a oneshot lease sweep from `/opt/relay` as
the relay user, ordered after `network-online.target` and
`relay-bus.service`, so the pass never runs before the bus side
it reads. The sweep requeues claimed jobs whose claim holder is
gone (`cmd_sweep` in `jobs.py`), which is what makes a job
posted before shutdown claimable again after boot. The unit
belongs to `relay.target` (`PartOf` plus `WantedBy`, and
`relay.target` wants it back). The OS-012 secrets gate applies:
`ConditionPathExists=/etc/metaos/secrets.env` means systemd
skips the unit until firstboot has written the secrets file.
No secret ever lands on the unit command line: the command is
exactly `jobs.py sweep`, and the token travels only as the
`MUSE_RELAY_TOKEN_FILE` path in the unit environment. Both
image routes carry the unit: `build-image.sh` enables it with
a `relay.target.wants` symlink, and `build-live.sh` stages
`services/*.service`.

UNPROVEN, stated plainly: the announced-and-claimable-after-boot
run in the acceptance is owed on the test image. The unit
as landed is a boot-time sweep oneshot, not a continuous
queue-service loop: `jobs.py` defines no loop or serve
subcommand, so the continuous-loop half of the OS-014 wording
is owed, not claimed here. The pinning tests live in
`tests/test_os_jobs_unit.py`.

## Relay overseer unit (OS-015, first light)

`services/relay-overseer.service` is the unit that runs the
overseer tick as a service: one overseer pass from `/opt/relay`
as the relay user, ordered after `network-online.target`,
`relay-bus.service`, and `relay-jobs.service` and wanting all
three, so the tick never runs before the bus side and the queue
pass it reads. The pass itself is `mos.py tick` (a shim onto
`mos/cli.py`, whose tick subcommand runs `mos/overseer.py`
`tick()`): a lease sweep, a stale-capability prune, and
verification of done-but-unverified jobs. The service is a
oneshot, and the loop is the timer: `relay-overseer.timer`
fires it 2 minutes after boot and every 5 minutes after, wanted
by `relay.target`. The unit belongs to `relay.target`
(`PartOf` plus `WantedBy`, and `build-image.sh` enables the
service itself with a `relay.target.wants` symlink while
`relay.target` wants the timer back). The OS-012 secrets gate
applies: `ConditionPathExists=/etc/metaos/secrets.env` means
systemd skips the unit until firstboot has written the secrets
file. No secret ever lands on the unit command line: the
command is exactly `mos.py tick`, and the token travels only
as the `MUSE_RELAY_TOKEN_FILE` path in the unit environment.
`build-live.sh` stages `services/*.service`, so both image
routes carry the unit. Note: the unit as it landed with the
OS-006 tree wanted only `network-online.target` and ordered
after `relay-jobs.service` alone; this batch brings the
`[Unit]` section up to the OS-015 wording before pinning it.

UNPROVEN, stated plainly: the tick-on-a-booted-image run in the
acceptance is owed on the test image, including the timer
actually firing on schedule and the verify-done half against a
real worker branch. The pinning tests live in
`tests/test_os_overseer_unit.py`.

## Boot target and ready gate (OS-016, first light)

`services/relay.target` is the boot target that groups the crew
units: dashboard, bus, jobs, overseer timer, ready gate,
watchdog, brief, and firstboot, all wanted by the target itself
and enabled into `relay.target.wants` by `build-image.sh`, the
Packer provisioner, and the live-build hook on the same list, so
all three image routes carry the same set. The overseer service
itself is symlinked into `relay.target.wants` beside the timer,
as with OS-015. The target as it landed with the OS-006 tree
wanted only dashboard, bus, jobs, overseer timer, ready, and
firstboot; this batch adds watchdog and brief to the target
wants and to all three enablement lists before pinning them.

`services/relay-ready.service` is the oneshot gate that runs
`bin/metaos-boot-checklist` once at boot, with
`RemainAfterExit=yes`. It orders after every unit the gate
checks (dashboard, bus, jobs, overseer timer, watchdog,
firstboot) and deliberately not after `relay-brief.service`,
because the brief runs after the ready gate by design and the
gate cannot wait on a unit that waits on the gate. The
checklist writes `/run/metaos/ready` only when the gateable set
passes: dashboard and watchdog always, plus bus, the jobs sweep
result, and the overseer timer once secrets exist. Before
firstboot the secrets-gated units are honestly skipped by their
OS-012 gates, so the gate requires only dashboard and watchdog
there. The jobs sweep is gated on its `Result`, not on
`is-active`: jobs and overseer are oneshots with no
`RemainAfterExit`, so `is-active` reads inactive after a clean
run. The overseer tick itself is not gated, because its timer
first fires 2 minutes after boot and no tick has run when the
gate runs; the timer being armed is the gateable signal. When
the gate blocks, no marker is written and the blocked lines are
printed; the marker absence is the signal.

Excluded for stated reasons, not by omission: worker instances
are not auto-enabled (the template `relay-worker@.service` is
enabled per nick only, OS-017, until the handler program and
the mos.py DM-secret env path land), so the gate requires no
worker unit. The watchman IS grouped in the target now
(OS-118, below) but is deliberately not in the ready gate's
checked set: the gate checks dashboard and watchdog always
(plus the secrets-gated units once secrets exist), and the
watchman's health is the watchdog's OS-122 crew-dark beat,
not a gate line. Adding it to the gate is owed follow-up,
not silently present.

UNPROVEN, stated plainly: reaching `relay.target` on a booted
image, and the marker appearing only with all units active as
proven by disabling one unit, are owed on the test image; so is
a completion stamp for the oneshot jobs sweep and overseer tick
beyond the jobs `Result` the gate reads today, and any
restart-window case where a checked unit restarts after the
oneshot gate has already run. The pinning tests live in
`tests/test_os_target_unit.py`.

## Worker fleet units (OS-017, first light)

`services/relay-worker@.service` is the worker fleet template:
one instance per crew nick, enabled as
`relay-worker@<nick>.service`. The instance name is the nick
(`MUSE_RELAY_NICK=%i`), the per-instance env file is
`/etc/metaos/worker-%i.env` (optional: caps and roles for that
nick), the image-wide secrets file is required (OS-012 gate),
and the instance joins `relay-workers.slice` (OS-035) and orders
after `relay-jobs.service` (the boot lease sweep runs before
any worker claims). Both image routes install it: the
`services/*.service` install in `build-image.sh` and the
live-build services hook carry the template, but neither
auto-enables any instance.

UNPROVEN, stated plainly: no instance is enabled yet, on
purpose. Two things are owed before the "two instances side by
side claim disjoint jobs" acceptance can be met: a handler
program for the mos.py worker loop (loop mode exits 2 by
design, the handler is the calling agent, and no stock handler
ships in this repo), and an environment path for the DM secret
(mos.py worker takes `--dm` on the command line only, a worker
with an empty secret polls zero DMs, and this template puts no
secret on its command line). Until both land, enabling an
instance would start a worker that registers but never claims.
`systemd-analyze verify` on the template is a syntax check
only; the live two-instance run on the test image is owed
with the two items above.

## Agent driver contract (OS-053, first light)

`drivers/CONTRACT.md` is the driver interface every coding agent
adapter implements: `start(job_spec)` against a signed spec,
`stop()`, `heartbeat()` in bus progress format, and `artifacts()`
plus a status record out. `drivers/stub_driver.py` is the
reference implementation: it runs a caller supplied command as
the agent child, logs its output to `driver.log` in the workdir,
diffs a before/after file snapshot for the changed file list, and
builds the status record from `mos/acceptance.verify` against the
workdir on disk. `drivers/CONFORMANCE.md` is the ten item
checklist (C1-C10) any future driver must pass; the pinning tests
in `tests/test_os_driver_contract.py` run it against the stub.

UNPROVEN, stated plainly: the stub proves contract mechanics, not
a coding agent doing work. The per driver systemd template is owed with it, and the "passes every
checklist item on the test image" acceptance is met on a developer
machine only until a test image exists. The driver never posts to
the bus: heartbeat records go to a caller supplied sink, and
signature presence is enforced at `start()` while cryptographic
verification stays at `jobs.py verify_job` claim time.

## Muse Code driver (OS-054, first light)

`drivers/muse_driver.py` is the first real driver: it builds a
prompt from the signed job spec (title, spec text, owned files,
acceptance lines, attempt budget; the signature is never in the
prompt, the argv, or a log), writes it to a temp file outside the
workdir, and launches the Muse Code CLI headless as
`muse exec --prompt-file <file>` with cwd=workdir. The child's
stdout lines stream into heartbeat records (one PROGRESS record
per line, note truncated) and verbatim into `driver.log`; on exit
it returns the contract artifacts record from the snapshot diff
and `mos/acceptance.verify` on disk. `drivers/run_driver.py` is
the runner `services/relay-driver@.service` executes: one spec
file in, artifacts JSON out, exit 2 on driver errors, no bus
post, no job record touch. The pinning tests in
`tests/test_os_driver_muse.py` run the full C1-C10 checklist
against the driver plus prompt, argv, streaming, missing binary,
and runner cases.

UNPROVEN, stated plainly: no `muse` binary exists on a dev
machine and no booted test image exists in this repo, so the
checklist run uses a fixture stand-in executable in place of the
binary. The argv shape is the documented headless form, not a
shape proven against a live CLI here. No approval bypass flag is
passed: headless approval behavior is the CLI's own
configuration, and the overseer handoff that writes the spec file
and consumes the artifacts JSON is OS-055 work.

## The watchman (OS-118, first light)

`watchman/relay_watchman.py` is the resident bell: one watch
cycle over job records and agent heartbeat records yields wake
events (open job addressed to a local sleeping agent) and nudge
events (claimed job whose local claimer heartbeat went stale),
each naming job + agent, each rung at most once per rung-ledger
key (wake per job id; nudge per job id + the heartbeat value
that went stale, so a worker that recovers and stalls again
earns a fresh nudge). Detection reads job state only, never a
bus message counter: tick() takes no counter argument, and a
stray counter field carried on a job record changes nothing.
The program makes no model calls, holds no session, posts
nothing to the bus, and moves no claim. Ringing is the event;
starting the agent's session with the job as its brief is the
OS-119 wake adapter's work. `services/relay-watchman.service`
runs the loop under relay.target after relay-jobs.service
with the OS-012 secrets gate, and all three image routes
enable it into relay.target.wants (the OS-016 target set now
includes it; the ready gate deliberately does not check it
yet, see the OS-016 section). The CLI reads JSON snapshot
files (`--once` for one cycle, `--loop` re-reading each
cycle, `--max-cycles` for tests and debugging); a missing
snapshot file reads as an empty cycle, never a crash and
never a phantom ring. Pinning tests in
`tests/test_os_watchman.py`.

UNPROVEN, stated plainly: no booted test image exists in this
repo, so the one-cycle wake and the same-cycle nudge are
proven on fixtures only, not on a running machine. The
live-queue reader (jobs.py list output plus presence
heartbeats, the same fields tick() already takes) is owed
follow-up before the unit is claimed live; until then the
unit's snapshot files are the interface. The mechanical
restart rung (systemd, OS-034) and reassign rung (overseer
via the OS-125 baton pass) are owed follow-up too: this
first light emits wake + nudge only, and says so, rather
than claiming rungs it does not work.

## The order door (OS-093, first light)

`uplink/relay_uplink.py` is the order door: one cycle over
order records yields intake records (valid order, raw text
as spec, marked ORDER, no invented files or accept lines),
queued events (connection down, order kept in pending),
duplicate events (same id seen again, no second record),
rejected events (missing id, empty text, or missing origin,
with the reason named), and unsigned-refused events (crew
mode with no signing key, order kept pending). Signing is
HMAC-SHA256 over id + text with a caller-supplied key, the
jobs.py v2 shape; with no key the intake is honestly
unsigned outside crew mode. Connection health is a backoff
state machine: failures wait 5, 10, 20, ... seconds capped
at 300, and one good connection clears the count, so a
network kill mid-flight costs a bounded wait and loses
no order, and pending orders drain in received order on
reconnect. The program makes no model calls, holds no
session, posts nothing to the bus, moves no claim, and
never auto-posts past the DSP-007 approval gate: an intake
record waits for the dispatch path. `services/relay-uplink.service`
runs the loop under relay.target after network-online and
relay-jobs with the OS-012 secrets gate, and all three
image routes enable it into relay.target.wants. Pinning
tests in `tests/test_os_uplink.py`.

UNPROVEN, stated plainly: no booted test image exists in
this repo, so intake, queueing, and reconnect drain are
proven on fixtures only, not against a live cloud room.
The live cloud reader (the Upstash room the order arrives
in, the same fields tick() already takes) is owed follow-up
before the unit is claimed live; until then the unit's
snapshot files are the interface. The dispatch posting
itself (DSP-007 gate + DSP-008 poster turning an intake
record into posted jobs) is owed follow-up too: this first
light takes orders in and says so, rather than claiming
work has started.

## The MCP gateway daemon (OS-058, first light)

`services/relay-mcp-gateway.service` runs Dale's MCP gateway
as a system daemon under relay.target: the gateway program
(`gateway.py`, Streamable HTTP on 127.0.0.1:8931/mcp per its
backends.json) as the relay user, after network-online.target,
with Restart=on-failure per the OS-034 contract, and with the
OS-012 secrets gate (EnvironmentFile and ConditionPathExists
both name /etc/metaos/secrets.env, so an unconfigured boot
skips the unit instead of starting a gateway whose keyed
servers have no keys). No secret is on the command line.
Pinning tests in `tests/test_os058_gateway_unit.py`.

UNPROVEN, stated plainly: no booted test image exists in
this repo, so service active at boot and a worker plus a
driver calling a gateway tool through the local endpoint are
proven nowhere yet. And the OS-059 bake is owed before any of
that can be proven: nothing in this tree bakes the gateway
beside /opt/relay yet, so the unit's ExecStart path does not
exist on a machine built from this tree. The unit declares
WantedBy=relay.target, but relay.target does not Want it
back yet and neither image route enables it yet, on purpose:
wiring it in before the bake lands would put a failed unit
on every boot. The OS-059 batch flipped that wiring and
says so in the Gateway bake section below.

## Gateway bake (OS-059, first light)

The three image routes bake Dale's MCP gateway beside
/opt/relay so the OS-058 daemon unit has something to run.
Each route copies exactly two files from the workspace
mcp-gateway checkout (or $METAOS_GATEWAY_SRC): gateway.py,
the daemon, and backends.json, the server catalog. Nothing
else from that checkout is baked: no .venv, no servers/
runtimes, no debug/ logs, no databases, no backups. A
missing source file refuses the build instead of baking a
gateway that cannot start. Beside the two files each route
writes .metaos-gateway-bake, a stamp with the bake date,
the source dir, and the sha256 of both files. That hash
record is the pin: the gateway source is a workspace
checkout, not a git repo, so there is no commit to pin.
All three routes enable relay-mcp-gateway.service under
relay.target, and relay.target Wants it back. The OS-012
sweep gains the bake allowlist: any other file under
/opt/relay/mcp-gateway in a built rootfs is a finding, so
credential adjacent estate cannot ride into the image
beside the daemon. Pinning tests in
tests/test_os059_gateway_bake.py; the OS-058 deferral pins
in tests/test_os058_gateway_unit.py are flipped by this
batch, deliberately.

UNPROVEN, stated plainly: no image build has run from this
tree in the sandbox, so a booted gateway serving its catalog
is proven nowhere yet. Two gaps stay open. The gateway
Python deps (mcp, starlette, uvicorn) have no venv or pip
step in this bake, so a bare image would fail the unit at
import time until that step lands. And the downstream server
runtimes are not baked, so only the backends whose runtimes
the image carries will come up; the gateway skips a dead
backend with a log line and keeps serving, which is why the
catalog is servable offline even while most backends stay
owed to the OS-063 package pass.

## Artifact store (OS-083, first light)

`mos/artifact_store.py` is the workspace/artifact store in
minimal form: a git-backed versioned shared filesystem under
/var/lib/metaos/artifacts on the image. Dispatched jobs deposit
work products there by path (jobs/<job id>/<name>), one git
commit per deposit, with a manifest per job recording version,
sha256, size, author, and deposited time. A job record carries
artifact paths through `attach()`, which returns a copy, never
a mutation, with entries of the form
artifact:<job id>/<name>@v<version>. Names are relative paths
below the job directory; traversal, absolute paths, and slash
job ids are refused. A byte-identical redeposit returns the
current version with no new commit, rather than inventing a
version for unchanged bytes. All three image routes bake the
store root empty plus a .metaos-artifact-store marker, owned
by the relay user; the store repo is created on first deposit,
not baked, so no build-machine git state rides into the image.
Pinning tests in tests/test_os083_artifact_store.py.

UNPROVEN, stated plainly: no image build has run from this
tree in the sandbox, so deposits on a booted image are proven
nowhere yet. No driver-executed job has deposited through this
module. jobs.py itself does not read or write the store, so
attaching artifact paths to a live job hash is OS-094 work,
still owed, and the dashboard links that consume these paths
are OS-084, also still owed.

## Memory service (OS-078, first light)

`mos/memory.py` is the memory service in minimal form: a
journaled, versioned store under /var/lib/metaos/memory on
the image. Each agent has its own journal under agents/<nick>
and the crew shares one journal under shared/. A journal is
append-only JSON lines, one per write, with a version that
counts from 1 per key inside its namespace, so the same key
in the own and shared namespaces versions independently. A
write identical to the latest text is a no-op returning the
current version, never a new version for unchanged text.
Keys are relative paths below the namespace directory;
traversal, absolute paths, and slash nicks are refused.
`read_all()` returns own and shared latest entries under
separate keys, never merged, and no cross-agent read is
offered: another agent's private memory is the OS-086
scoping question (Phase B), not a default here.
`mount_paths()` names the two directories a launcher mounts
into a process at start (own memory home, shared shelf).
The service itself is a filesystem store, not a daemon, so
its relay.target presence is the oneshot
relay-memory.service, which runs the module's ensure step as
the relay user at boot. All three image routes bake the
store root empty plus a .metaos-memory-store marker, owned
by the relay user; the namespaces are created at boot, not
baked, so no memory entry rides into the image.
Pinning tests in tests/test_os078_memory.py.

UNPROVEN, stated plainly: no image build has run from this
tree in the sandbox, so memory on a booted image is proven
nowhere yet. No process has launched with these directories
mounted; that launcher wiring is owed beside OS-080's. The
boot brief reading settled decisions from this store is
OS-079 (Hana), still owed, as are scoping enforcement
(OS-086) and compaction/retention (OS-087) in Phase B.

## Two routes, stated plainly

The spec route (plan/META_OS.md) is Packer plus QEMU with
`preseed.cfg`. The route that actually produced a booting image in
this sandbox is the debootstrap route: `build-all.sh` then
`build-image.sh`. This tree carries both: the proven scripts plus
the spec preseed. Nothing here claims the Packer route has run.

## What OS-006 is not

- Not OS-007: the pipeline is not claimed working from this tree
  until a build run from this tree produces a booting image.
- Not OS-008: the fallback ISO is not claimed buildable from
  this tree until a build host runs `build-live.sh` end to end
  and the ISO boots in QEMU to the crew session.
- Not OS-009: `preseed.cfg` is written from the OS-009 spec and
  has no unattended-install run behind it yet.
- Not OS-010 (versions): `packages.txt` now freezes the name set
  under OS-010 first light, but versions pin only when a built
  image's package list is diffed against it; that diff is still
  owed.
- Not a new boot claim: the 2026-10-26 QEMU boot verdict belongs
  to the lane artifact as recorded at the time. The lane file's
  current hash no longer matches the recorded hash (flagged
  2026-10-27, re-verify owed), so this tree makes no boot claim
  of its own until a build from this tree boots.
- Not a behavior change to the image: `relay-brief.service`
  ships in `services/` but `build-image.sh` enables a fixed unit
  list that does not include it, so installing it alone does
  not start it. Enabling it is OS-049/OS-016 follow-up.

## Update path (OS-021, first light)

On the image, `metaos-update` is installed at `/usr/local/bin`
by `build-image.sh` (mode 755) and updates only the crew tree,
never base OS packages (frozen base, OS-003/OS-005).

Apply an update bundle:

```
sudo metaos-update /path/to/metaos-update.bundle
```

The script verifies the bundle first (`git bundle verify`), then
keeps the current tree at `/opt/relay.prev`, fetches the bundle
into `/opt/relay`, checks out its `main`, and restarts
`relay.target`. A failed verify or a target that is not a git
checkout refuses before anything moves.

Roll back to the previous tree:

```
sudo metaos-update --rollback
```

Rollback swaps the live tree with the kept previous tree, so the
tree that was live becomes the new previous tree and a second
rollback swaps back. There is no third state: rollback with no
previous tree exits 1 and changes nothing.

Exit codes: 0 applied or rolled back, 1 refused (no previous
tree, not a git checkout, bad bundle), 2 usage (no bundle file
given or the file does not exist).

UNPROVEN, stated plainly: the N to N+1 update plus rollback run
on a scratch VM with all services active again is still owed;
the tests in `tests/test_os021_update.py` prove apply, swap
rollback, and every refusal against fixture trees only, using
the `METAOS_RELAY_ROOT` test hook in the script (never set on
the image, where the target stays `/opt/relay`).

## Build outputs never commit

`build-all.sh` and `build-image.sh` write under `os/work/` and
drop `metaos-*.img` plus `.sha256` in this directory. Both paths
are gitignored. The image itself is never a repo file.
`build-live.sh` drops `metaos-*.iso` plus `.sha256` in this
directory, also gitignored; the ISO itself is never a repo file.
