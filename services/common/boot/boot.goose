// services/common/boot/boot.goose
//
// B-L1-08: the BootInfo block, as Goose sees it.
//
// Status: WRITTEN (not COMPILED). Verified forms: struct with typed fields and
// defaults (tutorial#3, samples/01_tour.goose), fixed arrays `T[..N]` and
// `u8[..N]` (samples/03_strings.goose), i32/i64/u32/u64 keywords
// (list_keywords), reference parameter `&` (spec#40).
//
// WHAT THIS MIRRORS, HONESTLY
//
// The kernel today is K1 only: `kernel/src/main.rs` (66 lines). It receives
// `&'static mut bootloader::BootInfo` at line 52 and ignores it (`_boot_info`).
// There is NO framebuffer module in the tree -- no K2 -- so there is no
// `FramebufferInfo` to mirror field by field, which is what this task asks for.
//
// So this file is split in two, and the split is the point:
//   - the parts marked [K1] mirror something that exists and cite the line;
//   - the parts marked [PROPOSED] are this layer's request to Rowan's K2/K3
//     work. They are not a mirror of anything. Anyone reading a field marked
//     [PROPOSED] should treat it as a proposal on the table, not a fact.
//
// If Rowan's K2 lands with a different field set, THIS file changes to match
// the kernel -- never the other way round. KERNEL_SPEC.md is the law.

// ---------------------------------------------------------------------------
// [K1] Serial: the one output path that exists today.
// ---------------------------------------------------------------------------
//
// kernel/src/main.rs lines 15 and 33-42: COM1 at 0x3F8, 16550 initialisation,
// 8N1, FIFO on, divisor 3 = 38400 baud. Line 44-50 writes a string by polling
// the transmit-holding-register-empty bit (line status bit 0x20).
//
// A service does not touch the UART: it calls sys_write_serial (see sys.goose).
// These fields exist so the service can state the line settings it is logging
// on, which is the difference between a useful boot record and a guess.

struct SerialInfo {
    port: u16,          // [K1] main.rs:15  COM1 = 0x3F8
    baud: u32,          // [K1] main.rs:37  divisor 3 at 115200 base = 38400
    data_bits: u8,      // [K1] main.rs:39  8
    stop_bits: u8,      // [K1] main.rs:39  1
    parity: u8,         // [K1] main.rs:39  none (0)
}

// ---------------------------------------------------------------------------
// [PROPOSED] Framebuffer: what K2 will hand over.
// ---------------------------------------------------------------------------
//
// No K2 module exists. Rowan's R2 writes `kernel/src/framebuffer` against the
// bootloader version in the lockfile. The field set below is the minimum a text
// console needs and nothing more: services draw characters, not graphics, until
// something needs otherwise.

struct FramebufferInfo {
    address: u64,       // [PROPOSED] physical base of the framebuffer
    width: u32,         // [PROPOSED] pixels
    height: u32,        // [PROPOSED] pixels
    stride: u32,        // [PROPOSED] bytes per scanline, which is NOT width*4
    pixel_format: u32,  // [PROPOSED] 0 = RGB32, 1 = BGR32, 2 = other
    glyph_width: u16,   // [PROPOSED] pixels per character cell
    glyph_height: u16,  // [PROPOSED] pixels per character cell
    cols: u16,          // [PROPOSED] width / glyph_width, precomputed by kernel
    rows: u16,          // [PROPOSED] height / glyph_height
}

// ---------------------------------------------------------------------------
// [PROPOSED] Timing: what K3 hands over.
// ---------------------------------------------------------------------------
//
// `time` (services/time) currently *requests* 1000 Hz and says so. If the
// kernel picks a different rate, it says so here and one line in `time` changes.

struct TimeInfo {
    tick_hz: u32,       // [PROPOSED] ticks per second; services never assume
    boot_ticks: i64,    // [PROPOSED] ticks already elapsed when we start
}

// ---------------------------------------------------------------------------
// [K1-ish] Memory: a summary, not a map.
// ---------------------------------------------------------------------------
//
// K1 proves nothing about memory; K4 owns paging and the heap. A service needs
// exactly two numbers to size itself honestly: how much static storage it was
// granted, and how much of the machine is real. Anything richer is K4's design
// and would be invented here.

struct MemoryInfo {
    total_bytes: u64,   // [PROPOSED] usable RAM
    service_bytes: u64, // [PROPOSED] this process's static allowance (A10)
}

// ---------------------------------------------------------------------------
// The block
// ---------------------------------------------------------------------------

// Field order is part of the contract: the kernel lays this out, the service
// reads it, and neither may reorder without the other. `version` is first so a
// service can refuse a block it does not understand instead of misreading it.
struct BootInfo {
    version: u32,
    serial: SerialInfo,
    framebuffer: FramebufferInfo,
    time: TimeInfo,
    memory: MemoryInfo,
    // Reserved: pad so future fields can be added without moving anything a
    // service already reads. A fixed size here is cheaper than a version bump
    // every time the kernel learns something new.
    reserved: u64[..8] = [0; 8],
}

// The version this source understands. Bump it in the same commit that changes
// a field above, and never silently.
let BOOTINFO_VERSION = 1;

// A service that cannot read the block correctly must fail loudly at start-up,
// not run on garbage. This is the check every service's entry makes first.
fn bootinfo_supported(boot: BootInfo&) -> bool {
    return boot.version == BOOTINFO_VERSION;
}

// ---------------------------------------------------------------------------
// Open items (also in os-build/layer1/BOUNDARIES.md)
// ---------------------------------------------------------------------------
//
// Q-B-L1-4: how the block reaches the service -- argument pointer (as
// SERVICE_CONTRACT.md §2 assumes), a fixed address, or a syscall the service
// makes. Rowan owns this, and the answer changes the entry signature of every
// service in the layer.
//
// Deviation carried from B-L1-03: `bootlog` and `time` take no argument yet
// because this file did not exist when they were written. They are not edited
// retroactively here; the plumbing happens when the kernel can actually pass a
// block, which is K6. Until then the entry signature difference is a known,
// recorded gap rather than a silent one.
