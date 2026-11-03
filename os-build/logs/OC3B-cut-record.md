# OC3 ISO-3 — cut record (ran what runs here, named the rest)

Source ISO: `/private/tmp/xubuntu-base.iso`
- sha256 `4ed869ebf2b9f2f6118c1b60b9ed07576e8fe3d5cdfe10aae06869e669878b81`
- matches official `xubuntu-24.04.5-desktop-amd64.iso` line in
  `/private/tmp/xubuntu-SHA256SUMS`. VERIFIED (recomputed this run).

Output ISO (pre-drop-in baseline, per T1): `/private/tmp/isowork/metaos-1.0.iso`
- sha256 `6d3793eb1cfb34cb7ca537c90f965a916c1454695af270843a18f06363770dde`
- recomputed this run; matches `.sha256` + `.sha256-fixed`. VERIFIED.
- The NEW output (baseline + drop-ins + no-theme payload) does not
  exist yet: building it is ISO-lane/OC1 work (chroot + squashfs on
  Linux). BLOCKED, owner OC1. This record is the input half.

Package-list hashes (from `origin/main @8923da87`, read-only):
- `os-build/metaos1-base/packages.txt` `6ea5d926f51fd6cf50eba5f2cc2d5c16977984a3c6d8fb99232afad65b1615b6`
- `os/os/packages.txt` `1c976c37df139ad74f720a95a7b5619a4f5ebb67275f163c86b6a3664eb35db5`
- `os/os/live-build/config/package-lists/metaos.list.chroot` `ad8c211903e87e07ae9931e13721aa25e96dc83ae150e7a2307206a777ef9d28`

validate.py (`os-build/metaos1-base/validate.py`, stdlib-only):
- ran in a clean detached worktree of `origin/main @8923da87`
  (removed after): **OK: 0 failure(s)** — packages parse, firstboot
  clean (no prompt/credentials/network), mimeapps scoped, no frozen
  path touched, base-flow wiring names verify-rootfs.sh as gate,
  both dexubuntu scripts `sh -n` clean. Full output in shell history;
  rerunnable by anyone, no VM needed.

verify-rootfs.sh 7/7: BLOCKED, owner OC1.
- Needs a mounted/extracted rootfs; only `casper/filesystem.squashfs`
  exists locally and this Mac has no unsquashfs/mount tooling
  (checked: unsquashfs, unsquashfs4, mksquashfs all absent).
- OC1 runs the 7 checks at build/boot and posts the 7/7 line; this
  file takes the result without re-proving it.
