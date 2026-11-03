# Round 13 — userspace summary (Section S)

| section | state | counts | evidence |
|---|---|---|---|
| userspace | **WRITTEN — CHECK BLOCKED** | 25 / 25 sources; 19 implemented, 1 partial, 6 ABI-blocked; `cargo check` blocked on this host's toolchain | `os-build/round13/userspace/SECTION_S.md` |

## Programs

- 25 sources committed under `os-build/userspace/user/src/bin/`: 18 implemented, 1 partial, 6 blocked by the ABI.
- **`cargo check` is BLOCKED on this host.** Homebrew cargo 1.99.1 has no `x86_64-unknown-none` core; `rustup run nightly` still resolves a stable rustc and refuses `-Z build-std`. Both attempts are in `CARGO_CHECK.txt`.
- **Boot behaviour is not claimed.** The Mac gate is the only proof.
- The six ABI-blocked programs name the syscall they need (argv, spawn, wait, kill, mmap, process list) and exit 2. `PROPOSALS.md` is the proposal payload; posting it on room 1 needs the bus.
