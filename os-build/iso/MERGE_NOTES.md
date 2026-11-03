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
