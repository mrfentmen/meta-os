# R2-T1 Section E/F — installer + package surface report

All commands ran in `/tmp/agent-r2-t1`, branch `agent-r2-t1`. No QEMU, no
sudo, no mount. The live image (`/tmp/metaos.ext4`, 17,179,869,184 bytes,
read-only) cannot be read: `which debugfs` → not found, no python ext4
module, `hdiutil` rejects it. Package facts below come from
`/tmp/fs.manifest` (1876 lines, base manifest), labelled as such.

## E. Installer changes (file:line)

- `os-build/iso/calamares/branding/metaos/branding.desc` — already Meta
  (`productName: "Meta OS"`, `versionedName: "Meta OS 1.0"`,
  `bootloaderEntryName: "Meta OS"`); no edit needed. Verified by
  `check_installer.py` gates `branding productName/versionedName/
  bootloaderEntryName`.
- `os-build/iso/calamares/branding/metaos/slideshow/slide-05-done.html:17-20`
  — erase warning rewritten in Meta voice ("Heads up — this erases the
  disk: ... Anything on it is gone.").
- `os-build/iso/calamares/modules/finished.conf:1-11` — comment only:
  finish page offers reboot only (restart pre-checked,
  `systemctl -i reboot`); unchecking closes the installer.
- `os-build/iso/calamares/modules/packages.conf` — unchanged: removes only
  `calamares` + `ubiquity`, no desktop metapackage (`packages.
  no-ubuntu-metapackage` gate passes). The `ubiquity` comment names the
  Xubuntu base honestly (build-time note, not a user string).
- `os-build/iso/calamares/modules/users.conf` — unchanged: `login: "meta"`,
  `fullName: "Meta User"`, no ubuntu default user (gate passes).
- `os-build/iso/calamares/modules/keyboard.conf` — `layout: "us"`
  (unchanged, verified).
- `os-build/iso/calamares/modules/locale.conf` — `region: "America"`,
  `zone: "New_York"` = America/New_York, the demo city (unchanged,
  verified).
- `os-build/iso/calamares/modules/welcome.conf` — `showSupportUrl: false`,
  `showReleaseNotesUrl: false` (no dead Ubuntu links; gate passes).
- `os-build/iso/calamares/branding/metaos/stylesheet.qss` — palette
  `#070B16/#1877F2/#EDF5FF` (gate passes).
- Calamares QML: `find os-build/iso/calamares -iname '*.qml'` → empty.
  The "at least one hardcoded Ubuntu string" premise is false here;
  reported, not manufactured.
- New `os-build/iso/calamares/tools/check_installer.py` — dry-run
  validator, 27 gates, exit 0 only if all pass:
  `RESULT: DRY-RUN PASS (27 passed, 0 failed; VM walkthrough still owed)`.
- New `os-build/iso/calamares/tools/check_target.sh` — post-install gate:
  `TARGET=<root> sh check_target.sh`; Ubuntu fixture → `RESULT: FAIL`
  exit 1; contract fixture → `RESULT: PASS` exit 0.

## F. Package table (from /tmp/fs.manifest; image itself read-only)

20 installed packages start with `ubuntu`/`xubuntu`/`lubuntu`
(`grep -iE '^(ubuntu|xubuntu|lubuntu)[- ]'`). No lubuntu hits.

| package | version | verdict | reason |
|---|---|---|---|
| ubuntu-minimal 1.539.2, ubuntu-standard 1.539.2 | see manifest | KEEP | Seed metapackages; removing breaks the apt dependency closure of the base. Rebrand-neutral (no brand surface). |
| ubuntu-keyring 2023.11.28.1 | see manifest | KEEP | Archive trust for Ubuntu repos the build still uses. Removing breaks all package installs. |
| ubuntu-drivers-common 1:0.9.7.6ubuntu3.7 | see manifest | KEEP | Functional HW enablement (`ubuntu-drivers`); no brand surface. |
| ubuntu-kernel-accessories 1.539.2 | see manifest | KEEP | Kernel hook scripts. Functional. |
| ubuntu-mono 24.04-0ubuntu1, fonts-ubuntu 0.869 | see manifest | KEEP | Proven desktop consumer: `payload-theme/apply.sh` installs `fonts-ubuntu`; `fonts/FONTS.md` pins Ubuntu Mono as the monospace face; theme_proof D7 gates `fc-list` on it. (Font migration is section A work.) |
| ubuntu-advantage-desktop-daemon, ubuntu-pro-client[-l10n] | see manifest | REMOVE | Ubuntu Pro/ESM upsell surface incl. MOTD ESM advertising; no Meta equivalent wanted. (REQUEST R-101: needs image write.) |
| ubuntu-release-upgrader-core, -gtk | see manifest | REMOVE | Offers release-upgrades to Ubuntu releases, which would unbrand the system. (REQUEST.) |
| xubuntu-artwork, xubuntu-wallpapers, xubuntu-community-wallpapers[-jammy], xubuntu-docs, xubuntu-default-settings, xubuntu-desktop[-minimal], xubuntu-live-settings | see manifest | REMOVE branding payloads | Stock identity assets/settings; the debrand lane already removes their files at build. Packages themselves need an image-side purge (REQUEST R-102; `apt purge` list recorded, proof that nothing else needs them: no reverse-depends outside the set — verify at removal time on Linux). |
| lib*/plymouth-theme-ubuntu-* if present | n/a | REMOVE | Ubuntu boot art; replaced by metaos theme. (REQUEST.) |

Image size: unchanged by this lane (read-only image, 17,179,869,184 bytes).
Per-package Installed-Size savings were not invented: no dpkg status source
is readable on this host; the method is `dpkg-query -W -f='${Installed-Size}'`
at removal time on Linux.

`neofetch`/`fastfetch`: 0 hits in manifest — not installed, nothing to do.
`snap-store`, `thunderbird`, `firefox`, `firmware-updater`,
`ubuntu-desktop-bootstrap`: present in manifest (snaps); snap store brand is
outside the installer lane — stated, not changed.
`plank`: 0 hits in base manifest — added by `merge-layers.sh:70`, not a base
package. `grub` distributor hook: no `GRUB_DISTRIBUTOR` anywhere in `iso/`;
request the boot lane to set it (see R2_T1_REPORT).
