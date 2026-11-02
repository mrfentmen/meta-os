# Section 6 status block (OC2B-146) — stands in for the STATUS-file §6 block

Lane fence forbids editing `os-build/OPENCODE2_500_STATUS.md`, committing, pushing, and staging
`.img` files — so this file carries the §6 block. No commit or push was made (OC2B-147: N/A by
fence; Pax to checkpoint). No `.img` enters git: `git status` shows only the allowed
`OC2B-img-*.md` / `OC2B-oc-*.md` / captures PNGs (verified before handoff).

- OC2B-126: STATUS read — repo copy `os-build/image-status-2026-11-02.md` (no sha, no PARTIALs,
  four checks PROVEN); expected sha prefix `f7d8581e…` from `os-build/face/image/JOIN.note`
  (`OC2B-img-status.md`).
- OC2B-127/128: rebuilt with `os-build/face/build-image.sh` → 448,790,736 bytes,
  sha256 `f7d8581ebb05a8b708b9cc4252a50e1b90681cad684d5e8778a95951363167c3` (`OC2B-img-build.md`).
- OC2B-129–142: checks in `OC2B-img-checks.md`; boot log `OC2B-img-boot1.md`;
  screendump `OC2B-img-desktop.png`; verdicts `OC2B-img-verdict.md`.
- OC2B-144: no lane-script failure (no-failure line).
- OC2B-145: rebuild wall ~25s cache-hit; full §6 boot/check cycle ~35 min across 3 boots.
- OC2B-148: MATCH — fresh shasum equals recorded prefix and the 06:47 face-lane build byte-for-byte.
- OC2B-149 gaps for the demo (besides §7 bake): (1) pristine output has no node/git/chromium —
  all face tooling arrives via guest provisioning, not the build script; (2) no graphical
  stack in build output (face screenshots come from provisioned VMs); (3) QMP runtime hostfwd
  unsupported — forwarded ports must be declared at VM startup; (4) `/tmp` is cleared on boot
  (stage persistent state under `$HOME`, not `/tmp`); (5) guest clock +36s until NTP converges.
- OC2B-150 QEMU cmdline verbatim (boots 1–2; boot 3 adds the hostfwd pair):
  `qemu-system-x86_64 -m 2048 -drive file=/tmp/oc2b-img/oc2b-work.qcow2,format=qcow2 -cdrom /tmp/oc2b-img/seed.iso -serial file:/tmp/oc2b-img/bootN.txt -display none -qmp unix:/tmp/oc2b-qmp,server,nowait -net nic -net user,hostfwd=tcp::2223-:22[,hostfwd=tcp::18909-:18900]`

§6 rollup for Pax: carrier rebuild is reproducible (byte-identical sha), boots clean, autologin/DHCP/egress/dashboard/host-fwd/mem/clock/shutdown all PROVEN on the fresh output.
UNPROVEN: face-in-chromium (139) + baked-toolchain versions (138) — both need guest provisioning,
in flight / handed to §7.
