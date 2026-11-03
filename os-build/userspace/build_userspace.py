#!/usr/bin/env python3
"""Build the kernel's userspace programs at distinct link bases (RK-013/14/15).

Cause (diagnosed from Pax's RK-007 ruling + the tree, not from a boot
log on this VM): the kernel loader (`kernel/src/user.rs`, `load_elf`)
maps every LOAD segment at its linked address and refuses any page
already mapped -- "address in use" is a hard refusal across ELFs.
The userspace crate's build line never passed a linker script:
`os-build/userspace/.cargo/config.toml` sets only `-no-pie` /
static / large code-model, and `kernel/build.rs` stages ELFs from a
plain `cargo build --target x86_64-unknown-none --bins`. A plain
build therefore links every program at the same default layout
(entry ~0x201160 on the RK-007 ELFs), so the second program to load
collides with the first and every program is loader-refused.
`link-base.ld` names per-program bases in its comment (hello /
sleeper / crasher) but nothing ever substituted BASE per program,
and the committed `link.ld` is a single-base artifact (crasher's
base) that the plain build never used either.

Fix: for each program in `kernel/build.rs`'s BINS list, generate a
link script from `link-base.ld` with BASE replaced by that program's
base, build that one bin with `cargo rustc` passing the generated
script as the link script, and verify the resulting ELF's entry
address equals its base. The entry check is the safety property:
if the link-arg handling ever changes (config rustflags, linker
choice), a bin linked at the wrong address FAILS HERE, loudly, and
is never silently staged as a good build.

Bases: hello / sleeper / crasher keep exactly the bases named in
`link-base.ld`'s comment; readkey takes the next slot in the same
0x10_0000_0000 spacing. All four sit far above the 0.11 kernel image
range (0x200000-0xbfba2c per the RK-007 diagnosis) and far from the
physmap, and no two share a page.

Usage (from the repo root):
    python3 os-build/userspace/build_userspace.py [--release] [bin ...]
Default builds all four BINS in order, dev profile. The generated
`link-<bin>.ld` files are working-tree artifacts: do not hand-edit
them (edit `link-base.ld`) and do not commit them. This script
changes no kernel code, no loader code, and does not touch
`syscalls.rs` (FROZEN) or the committed `link.ld` (left as-is,
stale, unused by this script).

Status: written on a VM with no cargo, so UNCOMPILED here. Milo
gate-1 must run this script and confirm the entry lines; Mac/Buffy
boot proof (gate pack L1-L5 in `os-build/ROWAN_TEST_PREP.md`) is
still owed after that. Merge is Pax's call.
"""

import struct
import subprocess
import sys
from pathlib import Path

# (program, link base) -- order matches kernel/build.rs BINS.
PROGRAMS = [
    ("hello", 0x600000000000),
    ("sleeper", 0x610000000000),
    ("crasher", 0x620000000000),
    ("readkey", 0x630000000000),
]

TARGET = "x86_64-unknown-none"


def main(argv):
    release = "--release" in argv
    wanted = [a for a in argv if not a.startswith("--")]
    profile = "release" if release else "debug"
    script_dir = Path(__file__).resolve().parent
    user_dir = script_dir / "user"
    template = user_dir / "link-base.ld"
    if not template.is_file():
        print(f"missing template: {template}", file=sys.stderr)
        return 2
    text = template.read_text()
    bases = [base for _, base in PROGRAMS]
    if len(set(bases)) != len(bases):
        print("duplicate link base in PROGRAMS table", file=sys.stderr)
        return 2
    selected = PROGRAMS
    if wanted:
        known = dict(PROGRAMS)
        for name in wanted:
            if name not in known:
                print(f"unknown bin: {name} (known: {sorted(known)})",
                      file=sys.stderr)
                return 2
        selected = [(name, known[name]) for name in wanted]
    for name, base in selected:
        # Substitute exactly the placement line, not the comment text:
        # ". = BASE;" must occur exactly once in the template.
        placed = text.replace(". = BASE;", f". = 0x{base:x};")
        count = text.count(". = BASE;")
        if count != 1:
            print(f"link-base.ld: expected 1 placement line, found {count}",
                  file=sys.stderr)
            return 2
        generated = user_dir / f"link-{name}.ld"
        generated.write_text(placed)
        cmd = ["cargo", "rustc", "--target", TARGET, "--bin", name]
        if release:
            cmd.append("--release")
        # rustc needs -C and its value as separate argv entries: one
        # combined "-C link-arg=..." string is parsed as a codegen
        # option " link-arg" (leading space) and fails (Milo gate-1 RED).
        cmd += ["--", "-C", f"link-arg=-T{generated}"]
        print(f"== {name}: base 0x{base:x}, link script {generated.name}")
        print(f"   {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=user_dir)
        if result.returncode != 0:
            print(f"cargo rustc failed for {name} (exit {result.returncode})",
                  file=sys.stderr)
            return result.returncode
        elf = (user_dir / "target" / TARGET / profile / name)
        entry, etype = read_elf_entry(elf)
        print(f"   entry 0x{entry:x} type {etype} (want base 0x{base:x})")
        if entry != base:
            print(f"FAIL: {name} entry 0x{entry:x} != base 0x{base:x} -- "
                  "link script was not applied; do not stage this ELF",
                  file=sys.stderr)
            return 1
        print(f"   {name} OK: entry == base 0x{base:x}")
    print("all selected programs linked at distinct bases, entries verified")
    return 0


def read_elf_entry(path):
    """Return (e_entry, e_type) of a 64-bit little-endian ELF."""
    data = Path(path).read_bytes()[:64]
    if len(data) < 64 or data[:4] != b"\x7fELF":
        raise ValueError(f"not an ELF file: {path}")
    if data[4] != 2 or data[5] != 1:
        raise ValueError(f"not a 64-bit little-endian ELF: {path}")
    etype = struct.unpack_from("<H", data, 16)[0]
    entry = struct.unpack_from("<Q", data, 24)[0]
    return entry, etype


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
