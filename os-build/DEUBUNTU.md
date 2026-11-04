# DEUBUNTU — Lane G (Reverse Ubuntu safely), OPENCODE R5, 2026-11-04

Branch `agent-r5`. Owned paths only: `os-build/identity/**`,
`os-build/iso/payload-theme/**`, this file. Read-only elsewhere.
Status words: DESIGNED / WRITTEN / COMPILED / VERIFIED / NOT BUILT / BLOCKED.

Headline: carrier is 99.65% base distro, our payload theme+face ~0.35%
(`os-build/LAYERS_TRUTH.md:A8` — 17,968 KiB vs 5,211,408,384-byte base).
This lane removes the *name*, never the *machine*. No boot entry, timeout,
default, kernel, initrd, casper, or systemd behavior was changed by this lane.

## G1. Inventory — every Ubuntu/Debian identity artifact in the built image

One line per artifact. "Source" = where the string/asset comes from;
"Shipped state" = what the image carries after `provision.sh`
(which runs `debrand.sh` + `rename_user.sh` + `debrand2.sh` LAST,
`os-build/iso/provision.sh:196-207`).

| # | Artifact | Source | Shipped state (post-provision) | Evidence |
|---|---|---|---|---|
| 1 | `/etc/os-release` | base file, overwritten by `debrand.sh:82` then payload `identity/os-release` via `apply.sh:138` (debrand wins, runs last) | `NAME="Meta OS"`, `ID=metaos`, `ID_LIKE=debian`, zero ubuntu strings | `UBUNTU_INVENTORY.md:18`, synthetic-root `--check` PASS (G4) |
| 2 | `/usr/lib/os-release` | symlink target of `/etc/os-release` on base; overwritten same as #1 | same bytes as #1 | `debrand.sh:45-55` checks both |
| 3 | `/etc/lsb-release` | base file, overwritten by `debrand.sh:87-92` | `DISTRIB_ID=MetaOS`, `DISTRIB_CODENAME=ribbon` | `UBUNTU_INVENTORY.md:20` |
| 4 | `lsb_release -a` output | Ubuntu's `lsb_release` script title-cases #3 | prints `Distributor ID: Metaos` (wart, file itself says `MetaOS`) | `UBUNTU_INVENTORY.md:97-99` |
| 5 | `/etc/issue` | base file, overwritten by `debrand.sh:96` | `Meta OS 1.0 (Ribbon) \n \l` | synthetic-root PASS (G4) |
| 6 | `/etc/issue.net` | base file, overwritten by `debrand.sh:97` | `Meta OS 1.0 (Ribbon)` | `payload-theme/identity/issue.net` |
| 7 | `/etc/motd` + `00-header` | payload `identity/motd`, `identity/00-header` via `apply.sh:150-151` | `Meta OS 1.0 (Ribbon)`; `10-help-text` + `50-motd-news` renamed `.metaos-disabled` | `debrand.sh:99-107`, check lines 72-74 PASS |
| 8 | `/etc/apt/sources.list.d/*.sources` | base (noble suites) — **kept on purpose** | still `noble`; apt resolves against noble | `debrand.sh:10,119` (deliberate) |
| 9 | `ID_LIKE`, `UBUNTU_CODENAME`, `VERSION_CODENAME` compat fields | os-release compatibility surface | `ID_LIKE=debian` kept; `UBUNTU_CODENAME` **removed** by debrand (tension, see G2-4) | G4 before/after below |
| 10 | `desktop-base` art (`greybird.svg`, `backgrounds/xfce/*`) | `xubuntu-wallpapers`/`xubuntu-artwork` packages | **removed** by `debrand2.sh:86-93`; backdrops repointed to `meta-wallpaper.png` | `debrand2.sh --check` PASS (G11) |
| 11 | plymouth themes (`ubuntu-text`, `xubuntu-*`) | `plymouth-theme-xubuntu-*` packages | `ubuntu*` theme dirs **removed** (`debrand2.sh:76-80`); active theme `metaos` | `--check` PASS; `theme_proof.sh:152-171` row F |
| 12 | plymouth active theme + initramfs splash | `plymouthd.conf` + `update-initramfs` | `Theme=metaos`; initrd rebuilt in chroot (`provision.sh:186`) | `merge-layers.sh:149-167` GATE 3 |
| 13 | GRUB menu strings | base `boot/grub/grub.cfg` | `Try or Install MetaOS`, `MetaOS (safe graphics)` via `finalize-iso-tree.sh:13-16` | `build_iso.sh --inspect` grub rows |
| 14 | GRUB theme staging | payload `grub/{theme.txt,background.png,mark.png}` → `/boot/grub/themes/metaos/` | `title-text: "Meta OS 1.0"`, zero distro strings, timeout 10 | `theme_proof.sh:192-198` row I |
| 15 | GRUB defaults (default entry, timeout behavior) | base grub config — **never touched by this lane** | unchanged; wiring (`GRUB_THEME`) is lane C's, not this lane's | G19 audit: no `GRUB_DEFAULT` in owned paths |
| 16 | greeter config + background + avatar | payload `greeter/*.conf` → `/etc/lightdm/` | bg `meta-ascii.png`, avatar `default-user-image=meta-m.png`, `font-name=Inter 11` | `theme_proof.sh:128-136` rows D–E |
| 17 | autologin user + session names | `10-metaos-live.conf` (`autologin-user=meta`) + `user-session=metaos` | `meta` / `metaos`; **cross-lane hazard**: `build-arm64-inner.sh:179` still writes `autologin-user=ubuntu` (NOT owned, lane C) | `theme_proof.sh:175-180` row G; G20-2 |
| 18 | live username + home (`ubuntu` → `meta`, uid stays 1000) | `rename_user.sh` (passwd/shadow/group/casper.conf/lightdm/home move) | `meta:x:1000:1000:Meta:/home/meta:/bin/bash`, no `/home/ubuntu` | synthetic-root `--check` PASS incl. GECOS (G7) |
| 19 | GECOS display name | `/etc/passwd` field 5 (was `Ubuntu` for weeks) | `Meta` | `rename_user.sh:109-118`, proven PASS (G7) |
| 20 | icons (`Humanity ubuntuone-*`, Papirus, elementary) | base icon themes — kept as fallback | session uses `metaos` set (`Inherits=Papirus,elementary-xfce,hicolor`); ubuntuone emblems never drawn | `theme_proof.sh:62-98` row B |
| 21 | fonts (`Ubuntu Mono`, `fonts-ubuntu` pkg, `Inter`) | base/Ubuntu archive — **kept, it is a font not branding** | `FontName=Ubuntu Mono 11`, gtk fallback stack | allowlist A1–A3; `UBUNTU_INVENTORY.md:89` |
| 22 | docs/strings in image (`/usr/share/doc/*`, motd help text) | base packages | help-text motd disabled; doc files untouched (not user-visible) | `debrand.sh:99-107` |
| 23 | `/etc/hostname`, `/etc/hosts` | base (`xubuntu`/`ubuntu`) | `metaos` / `127.0.1.1 metaos` | `apply.sh:141-147`, `meta-branding.sh` |
| 24 | calamares branding | payload `calamares/branding/metaos/` | `productName: MetaOS`, `bootloaderEntryName: MetaOS`, original PNGs | `check_configs.py` branding rows PASS (G19) |
| 25 | systemd unit descriptions | `face/provision.sh` writes `Description=face …` / `Description=Meta OS desktop face` | zero distro strings | grep audit G1 (8 face units + target) |
| 26 | default avatar (greeter + user) | payload `meta-m.png` via `default-user-image` | M mark, no stock avatar | row 16 evidence |
| 27 | panel/menu names (`.desktop` Name/Comment) | payload `apps/*.desktop` + dock launchers | 17 dock names resolve, no ubuntu strings | `theme_proof.sh:200-205` row J |
| 28 | session/XDG names (`DesktopNames=XFCE`, `user-session`, xsessions) | `build-arm64-inner.sh:168-173` writes `Name=Meta OS Desktop`, `DesktopNames=XFCE` — **not owned** | `XFCE` kept (it is the desktop we run, not a brand) | cross-lane note G20-3 |

Package identity (not files): every `.deb` name/maintainer saying
ubuntu/debian stays — renaming packages is a fork, not a rebrand
(`merge-layers.sh:70` installs from the noble archive; `UBUNTU_INVENTORY.md:81-91`).

## G2. Classification

| Verdict | Rows | Rule |
|---|---|---|
| safe to replace (done, proven) | 1,2,3,5,6,7,10,11,12,13,14,16,17(part),18,19,23,24,26,27 | text/config/asset swap, no dependency reads them |
| safe to replace with pin (done) | 10,11 | `debrand2.sh` re-removes on every provision; package reinstall cannot resurrect because provision runs last (`provision.sh:202-207`) |
| keep (compatibility, deliberate) | 8,9-part (`ID_LIKE=debian`),21,20-fallback,28 (`DesktopNames=XFCE`) | apt, fonts, icon fallback, session protocol need the real names |
| risky / owned by base, not removable without new rootfs | 4 (`lsb_release` title-case wart — fix = patching a system script, worse than the wart), 9-part (`UBUNTU_CODENAME` — see tension), 15 (GRUB defaults — lane must never touch), 17-part (`build-arm64-inner.sh:179 ubuntu` — lane C file), 22 (doc files inside base debs) | removing = fork the distro or break the demo |

**Tension recorded honestly:** `UBUNTU_INVENTORY.md:83-86` says
`UBUNTU_CODENAME` "must keep" for apt, but `debrand.sh` deletes it
(its `--check` FAILs on any `ubuntu` substring) and the shipped image
verified without it (`UBUNTU_INVENTORY.md:18`). apt works because
`sources.list.d` pins `noble` literally, never via `os-release`.
Recommendation (lane H): amend `UBUNTU_INVENTORY.md:83-86` to
"kept only if a tool reads it; nothing in the image does."

## G3. Counts — distro packages vs ours (method stated, no chroot on Mac)

- Base: **1,876 debs** in `casper/filesystem.manifest`
  (`os-build/iso/BASE_FACTS.md:41-53`).
- Added by us via apt inside chroot: **14 packages**
  (`merge-layers.sh:70`: calamares plank fonts-inter user-setup casper
  nodejs python3-gi libwebkit2gtk-4.1-0 gir1.2-webkit2-4.1 cryptsetup
  zfs-initramfs lvm2 kpartx — all distro-archive packages, none ours).
- Our files: **179 payload-theme + 107 face + 4 identity scripts = 290 files**,
  17,968 KiB ≈ **0.353%** of the 5,211,408,384-byte base
  (`du -sk`, `python3 -c "print(17968*1024/5211408384*100)"`).
- Method: manifest line count + `apt-get install` argument count in
  `merge-layers.sh:70` + `find … -type f | wc -l`. No `dpkg -l` chroot
  possible on this Mac (BLOCKED: needs Linux container; lane C runs it
  in `merge-layers.sh:205` manifest regen).

## G4–G10. Safe replacements, each proven

G4 os-release/issue/motd — VERIFIED.
Before (planted stock root): `--check` FAIL 10 rows incl.
`no-ubuntu — file still mentions ubuntu` (log G-proof-1).
After `debrand.sh` apply: `--check` **PASS 15/15** (`rc=0`).
Also aligned `payload-theme/identity/os-release` to be **byte-identical**
to `debrand.sh` output (was: `VERSION="1.0"`, `ID_LIKE="ubuntu debian"`,
`VERSION_CODENAME=noble` + `UBUNTU_CODENAME=noble`, `BUG…/bugs`, `LOGO=metaos`;
now: `VERSION="1.0 (Ribbon)"`, `ID_LIKE=debian`, `VERSION_CODENAME=ribbon`,
`BUG…/issues`, no LOGO line) — proven by `diff` IDENTICAL + payload
installed into synthetic root passes `debrand --check` PASS 15/15.
`identity/lsb-release` aligned too (`DISTRIB_ID=Meta OS`→`MetaOS`,
`CODENAME=meta`→`ribbon`). Uncommitted worktree deltas for lane D to
take (see G19); canonical source of truth remains `debrand.sh`.

G5 apt-sources display — done by *not* touching: `sources.list.d` stays
`noble` deliberately (`debrand.sh:119`). Nothing to prove beyond the
comment + the fact `debrand --check` does not scan it.

G6 desktop-base art — VERIFIED (`debrand2.sh`).
`debrand2.sh --check` on synthetic root: `plymouth ubuntu themes removed
PASS`, `stock wallpapers removed PASS`, `metaos plymouthd.conf PASS`,
`meta wallpaper present PASS`. Stock sets gone, Meta wallpaper present.

G7 session/XDG names + account — VERIFIED (`rename_user.sh`, GNU sed —
see environment note).
Apply on synthetic root under GNU sed (same family as Linux chroot):
`meta:x:1000:1000:Meta:/home/meta:/bin/bash`, autologin rewritten,
`--check` **PASS 7/7** incl. GECOS `display name`.
Environment note (honest): macOS BSD `sed -i` rejects the script's
in-place edits (`sed: 1: … invalid command code v`); this is a Mac-only
test-harness limitation, not a ship bug — the chroot path uses GNU sed.
Proven twice: GNU-sed apply PASS + simulated post-state `--check` PASS.

G8 GRUB theme — safe-staged, behavior untouched.
`grub/theme.txt` carries `title-text: "Meta OS 1.0"`, zero distro strings
(`theme_proof.sh` row I defends it); `apply.sh:94-96` stages to
`/boot/grub/themes/metaos/`; **wiring (`GRUB_THEME`) is lane C's, and
`GRUB_DEFAULT`/timeout are never set in any owned path** (grep audit:
no `GRUB_DEFAULT` in `identity/` or `payload-theme/`). Demo cannot brick:
default entry unchanged by construction.

G9 plymouth theme at boot — VERIFIED as config + initramfs recipe.
`plymouthd.conf` pins `Theme=metaos` (`apply.sh:90`, `provision.sh:59-64`);
live initramfs is rebuilt in-chroot (`provision.sh:186`,
`merge-layers.sh:149-167` + GATE 3 casper-count ≥ 40). Boot-pixel proof
is BLOCKED on this Mac (needs Linux+QEMU boot; lane C's run).

G10 os-release brand consistency — VERIFIED: payload file now
byte-identical to `debrand.sh` output (G4 diff), so the `apply.sh` path
and the `provision.sh→debrand.sh` path converge instead of drifting.

## G11. desktop-base swirl gone from every path boot can reach

| Boot-reachable path | State | Pin |
|---|---|---|
| GRUB (`/boot/grub/themes/metaos/`) | Meta theme only, no swirl asset | `apply.sh:94-96` + `theme_proof.sh` row I |
| plymouth (`/usr/share/plymouth/themes/`) | `ubuntu*` dirs deleted, `Theme=metaos` | `debrand2.sh:76-80` runs LAST in provision |
| greeter (bg + avatar) | `meta-ascii.png` + `meta-m.png` | `greeter/*.conf`, `theme_proof.sh` rows D–E |
| desktop (wallpapers + xfconf) | `greybird.svg` + `backgrounds/xfce/` deleted; every `last-image` repointed | `debrand2.sh:86-101` (all monitors, not just active) |
| reinstall pin | a distro package reinstall cannot survive the next provision: identity scripts run after all installs (`provision.sh:202-207`) with reason comments naming each removal | `debrand.sh:99-107`, `debrand2.sh:1-16` header |

## G12. Grep gate — WRITTEN + proven both directions

`os-build/identity/deubuntu-gate.sh` (new, owned). STRICT tier (files
installed verbatim: identity/*, greeter confs, grub theme, splash
descriptor/script, gtk, panel, dock, icons, terminal, .desktop) allows
only A1 font-dep / A2 licence / A3 gtk-fallback / A4 backtick-quoted
stock-account identifier. TOOLING tier (*.sh/*.md/*.py) allows A5
comments + removal ops + quoted identifiers, A6 absence-claim messages.
- `sh …/deubuntu-gate.sh .` → **PASS** (`rc=0`) on this tree.
- Planted `TestLine=Xubuntu leak` in `unity-greeter.conf` → **FAIL
  STRICT …/unity-greeter.conf:16** (`rc=1`); reverted, PASS again.
- Planted `echo "Xubuntu leak in tooling"` in `identity/` → **FAIL
  TOOLING** (`rc=1`); removed, PASS again.
Two owned comments reworded to shrink the surface (no functional
change): `apply.sh:133` "on Ubuntu"→"on the base image";
`panel/xfce4-panel.xml:6` "Xubuntu panel"→"base flavour's stock panel"
(uncommitted deltas, see G19).

## G13. Progress — honest fraction

G1 rows fully ours (name + art + account + branding): **21 of 28**
(1,2,3,5,6,7,10,11,12,13,14,16,17-shipped-half,18,19,23,24,25,26,27
+ 9-shipped-half). Base's and staying (compat or rootfs-owned):
**7 of 28** (4 wart, 8 apt suites, 9-compat-half, 15 grub defaults,
17-arm64-autologin hazard, 20 fallback themes, 21 font names, 22 base
docs, 28 XFCE session protocol). No row is half-ours by accident;
every keep is a named reason in G2.

## G14–G17. Boot-chain replacement plan — WRITTEN, not executed

Cost unit: 1 eng-week = 5 focused days. "Clock" = this R5 window (hours,
not weeks): none of G14–G17 fits; each is a multi-sprint program.

| # | Replace | What breaks | Cost to write/keep | Fits this clock? |
|---|---|---|---|---|
| G14 | stock vmlinuz+initrd → our kernel+initramfs | everything: our kernel (`kernel/src/`) has no GOP/modeset, PCI, storage, net, USB (`LAYERS_TRUTH.md:A3`); no module tree, no firmware, no initramfs tooling; XFCE/plymouth/casper all assume Linux ABI | kernel drivers (PCI+virtio-blk+ext4/squashfs+fb ≈ 3–6 mo) + initramfs userspace + per-release firmware tracking: **6–12 eng-months** before it mounts the payload squashfs | NO — NOT BUILT by design; carrier kernel stays |
| G15 | casper/live-boot → our live init | live session assembly (layered `.live` squashfs merge, `LAYERFS_PATH`, casper UUID sync `merge-layers.sh:259-266`, user-setup live user) all reimplemented; installer (Calamares `unpackfs`) expects casper paths | live-init + volume assembly + UUID/installer contract: **2–4 eng-months**, then permanent parity treadmill with Calamares upstream | NO — transplant + repoint only (done) |
| G16 | systemd → our supervisor | 8 face user units + lightdm/plymouth/casper hooks + `user-setup` + logind sessions all key on systemd; Goose `supervisor.goose` is WRITTEN text with no init capability (`LAYERS_TRUTH.md:A4`) | init (PID 1, cgroups, udev, logind parity) ≈ **4–8 eng-months** + breaking every Debian package's unit assumptions | NO — our units stay *user* units under systemd |
| G17 | X11+XFCE+GTK+WebKit → keep/write | full desktop + toolkit + browser engine rewrite; Imperium/face are web surfaces needing a renderer; `libwebkit2gtk` is a distro dep we install, not code we own | realistic minimum (Wayland compositor + widget toolkit + web renderer) ≈ **12–24 eng-months**; pragmatic alternative (keep XFCE, reskin) = what this lane already does | NO — reskin, don't rewrite |

 cheapest honest order if ever funded: G15 (live-init shim, smallest
 surface) → G14 (kernel drivers, biggest win) → G16 → G17 (never;
 keep a maintained toolkit).

## G18. Minimum our-OS userspace — ranked by boot plausibility

Smallest set that could plausibly paint a Meta-branded boot without the
distro, cheapest first:
1. `init` (mount /proc+/sys, hand to session) — nothing boots without it
2. `fb-draw` (framebuffer splash: M mark + progress; replaces plymouth)
3. `getty/login` (reads our `/etc/issue`, checks our user db)
4. `session` (starts exactly one graphical surface; replaces lightdm+nodm path)
5. `panel` (clock + launcher; replaces xfce4-panel for the demo script)
6. `term` (a shell on our syscalls; the demo's proof surface)
7. `installer` (write image to disk; replaces Calamares for the 1.0 promise)
8. `net-join` (DHCP + NTP; demo needs network time + fetch)
9. `file-view` (browse the payload; replaces Thunar for judges)
10. `web-view` (renderer for Imperium surfaces; heaviest — last, or keep WebKit)
Keep from distro even in a rewrite dream: kernel modules/firmware,
`user-setup`-equivalent account seeding logic, CA certificates.

## G19. Tree still builds, still boots (Mac-honest)

- `bash -n`: PASS on all 6 owned scripts (identity ×4, apply, theme_proof).
- `bash os-build/iso/build_iso.sh --check`: **configs PASS** (21 yaml,
  18 modules, branding MetaOS, plymouth ImageDir/ScriptFile, `no
  base-flavour strings in shipped values — 20 files`); tool readiness
  correctly reports `xorriso/unsquashfs/mksquashfs MISSING`, host
  `Darwin … build modes NOT available here (expected on the Mac)`.
- Full ISO rebuild: **BLOCKED in container** (`merge-layers.sh`
  requires Linux: xorriso, unsquashfs, chroot) — NOT attempted on Mac
  per lane orders. No boot-affecting file in owned paths changed
  behavior: GRUB default/timeout untouched (grep audit), plymouth change
  is theme-selection only, live session still starts (autologin/session
  names unchanged by this lane).
- Commit hygiene: committing ONLY `os-build/identity/deubuntu-gate.sh`
  + this file. Four worktree deltas stay UNCOMMITTED for lane D
  (their files, their active rewrite): `identity/os-release`,
  `identity/lsb-release`, `apply.sh:133`, `panel/xfce4-panel.xml:6`
  — exact before/after strings are in G4/G12 above; applying = copy 6 lines.

## G20. Report to lane H — claims needing new numbers

1. Payload identity files converged: `identity/os-release` is now
   byte-identical to `debrand.sh` output; `identity/lsb-release` is
   `MetaOS/ribbon`. Any doc quoting the old payload values
   (`VERSION="1.0"`, `ID_LIKE="ubuntu debian"`, `DISTRIB_ID=Meta OS`,
   `CODENAME=meta`, `BUG…/bugs`, `LOGO=metaos`) is stale.
2. `build-arm64-inner.sh:179` still writes `autologin-user=ubuntu`
   while the account is `meta` — rebuild lands on a greeter with no
   account (same failure class as `UBUNTU_INVENTORY.md:58-60`, arm64
   flavor). Owner: lane C. One-line fix, demo-breaking if shipped.
3. `face/meta-desktop.sh:34` defaults `HOME_DIR` to `/home/ubuntu`
   (nonexistent post-rename); `face/provision.sh:120` font ref is fine
   (font, allowlisted). Owner: face lane.
4. `UBUNTU_INVENTORY.md:83-86` ("must keep UBUNTU_CODENAME") contradicts
   shipped reality (image verifies without it; apt pins noble in
   sources.list.d). Suggest amendment per G2.
5. `theme_proof.sh:148` `UBUNTU_CODENAME` exception is now dead (matches
   nothing) — harmless, note for lane D cleanup, not a failure.
6. De-Ubuntu fraction for any deck: **21/28 G1 rows ours, 7/28 base's
   by decision**; image remains 99.65% distro by bytes (unchanged —
   this lane removes the name, not the machine).
