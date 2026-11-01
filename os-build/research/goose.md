# Goose toolchain research (OS-153)

Sources: goose-mcp 1.1.0 (bundled from upstream commit
b78158797a3a4199a2c519d90d4e5421b2760fe3: 389 doc sections, 702
stdlib symbols, 57 keywords, 32 samples) + the live toolchain
build below. No network at MCP runtime; the toolchain builds
from https://github.com/aardappel/goose.

## What it is

Memory-safe systems language by Wouter van Oortmerssen: no
garbage collector, no lifetime annotations. Non-fixed values live
on a data stack; data structures are flat and pointerless. The
compiler emits ONE C file that its bundled TinyCC backend
compiles and runs in-process. `fn main()` is the entry.

## How a program builds and runs

`goose -o hello.c hello.goose && cl hello.c && hello` (tutorial
convention; `cl` = the C compiler step — on the Mac that is
`cc`). `print(...)` writes to stdout. Errors are trailing return
values by convention (`-> T, bool`), not exceptions.

## What the stdlib gives a daemon (all `[os]`, verified present)

`read_file` / `write_file` / `write_file_atomic` /
`append_file` / `file_exists` / `delete_file` / `rename_file`,
`make_dir`/`is_dir`/`delete_dir`/`list_dir`, `read_line` /
`read_stdin` / `write_stdout` / `flush_stdout`, `args`/`arg(i)` /
`env`, `time`/`clock`/`time_ns`, `sleep(f64)` / `sleep_ms`,
`random_seed`. Strings are `u8[:]` slices.

## How thin it is (honest)

- NO signals, NO exit call, NO sockets in the symbols I could
  find. A daemon stops via a sentinel file it polls (documented
  workaround, OS-166), not SIGTERM.
- No test-runner convention found yet — Section K tests ride in
  a runner script if the language lacks one (OS-164 states which).
- Build state: cloned shallow 2026-11-01, cmake Release +
  `GOOSE_BUILTIN_LIBS=all`, built on this Mac (versions in the
  Section K report block). If the build fails, the honest entry
  goes in the report, not a silent skip.
