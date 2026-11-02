# `crates/os-memory` — callers (B043)

Every caller found in the repo, what it expects, and whether the crate
meets it.

## Rust callers: none

A repo-wide search for `os_memory`, `os-memory`, `with_memory_depth`,
and `memory_depth_lines` (excluding `target/` and `Cargo.lock`) returns:

- `Cargo.toml:17` — the workspace member list. Not a caller.
- `crates/os-memory/**` — the crate and its own tests.
- `os-build/aegis/*` — inventories that mention the path.
- `os-build/BOND_TASKS.md` — this task list.
- `docs/RUST_REBUILD_PLAN.md`, `BATCHES.md`, `TASKS.md`,
  `batches/B17.md`, `SUPER_PROMPT.md` — the batch map and its
  instructions.

No crate or binary depends on `os-memory` in its `Cargo.toml`, and no
`use os_memory::…` exists outside the crate. The crate is a port that
is not linked into a caller yet.

## Expectations of the port (from the batch map, not code)

- `batches/B17.md:33-34` expects `cargo build -p os-memory` and
  `cargo test -p os-memory` to pass. It does not call the API.
- `SUPER_PROMPT.md:208-213` defines the B17 port claim and the test
  parity requirement; it expects the Python tests' behaviour, not a
  Rust call site.
- `BATCHES.md:462` names the batch and owner only.

## Python callers of the original — not callers of this crate

These matter because they define the contract the port is meant to
satisfy, but they call `os/mos/memory.py` or `os/intel/brief.py`, never
the Rust crate:

- `os/intel.py:246` calls `_brief.with_memory_depth(...)` while building
  a brief snapshot. It expects a snapshot value with `memory_depth`
  added and no mutation of the input. The Rust `with_memory_depth`
  returns the filled value and clones the input (`lib.rs:1261-1346`),
  so the behaviour matches; there is simply no Rust caller.
- `os/intel/brief.py:3834` and `os/intel/brief.py:4010` call
  `memory_depth_lines(...)` and join the lines into the brief. The Rust
  function returns `Vec<String>` in the same order and wording
  (`lib.rs:1348-1440`).
- `os/os/services/relay-memory.service` runs the Python CLI
  `memory.py ensure /var/lib/metaos/memory`. The Rust CLI is a library
  function (`run_cli`, `lib.rs:1008`), has no binary target, and is not
  what the unit starts.

## Mismatches to flag

1. **No launcher wiring.** `mount_paths` exists
   (`lib.rs:947-955`), but nothing in the repo calls it to mount the
   directories into a process. The Python docstring says this wiring is
   owed beside OS-080 (`os/mos/memory.py:52-60`); the Rust port inherits
   the gap. A caller expecting automatic mounts will not find them.
2. **No CLI binary.** Any script expecting `cargo run -p os-memory` or
   an installed `os-memory` executable will fail: `Cargo.toml:1-5` has
   no `[[bin]]`, and the port deliberately returns `CliOutcome` instead
   (`lib.rs:24-30`). The image service still calls the Python CLI.
3. **No cross-agent read API.** Nothing asks for one, and the port does
   not offer it (`os-memory.md` section 6). If a future caller wants
   agent A to read agent B, that is an OS-086 scoping decision, not a
   missing function in this crate.

No caller in the repo expects behaviour the crate does not implement.
The gaps are integration gaps, not contract mismatches.
