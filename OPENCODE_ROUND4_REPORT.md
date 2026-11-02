# OPENCODE ROUND 4 REPORT — 72h window, Mac lane

Branch: `opencode/round4`. Tip at start: `e0d8d94` (will re-record if main moves during merge-watch).
Standing rules: no source edits outside task scope; errors verbatim + stop; 4 bus files never committed.

## MAC-PROOF (amended, comes first) — DONE
- Tip: `e0d8d94` (Buffy Round 4 merged; R4 branch cut here).
- Toolchain (pinned PATH `NIGHTLY="$(dirname "$(rustup which --toolchain nightly rustc)")"`):
  plain `cargo` under the pin = `cargo 1.101.0-nightly (31d3246e0 2026-10-27)`;
  `rustc +nightly --version` = `rustc 1.101.0-nightly (f9ceb4a4d 2026-10-31)`;
  targets `aarch64-apple-darwin + x86_64-unknown-none`; components `llvm-tools + rust-src`;
  `bootimage 0.10.5`; `QEMU emulator version 11.1.3`.
  Note: with the pin active, `cargo +nightly` fails (`no such command`)
  because the pin bypasses the rustup proxy — plain `cargo` IS nightly.
- Userspace per-program (Appendix A3, colon-split pairs so zsh is safe;
  Appendix B's `set -- $pair` does not word-split under zsh and fed the
  base address to the linker as a filename — found and avoided):
  hello entry 0x600000000000, sleeper 0x610000000010, crasher 0x620000000110.
- Kernel: plain `cargo bootimage` under the pin → 8,367,616 bytes,
  bootloader 0.9.35 (Cargo.lock), kernel/.cargo/config.toml untouched.
- Boots (headless, `-serial file:merged-boot-N.txt -display none -m 512M`):
  boot 1, 2, 3 — every K-all.txt line present (alive 1, milestone 1,
  mem summary 1, C awake 1, HELLO 1, after sleep 1, exit code 2,
  bad-call refused 1, task killed 1), loader refused 0, panic 0.
  Best log: merged-boot-3.txt (saved as os-build/logs/MERGED-boot.txt).
- Musica: pretty_midi 0.2.11.post0 present; `node --test
  tests/musica-export.test.mjs tests/musica-products.test.mjs` → 4 pass, 0 fail.
- Verdict: MERGED TREE PROVEN at `e0d8d94`.

## R4-1 gate.sh, landed and green from a clean checkout — DONE
- Delivered `os-build/gate.sh` (bash, adapted from PAX_12H.md Appendix B;
  colon-split pairs so it survives zsh; one QEMU, PID kill, deadline
  wait for `sleeper: bad call refused`, drive.py --monitor types
  `help` + `status`, 7 checks + hard FAIL on `loader refused`).
- In-branch run: GATE GREEN, 7/7 ok (log os-build/logs/GATE-boot-r4-1.txt,
  3281 bytes, STATUS line present; full output os-build/logs/gate-run-r4-1.txt).
- Clean-clone run: fresh clone of opencode/round4 @ c541cf2 to
  /tmp/round4-clean, `sh os-build/gate.sh` → GATE GREEN, 7/7 ok
  (log os-build/logs/GATE-boot-clean.txt, STATUS present;
  full output os-build/logs/gate-run-clean.txt, pasted: toolchain /
  userspace / kernel / boot / assert sections all green, zero FAIL).
  Green from clean checkout: PROVEN.
## R4-2 userspace build fix — DONE (by verification, no edit allowed)
- The repo's build path already encodes per-program bases:
  `os-build/boot-test.sh` lines 24-30 build each bin with its own
  `-T$PWD/link.ld` (sed from link-base.ld at the right base), and the
  new `os-build/gate.sh` does the same via /tmp/link-*.ld. Both
  produce hello 0x600000000000 / sleeper 0x610000000010 /
  crasher 0x620000000110 (verified this session).
- No standalone `.cargo/config.toml` patch landed (Pax forbade it:
  it links every program at crasher's base). The tracked config
  stays without `-Tlink.ld`; bare `cargo build` in
  os-build/userspace/user is NOT the supported path — stated, not hidden.
- Loader refusal path untouched (`address in use` arm intact; this
  session's gates show 0 loader-refused lines because the build is right).
- Proof: clean-clone GATE GREEN above used only the branch's scripts.
## R4-3 K7 demo boot log — TODO
## R4-4 merge-watch — TODO
## What remains unverified — TODO
