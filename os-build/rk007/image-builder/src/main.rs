use bootloader::BiosBoot;
use std::path::Path;

fn main() {
    let mut args = std::env::args().skip(1);
    let kernel = args.next().expect("usage: rk007-image-builder <kernel-elf> <out-img>");
    let out = args.next().expect("usage: rk007-image-builder <kernel-elf> <out-img>");
    println!("rk007-image-builder: bootloader 0.11 BIOS flow (no bootimage)");
    println!("  kernel {kernel}");
    println!("  out    {out}");
    BiosBoot::new(Path::new(&kernel))
        .create_disk_image(Path::new(&out))
        .expect("create_disk_image failed");
    let n = std::fs::metadata(&out).expect("image missing").len();
    println!("  image  {n} bytes");
}
