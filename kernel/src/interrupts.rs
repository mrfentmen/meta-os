//! Meta OS kernel, milestone K3: interrupts, timer, keyboard (UNWIRED).
//!
//! Status: **UNCOMPILED, UNVERIFIED, NOT WIRED INTO `main.rs`.**
//! Written in the sandbox, which has no Rust toolchain (`cargo`/`rustc`
//! not installed), so nothing here was compiled and no boot log exists.
//! Per KERNEL_SPEC.md rule 2, this code counts only when it builds on
//! the boss's Mac and a QEMU boot shows its behavior. Per
//! OS_BUILD_TASKS.md R5, it is wired into `main.rs` only onto the
//! proven tree, one module per commit, after a K1 boot log exists.
//! Until then it is code, not a running interrupt system, and no claim
//! is made that it compiles or boots.
//!
//! Authority: boss layer order 2026-11-01 ~08:18, relayed by Pax on
//! room 1 (index 498) and written into OS_BUILD_TASKS.md on main:
//! Layer 0 is Rowan + OpenCode, and Rowan writes the R2/R3 modules
//! unwired with real behavior. That order supersedes the R4 hold in
//! `kernel/MAC_QUESTIONS.md` ("no R2 code until Q1 is answered") for
//! drafting purposes only: `kernel/Cargo.lock` is STILL absent on main
//! (checked this run: 404, main tip 89209d6), so there is still no
//! resolved bootloader version to write against. What this module does
//! about that, honestly, following the R2 precedent in
//! `kernel/src/framebuffer.rs`:
//!
//! - It does NOT import any bootloader type and it does NOT depend on
//!   the `x86_64` crate (not in `kernel/Cargo.toml`). Every structure
//!   below is local, defined from the x86_64 long-mode IDT layout, and
//!   uses `core` only, no `alloc`, no external crate, so it cannot
//!   drag a dependency question into R5.
//! - It does NOT assert a Rust function address into the IDT. A Rust
//!   `fn` is not a valid IDT entry point: a real entry point must
//!   build the interrupt frame and return with `iretq`, which is a
//!   calling-convention property, not something a plain `fn` carries.
//!   The IDT entries are therefore filled by the R5 wiring commit
//!   with the addresses of real asm trampolines (one per vector), and
//!   each trampoline's contract is stated below. No handler ABI name
//!   is asserted here, so none can be wrong here; the ABI decision
//!   (`extern "x86-interrupt"` nightly feature vs asm trampolines) is
//!   open question Q9 in `kernel/MAC_QUESTIONS.md`.
//! - The handlers in this file have their REAL print behavior: when
//!   dispatched, each one writes its real line to the COM1 serial port
//!   with the same raw port IO `kernel/src/main.rs` already uses, and
//!   the timer/keyboard handlers change real state (tick counter,
//!   scancode ring buffer) and send the real PIC end-of-interrupt.
//!   What is NOT claimed: that any handler has ever run. They run only
//!   when the R5 trampolines call `dispatch()`.
//!
//! Trampoline contract (for the R5 commit): for vector `v`, the
//! trampoline pushes an error code if the CPU pushed one (see
//! `has_error_code()`), otherwise pushes zero, builds an
//! `InterruptFrame` with the values the CPU pushed (instruction
//! pointer, code segment, flags, stack pointer, stack segment), calls
//! `dispatch(v, &frame, error_code)`, then returns with `iretq`.
//! Until the trampolines exist, `dispatch()` is callable from ordinary
//! code for testing the print behavior only — that is not an
//! interrupt, and it is not presented as one.
//!
//! Entry-state assumption (Q6, still open): `load_idt()` does not
//! itself enable or disable interrupts. The documented install
//! sequence is: `disable()` (cli), `pic_remap()`, `pit_set_hz()`,
//! `load_idt()`, then `enable()` (sti) — and only once the trampoline
//! addresses are installed. If the Mac build finds the bootloader
//! leaves interrupts enabled on entry, the sequence still holds: the
//! first step is `disable()`.
//!
//! Hardware assumed, to be confirmed on the Mac build (Q9): a dual
//! 8259 PIC at ports 0x20/0x21 and 0xA0/0xA1, a PIT channel 0 at
//! 0x40/0x43 ticking at 1,193,182 Hz, and a PS/2 keyboard at data port
//! 0x60 / status port 0x64. These are the devices QEMU presents to a
//! standard PC target; if the K1 QEMU command line uses anything else,
//! the port map in this file is wrong and the R5 commit must say so.
//!
//! No mocks (KERNEL_SPEC.md rule 6): every function below drives real
//! ports, real table bytes, or real counters. Nothing here prints a
//! canned "interrupt happened" line from a test double; the serial
//! lines are written by the handlers themselves, from the vector and
//! error code they were actually dispatched with.

// ---------------------------------------------------------------------------
// Raw port IO (same shape as kernel/src/main.rs: unsafe asm, nothing else)
// ---------------------------------------------------------------------------

const COM1: u16 = 0x3F8;

fn outb(port: u16, val: u8) {
    unsafe {
        core::arch::asm!("out dx, al", in("dx") port, in("al") val,
            options(nomem, nostack, preserves_flags));
    }
}

fn inb(port: u16) -> u8 {
    let val: u8;
    unsafe {
        core::arch::asm!("in al, dx", out("al") val, in("dx") port,
            options(nomem, nostack, preserves_flags));
    }
    val
}

/// Tiny busy-wait so back-to-back PIC command writes are not lost.
fn io_wait() {
    outb(0x80, 0);
}

// ---------------------------------------------------------------------------
// Serial output (assumes kernel_main already ran serial_init; this file
// only writes, it never re-initialises the UART)
// ---------------------------------------------------------------------------

fn serial_write_byte(byte: u8) {
    while inb(COM1 + 5) & 0x20 == 0 {}
    outb(COM1, byte);
}

fn serial_write_str(s: &str) {
    for byte in s.bytes() {
        serial_write_byte(byte);
    }
}

const HEX_DIGITS: &[u8; 16] = b"0123456789abcdef";

fn serial_write_hex_u64(mut value: u64) {
    let mut buf = [b'0'; 16];
    for i in (0..16).rev() {
        buf[i] = HEX_DIGITS[(value & 0xF) as usize];
        value >>= 4;
    }
    for byte in buf {
        serial_write_byte(byte);
    }
}

// ---------------------------------------------------------------------------
// IDT: 256 long-mode gate descriptors, 16 bytes each
// ---------------------------------------------------------------------------

/// One IDT gate descriptor, x86_64 long mode (Intel SDM Vol. 3, 6.14):
/// offset low 16, segment selector, IST index + reserved, type/attrs,
/// offset mid 16, offset high 32, reserved 32.
#[derive(Clone, Copy)]
#[repr(C)]
pub struct IdtEntry {
    offset_low: u16,
    selector: u16,
    ist: u8,
    type_attr: u8,
    offset_mid: u16,
    offset_high: u32,
    reserved: u32,
}

impl IdtEntry {
    pub const EMPTY: IdtEntry = IdtEntry {
        offset_low: 0,
        selector: 0,
        ist: 0,
        type_attr: 0,
        offset_mid: 0,
        offset_high: 0,
        reserved: 0,
    };

    /// Build a gate from a raw handler address. The caller supplies a
    /// trampoline address (see the header contract), never a Rust `fn`.
    /// `type_attr` must already carry present bit + gate type: 0x8E is
    /// a present 64-bit interrupt gate, 0x8F a present trap gate.
    pub const fn new(handler_addr: u64, selector: u16, ist: u8, type_attr: u8) -> IdtEntry {
        IdtEntry {
            offset_low: handler_addr as u16,
            selector,
            ist: ist & 0x07,
            type_attr,
            offset_mid: (handler_addr >> 16) as u16,
            offset_high: (handler_addr >> 32) as u32,
            reserved: 0,
        }
    }

    /// The handler address this entry points at, reconstructed from
    /// its three offset fields. This is the inverse of `new()` and is
    /// how the R5 commit verifies an installed entry round-trips.
    pub const fn handler_addr(&self) -> u64 {
        (self.offset_low as u64)
            | ((self.offset_mid as u64) << 16)
            | ((self.offset_high as u64) << 32)
    }
}

pub const IDT_ENTRIES: usize = 256;

/// The IDT itself. A single static, mutated only through `idt_set()`
/// before `load_idt()` runs.
pub struct Idt {
    entries: [IdtEntry; IDT_ENTRIES],
}

impl Idt {
    pub const fn new() -> Idt {
        Idt {
            entries: [IdtEntry::EMPTY; IDT_ENTRIES],
        }
    }
}

pub static mut IDT: Idt = Idt::new();

/// Install one gate. Must be called before `load_idt()`; installing
/// into a live IDT is the R5 commit's problem, not this file's.
pub fn idt_set(vector: u8, entry: IdtEntry) {
    unsafe {
        IDT.entries[vector as usize] = entry;
    }
}

/// Read one gate back (for the R5 round-trip check).
pub fn idt_get(vector: u8) -> IdtEntry {
    unsafe { IDT.entries[vector as usize] }
}

/// Operand for `lidt`: 16-bit limit, 64-bit base.
#[repr(C, packed)]
struct DescriptorTablePointer {
    limit: u16,
    base: u64,
}

/// Load the static IDT into the CPU. Unsafe: the caller must have
/// installed valid trampoline addresses for every vector it enables,
/// and must have disabled interrupts first (see header sequence).
pub unsafe fn load_idt() {
    let ptr = DescriptorTablePointer {
        limit: (core::mem::size_of::<Idt>() - 1) as u16,
        base: core::ptr::addr_of!(IDT) as u64,
    };
    unsafe {
        core::arch::asm!("lidt [{}]", in(reg) &ptr,
            options(readonly, nostack, preserves_flags));
    }
}

pub fn disable() {
    unsafe {
        core::arch::asm!("cli", options(nomem, nostack, preserves_flags));
    }
}

pub fn enable() {
    unsafe {
        core::arch::asm!("sti", options(nomem, nostack, preserves_flags));
    }
}

// ---------------------------------------------------------------------------
// 8259 PIC: remap + end-of-interrupt (real port IO, ICW sequence)
// ---------------------------------------------------------------------------

const PIC1_CMD: u16 = 0x20;
const PIC1_DATA: u16 = 0x21;
const PIC2_CMD: u16 = 0xA0;
const PIC2_DATA: u16 = 0xA1;

/// Remap the PICs so IRQ 0..15 arrive as vectors offset1..offset1+15.
/// The standard values are offset1 = 32, offset2 = 40 (vectors 0..31
/// are the CPU exceptions and must never collide with IRQs).
pub fn pic_remap(offset1: u8, offset2: u8) {
    outb(PIC1_CMD, 0x11); // ICW1: init, expect ICW4
    io_wait();
    outb(PIC2_CMD, 0x11);
    io_wait();
    outb(PIC1_DATA, offset1); // ICW2: master vector offset
    io_wait();
    outb(PIC2_DATA, offset2); // ICW2: slave vector offset
    io_wait();
    outb(PIC1_DATA, 0x04); // ICW3: slave at IRQ2
    io_wait();
    outb(PIC2_DATA, 0x02); // ICW3: slave cascade identity
    io_wait();
    outb(PIC1_DATA, 0x01); // ICW4: 8086 mode
    io_wait();
    outb(PIC2_DATA, 0x01);
    io_wait();
    // Unmask everything; masking policy belongs to the R5 commit.
    outb(PIC1_DATA, 0x00);
    outb(PIC2_DATA, 0x00);
}

/// Send end-of-interrupt for an IRQ. IRQs >= 8 must EOI the slave too.
pub fn pic_send_eoi(irq: u8) {
    if irq >= 8 {
        outb(PIC2_CMD, 0x20);
    }
    outb(PIC1_CMD, 0x20);
}

// ---------------------------------------------------------------------------
// PIT timer: channel 0, mode 3 (square wave), divisor from real arithmetic
// ---------------------------------------------------------------------------

const PIT_CH0: u16 = 0x40;
const PIT_CMD: u16 = 0x43;
const PIT_FREQUENCY_HZ: u32 = 1_193_182;

/// Divisor for a target tick rate. 100 Hz -> 11931 (the value is
/// PIT_FREQUENCY_HZ / hz, integer division, remainder dropped).
pub const fn pit_divisor(hz: u32) -> u16 {
    (PIT_FREQUENCY_HZ / hz) as u16
}

/// Program PIT channel 0 to `hz` ticks per second (mode 3, lo/hi bytes).
pub fn pit_set_hz(hz: u32) {
    let divisor = pit_divisor(hz);
    outb(PIT_CMD, 0x36); // channel 0, lo/hi, mode 3
    outb(PIT_CH0, (divisor & 0xFF) as u8);
    outb(PIT_CH0, (divisor >> 8) as u8);
}

static mut TICKS: u64 = 0;

/// Timer ticks since the timer handler first ran. Read by the
/// scheduler-to-be (K5); for now it is the only observable timer state.
pub fn ticks() -> u64 {
    unsafe { TICKS }
}

// ---------------------------------------------------------------------------
// PS/2 keyboard: scancode ring buffer (real port reads)
// ---------------------------------------------------------------------------

const KEYBOARD_DATA: u16 = 0x60;

const KEY_BUFFER_LEN: usize = 64;
static mut KEY_BUFFER: [u8; KEY_BUFFER_LEN] = [0; KEY_BUFFER_LEN];
static mut KEY_HEAD: usize = 0;
static mut KEY_TAIL: usize = 0;

fn keyboard_push(scancode: u8) {
    unsafe {
        let next = (KEY_HEAD + 1) % KEY_BUFFER_LEN;
        if next != KEY_TAIL {
            KEY_BUFFER[KEY_HEAD] = scancode;
            KEY_HEAD = next;
        }
        // Full buffer drops the newest scancode rather than overwriting
        // an unread one; dropping is documented, overwriting would lie.
    }
}

/// Oldest unread scancode, if any. Returns None when the buffer is empty.
pub fn keyboard_read() -> Option<u8> {
    unsafe {
        if KEY_HEAD == KEY_TAIL {
            return None;
        }
        let scancode = KEY_BUFFER[KEY_TAIL];
        KEY_TAIL = (KEY_TAIL + 1) % KEY_BUFFER_LEN;
        Some(scancode)
    }
}

// ---------------------------------------------------------------------------
// Interrupt frame + dispatch
// ---------------------------------------------------------------------------

/// The values the CPU pushes on an interrupt, in push order, as the
/// trampoline must present them. The error code is NOT part of this
/// struct: it travels as `dispatch()`'s third argument because the CPU
/// pushes one only for some vectors (see `has_error_code()`).
#[derive(Clone, Copy)]
#[repr(C)]
pub struct InterruptFrame {
    pub instruction_pointer: u64,
    pub code_segment: u64,
    pub cpu_flags: u64,
    pub stack_pointer: u64,
    pub stack_segment: u64,
}

/// True for the vectors where the CPU pushes an error code: 8, 10-14,
/// 17, 21, 29, 30 (Intel SDM Vol. 3, 6.15). Every other exception and
/// every IRQ has no error code, and the trampoline must push zero.
pub const fn has_error_code(vector: u8) -> bool {
    matches!(vector, 8 | 10 | 11 | 12 | 13 | 14 | 17 | 21 | 29 | 30)
}

/// A handler: real print behavior + real state change, no return value
/// to fake. Called by the trampoline via `dispatch()`.
pub type Handler = fn(&InterruptFrame, u64);

static mut HANDLERS: [Option<Handler>; IDT_ENTRIES] = [None; IDT_ENTRIES];

pub fn register_handler(vector: u8, handler: Handler) {
    unsafe {
        HANDLERS[vector as usize] = Some(handler);
    }
}

/// Dispatch vector `v` to its registered handler, or print the
/// unhandled line if none is registered. This is what the trampoline
/// calls; it is not itself an interrupt entry point.
pub fn dispatch(vector: u8, frame: &InterruptFrame, error_code: u64) {
    let handler = unsafe { HANDLERS[vector as usize] };
    match handler {
        Some(h) => h(frame, error_code),
        None => {
            serial_write_str("INT unhandled vector 0x");
            serial_write_hex_u64(vector as u64);
            serial_write_str(" ip 0x");
            serial_write_hex_u64(frame.instruction_pointer);
            serial_write_str("\n");
        }
    }
}

fn print_exception(name: &str, vector: u8, frame: &InterruptFrame, error_code: u64) {
    serial_write_str("INT exception ");
    serial_write_str(name);
    serial_write_str(" vector 0x");
    serial_write_hex_u64(vector as u64);
    serial_write_str(" ip 0x");
    serial_write_hex_u64(frame.instruction_pointer);
    if has_error_code(vector) {
        serial_write_str(" err 0x");
        serial_write_hex_u64(error_code);
    }
    serial_write_str("\n");
}

pub fn divide_error_handler(frame: &InterruptFrame, error_code: u64) {
    print_exception("divide-error", 0, frame, error_code);
}

pub fn debug_handler(frame: &InterruptFrame, error_code: u64) {
    print_exception("debug", 1, frame, error_code);
}

pub fn breakpoint_handler(frame: &InterruptFrame, error_code: u64) {
    print_exception("breakpoint", 3, frame, error_code);
}

pub fn invalid_opcode_handler(frame: &InterruptFrame, error_code: u64) {
    print_exception("invalid-opcode", 6, frame, error_code);
}

pub fn double_fault_handler(frame: &InterruptFrame, error_code: u64) {
    print_exception("double-fault", 8, frame, error_code);
}

pub fn general_protection_handler(frame: &InterruptFrame, error_code: u64) {
    print_exception("general-protection", 13, frame, error_code);
}

pub fn page_fault_handler(frame: &InterruptFrame, error_code: u64) {
    // Mac-build note (opencode/os-build, OS-040): the fault ADDRESS
    // lives in CR2, which the CPU does not push. Read it here so the
    // log shows address + error code, not just the faulting ip.
    let addr: u64;
    unsafe {
        core::arch::asm!("mov {}, cr2", out(reg) addr,
            options(nomem, nostack, preserves_flags));
    }
    // OS-085: a ring-3 fault kills only that userspace task — log it,
    // exit the task, and let the kernel (and the console task) carry
    // on. Never iret back into the faulting context.
    if frame.code_segment & 3 == 3 {
        serial_write_str("INT user page-fault addr 0x");
        serial_write_hex_u64(addr);
        serial_write_str(" err 0x");
        serial_write_hex_u64(error_code);
        serial_write_str(": task killed\n");
        crate::sched::exit_task();
    }
    serial_write_str("INT exception page-fault vector 0x");
    serial_write_hex_u64(14);
    serial_write_str(" addr 0x");
    serial_write_hex_u64(addr);
    serial_write_str(" ip 0x");
    serial_write_hex_u64(frame.instruction_pointer);
    serial_write_str(" err 0x");
    serial_write_hex_u64(error_code);
    serial_write_str("\n");
}

/// IRQ 0 (vector 32 after the standard remap): count the tick, EOI.
/// It deliberately prints nothing per tick: at 100 Hz a print per tick
/// would flood the serial log and bury every other line. The count is
/// observable through `ticks()`.
pub fn timer_handler(_frame: &InterruptFrame, _error_code: u64) {
    unsafe {
        TICKS += 1;
    }
    pic_send_eoi(0);
}

/// IRQ 1 (vector 33 after the standard remap): read the scancode from
/// port 0x60, buffer it, print it in hex, EOI. One key press is one
/// line, so printing here does not flood.
pub fn keyboard_handler(_frame: &InterruptFrame, _error_code: u64) {
    let scancode = inb(KEYBOARD_DATA);
    keyboard_push(scancode);
    serial_write_str("INT keyboard scancode 0x");
    serial_write_hex_u64(scancode as u64);
    serial_write_str("\n");
    pic_send_eoi(1);
}

/// Register the built-in handlers. Does not touch the IDT: the R5
/// commit installs trampoline addresses with `idt_set()` and calls
/// `load_idt()`; this only fills the dispatch table.
pub fn register_builtins() {
    register_handler(0, divide_error_handler);
    register_handler(1, debug_handler);
    register_handler(3, breakpoint_handler);
    register_handler(6, invalid_opcode_handler);
    register_handler(8, double_fault_handler);
    register_handler(13, general_protection_handler);
    register_handler(14, page_fault_handler);
    register_handler(32, timer_handler);
    register_handler(33, keyboard_handler);
}
