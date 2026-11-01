# Building a Layer 4 service

One recipe, applied identically to every service. Status: **DESIGNED**. No step
below has been executed on this machine — `goose__toolchain_status` returns
`Goose toolchain: NOT FOUND`, so there is no `goose` binary to run and no build
log to show. This file is the recipe the first COMPILED pass (B-L1-75) will
follow or correct.

## Layout

```
services/
  BUILD.md              this file
  MANIFEST.md           the worklist (B-L1-01)
  common/               shared libraries, imported by services
    boot/               BootInfo types (B-L1-08)
    sys/                kernel syscall externs (B-L1-09)
    fmt/                fixed-buffer formatting (B-L1-10)
    ring/               ring buffers (B-L1-11)
    err/                error codes (B-L1-12)
    cfg/                config parser (B-L1-13)
    hash/               CRC32 + SHA-256 (B-L1-14)
    args/               shell argument parser (B-L1-88)
    json/               JSON subset (B-L1-120)
  <service>/            one directory per service
    <service>.goose     the source
    README.md           contract, status word, verification table
    build.sh            optional: the exact commands for this service
```

Every service directory named in `MANIFEST.md` exists from the moment this file
lands, each with a README that states **NOT BUILT** and the task that will fill
it. An empty directory with a promise in it is honest; a directory that looks
finished and is not is the thing the no-mocks rule exists to prevent.

## The recipe

A Goose program compiles to C, and then C compiles to an object. The syntax of
the first step is verified in the bundled samples, which all carry the same
comment (`samples/01_tour.goose`, `03_strings.goose`, and the rest):

```
goose -o tour.c 01_tour.goose && cc tour.c && tour
```

So, per service:

```sh
# 1. Goose -> C  (verified form: `goose -o <out.c> <in.goose>`)
goose -o build/<service>.c services/<service>/<service>.goose

# 2. C -> object, freestanding.  NOT verified: this is the layer's assumption.
cc -c -ffreestanding -fno-stack-protector -fno-builtin \
   -mno-red-zone -nostdlib \
   -o build/<service>.o build/<service>.c

# 3. Link with the kernel's service shim, no libc.
ld -T services/link/service.ld -nostdlib \
   -o build/<service>.elf build/<service>.o build/svc_shim.o
```

Step 1 is the part Goose owns. Steps 2 and 3 are the part **nobody has proven**,
and the honest label for the whole recipe is "expected to work, untested".

### Why `-ffreestanding` and friends

- `-ffreestanding` — there is no hosted C environment; the compiler must not
  assume `main`, `printf` or a libc it can call.
- `-nostdlib` — no startup files, no libc. The kernel hands control to
  `svc_entry`, not to a C runtime.
- `-fno-builtin` — stops the compiler turning a loop into a call to `memset`
  that does not exist.
- `-mno-red-zone` — interrupt handlers on x86-64 must not have the compiler
  using the 128-byte red zone under the stack pointer. This matters the moment
  K3 lands, and finding it later costs a day.
- `-fno-stack-protector` — the protector needs a per-thread guard value from a
  libc-ish runtime we do not have.

These flags are the standard set for this kind of work; they are listed so the
first person with a real compiler can argue with them in one place.

### The link script

`services/link/service.ld` does not exist yet. It has to place:

- the entry symbol `svc_entry` at the address the kernel loads the image to;
- `.text`, `.rodata`, `.data`, `.bss` with the alignment the kernel's loader
  expects (unknown — a K6 requirement, listed as A10 in `BOUNDARIES.md`);
- a symbol at the end so the size audit (B-L1-136) can measure each service
  without guessing.

Writing that script now would be inventing the kernel's loader. It is listed as
a blocker instead, and B-L1-63 (link map) is where it gets written once K6's
shape is known.

## Per-service static storage

Goose services allocate nothing at run time: builders live on the data stack, and
anything longer-lived is a global or a caller-supplied buffer. That means each
service's memory need is knowable at link time — which is exactly what makes the
size audit possible later, and why A10 (a documented per-process storage limit)
is a requirement rather than a nicety.

## Build artifacts

`services/build/` holds generated `.c`, `.o` and `.elf` files and is not
committed. Generated C is a build output, not source; committing it would make
the repository's diff lie about what changed.

## What a service build does NOT do

- It does not run the service. Running needs K6 and a kernel to run it on.
- It does not install anything. Layer 4 has no installer yet; the updater
  (B-L1-34..36) is where that belongs.
