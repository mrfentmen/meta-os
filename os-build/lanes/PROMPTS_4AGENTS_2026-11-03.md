# Four lanes, four agents — Meta OS, night of 2026-11-03

Each block below is a standalone prompt for one new chat. They do not overlap:
the ownership table in each prompt says what that lane may edit.

Shared ground truth all four repeat, because it stops re-auditing:
- Repo: `/Users/test/Desktop/meta-os`
- Live disk: `/tmp/metaos.ext4` (16 GB, arm64 Ubuntu 24.04, user `ubuntu`),
  boots XFCE + kiosk → epiphany fullscreen on `http://127.0.0.1:18900/shell.html`.
- Backends: 18900 face-http, 18931 launcher, 18932 facts, 18933 ptyd,
  18934 face-site, 18935 board, 18936 files, 18940 metaosd (18999/98/97 are
  ptyd selftests).
- macOS cannot mount ext4: use
  `docker run --rm --privileged -v /tmp/metaos.ext4:/disk.img ubuntu:24.04`
  + `mount -o loop`, or `debugfs -w`, then md5-compare repo vs image.
- Settled, do not redo: wallpaper (`meta-live.py`, 32 frames), `kiosk.sh`,
  `session.sh`, `proof_boot.sh`, `proof_session.sh`, the 14-link table in
  `os-build/INTEGRATION.md`.

Lane reports go to `os-build/lanes/` — one file each, append nothing to
another lane's report.

---

## LANE A — Apps

You are working in `/Users/test/Desktop/meta-os`. You are one of four agents
building Meta OS in parallel tonight. You own the **desktop applications**
lane: every icon in the dock must do real work, offline, and keep its data.

### Read first (do not re-audit)
`os-build/INTEGRATION.md`, `os-build/DEMO.md`, `os-build/face/APP_MATRIX.md`,
`os-build/face/SESSION.md`. They already list what is proven and what is only
installed. Do not re-derive those; build on them.

### Ground truth
- Image `/tmp/metaos.ext4` (16 GB, arm64 Ubuntu 24.04, user `ubuntu`) boots
  XFCE + kiosk → epiphany fullscreen on `http://127.0.0.1:18900/shell.html`.
- 17 dock apps live in `os-build/face/shell.html` (`APPS` array, line ~73).
  Pages are served by `face-http` on 18900 out of `/opt/face`; the repo pages
  (index.html, surfaces.html, labs/molecules/index.html, logo-studio.html)
  are served by `face-site` on 18934 from `/opt/face-site`.
- Backends: 18931 `launcher.py`, 18932 `facts.py`, 18933 `ptyd.py`,
  18935 `board.py`, 18936 `files.py` (already real `$HOME` + XDG trash),
  18940 `metaosd`.
- `os-build/face/provision.sh --root <mnt>` stages `/opt/face`, the systemd
  units and the enable links. Everything it stages must also exist in repo.
- macOS cannot mount ext4. Use `docker run --rm --privileged -v
  /tmp/metaos.ext4:/disk.img ubuntu:24.04` + `mount -o loop`, or `debugfs -w`.

### You own (edit freely)
`os-build/face/*.html` **except `agents.html`**, `os-build/face/*.py`
(you may extend handlers; do not change existing ports or wire protocols),
`os-build/face/search.js`, `tile.js`, `workspace.js`, `os-build/face/provision.sh`,
`os-build/face/APP_MATRIX.md`, and any new daemon you add (e.g. `notesd.py`).

### You must NOT touch
`agents.html`, `agents/**`, `agent-layer/**`, `os-build/iso/**` (including
`payload-agent`, `build_iso.sh`, `calamares`), `os-build/tools/proof_*.sh`,
`os-build/face/kiosk.sh`, `session.sh`, `meta-live.py`, `payload-theme/**`,
and the window-manager half of `shell.html` (you may edit the `APPS` array
only). No `git reset`, `git checkout`, or `git push`.

### Build list, in this order

**A1. The Chrome dock tile is a remote URL.** `APPS[0]` points at
`https://meta-os.pages.dev`, so offline it is a blank window. Replace it with a
local `start.html` on 18900: the Meta wordmark, all 17 app tiles, and the real
local services list. No external URL anywhere in the file (grep must show
only `127.0.0.1`). Rename the tile "Web".

**A2. Notes are localStorage, not files.** Add `notesd.py` on **18937** that
writes notes to `$XDG_DATA_HOME/metaos/notes/<id>.json` plus a readable
markdown mirror in `~/Notes/`. Wire `notes.html` to it. localStorage may stay
only as an offline cache and must say `cached` when it is being read.
Acceptance: `curl` create → list → restart daemon → list still has the note →
`~/Notes/*.md` exists → `files.html` shows it.

**A3. Calendar is localStorage.** Same daemon: events persist as a valid
`~/Notes/calendar.ics` (VCALENDAR/VEVENT, DTSTART/DTEND, escaping), with
import and export buttons and the file path shown in the UI. Acceptance: a
small python check parses the file back and matches the event count.

**A4. Settings only live in one epiphany profile.** Persist them through the
daemon to `~/.config/metaos/settings.json` and add `GET /settings`. The shell
keeps its localStorage read for instant paint, but after you delete the
epiphany profile and reload, theme, bar colour and wallpaper choice must come
back. Acceptance: exact commands in the report.

**A5. Dashboard must not show invented numbers.** Extend `facts.py` with
distro, kernel, uptime, mem, disk free, package count, and agent count read
from 18940. `dashboard.html` renders a card only from a successful fetch and
prints `backend unreachable` on failure. No hardcoded values.

**A6. Editor + Files + Trash as one system.** Editor saves through
`files.py` into `$HOME`; `files.html` opens the Notes folder; `trash.html`
shows the original path out of each `.trashinfo`. Acceptance: save from the
editor, see the file in Files, trash it, restore it, byte-identical.

**A7. Top-bar search.** `search.js` must index the 17 apps, `~/Notes` and
files via 18936, and Enter must open the result in the window manager. No
network calls.

**A8. Musica.** `musica.html` points at a `.wav` under the 18934 root. Prove
that file exists **in the image**; if it does not, point at a real file that
does and list it, never a 404.

**A9. The four 18934 iframes.** Prove in-image that `surfaces.html`,
`labs/molecules/index.html`, `index.html` and `logo-studio.html` return 200
and that the `#board-custos` anchor exists. Fix a dock target rather than
leaving a blank frame.

**A10. Provisioning.** Add the notesd unit + enable link, install the new
pages, keep `--root` mode working on a disk, and keep the live `check` rows
passing.

### Proof (required, pasted into the report)
- `bash /opt/face/proof_session.sh` still 9/9.
- New `os-build/face/app_proof.sh`: write a note → read it back → see the .md
  → trash → restore → edit-save → read, printing PASS/FAIL per row and
  exiting 1 on any failure.
- Install every changed file into `/tmp/metaos.ext4` and md5-compare repo vs
  image; list the md5s in the report.

### Report
`os-build/lanes/A_APPS_REPORT.md`: per item — what changed, the command, the
output excerpt, and one of PROVEN / INSTALLED / BLOCKED. Never write PROVEN
for something you did not run.

### Rules
No mock data as product, no `|| true` around a proof, no fabricated PASS, do
not boot QEMU, no git push. Timebox 4 h.

---

## LANE B — Agents that do work

You are working in `/Users/test/Desktop/meta-os`. One of four parallel agents.
You own the **agent relay** lane: a person must be able to give an agent an
order inside the OS and watch it actually run, with the log on screen.

### Read first
`agent-layer/README.md`, `os-build/AGENT_RUNTIME_REPORT.md`,
`agent-layer/RELAY_STATUS.md`, `os-build/INTEGRATION.md` links 11–14.

### Ground truth
- `agents/registry.json`: 23 entries, **16 live with a real `command`**, 7
  drafts with `command: []` (imperium-patrol + 6 Science Lab roles).
  `runtime.spawnAgent` resolves `repo:` prefixed commands against the payload.
- Jobs live on the board (`~/.local/state/oc2-agent/jobs/*.job.json`),
  results and a ledger beside them; `agents/watchman.mjs` polls it and spawns
  through `agents/runtime.mjs`.
- `metaosd.mjs` on 18940 serves `/status` and `/agents`; `agents.html` reads
  it. `meta-ask` (staged to `/usr/local/bin`) lists and submits jobs.
- Port **8935 is the Trio assessment queue**, not the agent board. Do not post
  agent jobs to it; it correctly refuses them.

### You own
`agents/**`, `agent-layer/**`, `os-build/iso/payload-agent/**`,
`os-build/face/agents.html`.

### You must NOT touch
Any other `os-build/face/*.html` or `*.py`, `os-build/face/provision.sh`,
`os-build/iso/**` outside `payload-agent`, `kiosk.sh`, `session.sh`,
`payload-theme/**`. No git reset/checkout/push.

### Build list

**B1. Capture every run.** `spawnAgent` must write
`runs/<jobId>/stdout.log` (+ stderr, exit code, start/end time, duration) with
timestamps, redacting any env value that looks like a key. Nothing truncated
to a teaser that hides the failure.

**B2. metaosd read API.** `GET /runs?agent=&limit=`, `GET /runs/<id>` (log tail
+ result + exit), `GET /ledger?n=`. Read-only, loopback only, no secrets. Keep
`/status` and `/agents` backward compatible — `proof_session.sh` checks them.

**B3. agents.html becomes a console.** Board from 18940, a submit box that
posts through metaosd to `agents/submit.mjs`, halt/resume buttons that write
`stop/<agent>.STOP`, and the selected run's log scrolling live (SSE endpoint
or a 2 s poll — pick one, do not hammer the port). Nothing renders from
hardcoded arrays.

**B4. The 7 drafts.** Either implement a real offline command for the 6
Science Lab roles (math/chem/bio/physics/hypothesis/statistician) that writes
real output to disk, or keep them draft with an explicit refusal shown in the
UI and by `meta-ask`. A stub that pretends to think is forbidden. State the
choice per agent in the report.

**B5. End-to-end proof, offline, in a chroot on the image.**
`meta-ask "<real order>" --agent watch` → job on board → `watchman.mjs --once`
spawns → `runs/<id>/stdout.log` has real output → result written →
`curl 18940/runs/<id>` shows it. Delete the test job afterwards; leave the
board empty.

**B6. Relay at login.** `oc2-watchman` must be a real user unit, enabled,
with heartbeat freshness recorded and a stale-heartbeat restart. Verify all
enable links resolve in the image.

**B7. Do not regress the semantics.** Budget ceiling, halt-holds-work,
retry-once, proposal rules stay. `node --test agents/*.test.mjs` must pass,
and the report quotes the summary line.

**B8. Honest degradation.** No SPARK key, no network: a job that needs either
must fail loudly with the reason in `stdout.log` and in the UI row, not sit
silent.

### Proof
`node --test agents/*.test.mjs`; the chroot end-to-end run above with the
actual output pasted; `meta-ask --list` showing live vs draft counts that
match the registry. Install changed payload files into the image and md5 them.

### Report
`os-build/lanes/B_AGENTS_REPORT.md`, per item: change, command, output,
PROVEN / INSTALLED / BLOCKED.

### Rules
No mocked agent output, no `|| true` proofs, no boot, no git push. Timebox 4 h.

---

## LANE C — Installable media

You are working in `/Users/test/Desktop/meta-os`. One of four parallel agents.
You own **the artifact**: the thing a judge can boot or install, built by a
script that runs again tomorrow.

### Read first
`os-build/iso/PIPELINE.md`, `os-build/iso/BASE_FACTS.md`,
`os-build/iso/README.md`, `os-build/tools/proof_boot.sh`,
`os-build/BOOT_ON_32GB_MAC.md`.

### Ground truth, including the trap
- The live image `/tmp/metaos.ext4` is **arm64** (aarch64) and is booted on
  this Mac with `qemu-system-aarch64 -M virt -cpu host -accel hvf`, direct
  `-kernel /tmp/meta-boot/vmlinuz -initrd /tmp/meta-boot/initrd.img`.
- `/tmp/xubuntu-base.iso` (5.2 GB) is **amd64** Xubuntu 24.04.5. The Calamares
  lane (`os-build/iso/build_iso.sh`, `calamares/**`) is built on it and has
  never been run end to end (`--check` is the only proven mode).
- **Do not ship two architectures.** Decide one and write the decision, with
  the reason, in `os-build/lanes/C_ISO_REPORT.md`. The working system is
  arm64; that is the one that boots tonight.

### You own
`os-build/iso/build_iso.sh`, `os-build/iso/*.sh` (except `provision-all.sh`
which lane D does not touch either — you may call it), `os-build/iso/calamares/**`,
`os-build/iso/finalize-iso-tree.sh`, `os-build/iso/repack-iso.sh`,
`os-build/iso/provision.sh`, `os-build/iso/merge-layers.sh`, new files under
`os-build/iso/` that you create, and `os-build/tools/proof_iso.sh` if you add it.

### You must NOT touch
`os-build/face/**` (lanes A and B own it), `os-build/iso/payload-theme/**`
(lane D), `os-build/iso/payload-agent/**` (lane B), `agents/**`,
`agent-layer/**`, `meta-live.py`, `kiosk.sh`, `session.sh`.

### Build list

**C1. Architecture decision, written down.** State which base and which arch,
and the hash. If arm64: obtain the official Ubuntu 24.04.x arm64 ISO, record
sha256 in `os-build/iso/BASE_FACTS.md`. If amd64: say plainly that the demo
image is arm64 and this artifact is a separate build, and why.

**C2. A build that runs to completion on this Mac.** `build_iso.sh` currently
needs `xorriso`/`mksquashfs` which the Mac lacks. Run it inside
`docker run --rm --platform linux/arm64 -v $PWD:/repo ... ubuntu:24.04` with
those packages installed, or add a containerised path to the script. Either
way the command must be one line in the report and must exit 0.

**C3. The ISO must carry Meta OS, not Xubuntu.** `--inspect` must show: the
kiosk session, `/opt/face` payload, the theme, autologin as `ubuntu`, the
Meta `.disk/info`, and the agent payload. Extend `--inspect` for anything it
does not already assert, and paste its output.

**C4. Boot the built ISO once, bounded.** `qemu-system-aarch64 -M virt` with
EDK2 (`QEMU_EFI.fd`) if that is what arm64 needs, `-display none`, monitor
socket, `screendump` polling with a hard timeout (≤ 300 s), VM killed on
exit, image untouched. Save capture to `os-build/captures/iso-<arch>-<UTC>.png`
and prove the framebuffer is not single-colour, same standard as
`proof_boot.sh`. This is a **boot** proof, not an install proof — say which.

**C5. An installer that works without Calamares.** If arm64 has no Calamares
packages, ship `os-build/iso/metaos-install.sh`: rsync the live rootfs to a
target disk, install the bootloader, set hostname/user, keep `/etc/metaos`.
Prove it against a **blank 8 GB qcow2**: install, then boot that disk and show
it reaches the shell. That is the only acceptable "installable" claim.

**C6. Reproducibility.** A `--rebuild` path that takes only the base ISO and
the repo, prints the output sha256, and fails if any required payload file is
missing. No hidden manual steps; if something must be manual, the script must
print it as a named step and exit non-zero.

### Proof
`--check`, the full build command, `--inspect` output, the ISO boot capture
path + non-single-colour line, and the install→boot capture for C5. Install
nothing into `/tmp/metaos.ext4` — this lane produces files, not disk edits.

### Report
`os-build/lanes/C_ISO_REPORT.md`: the arch decision, each item with command
and output, and PROVEN / BUILT-UNBOOTED / BLOCKED, named exactly.

### Rules
No claim of "boots" without a capture from a real boot, no timeouts over
300 s, always kill the VM, no git push. Timebox 5 h.

---

## LANE D — Boot to desktop is one product

You are working in `/Users/test/Desktop/meta-os`. One of four parallel agents.
You own **identity**: everything a person sees between power-on and the
spinning ribbon desktop, and everything that makes it not look like Ubuntu.

### Read first
`os-build/iso/payload-theme/README.md`, `os-build/iso/plymouth/**`,
`os-build/face/plymouth/**`, `metaos-theme/icons/ICONS.md`,
`os-build/WALLPAPER_BOOT_CHECK.md`.

### Ground truth
- The wallpaper is settled: `meta-live.py` (32 frames, 16 fps) as a systemd
  user unit with monitor geometry. Do not touch it or its frames.
- `os-build/face/kiosk.sh` and `session.sh` are settled. Do not touch.
- The visible palette is blue/black/white, the mark is the ASCII ribbon.
  Icons already exist under `metaos-theme/` and `os-build/iso/payload-theme/icons`.
- The image is `/tmp/metaos.ext4` (arm64 Ubuntu 24.04, user `ubuntu`).

### You own
`os-build/iso/payload-theme/**`, `os-build/iso/plymouth/**`,
`os-build/face/plymouth/**`, `metaos-theme/**`, `os-build/iso/payload-theme/apply.sh`.

### You must NOT touch
`os-build/iso/build_iso.sh`, `calamares/**`, `finalize-iso-tree.sh`,
`repack-iso.sh`, `iso/provision.sh`, `iso/provision-all.sh` (lane C calls your
`apply.sh`), `os-build/face/*.html`, `os-build/face/*.py`, `kiosk.sh`,
`session.sh`, `meta-live.py`, `agents/**`.

### Build list

**D1. The theme must actually land.** `apply.sh` must install icons, fonts,
GTK, xfwm4, panel, dock, terminal and greeter assets with absolute paths,
and refuse to run if a referenced asset is missing. Prove by running it
against the mounted image and comparing every referenced path.

**D2. Icons are complete, not decorative.** Every icon name used by the panel,
dock, `.desktop` launchers and file manager must resolve in the theme's
`index.theme`. Write a checker that walks the names and fails on a miss, and
paste its PASS line.

**D3. Plymouth: the ribbon spins during boot.** One theme, one owner. Reuse
the existing 32-frame ribbon at a plymouth-appropriate size (PNG sequence or
script plugin), meta blues only, no Ubuntu logo, no text cursor flash. Prove
what can be proven without a boot: `plymouth-set-default-theme` resolves to
`metaos`, the `.plymouth`/`*.plymouth` descriptors parse, the frame count and
fps match the animation module, and a contact sheet of the frames is written
next to the report. Say plainly that a boot capture is lane C's.

**D4. GRUB.** A theme file under `payload-theme/grub/` (lane C integrates it),
with `Meta OS 1.0` title, the mark, and a sane timeout. No `xubuntu`/`ubuntu`
strings.

**D5. Greeter.** LightDM greeter config/theme matching the desktop: mark,
blue field, the same font. Autologin for `ubuntu` must stay exactly as it is
(link 1 in `INTEGRATION.md`) — if you touch `lightdm.conf`, prove autologin
still says `autologin-user=ubuntu`, `user-session=metaos`.

**D6. Identity strings.** `/etc/os-release` → `Meta OS 1.0 (Ribbon)`, `ID=metaos`,
`PRETTY_NAME`; `/etc/issue`, hostname, and every `.desktop` `Name=` for the 17
dock apps. Then a scan: no `ubuntu`, `xubuntu`, `Xubuntu` on any **visible**
surface (allowlist the technical ones: apt sources, package names) — write the
allowlist and the scan into the report.

**D7. Fonts.** One monospace and one display face, licensed, installed and
referenced by GTK + terminal + greeter. If you add a font, record its licence
in the report; do not ship an unlicensed one.

### Proof
A `theme_proof.sh` under `os-build/iso/payload-theme/` that asserts, per row:
asset exists in the image, icon resolves, unit/config references an absolute
path, no forbidden brand string — printing PASS/FAIL and exiting 1 on a miss.
Install into `/tmp/metaos.ext4` via the docker mount, md5-compare, list md5s.
Do not boot; do not claim a boot visual.

### Report
`os-build/lanes/D_IDENTITY_REPORT.md`, per item: change, command, output,
PROVEN / INSTALLED / BLOCKED, plus the two allowlists (brand strings, fonts).

### Rules
No bright/party palette, no Ubuntu art left visible, no mock screenshots, no
`|| true` proofs, no git push. Timebox 3 h.
