# Parity reading (Bond, Lane 4)

Lane 4 of `os-build/BOND_LIGHT_LANES.md`: run the parity checks that are
text reads, plus the Goose typecheck, without a Rust workspace build or a
QEMU boot. This file says exactly what each check proves and what a SKIP
means on this machine.

Runner: `os-build/tools/parity_lane.sh`

```
bash os-build/tools/parity_lane.sh
PARITY_RUST=1 bash os-build/tools/parity_lane.sh   # opt-in extra stage
```

The runner reads sources and runs tests. It changes no file, calls no
network, starts no emulator.

## Which checks are text reads, and which need a compiled binary

| Check | What it reads | Needs a compiler? |
|---|---|---|
| `tests/product-parity.test.mjs` | `js/products.js` and the web/native product keys; source text only | No |
| `os/tests/test_bustools_parity.py` | SHA-256 of `bus-tools/bus-send`, `bus-poll`, `bus-rooms` against the live copies in `~/workspace/skills/muse-bus-relay/bin` | No — but it needs that external install to exist |
| `crates/*/tests/*_parity.rs` (e.g. `crates/intel/tests/b13_parity.rs`) | Checked-in fixtures and Rust port functions | Yes — `cargo test` compiles the crate and its dependencies |
| `tests/goose-programs.test.mjs` | Runs `hello`, `echo`, `heartbeat`, `mcp-host` through the Goose binary | Needs `goose` on `PATH`; skips itself when absent |

The Rust parity files compare behavior, not bytes: they call the port's
functions and assert the same rules the Python side pins. They still need
a compile to run, which is why Stage 3 is opt-in.

## Stage 1 — Goose typecheck

The toolchain is documented in `os-build/research/goose.md`; the verified
compile form is `goose -o <out.c> <in.goose>` (`services/BUILD.md`). The
runner tries `goose -check <file>` first. If the installed build rejects
that flag, it falls back to `goose -o` into a temp directory and reports
the result as **COMPILE**, never as "typecheck", because compiling to C is
a different (stronger) claim than a front-end typecheck.

When `goose` is not on `PATH`, Stage 1 prints:

```
SKIP  goose typecheck: goose not on PATH (...)
```

That is not a pass. `tests/goose-programs.test.mjs` makes the same honest
skip when the binary is missing.

## Stage 2 — text parity

```
node --test tests/product-parity.test.mjs
python3 -m pytest os/tests/test_bustools_parity.py -q
```

`test_bustools_parity.py` hardcodes `SKILL_BIN = ~/workspace/skills/muse-bus-relay/bin`.
On a machine without that live skill install it fails for an environment
reason (missing file), not because the repo drifted. The runner reports
that FAIL with the pytest output so the reason is visible; it does not
turn it into a SKIP.

## Stage 3 — Rust parity (opt-in)

```
PARITY_RUST=1 bash os-build/tools/parity_lane.sh
# inside: cargo test -p intel --test b13_parity -j1
```

Default is SKIP with the reason `opt-in: cold compile, 8GB lane`, per the
machine rules in `os-build/BOND_LIGHT_LANES.md`: no `cargo build/check`
over `crates/` on this laptop, and if a command must compile it runs alone
with `-j1`. This stage is one crate, not a workspace build, and it is the
only stage that compiles anything.

## Reading the counts

- `PASS` — the command ran and exited 0. The line names the file or test.
- `FAIL` — the command ran and exited non-zero. The real output is above
  the line; a FAIL is a finding, never rounded to green.
- `SKIP` — the command did not run, and the line says why (missing binary,
  or opt-in stage not requested). A SKIP is not evidence.

Final line: `== summary: N pass, N fail, N skip ==`. The script exits
non-zero only when `FAIL > 0`; a run that is all PASS and SKIP exits 0.

## Not in this lane

- `cargo build/check/bootimage` over the kernel (`kernel/`) — Mac/OpenCode lane.
- QEMU or UTM boots against the face image — proves nothing by text read.
- Anything holding a model.
