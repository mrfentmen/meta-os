# INITRD forensics: stock vs rebuilt — why find_livefs rejects a present medium

Date: 2026-11-03. Scope: `metaos-1.0.iso`
sha256 `942018bd…578` (single `filesystem.squashfs` + rebuilt initrd) drops to
initramfs with `Unable to find a medium containing a live file system`, while the
stock ISO boots. Investigation was read-only (listings, greps, diffs, one
`docker cp` of the 52 MB initrd to host scratch); no VM/QEMU boots, no image
repacks, mergebox rootfs/ISO tree untouched.

Artifacts compared (all hashes/bytes verified, not assumed):

| artifact | path | identity |
|---|---|---|
| stock initrd | `/tmp/iso-mnt/casper/initrd` (bind-mounted `:ro` into a throwaway `ubuntu:24.04` container) | 99,906,755 B |
| rebuilt initrd | mergebox `/root/isowork/rootfs/boot/initrd.img-7.0.0-31-generic` ≡ `/root/isowork/iso/casper/initrd` (md5 `37e6e39d…4ced` both) ≡ host `/tmp/isowork/isowork/casper/initrd` (52,085,366 B) | 52,085,366 B |
| tested ISO tree | host `/tmp/isowork/isowork/` (export 2026-11-03 00:02, ISO built 00:02:57) | grub HAS `layerfs-path`+console fixes |
| mergebox ISO tree | mergebox `/root/isowork/iso/` (initrd refreshed 04:59) | grub currently STOCK (see §4) |

Listings: `lsinitramfs -l` on both → stock 2760 entries, rebuilt 2199.
Both unpacked (`unmkinitramfs`) to host scratch and diffed file-by-file.

## (a) Stock-vs-rebuilt deltas

### A1. THE delta — `conf/uuid.conf` (root cause, §c)

| | stock initrd | rebuilt initrd | ISO tree `.disk/casper-uuid-generic` (host export AND mergebox tree) |
|---|---|---|---|
| `conf/uuid.conf` | `7e44816f-6db3-4bb5-a866-7f445ce36779` | `7337b2ad-5e3e-4559-b668-51d8fba590e3` | `7e44816f-6db3-4bb5-a866-7f445ce36779` |

The rebuilt initrd carries a **fresh random UUID that matches nothing on the
ISO**. Mechanism (§c): casper's initramfs hook mints it at build time.

### A2. casper scripts — functionally identical

- `scripts/casper`: **byte-identical** stock vs rebuilt (casper 1.498 in both:
  stock `minimal.standard.live.manifest` and rootfs `dpkg-query` agree).
- `scripts/casper-bottom`: only delta is `48xubuntu_maybe_ubiquity` present in
  stock, absent in rebuilt (+2 lines in `ORDER`). It is an installer shim that
  runs *after* the medium is found — inert for this failure.
- `scripts/casper-premount` (`10driver_updates`, `20iso_scan`): identical.
- `scripts/local`: identical.
- Missing in rebuilt `scripts/{local-top,local-block}` (`cryptopensc`,
  `cryptroot`, `dmraid`, `zfs`) and crypto entries in `local-bottom/ORDER`:
  all encryption/LVM/ZFS unlock hooks. A plain live-CD boot never enters them.

### A3. kernel modules — boot path coverage identical

Both initrds target `usr/lib/modules/7.0.0-31-generic`, and
`/casper/vmlinuz` *is* `7.0.0-31-generic`
(`strings` → `#31~24.04.1-Ubuntu SMP PREEMPT_DYNAMIC`). No mismatch.

| driver | stock | rebuilt | note |
|---|---|---|---|
| `squashfs`, `cdrom`, `sr_mod`, `loop`, `sd_mod`, `virtio_blk`, `ata_piix` | builtin (`modules.builtin`, byte-identical 10431 B) | builtin | QEMU cdrom path covered |
| `isofs`, `overlay` | `.ko.zst` module | `.ko.zst` module | present in both |
| delta (105 modules, all absent in rebuilt) | crypto (`aesni-intel`, `chacha`, `adiantum`, …), `dm-*`, `raid0/1/10/456`, `zfs`+`spl`, `zstd`(crypto API) | — | none on the iso9660→squashfs→overlay path |

### A4. binaries / udev / firmware

- `bin/`, `sbin/`: identical sets. `usr/sbin` delta is crypt/LVM/RAID/ZFS
  tooling present only in stock (`cryptsetup`, `lvm`, `dmraid`, `zfs`,
  `kpartx`, …); rebuilt adds only `modprobe`/`rmmod`, `mkfs.ext4`,
  `mount.ntfs*`. `blkid`, `busybox`, `mount` present in both.
- udev: `cdrom_id` + `60-cdrom_id.rules` present in **both** (2 hits each).
  Rebuilt lacks only dm/lvm/kpartx/zvol rules — inert here.
- `usr/lib/zfs-linux/*`, ISH sensor-hub firmware, extra crypto `.ko`s account
  for the rest of the ~560-entry count gap. None reachable during medium scan.
- `etc/casper.conf` (live-user identity): identical (`ubuntu`/`ubuntu`/…).
- `conf/conf.d`: rebuilt correctly bakes `LAYERFS_PATH=filesystem.squashfs`
  (stock: `minimal.standard.live.squashfs`); `casperize.conf`
  (`CASPER_GENERATE_UUID=1`) identical; only `zfs` conf-d snippet missing.
- `md5sum.txt` in the tested tree is stale for the edited `grub.cfg`
  (md5 `dd6d716b…` vs recorded `2c0467f5…`). Hygiene only: nothing on the
  default boot entries enforces it (no `integrity-check`).

### A5. boot cmdline (tested tree, `/tmp/isowork/isowork/boot/grub/grub.cfg`)

```
linux  /casper/vmlinuz layerfs-path=filesystem.squashfs  console=ttyS0 --- quiet splash
initrd /casper/initrd
```

`layerfs-path` correct, target `casper/filesystem.squashfs` (3,100,311,552 B)
exists, `.disk/casper-uuid-generic` present. No `uuid=`, no `ignore_uuid`, no
`live-media=` override → the initrd-baked UUID check is **active**.

## (b) Every condition that yields "Unable to find a medium" — ranked

References are to the identical `scripts/casper` in both initrds.
`mountroot()` (l.901) → `find_livefs` loop (ll.946–960, 60 × 1 s retries) →
l.962–970: `panic "Unable to find a medium containing a live file system"`.
`find_livefs` (l.788) accepts a device only via `check_dev` (ll.725–772),
whose accept predicate is (ll.754–755):

```
is_casper_path($mnt) AND ( skip_uuid_check OR $UUID == blkid-fs-UUID OR matches_uuid($mnt) )
```

with `UUID=$(cat /conf/uuid.conf)` (l.9), `is_casper_path` = `$mnt/casper/`
holds ≥1 `*.squashfs` (ll.88–98), `matches_uuid` = some
`$mnt/.disk/casper-uuid*` content equals `$UUID` (ll.100–113, true
unconditionally iff `$UUID` empty).

| # | hypothesis | exact failing check | verdict |
|---|---|---|---|
| H1 | **Stale-vs-fresh UUID mismatch** | `$UUID`=initrd `7337b2ad…` ≠ ISO fs UUID (xorriso-minted) AND ≠ `.disk/casper-uuid-generic` (`7e44816f…`); no `ignore_uuid`/`uuid=`/`live-media=` on cmdline → `check_dev` rejects `/dev/sr0` every retry → l.970 panic | **CONFIRMED.** Explains the probe record exactly: medium present (`sr0`, `LABEL=METAOS_1_0`), correct cmdline, yet rejected. Also explains history: stock-initrd + new tree booted (UUIDs still matched), rebuilt-initrd fails. |
| H2 | Missing storage/cdrom/fs drivers | `get_fstype`/mount failing inside `check_dev` | RULED OUT (§A3: identical coverage; key drivers builtin). |
| H3 | Wrong layer path | `mount_images_in_directory` (ll.603–611) after medium found | RULED OUT: baked `LAYERFS_PATH` + cmdline agree, file present. (Its absence would print "File system layers are missing", a *different* panic we do not see.) |
| H4 | Missing `48xubuntu_maybe_ubiquity` | casper-bottom ORDER | RULED OUT: post-medium installer shim; and the panic precedes it. |
| H5 | Kernel/initrd mismatch | modules dir vs `/casper/vmlinuz` | RULED OUT: both `7.0.0-31-generic`. |
| H6 | Slow device enumeration | 60 s retry expiry | RULED OUT as primary: deterministic rejection of a visible `sr0` per probe, and stock initrd enumerates the same virtual hardware fine. |

Netboot (`do_netmount`, l.942) and `20iso_scan` paths are unreachable here
(`NETBOOT` unset, no `*.iso`-on-disk layout); `do_interactive_netmount`
(l.309) prints the distinct "Attempt interactive netboot" prompt, not our panic.

## (c) Top cause + precise fix

**Cause:** `update-initramfs -u` in the chroot regenerates
`conf/uuid.conf` because the rootfs carries
`/etc/initramfs-tools/conf.d/casperize.conf` with
`CASPER_GENERATE_UUID=1`, and the hook does (rootfs
`/usr/share/initramfs-tools/hooks/casper`, ll.85–88):

```sh
if [ "$CASPER_GENERATE_UUID" ]; then
    uuidgen -r > $DESTDIR/conf/uuid.conf
```

The new initrd's UUID (`7337b2ad…`) was never propagated to the ISO tree's
`.disk/casper-uuid-generic` (`7e44816f…`, carried over unchanged from the base
via `xorriso -osirrox`), so `matches_uuid` fails on the real medium while the
stock initrd kept matching. The pipeline's GATE 3 (casper file count ≥ 40)
cannot catch this — counts were 51 → 50, both passing.

**Fix (preserves stock semantics — keep the UUID check, sync it).**
After the `update-initramfs` step, before `xorriso`, extract the baked UUID
from the new initrd and write it into the ISO tree (one step in
`merge-layers.sh`, right after `cp …/initrd.img-$KVER $WORK/iso/casper/initrd`):

```sh
rm -rf "$WORK/uuidx" && unmkinitramfs "$WORK/iso/casper/initrd" "$WORK/uuidx"
cat "$WORK/uuidx/main/conf/uuid.conf" > "$WORK/iso/.disk/casper-uuid-generic"
rm -rf "$WORK/uuidx"
```

then rebuild + re-verify, and add **GATE 6** (fails the build instead of the boot):

```sh
INITRD_UUID=$(unmkinitramfs -l "$WORK/iso/casper/initrd" 2>/dev/null \
  | awk '$NF=="conf/uuid.conf"')  # or unpack as above and cat
[ "$(cat "$WORK/uuidx/main/conf/uuid.conf")" = "$(cat "$WORK/iso/.disk/casper-uuid-generic")" ] \
  || fail "initrd uuid.conf != ISO .disk/casper-uuid-generic (find_livefs would reject the medium)"
```

Accepted fallbacks (weaker — drop the wrong-medium guard): set
`CASPER_GENERATE_UUID` empty before `update-initramfs` (no `uuid.conf` baked
→ `UUID` empty → `matches_uuid` always true), or append `ignore_uuid` to the
grub `linux` lines in `finalize-iso-tree.sh`.

**Secondary flag (not this failure, will bite the next build):**
mergebox's live `/root/isowork/iso/` tree has been re-extracted since the
tested export — its `boot/grub/grub.cfg` and `.disk/info` are pristine stock
(Xubuntu branding, no `layerfs-path=`, no `console=ttyS0`, Sep-08 mtimes)
while `/tmp/isowork/isowork/` (the tested tree) has the fixes. The pipeline
already re-applies them via `finalize-iso-tree.sh`, but any hand-rolled
`xorriso` from mergebox's current tree would regress to the old
"File system layers are missing" failure. Always build through
`merge-layers.sh` end-to-end (it also refreshes `md5sum.txt`, which the tested
artifact lacked).

## Proof paths (re-run, all read-only)

```sh
# 1. baked UUIDs diverge; ISO tree still carries the stock one
docker exec mergebox unmkinitramfs /root/isowork/rootfs/boot/initrd.img-7.0.0-31-generic /tmp/uuidx >/dev/null \
 && cat /tmp/uuidx/main/conf/uuid.conf && rm -rf /tmp/uuidx
# → 7337b2ad-5e3e-4559-b668-51d8fba590e3
cat /tmp/isowork/isowork/.disk/casper-uuid-generic
docker exec mergebox cat /root/isowork/iso/.disk/casper-uuid-generic
# → 7e44816f-6db3-4bb5-a866-7f445ce36779 (both)
# 2. stock initrd's baked UUID equals the ISO one (why stock booted)
docker run --rm -v /tmp/iso-mnt:/mnt:ro ubuntu:24.04 bash -c \
 'apt-get update -qq && apt-get install -y -qq initramfs-tools-core cpio >/dev/null && unmkinitramfs /mnt/casper/initrd /tmp/sx && cat /tmp/sx/main/conf/uuid.conf'
# → 7e44816f-6db3-4bb5-a866-7f445ce36779
# 3. hook that mints the fresh UUID at every rebuild
docker exec mergebox sed -n '83,92p' /root/isowork/rootfs/usr/share/initramfs-tools/hooks/casper
# 4. the exact accept predicate + panic site in the (identical) casper script
sed -n '754,755p;969,970p' <stock scripts/casper>   # see §b
# 5. module/kernel equivalence
grep -c '\.ko\.zst' stock.list ours.list  # delta is crypto/dm/raid/zfs only
strings -a /root/isowork/iso/casper/vmlinuz | grep -m1 'Linux version'  # 7.0.0-31-generic
```
