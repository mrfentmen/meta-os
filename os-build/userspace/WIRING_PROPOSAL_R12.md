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

## The ruling this needs

If the intent is a real allocator drill (`hog` asks for memory until the kernel refuses), then
the kernel needs an allocation call and Pax must assign its number first. The current program
tests the refusal path that exists today; it does not pretend `mmap` exists.

## What is NOT claimed

- Nothing here is compiled against the kernel or booted.
- The userspace crate compile is checked separately; it is not a boot proof.
- `ps` output is unchanged; this proposal does not add a field to it.
