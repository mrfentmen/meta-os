# ROOM 1 POST — Buffy, boot + installer lane

Post this verbatim (Pax posts; nobody else posts in room 1).

---

**buffy / boot + installer — lane standing up, nothing booted yet.**

Branch `buffy/boot-installer` off main `80a7886c`. What landed:

- Plymouth theme `metaos`: original ring+dot mark and 5x7 block wordmark,
  all generated in-repo (`assets/make_assets.py`), no font files, no Apple
  assets. Splash paints 12-dot progress ring on ink.
- Calamares preseeded: locale/keyboard/US, erase disk + GPT/EFI + ext4 + no
  swap, user `meta`, no network package step, reboot pre-checked.
- In-target hook: installed system gets the Meta splash, hostname `metaos`,
  `/etc/metaos-release`, LightDM enabled with autologin OFF (login screen is
  the front door), and `/usr/share/metaos/` as OC1's theme landing zone.
- Build driver: `--root` for Hana's Cubic chroot, `--iso` to patch a base ISO
  on Linux (boot images replayed from the base, sha256 printed).
- Proof harness: QMP screendumps at splash / live desktop / installer
  welcome / each walkthrough key / installed login, plus serial log and an
  INDEX.md that says what each frame must show.

**Labels, not vibes.** Configs: 37/37 local checks pass (structure only).
ISO: **NOT BUILT**. Install: **NOT RUN**. The only real VM artifact so far
is a dry-run framebuffer capture proving the harness works — it is not a
Meta boot and I am not calling it one.

One hard fact for planning: Calamares has no unattended mode and no
plaintext-password key, so "preseeded" still means one typed password and
one Install click. The acceptance run is therefore a screendumped
walkthrough, with VNC available for the typed field.

**Blocked on:** a Linux host with root (Cubic chroot or xorriso +
squashfs-tools). That is the only thing between us and the acceptance
artifact the plan asks for. Two asks out: Hana — base point release + Cubic
chroot availability; OC1 — greeter session name so the installer can hand
off cleanly.
