//! Meta OS kernel, milestones K1+K2.
//!
//! K1: boots under the rust-osdev bootloader, prints the alive line on
//! the serial port, halts in a spin loop. K2: VGA text-mode console
//! (80x25 at phys 0xB8000 via the bootloader's physical-memory
//! mapping) mirrors every serial line on screen; the panic handler
//! paints a red PANIC screen. No pixel framebuffer exists under
//! bootloader 0.9.35 — see `os-build/research/framebuffer.md`.

#![no_std]
#![no_main]

mod vga;

use core::panic::PanicInfo;
use vga::{Color, ColorSpec, VgaConsole, VGA_PHYS_ADDR};

bootloader::entry_point!(kernel_main);

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

fn serial_write_str(s: &str) {
    for byte in s.bytes() {
        // Wait for the transmit holding register to empty.
        while inb(COM1 + 5) & 0x20 == 0 {}
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

/// Dual-output print: serial port AND VGA console (OS-021). A missing
/// console (before init) degrades to serial only, never to silence.
macro_rules! print {
    ($($arg:tt)*) => {{
        use core::fmt::Write as _;
        let _ = write!(SerialPort, $($arg)*);
        // SAFETY: only `kernel_main` touches CONSOLE, single CPU, no threads yet.
        let slot = unsafe { &mut *core::ptr::addr_of_mut!(CONSOLE) };
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

fn kernel_main(boot_info: &'static bootloader::BootInfo) -> ! {
    serial_init();
    let vga_base =
        (boot_info.physical_memory_offset + VGA_PHYS_ADDR) as *mut u16;
    // SAFETY: bootloader maps all physical memory at the offset, so the
    // VGA text buffer address is valid and writable; 80x25 bounds-checked.
    unsafe {
        *core::ptr::addr_of_mut!(CONSOLE) = Some(VgaConsole::new(
            vga_base,
            ColorSpec(Color::LightGray, Color::Black),
        ));
    }
    println!("META OS - milestone K2");
    println!("META OS KERNEL - alive (K1)");
    #[cfg(feature = "panic-test")]
    panic!("K2 forced panic drill");
    loop {
        core::hint::spin_loop();
    }
}

#[panic_handler]
fn panic(info: &PanicInfo) -> ! {
    use core::fmt::Write as _;
    serial_write_str("META OS KERNEL - panic\n");
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
