# dexubuntu — MetaOS 1.0 identity step

Removes the Xubuntu identity from the remastered image and stamps MetaOS
1.0 in its place. Identity only: it renames what the user sees as the OS.
It does not remove Xfce or any functional package, and it ships no
artwork (wallpapers, greeter and Plymouth art belong to the OC1 theme and
Buffy boot lanes).

## Where it runs

Inside the remaster chroot, in this order:

1. Hana's base packages (`os-build/metaos1-base/packages.txt`)
2. OC1's theme installer (`metaos-theme/apply.sh`)
3. This step: `apply-in-chroot.sh` from this directory

Works in Cubic's customisation phase or under Buffy's
`os-build/iso/build_iso.sh --root`.

## What it changes

- `/etc/hostname` -> `metaos`, `/etc/hosts` 127.0.1.1 entry follows
- `/etc/os-release` and `/etc/lsb-release` -> `identity/` payloads
  (PRETTY_NAME/NAME "Meta OS 1.0 (Ribbon)", ID=metaos, ID_LIKE=debian,
  VERSION_CODENAME=ribbon, no UBUNTU_CODENAME — byte-identical to
  `os-build/identity/debrand.sh` output; the apply step gates this and
  refuses a forked payload)
- `/etc/issue`, `/etc/issue.net`, `/etc/motd`, motd header -> Meta OS 1.0 (Ribbon)
- Purges branding-only packages: `xubuntu-default-settings`,
  `xubuntu-wallpapers`, `xubuntu-artwork`, `xubuntu-docs`; removes their
  asset dirs if a purge was partial
- If OC1's wallpaper is installed, writes the Xfce per-channel default
  pointing at it
- If a MetaOS Plymouth theme is registered, selects it as default

## Proof

`verify-rootfs.sh <rootfs>` checks the end state read-only: 7 checks
(os-release x3, lsb-release, hostname, issue banner, xubuntu asset dirs
absent). Exit 1 on any FAIL.

Pax, 2026-11-02: full cycle run in a real chroot on a planted
Xubuntu-identity rootfs — verify failed 7/7 before, apply exited 0,
verify passed 7/7 after, second apply also exited 0 (idempotent).
Not yet run against the real layered base image; that happens at the
first byte-build cut on the build host.
