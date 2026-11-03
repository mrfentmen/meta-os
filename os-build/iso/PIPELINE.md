# MetaOS 1.0 ISO pipeline — operator runbook

`merge-layers.sh` is the full reproducible build: layered Xubuntu base in,
single-squashfs MetaOS ISO out. This file is the runbook for the human (or
lane agent) who presses the button on a Linux host. It documents the exact
commands, expected outputs, gates, and every known failure mode from the
live build (`MERGE_NOTES.md`). No stage here was executed during the
hardening pass that wrote it — `sh -n` only.

Related: `BASE_FACTS.md` (measured base), `MERGE_NOTES.md` (execution
record), `LANE_TAKEOVER.md` (why option B), `ACCEPTANCE.md` (VM proof).

## 0. Host prereqs (all mandatory)

| need | check |
|---|---|
| Docker, Linux containers, daemon up | `docker info` exits 0 |
| ~15 GB free where `$WORK` and `$OUTDIR` live | `df -h` (live build used 667 GB free; the work tree peaks near ~12 GB + 4 GB ISO) |
| Base ISO: `xubuntu-24.04.5-desktop-amd64.iso` | `shasum -a 256 <base>` must print `4ed869eb…69e8` (full hash in `BASE_FACTS.md`); or verify against Canonical's `SHA256SUMS` |
| This repo at branch `opencode1/pipeline` (or later) | `git log --oneline -1 -- os-build/iso/merge-layers.sh` |

Also run the Mac-side lane gate first — it catches config drift before you
spend 30+ min on a build:

```sh
os-build/iso/test/run_checks.sh   # expect: 9 pass, 0 fail (QEMU dry frame may SKIP without qemu)
```

## 1. One-command build (Docker)

The script runs **inside** Linux as root. Mount the base ISO read-only, a
Linux work volume (NOT a macOS bind mount — xattrs/case-insensitivity break
unsquash), a macOS bind mount for export, and the lane dir so the sibling
scripts resolve:

```sh
BASE=/private/tmp/xubuntu-base.iso   # adjust
OUT=/path/to/macos/export            # bind mount, ~6 GB free (tree + ISO)
mkdir -p "$OUT"

docker run --rm --privileged \
  -v "$BASE:/iso/base.iso:ro" \
  -v isowork:/root/isowork \
  -v "$OUT:/work" \
  -v "$PWD/os-build/iso:/build:ro" \
  ubuntu:24.04 bash -c '
    mkdir -p /iso-mnt &&
    mount -o loop,ro /iso/base.iso /iso-mnt &&
    ISO=/iso/base.iso SRCDIR=/iso-mnt WORK=/root/isowork OUTDIR=/work \
      sh /build/merge-layers.sh'
```

Why `--privileged`: the script bind-mounts `/dev`, mounts `proc`/`sysfs`,
and chroots — all need real privileges. Why a named volume for `$WORK`:
squashfs + chroot on a macOS bind mount fails on permissions and filenames.

`OUT_ISO` (optional env): final ISO path, default
`$WORK/metaos-1.0-amd64.iso`, copied to `$OUTDIR` at export.

## 2. Stages, expected outputs, gates

| # | script echo | what it does | expected output |
|---|---|---|---|
| 1 | `tools-ok` | installs xorriso, squashfs-tools, rsync, initramfs-tools-core | `tools-ok` |
| 2 | `extract ISO tree` | xorriso copy of the base ISO to `$WORK/iso` | file list tail |
| 3 | `unsquash layers` | both squashfs layers out, 11 char-device whiteouts excluded via `-exclude-file` | silent (redirected) |
| 4 | `overlay minimal, then std` | rsync minimal/ then std/ into rootfs; clears dev/proc/sys/tmp | — |
| G1 | `GATE 1` | **FAIL if rootfs lacks bin/etc/usr or /bin/sh** | `gate: PASS (rootfs has bin/etc/usr + sh (... entries))` |
| 5 | `foreign-arch chroot setup` | ARM host → installs qemu-user-static, stages `qemu-x86_64-static` in chroot; x86_64 → skip; then chroot `true` smoke test | `foreign-arch host ...` or `native x86_64 host...` |
| 6 | `provision in chroot` | apt installs **calamares plank fonts-inter user-setup casper** | silent |
| G2 | `GATE 2` | **FAIL unless all 5 debs report `install ok installed`** (versions printed) | `gate: PASS (5/5 provision packages installed)` |
| 7 | `Meta payload` | runs sibling `provision.sh --no-initramfs` (theme, Calamares config, hook, autostart); **FAILs if sibling/payload dirs missing** | `provision: provision complete...` |
| P | `payload gate` | **FAIL if theme/settings/hook/autostart absent from rootfs** | `gate: PASS (Meta payload present in rootfs)` |
| 8 | `live-session files` + `initramfs-conf transplant` + `kernel-module transplant` | unsquashes `.live` layer paths (skel, casper.conf, initramfs conf.d/hooks, modules); copies what exists; aligns `LAYERFS_PATH` default to `filesystem.squashfs` | `transplanted ...` lines; `WARN` lines if a path is absent from the layer (non-fatal by design) |
| 9 | `rebuild initrd` | `update-initramfs -u -k <newest kver>` in chroot; installs to `casper/initrd`; **FAILs if no kver or no `casper/initrd` in the base tree** | `target kernel: ...`, `initrd installed: ...(size)` |
| G3 | `GATE 3` | **FAIL if `lsinitramfs` counts < 40 casper files in the new initrd** | `gate: PASS (initrd casper file count N >= 40)` |
| 10 | `grub finalize` | calls sibling `finalize-iso-tree.sh` (layerfs-path + serial console + Meta branding strings); inline fallback + WARN if sibling missing | `grub: layerfs=N console=M` |
| 11 | (grub assert) | **FAIL if grub.cfg lacks `layerfs-path=filesystem.squashfs` or `console=ttyS0`** | `gate: PASS (grub carries layerfs-path + serial console)` |
| 12 | `manifest regen` | `dpkg-query` from the new rootfs; **FAIL if empty or lacks calamares** | `manifest: NNNN packages` (live build: 1857) |
| 13 | `repack single squashfs` | `mksquashfs` xz, 128K blocks; deletes the 3 layered sources | silent |
| G4 | `GATE 4` | **FAIL if `filesystem.squashfs` missing or ≤ 1 GB** | `gate: PASS (filesystem.squashfs 2.9G > 1 GB)` (live size 2.9 GB) |
| 14 | `rewrite install-sources.yaml` + md5sum refresh | single `metaos-desktop` source; `filesystem.size` from the new rootfs; md5sum.txt refreshed if present | — |
| 15 | `rebuild bootable ISO` | `xorriso -boot_image any replay` clones base El Torito + MBR/GPT; writes `.sha256` | `iso: ...(size) sha256 ...` |
| G5 | `GATE 5` | **FAIL unless El Torito reports exactly 2 boot images (BIOS + UEFI)** | `gate: PASS (El Torito BIOS + UEFI entries present (2/2))` |
| 16 | `export` | `chmod -R u+rwX,a+rX` (macOS bind-mount readability), copies tree + ISO + sha256 to `$OUTDIR` | `ls -la` of both artifacts, `ALL-DONE` |

Re-run any gate by hand (paths are inside the container):

```sh
# G1: [ -d $WORK/rootfs/bin ] && [ -d $WORK/rootfs/etc ] && [ -d $WORK/rootfs/usr ]
# G2: chroot $WORK/rootfs dpkg-query -W -f='${Status}\n' calamares plank fonts-inter user-setup casper
# G3: lsinitramfs $WORK/iso/casper/initrd | grep -c casper        # >= 40
# G4: stat -c %s $WORK/iso/casper/filesystem.squashfs             # > 1073741824
# G5 (also runnable on the Mac against the exported ISO):
xorriso -indev metaos-1.0-amd64.iso -report_el_torito as plain
#    expect exactly 2 "Boot image" entries: BIOS eltorito + appended EFI partition
```

## 3. Known failure modes (from the live build — all baked into the script)

| symptom | cause | fix (now in-script) |
|---|---|---|
| unsquashfs fails creating `var/lib/swcatalog/yaml/*` char devices | 11 whiteouts (0,0) in the layers | `-exclude-file` (§3); note `-ef` is the wrong flag (extract-only) |
| `chroot: failed to run command '/bin/bash': Exec format error` | ARM host, x86_64 rootfs | qemu-user-static stage (§5); Docker Desktop pre-registers binfmt |
| initramfs shell: `File system layers are missing` | stock initrd defaults `LAYERFS_PATH=minimal.standard.live.squashfs` | grub `layerfs-path=filesystem.squashfs` (finalize) + initrd default realigned + rebuild (§8–10) |
| greeter shows only `Other...`, no live user | `user-setup-apply` lives only in the `.live` layer; `casper-bottom/25adduser` fails | `user-setup` in the apt line + skel/casper.conf transplant (§6, §8) |
| grub edits vanish after export | tree exports clobber `grub.cfg` | finalize call + assert counts (§10–11); standalone re-apply: `sh grub-fix.sh <tree>/boot/grub/grub.cfg` |
| `permission denied` reading the export on the Mac | root-owned bind-mount files | export chmod stage (§16) |
| wallpaper rays render green-cast under QEMU std VGA | palette/quirk, cosmetic | verify on real hardware; theme-lane follow-up, not a build gate |
| live session still says "xubuntu" (hostname/branding) | base strings survive the merge | theme-lane follow-up (`.disk/info` is already rewritten to `MetaOS 1.0 LTS`) |

## 4. After the build (Linux host)

```sh
os-build/iso/build_iso.sh --inspect metaos-1.0-amd64.iso   # 12 payload paths inside the squashfs
os-build/iso/tools/vm_install_proof.sh --iso metaos-1.0-amd64.iso --keys ret,ret,ret,ret --reboot
# frames land in proof/<stamp>/; see ACCEPTANCE.md for the H+2/H+8 checklists
```

## 5. What this hardening pass could NOT verify without a run

1. **Exact `.live`-layer paths** for the initramfs conf transplant
   (`etc/initramfs-tools/conf.d`, `usr/share/initramfs-tools/{conf.d,hooks,scripts}`)
   and the module dirs (`lib/modules` vs `usr/lib/modules`): the script
   extracts/copies whatever exists and WARNs (never fails) on absence, but
   the true listing needs `unsquashfs -l` on the base ISO in Linux.
2. **`casper/initrd` filename**: assumed from the grub/initrd convention;
   the script FAILs loudly listing the actual `casper/` contents if absent.
3. **`xorriso -report_el_torito as plain` output shape**: the G5 counter
   greps `boot image` case-insensitively and prints the full report on
   failure — if xorriso words it differently, the gate fails loud and the
   operator adjusts the pattern to the printed text.
4. **End-to-end run**: no Docker build, no chroot, no boot was performed
   here (merge build in flight on this box). First green run owns updating
   the `WARN`-path notes and the live size figures above.
