# Debian init and service model (OS-090)

- systemd is PID 1 (`systemd` + `systemd-sysv` in packages.txt;
  sysv compat present but unused — no init scripts ship).
- Units are plain files in `os/os/services/` baked to
  `/etc/systemd/system/`; enablement is symlinks in
  `*.wants/` dirs created at bake time (not `systemctl enable`
  at runtime, except serial-getty in the chroot block).
- Supervision: `Restart=` lives in the unit files (read them for
  policy); watchdog coverage is `relay-watchdog.service` plus
  `metaos-custos.timer` / `metaos-loop.timer` for periodic work.
- Targets: `relay.target` (the appliance state) vs
  `multi-user.target` (rescue entry: base system, no crew).
- Ordering: `relay.target.wants` is flat — every crew service
  starts in parallel after the target; there is no staged
  dependency tree (a rough edge, recorded in rough-edges.md).
- No per-service sandboxing flags were spotted in the bake (no
  `ProtectSystem=`/`PrivateTmp=` mentioned anywhere in the script;
  units themselves not audited here — open item, not a claim).
