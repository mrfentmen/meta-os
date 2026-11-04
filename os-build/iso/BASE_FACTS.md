# Reference base ISO — measured facts (2026-11-02 22:2x EST)

File: `/private/tmp/xubuntu-base.iso` (5,211,408,384 bytes ≈ 4.9 GiB).
Identity: **Xubuntu 24.04.5 LTS "Noble Numbat" — Release amd64 (20260908.2)**,
from `.disk/info`.

## It is the official image (verified, not assumed)

```
$ shasum -a 256 /private/tmp/xubuntu-base.iso
4ed869ebf2b9f2f6118c1b60b9ed07576e8fe3d5cdfe10aae06869e669878b81

$ curl -fsSL https://cdimage.ubuntu.com/xubuntu/releases/24.04.5/release/SHA256SUMS | grep desktop-amd64
4ed869ebf2b9f2f6118c1b60b9ed07576e8fe3d5cdfe10aae06869e669878b81 *xubuntu-24.04.5-desktop-amd64.iso
```

Exact match against Canonical's published sums. This is the same hash the
chat reported for the theme lane's download, so both lanes are on one image.

## It does NOT ship `casper/filesystem.squashfs`

`bsdtar -tf` on the ISO lists:

| path | bytes | what it is |
|---|---|---|
| `casper/minimal.squashfs` | 2,382,872,576 | minimal desktop source |
| `casper/minimal.standard.squashfs` | 3,451,191,296 | standard desktop source (**default**) |
| `casper/minimal.standard.live.squashfs` | 3,845,931,008 | live-session layer |
| `casper/filesystem.size` | 9,679,994,880 | **exact sum of the three layers** |
| `casper/install-sources.yaml` | — | declares the sources, `type: fsimage-layered` |

2,382,872,576 + 3,451,191,296 + 3,845,931,008 = **9,679,994,880** — byte-exact.
So the three images are additive layers in that order, and the filesystem is
assembled at boot; there is no single root image to unpack.

`install-sources.yaml` declares two sources (`xubuntu-desktop-minimal` →
`minimal.squashfs`, default false; `xubuntu-desktop` →
`minimal.standard.squashfs`, default true), both `type: fsimage-layered`.
The `.live` layer is applied on top for the live session.

## Package facts from `casper/filesystem.manifest` (1,876 debs)

| package area | count | note |
|---|---|---|
| `plymouth`, `plymouth-label`, `-theme-xubuntu-*` | 5 | splash stack present; our theme can replace theirs |
| `lightdm`, `lightdm-gtk-greeter`, `…-settings` | 3 | the greeter exists (OC1's lane target) |
| `xfce4-panel`, `xfdesktop4`, `xfce4-session` | present | desktop present |
| `casper` | 1.498 | live-boot tooling |
| `squashfs-tools` | present | `mksquashfs` exists inside the live image |
| `xubuntu-desktop`, `xubuntu-desktop-minimal` | 2.262 each | metapackages |
| **`calamares`** | **0** | absent from all four manifests |
| `ubiquity`, `subiquity`, `ubuntu-desktop-provision` | 0 each | not present as debs |
| `snapd` | present | — |

**Inference, labelled as such:** the installer is delivered as a snap
(`snapd` is present; snaps do not appear in the deb manifest), not as a deb.
That has to be confirmed at boot before the autostart hand-off is final.

## What this means for the lane

1. **`build_iso.sh --iso` must not patch this image.** It now detects the
   layout and refuses a layered base with an actionable message
   (`--base-info` prints the table above). Patching
   `/casper/filesystem.squashfs` would have targeted a file that does not
   exist.
2. **Calamares `unpackfs` cannot consume layers.** It expects one root
   image. A Calamares install of this base needs one merged
   `casper/filesystem.squashfs` produced at build time. For the default
   source that merge is `minimal.squashfs` **then**
   `minimal.standard.squashfs` (the `.live` layer is live-session only,
   not installed), i.e. 5,833,063,872 bytes uncompressed.
3. **The base has no Calamares.** `provision.sh` installs it in the chroot,
   which needs network in the chroot at build time (already implemented,
   currently unrun).
4. **Cubic may or may not handle layered sources.** Cubic historically
   extracts a single `filesystem.squashfs`. Hana's base lane should verify
   that before the H+2 cut, because it changes which build path exists.

## Options (decision is Pax/Hana's, not mine to take alone)

- **A — change base** to a flavour ISO that ships `casper/filesystem.squashfs`.
  Cheap if one exists in the 24.04.x line; that must be verified, not
  assumed, with `--base-info`.
- **B — merge layers at build time** (recommended for this verified image):
  unsquash `minimal.squashfs`, overlay `minimal.standard.squashfs` in that
  order, provision, repack one `casper/filesystem.squashfs`, rewrite
  `install-sources.yaml` to a single source. Needs Linux + root + ~12 GB
  free in the work dir. Keeps Calamares and keeps this hash.
- **C — keep the distro installer** and drop the Calamares box. Contradicts
  `METAOS_1.0_12H_PLAN.md`; only Pax can change that.

My recommendation is **B**, because the image is already here and verified,
and the merge is mechanical. It is not built yet; this file records the
measurement, not a claim that it works.

---

# arm64 base — decision of lane C, 2026-11-03 (verified, not assumed)

File: `/tmp/ubuntu-24.04.5-desktop-arm64.iso` (3,967,463,424 bytes ≈ 3.7 GiB).
Identity: **Ubuntu 24.04.5 LTS "Noble Numbat" — Release arm64 (20260908)**,
from `.disk/info`.

## It is the official image (verified, not assumed)

```
$ shasum -a 256 /tmp/ubuntu-24.04.5-desktop-arm64.iso
2be09ca883921bff6d8e6b0bfbafd13e32436553b7086f33bce3a4c5bad8bd14

$ curl -fsSL https://cdimage.ubuntu.com/ubuntu/releases/24.04.5/release/SHA256SUMS | grep desktop-arm64
2be09ca883921bff6d8e6b0bfbafd13e32436553b7086f33bce3a4c5bad8bd14 *ubuntu-24.04.5-desktop-arm64.iso
```

Exact match against Canonical's published sums (ubuntu/releases/24.04.5).

## It is layered, like the amd64 Xubuntu base

`casper/` carries `minimal.squashfs` (1.9 GB) + `minimal.standard.squashfs`
(480 MB) + `minimal.standard.live.squashfs` (1.19 GB), selected by
`casper/install-sources.yaml` (`type: fsimage-layered`). There is no
`casper/filesystem.squashfs`. Same merge strategy as BASE_FACTS option B,
but native: host and rootfs are both aarch64, so no qemu-user-static.

## Why arm64 is the lane decision (see os-build/lanes/C_ISO_REPORT.md)

The working MetaOS system (`/tmp/metaos.ext4`) is arm64 and boots on this
Mac under `qemu-system-aarch64 -M virt -cpu host -accel hvf`. The amd64
base can only boot under full x86 emulation here. One architecture ships:
arm64. The amd64 lane (`merge-layers.sh`, this file's first half) stays as
the separate-build record; it is not deleted, but no amd64 ISO is produced
by lane C.

