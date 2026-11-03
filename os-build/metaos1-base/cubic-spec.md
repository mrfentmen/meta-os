# Cubic project definition — MetaOS 1.0 base (Hana lane)

Tool: Cubic (Custom Ubuntu ISO Creator), run on the cut machine.
Base: the reference Xubuntu ISO, x86_64 — Xubuntu 24.04.5, per the
decoupling amendment on main @d835b59a (same file every lane tests
against; no lane waits on another). This supersedes slice 1's
"pick the current LTS at cut time" line. The cut record still pins
the exact filename + SHA-256 actually used; this slice names the
version, not a checksum it has not verified — the checksum value
comes from the frozen contracts / cut record at cut time, never
from a guess here.

## Steps, in order

1. Create a new Cubic project. Point it at the reference ISO
   (Xubuntu 24.04.5).
2. In the Cubic terminal (chroot), apply `packages.txt`:
   - `apt update`
   - install every package under `ADD:` (one `apt install -y` run)
   - remove every package under `REMOVE:` — slice 1 lists none, so
     this step is a no-op until a later slice names a removal with a
     reason and a Milo audit row.
   - `apt autoremove -y` only if a removal was made; otherwise skip
     it, so the base is not trimmed by accident.
3. Install the first-boot pieces from this slice:
   - `firstboot/metaos1-firstboot.sh` → `/usr/local/bin/metaos1-firstboot`
     (executable, root-owned)
   - `firstboot/metaos1-firstboot.service` → `/etc/systemd/system/`
   - `systemctl enable metaos1-firstboot.service`
4. Install the defaults:
   - `defaults/mimeapps.list` → `/etc/xdg/mimeapps.list` (system
     default; a user file overrides it later, which is normal)
5. Leave the desktop theme, wallpaper, login theme, dock, launcher,
   and browser exactly as Xubuntu ships them. Those are OC1's and
   Bond's lanes, not this one. Do not recolor anything from this
   slice.
6. Leave the installer exactly as Xubuntu/Calamares ships it. The
   preseeded installer is Buffy's lane.
7. Generate the ISO in Cubic. Record: source ISO filename + SHA-256,
   output ISO filename + SHA-256, package list hash, and the
   `validate.py` result, in the cut record.

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
