# Stdlib gap audit — what the services need vs what Goose provides

Method: every capability below was checked through `goose-mcp@1.1.0` (bundled
from `aardappel/goose` @ `b781587`) on 2026-11-01, using
`list_stdlib_modules`, `list_symbols_in_module` and `lookup_symbol`.

**One caveat about the tool, because it changes how to read a "not found".**
`lookup_symbol` indexes the *stdlib*. Language-level builtins are not in it:
`print`, `assert` and `exit` all return "no stdlib symbol named …" while plainly
existing in the language (they appear in the bundled samples). So every "not
found" below means "not in the stdlib index", and each one is marked either
**gap** (nothing in the language either, per the samples) or **builtin** (exists,
just not as a stdlib symbol).

Goose ships **18 stdlib modules, 702 symbols**:

```
physics 171 · ui 161 · gfx 104 · std 98 · json 32 · os 25 · binary 24 ·
regex 15 · slot_pool 15 · dictionary 12 · vec 12 · slice_pool 7 · ffi 6 ·
audio 5 · exception 5 · csv 4 · math 4 · base64 2
```

That list is itself the headline finding: **~370 of the 702 symbols are `physics`,
`ui`, `gfx` and `audio`** — a games and graphics toolkit. For a service layer
that writes bytes to a serial port and watches a timer, most of the standard
library is inapplicable, and the parts we need are absent.

## The gap table

| Capability | What Goose provides | Verdict | Our answer |
|---|---|---|---|
| Serial write | nothing (no stdout on a kernel) | **gap** | `common/sys` `sys_write_serial` |
| Console write | nothing; `gfx`/`ui` draw into a host window | **gap** | `sys_write_console` + `display` (B-L1-27) |
| Read a key | nothing; `ui` handles host events | **gap** | `sys_read_key` + `input` (B-L1-26) |
| Monotonic clock | `os.time()`, `os.clock()` — **host runtime** | **gap on our kernel** | `sys_ticks` + `time` |
| Sleep | `os.sleep()`, `os.sleep_ms()` — host runtime | **gap on our kernel** | `time.sleep_ms` (poll + yield) |
| Process exit | `exit` (builtin) exists; `os.*` process control is host | **builtin + gap** | `sys_exit` |
| Yield / schedule | `thread_fn`, `thread_spawn` (builtin) — needs a C compiler and real threads | **builtin, unusable here** | `sys_yield`; services are single-threaded by contract |
| Files | `os.read_file`, `os.write_file`, … all `gs_os_*` host bindings | **gap on our kernel** | `fs` service (B-L1-79..84) over `storage` |
| Directory listing | `os.list_dir` — host | **gap** | `fs` |
| Sockets / TCP / UDP | nothing | **gap** | `sockets` (B-L1-33), protocols B-L1-95..101 |
| DNS | nothing | **gap** | `dns` (B-L1-32) |
| DHCP | nothing | **gap** | `dhcp` (B-L1-31) |
| Calendar date / time zones | nothing (only epoch seconds from `os.time`) | **gap** | `time` (B-L1-110) |
| Config file parsing | nothing | **gap** | `common/cfg` (B-L1-13) ✔ written |
| Command-line arguments | `os.arg`, `os.args` — host process args | **gap on our kernel** | `shell` argument parser (B-L1-88) |
| Ring buffer / queue | `vec`, `slice_pool` (pools, not rings) | **gap** | `common/ring` (B-L1-11) ✔ written |
| Formatting into a fixed buffer | `format`, `format_int`, `format_uint`, `str` | **provided** | wrapped by `common/fmt` ✔ for the overflow answer |
| String search/split/trim | `std`: `find`, `rfind`, `split`, `words`, `join`, `trim`, `compare`, `parse_int`, `parse_flt`, `to_lower`, `to_upper`, `concat` | **provided** | use directly |
| Sorting | `std.sort` (verified via `lookup_symbol`) | **provided** | use directly |
| Hashing | nothing in stdlib (no sha/crc in the index) | **gap** | `common/hash` (B-L1-14) ✔ written |
| JSON | `json` module, 32 symbols | **provided** | use directly; `common/json` (B-L1-120) is a subset only if the full one is too big |
| Binary encode/decode | `binary`, 24 symbols, endian-aware | **provided** | use for on-disk records |
| Hash tables | `dictionary` (12), `slot_pool` (15) | **provided** | registry, process table |
| Regex | `regex`, 15 symbols | **provided** | shell globbing later; watch code size |
| Base64 | `base64`, 2 symbols | **provided** | manifest encoding if needed |
| CSV | `csv`, 4 symbols | **provided** | not needed by any service; skip |
| Errors | no `Result` type; trailing bool/code + `exception.try` | **idiom** | `common/err` (B-L1-12) ✔ defines the code set |
| Constant-time compare | nothing | **gap** | `common/hash.equal_constant_time` ✔ |
| Random | `std.rng`, `rand_u64/int/flt` | **provided** | not needed by services; keys are the updater's problem |
| C interop helpers | `ffi.cstr`, `ffi.bytes`, plus `SDL_Init` (!) | **partial** | `ffi` is for pointers; the SDL symbols show what the module was built for |
| Threads | `thread_fn`, `thread_spawn` exist but need an external C compiler and TLS | **unusable here** | single-threaded services; kernel schedules |

## Gaps that are now library work, and where they live

| Gap | Owning task | State |
|---|---|---|
| Kernel boundary (6 calls) + shim spec | B-L1-09 | ✔ written |
| Formatting with an overflow answer | B-L1-10 | ✔ written |
| Ring buffers | B-L1-11 | ✔ written |
| Error codes and conventions | B-L1-12 | ✔ written |
| Config parser | B-L1-13 | ✔ written |
| CRC32 + SHA-256 | B-L1-14 | ✔ written |
| Argument parser | B-L1-88 | not started |
| JSON subset | B-L1-120 | not started (only if `json`'s 32 symbols do not fit the size budget) |
| Encoding (base16/hex helpers) | B-L1-121 | not started |
| Filesystem | B-L1-79..84 | not started |
| Networking stack | B-L1-29..33, 95..101 | not started |
| Calendar and zones | B-L1-110 | not started |

## The three findings worth acting on

1. **The stdlib is a games toolkit.** `gfx` + `ui` + `physics` + `audio` are more
   than half the symbols. Nothing there draws to a framebuffer we own. Expect to
   write the display path from scratch (B-L1-27) and do **not** plan on `ui`.
2. **`os` is the only module that looks like it solves our problem, and it is the
   one we cannot use.** Every function in it is a host syscall wrapper
   (`gs_os_*`, `spec#40`). This is the same trap recorded in
   `SERVICE_CONTRACT.md` §3, and this audit is the second independent sighting of
   it.
3. **The pieces we need are small and were quick to write.** The kernel boundary,
   formatting, rings, errors and config are ~1,000 lines total. The large gaps
   are the ones with real design content — filesystem, networking, agent host —
   and they are already their own tasks.

## What this audit does not claim

No symbol count here was checked by compiling anything. `sort` is confirmed to
exist in `std` by name only — its signature was not read, and B-L1-88 will read it
before relying on it.
