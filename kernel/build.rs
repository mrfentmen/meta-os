//! Kernel build script (OS-077): stages the userspace ELFs into
//! OUT_DIR for `include_bytes!`. It does NOT build them — the
//! userspace crates build first (`os-build/userspace/user`, normal
//! `cargo build --target x86_64-unknown-none`; the Section N
//! pipeline runs both in order). A nested cargo from inside build.rs
//! proved unreliable here (stale artifacts, silent flag loss), so
//! the ordering lives in the pipeline script instead, stated, not
//! hidden. Missing ELFs fail here with the exact recovery command.

use std::path::PathBuf;

const BINS: &[&str] = &["hello", "sleeper", "crasher", "readkey", "demand"];

fn main() {
    let kernel_dir = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").unwrap());
    let user_dir = kernel_dir.join("../os-build/userspace/user");
    // Watch every userspace source individually: a bare directory
    // watch only fires on entry add/remove, never on content edits
    // (that staleness bug cost an hour — see the report).
    fn watch_dir(dir: &std::path::Path) {
        for entry in std::fs::read_dir(dir).expect("build.rs: read src").flatten() {
            let path = entry.path();
            if path.is_dir() {
                watch_dir(&path);
            } else {
                println!("cargo:rerun-if-changed={}", path.display());
            }
        }
    }
    watch_dir(&user_dir.join("src"));
    for f in ["Cargo.toml", "link.ld", ".cargo/config.toml"] {
        println!("cargo:rerun-if-changed={}", user_dir.join(f).display());
    }

    let profile = std::env::var("PROFILE").unwrap();
    let out = PathBuf::from(std::env::var("OUT_DIR").unwrap());
    for bin in BINS {
        let elf = user_dir
            .join("target")
            .join("x86_64-unknown-none")
            .join(&profile)
            .join(bin);
        let dest = out.join(format!("{}.elf", bin));
        std::fs::copy(&elf, &dest).unwrap_or_else(|_| {
            panic!(
                "build.rs: {} missing — build userspace first: \
                 cd os-build/userspace/user && cargo build --target x86_64-unknown-none --bins",
                elf.display()
            )
        });
    }
}
