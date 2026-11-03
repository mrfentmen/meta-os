# Round 13 — full-lane test run

Tip: `buffy/round13`. Generated 2026-11-03T01:55:59.863Z by `os-build/round13/closeout.mjs`.

| suite | files | pass | fail | exit | ms |
|---|---|---|---|---|---|
| Hands-Free intake (P) | 1 | 25 | 0 | 0 | 152 |
| Nuntius relay (Q) | 1 | 25 | 0 | 0 | 388 |
| Nuntius board (R) | 1 | 25 | 0 | 0 | 335 |
| Agent runtime (K/L) | 10 | 55 | 0 | 0 | 1541 |

**Totals: 130 passing, 0 failing across 4 suite runs.**

## Not run here, and why

- The Goose service suites (`services/tests/t*.goose`) need the Goose toolchain, which is not installed on this host.
- The kernel and all 25 userspace programs need `cargo` with an `x86_64-unknown-none` core; see
  `os-build/round13/userspace/CARGO_CHECK.txt`. **Nothing in this round was compiled or booted.**
- The `relay/` and `board/` original suites (`relay.test.mjs`, `board.test.mjs`) are run by `npm test`, not here;
  the Round 13 suites above supersede them for this round's evidence.

Round 13 task: R13-492.
