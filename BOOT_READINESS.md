# BOOT_READINESS — boot-to-screen gap audit for opencode1

Scope: audit only. No VM was booted and no image was built for this
report (opencode1 owns booting). Every verdict below is grounded in
files at this worktree's `main` checkout (`4bef226a`) plus the
`opencode2/proof` tip named at the end. "READY" means the config
exists in-tree; "GAP" means work is owed before a VM can reach a
Mac-like desktop with openable programs. Most READY rows still carry
a run-proof gap — the repo itself says so, and this report quotes it.

## 0. Known-good proof commit to start from — READY

Start from `opencode2/proof` tip **`3987b936`** ("OC2 appliance
proof: bootable agent box, 20/20 baselines $0.43, reboot survival",
2026-11-02):

- `os-build/logs/OC2-appliance-proof-journal.txt` — journal from a
  real boot: `oc2-queue` + `oc2-trio` up, patrol 20/20 checks,
  0 errors, reboot survival.
- Companion S1 proof `e39ab52e` (OC2P-001..005, VERDICT: BOOT):
  kernel ELF built, 17 MB image with valid MBR, QEMU boot +
  screendumps `os-build/captures/OC2P-kf01-fb*.png`.
- Proof recipe: `os-build/OPENCODE2_PROOF_LANE.md` (S2 OC2P-010:
  fresh-boot acceptance re-run per main move).

Caveat: the appliance proof covers the `agent-layer/` user units
(`oc2-queue`, `oc2-trio`, `oc2-patrol` on `default.target`), NOT the
`os/os/services/` crew target below. Before building, verify the
`os/` tree on the start commit matches `main`:
`git diff main -- os/os | head` must be empty or each delta named.

## 1. Firstboot (zero-credentials prompt) — READY (config) / GAP (run proof)

| File | State |
| ---- | ----- |
| `os/os/firstboot/metaos-firstboot` | READY — console prompt (Upstash URL, hidden bus token, optional Spark key, generated job-signing keyring), 60 s timeout so unattended boots never wedge, re-runnable via `sudo metaos-firstboot` |
| `os/os/services/metaos-firstboot.service` | READY — `ConditionPathExists=!/etc/metaos/secrets.env`, `WantedBy=multi-user.target`, `TTYPath=/dev/console`, `TimeoutStartSec=0` |
| `os/os/bin/metaos-secrets-sweep` | READY — build-time gate; `build-image.sh` runs it pre-assembly and fails the build on a finding |
| `os/os/README-FIRSTBOOT.md` | READY — documents boot entries (crew `relay.target` vs rescue `multi-user.target`), autologin appliance posture, update path |

GAP: the prompt flow has never run on a scratch VM — wording,
timeout paths, and the post-setup `systemctl start` line are written
from the script, not from a run (`os/os/README.md` §Secrets rule,
verbatim UNPROVEN). Prove with one attended + one unattended boot.

## 2. Services and targets — READY (units present) / GAP (three wirings)

| File | State |
| ---- | ----- |
| `os/os/services/relay.target` | READY — groups dashboard, bus, jobs, overseer service + timer, ready gate, watchdog, brief, watchman, uplink, mcp-gateway, memory, firstboot, custos/loop timers |
| `os/os/services/relay-dashboard.service` | READY but NOTE — `python3 -m http.server 8080 --directory /opt/relay`: a static file viewer, not a desktop and not the Trio app (which also defaults to `:8080`; only one can own the port on an image) |
| `os/os/services/relay-bus.service`, `relay-jobs.service` | READY — bus listener + boot lease sweep, both behind the OS-012 secrets gate |
| `os/os/services/relay-brief.service` | READY — oneshot `After=relay-ready.service` by design (template brief until Spark transport lands; no unit change needed for the switch) |
| `os/os/services/relay-watchdog.service` (+ `.d/demo-thresholds.conf`) | READY — loop with `--beat`; demo drop-in is image-gated (`METAOS_DEMO=1` only) |
| `os/os/services/relay-uplink.service`, `relay-watchman.service`, `relay-memory.service` | READY — uplink order door, watchman bell, memory store ensure-step; all snapshot/file interfaces, live readers owed as follow-up |
| `os/os/services/relay-mcp-gateway.service` | READY (unit) / GAP (deps) — bake lands `gateway.py` + `backends.json` only; the gateway Python deps (`mcp`, `starlette`, `uvicorn`) have **no venv/pip step** in any route, so the unit fails at import on a bare image (`os/os/README.md` §Gateway bake) |
| `os/os/services/relay-worker@.service`, `relay-driver@.service` (+ `.slice` units) | GAP by design — templates never auto-enabled: no handler program ships for the worker loop and no DM-secret env path exists (OS-017); the driver needs a real `muse` binary + the OS-055 handoff (spec file in, artifacts JSON out) |
| `os/os/services/relay-watchman-watch.service` | GAP (unwired) — unit file exists but is in **neither** `relay.target` Wants **nor** any image enablement list (`build-image.sh`, Packer provisioners, live-build hook); its own header says the wiring is Pax's OS-101 integration, deliberately not claimed |

All three image routes enable the same unit set from the single
source of truth in `services/` (never a second copy in-tree).

## 3. Image build (three routes, none proven from this tree) — GAP

| File | State |
| ---- | ----- |
| `os/os/build-all.sh` + `os/os/build-image.sh` | GAP (UNPROVEN) — debootstrap bookworm rootfs (needs root, tmpfs mount, Debian mirror) + scripted assembly to `metaos-<date>.img`; the only route with a prior booting artifact (2026-10-26), but **no build has run from this tree** |
| `os/os/build-packer.sh` + `os/os/packer/metaos.pkr.hcl` | GAP (UNPROVEN) — spec primary route; needs packer + qemu + KVM; ISO resolved at build time and verified against the publisher SHA256SUMS; **`/opt/relay` payload bake is OS-011 follow-up — a Packer image boots with crew units waiting on firstboot and no pinned-commit stamp** |
| `os/os/build-live.sh` + `os/os/live-build/` (`auto/config`, `config/package-lists/metaos.list.chroot`, `config/hooks/live/0900-metaos-services.hook.chroot`) | GAP (UNPROVEN) — fallback live ISO (needs root + `lb`/`mksquashfs`/`xorriso`); boots to a live crew session, **does not install**, state does not survive reboot |
| `os/os/BASE.md`, `os/os/packages.txt`, `os/os/preseed.cfg`, `os/os/grub-early.cfg` | READY (frozen names: Debian 12 bookworm amd64, 17-package name set, unattended answers, early GRUB) / GAP (versions unpinned — OS-010 diff against `dpkg -l` owed; preseed has no install run) |

Common guards (READY): all three routes refuse dirty checkouts and
stamp the source commit; outputs (`metaos-*`, `work/`) are
gitignored and never commit. Recommendation: build the debootstrap
route first — it is the shortest path to a booting `.img` — then
close the Packer payload gap before calling Packer primary.

## 4. Overseer timer — READY (config) / GAP (firing proof)

| File | State |
| ---- | ----- |
| `os/os/services/relay-overseer.service` | READY — oneshot `mos.py tick` (lease sweep, stale-capability prune, verify done jobs), ordered after bus + jobs + network, secrets-gated |
| `os/os/services/relay-overseer.timer` | READY — `OnBootSec=2min`, `OnUnitActiveSec=5min`, `WantedBy=relay.target`; symlinked into `relay.target.wants` beside the service on all three routes |
| `os/os/services/relay-ready.service` + `os/os/bin/metaos-boot-checklist` | READY — the gate correctly checks the **timer armed**, not a tick (no tick has run when the gate runs); jobs sweep gated on `Result=success`, not `is-active` (oneshots); `/run/metaos/ready` is the `test-boot.sh` wait condition |

GAP: the tick on a booted image and the timer actually firing on
schedule are owed on the test image (`os/os/README.md` §Overseer
unit). No completion stamp exists yet for the oneshot sweep/tick
beyond the jobs `Result` the gate reads.

## 5. Boot-to-screen: Mac-like desktop with openable programs — GAP (headline)

This is the gap the audit is for. What the VM reaches today:

- GRUB menu ("Meta OS" → `systemd.unit=relay.target`; rescue →
  `multi-user.target`) → getty autologin as `relay` on tty1 +
  serial → `relay.target` → static file listing at
  `http://<machine>:8080/`.

What is missing, verified by repo-wide grep (zero hits for
`xorg|x11|wayland|gdm|lightdm|sddm|openbox|gnome|kde|xfce|autostart`
outside this report; only `chromium` the package name plus the
live-boot `quiet splash` flag):

1. **No display stack.** No X server, no Wayland compositor, no
   window manager, no display manager in `packages.txt`, no
   graphical unit in `services/`, no Plymouth/boot-splash unit.
   `chromium` ships as a package but **nothing launches it** — no
   kiosk unit, no autostart entry, no session script.
2. **No desktop-proof capture.** `os/os/test-boot.sh` (OS-019)
   automates BOOT_OK / READY_OK (`/run/metaos/ready` via guest
   agent) / VERSION / non-empty screendump — but a non-empty PPM
   is evidence to open, not proof the dashboard rendered, and the
   proof branch states it plainly: "Desktop screendump IMPOSSIBLE
   (no desktop env in server image) — none claimed"
   (`OPENCODE2_500_STATUS.md` §19/§20 UNPROVEN list).
3. **Dashboard is not a desktop.** `relay-dashboard.service`
   serves `/opt/relay` over plain HTTP; the Mac-like surface
   (`index.html`, `bus.html`/crew board) is a browser page with
   no browser on the image and no openable-program launcher.

To close it, opencode1 needs (in order): a GUI base decision
(full DE vs minimal WM + Chromium kiosk — the proof lane's S2
OC2P-012 bounds this as one spike, Xubuntu ISO only if present
locally, never a 9 GB download on a hunch); the kiosk/autostart
unit(s) under `relay.target` plus packages; then a desktop
screendump in `test-boot.sh` output judged by a human, and only
then "openable programs" (each program = a `.desktop`/launcher
entry or a dashboard card backed by a real unit — never a
screenshot mock).

## Suggested opencode1 run order

1. `git worktree add /private/tmp/oc1-boot -b opencode1/boot-installer 3987b936`; confirm `git status --porcelain` empty.
2. `diff <(git show main:os/os/services/relay.target) os/os/services/relay.target` — name every delta or rebase onto `main`.
3. Build route 1 (`os/os/build-all.sh`) on a KVM host; file the
   build log verbatim.
4. Boot via `os/os/test-boot.sh <img>`; require `READY_OK` +
   non-empty screendump before touching desktop work.
5. Prove firstboot attended + unattended; then the GUI spike
   (OC2P-012 bounds); then wire `relay-watchman-watch.service`
   (OS-101) and the gateway venv before claiming the full target.
