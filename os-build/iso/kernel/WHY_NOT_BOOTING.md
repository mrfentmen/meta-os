# WHY_NOT_BOOTING — why our kernel cannot boot from the live-ISO chain (Lane F)

Status: NOT BUILT as an ISO-chain stage. The GRUB entry (`../grub/40_metaos.cfg`)
is DISABLED for exactly the reasons below — shipping it live would hang the
menu on a stanza that cannot succeed. No log faked (F5/F6 HARD RULE).

## The two boot stacks have nothing in common

Our kernel boots today ONLY one way: `os-build/rk007/disk.img` (20415488 B),
a raw BIOS disk whose first stages are the `bootloader` 0.11.17 crate's
`BiosBoot` image. The 0.11 stages parse the ELF
(`kernel/target/x86_64-unknown-none/debug/metaos-kernel`, 17588736 B), build
the `BootInfo` struct (framebuffer 1280x720 Bgr, memory map), and jump to the
kernel entry (`kernel/logs/E-boot-vnc.txt:4-23`, `KF-03 framebuffer … :24`,
alive `:26`). Reproduce: `os-build/rk007/build.sh` + QEMU `-drive
format=raw,file=os-build/rk007/disk.img` (`kernel/BUILD_LOG.md:153-166`).

The live ISO boots the opposite way: GRUB → Ubuntu Linux `casper/vmlinuz` +
`initrd` → casper/squashfs assembly → systemd → lightdm → XFCE session.
Every layer of that chain assumes the Linux ABI.

## Five concrete blockers (each independently fatal)

1. **No handoff protocol.** The ISO's GRUB can issue `linux` (bzImage) or
   `multiboot`/`multiboot2`. Our ELF is neither: it is a `bootloader_api`
   0.11 image expecting a `BootInfo` struct the 0.11 stages construct. GRUB
   supplies no `BootInfo`; there is no Multiboot header in our kernel to
   anchor a `multiboot` load. (Lane A: `LAYERS_TRUTH.md:A3` — bootloader
   0.9.35 dep hands the machine to the kernel in QEMU; the ISO GRUB is not
   that bootloader.)
2. **No storage driver.** The kernel has no PCI enumeration, no virtio-blk /
   AHCI / NVMe, no FAT/ext2/squashfs (`LAYERS_TRUTH.md:A3`, `A7`; Lane G
   G14 prices this at 6–12 eng-months). Even if GRUB loaded the image, the
   kernel could not mount `filesystem.squashfs` or any casper layer.
3. **No initramfs/userspace contract.** There is no init, no `/sbin/init`
   the kernel could exec, no module tree, no firmware loading. The five
   userspace bins are `BootInfo`-staged ELFs at fixed link bases
   (`rk007/build.sh`), not an initramfs.
4. **Display mismatch under GRUB.** The kernel draws via the framebuffer
   `BootInfo` hands it (KF-03, 1280x720 Bgr — `E-framebuffer.png`). GRUB's
   `gfxmode`/`gfxpayload` path does not construct that struct; the VGA-text
   fallback (`0xB8000`) is not the displayed surface in framebuffer mode
   (proven the hard way in `os-build/rk007/README.md`: bootloader INFO log
   on screen, kernel prints on serial only).
5. **No live-session services.** Casper live user, `user-setup`, lightdm
   autologin, plymouth, XFCE — all Linux-ABI consumers. Our kernel runs 9
   scheduler tasks and 4 staged programs (`STATUS tasks=9`, E `:809`); it
   cannot host the session the demo boots into.

## What enabling would take (not this round)

A `multiboot2` header + entry shim in our kernel that builds a synthetic
`BootInfo` from the Multiboot tags; a virtio-blk + squashfs read path (or a
ramdisk staging of the kernel + userspace ELFs into the ISO tree, e.g.
`/boot/metaos/*`, loaded via GRUB `module2`); then proof: two consecutive
QEMU ISO boots selecting the experimental entry with `META OS KERNEL -
alive (K1)` on serial. Until that proof exists twice, the entry stays
disabled and the default entry is the product (F14: lead's call).

## Deliberately NOT done

No `linux`-line pointing at our ELF (it is not a bzImage; GRUB would print
`invalid magic` and drop to rescue — a shipped hang). No `chainloader` to a
partition that does not exist on the ISO. No edited `vmlinuz`/`initrd`.
No pixels claimed without a boot (F7/F9/F10 renders BLOCKED, stated in
`../grub/README.md`).
