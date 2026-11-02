# Callers of `crates/os-boot` (B007)

Search basis: `os_boot::` / `use os_boot` across `crates/` returns **zero** matches; `-p os-boot`
across scripts and docs returns the callers below. There is no Rust crate that depends on
`os-boot`, and no binary in the crate (`Cargo.toml:1-5`).

## Callers and what they expect

| Caller | Line | What it does | What it expects | Does the crate meet it? |
|---|---|---|---|---|
| `Cargo.toml` (workspace) | `Cargo.toml:13` | lists `crates/os-boot` as a member | the crate builds as part of `cargo check` | yes |
| `os-build/layer1/build_kernel.sh` | `:22-29` | `cargo check -q -p os-boot` | a clean compile; on failure prints `build_kernel: os-boot crate does not compile` and exits | yes (compiles) |
| `os-build/layer1/check_all.sh` | `:44-49` | `cargo check -q -p os-boot` | a compile result only; reports `os-boot crate PASS/FAIL` | yes (compiles) |
| `os-build/OS_STATUS.md` | `:59` | describes `check_all.sh` as covering "kernel, os-boot, Goose corpus, node suite" | documentation only | partially — see flag 2 |

## Callers that do not exist

- **No production caller of `run_cli`.** `run_cli` is referenced only in `cli.rs` tests
  (`cli.rs:1102-1160`). Nothing constructs `Backends` outside tests.
- **No production caller of `GitCliBackend`.** Referenced only in `git.rs` tests
  (`git.rs:192-243`).
- **No crate depends on the public API.** `Cargo.toml` of every other member lists no
  `os-boot` path dependency.
- **The `test_os_boot_*` tests in `crates/parity-tests` are not callers.** They cover the OS
  boot drills (`os/tests/test_os_boot_harness.py` etc., `crates/parity-tests/src/tests/mod.rs:33-35`),
  not this crate; they do not import `os_boot`.

## Flags — callers expecting something the crate does not do

1. **Both scripts call `cargo check`, never `cargo test`.** The crate's 23 tests (16 in `cli`,
   4 in `git`, 3 in `carried`) therefore do not run in either gate. A caller reading
   `check_all.sh` would believe `os-boot` is verified; it is only compiled.
2. **`OS_STATUS.md:59` says `check_all.sh` covers os-boot.** In strict terms it covers
   compilation. The CLI's refusals, the git guards, and the carried byte-identity assertion are
   not exercised by that script.
3. **No caller can construct the CLI.** The five backend traits have no production
   implementations (see `os-boot-gaps.md` G1-G4), and no binary exists to build them. Any future
   caller expecting `run_cli` to work end-to-end will find it does not.
