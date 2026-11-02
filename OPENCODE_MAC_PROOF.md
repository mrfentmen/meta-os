# OpenCode task: prove the merged kernel tree on the Mac

Boss order, 2026-11-01 (via Pax). The OpenCode OS build (240 tasks,
sections A to Q plus the OS-230 soak) was merged into main today by Pax
as commit eb7653f, and main has since settled at the tip you will pull.
The branch code was gate-checked and boot-proven on the branch. What has
never been proven is the MERGED tree itself: nobody has compiled it or
booted it since the merge. That is this job. Nothing else is in this
task: no new features, no fixes, no 8 PM test work.

Repo: mrfentmen/meta-os. Work on your existing Mac checkout. Report on
branch opencode/mac-tasks in OPENCODE_MAC_PROOF_REPORT.md. Never commit
the 4 excluded bus files: bus-tools/bus-poll, bus-tools/bus-rooms,
bus-tools/bus-send, tests/test_bus_admin_e2e.py.

## The job

1. Pull main. Record the exact tip hash in the report.
2. Toolchain, per os-build/OPENCODE_K1_RUN.md: nightly toolchain with
   the rust-src and llvm-tools-preview components, and bootimage
   installed. Record `rustc +nightly --version` and
   `qemu-system-x86_64 --version` in the report.
   PATH WARNING (Buffy's finding, 2026-11-01, os-build/PAX_12H.md):
   on this Mac, Homebrew's stable cargo/rustc sit ahead of the rustup
   proxies in PATH, so `cargo +nightly` and -Z flags hit the WRONG
   compiler and the failure reads like "no toolchain". Pin nightly
   explicitly for every cargo call in this task:
   NIGHTLY="$(dirname "$(rustup which --toolchain nightly rustc)")"
   and prefix commands with PATH="$NIGHTLY:$PATH".
3. Build the userspace FIRST, per program, with its linker script.
   kernel/build.rs stages the userspace ELFs with include_bytes and
   does not build them; it panics with a recovery command if they are
   missing. The tracked config in os-build/userspace/.cargo does NOT
   pass the linker script, so a plain build links all three programs
   near 0x201000 and the kernel loader refuses them at boot
   ("loader refused: address in use") — a known defect, proven and
   documented in os-build/PAX_12H.md section 0.2. Build each program
   at its own base (hello 0x600000000000, sleeper 0x610000000000,
   crasher 0x620000000000): from os-build/userspace/user, for each
   program, sed its base into a copy of link.ld (the shipped link.ld
   already carries crasher's base) and build with
   RUSTFLAGS="-C relocation-model=static -C code-model=large -C link-arg=-no-pie -C link-arg=-T<that copy>"
   and the pinned PATH from step 2. The full recipe is Appendix A3
   and Appendix B of os-build/PAX_12H.md; follow it exactly. Do not
   edit the tracked config or link.ld in this task; the pipeline fix
   lands separately through Pax.
   ALSO deliverable in this task: save that exact build+boot recipe
   as os-build/gate.sh on the report branch (Buffy's Appendix B is
   the proven draft; adapt the paths to this repo state) so the next
   proof is one command, not a human who knows the tricks.
4. Build the kernel image. From kernel/: `cargo +nightly bootimage`.
   Do not edit kernel/.cargo/config.toml (it carries the
   relocation-model=static fix and the build-std list; the merge
   combined both sides on purpose) and do not upgrade the bootloader:
   Cargo.lock pins 0.9.35, the proven version. Record the result.
5. Boot the image directly, three times, capturing serial output to a
   file each time (do not use `cargo run`; it hides the serial log in
   the QEMU window):
   qemu-system-x86_64 -drive format=raw,file=target/x86_64-unknown-none/debug/bootimage-metaos-kernel.bin -serial file:merged-boot-N.txt -display none
   (adjust the image path to the one step 4 produced). A short timeout
   per boot is fine; the kernel prints and idles.
6. Verdict per boot, checked against os-build/expected/K-all.txt:
   the log must contain `META OS KERNEL - alive (K1)`, must show the
   K3 line, the K4 memory summary, the userspace lines (C awake,
   HELLO FROM USERSPACE, sleeper: after sleep, user exit code 0), and
   must contain no panic. Save the best full log as
   os-build/logs/MERGED-boot.txt on the report branch.
   If a boot log instead shows "loader refused", the per-program
   build in step 3 was not used or did not take: that is a FAIL
   verdict for this proof. Report it with the log attached and the
   exact build commands you ran; do not paper over it and do not
   hand-edit binaries.
7. Musica on the Mac: install pretty_midi for the Python the repo
   tests use (it is missing on the Mac; the sandbox needed the same
   install), then from the repo root run
   `node --test tests/musica-export.test.mjs tests/musica-products.test.mjs`
   and record the test/pass/fail counts.

## Rules

- Proof or it did not happen. Every claim in the report carries the
  command and its real output numbers.
- If the kernel or userspace fails to compile, STOP. Put the full
  error output in the report verbatim and finish the report with the
  failure stated plainly. Do not edit kernel source, config, or
  Cargo.lock to make it pass; fixes are Pax and Rowan's call once the
  errors are on record.
- Bootloader stays at 0.9.35 no matter what a warning suggests.
- No spend in this task. No API keys are needed or used.

## Report

OPENCODE_MAC_PROOF_REPORT.md on opencode/mac-tasks: tip hash,
toolchain versions, userspace build result, kernel build result, the
three boot verdicts line by line against K-all.txt, the musica
counts, and a final line that says either MERGED TREE PROVEN or the
exact step where it failed.
