# `common/hash` — CRC32 and SHA-256

**Status: WRITTEN.** Not COMPILED. **Nothing in this file is claimed correct
until the vectors below pass on a real toolchain (B-L1-55).**

## Why unsigned, always

From the Goose docs (`tutorial#3`): *"Unsigned arithmetic wraps, in every build,
by definition, because that is what hashes and PRNGs mean by unsigned math.
Signed overflow aborts in debug and wraps in release."*

A hash written over signed integers would behave one way in a debug build and
another in release — and the debug build is where tests run. So no signed value
touches a word here. That is a correctness requirement, not style.

## CRC32 (IEEE 802.3)

Reflected polynomial `0xEDB88320`, init `0xFFFFFFFF`, final xor `0xFFFFFFFF`.
Bit-at-a-time, not table-driven: a 256-entry table costs 1 KiB of static storage
per linking service, and this protects records of tens of bytes. If something
later hashes megabytes, the table is a size/time trade for the size audit
(B-L1-136) to decide with numbers.

Incremental form for assembled records: `crc32_start()` → `crc32_update()` …
→ `crc32_finish()`.

### Vectors

| Input | CRC32 |
|---|---|
| `""` | `0x00000000` |
| `"a"` | `0xE8B7BE43` |
| `"abc"` | `0x352441C2` |
| `"123456789"` | `0xCBF43926` |
| `"The quick brown fox jumps over the lazy dog"` | `0x414FA339` |

## SHA-256 (FIPS 180-4)

Streaming: `sha256_init()` → `sha256_update()` (any number of chunks, any size)
→ `sha256_final(out, cap)`, or one-shot `sha256(data, out, cap)`. Padding follows
§5.1.1: `0x80`, zeros, then the message length **in bits** as a big-endian u64.

Rotations are `rotr32(x, n)` only — never a shift by 32, which is undefined in C
and would be a silent difference between `goose`-generated C and this source.

### Vectors

| Input | SHA-256 |
|---|---|
| `""` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `"abc"` | `ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad` |
| `"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"` | `248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1` |
| `"a"` × 1,000,000 | `cdc76e5c9914fb9281a1c7e284d73e67f1809a48a497200e046d39ccc7112cd0` |

The million-`a` case is the one that catches a padding bug: it needs a
two-block tail (63 bytes + 0x80, then a length-only block), which the `n > 56`
branch handles.

## Constant-time comparison

`equal_constant_time(a, b)` reads every byte. An early-returning compare tells an
attacker how much of a forged digest was right, which is exactly what an updater
check must not leak.

## Verification

| Form | Source |
|---|---|
| unsigned wraps in every build | `tutorial#3`, `stdlib#1` |
| `u8`/`u32`/`u64` keywords | `list_keywords` |
| fixed array `u32[..64]` globals and locals | `tutorial#3` |
| `as` casts | `list_keywords` |

## Not verified

Compilation, and the algorithm itself. The vectors above are the specification's
own; they are recorded here so B-L1-55 is a mechanical check rather than a
research task. Two specific worries for that task: whether `ctx.block[:]` slices
a struct field array, and whether an uninitialised `var w: u32[..64]` is
zero-filled — the schedule writes every slot before reading it, so only the
second would matter, and only if the language zero-fills lazily.
