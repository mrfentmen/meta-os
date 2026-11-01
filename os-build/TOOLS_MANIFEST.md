# Tools manifest (OS-133..OS-141, OS-146..OS-150)

Living file (OS-150, update rule at the bottom). Categories first
(OS-133). Every tool: name, version source, license, size (OS-141).

## Languages and runtimes (OS-134)

- Rust toolchain (rustup stable + x86_64-unknown-none + llvm-tools
  + rust-src): `rustup show` / MIT+Apache-2.0.
- Goose toolchain: `goose-mcp` toolchain_status + local install
  notes in os-build/research/goose.md (OS-153/154 fill versions).
- Lobster interpreter: `lobster-mcp` toolchain_status + local
  install notes (OS-167/168 fill versions).
- Python 3 (system + pip): `python3 --version` / PSF.
- Node 22 + npm: `node --version` / MIT.

## Build tools (OS-135)

- cargo bootimage 0.10.5: `cargo bootimage --version` / MIT.
- QEMU 11.1.3 (`brew install qemu`): `qemu-system-x86_64
  --version` / GPL-2.0 (dev-carrier tool only, never ships in
  the product — red-list rule applies to use, not just code).
- git, make/cmake (Xcode CLT): `git --version` / GPL-2.0 + MIT.
- llvm tools (via rustup component): bundled with Rust.

## Networking (OS-136)

- curl, openssh (macOS built-in): `curl --version` / MIT-style.
- dig (bind, brew): `dig -v` / MPL-2.0.
- nmap class: NOT installed (rough edge: security tooling needs
  a stated install story, not a quiet absence).

## Disk and system (OS-137)

- hdiutil/diskutil (macOS built-in): system tools.
- mtools/mformat family: needed only for the Debian image route
  (not on this Mac — image work runs on Linux hosts).

## Media (OS-138)

- ffmpeg (brew): `ffmpeg -version` / GPL-2.0+ (carrier tool).
- sips (macOS built-in, image conversion): system.

## Text and data (OS-139)

- jq (brew): `jq --version` / MIT.
- ripgrep (brew): `rg --version` / MIT+Unlicense.
- sqlite3 (macOS built-in): public domain.
- hexdump/xxd (system): BSD.

## Agent tooling (OS-140)

- MCP servers wired in Section M (WIRING.md): goose-mcp 1.1.0,
  lobster-mcp 1.1.0, filesystem/git MCPs + smoke results.
- Crew bus tools + records tools: as Section M wires them.

## Sizes (OS-146, this Mac, 2026-11-01)

Recorded by the verify run (see report): QEMU ~729 MB installed,
Rust toolchain ~1 GB, Node/Python system. Full table in the
Section J report block.

## Trim pass (OS-147)

- CUT from any minimal story: nmap (absent, stays absent until
  a lane needs it with a written reason), chromium-class browsers
  (demo needs only, never build needs), duplicate image viewers
  (sips covers conversion, no new tools).
- KEEP: everything above — each has a build step that fails
  without it, which is the keep criterion.

## Kernel-native carry (OS-148, second view)

Tools the kernel image itself will eventually carry natively
(post-K6): NONE yet — the kernel prints, switches, maps, and
loads; it carries no tools. First candidates when userspace
grows: a memory-map printer (mem summary already is one) and
the structured status record (OS-208). Everything else stays
outside the image by design (small kernel, tools in userspace).

## Prerequisites (OS-149, fresh machine order)

1. Xcode command line tools (git, make, compilers).
2. Homebrew.
3. `install-tools.sh` (this manifest, Mac side).
4. rustup toolchain + targets + components (OS-002 list).
5. `cargo install bootimage`.
6. Goose + Lobster toolchains (Sections K/L record exact steps).
7. MCP wiring (Section M).

## Update rule (OS-150, read before adding a tool)

A new tool needs: a named build step that fails without it, a
license line, a size line, and a smoke command in Section M. No
drive-by installs. The manifest edits ride with the commit that
first needs the tool.
