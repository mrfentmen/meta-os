//! Meta OS kernel, milestone K1.
//!
//! Boots under the rust-osdev bootloader, initialises the COM1 serial
//! port with raw port IO (no external crates), prints the alive line,
//! and halts in a spin loop. The QEMU serial log showing that line is
//! the K1 proof.

#![no_std]
#![no_main]

use core::panic::PanicInfo;

bootloader::entry_point!(kernel_main);

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

fn kernel_main(_boot_info: &'static bootloader::BootInfo) -> ! {
    serial_init();
    serial_write_str("META OS KERNEL - alive (K1)\n");
    loop {
        core::hint::spin_loop();
    }
}

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    serial_write_str("META OS KERNEL - panic\n");
    loop {
        core::hint::spin_loop();
    }
}
