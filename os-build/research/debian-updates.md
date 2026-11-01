# Debian updates (OS-096)

- Mechanism: `apt update` (refresh indexes) + `apt upgrade`
  (unpack in dependency order, maintainer scripts, services
  restarted by policy). Reboot needed for kernel/systemd updates.
- Failure modes, each real: power loss mid-unpack leaves dpkg in
  a half-configured state (`dpkg --configure -a` recovery);
  maintainer-script failure aborts the transaction mid-list; a
  restarted service can come up on a new config it cannot parse;
  kernel update without bootloader refresh boots the OLD kernel
  silently.
- Our image: `metaos-update` pulls the payload repo (empty-commit
  tree + source-commit stamp keeps bake and payload matched), but
  there is no A/B partition, no snapshot, no rollback path — a bad
  update is repaired by rebaking, not by reverting (rough edge;
  the A/B design note OS-114 answers exactly this).
