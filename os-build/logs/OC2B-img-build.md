build-image: writing NoCloud seed (hostname metaos, relay user, autologin tty1)...

Image resized.
f7d8581ebb05a8b708b9cc4252a50e1b90681cad684d5e8778a95951363167c3  metaos-face.img
build-image: done. Boot with:
  qemu-system-x86_64 -m 2048 -drive file=/tmp/oc2b-img-build/metaos-face.img,format=qcow2 -cdrom /tmp/oc2b-img-build/seed.iso -serial file:boot.txt -display none -qmp unix:/tmp/face-qmp,server,nowait -net nic -net user,hostfwd=tcp::2222-:22

## OC2B-127/128/144/145 rebuild record (OC2B lane, 2026-11-02)

- Build script NAMED: `os-build/face/build-image.sh` (the Mac-lane recipe: official Debian 12
  cloud image + NoCloud seed, `qemu-img resize +10G`, sha printed). The Linux-only
  `os/os/build-image.sh` (debootstrap, needs root) is NOT usable on this Mac — recorded, not run.
- Command: `sh os-build/face/build-image.sh /tmp/oc2b-img-build` (base qcow2 pre-seeded in
  workdir from the face lane's 02:25 download — the script's own cache path, skipped download).
- Above is the script's verbatim stdout. Wall time ~25s (cache-hit; cold download would add minutes).
- Output: `/tmp/oc2b-img-build/metaos-face.img`, 448,790,736 bytes,
  sha256 `f7d8581ebb05a8b708b9cc4252a50e1b90681cad684d5e8778a95951363167c3`
  — byte-identical to the face lane's 06:47 build. Reproducible: YES.
- OC2B-144: lane-script failure? NONE — no failure, no patch, nothing to flag for Pax.
- OC2B-145 wall time: ~25s rebuild (+ ~2 min seed/SSH-key setup documented in checks log).
- Note (fence): this log lives at `OC2B-img-build.md` instead of the task-spec `OC2B-img-build.txt`
  because the lane fence allows writes only under `OC2B-img-*.md` / `OC2B-oc-*.md` / captures PNGs.
