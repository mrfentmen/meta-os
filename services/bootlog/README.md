# `bootlog` — Layer 4, service 1

**Status: WRITTEN.** Not COMPILED. `goose__toolchain_status` on this machine
returns `Goose toolchain: NOT FOUND`, so this source has never been through a
compiler and no part of this build claim rests on one.

## What it does

The first service to run and the last to go quiet. It writes records to the
serial port in the form:

```
<ticks> bootlog <level> <message>
```

One record per syscall, so a record is never interleaved with another writer's
bytes. Levels are fixed integers (`1` info, `2` warn, `3` error) rather than
strings, so the record header has a constant size.

## Contract

- **Entry:** `svc_entry` (`export "svc_entry" fn service_main() -> i32`), per
  `os-build/layer1/SERVICE_CONTRACT.md` §2. Returns `0` on a clean stop.
- **Kernel surface:** `sys_write_serial(s: const u8[:]) -> i64` and
  `sys_ticks() -> i64`, declared as `extern fn`. The transport is open question
  Q9 and is not asserted in the source.
- **Needs:** K-serial (K1 has the skeleton), K-timer for the tick stamp (K3).
- **Offers the layers above:** an append-only boot record. Nothing else imports
  it; it imports nothing but the kernel.

## Deviations and gaps, stated rather than hidden

1. **Entry takes no argument.** The contract says `service_main(boot: BootInfo&)`.
   `BootInfo` is B-L1-08 and does not exist yet; a placeholder struct would be a
   mock. Reconciling the signature is a listed step in B-L1-08.
2. **No ring retention.** Records go straight to the kernel. Retention over a
   ring needs B-L1-11 (`ring`), which does not exist yet, and pretending to
   buffer would hide the gap. A full serial buffer therefore drops the record —
   `record` returns `false` and `stage` propagates it, but `service_main`
   deliberately does not abort the boot over it.
3. **No config.** The tag and levels are globals; a real service reads its config
   through B-L1-13. Until then there is nothing to configure.

## How every symbol was verified

All checks through `goose-mcp@1.1.0` (bundled from `aardappel/goose` @
`b781587`), 2026-11-01:

| Symbol / form used | Where it came from |
|---|---|
| `export "svc_entry" fn` | `spec#41` (7.11 Exporting Goose functions to C), `reference#108` |
| `extern fn name(...) -> T` | `spec#40` (7.10 `extern fn`), `reference#106` |
| `const u8[:]` slice parameter | `spec#40` (`read_file(path: u8[:], ...)`) |
| `u8[>..]&` caller-supplied output buffer | `spec#40`, `samples/03_strings.goose` |
| `var b: u8[>..] = [];` builder | `samples/03_strings.goose` |
| `format(out, ...)` appending several values | `samples/03_strings.goose` |
| trailing `-> bool` for a two-outcome call | `samples/04_errors.goose` |
| top-level `let` globals | `reference#5` (Globals), `spec#57` |
| `i32` / `i64` / `bool` scalar keywords | `list_keywords` (46 keywords) |

## What is not verified

- That it compiles, or that `format` accepts a `u8[>..]&` and a `const u8[:]` in
  the same call in exactly this shape — the sample does it, but a compiler check
  does not exist here.
- That `sys_write_serial` returns a byte count rather than a status — that is our
  requirement on the kernel, not a fact (`SERVICE_CONTRACT.md` §3).
- That a freestanding link of Goose-generated C against our kernel works at all.
  B-L1-75 is the task that finds out.
