# Wiring proposal — hog and quitter (R12-011, R12-012)

For Rowan / OpenCode. This is a **proposal**, not an edit: `kernel/build.rs` and
`kernel/src/*.rs` are Rowan's pen, and the boot proof belongs to the Mac lane.

## quitter — already written and specified

`os-build/userspace/user/src/bin/quitter.rs` writes `quitter: exiting 7` and calls `sys_exit(7)`.
The kernel's exit arm already prints `user exit code 7`. `ps` keeps its current shape; the exit
is proven by that line, not by a new `ps` field.

**Proposed change:** add `"quitter"` to `const BINS` in `kernel/build.rs`. Rebuild the userspace
crate, then the kernel. No other source change.

**Expected boot lines:**

```
quitter: exiting 7
user exit code 7
```

## hog — written, but the ABI cannot allocate

`os-build/userspace/user/src/bin/hog.rs` writes `hog: allocating`, then touches 64 pages from
`0x7000_0000_0000` at 4 KiB stride. There is no allocation syscall in the ABI (0 exit, 1 write,
2 sleep, 3 pid, 4 yield, 5 read_key; 6–15 reserved), so this is a fault-containment drill, not
an allocator test.

**Proposed change:** add `"hog"` to `BINS`, next to `quitter`.

**Expected boot lines, one of two shapes:**

```
hog: allocating
INT user page-fault addr 0x700000000000 err 0x2: task killed
```

and afterwards the shell must still answer:

```
status
STATUS tasks=<n>
```

If the kernel maps that range for any reason, the program prints
`hog: SURVIVED (containment did not fire)` and exits 1 — which is a failure, not a pass.

## The four ABI probes (written and built 2026-11-02)

These are **diagnostics**, not part of the default boot. They are listed so the kernel lane has
the exact lines and the stack cost, not so all four get wired at once.

| program | base | expected lines | what it proves |
|---|---|---|---|
| `abiprobe` | `0x6818…` | `abiprobe: checks 9 failures 0`, `abiprobe: ABI OK` | page cap refuses 4097, chunked 10 KiB lands, pid survives yield/sleep, read_key stays in 0..255 or the sentinel, 6/15/99 refuse |
| `selfinfo` | `0x6819…` | `selfinfo: pid <n>`, `selfinfo: identity held` | syscall 3 is nonzero and stable across sleep |
| `yielder` | `0x681b…` | `yielder: yields 8 failures 0`, `yielder: identity stable` | yield returns to the same task eight times |
| `writechain` | `0x681a…` | `writechain: failures 0`, `writechain: OK` | eight page writes each return 4096; `sys_write_all` lands 8192 |

**Blocking fact:** `kernel/src/user.rs::take_ustack` refuses a fifth program, and `BINS`
currently holds four. Wiring any probe means either replacing one of the four (useful while
the kernel is at K6) or raising the slot count. That is a kernel decision, not a build one.

The probe sources are in `os-build/userspace/user/src/bin/`; all four are built and
base-verified by `os-build/userspace/build.sh`, and `os-build/USERSPACE_BUILD_STATUS.md`
records the 36-program check.

## The ruling this needs

If the intent is a real allocator drill (`hog` asks for memory until the kernel refuses), then
the kernel needs an allocation call and Pax must assign its number first. The current program
tests the refusal path that exists today; it does not pretend `mmap` exists.

## Measured state of the corpus (2026-11-02)

`PROFILE=debug os-build/userspace/build.sh` builds all 36 bins; `verify_bases.py` reads the
ELF headers and reports them disjoint, at their manifest bases, entries inside their images.
That is a build proof. It is **not** a boot proof, and only the four in `BINS` have ever run.

## What is NOT claimed

- Nothing here is compiled against the kernel or booted.
- The userspace crate compile is checked separately; it is not a boot proof.
- `ps` output is unchanged; this proposal does not add a field to it.
