# OC2B-032 — KF-01 cross-check table: Rowan vs this Mac (2026-11-02)
Scratch trees detached at 67949822; branch kernel/ untouched. QEMU 11.1.3.

| version | Rowan result (round7 db0b0020) | this Mac result | framebuffer in BootInfo |
|---|---|---|---|
| 0.11.17 | BUILD FAIL: E0463 can't-find-std (x6+ shown), serde_core 5829 errors, no image, no boot | BUILD FAIL, EXIT=101: E0463 x6, serde_core 5829 errors — MATCH (report prose x6+ ✓, 5829 ✓; surviving raw log greps x4 E0463, immaterial) | YES — `pub framebuffer: Optional<FrameBuffer>` (bootloader_api 0.11.17 src/info.rs:33) |
| 0.10.9 (resolves 0.10.13, both lanes) | BUILD FAIL: deps compile, kernel source (0.9 API) does not — E0433 x2, E0408 vars unbound, 15 errors, no image, no boot | BUILD FAIL, EXIT=101, twice (A2 + clean-tree A3): E0433 x2 verbatim, E0408 x9 same vars, 15 errors, 7 warnings, identical tail line — MATCH | YES — `pub framebuffer: Optional<FrameBuffer>` (bootloader 0.10.13 src/boot_info.rs:40) |
| 0.9.35 (current main pin, reference) | boots (baseline gate GREEN) | not re-run in §2 (proven §1: OC2B-baseline-gate.txt GREEN) | NO — fields are memory_map / recursive_page_table_addr / physical_memory_offset only |

Route input for Pax (unchanged from spike): 0.11.x is a dead end without a
std-shim strategy for its dep tree; 0.10.x resolves deps and the remaining
work is source-only (kernel rewrite to the new bootloader API — Rowan's lane).
No newer upgrade candidate is named anywhere; 0.10.9 (the attempted fallback)
is the candidate of record.

OC2B-048 panic note: NO PANIC occurred in §2 — all three scratch builds stop
at compile time, before any image or boot exists. No panic screendump/serial
pair; nothing to capture.
