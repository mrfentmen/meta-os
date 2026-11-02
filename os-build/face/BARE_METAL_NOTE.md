# Bare-metal face: what the kernel would need

Scope: `os-build/face/shell.html` + `login.html` run on a Debian carrier in QEMU today.
The bare-metal line (`kernel/`, K1–K6) boots to a VGA text console with a cooperative
scheduler, 6 syscalls, and 3 baked-in userspace programs. This note lists the gaps honestly.
Grounding: every claim cites a file that exists in this tree. Anything not verified is marked OPEN.

## 1. Pixel framebuffer (the hard blocker)

Today there is no pixel surface. `kernel/src/main.rs` maps only the VGA text buffer
(`physical_memory_offset + VGA_PHYS_ADDR`, `kernel/src/vga.rs`: 80x25 cells at phys
`0xB8000`, hardware ROM font, 16 colors). `kernel/Cargo.toml` pins
`bootloader = { version = "0.9", features = ["map_physical_memory"] }`, and
`os-build/research/framebuffer.md` records `grep -c framebuffer == 0` on the 0.9.35
`BootInfo`: no framebuffer field, no stride/format/resolution. A pixel face needs: a newer
bootloader (0.10+-style GOP/VBE handover) or our own VBE/GOP mode set; pixel-format/stride
handling; and a double-buffered present path (offscreen compose, then blit/vsync) instead of
the current direct `write_volatile` cell writes. `kernel/src/framebuffer.rs` already drafts
an unwired pixel console + Terminus 8x16 table — code only, no pixel buffer to drive until
the bootloader handover lands. OPEN: exact bootloader version and mode-set path.

## 2. Input: keyboard exists, mouse does not

Keyboard works: `kernel/src/interrupts.rs` reads real PS/2 scancodes from port `0x60`
into a 64-byte ring (`keyboard_read()`); `kernel/src/sched.rs` decodes set-1 scancodes in
the console task, and syscall 5 (`kernel/src/user.rs`, vector 128 via `kernel/src/traps.rs`)
hands raw scancodes to userspace. A mouse needs what does not exist: a PS/2 mouse driver
(0x60/0x64 aux enable, packet decode) plus an IRQ12 handler — `traps.rs` wires only
`[0,1,3,6,8,10,11,12,13,14,32,33]` + 128 (PIT = 32, keyboard = 33); vector 44 (IRQ12)
is unwired and there is no pointer-event path at all. Keyboard-first is viable; mouse can wait.

## 3. Userspace compositor: thin base, missing shared memory/IPC

Per `KERNEL_SPEC.md` (frozen table) and `kernel/src/user.rs`, exactly six syscalls exist:
0 exit, 1 write (mapped-range-checked, one page per call), 2 sleep (tick count),
3 pid (`current_id`), 4 yield, 5 read_key (non-blocking raw scancode or `u64::MAX`).
`kernel/src/sched.rs` is cooperative round-robin (timer IRQ counts ticks, never preempts;
`MAX_TASKS = 8`, 16 KiB stacks). A compositor is missing: shared memory or framebuffer
`mmap` (no way to map the pixel buffer into ring 3 today; `user.rs` maps only ELF LOADs +
8 KiB stacks at `USTACK_BASE`), real timers/deadlines (only tick-count sleep), and any IPC
(no pipes, sockets, or message passing — `write` prints to the console, nothing routes
between tasks). Also missing: preemption/priority and allocation accounting for a frame loop.

## 4. Storage + network: the face backends have nowhere to live

The face's services (`os-build/face/launcher.py`, `ptyd.py`, `facts.py` style backends) assume
a POSIX OS: processes, a filesystem, PTYs, and localhost TCP. The kernel has none of it:
no block/virtio driver, no filesystem, no NIC driver, no TCP/IP stack. Userspace today is
three static ELFs baked in with `include_bytes!` (`HELLO_ELF`/`SLEEPER_ELF`/`CRASHER_ELF`
in `user.rs`) loaded by `load_elf` — there is no `exec`, no dynamic loading, no storage
beyond what the bootloader maps (`kernel/src/mem.rs` + `kernel/src/memory.rs`: frame
allocator, mapper over the physmap, 512 KiB heap). Persistent face state (settings,
wallpapers, trash) and any multi-process backend are therefore OPEN work: virtio-blk + a
minimal filesystem first, virtio-net + a minimal TCP/IP stack much later.

## 5. Rough ordering: what comes first, what can wait

1. Framebuffer handover (newer bootloader or VBE/GOP mode set) + wire `framebuffer.rs` —
   nothing graphical happens before this. 2. Map the framebuffer into userspace (or a
   `mmap`/shared-memory syscall) so a compositor can draw without kernel mediation per
   pixel. 3. PS/2 mouse driver + IRQ12 vector + pointer events (keyboard carries input
   until then). 4. IPC primitives + a spawn/exec path past the 3 baked-in ELFs so face
   backends can become real services. 5. Storage (virtio-blk + minimal fs) for persistent
   state. 6. Network (virtio-net + TCP/IP) last — the face works offline long before it
   needs it. Memory management (`memory.rs`/`mem.rs`) and the tick source already exist,
   so steps 1–3 are the true critical path.
