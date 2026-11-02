# Debian package system (OS-091)

- Unit of software: a `.deb` (ar archive: control + data tarballs),
  installed by dpkg, resolved from APT sources by apt.
- Install: `apt install <name>` → dependency resolve → dpkg unpack
  + configure (maintainer scripts pre/postinst run as root).
- Remove: `apt remove` (config files stay) vs `purge` (config gone).
- State lives in `/var/lib/dpkg/status` (installed set + versions)
  and `/var/lib/apt/lists/` (repository indexes).
- Our manifest (`os/packages.txt`): 17 names, deliberately
  VERSIONLESS — the header says versions would be a guess without
  a built image to read `dpkg -l` from. Proven block (debootstrap
  2026-10-26 boot): systemd, systemd-sysv, udev, dbus,
  linux-image-amd64, initramfs-tools, python3, curl,
  ca-certificates, iproute2, git. Spec block: python3-venv,
  redis-tools, chromium, fonts-dejavu, openssh-server (disabled by
  default), qemu-guest-agent.
- The pin step is OWED to a build host run (diff list vs `dpkg -l`,
  record versions, flag extras) — not done here, stated.
