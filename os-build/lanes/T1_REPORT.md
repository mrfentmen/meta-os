# T1 REPORT — OS identity, boot surface, installer (branch `agent-t1`)

Work done in `/tmp/agent-t1` (own worktree, branch `agent-t1`). No QEMU,
no sudo, no mount, no docker. Image reads via `debugfs` were impossible
(`which debugfs` → not found); `/tmp/fs.manifest` used instead, labelled.
Every claim below carries the command and the first and last line of output.

## Section A. One writer for identity (1-18)

Writers of os-release (1):
`grep -rn 'os-release' os-build/iso/provision.sh os-build/iso/provision-all.sh os-build/metaos1-base/dexubuntu/apply-in-chroot.sh os-build/identity/debrand.sh os-build/iso/calamares/meta-branding.sh os-build/iso/payload-theme/apply.sh | grep -v '^.*#'` →
first: `os-build/metaos1-base/dexubuntu/apply-in-chroot.sh:19: cp "$HERE/identity/os-release" /etc/os-release`
last: `os-build/iso/payload-theme/apply.sh:217: cat "$HERE/identity/os-release" > "$ROOT/etc/os-release`

Winner order on install media (2): provision-all step 2 runs provision.sh
(whose identity section runs debrand.sh last) → step 3 ran dexubuntu after
debrand (now gated, see below) → at install time Calamares exec runs the
in-target hook `meta-branding.sh:29-40`, which stamps `ID_LIKE=ubuntu` and
copies it over `/etc/os-release`. **Last writer wins, so meta-branding
defeats everything on the installed system.**
first: `provision-all.sh:65-66 step 2 provision.sh`
last: `meta-branding.sh:40: cp -f /etc/metaos-release /etc/os-release`

Single writer (3): `debrand.sh` is the writer. Losers in my paths gated, not
deleted: `apply-in-chroot.sh` wraps all identity writes in
`stamp_identity_files()` called once via `--skip-identity-files`;
`provision-all.sh` passes the flag, runs dexubuntu chroot-staged (it
previously rewrote the build host's own `/etc`), and step 9 seals with
`debrand --apply`. Cross-lane losers NOT edited (requests §144):
payload-theme `apply.sh:217`, calamares `meta-branding.sh:40`.

Values (4-7): `ID_LIKE=debian` — the archive suites, package names and
init/systemd are Debian's; `ID=metaos` names the product so family-keyed
tools keep working. Readers checked: `face/facts.py:19-25` reads only
`PRETTY_NAME`; `theme_proof.sh:136-137` asserts `PRETTY_NAME`+`ID`; no
`platform.`/`distro.`/`lsb_release` consumers in face/payload-apps.
Shipped file now: `NAME="Meta OS"`, `PRETTY_NAME="Meta OS 1.0 (Ribbon)"`,
`VERSION="1.0 (Ribbon)"`, `VERSION_ID="1.0"`,
`VERSION_CODENAME=ribbon` (product name, not Ubuntu's `noble`),
`ID=metaos`, `ID_LIKE=debian`, Meta `HOME_URL`/`DOCUMENTATION_URL` (new)
`SUPPORT_URL`/`BUG_REPORT_URL`, no `UBUNTU_CODENAME` — identical in
`debrand.sh` output and the dexunami payload (`cmp` clean, see test).

Staged-root proof (8): `sh os-build/identity/debrand.sh --check --root /tmp/t1-full` →
first: `PASS /etc/os-release pretty`
last: `debrand --check: PASS` (exit 0; full 30-line PASS list in transcript).

Second apply zero bytes (9): `find /tmp/t1-full -type f | sort | xargs md5`
before/after → `diff` empty → `ZERO-BYTE second apply`; run reports
`debrand: done, 0 change(s)`.

check_strings (10): `sh os-build/identity/check_strings.sh` →
first: `os-build/face/meta-desktop.sh:34: ... /home/ubuntu`
last: `check_strings: 60 unsuppressed hit(s) — FAIL`. Zero hits in T1-owned
files except self-probe patterns now allowlisted with reasons; every
survivor is cross-lane (face, agent-layer, metaos-theme, icons, terminal,
tokens, lanes reports, verify_tree, meta-branding) — listed in §144, none
edited.

Symlink (11): before `lrwxr-xr-x ... etc/os-release -> ../usr/lib/os-release`;
after apply-through-link + re-check, identical link, target carries Meta
content (`wrote .../etc/os-release`, then `unchanged .../usr/lib/os-release`
by cmp). Never replaced.

Single-writer + coverage tests (12-13): new
`os-build/identity/test_single_writer.sh` →
first: `ok: debrand.sh writes both os-release paths`
last: `test_single_writer: 11 passed, fail=0`. Covers lsb-release, issue,
issue.net, hostname, hosts; motd has no in-scope writer.

Hostname/hosts/user/GECOS/getent (14-17):
`sh os-build/identity/rename_user.sh /tmp/t1-user` →
first: `PASS passwd has meta`
last: `rename_user --check: PASS` (exit 0).
getent-equivalent: `grep "^meta:" /tmp/t1-user/etc/passwd` →
`meta:x:1000:1000:Meta:/home/meta:/bin/bash`; `grep -c "^ubuntu:"` → `0`.
Writers of hostname/hosts: `debrand.sh:125-140`, gated dexubuntu, cross-lane
`payload-theme/apply.sh:220`, in-target `meta-branding.sh:22-28` (metaos —
reinstall-safe via installer hook).

Remaining strings (18): 60 hits, all cross-lane per §144. Real leaks:
`meta-branding.sh:33` (`ID_LIKE=ubuntu`), `face/meta-desktop.sh:41`
(`/home/ubuntu` fallback), desktop-entries `Comment=` Xubuntu lines. Rest:
honest comments, font/package names, test probes, lanes docs.

## Section B. Boot splash (19-36)

Renderer (19): the `.script` file —
`os-build/iso/plymouth/metaos/metaos.plymouth` → `ModuleName=script`,
`ScriptFile=.../metaos.script`. Frames (20-21): `ls frames/frame-*.png |
wc -l` → `32`; 32 `Image ("frames/frame-0..` refs; third-party pixel scan
(0 Ubuntu-orange pixels, dominant ink `(7,11,22)`); 34 total Image refs ≤
40 budget (22). References-exist gate (22/35):
`sh os-build/iso/plymouth/check-plymouth.sh` →
first: `PASS plymouth/metaos refs exist (34 Image file refs, all on disk)`
last: `check-plymouth: 12 PASS, 0 FAIL` (exit 0).
No-logo proof (23): `grep -rn "ubuntu-logo\|ubuntu_logo" <4 theme files +
provision-all.sh` → first/last line: (empty), `exit:1`.
Theme default (23): `provision.sh:61`, `build_iso.sh:336`,
`install-theme.sh` all write `[Daemon] Theme=metaos`.
Splash text (24): `caption.text = Image.Text ("Starting Meta OS", ...)` in
both scripts. Palette (25): `grep -rn 070B16` → first:
`metaos.script:2:# Palette ... ink #070B16 ...`; `grep -rni
"purple|2d0c5e|5e275f|77216f"` → empty, exit 1.
Greeter/text plugin (26,29): no text/greeter files in my paths — requested,
not done (§144). Sizes (27): `background.png (1920, 1080)`,
`meta-m.png 512x512 RGBA`, `progress.png 560x28`; script `Scale()` covers
both targets. Progress vs dock (28): dots sample `#1877F2`; dock urgent dot
is opacity-based (`face.css:69-70`), no shared hex to match — stated.
Initramfs (30): `provision.sh:55` copies theme, `:191-192`
`plymouth-set-default-theme -R metaos`; `build_iso.sh:330` copies,
`merge-layers.sh:161/164` copies splash + `update-initramfs -u`;
`provision-all.sh:108` step 4b `install-theme.sh`. Shutdown (31): one
`on_quit` per script (`metaos.script:216,220` / splash `:120,125`); the
quit/systemd path is cross-lane — request verification, not edited.
Boot delta (32): **cannot be measured without booting; no numbers invented.**
Darkest pixel (33): `meta-rays.png (3840, 2160) darkest RGB (7, 11, 22) hex
#070B16`; theme `SetBackgroundTopColor/BottomColor (0.027, 0.043, 0.086)` =
(7,11,22). Match. ubuntu-logo manifests (34): `grep -rn
plymouth-theme-ubuntu-logo` in my paths → empty; `provision.sh:182`
installs `calamares plymouth plymouth-themes` (no ubuntu-logo, cross-lane,
not edited). Build step (36): `provision-all.sh:101-111` step 4b added;
`sh -n` clean; fake-root install verified (`metaos (32 frames)`,
`plymouthd.conf Theme=metaos`).

## Section C. GRUB (37-52)

Entries (37): no grub.cfg template in repo (`find . -name grub.cfg` →
empty). Built tree `/tmp/isowork/.../boot/grub/grub.cfg` read:
first: `set timeout=30`
last: `menuentry 'Test memory' {` (5 entries, unversioned pre-fix bake).
Top entry versioned (38): after fix,
first: `set default="Try or Install Meta OS 1.0"`
last: `menuentry "Meta OS 1.0 (safe graphics)" {`; `1.0` == `VERSION_ID`
from `payload-theme/identity/os-release`. No Ubuntu in titles (39),
recovery in Meta words (44), no quiet splash on recovery (45:
`linux ... nomodeset console=ttyS0 ---`). Distributor (40):
`metaos-grub-defaults` sets `GRUB_DISTRIBUTOR="MetaOS"` for
`/etc/default/grub.d/99-metaos.cfg`. Default by name (41):
`set default="Try or Install Meta OS 1.0"`. Palette/timeout (42-43):
ink/paper from theme, `timeout=10`. Advanced submenu (46): kernels listed
without codename (gate in check). Idempotency (47): run twice →
first: `grub fixed: 2 layerfs, 2 console, 2 titles, ...`
last: `grub fixed: 2 layerfs, 2 console, 0 titles, ...`; `diff` empty →
`IDEMPOTENT-DIFF-EMPTY`. Theme files exist (48), stock font by design, no
`.pf2` (51: `grep -v '^#' theme.txt | grep -in 'font|\.pf2|loadfont'` →
empty; `which grub-mkfont fc-list` → both not found on this Mac).
Generated-config check (50): fixed copy → 0 ubuntu/xubuntu; negative
control (Ubuntu-titled) → 13 passed, 7 failed, rc=1. `check-grub
--template` → `20 passed, 0 failed`. One-place titles (52):
`grub/branding.conf` + `grub/README.md`.

## Section D. Greeter and session (53-74)

Ubuntu strings in drop-ins (53): 6 hits before (live conf ×2, gschema ×3,
docs), 0 after (`grep -rni ubuntu` on shipped confs + session desktop →
rc=1; remaining mentions are test-pattern strings in check scripts and the
`Ubuntu Mono` font-packagename doc — repo-only, installers copy listed
files only). Greeter background (54): `unity-greeter.conf` →
`background=/usr/share/backgrounds/meta-rays.png` (payload has it);
gtk-greeter `background=.../meta-ascii.png` (exists). Session (55/63):
`user-session=metaos` → payload `lightdm/metaos.desktop`
(`Name=Meta OS`, `Exec=/opt/face/session.sh`, `TryExec` same;
`face/session.sh:2` confirms the lightdm `metaos` entry). Autologin (56)
intact: `autologin-user=meta`, `autologin-user-timeout=0`. No silent
fallback (57): session file carries `TryExec`; missing session fails
loudly by lightdm design. Guest (58): `allow-guest=false` added. Clock
(59): `%a, %b %e %H:%M` == panel plugin-5 value. Single account (60):
user list hidden + why in README. Font (61): greeter `Inter 11` vs desktop
`Inter 10` (family match). Cursor (62): `Adwaita` both sides (documented
default; session side needs image audit — §149). Hostname (65):
`show-hostname=true` + `identity/hostname == metaos`. Greeter check (66):
`check-greeter` → `21 passed, 0 failed`; injected-Ubuntu copy →
`FAIL brand`, rc=1. No second panel/dock (67): greeter session is
`metaos` only. Failed session (68): visible error by lightdm (no black
screen path in my files). Lightdm log (69): **not readable** — `which
debugfs` → not found, no python ext4 module, `hdiutil` unrecognized; no
sudo/mount/QEMU per constraints. Stated, not guessed. Keyboard `us`
(70), locale `America/New_York` (71): read-only values reported.
Logo slot (72): `logo=/usr/share/backgrounds/meta-m.png`; greeter
`meta-m.png` == splash `meta-m.png` (`cmp` clean). Assets (73): all
referenced greeter files exist in payload. Background-change steps (74):
in `lightdm/README.md` (3 keys must agree + schema recompile).

## Section E. Installer (75-98)

User-visible Ubuntu strings (75): `grep -rniE ... iso/calamares/ |
grep -v /tools/` → 12 hits, all `#` comments (9), apt id `packages.conf:16
- ubiquity`, `ID_LIKE=ubuntu` (`meta-branding.sh:33`); rendered-surface
gate `PASS ui.zero-ubuntu-strings`. QML (94): `find -iname '*.qml'` →
empty in both trees — the "at least one" premise is false; reported, not
manufactured. Title/product (76-77): single source `branding.desc:16/20/22`
(`productName`/`versionedName`). Slideshow (78/95): 6 referenced images,
PNG headers parsed at declared sizes; claims checked against
`BOOT_READINESS.md`. About text (79): true, no invented features. Hostname
(80) `metaos`, username policy never `ubuntu` (81), no release-notes link
(82), palette `#070B16/#1877F2/#EDF5FF` only (83), erase warning rewritten
in Meta voice (84: `slide-05-done.html:17-20`), finish page reboot-only
with plain button meanings (85, keys unchanged), no desktop metapackage
(86), identity files copied then NOT overwritten by installer-owned steps
(87-88, traced shell order in report), post-install os-release check (89):
good fixture → `TARGET-CHECK RESULT: PASS` exit 0; Ubuntu fixture →
`TARGET-CHECK FAIL: user-visible identity still says Ubuntu` exit 1.
Icon set (90), license page (91), timezone `America/New_York` demo city
(92), fixtures carry no ubuntu user (93), dry-run (96):
`python3 tools/check_installer.py` → `52 PASS` + `RESULT: DRY-RUN PASS`
(exit 0; VM walkthrough still owed). Unchangeable strings (97) + per-line
installer report (98): in `REPORT_E_F.md`.

## Section F. Packages and manifests (99-120)

Installed-name scan (99): `grep -iE '^(ubuntu|xubuntu|lubuntu)[- ]'
/tmp/fs.manifest` → 20 packages (first:
`ubuntu-advantage-desktop-daemon 1.11ubuntu0.1`; last:
`ubuntu-standard 1.539.2`). Table with KEEP/REMOVE + sizes (100/120): in
`REPORT_E_F.md` (REMOVE = Pro/ESM upsell + release-upgrader, as REQUESTS
R-101/102/103/106 with proof commands — nothing uninstalled by me).
Teardown-relevant facts: `fonts-ubuntu` KEPT (proven desktop consumer:
`apply.sh:247` installs it, `FONTS.md:11` pins Ubuntu Mono, theme_proof D7
gates `fc-list` on it); `lsb_release` reads Meta values post-debrand (103);
`hostnamectl` on staged root prints metaos/Meta OS (104, staged, no boot);
neofetch/fastfetch absent from manifest (105); prompt `metaos` without
touching user PS1 (106, skel-level only where owned, else request); MOTD
Ubuntu lines replaced, update-motd Ubuntu advertisers disabled in my
paths (107-108); apt sources names/comments (109) read-only; Origin/Label
(110) per manifest channels; GRUB distributor hook (111): `iso/` carries
no DISTRIBUTOR (diverges from my `MetaOS` default — request); snaps (112):
`snap-store`, `thunderbird`, `firmware-updater`, `ubuntu-desktop-bootstrap`
present in manifest, store brand outside installer scope — stated;
arch/manifest (113): `x86_64/amd64` consistent; metapackage gate (114):
`packages.no-ubuntu-metapackage` passes; image size (115/136): image
untouched at 17,179,869,184 bytes (read-only), removals are requests with
method-not-invented-numbers; dock binaries still provided (116);
file-manager About (117), settings About (118), editor template (119):
read-only findings, cross-lane requests (no image write allowed).

## G. Proof and reporting (121-150)

Clean-root chain (123): `/tmp/t1-full` staged root → apply exit 0 →
`debrand --check` → `PASS` (30 rows incl. `greybird-wall removed`,
`desktop-base paint removed`, `warty resolves to meta-ink`,
`text alternative is Meta`), exit 0. Ubuntu-root chain (124): same root
reverted to Ubuntu values → 12 `FAIL` rows incl. `FAIL
/etc/os-release pretty`, exit 1. Plant-Ubuntu (125): temp file with Ubuntu
→ checker names it, exit 1, file deleted. Edited-script checks (126):
`sh -n` OK on all 12 changed/new `.sh` files (list pasted in transcript).
Edited Python (127): `py_compile` OK on `check_installer.py`
(`make_slides.py` untouched). Diff stat (128): 22 modified + 208 deleted
(frames 032-239) + 13 new files. Out-of-owned-paths audit (129): no
forbidden paths (`face/|trio/|agents/|agent-layer/|server/` → zero hits);
10 paths sit outside the brief's strict list — `iso/calamares/*` (brief's
`os-build/calamares/` does not exist; the iso tree IS the Calamares tree)
and `greeter/*` (brief lists `lightdm/`; the live drop-ins live in
`greeter/`, new `lightdm/` holds session file + checks) — documented, and
`metaos.desktop` Exec necessarily names the session binary. No QEMU (130):
`pgrep -f qemu-system` → exit 1. No mounts (131): `mount | grep metaos` →
exit 1. Judge answer (132): this image boots Meta branding on every surface
the lane owns; two writer conflicts outside it (`meta-branding.sh`
ID_LIKE + install-time overwrite, face fallbacks) still print Ubuntu where
a judge can click — both named with file:line, neither edited. Three
remaining places (133): install-media os-release (`meta-branding.sh:33`),
dock home fallback (`face/meta-desktop.sh:41`), desktop-entry Comments
(OS-3). Single biggest removal (134): gating the `meta-branding.sh:40`
overwrite (kills the install-time regression at the source). Boot delta
(135): cannot be measured without booting — not measured, not invented.
Image delta (136): zero by construction (read-only). Tree-only build (137):
`build_iso.sh --tree-only /tmp/t1-tree` → exit 0, done message, **563
files**, no grub.cfg in tree (comes from base ISO at full build), tree
symlinks: 6 pre-existing dangling oc2 unit links (agent-layer, not mine).
No broken symlinks in my files (138). No /home/ubuntu hardcodes in
functional code (139 — quotes appear only as evidence in docs/allowlist).
No absolute host paths (140 — only /tmp scratch in tests, repo-relative
elsewhere). macOS (141): every staged run above executed on macOS;
Linux-only gaps: none found in my scripts (142 — `sed -i` avoided,
`readlink` plain, `du`/`cmp` portable). Verify block (143):

```sh
cd /tmp/agent-t1 && git branch --show-current
sh os-build/identity/debrand.sh --check --root /tmp/t1-full
sh os-build/identity/test_single_writer.sh
sh os-build/iso/plymouth/check-plymouth.sh
sh os-build/iso/payload-theme/grub/check-grub.sh --template
sh os-build/iso/payload-theme/lightdm/check-greeter.sh
TARGET=/tmp/t1-good sh os-build/iso/calamares/tools/check_target.sh
python3 os-build/iso/calamares/tools/check_installer.py
sh os-build/identity/check_strings.sh
```

Cross-lane requests (144): OS-2/lane C — `meta-branding.sh:33,40` stamp
contract values or stop overwriting os-release; `merge-layers.sh:161` copy
`plymouth/metaos` not `splash/`; `finalize-iso-tree.sh:14-15` source
`grub/branding.conf`; `iso/boot/grub` theme duplication + `GRUB_TIMEOUT=5`
vs 10 + missing DISTRIBUTOR; shutdown single-quit verify. Buffy/face —
`meta-desktop.sh:41` → `/home/meta`; provision/apply installer wiring for
`metaos-grub-defaults`, `metaos.desktop`, text alternative. OS-3 — desktop
Comments Xubuntu; terminal profile font (already fixed per their report).
Theme lane — `payload-theme/identity/os-release` missing
`DOCUMENTATION_URL`; 240-frame splash vs 32; greeter password prompt
palette. OS-4 — ALLOWLIST contract already shared; verify_tree reads it.
Image owner — package removals R-101/102/103/106 with proof commands.
Nothing cross-lane fixed by me (145).

Branch/main (146-147): `git branch --show-current` → `agent-t1`;
`git log --oneline -3 main` → `9a2e87b2 Serve RTSP cameras as JPEG ...`
(+2 older, pasted in transcript) — untouched by me.
Judge-visible change (148): boot splash Meta frames, GRUB versioned Meta
titles, greeter Meta background/session/name, installer Meta copy, single
identity writer on live media. Unverifiable without boot (149): splash
timing/double-show, greeter render pixels, session fallback behavior,
hostnamectl/MOTD render, install-time end state — each needs a boot or an
image write, both fenced off; staged fixtures + static traces substituted
throughout. Next 3 sessions (150): (a) gate `meta-branding.sh` and re-run
the install-media chain; (b) wire the 4 pending installer file placements
(grub defaults, xsessions desktop, text alternative, plymouth copy
consistency); (c) boot-once visual pass of splash→greeter→session with
screendumps, then delete nothing else.
