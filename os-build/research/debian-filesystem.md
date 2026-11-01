# Debian filesystem layout (OS-092)

From the bake (`build-image.sh` writes hostname, fstab, locale,
version stamp, units, payload, stores) plus FHS:

- `/` ext4, `UUID=3d9a5c41-...` (fstab), 3 GiB image, 64 MiB ESP.
- `/boot/efi` vfat (`LABEL=METAESP`); `/boot/grub/grub.cfg` with
  the two menu entries (Meta OS / rescue).
- `/etc/metaos/` (mode 700): machine-local config; `/etc/hostname`
  = `metaos`; `/etc/metaos-version` = date + Debian version +
  source commit.
- `/opt/relay/`: the WHOLE repo payload (rsync, no `.git`) plus a
  fresh empty-commit git tree so `metaos-update` sees a repo.
- `/var/lib/metaos/{artifacts,memory,skills,custos,loop}`: runtime
  stores, created EMPTY with marker files, relay-owned.
- What breaks if it moves: `/boot/efi` (firmware finds BOOTX64.EFI
  by path), `/etc/fstab` UUIDs (wrong UUID = unbootable),
  `/opt/relay` (units + `metaos-update` assume it), `/var/lib/metaos`
  (services write records there; missing dirs fail at runtime —
  the units `ensure` some, not all — open item).
