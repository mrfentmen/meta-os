# Layer merge — execution record (OpenCode 1, lane takeover)
Base verified: xubuntu-24.04.5-desktop-amd64.iso, sha256 4ed869eb (match).

## Findings (correcting/confirming the handoff)
- 11 char-device whiteouts (0,0) under var/lib/swcatalog/yaml — excluded
  via `-exclude-file` (unsquashfs `-ef` means extract-only; the flag is
  `-exclude-file`).
- Mount nuance: macOS reads the ISO9660 wrapper fine; only squashfs
  contents need Linux. On-disc sizes sum to 4.00 GB; the 9.68 GB figure
  is uncompressed total. Both additive in their own domain.
- minimal/standard are base + delta (not alternatives): standard alone
  has only etc/run/snap/usr/var (59k files) on top of minimal's full
  tree (80k files). Merge = extract separately, rsync overlay in order.
- Whiteout char devices cannot be created in the merge container's
  unsquashfs path — excluded, not fabricated. Dangling apt-list
  symlinks left as-is (harmless).

## What ran
merge-layers.sh: extract ISO tree, unsquash both layers (excludes),
rsync overlay, dev-null cleanup, chroot provision (calamares, plank,
fonts-inter — note: calamares-settings-ubuntu does not exist; branding
is ours), Meta theme files baked in, mksquashfs single
casper/filesystem.squashfs (2.9 GB), manifest regenerated from the new
rootfs (1857 pkgs), install-sources.yaml rewritten to one source,
ISO repacked with xorriso (original El Torito layout cloned: BIOS
eltorito + appended EFI partition, protective MBR + GPT).
chroot needed qemu-user-static (ARM host, x86_64 rootfs; binfmt
x86_64 pre-registered by Docker Desktop).

## Update: single squashfs boots to greeter (2026-11-02 ~22:3x EST)
- layerfs-path kernel param required: the stock initrd hardcodes
  LAYERFS_PATH=minimal.standard.live.squashfs (initramfs conf.d).
  Fix: `layerfs-path=filesystem.squashfs` on the grub linux lines.
  Without it: initramfs shell, "File system layers are missing".
- Proof: MetaOS-1.0.iso (4.1 GB) boots to LightDM with the Meta rays
  wallpaper. Serial shows systemd targets + lightdm starting.
- Open: greeter shows "Other..." only — no live user. Cause found:
  user-setup-apply lives ONLY in the excluded .live layer, so
  casper-bottom/25adduser fails and no live user is created.
  Fix applied to rootfs: apt install user-setup + live skel/casper.conf.
  Repacked, ISO rebuilt, boot retest in flight.

## Update 2: BOOTED TO DESKTOP (2026-11-02 ~22:5x EST)
- user-setup installed in chroot (+ live skel/casper.conf) → live user
  created, autologin works. Proof: os-build/iso/proof/metaos-first-desktop.png
  — Xfce desktop, top panel, Trash/Home, whisker menu, Meta rays wallpaper.
- воспроизводимо: single filesystem.squashfs (2.9 GB) + layerfs-path grub
  param + grub console. ISO: 4.1 GB, boots under TCG in ~9 min.
- Known cosmetic: wallpaper rays render green-cast under QEMU std VGA —
  palette to be verified on real hardware. Session still says xubuntu
  (hostname/branding follow-up for the theme lane).
- Grub edits now protected by /tmp/grub-fix.sh (must be promoted into
  the lane repo — next commit).
