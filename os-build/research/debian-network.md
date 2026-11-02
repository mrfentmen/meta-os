# Debian networking bring-up (OS-094)

- Interfaces: predictable names via udev (`enp0s3`-style on net
  devices; serial console on ttyS0,115200). DHCP by default
  (preseed `choose_interface auto`); hostname `metaos`.
- DNS: `/etc/resolv.conf` (symlink to systemd-resolved stub on a
  full system; on our minimal image whatever DHCP supplies).
- Time sync: `clock-setup/ntp true` at install; no chrony/ntpd in
  the proven package set — time sync after install rides on
  systemd-timesyncd if enabled (not verified in the bake — open
  item, not a claim).
- Failure modes: no network at boot = DHCP timeout delay, then
  boot continues offline; DNS failure breaks apt/gateway backends
  silently (no local mirror, no retry policy recorded anywhere —
  rough edge).
