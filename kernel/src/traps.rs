//! Meta OS kernel: interrupt entry wiring (Section C, OS-029..OS-044).
//!
//! Rowan's `interrupts.rs` owns the IDT table, the PIC/PIT/keyboard
//! drivers, and the dispatch table. This module is the R5 wiring it
//! was written for: per-vector asm trampolines, one common stub that
//! saves the scratch registers, builds the argument triple, and calls
//! back into `dispatch`, plus the install sequence. `core` only.

use core::arch::global_asm;

use crate::gdt::CODE_SELECTOR;
use crate::interrupts::{
    self, has_error_code, idt_get, idt_set, IdtEntry, InterruptFrame,
};

/// Vectors wired to trampolines: CPU exceptions of interest plus the
/// two remapped IRQs. The error-code set must match
/// `interrupts::has_error_code` (8, 10-14 here).
const VECTORS: [u8; 12] = [0, 1, 3, 6, 8, 10, 11, 12, 13, 14, 32, 33];

macro_rules! trap_gate {
    ($name:ident, $vec:expr, dummy) => {
        global_asm!(concat!(
            ".globl ",
            stringify!($name),
            "\n.type ",
            stringify!($name),
            ",@function\n",
            stringify!($name),
            ":\n",
            "push 0\n",
            "push ",
            stringify!($vec),
            "\njmp trap_common\n",
        ));
    };
    ($name:ident, $vec:expr, cpu) => {
        global_asm!(concat!(
            ".globl ",
            stringify!($name),
            "\n.type ",
            stringify!($name),
            ",@function\n",
            stringify!($name),
            ":\n",
            "push ",
            stringify!($vec),
            "\njmp trap_common\n",
        ));
    };
}

trap_gate!(trap_0, 0, dummy);
trap_gate!(trap_1, 1, dummy);
trap_gate!(trap_3, 3, dummy);
trap_gate!(trap_6, 6, dummy);
trap_gate!(trap_8, 8, cpu);
trap_gate!(trap_10, 10, cpu);
trap_gate!(trap_11, 11, cpu);
trap_gate!(trap_12, 12, cpu);
trap_gate!(trap_13, 13, cpu);
trap_gate!(trap_14, 14, cpu);
trap_gate!(trap_32, 32, dummy);
trap_gate!(trap_33, 33, dummy);
trap_gate!(trap_128, 128, dummy);

// Common entry: stack on arrival (top first) is
//   [vector][error][rip][cs][rflags][rsp][ss]
// (CPU frame first, then our two pushes). Save the nine scratch
// registers, then rdi = vector, rsi = &frame (rip..ss), rdx = error.
// 136 bytes are skipped past the red zone before the call; the call
// itself needs 16-byte alignment, which the sub/add pair preserves.
global_asm!(
    ".globl trap_common\n",
    ".type trap_common,@function\n",
    "trap_common:\n",
    "push rax\n",
    "push rcx\n",
    "push rdx\n",
    "push rsi\n",
    "push rdi\n",
    "push r8\n",
    "push r9\n",
    "push r10\n",
    "push r11\n",
    "mov rdi, [rsp + 72]\n",
    "lea rsi, [rsp + 88]\n",
    "mov rdx, [rsp + 80]\n",
    "sub rsp, 136\n",
    "call dispatch_trampoline\n",
    "add rsp, 136\n",
    "pop r11\n",
    "pop r10\n",
    "pop r9\n",
    "pop r8\n",
    "pop rdi\n",
    "pop rsi\n",
    "pop rdx\n",
    "pop rcx\n",
    "pop rax\n",
    "add rsp, 16\n",
    "iretq\n",
);

extern "C" {
    fn trap_0();
    fn trap_1();
    fn trap_3();
    fn trap_6();
    fn trap_8();
    fn trap_10();
    fn trap_11();
    fn trap_12();
    fn trap_13();
    fn trap_14();
    fn trap_32();
    fn trap_33();
    fn trap_128();
}

// `trap_common` reads its arguments at fixed offsets from the stack it
// builds: nine register pushes (72 bytes), then the vector and error code it
// pushed, so the CPU frame starts at rsp+88 and runs rip..ss. Those literals
// are only correct while `InterruptFrame` has this exact layout. If the struct
// changes shape, the stub would hand `dispatch` garbage and every handler
// would print nonsense about a fault that never happened — silently, at boot.
// These fail the build instead.
const _: () = {
    assert!(core::mem::size_of::<InterruptFrame>() == 40);
    assert!(core::mem::offset_of!(InterruptFrame, instruction_pointer) == 0);
    assert!(core::mem::offset_of!(InterruptFrame, code_segment) == 8);
    assert!(core::mem::offset_of!(InterruptFrame, cpu_flags) == 16);
    assert!(core::mem::offset_of!(InterruptFrame, stack_pointer) == 24);
    assert!(core::mem::offset_of!(InterruptFrame, stack_segment) == 32);
};

fn trap_addr(vector: u8) -> u64 {
    let f: unsafe extern "C" fn() = match vector {
        0 => trap_0,
        1 => trap_1,
        3 => trap_3,
        6 => trap_6,
        8 => trap_8,
        10 => trap_10,
        11 => trap_11,
        12 => trap_12,
        13 => trap_13,
        14 => trap_14,
        32 => trap_32,
        33 => trap_33,
        128 => trap_128,
        _ => unreachable!(),
    };
    f as usize as u64
}

/// Rust entry point for the asm stub. Named without mangling so
/// `trap_common` can `call` it directly.
#[no_mangle]
pub extern "C" fn dispatch_trampoline(
    vector: u64,
    frame: *const InterruptFrame,
    error_code: u64,
) {
    // SAFETY: the stub passes the vector it was entered on, a pointer
    // to the live CPU frame, and the pushed error code. Single CPU,
    // interrupts already masked by the interrupt gate.
    unsafe {
        interrupts::dispatch(vector as u8, &*frame, error_code);
    }
}

/// Install one gate per wired vector (present 64-bit interrupt gate;
/// double fault on IST stack 0) and round-trip-check every address.
/// Vector 128 (`int 0x80`, the syscall gate) is DPL 3 (0xEE) so ring 3
/// can enter; all others are ring 0 only (0x8E).
pub fn install() {
    for vector in VECTORS {
        let ist = if vector == 8 { 1 } else { 0 };
        idt_set(
            vector,
            IdtEntry::new(trap_addr(vector), CODE_SELECTOR, ist, 0x8E),
        );
        debug_assert!(idt_get(vector).handler_addr() == trap_addr(vector));
    }
    idt_set(
        128,
        IdtEntry::new(trap_addr(128), CODE_SELECTOR, 0, 0xEE),
    );
    debug_assert!(idt_get(128).handler_addr() == trap_addr(128));
}

/// True only for vectors the CPU pushes an error code for; the
/// trampoline set above must agree with this.
pub fn trampolines_match_cpu() -> bool {
    VECTORS
        .iter()
        .all(|v| has_error_code(*v) == matches!(*v, 8 | 10 | 11 | 12 | 13 | 14))
}
