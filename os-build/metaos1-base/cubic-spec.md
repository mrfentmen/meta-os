# Cubic project definition — MetaOS 1.0 base (Hana lane)

Tool: Cubic (Custom Ubuntu ISO Creator), run on the cut machine.
Base: Xubuntu core, x86_64. The exact source ISO is NOT fixed in this
slice: the cut operator picks the current Xubuntu LTS core ISO at cut
time and records its filename + SHA-256 in the ISO cut record. Any
slice text that named a version would go stale; the cut record is the
truth for which ISO was used.

## Steps, in order

The base flow runs in this exact order. The packages, theme, and
identity steps below are the order Pax's dexubuntu README states,
and the step right after them is the gate on the identity step.
Nothing here authors theme or identity files: the theme script is
OC1's, the identity script is Pax's gap-fill. This slice only wires
them into the cut, in order, and gates the result.

1. Create a new Cubic project. Point it at the recorded source ISO.
2. In the Cubic terminal (chroot), apply `packages.txt`:
   - `apt update`
   - install every package under `ADD:` (one `apt install -y` run)
   - remove every package under `REMOVE:` — slice 1 lists none, so
     this step is a no-op until a later slice names a removal with a
     reason and a Milo audit row.
   - `apt autoremove -y` only if a removal was made; otherwise skip
     it, so the base is not trimmed by accident.
3. Run OC1's theme installer from the chroot:
   `metaos-theme/apply.sh`. It installs the greeter config, the
   wallpaper files, the dock theme, the GTK theme, and the terminal
   welcome. The per-user panel step it prints is OC1's lane to apply
   for the console user, not this slice's.
4. Run the identity step from the chroot:
   `dexubuntu/apply-in-chroot.sh`. It stamps hostname `metaos`,
   the MetaOS 1.0 os-release/lsb-release payloads, the issue and
   motd banners, purges the branding-only Xubuntu packages, points
   the Xfce desktop default at OC1's wallpaper when present, and
   selects a registered MetaOS Plymouth theme when one exists. It
   must run AFTER the theme step: its wallpaper default points at a
   file the theme step installs. It is idempotent; a second run
   exits 0. It removes no Xfce functional package.
5. Identity gate, before any ISO is generated: run
   `dexubuntu/verify-rootfs.sh` against the chroot rootfs. All 7
   checks must PASS (os-release PRETTY_NAME, os-release NAME,
   os-release free of the Xubuntu string, lsb-release DISTRIB_ID,
   hostname, issue banner, Xubuntu asset dirs absent). Any FAIL is
   a named cut failure: stop, do not generate the ISO, do not
   quietly pass. Said plainly, the gate covers only those 7 checks.
   The apply step also changes the hosts entry, issue.net, the
   motd header, and the artwork dir; verify does not check those,
   and Milo has asked Pax whether that gap is intentional or a
   later verify round. Until Pax answers, those effects are
   apply-script claims, not gate-proven facts.
6. Install the first-boot pieces from this slice:
   - `firstboot/metaos1-firstboot.sh` → `/usr/local/bin/metaos1-firstboot`
     (executable, root-owned)
   - `firstboot/metaos1-firstboot.service` → `/etc/systemd/system/`
   - `systemctl enable metaos1-firstboot.service`
7. Install the defaults:
   - `defaults/mimeapps.list` → `/etc/xdg/mimeapps.list` (system
     default; a user file overrides it later, which is normal)
8. Leave the installer exactly as Xubuntu/Calamares ships it. The
   preseeded installer is Buffy's lane. Leave core app configs and
   the browser default to Bond's lane, and agent autostart to OC2's
   lane. This slice recolors nothing itself.
9. Generate the ISO in Cubic. Record: source ISO filename + SHA-256,
   output ISO filename + SHA-256, package list hash, the
   `validate.py` result, and the `verify-rootfs.sh` 7/7 result, in
   the cut record.

## Out of scope for this slice (other lanes, not silently dropped)

- Plymouth splash: Buffy.
- Login/desktop theme, lock screen, top bar, dock, launcher, GTK
  recolor, wallpaper pack, font picks, brand kit: OC1.
- Core apps and their configs, Chromium default + start page: Bond.
- Agent-layer services autostarting at login: OC2.
- Installer preseed + install-path testing: Buffy.
- Bare-metal kernel (2.0 track): Rowan. Nothing in this ISO waits
  on it.

## First boot, what actually happens

The installer (Buffy's lane) creates the user account. On first boot
into the installed system, `metaos1-firstboot.service` runs once:
the script applies the system mimeapps defaults for the console
user's home if they are missing, writes
`/var/lib/metaos1-firstboot.done`, and exits. On later boots the
unit's condition (`ConditionPathExists=!/var/lib/metaos1-firstboot.done`)
skips it. It never prompts — an unattended boot must never wedge on
a question — and it never writes a credential anywhere.
