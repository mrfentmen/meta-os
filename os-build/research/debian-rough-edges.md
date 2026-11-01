# Debian's 20 roughest edges for an agent-hosting machine (OS-097)
# + what our OS does instead, one line each (OS-098)

Evidence key: [bake] = os/build-image.sh, [pre] = preseed.cfg,
[pkg] = packages.txt, [doc] = upstream Debian docs, [obs] = this
repo's recorded runs. Second-source spot checks (OS-102): edges
1, 7, 12, 15, 19 rechecked against `systemd.special(7)`, the APT
and FHS documentation — descriptions corrected where they
overstated (no per-service sandbox flags claimed; timesync left
open; demo-thresholds confirmed demo-only).

1. One shared `relay` uid for every agent [bake][pre] → per-agent
   identities with home isolation (OS-119/127).
2. Agents restartable but not supervised-in-order; flat wants-dir,
   no staged tree [bake] → dependency-ordered supervision (Pax
   K6 shape; Buffy services).
3. No rollback: rebake is the recovery path [bake] → A/B update
   rule (OS-114).
4. No log rotation or size caps; 3 GiB root fills [bake][pkg] →
   capped, rotated, per-service budgets (OS-126).
5. Minimal observability: journal volatile, no audit trail
   [bake] → append-only deterministic records (OS-124).
6. Update mid-transaction failure = half-configured dpkg [doc] →
   staged + atomic activation, never in-place mutation.
7. Kernel update can silently keep the old kernel [doc] → the
   boot proof names its exact binary (our K1-K6 logs already do).
8. DHCP-or-wait boot; DNS failure silent [pre][doc] → explicit
   offline mode + retry policy in the network contract.
9. No time-sync daemon in the proven set [pkg] → time is an OS
   service with a stated source, not an accident.
10. No default-off for ssh in PROD (present; enabling is a
    runtime decision, undocumented trigger) [pkg] → services
    declare network exposure; default is loopback-only.
11. Secrets sweep exists but runs only at bake [bake] → sweeps
    run on every state change, counts recorded (OS-225 does this).
12. Demo thresholds can leak into prod thinking [bake] → demo
    and prod are different images by construction, never a flag.
13. Payload is the whole repo (rsync) — ships tests, plans, docs
    [bake] → programs ship as declared manifests (OS-133+), not
    checkouts.
14. Empty-commit git tree as update anchor is fragile (a real
    push can diverge it) [bake] → updates address immutable
    generations, not a mutable branch.
15. No per-service resource limits anywhere in the bake [bake] →
    agent compute/spend caps as OS rules (OS-126).
16. Rescue entry = full multi-user without crew: a human clicks
    past the whole agent layer with no audit difference [bake] →
    rescue is a capability with a record, not a silent door.
17. Preseed route unproven (spec only) while the bake assumes it
    for Packer parity [pre] → one proven build route; spec routes
    stay labeled SPEC until their acceptance run.
18. Package versions unpinned (names only) [pkg] → the pin step
    runs on every build host run; unpinned extras fail the build.
19. `policy-rc.d` + chroot service enables are build-time lies
    services never start in (serial-getty enabled blindly) [bake]
    → units declare real boot requirements; nothing is
    enabled-but-never-started.
20. 3 GiB fixed image, no growth story [bake] → storage is a
    named pool with quotas; full-pool behavior is specified.

## Keep vs replace (OS-099/100)

KEEP from Debian (the carrier stays useful): debootstrap rootfs
flow, GRUB/UEFI standalone pattern, fstab-by-UUID, ext4 + FAT
layout, policy-rc.d chroot hygiene, secrets sweep before
assembly, pinned-commit stamping, empty-store-root pattern.
REPLACE with our layers: everything the crew runs (supervision,
updates, records, memory, tools) moves off systemd/dpkg onto
Goose services + Lobster agents; the kernel eventually replaces
Linux itself. Covered today by our layers: none at runtime yet
(K6 just landed) — the replace list is a direction, not a claim.
