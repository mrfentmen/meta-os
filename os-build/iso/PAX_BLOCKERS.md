# PAX — blockers and asks, Buffy boot + installer lane

From: Buffy. Branch: `buffy/boot-installer` (off main `80a7886c`).
Full detail: `os-build/iso/LANE_REPORT.md`. Post text: `ROOM1_POST.md`.

## Blocked (hard, cannot be worked around from this Mac)

1. **ISO build.** Needs Linux + root + `xorriso unsquashfs mksquashfs`.
   macOS has none of the first three; Docker on this Mac cannot loop-mount,
   so a container is not a workaround either.
2. **Install → login proof (the lane's acceptance artifact).** Needs the ISO
   from (1), then `tools/vm_install_proof.sh --iso … --reboot`. QEMU and the
   harness are ready on this machine; only the image is missing.

Neither is a code problem. If any lane has a Linux box with root — Hana's
Cubic host is the natural candidate — this closes in one build plus one VM
run.

## Blocked (soft, needs a decision)

3. **Base ISO point release.** The plan says Xubuntu core + Cubic; it does
   not pin a version. My build takes the ISO as an argument, so I can land
   either — but the acceptance proof should name one. Hana's call.
4. **Greeter handoff.** The installer enables LightDM and disables
   autologin, but does not theme the greeter. I need OC1's greeter session
   name and theme package path so `meta-branding.sh` points at it instead of
   leaving the base greeter.

5. **Base layout decision (new, measured).** The only base ISO on this
   machine is the official Xubuntu 24.04.5 desktop image, checksum-verified,
   and it ships **layered** squashfs (`minimal.squashfs` +
   `minimal.standard.squashfs` + `.live`), not the single
   `casper/filesystem.squashfs` that Calamares `unpackfs` and every remaster
   recipe assume. Evidence: `os-build/iso/BASE_FACTS.md` (layer sizes sum
   byte-exactly to `filesystem.size`; zero calamares in 1,876 debs).
   - Option A: switch base to one that ships `filesystem.squashfs`
     (verify with `build_iso.sh --base-info`, do not assume).
   - Option B (my recommendation): merge the layers at build time into one
     root image, then the existing recipe works. Needs Linux + root +
     ~12 GB work dir.
   - Option C: keep the distro installer and drop the Calamares box — a
     plan change only you can make.
   Until this is decided, H+8 cannot start even with a Linux host.

## What I am NOT claiming

- No ISO exists.
- No install has been attempted.
- The Plymouth script has never run under plymouth.
- 36 local assertions cover structure, cross-references and asset hashes
  only. Milo should record them as CODE-INSPECTED / LOCAL-CHECK, not
  VERIFIED, until the Linux run produces frames.

## What I suggest for the 12-hour clock

- H+0..H+1: you (or Hana) give me the Linux chroot path; I build.
- H+1..H+2: `--root` provision + Cubic Generate, or `--iso` patch; sha256
  goes in the room-1 post.
- H+2..H+3: install walkthrough with screendumps; that is the acceptance
  frame set, plus the installed-boot login frame.
- If no Linux host appears by H+2, the honest fallback is: ship the
  documented build + proof commands and mark the lane **CODE-COMPLETE,
  UNPROVEN**. Do not let anyone present the splash mock as a boot.
