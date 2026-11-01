# `common/fmt` — fixed-buffer formatting

**Status: WRITTEN.** Not COMPILED (no Goose toolchain).

## Why it exists

Goose's `std` already has `format`, `format_int`, `format_uint` (verified:
`stdlib#9`). What it does not have is an answer to "the buffer is full": every
index is bounds-checked and **a failed check aborts the program**
(`reference#82`). A log line that overflows would kill the service that was
trying to report a problem.

So this library checks capacity *before* writing and returns a trailing `false`.
Nothing truncates silently, nothing aborts on a condition the caller can handle.

## The cap rule

Builders (`u8[>..]`) grow on the data stack and have no built-in limit. Every
call takes `cap` — the size the caller is willing to let the buffer reach — and
refuses to cross it. Passing `cap` larger than the storage you actually have is
a caller bug that this library cannot detect, and it is stated here rather than
hidden.

## API

| Function | Does |
|---|---|
| `digits_needed(v, base) -> i64` | digits a value needs in a base, without writing |
| `room_left(out, cap) -> i64` | bytes still allowed, never negative |
| `full(out, cap) -> bool` | buffer is at its cap |
| `used(out, cap) -> i64` | bytes written, clamped to cap |
| `append_str(out, cap, s) -> bool` | append a slice |
| `append_char(out, cap, c) -> bool` | append one byte |
| `append_int(out, cap, v) -> bool` | signed decimal |
| `append_int_pad(out, cap, v, width, pad) -> bool` | right-aligned, zero-padded |
| `append_uint(out, cap, v, base, width, pad) -> bool` | hex = base 16, and any 2..36 |
| `append_bool(out, cap, b) -> bool` | `true` / `false` |
| `append_nl(out, cap) -> bool` | newline |
| `terminate(out, cap) -> bool` | reserve a NUL for a C shim that wants one |

There is no `append_hex` wrapper: hex is `append_uint(..., 16, 4, '0')`, and a
second name for the same call is a second thing to keep in sync.

## Deliberate omissions

- **No float formatting.** `format_flt` exists, but a kernel log line does not
  need decimals and every float path is somewhere a no-libc build can drag in
  soft-float code. If it is needed, it arrives with its own test (B-L1-45).
- **No silent truncation.** A caller that wants the first N bytes says so.
- **No allocation.** `out` is the caller's storage, `cap` is its limit.

## Verification

| Form | Source |
|---|---|
| `u8[>..]` builder, `.len`, `append`, `push` | `samples/03_strings.goose` |
| `format_int(out, v, base, width, padc)` | `stdlib#9` |
| `format_uint(out, v, base, width, padc)` | `stdlib#9` |
| bounds check aborts | `reference#82` |
| trailing `-> bool` | `samples/04_errors.goose` |
| `while`, `if`, `return`, `as` casts | `list_keywords` |

## Not verified

That it compiles; that `format_int` with `width = 0` behaves as "no padding"
rather than "no digits" (the docs show the parameter, not that edge); and that
`out.len` on a builder is the count of bytes appended rather than its capacity.
Those three are the first things B-L1-45 checks with a real compiler.
