//! rk007-builder — the bootloader 0.11 host-side image builder.
//!
//! Usage: rk007-builder <kernel-elf> <out-image>
//!
//! In bootloader 0.11 there is no `cargo bootimage`: the host-side
//! `bootloader` crate builds the image itself. `BiosBoot::new(kernel)`
//! stages the BIOS bootloader, and `create_disk_image(path)` writes the raw
//! image QEMU boots. The kernel ELF is passed through untouched — this
//! never edits or relinks kernel code.

use std::path::Path;

fn main() {
    let mut args = std::env::args().skip(1);
    let (kernel, out) = match (args.next(), args.next()) {
        (Some(k), Some(o)) => (k, o),
        _ => {
            eprintln!("usage: rk007-builder <kernel-elf> <out-image>");
            std::process::exit(2);
        }
    };
    let kernel = Path::new(&kernel);
    if !kernel.is_file() {
        eprintln!("rk007-builder: kernel ELF not found: {}", kernel.display());
        std::process::exit(1);
    }
    println!("rk007-builder: kernel {}", kernel.display());

    let out_path = Path::new(&out);
    let boot = bootloader::BiosBoot::new(kernel);

    // 0.11 takes the destination path and returns the unit type. There is no
    // returned path to print, so the size is read back from the filesystem.
    if let Err(e) = boot.create_disk_image(out_path) {
        eprintln!("rk007-builder: image build failed: {e}");
        std::process::exit(1);
    }

    match std::fs::metadata(out_path) {
        Ok(meta) if meta.len() > 0 => println!(
            "rk007-builder: image {} ({} bytes)",
            out_path.display(),
            meta.len()
        ),
        Ok(_) => {
            eprintln!("rk007-builder: image is empty: {}", out_path.display());
            std::process::exit(1);
        }
        Err(e) => {
            eprintln!("rk007-builder: image missing after build: {e}");
            std::process::exit(1);
        }
    }
}
