# CARRIER JOIN note (OC1B-292)

The §12 carrier image ships as ONE part (no split transport was used):

- part: metaos-face.img — 4211802112 bytes, qcow2, 13G virtual
- sha256: fe039dda564774752bf6c721a712a16940d316329666bfde95bda26f403d3e4f

Rejoin: nothing to rejoin (single part). Verify after any copy:

  shasum -a 256 metaos-face.img
  # must equal fe039dda...7c77d04c (as-checked state; the guest appends
  # writes on every boot, so hash BEFORE first check boot; the manifest
  # records the as-checked digest)

Boot (QEMU; `-cpu max` is required — the Bun-compiled opencode binary
needs x86-64-v3/AVX2, absent from QEMU's default CPU under TCG):

  qemu-system-x86_64 -cpu max -m 2048 -drive file=metaos-face.img,format=qcow2 \
    -cdrom seed.iso -serial file:boot.txt -display none \
    -net nic -net user,hostfwd=tcp::2224-:22

SSH: relay@127.0.0.1:2224 with the build-local face-key (key material is
build-local and never enters git; regenerate per build).
Login: relay/metaos. Seed: NoCloud (hostname metaos, autologin tty1).
