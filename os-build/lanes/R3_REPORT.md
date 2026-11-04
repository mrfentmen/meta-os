# R3 identity lane report — OS identity lead (branch `agent-r3`)

Date: 2026-11-04. Worktree: `/tmp/wt_land`, branch `agent-r3` (cut from local
`main` @ `a6e1a9c6`). Main frozen: no merge, no push, no rebase. No QEMU,
no mounts, no sudo writes to a live image anywhere below — static proof +
scripted dry-runs only.

Nine subagents (sections A–I) ran read-only audits; the lead verified every
claim below by re-running the commands and then applied the edits listed in
§10. A subagent claim without a pasted command + output is not evidence —
every command in this report was run by the lead in `/tmp/wt_land`.

## Definition-of-done status

- `check_strings.sh` exits 0 with a justified allowlist: YES.
- `verify_tree.sh` table with no unexplained FAIL: YES — 6 PASS + 2
  `absent (owned by OS-3)` (missing checkers are reported, never passed).
- Six user-visible artefacts each with before/after proof: YES (§9).
- This report complete: YES.

```
$ sh os-build/identity/check_strings.sh; echo "CS_EXIT:$?"
check_strings: clean — PASS
CS_EXIT:0
```

```
$ sh os-build/tools/verify_tree.sh; echo "VT_EXIT:$?"
check | result | detail
allowlist | PASS | os-build/identity/ALLOWLIST.tsv present with 323 non-empty lines
identity-strings | PASS | check_strings: clean — PASS
launcher-allowlist | absent (owned by OS-3) | agent-layer/desktop-entries/selftest.sh not present yet
desktop-entries | absent (owned by OS-3) | agent-layer/desktop-entries/check_desktop.sh not present yet
tree-refs | PASS | 22 .desktop files: Name+Exec present, absolute icons resolve
no-ubuntu | PASS | no case-insensitive ubuntu in shipped sources
home-refs | PASS | no :-/home/ubuntu default in face/iso launch code
os-release-identity | PASS | 2 shipped os-release files: ID=metaos, no ubuntu
VT_EXIT:0
```

(`verify_tree: 8 rows` on stderr, no `DEAD` line. `--json` mode returns the
same 8 rows as pure JSON, exit 0. `test_check_strings.sh`: `3 passed,
0 failed`, exit 0.)

## A. Identity / os-release (tasks 1–22)

Writers found (all verified with `grep -rn "etc/os-release"`):
`os-build/identity/debrand.sh:106-107` (canonical, contract
`ID=metaos/ID_LIKE=debian`), `os-build/iso/payload-theme/apply.sh:217`
(clobbers `/etc/os-release` via `>`), `os-build/metaos1-base/dexubuntu/
apply-in-chroot.sh:19-20` (hardcoded `/`, no `$ROOT`),
`os-build/iso/calamares/meta-branding.sh:37-40` (last writer on installed
media). Readers: `os-build/face/facts.py:19`,
`os-build/iso/payload-theme/apps/metaos-welcome.py:88`,
`os-build/face/session.sh:96-105` — all read-only, correct as-is.

Fixes applied (cross-lane requests R1–R2 filed, §11):
- `meta-branding.sh` heredoc now stamps the contract
  (`NAME="Meta OS"`, `VERSION="1.0 (Ribbon)"`, `VERSION_CODENAME=ribbon`,
  `ID=metaos`, `ID_LIKE=debian`, `LOGO=metaos`, metaos.local URLs) and backs
  up the base flavour only once (`[ ! -f ...base-flavour ]`).
- `dexubuntu/identity/os-release` rewritten to the contract, byte-identical
  to `payload-theme/identity/os-release` (`diff` exit 0); dex
  `lsb-release` moved to `ribbon` / `Meta OS 1.0 (Ribbon)`;
  `apply-in-chroot.sh` issue/issue.net/motd printf lines moved from
  `MetaOS 1.0` to `Meta OS 1.0 (Ribbon)`.
- No package needs `ID_LIKE=ubuntu`: zero in-tree consumers reference it;
  `ID_LIKE=debian` preserves the noble-apt compat layer (static proof —
  live `apt-cache rdepends` not run, no image: NOT RUN, §12).
- Remaining `/etc`-shipped `ubuntu` hits are font-package names and gate
  probes, each allowlisted with owner/reason; `dpkg/origins`,
  `unattended-upgrades`, `sources.list.d` untouched by every lane (verified
  zero hits outside docs); `GRUB_DISTRIBUTOR` is unwired (request R9).

Repro (lead-run, verbatim excerpts):

```
$ diff os-build/metaos1-base/dexubuntu/identity/os-release os-build/iso/payload-theme/identity/os-release && echo IDENTICAL
IDENTICAL
$ grep -rn "GRUB_DISTRIBUTOR" os-build/ --include="*.sh" | head
(empty — only theme.txt comments name it; request R9)
```

## B. Wallpapers / Plymouth / splash (tasks 23–40)

- Inventory: 4 static wallpapers
  (`meta-ascii/meta-dawn/meta-dusk/meta-rays.png`, hashes §9) + live
  `meta-loop.mp4` + 240-frame `studio-loop`; greeter copies are byte-identical.
- No spiral/swirl/ubuntu/debian/warty/emerald FILES ship anywhere:

```
$ find os-build/iso/payload-theme os-build/iso/plymouth os-build/iso/splash metaos-theme \
  -iname "*spiral*" -o -iname "*swirl*" -o -iname "*ubuntu*" -o -iname "*debian*" | grep -v logs
(empty=none)
```

  Remaining `swirl/spiral` mentions are provenance comments (Debian base art
  being replaced), allowlisted as upstream-notice where the string gates
  require it.
- Green wallpaper: none ships. Measured centers (PIL 11.3.0):
  `meta-ascii #070B16`, `meta-dawn #124C9C`, `meta-dusk #0A162E`,
  `meta-rays #0B2346` — all ink/blue, no green. The "green" frame users saw
  is the base image's `emerald #05475C` desktop-base fallback, replaced by
  the desktop-base art override (see `provision.sh:213-262` trace in §H).
- Plymouth: ours is `os-build/iso/plymouth/metaos` (240 frames, 480×272,
  `Theme=metaos` in `plymouthd.conf` writers `apply.sh:106-107`,
  `provision.sh:59-63`, gated by `debrand.sh:318-320`). No ubuntu/debian
  theme dirs ship; target-side removal of `ubuntu*` dirs is
  `debrand.sh:157-160`. Frame palette proof (T1-style):

```
PLYMOUTH FRAMES darkest pixel (sample 8 of 240):
  total frames: 240
  frame-000.png darkest=#050B1B
  frame-120.png darkest=#040B1B
  frame-238.png darkest=#070B16
palette refs: ink #070B16 blue #1877F2 paper #EDF5FF
```

  (darkest pixels within ±2 LSB of ink; dominant buckets near-black/navy —
  ink backdrop + blue ribbon, no teal/orange outlier).
- GRUB theme (`theme.txt`): `title-text "Meta OS 1.0"`, no purple, no logo
  bytes; greeter points at `meta-ascii/meta-rays/meta-m.png`; no slideshow,
  no hint text; lock art follows `login/background.svg`.

## C. Desktop / panel / menu (tasks 41–60)

- Whisker: shipped panel XML uses classic `applicationsmenu` titled `Meta`
  (`panel/xfce4-panel.xml:50-51`); no whisker config ships in this tree.
- `.desktop` Comments: clean —

```
$ grep -rni "ubuntu\|xubuntu" os-build/iso/payload-theme/apps/*.desktop \
  os-build/iso/payload-theme/apps/dock/*.desktop agent-layer/desktop-entries/*.desktop metaos-theme/apps/*.desktop
(exit 1, no output)
```

- `meta-desktop.sh:379-384`: default `CALC_BIN=galculator` with mate-calc
  probe; `APP_MATRIX.md:55` proves galculator absent / mate-calc 1.26.0
  present; dock launcher already `Exec=mate-calc`. Stronger fix (flip the
  default) is request R4 — not applied unilaterally.
- Font: `provision.sh:376` and `metaos-terminal-profile.txt:20` both
  `FontName=Monospace 11` (before: `Ubuntu Mono 11` — the worktree already
  carried this fix uncommitted; verified no `Ubuntu Mono` remains in either
  file). `theme_proof.sh:189` still asserts `^FontName=Ubuntu Mono 11` —
  contradiction, request R5, not "fixed" from this lane.
- `/home/ubuntu`: only the last-resort probe `meta-desktop.sh:41`
  (getent + `/home/meta` win first); comment `:34` reworded so it no longer
  teaches the old name; probe line allowlisted as compat. Stronger fix
  (drop the fallback) is request R3.
- `provision.sh:287` Xubuntu comment reworded to `stock base-image`.
- Locale/keyboard/timezone, power policy, notifyd, settings-manager title,
  polkit vendor, apport autostart: no strings ship from this lane's files;
  all are ISO-build-lane owned — requests R9, verified by empty greps (see
  section-C evidence in working notes; representative:
  `grep -rn -i "apport\|whoopsie" os-build/face/ os-build/iso/payload-theme/`
  → no output).
- `facts.py` is correct as-is — deliberately NOT touched.

## D. Installer / first boot (tasks 61–78)

- `branding.desc`: `MetaOS 1.0`, no Ubuntu strings; slideshow is 5 Meta HTML
  pages + 3 PNGs, no QML, no Ubuntu/Debian mentions (`find ... -name
  "*.qml"` empty); `finished.conf` has no URLs; welcome app
  (`metaos-welcome.py`) is Meta-named, no telemetry/opt-in (411 lines read).
- `users.conf`: `meta`/`Meta User`, `doAutologin:false`,
  `allowWeakPasswords:false`; no ubuntu group; partition labels
  (`EFI/ext4`) generic.
- `check_target.sh` does not exist (verified `find` empty) — 10 proposed
  rows with exit codes are specified in §12, file creation left to the ISO
  lane (request R10).
- `debrand.sh` has NO sentinel/first-boot mode (verified grep) — it runs at
  build time via `provision.sh:279-284` with `--check` after. Idempotence
  proven in a /tmp sandbox (run1: 11 changes; run2: 0 changes, exit 0).
  Gated-first-boot unit is a proposal, not implemented (NOT RUN on live
  image — no rootfs on this host).
- `rename_user.sh` has no pre-existing-`meta` guard (verified by read) —
  one-line guard proposed, not applied (request R10).
- Cross-lane: `merge-layers.sh:99-102` transplants base `etc/casper.conf`
  verbatim (USERNAME rewrite missing); xubuntu branding packages are purged
  only on the dexubuntu path (request R6).

## E. Packages that pull Ubuntu in (tasks 79–96)

Static inventory (no image; `dpkg`/`apt-cache` absent on this host — NOT RUN):

```
$ which dpkg dpkg-query apt-cache
dpkg not found / dpkg-query not found / apt-cache not found
```

- Only `ubuntu-`-prefixed tokens in repo lists: 4× `xubuntu-*` purge names
  (`apply-in-chroot.sh:36`) + `ubuntu-minimal` compat warning
  (`identity/README.md:11`). Pool `iso-filelist.txt` 121 `*ubuntu*` lines
  are version suffixes, not package names.
- Classification: removable (`advantage-tools`, `release-upgrader`,
  `ubuntu-wallpapers`, `ubuntu-sounds`, `ubuntu-report`,
  `popularity-contest`, `apport/whoopsie`), keep (`ubuntu-minimal/standard`
  metapackages, `fonts-ubuntu` compat, `initramfs-tools`, `casper`,
  `user-setup`), conditional (`ubuntu-drivers-common`, `snapd`).
- Removal script with `--dry-run` + dependency diff drafted and dry-run in
  /tmp (23 candidates → 4 listed-in-tree vs 19 inherited-from-base needing
  target `apt-get purge -s`); removals NEVER executed (NOT RUN on image).

## F. Strings / docs / licenses (tasks 97–112)

Fresh inventory (checker scope: `git ls-files`, minus plan/logs/node_modules,
case-sensitive whole-word):

```
Ubuntu: 335 (tree-wide) — checker-unsuppressed after allowlist: 0
```

Final verdict: `check_strings: clean — PASS`, exit 0 (was 62 unsuppressed).
Every remaining hit class: license/compat/upstream-notice or fix. No fourth
category. User-visible fixes applied: meta-branding ID_LIKE, dexubuntu
os-release/lsb-release/issue/motd, meta-desktop comment, provision comment,
payload README font line. Everything else is a gate probe string, a real
font/package name, or a lane evidence report quoting a leak — one allowlist
row each with an owner/reason (ALLOWLIST.tsv now 323 non-empty lines, every
row 4-column verified with `awk -F'\t' 'NF!=4'` → no output).

- No man pages in tree (`git ls-files | grep -E '\.(1|5|7|8)$'` empty).
- `/usr/share/doc` untouched by every lane script (verified grep) — legal:
  licenses stay.
- Doc-count contradictions recorded, not hidden: HACKATHON dock-tile claim
  (27) vs measured `grep -cE '^\s*add_app '` = 24 vs APP_INVENTORY 19;
  APP_MATRIX vs manifest; `payload README:66` galculator pointer is stale
  (file is 33 lines, calculator docs name mate-calc) — requests R7.
- `plan/TRIO_GAPS.md`: trio pages are clean (`grep -ri ubuntu trio/` empty);
  no identity change required from that doc.

## G. Apps / assets (tasks 113–132)

- `verify_tree.sh` `tree-refs`: 22 `.desktop` files, Name+Exec present,
  absolute icons resolve — PASS (verbatim in gate table).
- Trio tiles: absent by design (only 3 payload apps ship;
  `meta-desktop.sh:399-401` writes police/fire/ems at login). No action.
- 3D map band: NOT fixed (Buffy owns trio). Measured: `ignis.html:147`
  grid row is **284px**, not 283; `map3d.js:32` pitch 46. Request R8 filed;
  trio untouched by this lane.
- Icons resolve (`controls/imperium/help-about` all present); `FONTS.md`
  Ubuntu rows are compat (real package names); terminal no longer references
  Ubuntu Mono but the image still installs `fonts-ubuntu` (image-lane call,
  request R5).
- `board/board.mjs:552-553` binds all interfaces (no `127.0.0.1`) while
  face/trio services bind loopback — request R8 (board lane).
- No `/healthz` on face py services (18931/2/36/37) or ptyd (18933);
  Board has `/health`, trio `/api/health` — request R8 (face runtime lane).
- Legacy `relay` messaging refs removed (receipts in tree); residual
  `relay*` UI strings in `face/agents.html`/`start.html` are renames for the
  face lane (request R8).
- No remote CDN in shipped surfaces (only archived `imperium/` fixture
  references cartocdn, not installed — verified); no dead logo-studio links
  (only the two removal lines reference them).
- Headless render proof (one page per app PNG + font-load assert): NOT RUN —
  no chromium/rsvg/playwright on this host (`which` failures recorded in
  working notes).

## H. Boot chain proof (tasks 133–143, file trace only — no boot)

`grub-fix.sh:8-12` → cmdline (`quiet splash` + `console=ttyS0`,
`layerfs-path`) → `provision.sh:59-64` (`plymouthd.conf` Theme=metaos) →
`metaos.plymouth` + 240-frame script → greeter drop-ins
(`lightdm-gtk-greeter.conf`, `10-metaos-live.conf` autologin-user=meta,
`90-metaos.conf` blanking on installed system, two gschema overrides) →
session (`session.sh:228 exec startxfce4`; NO xsessions file is ever written
— verified `grep -rn xsessions` finds only the reader at `session.sh:109`;
request R9) → autostart order (services before apps per unit
`After=` + `session.sh` sequencing) → wallpaper (livebg paints first frame
synchronously; static fallbacks dangle at the never-installed
`meta-wallpaper.png` — request R9).

Not provable without a boot (§H140, each with reason): GRUB menu rendering,
effective `/proc/cmdline` (incl. untouched `xubuntu.seed` preseed arg),
plymouth actually displaying, greeter actually drawn, session selection,
autostart timing, first-frame paint race, runtime resize paint, welcome
window lifecycle, installed-system Calamares path. One-command hardware
checklist provided:

```
grep '^Theme=' /etc/plymouth/plymouthd.conf; ls /usr/share/xsessions/ | head;
ls -l /opt/face/kiosk.sh; readlink /etc/alternatives/desktop-background;
systemctl --user is-active metaos-livebg.service; cat /proc/cmdline
```

## I. Verification (tasks 144–150)

- New checks added to `verify_tree.sh` (8 rows total): `home-refs`
  (no `:-/home/ubuntu` default in face/iso launch code) and
  `os-release-identity` (both shipped os-release files: `ID=metaos`, no
  ubuntu) — both PASS (table above). Proposed further rows
  (scripts-executable, checker-selftest, allowlist-sync, autologin/font/
  desktop/grub/calculator consistency) documented for OS-1/OS-4, not added
  (keep the gate minimal before submission).
- Branch diff: `git diff --stat main...HEAD` — branch `agent-r3` was cut
  from local main; all work is unstaged (20 files). Lane files touched:
  `identity/check_strings.sh`, `identity/ALLOWLIST.tsv`,
  `identity/test_check_strings.sh` (mode only), `tools/verify_tree.sh`,
  `lanes/R3_REPORT.md` (new). Cross-lane edits (each with a request below):
  `iso/calamares/meta-branding.sh`, `metaos1-base/dexubuntu/*`,
  `face/meta-desktop.sh`, `face/provision.sh`, `iso/payload-theme/README.md`.
- Zero forbidden paths touched: no edits in `trio/*`, `agent-layer/server/*`,
  `agents/*`, `server/*`, `board/*`, `iso/build_iso.sh`,
  `iso/merge-layers.sh`, `iso/provision*.sh`, theme token generator sources.
  Pre-existing dirty files in those paths belong to other lanes (listed in
  §12) and were not modified by this lane — verified with
  `git status --short` before and after (only §10 files changed).

## 9. Six artefacts: before / after

1. Spiral splash: BEFORE — base `emerald` desktop-base + Debian plymouth
   link painted ~2.5 s of foreign branding (`provision.sh` measured
   3.6→6.2 s). AFTER — `Theme=metaos` everywhere provisioned, 240 Meta
   frames (darkest pixels ≈ ink, §B), zero spiral/swirl/ubuntu/debian
   filenames in shipped theme dirs (find, empty). Boot-display itself NOT
   RUN (no hardware).
2. Green wallpaper: BEFORE — user-kept seeing base teal/green fallback.
   AFTER — only 4 Meta PNGs + live loop ship (hashes:
   `meta-ascii 03644f47…`, `meta-dawn 2f8f2ca1…`, `meta-dusk e71bb22d…`,
   `meta-rays 57ef6f26…`; centers `#070B16/#124C9C/#0A162E/#0B2346`), no
   green generator in tree. Daemon resize path fixed in-tree
   (`cover_metrics` + `test_cover.py` 10/10); live repaint NOT RUN (no X).
3. Ubuntu Mono font: BEFORE — `FontName=Ubuntu Mono 11` (theme_proof still
   asserts it). AFTER — provision + shipped profile both
   `FontName=Monospace 11` (verified grep, two files agree); image still
   installs `fonts-ubuntu` (compat, request R5). Render-to-PNG proof NOT
   RUN (no headless browser).
4. Xubuntu comments: BEFORE — `Comment=` fields stripped by OS-3 (verified
   still clean, grep exit 1); code comments remained (`meta-desktop.sh:81`
   allowlisted upstream-notice, `provision.sh:287` reworded R3).
5. ubuntu user/home: BEFORE — base account `ubuntu`. AFTER —
   `rename_user.sh` renames to `meta` at build time; only reference left is
   the last-resort probe `meta-desktop.sh:41` (getent + `/home/meta` first).
   Live rename NOT RUN (no image).
6. ID_LIKE=ubuntu: BEFORE — two writers stamped it
   (`git show HEAD:...meta-branding.sh` → `ID_LIKE=ubuntu`;
   `git show HEAD:...dexubuntu/identity/os-release` → `ID_LIKE=ubuntu` +
   `UBUNTU_CODENAME=noble`). AFTER — both stamp `ID_LIKE=debian` with Ribbon
   contract fields; dex payload byte-identical to the canonical payload
   (`diff` → IDENTICAL). Installed-system write NOT RUN (no Calamares run).

## 10. What changed (file list, this lane's session)

Own lane: `os-build/identity/check_strings.sh` (`--check` alias for the
verify_tree contract), `os-build/identity/ALLOWLIST.tsv` (+29 rows, all
4-column), `os-build/tools/verify_tree.sh` (+2 rows: `home-refs`,
`os-release-identity`), `os-build/identity/check_strings.sh` +
`test_check_strings.sh` + `tools/verify_tree.sh` mode `644→755`,
`os-build/lanes/R3_REPORT.md` (this file).
Cross-lane (with requests §11):
`os-build/iso/calamares/meta-branding.sh` (contract release block + once-only
backup), `os-build/metaos1-base/dexubuntu/identity/os-release`,
`identity/lsb-release`, `apply-in-chroot.sh` (Ribbon strings),
`os-build/face/meta-desktop.sh:34` (comment reword),
`os-build/face/provision.sh:287` (comment reword),
`os-build/iso/payload-theme/README.md:67` (font doc accuracy).

## 11. Cross-lane requests (file:line)

- R1 (OS-2 / ISO build): `os-build/iso/calamares/meta-branding.sh:28-44` —
  values fixed R3 to the Ribbon contract; open: add a gate so an already-
  contract `/etc/os-release` is never regressed, and own the last-writer
  order vs `unpackfs`/`bootloader` in `modules/meta-branding.conf:8`.
- R2 (Pax / metaos1-base): `os-build/metaos1-base/dexubuntu/identity/
  os-release:7,11` + `lsb-release` + `apply-in-chroot.sh:19-27` — aligned R3
  to contract; open: confirm no packaging tool consumed `UBUNTU_CODENAME`
  (removed), and fix the GNU-only `sed -i` + literal `\t` hosts rewrite
  (`:12-15`, breaks on BSD sed).
- R3 (Buffy / face): `os-build/face/meta-desktop.sh:41` — keep or drop the
  `/home/ubuntu` last-resort probe (lane kept + allowlisted); open: flip
  `CALC_BIN` default `:382` galculator → mate-calc (matrix proves mate-calc
  present, galculator absent).
- R4 (Buffy / face): `os-build/face/meta-desktop.sh:379-384` galculator
  comment block (stale line refs `:287`/`README:66` in the brief — actuals
  are `:379-384` and no README:66); open: reword, already correct behavior.
- R5 (theme lane): `os-build/iso/payload-theme/theme_proof.sh:189` asserts
  `^FontName=Ubuntu Mono 11` while provision + shipped profile ship
  `Monospace 11` — one side must move (atomic with `apply.sh:247` gate,
  both FONTS.md, payload README). Font files are compat; the *name string*
  is the issue.
- R6 (ISO build): xubuntu branding packages (`xubuntu-default-settings`,
  `-wallpapers`, `-artwork`, `-docs`) purged only on the dexubuntu path;
  `merge-layers.sh:99-102` transplants base `etc/casper.conf` verbatim
  (USERNAME=meta rewrite missing) and base skel over provisioned skel
  (precedence unconfirmed); `casper:` preseed `xubuntu.seed` cmdline arg
  untouched by `grub-fix.sh`.
- R7 (docs): HACKATHON dock count (27 vs measured 24 vs INVENTORY 19),
  `APP_MATRIX` vs manifest, stale `README:66`-style pointers.
- R8 (trio/board/face-runtime): `trio/ignis.html:147` 284-vs-283px mapband +
  `map3d.js:32` pitch (demo blocker, Buffy); `board/board.mjs:552-553`
  non-loopback bind; missing `/healthz` on face py services + ptyd; residual
  `relay*` UI strings in `face/agents.html:63,100,146-149`
  (`start.html:41,60`, `session.sh:81-82`); cursor theme falls back to base
  defaults (`greeter/KEYS.md:31`).
- R9 (ISO build / debrand): wire `GRUB_DISTRIBUTOR="MetaOS"` + `GRUB_THEME`
  into the installed root (nothing writes `/etc/default/grub` today);
  ship `/usr/share/xsessions/metaos.desktop` (`Name=Meta OS`, no ubuntu) —
  nothing installs it today (`session.sh:109` only reads); install a real
  `meta-wallpaper.png` or repoint the three dangling references
  (`provision.sh:140`, `face/provision.sh:245`, `gnome-background.xml:10`,
  gschema override); decide `studio-loop` 240-vs-16 duplication and the
  orphan `face/plymouth/metaos/ring-dot.png`.
- R10 (ISO build): create `check_target.sh` (10 rows proposed §D78) and
  confirm `metaos-install.sh` path; add the `rename_user.sh` pre-existing-
  `meta` guard; decide first-boot vs build-time debrand (no sentinel today,
  by design).
- KNOWN (do not "fix"): `os-build/face/facts.py` is correct as-is.

## 12. Not run and why

- No QEMU/boot/mount/sudo/image writes (lane rule; this host is macOS,
  no target rootfs): H140 ten items, D72/D73 live runs, E79–E96 target
  `dpkg`/`apt/snap` proofs, G122 headless renders, G123–G125/G142–G143 live
  paint/resize/handoff, first-boot welcome window, Calamares install path.
- `apt-cache rdepends`, `plymouth-set-default-theme -R`, `update-initramfs`,
  `snap list`, `lsinitramfs`, `xfconf-query` reads: need a Linux rootfs —
  file-trace evidence substituted throughout.
- Pre-existing dirty files NOT touched by this lane (other lanes' in-flight
  work, verified untouched): `agents/model_client.mjs`,
  `os-build/face/metaos-update.sh`, `os-build/face/shell.html`,
  `os-build/iso/payload-apps/server/*`, `server/cams.json`,
  `trio/{ignis,medicus,vigiles}.html`, captures/icons worktrees output.
- HACKATHON/DEMO capture PNGs and `os-build/logs` evidence: referenced, not
  re-verified pixel-by-pixel in this static pass.
