# Meta OS base freeze (OS-005)

Frozen base: Debian 12 (bookworm) amd64. One base only. Nothing in
the os/ tree may name a second base.

## Source

The build route that produced the booting image is debootstrap, not
an ISO install. The exact base source is the debootstrap call pinned
in build-all.sh:

- Suite: bookworm
- Mirror: http://deb.debian.org/debian
- Architecture: amd64 (linux-image-amd64; the booted kernel is
  6.1.0-50-amd64)
- Variant: minbase, via build-all.sh

## Verification performed 2026-10-27

1. Tree scan: every file under os/ that names a distribution names
   bookworm only. No second base appears in the build scripts, the
   preseed answers, the package list, the units, the firstboot
   program, the tools, or the GRUB config. The scan is pinned by
   tests/test_os_base.py, which fails on any other release or distro
   codename in those files.
2. Build evidence: the image lane build.log records debootstrap rc=0
   for the bookworm rootfs (the run that produced the booting
   image).
3. Boot evidence: the lane boot-log.txt line 8 records Linux
   version 6.1.0-50-amd64 built with the Debian 12.2.0 toolchain,
   and the 2026-10-26 QEMU boot reached relay.target.
4. preseed.cfg names no suite and no mirror: it holds installer
   answers only, for the spec Packer route (OS-009). It is not a
   second base. Its suite pin is OS-009 follow-up, and when pinned
   it must name bookworm.

## Checksum: what exists and what does not

The debootstrap route downloads no ISO file, so there is no ISO
sha256 to record for the base itself. Recording an ISO checksum
for a file this pipeline never downloads would be false precision,
so none is claimed here.

The checksum artifact for built images is metaos-<date>.img.sha256,
emitted by build-image.sh beside each image. That artifact belongs
to OS-007 (a build from this tree), not to this freeze.

Standing flag, unchanged by this freeze: the lane artifact's
current sha256 no longer matches the sha256 recorded at boot time
(flagged 2026-10-27, re-verify owed). This freeze does not
re-baseline that hash and makes no new boot claim.

## Fallback pipeline divergences (OS-008)

The fallback ISO (os/build-live.sh plus os/live-build/) and the
primary image (os/build-packer.sh plus os/packer/) share one
base (Debian 12 bookworm amd64), one package name set
(os/packages.txt, rendered as real Debian package names in the
live-build package list), and one unit set (os/services/,
staged at fallback build time, enabled by the same list
os/build-image.sh wires). They differ in exactly these ways,
and in no other way the repo claims:

- Form: the primary artifact is an installable raw image; the
  fallback is a live ISO. It boots to a live crew session and
  does not install. A persistent install from the fallback ISO
  is not a claimed path.
- Installer: the fallback ISO carries no installer. The
  primary route installs unattended from preseed.cfg (OS-009);
  the fallback has no equivalent install step.
- Persistence: state written in a fallback live session does
  not survive a reboot unless the operator adds persistence.
  Firstboot secrets (OS-012) still enter once, at first boot,
  through the same firstboot program, but on live media they
  live in the session unless persisted by hand.
- Package versions: both artifacts resolve versions at build
  time. OS-010 has not pinned either one yet, so no version
  claim is made for the fallback ISO either.
- Provenance: neither artifact has a build from this tree yet
  (OS-007 and OS-008 are both config plus wrapper plus tests
  until a build host runs them). The divergences above are
  design facts of the two configs, not observations from built
  artifacts, and the boot-to-crew-session claim for the
  fallback ISO is unproven until a QEMU boot run says so.

## What this freeze does not do

- Not OS-007: no build from this tree is claimed.
- Not OS-009: preseed.cfg still has no unattended-install run and
  no suite pin.
- Not OS-010: packages.txt versions are still unpinned.
