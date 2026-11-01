//! Meta OS kernel: GDT + TSS/IST setup (Section C, OS-031).
//!
//! The bootloader's GDT is active at entry. This module installs our
//! own GDT (null, kernel code, kernel data, 64-bit TSS) so the
//! double-fault gate can use IST stack 0, then reloads the segments
//! and the task register. `core` only, no dependencies.

/// GDT slot count: null, code, data, TSS low, TSS high (TSS takes
/// two), user code, user data (OS-076/079).
const GDT_LEN: usize = 7;
/// Selector of the kernel code segment in our GDT.
pub const CODE_SELECTOR: u16 = 0x08;
/// Selector of the kernel data segment in our GDT.
const DATA_SELECTOR: u16 = 0x10;
/// Selector of the TSS descriptor in our GDT.
const TSS_SELECTOR: u16 = 0x18;
/// User code segment (ring 3): index 5, RPL 3.
pub const USER_CODE_SELECTOR: u16 = 0x2B;
/// User data segment (ring 3): index 6, RPL 3.
pub const USER_DATA_SELECTOR: u16 = 0x33;
/// Bytes in a 64-bit TSS with no I/O bitmap.
const TSS_SIZE: u16 = 104;

/// 64-bit TSS layout (Intel SDM Vol. 3, Fig. 8-14): reserved word,
/// three privilege stacks, reserved, seven IST stacks, reserved,
/// I/O-map base. Only IST[0] is used (double fault).
///
/// `packed(4)`: RSP0 sits at byte 4, NOT byte 8 — plain `repr(C)`
/// would insert 4 bytes of padding after the opening `u32` and shift
/// every stack pointer, which triple-faults the first IST switch
/// (found the hard way: #DF delivery raised #SS on the QEMU trace).
/// All fields stay 4-aligned, so the CPU's 8-byte loads are fine.
#[repr(C, packed(4))]
struct Tss {
    reserved_0: u32,
    rsp: [u64; 3],
    reserved_1: u64,
    ist: [u64; 7],
    reserved_2: u64,
    _reserved_3: u16,
    iomap_base: u16,
}

impl Tss {
    const fn empty() -> Self {        Tss {
            reserved_0: 0,
            rsp: [0; 3],
            reserved_1: 0,
            ist: [0; 7],
            reserved_2: 0,
            _reserved_3: 0,
            iomap_base: TSS_SIZE,
        }
    }
}

static mut TSS: Tss = Tss::empty();
// The CPU reads fixed byte offsets: the TSS must be exactly 104 bytes.
const _: () = assert!(core::mem::size_of::<Tss>() == 104);
/// Double-fault stack, IST index 1. Top (high address) is installed.
static mut DF_STACK: [u8; 4096] = [0; 4096];
static mut GDT: [u64; GDT_LEN] = [0; GDT_LEN];

fn code_descriptor() -> u64 {
    // base 0, limit 0xFFFFF, access 0x9A (present, ring 0, code,
    // execute/read), flags 0xA (granularity, 64-bit, NOT 32-bit).
    0x00AF9B000000FFFF
}

fn data_descriptor() -> u64 {
    // access 0x92 (present, ring 0, data, writable), flags 0xC.
    0x00CF93000000FFFF
}

fn user_code_descriptor() -> u64 {
    // access 0xFA (present, ring 3, code, execute/read), flags 0xA.
    0x00AFFA000000FFFF
}

fn user_data_descriptor() -> u64 {
    // access 0xF2 (present, ring 3, data, writable), flags 0xC.
    0x00CFF2000000FFFF
}

fn tss_descriptors(tss_addr: u64) -> (u64, u64) {
    let limit = u64::from(TSS_SIZE - 1);
    let low = (limit & 0xFFFF)
        | ((tss_addr & 0xFFFFFF) << 16)
        | (0xE9 << 40) // present, DPL 0, 64-bit available TSS
        | (((limit >> 16) & 0xF) << 48)
        | (((tss_addr >> 24) & 0xFF) << 56);
    let high = tss_addr >> 32;
    (low, high)
}

/// Install our GDT, reload the segment registers, load the task
/// register with the TSS (whose IST[0] is the double-fault stack).
///
/// # Safety
/// Single CPU, interrupts must be off. Rewrites the active GDT.
pub unsafe fn init() {
    let tss_addr = core::ptr::addr_of!(TSS) as u64;
    let stack_top = core::ptr::addr_of!(DF_STACK) as u64 + 4096;
    // `packed(4)`: write through a raw pointer, never a reference.
    unsafe {
        core::ptr::addr_of_mut!(TSS.ist[0]).write_unaligned(stack_top);
    }
    let (tss_lo, tss_hi) = tss_descriptors(tss_addr);
    GDT[1] = code_descriptor();
    GDT[2] = data_descriptor();
    GDT[3] = tss_lo;
    GDT[4] = tss_hi;
    GDT[5] = user_code_descriptor();
    GDT[6] = user_data_descriptor();

    #[repr(C, packed)]
    struct GdtPointer {
        limit: u16,
        base: u64,
    }
    let ptr = GdtPointer {
        limit: (core::mem::size_of::<[u64; GDT_LEN]>() - 1) as u16,
        base: core::ptr::addr_of!(GDT) as u64,
    };
    core::arch::asm!(
        "lgdt [{0}]",
        "push {1:r}",
        "lea {2:r}, [rip + 2f]",
        "push {2:r}",
        "retfq",
        "2:",
        "mov ds, {3:x}",
        "mov es, {3:x}",
        "mov ss, {3:x}",
        "mov fs, {3:x}",
        "mov gs, {3:x}",
        in(reg) &ptr,
        in(reg) u64::from(CODE_SELECTOR),
        out(reg) _,
        in(reg) u64::from(DATA_SELECTOR),
        // No `nostack`: the far return pushes CS:RIP by design.
        options(preserves_flags),
    );
    core::arch::asm!(
        "ltr {0:x}",
        in(reg) TSS_SELECTOR,
        options(nostack, preserves_flags),
    );
}

/// Set the ring-0 stack the CPU loads on a ring 3 -> 0 transition
/// (syscall/IRQ from userspace). The Section F contract sets this to
/// the entering task's OWN kernel stack top, so scheduler calls
/// made from inside a syscall handler switch exactly like
/// task-called ones. Single CPU; call before `iretq` to userspace.
///
/// # Safety
/// The top must be a valid kernel stack for the current task.
pub unsafe fn set_rsp0(top: u64) {
    // `packed(4)`: write through a raw pointer, never a reference.
    core::ptr::addr_of_mut!(TSS.rsp[0]).write_unaligned(top);
}
