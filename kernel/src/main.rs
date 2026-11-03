//! Meta OS kernel, milestones K1+K2.
//!
//! K1: boots under the rust-osdev bootloader, prints the alive line on
//! the serial port, halts in a spin loop. K2: VGA text-mode console
//! (80x25 at phys 0xB8000 via the bootloader's physical-memory
//! mapping) mirrors every serial line on screen; the panic handler
//! paints a red PANIC screen. RK-008: the kernel side now speaks
//! bootloader_api 0.11 (see BOOTLOADER_CONFIG); the pixel
//! framebuffer field exists there (`Optional<FrameBuffer>`) but is
//! still unwired — that wiring is KF-03, not this rewrite — see
//! `os-build/research/framebuffer.md`.
//!
//! K3 evidence (2026-11-02): `prove_timer` measures the PIT by waiting
//! on the handler's tick counter, so the boot log carries a real
//! `K3 timer:` line rather than the inference "sleep worked, so a timer
//! must be firing". The keyboard half of K3 is proven by the console
//! echo in the same log when QEMU is given keystrokes.

#![no_std]
#![no_main]

extern crate alloc;

/// Dual-output print: serial port AND VGA console (OS-021). A missing
/// console (before init) degrades to serial only, never to silence.
/// Defined before the `mod` lines so every module sees it.
macro_rules! print {
    ($($arg:tt)*) => {{
        use core::fmt::Write as _;
        let _ = write!($crate::SerialPort, $($arg)*);
        // SAFETY: only `kernel_main` touches CONSOLE, single CPU, no threads yet.
        let slot = unsafe { &mut *core::ptr::addr_of_mut!($crate::CONSOLE) };
        if let Some(console) = slot {
            let _ = write!(console, $($arg)*);
        }
    }};
}

macro_rules! println {
    () => {
        print!("\n")
    };
    ($($arg:tt)*) => {
        print!($($arg)*);
        print!("\n")
    };
}

mod gdt;
mod interrupts;
mod logo_frames;
mod mem;
mod memory;
mod sched;
mod tasks;
mod traps;
mod user;
mod vga;

use core::panic::PanicInfo;
use vga::{Color, ColorSpec, VgaConsole, VGA_PHYS_ADDR};

/// Bootloader configuration (RK-008, bootloader_api 0.11). The default
/// config leaves `mappings.physical_memory` as `None`, and with no
/// mapping `physical_memory_offset` arrives as `Optional::None` — the
/// VGA base in `kernel_main` and `mem_init` would have nothing to work
/// through. Request a dynamic full-physical-memory mapping, the 0.11
/// replacement for the 0.9 `map_physical_memory` cargo feature.
pub static BOOTLOADER_CONFIG: bootloader_api::BootloaderConfig = {
    let mut config = bootloader_api::BootloaderConfig::new_default();
    config.mappings.physical_memory = Some(bootloader_api::config::Mapping::Dynamic);
    config
};

bootloader_api::entry_point!(kernel_main, config = &BOOTLOADER_CONFIG);

const COM1: u16 = 0x3F8;

/// The boot console. `None` until `kernel_main` maps the VGA buffer.
static mut CONSOLE: Option<VgaConsole> = None;

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

/// Standard 16550 UART initialisation: 38400 baud, 8N1, FIFO on.
fn serial_init() {
    outb(COM1 + 1, 0x00); // disable interrupts
    outb(COM1 + 3, 0x80); // DLAB on
    outb(COM1 + 0, 0x03); // divisor low: 3 (38400 baud)
    outb(COM1 + 1, 0x00); // divisor high
    outb(COM1 + 3, 0x03); // 8 bits, no parity, 1 stop bit; DLAB off
    outb(COM1 + 2, 0xC7); // FIFO on, clear, 14-byte threshold
    outb(COM1 + 4, 0x0B); // DTR + RTS + OUT2
}

/// How many status-port reads a transmit wait may take before the kernel
/// gives up on the UART. At a few ns per read this is tens of milliseconds.
const SERIAL_TX_SPINS: u32 = 100_000;

/// Write a string to COM1. The wait for the transmit holding register is
/// bounded on purpose: an unbounded `while inb(...) & 0x20 == 0 {}` hangs the
/// whole kernel on a missing or wedged UART, and a boot that never reaches
/// its first line is indistinguishable from a crash. Dropping the rest of the
/// line after SERIAL_TX_SPINS is the lesser failure — it is visible in the
/// log as a truncated line, and the machine keeps running.
fn serial_write_str(s: &str) {
    for byte in s.bytes() {
        let mut spins: u32 = 0;
        while inb(COM1 + 5) & 0x20 == 0 {
            spins += 1;
            if spins >= SERIAL_TX_SPINS {
                return;
            }
        }
        outb(COM1, byte);
    }
}

/// `core::fmt::Write` sink for the serial port, so `print!` can
/// target both outputs through the same `write!` machinery.
struct SerialPort;

impl core::fmt::Write for SerialPort {
    fn write_str(&mut self, s: &str) -> core::fmt::Result {
        serial_write_str(s);
        Ok(())
    }
}

fn kernel_main(boot_info: &'static mut bootloader_api::BootInfo) -> ! {
    serial_init();
    // 0.11: the offset is `Optional<u64>`, present only when the config
    // maps physical memory (BOOTLOADER_CONFIG above does). Without it
    // there is no VGA base and no `mem_init` mapping; fail loudly on
    // serial via the panic handler instead of computing a bogus base.
    let phys_offset = boot_info
        .physical_memory_offset
        .into_option()
        .expect("RK-008: bootloader did not map physical memory");
    let vga_base = (phys_offset + VGA_PHYS_ADDR) as *mut u16;
    // SAFETY: bootloader maps all physical memory at the offset, so the
    // VGA text buffer address is valid and writable; 80x25 bounds-checked.
    unsafe {
        *core::ptr::addr_of_mut!(CONSOLE) = Some(VgaConsole::new(
            vga_base,
            ColorSpec(Color::LightGray, Color::Black),
        ));
    }
    println!("META OS 0.1 (K6)");
    println!("META OS KERNEL - alive (K1)");
    #[cfg(feature = "panic-test")]
    panic!("K2 forced panic drill");
    // Section C install sequence (interrupts.rs documented order):
    // own GDT+TSS first, handlers, gates, then cli/remap/pit/lidt/sti.
    unsafe {
        gdt::init();
    }
    interrupts::register_builtins();
    traps::install();
    debug_assert!(traps::trampolines_match_cpu());
    interrupts::disable();
    interrupts::pic_remap(32, 40);
    interrupts::pit_set_hz(100);
    unsafe {
        interrupts::load_idt();
    }
    interrupts::enable();
    prove_timer();
    // Section D: frames, mapper, heap (IDT is live, so a stray fault
    // prints instead of triple-faulting).
    unsafe {
        mem::mem_init(&*boot_info);
    }
    #[cfg(feature = "break-test")]
    unsafe {
        core::arch::asm!("int3", options(nomem, nostack, preserves_flags));
    }
    #[cfg(feature = "fault-test")]
    unsafe {
        core::ptr::read_volatile(0xdead_beef as *const u8);
    }
    #[cfg(feature = "stack-test")]
    stack_overflow(0);
    // Section E: multitasking takes over (console task keeps the
    // echo loop and uptime; A/B/C prove rotation, sleep, exit).
    unsafe {
        sched::sched_init();
        sched::start_demo_tasks();
    }
}

/// K3 proof: wait for the PIT IRQ to actually advance `ticks()`, and say
/// so in the log. The install sequence above programs the PIC and PIT and
/// loads the IDT, but none of that is evidence that a timer interrupt ever
/// fired; the scheduler's sleep working is an inference, not a line.
///
/// Two properties matter. It is a measurement, not a canned print: `got`
/// comes from the handler's own counter. And it is bounded: a dead PIC
/// must not hang the boot, so after SPIN_LIMIT iterations it prints the
/// failure in the same shape. A silent boot would look identical to a
/// working one, which is exactly what this project keeps getting wrong.
fn prove_timer() {
    const WANT_TICKS: u64 = 10;
    const SPIN_LIMIT: u64 = 400_000_000;
    let start = interrupts::ticks();
    let mut spins: u64 = 0;
    while interrupts::ticks() < start.saturating_add(WANT_TICKS) && spins < SPIN_LIMIT {
        spins = spins.wrapping_add(1);
        core::hint::spin_loop();
    }
    let got = interrupts::ticks().saturating_sub(start);
    if got >= WANT_TICKS {
        println!("K3 timer: {} ticks after {} spins", got, spins);
    } else {
        println!(
            "K3 timer: FAILED, {} ticks after {} spins (PIT not firing)",
            got, spins
        );
    }
}

/// Test-only drill (OS-031, `stack-test` builds): recurse with 2 KiB
/// frames until the stack overflows. The nested fault escalates to a
/// double fault, which must arrive on the IST stack and print. Never
/// compiled into normal builds.
#[cfg(feature = "stack-test")]
#[inline(never)]
fn stack_overflow(depth: u64) -> u64 {
    let pad = [0xAAu8; 2048];
    let mut sum = depth;
    for b in pad {
        sum = sum.wrapping_add(b as u64);
    }
    sum + stack_overflow(depth + 1)
}

#[panic_handler]
fn panic(info: &PanicInfo) -> ! {
    use core::fmt::Write as _;
    serial_write_str("META OS KERNEL - panic\n");
    // The serial log is where a panic is actually read; the screen is for
    // whoever is standing in front of the machine. `PanicInfo`'s Display is
    // "panicked at <file>:<line>:\n<message>", so the message and the exact
    // location reach the log, not just a banner that says something broke.
    let mut serial = SerialPort;
    let _ = write!(serial, "{}\n", info);
    // SAFETY: same single-CPU reasoning as `print!`.
    let slot = unsafe { &mut *core::ptr::addr_of_mut!(CONSOLE) };
    if let Some(console) = slot {
        console.set_colors(ColorSpec(Color::White, Color::Red));
        console.clear();
        let _ = write!(console, "META OS KERNEL - PANIC\n{}", info);
    }
    loop {
        core::hint::spin_loop();
    }
}
