# Tools manifest research — five candidates per Section J category

Lane: Buffy, research and tools. Task B1. Written 2026-11-01.

Ten categories, not nine: OS-133 names nine (languages, compilers, editors,
networking, disks, media, security research, agent tooling, debugging) and
OS-139 adds text and data. All ten are here.
Status: RESEARCH. Nothing here is installed, compiled or run. No claim of a
working toolset is made by this file.

This is the candidate list behind `os-build/TOOLS_MANIFEST.md` (OpenCode's
Section J, OS-133..OS-152). It does not replace that manifest and it does not
have the same job: the manifest records what we actually install, this file
records what we chose it from and why, with the license position of each
candidate stated up front so the license gate (Section P) is not a surprise at
install time.

Deliberately absent: size and version numbers. Sizes get measured on the real
image at OS-143/OS-146, versions get pinned from the install log at OS-144.
A guessed number in a manifest is a lie with a shelf life, so every row names
its version source instead and the number is filled in by the run that
installs it.

## The license gate, in one paragraph

Our kernel is ours. Nothing GPL ever lands in `kernel/`, `services/` or
`lobster/`, and no GPL source gets copied, transcribed or paraphrased into
them (KERNEL_SPEC.md rule 1, Section P). But a development carrier is not the
product: Debian's own userland is GPL and we still run it to build. So the
question for a candidate is not "is it GPL", it is "does it stay a separate
program on the carrier, or does it end up inside the product". That is what
the Gate column answers.

| Gate | Meaning | What it may be used for |
|---|---|---|
| **GREEN** | Permissive (MIT, Apache-2.0, BSD, 0BSD, public domain, PSF). | Anything: carrier, image, linked, embedded, copied with notice. |
| **AMBER** | Copyleft or restricted (GPL, LGPL, MPL, custom). | Separate installed program only. Never linked into our code, never copied from, never vendored. LGPL additionally: dynamic link or separate process only. |
| **RED** | License unfit for redistribution in our product, or carrying a field-of-use restriction. | Local development only, or find a replacement. Never shipped on the image. |

A RED or AMBER line on a candidate is not a reason to skip the tool. `git`,
`qemu`, `gcc` and `make` are all AMBER and the build does not happen without
them. It is a reason to keep them where they belong and to know it before
somebody links them.

## 1. Languages and runtimes

Section J (OS-134). The three languages of the stack plus the two the existing
programs are written in. These five are not optional, they are the toolchain.

| Tool | Source | License | Gate | Why this slot |
|---|---|---|---|---|
| Rust toolchain + `rustup` | rustup.rs, channel `stable`; target `x86_64-unknown-none` added per OS-002 | MIT OR Apache-2.0 | GREEN | Layer 0. The kernel does not build without it, and `build-std` needs the rust-src component. |
| Goose | github.com/aardappel/goose, releases page (prebuilt, see 3 below) | Apache-2.0 | GREEN | Layer 1. One binary is compiler, runner, build tool, package fetcher, formatter and LSP. |
| Lobster | github.com/aardappel/lobster, prebuilt CI artifacts or build from source | Apache-2.0 | GREEN | Layer 2. Interpreter plus standard library, game oriented, no REPL. |
| Python 3 | apt `python3` (carrier: Debian 12 ships 3.11) | PSF-2.0 | GREEN | The existing programs' test suites (the 1906 case suite, queue suite, custos suite) run on it. Not the OS, a build dependency. |
| Node.js | nodejs.org LTS tarball, or apt `nodejs` | MIT | GREEN | The Node test suite (1933 cases) and the JS programs. Version must match `package.json` `engines` at install time, read it there, do not pin from memory. |

Note on Rust: `rustup` downloads a *toolchain* whose license is per component
(mostly MIT/Apache-2.0, some LLVM components carry the LLVM exception). The
embedded `core`/`alloc` sources we compile with `build-std` are Apache-2.0/MIT
and ship with the toolchain, which is what makes a `no_std` Rust kernel
licensable at all. If anyone ever proposes a `gcc`-built kernel or a
`libgcc`-style runtime shim, stop: that is the GPL line.

## 2. Compilers and build tools

Section J (OS-135), which also names git and the QEMU set. Both Goose and
Lobster need a C/C++ compiler and CMake, so this category is load bearing for
the two upper layers, not just for the kernel.

| Tool | Source | License | Gate | Why this slot |
|---|---|---|---|---|
| clang + LLVM | apt `clang`, `llvm` (or llvm.org apt repo for a newer one) | Apache-2.0 WITH LLVM-exception | GREEN | Kernel cross target, and the `cc` that Goose's `goose build` prefers. Permissive, unlike gcc. |
| lld | apt `lld` | Apache-2.0 WITH LLVM-exception | GREEN | The linker that matches clang. `bootimage`/`bootloader` link through it cleanly. |
| CMake | apt `cmake` | BSD-3-Clause | GREEN | Both Goose (needs 3.27+) and Lobster are CMake projects. Not optional if we build either from source. |
| Ninja | apt `ninja-build` | Apache-2.0 | GREEN | Generator for the two builds above. Faster than make and no copyleft. |
| QEMU (`qemu-system-x86_64`) | apt `qemu-system-x86` | GPL-2.0 | AMBER | The proof standard requires QEMU boot logs (KERNEL_SPEC rule 3). It is a host tool, it never ships inside Meta OS, and that is exactly why it is allowed. |

Also required, past the five row cap, all AMBER, all separate programs on the
carrier: `git` (GPL-2.0, and the whole repo workflow), GNU `make` (GPL-3.0,
Lobster's docs build with it), `pkg-config` (GPL-2.0).

Rule that falls out of the table: our kernel links clang's runtime, never
gcc's. `libgcc` is GPL-3.0 with the runtime exception, and the exception is
narrower than it looks. `compiler-rt` from LLVM is the permissive answer and
is what `rustc` uses on this target anyway. Write that into the manifest so
nobody "fixes" a link error with `-lgcc`.

## 3. Editors

Section J (OS-133). An editor is where every lane spends its day, and the
choice has a tooling consequence: Goose ships a VS Code extension and an LSP,
so the editor with the best tooling is not a taste question.

| Tool | Source | License | Gate | Why this slot |
|---|---|---|---|---|
| Neovim | apt `neovim` or the appimage | Apache-2.0 | GREEN | Works over SSH on the crew VMs, no GUI, no telemetry. The safe default for a sandbox lane. |
| Helix | apt `helix` or prebuilt | MPL-2.0 | AMBER | File level copyleft. Fine as a separate editor, do not vendor its source into anything. Fast, LSP native. |
| Vim | apt `vim` | Vim license (GPL-compatible, charityware) | AMBER | Present anyway on almost every image. Note it is not GPL, so a Vim *plugin* is not automatically GPL-tainted, but do not copy Vim source anywhere. |
| VS Code OSS build, or VSCodium | github.com/microsoft/vscode build from source; or vscodium.com binaries | MIT source; **Microsoft's binary build is proprietary** with telemetry | GREEN (source) / AMBER (Microsoft binary) | The only editor here with Goose's own extension (`goose-language.vsix` ships inside the Goose release archive). Install the OSS build or VSCodium, not Microsoft's binary, or the "no proprietary toolchain" story has a hole in it. |
| Kakoune | apt `kakoune` | Unlicense | GREEN | Public domain. The escape hatch if a copyleft editor is ever objected to. |

## 4. Networking

Section J (OS-136). Diagnostic and transfer tools for the carrier. Nothing here
goes into the OS itself; our networking stack is the kernel's and the Goose
layer's problem, and it is not written yet.

| Tool | Source | License | Gate | Why this slot |
|---|---|---|---|---|
| curl | apt `curl` | curl (MIT-like, no advertising clause) | GREEN | Every install script we write uses it, including the QEMU image fetch. |
| OpenSSH client + `sshd` | apt `openssh-client`, `openssh-server` | OpenSSH license (BSD-style, permissive) | GREEN | Crew VM access. Permissive, which surprises people who assume BSD `ssh` is GPL. |
| BIND utilities (`dig`, `host`) | apt `bind9-dnsutils` | MPL-2.0 | AMBER | DNS debugging for the relay and Custos work. MPL is file level, and we only call the binary. |
| tcpdump + libpcap | apt `tcpdump` | BSD-3-Clause | GREEN | The only way to see what the bus actually sends. Permissive including libpcap. |
| nmap | apt `nmap` | **NPSL** (GPLv2-based with added restrictions, not OSI-approved) | **RED** | Kept for local lab use only. Fedora's legal team rejected NPSL as non-free for redistribution; we do not ship it on the image and we do not link it. If the security program ever needs a scanner it ships, use `masscan` (AGPL, also out) or write our own. This is the one RED in the manifest and it should stay visible. |

Past the cap, AMBER: `wget` (GPL-3.0), `iproute2` (GPL-2.0, and you cannot
diagnose a link without `ip`), `socat` (GPL-2.0).

## 5. Disk and system

Section J (OS-137). Carrier tools for making, checking and imaging disks. The
kernel's own filesystem driver is a later milestone and owes none of these
licenses anything, because none of this code goes in it.

| Tool | Source | License | Gate | Why this slot |
|---|---|---|---|---|
| util-linux (`lsblk`, `blkid`, `mount`, `fdisk`) | apt `util-linux` | GPL-2.0 (a few parts BSD) | AMBER | `lsblk` is how every boot proof starts. Separate program. |
| e2fsprogs (`mkfs.ext4`, `fsck`) | apt `e2fsprogs` | GPL-2.0 (libext2fs LGPL-2.0) | AMBER | Root filesystem for the image and for the throwaway copy in OS-143. |
| dosfstools (`mkfs.fat`) | apt `dosfstools` | GPL-3.0 | AMBER | The EFI system partition. Nothing else does this job, so the license is accepted and contained. |
| libarchive (`bsdtar`) | apt `libarchive-tools` | BSD-2-Clause | GREEN | Reads and writes tar, zip, 7z, iso in one tool, permissively. Preferred over `tar` (GPL-3.0) and `7z` for anything scripted. |
| zstd | apt `zstd` | BSD-3-Clause OR GPL-2.0 (dual) | GREEN | Take the BSD arm. Image compression, and the kernel's own tools will want it later. |

Past the cap: GNU `tar` (GPL-3.0, AMBER, but it is on every image already),
`xz` (0BSD, GREEN, verified 2026-11-01 on tukaani.org, so it is the cleanest
compressor we have), `testdisk`/`photorec` (GPL-2.0, AMBER, the recovery pair
worth having on a throwaway image), `parted` and `gdisk` (GPL, AMBER).

One trap recorded here because it cost nobody anything yet: `7z`'s license is
LGPL-2.1-plus with the unRAR restriction (no building a RAR archiver from it).
AMBER, and `bsdtar` covers the need, so 7-Zip does not need a slot.

## 6. Media

Section J (OS-138), and the film work needs them. The demo footage pipeline is
real work in this repo, so these are not vanity installs.

| Tool | Source | License | Gate | Why this slot |
|---|---|---|---|---|
| ffmpeg + ffprobe | apt `ffmpeg`, or built with `--disable-gpl` | LGPL-2.1-or-later **by default**; becomes GPL-2.0 if built with `--enable-gpl` | AMBER | The carrier build is LGPL and calls only its own binary, which is fine. **Check the build flags before shipping a build of it**: Debian's `ffmpeg` package is built with GPL components enabled, so a shipped image needs our own LGPL configure, or ffmpeg stays a carrier-only tool. |
| ImageMagick | apt `imagemagick` | ImageMagick License (near-identical to Apache-2.0, SPDX id `ImageMagick`) | GREEN | Frame extraction, thumbnails, the repo's own screenshots and banners. Verified 2026-11-01 on imagemagick.org/license and the SPDX entry. |
| GraphicsMagick | apt `graphicsmagick` | MIT-style | GREEN | The fork with the simpler license and a stable CLI. Use where ImageMagick's policy file is in the way. |
| libvips | apt `libvips-tools` | LGPL-2.1-or-later | AMBER | Fastest of the three for bulk resizing. Dynamic link only if we ever link it, otherwise just call `vips`. |
| OBS Studio | obsproject.com or apt | GPL-2.0 | AMBER | Fallback recorder. Note the project already chose **OpenScreen** (MIT, verified in commit `d04cb7e`) for the demo takes, so this is the backup, not the plan. |

## 7. Text and data

Section J (OS-139). The five that turn a shell into a query engine. All
permissive, which is why this category has no AMBER rows at all.

| Tool | Source | License | Gate | Why this slot |
|---|---|---|---|---|
| jq | apt `jq` | MIT | GREEN | Every record, pack file and MCP payload in this repo is JSON. |
| ripgrep | apt `ripgrep` | MIT OR Unlicense | GREEN | Faster than grep and permissive, unlike grep (GPL-3.0). Grep stays on the image anyway, but scripts prefer `rg`. |
| sqlite3 | apt `sqlite3` | Public domain | GREEN | The records store for OS-124's append-only log, and already used by the programs. Public domain is the cleanest license in the whole manifest. |
| fd | apt `fd-find` | MIT OR Apache-2.0 | GREEN | `find` is GPL-3.0 and hostile; `fd` is neither. |
| hexyl | apt `hexyl` or `cargo install hexyl` | MIT OR Apache-2.0 | GREEN | Readable hex dumps for the binary record format and kernel images. The old answer, `xxd`, ships with Vim and carries the Vim license, so `hexyl` keeps this category clean. |

## 8. Security research

Section J lists this category (OS-133). **The cybersecurity program is PARKED
by the boss's order, and this lane did not start it.** The rows below are an
inventory of tools that already exist and are already installed on most
images, nothing more. No design work, no scanning, no program.

| Tool | Source | License | Gate | Why this slot |
|---|---|---|---|---|
| OpenSSL CLI | apt `openssl` | Apache-2.0 | GREEN | Certificates and hashes. Note the 1.1.1 to 3.x license change: 3.x is Apache-2.0, which is why 3.x is the only version worth having. |
| age | apt `age` | BSD-3-Clause | GREEN | Modern file encryption with no keyring to manage. The clean choice for encrypting agent homes or backups. |
| GnuPG | apt `gnupg` | GPL-3.0 | AMBER | Needed to verify release signatures, including the Goose and Lobster archives. Separate program, never linked. |
| tshark | apt `tshark` | GPL-2.0 | AMBER | Wireshark without the GUI. The bus and relay are ours, so packet truth is sometimes the only truth. |
| hashcat | apt `hashcat` | MIT | GREEN | Permissive, but it is a GPU tool and a carrier image has no GPU. Listed, not installed. |

## 9. Agent tooling

Section J (OS-140). This is the category that makes the OS ours, and it is the
thinnest one in the world right now: two of these five rows are code we have
to write.

| Tool | Source | License | Gate | Why this slot |
|---|---|---|---|---|
| MCP filesystem server | `modelcontextprotocol/servers` (reference servers) | MIT | GREEN | The agent's hands on a directory. Reference implementation, small enough to audit. |
| MCP git server | same repo | MIT | GREEN | Agents committing their own work with a record of it. |
| MCP memory server | same repo | MIT | GREEN | Prototype only. OS-120 owns the real agent memory format; do not let this become it by accident. |
| The `rustdocs` MCP pattern | in-repo pattern, documented in `batches/B##.md` prose | ours | GREEN | Section M's OS-181..OS-192 own the wiring. **As of this writing no MCP config file exists in the repo at all** (no `.mcp.json`, no `.vscode/mcp.json`), so this is a pattern on paper, not a wired server. See `LANE_NOTES.md`. |
| Crew bus tools + records reader | `os/poll.py`, `os/send.py`, `os/store.py` etc. and their Rust ports B24..B26, plus the sqlite record store | ours | GREEN | The bus is the OS's own nervous system (Section I, OS-123). It is the one agent tool we already have working, in Python, with tests. |

For the record on the layer languages: **neither Goose nor Lobster has an MCP
server**, verified 2026-11-01. Goose ships an LSP (`goose lsp`) and a VS Code
extension instead, which is better than an MCP for coding and useless for
agents calling tools. Details and links in `ecosystem-watch.md`.

## 10. Debugging

Section J (OS-133). The kernel is the hard part, and this category is where a
kernel bug gets found. Today the honest answer for debugging *our* kernel is
QEMU's gdbstub: boot with `-s -S`, attach the debugger, step the kernel. There
is no in-kernel debugger and there will not be one before K4.

| Tool | Source | License | Gate | Why this slot |
|---|---|---|---|---|
| LLDB | apt `lldb` | Apache-2.0 WITH LLVM-exception | GREEN | The debugger that matches clang, talks to QEMU's gdbstub, and is permissive. This is the one Rowan should learn for the kernel. |
| GDB | apt `gdb` | GPL-3.0 | AMBER | Most kernel tutorials assume it, so it is the compatibility answer. Separate program. |
| strace | apt `strace` | LGPL-2.1-or-later | AMBER | Syscall truth for the carrier and for the services layer. Useless against our own kernel until K6 gives syscalls a meaning. |
| valgrind | apt `valgrind` | GPL-2.0 | AMBER | Memory errors in the C that Goose and Lobster generate. Runs the program, never links into ours. |
| perf | apt `linux-perf` | GPL-2.0 | AMBER | Only if a number is disputed. The kernel is not ours to profile until it exists. |

Past the cap: `rr` (record and replay, the best tool here for a nondeterministic
boot, but its license is a custom permissive one and **this lane did not verify
it**, so it is listed and not gated), `ltrace` (GPL-2.0).

## What this list implies for the manifest

1. Eight of the ten categories are GREEN-dominated. The copyleft load is
   concentrated in disk tools, build tools and one scanner, all of which are
   separate programs on the carrier.
2. The one RED is `nmap` (NPSL). It should be the only RED in
   `TOOLS_MANIFEST.md`, and OS-147's trim pass should have to argue for it.
3. The debugger story is settled by one decision: LLDB plus QEMU's gdbstub,
   with GDB only when a tutorial assumes it. Write that into the K2 notes
   before somebody adds print statements to the framebuffer code.
4. Three rows carry a shipping condition rather than a license problem:
   `ffmpeg` (needs an LGPL-only build before it ships), VS Code (ship the OSS
   build, not Microsoft's binary), and `sqlite3` (fine, but the *format* we put
   in it is a design decision, not a tool decision).
5. Nothing here is inside the kernel. When OS-148 marks what the KERNEL image
   eventually carries natively, the honest answer today is: none of it. A
   `no_std` kernel that has not reached K4 cannot host a userland tool, and the
   permissive ones we would want first (`zstd`, `sqlite`, `ripgrep`) are all
   programs, not libraries we can link into `no_std` without an allocator.
