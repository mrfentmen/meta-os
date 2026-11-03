# Section S — userspace programs (R13-451..475)

Machine record: `S_PROGRAMS.json`. Check log: `CARGO_CHECK.txt`.

Counts: {"total": 25, "implemented": 18, "partial": 1, "abi_blocked": 6, "cargo_check": "BLOCKED"}

**`cargo check` is BLOCKED on this host, and no boot behaviour is claimed.** The installed `cargo` is Homebrew 1.99.1, which has no `x86_64-unknown-none` core; running the check through `rustup run nightly` still resolves a stable `rustc`, which refuses `-Z build-std`. Both attempts are in `CARGO_CHECK.txt`. The Mac gate is the only place these compile, and the only place anything may be said about booting them.

Six programs name an ABI they do not have (argv, fork/exec, kill, wait/status, process list). They are committed so the gap is executable rather than prose; `PROPOSALS.md` asks for the syscalls.

| task | program | spec | status |
|---|---|---|---|
| R13-451 | `hog_fast.rs` | throws 16 page touches in 4 KiB strides, then exits 0 | implemented (BSS; no allocator exists) |
| R13-452 | `hog_slow.rs` | touches the same 16 pages one byte at a time | implemented (BSS) |
| R13-453 | `hog_pulse.rs` | fills, clears, fills again over the same arena | implemented (BSS) |
| R13-454 | `quitter_1.rs` | exits 1 with no output | implemented |
| R13-455 | `quitter_7.rs` | exits 7 with no output | implemented |
| R13-456 | `quitter_after_print.rs` | prints one line then exits 3 | implemented |
| R13-457 | `crasher_null.rs` | reads address zero and must be killed | implemented |
| R13-458 | `crasher_stack.rs` | recurses until the stack guard faults | implemented |
| R13-459 | `spinner.rs` | loops forever and never yields | implemented |
| R13-460 | `sleeper.rs` | sleeps five ticks then exits 0 | implemented |
| R13-461 | `printer.rs` | writes 100 lines then exits 0 | implemented |
| R13-462 | `reader.rs` | reads keys until q then exits 0 | implemented |
| R13-463 | `counter.rs` | counts to 1000 and prints the total | implemented |
| R13-464 | `echoer.rs` | echoes its arguments | BLOCKED: no argv syscall |
| R13-465 | `leaker_slow.rs` | touches one new page per second | partial: no mmap/free, static pages only |
| R13-466 | `hog_then_quit.rs` | touches the arena then exits 9 | implemented (BSS) |
| R13-467 | `double_hog.rs` | two hogs at once | BLOCKED: no fork/exec |
| R13-468 | `hog_under_ps.rs` | a hog while ps is captured | BLOCKED: no process-list syscall, no ps |
| R13-469 | `spinner_killed.rs` | a spinner plus a kill | BLOCKED: no kill syscall |
| R13-470 | `crasher_then_status.rs` | a crash then a status capture | BLOCKED: no wait/status syscall |
| R13-471 | `reader_badkey.rs` | reads one key, exits 3 unless it is q | implemented |
| R13-472 | `printer_flood.rs` | writes 5000 lines past console size | implemented |
| R13-473 | `sleeper_killed.rs` | a sleeper plus a kill | BLOCKED: no kill syscall |
| R13-474 | `counter_big.rs` | counts to four billion | implemented |
| R13-475 | `echoer_empty.rs` | invoked with no arguments | implemented (and names the missing argv ABI) |
