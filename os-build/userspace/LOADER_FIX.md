# Loader fix (RK-013/14/15) — per-program link bases

## The failure

Pax's RK-007 ruling: all four userspace programs were loader-refused
with `address in use`. The kernel loader (`kernel/src/user.rs`,
`load_elf`) maps every LOAD segment at its linked address and
returns `Err("address in use")` for any page already mapped — across
ELFs, a mapped page is a hard refusal (intra-ELF page sharing is the
only skip).

## The cause

Nothing on the userspace build line ever passed a linker script:

- `os-build/userspace/.cargo/config.toml` sets `-no-pie`, static
  relocation, large code-model — no `-T` link script.
- `kernel/build.rs` stages ELFs from a plain
  `cargo build --target x86_64-unknown-none --bins` and even tells
  the operator to run that plain build when an ELF is missing.
- `os-build/userspace/user/link-base.ld` names per-program bases in
  its comment (hello 0x600000000000, sleeper 0x610000000000, crasher
  0x620000000000) but nothing substituted `BASE` per program.
- The committed `link.ld` is a single-base artifact (crasher's base)
  that the plain build never used either.

So a plain build linked every program at the same default layout
(RK-007 entry 0x201160, inside the 0.11 kernel image range
0x200000–0xbfba2c). The second program to load collided with the
first, and all four were refused.

## The fix

`os-build/userspace/build_userspace.py` (this branch, no kernel or
loader change, `syscalls.rs` untouched):

| Program | Link base | Source of base |
|---|---|---|
| hello | 0x600000000000 | `link-base.ld` comment |
| sleeper | 0x610000000000 | `link-base.ld` comment |
| crasher | 0x620000000000 | `link-base.ld` comment |
| readkey | 0x630000000000 | next slot, same spacing (new assignment) |

For each program it generates `link-<bin>.ld` from `link-base.ld`,
builds that one bin with `cargo rustc` passing the generated script,
and verifies the ELF's first LOAD segment address equals its base
and its entry point lies inside the loaded image, with no overlap
between programs' loaded ranges. The LOAD check is what makes a
wrong build loud instead of silent: if the link script ever stops
applying, the script fails rather than staging a colliding ELF.
Entry == base is deliberately NOT the check: Milo gate-1 RED on
5d3f0d1 showed sleeper's entry at base + 0xa40 while its first
LOAD started exactly at base (other .text sections precede
.ltext._start in link order). The loader maps LOAD segments, so
first LOAD == base is the loader-relevant property. The committed
`link.ld` is left untouched (stale, unused by this script); the
generated `link-<bin>.ld` files are working-tree artifacts — do
not hand-edit or commit them.

## Usage

From the repo root:

```
python3 os-build/userspace/build_userspace.py [--release] [bin ...]
```

Then build the kernel as usual; `kernel/build.rs` stages the ELFs
from `os-build/userspace/user/target/`.

## Gates (from `os-build/ROWAN_TEST_PREP.md`, Part 2)

- L1 static: every ELF first LOAD outside the kernel image range,
  distinct per-program bases, entry inside its loaded image — the
  script prints entry + first LOAD per bin.
- L2 build: this script is the repo build step, not a hand edit.
- L3 boot: zero `address in use` refusals across all four programs.
- L4 runtime: each program's output visible; K3 demand leg and K4
  still prove on the same boot.
- L5 gate: Milo gate-1 compile check first, then Mac/Buffy boot
  proof; merge is Pax's call.

## Status

UNCOMPILED on this VM (no cargo here). Milo gate-1 must run the
script; Mac/Buffy L1–L5 boot proof is still owed after that. This
branch is off `rowan/kernel-kf03` @4d04623 (the 0.11 console tree),
so the combined proof tree is KF-03 + loader fix; Pax decides the
merge order against current main.
