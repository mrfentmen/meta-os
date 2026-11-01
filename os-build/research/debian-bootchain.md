# Debian boot chain, end to end (OS-089)

Read from this repo's actual image route (`os/build-image.sh`,
`os/preseed.cfg`, `os/grub-early.cfg`), Debian 12 bookworm. The
preseed route (Packer) is SPEC ONLY — the header of preseed.cfg
says no unattended install has ever run; the booted route is
debootstrap + scripted assembly. Nothing below describes a run I
did not read.

1. Firmware (UEFI) reads the ESP (`work/esp.img`, FAT, `METAESP`),
   runs `EFI/BOOT/BOOTX64.EFI` — a GRUB standalone built by
   `grub-mkstandalone` with a fixed module set
   (part_msdos/part_gpt/fat/ext2/normal/configfile/linux/...).
2. GRUB's embedded config (`grub-early.cfg` + UUID) finds the root
   partition by UUID (`3d9a5c41-...`, baked into `grub.cfg`) and
   loads `/boot/vmlinuz-<KVER>` + initrd (KVER read from
   `lib/modules/*` at bake time — whatever debootstrap installed).
3. Kernel mounts root ext4 (`ROOT_UUID` in fstab) and runs systemd
   as PID 1 with `systemd.unit=relay.target` on the kernel command
   line (or `multi-user.target` on the rescue menu entry).
4. `relay.target` pulls the unit set in
   `etc/systemd/system/relay.target.wants/` (dashboard, bus, jobs,
   overseer, watchdog, brief, watchman, uplink, mcp-gateway,
   memory, custos timer, loop timer, firstboot).
5. First boot only: `metaos-firstboot.service` (wanted by
   multi-user.target) does one-time setup; getty autologs `relay`
   on tty1 + ttyS0 (appliance account, password locked `!`).

Second-source checks (OS-102, first two): the UEFI->GRUB->kernel
order matches the Debian installation guide's UEFI chapter, and the
`systemd.unit=` kernel-command-line override is documented in
`systemd.special(7)` — both confirm the mechanism, not just our script.
