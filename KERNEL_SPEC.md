# Meta OS — Kernel Spec (standing instruction)

For any agent working on the Meta OS bootable image (OpenCode included):
read this before touching the image build. This spec is settled by
Mrfentmen. Do not substitute, do not improvise.

## The spec

The bootable image uses the STOCK Debian 12 (Bookworm) kernel:

- Package: `linux-image-amd64` (6.1 series, Debian's official build)
- Source: Debian's official repository, `http://deb.debian.org/debian`
- Installed at bake time via debootstrap:
  `debootstrap --variant=minbase --include=...,linux-image-amd64,... bookworm <rootfs> http://deb.debian.org/debian`
- Official package page: https://packages.debian.org/uk/source/bookworm/linux

## Rules

1. Never substitute a custom or self-compiled kernel.
2. Never use a kernel from any other distro or source.
3. The kernel stays unmodified. Meta OS is a Linux-based operating
   system: stock kernel underneath, the Meta OS system layer on top.
4. Kernel updates come only through Debian's normal package updates.
5. If you touch the image build, confirm the kernel package name and
   source match this spec exactly, and report back what you verified.
