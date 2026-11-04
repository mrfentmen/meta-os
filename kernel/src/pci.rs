//! Meta OS kernel, build-out K5 storage step 1 (Lane E, R5).
//!
//! Read-only PCI scan: configuration mechanism #1 (`0xCF8` / `0xCFC`),
//! bus 0, every device/function. Logs one line per present device with
//! its real vendor:device and class bytes read from hardware. Attaches
//! NO driver, maps NO BAR, performs NO disk I/O: storage (IDE /
//! virtio-blk) stays NOT BUILT after this step, and the scan names the
//! exact device the next lane must drive. `core` only.
//!
//! Absent slots read vendor `0xFFFF` and are skipped silently — that is
//! the refusal path for this probe: no device, no line, no state change.
//! A scan that printed 256 absent lines would bury the present ones.

const PCI_ADDR: u16 = 0xCF8;
const PCI_DATA: u16 = 0xCFC;

fn outl(port: u16, val: u32) {
    unsafe {
        core::arch::asm!("out dx, eax", in("dx") port, in("eax") val,
            options(nomem, nostack, preserves_flags));
    }
}

fn inl(port: u16) -> u32 {
    let val: u32;
    unsafe {
        core::arch::asm!("in eax, dx", out("eax") val, in("dx") port,
            options(nomem, nostack, preserves_flags));
    }
    val
}

/// Read one 32-bit config register. `offset` must be 4-aligned and < 256.
fn cfg_read(bus: u8, dev: u8, func: u8, offset: u8) -> u32 {
    let addr: u32 = (1 << 31)
        | ((bus as u32) << 16)
        | ((dev as u32) << 11)
        | ((func as u32) << 8)
        | ((offset as u32) & 0xFC);
    outl(PCI_ADDR, addr);
    inl(PCI_DATA)
}

/// True when function `func` of (`bus`, `dev`) answers at all.
fn present(bus: u8, dev: u8, func: u8) -> bool {
    (cfg_read(bus, dev, func, 0) & 0xFFFF) != 0xFFFF
}

/// Scan bus 0 and log every present device. Returns the device count.
/// Prints through `println!` (serial + VGA + framebuffer, like boot).
pub fn probe() -> usize {
    println!("PCI scan: bus 0");
    let mut n = 0usize;
    for dev in 0..32u8 {
        // Function 0 decides: absent means no device here at all.
        if !present(0, dev, 0) {
            continue;
        }
        // Header type bit 7 set means multifunction: probe all 8.
        let multifunction = (cfg_read(0, dev, 0, 0x0C) >> 16) & 0x80 != 0;
        let funcs = if multifunction { 8 } else { 1 };
        for func in 0..funcs {
            if !present(0, dev, func) {
                continue;
            }
            let id = cfg_read(0, dev, func, 0);
            let class = cfg_read(0, dev, func, 0x08);
            println!(
                "pci 00:{}.{} {:04x}:{:04x} class {:02x}/{:02x}/{:02x}",
                dev,
                func,
                id & 0xFFFF,
                (id >> 16) & 0xFFFF,
                (class >> 24) & 0xFF,
                (class >> 16) & 0xFF,
                (class >> 8) & 0xFF,
            );
            n += 1;
        }
    }
    println!("PCI scan done, {} devices", n);
    n
}
