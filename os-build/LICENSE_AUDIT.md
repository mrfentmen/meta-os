# License audit (OS-217) — every crate, tool, font, borrowed idea

## In the kernel binary (linked)

- `bootloader` 0.9.35 (crates.io): MIT OR Apache-2.0. Verified
  in the registry Cargo.toml. NOT GPL.
- `core` + `compiler_builtins` (build-std, rustc): MIT OR
  Apache-2.0. NOT GPL.
- `metaos-kernel` itself: MIT (Cargo.toml).
- Kernel dependency closure: bootloader + core only. ZERO GPL
  (OS-218 satisfied — there is nothing to remove).
- `bootimage` 0.10.5: HOST build tool, never linked into the
  kernel image. (Same class as the compiler: used, not shipped.)

## Fonts

- None embedded on this branch. The console uses the VGA ROM
  font (hardware). Rowan's Terminus table (OFL, license file
  carried at kernel/FONT_TABLE_LICENSE.md) stays UNWIRED —
  audited, not used.

## Dev-carrier tools (used to build, never shipped in the image)

- QEMU 11.1.3: GPL-2.0. Carrier-only (runs the image; no QEMU
  code enters it). Red-list rule applies to use: it is never
  presented as part of the product.
- Goose toolchain (built from aardappel/goose): Apache-2.0
  (LICENSE in the toolchain checkout).
- Lobster interpreter (built from aardappel/lobster):
  Apache-2.0 (dev/LICENSE.txt).
- Rust toolchain, clang, make, binutils: MIT/Apache/Apple —
  standard Mac toolchain, carrier-only.

## Borrowed ideas (OS-113/116 — ideas only, zero code)

NixOS generations, Redox capabilities, ChromeOS verified boot,
Serenity milestones, SteamOS appliance, Alpine budgets, Arch
explicitness, Haiku focus. Clean-room grep (OS-219): no Linux
identifiers or comments in kernel/ — the one grep that matters
came back empty (see the report).

## Verdict

No GPL in the product. No borrowed code anywhere. Fonts: none
shipped. The audit is a table, not a feeling.
