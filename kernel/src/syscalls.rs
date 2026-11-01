//! Meta OS kernel, milestone K6: system calls + first userspace process shape (UNWIRED).
//!
//! Status: **WRITTEN, NOT WIRED INTO `main.rs`, NOT A KERNEL-CRATE
//! COMPILE, NOT A BOOT VERDICT, NOT A SYSCALL THAT HAS EVER RUN.**
//! This file is code, not a running syscall layer, and no claim is
//! made that any userspace program has ever executed on it or that
//! any trap has ever been taken. Per KERNEL_SPEC.md rule 2, it counts
//! only when it builds on the boss's Mac and a QEMU boot shows its
//! behavior. Per KERNEL_SPEC.md milestones, K6 is "system calls, first
//! userspace program, the Goose services layer gets its first
//! process". Per OS_BUILD_TASKS.md R5 / RW-L0-01, it is wired into
//! `main.rs` only onto the proven tree, one module per commit, after
//! a K1 boot log exists and `kernel/Cargo.lock` is committed (Q1).
//! Until then it is code, not a running kernel.
//!
//! Authority: boss layer order 2026-11-01 ~08:18, relayed by Pax on
//! room 1 and written into `os-build/LAYERS.md` +
//! `ROWAN_LAYER0_TASKS.md` on main: Rowan owns Layers 1-3 (boot,
//! kernel core, drivers; renumbered to seven layers on the boss's
//! word 2026-11-01 ~09:02, file names and task IDs kept as stable
//! identifiers). K6 has no separate RW-L0 task ID in the live docs
//! read this run (`ROWAN_LAYER0_TASKS.md` lists RW-L0-01 wiring,
//! RW-L0-02 K4, RW-L0-03 K5, RW-L0-04 questions), so none is claimed
//! here. The kernel-side shape this module implements is Pax's
//! `os-build/layer1/K6_SERVICE_SHAPE.md` (Layer 4 shape, DESIGNED):
//! six syscalls, no service-to-service IPC, failure final, first
//! service `bootlog`. This module is drafted unwired in the R2/R3/K4/
//! K5 pattern, started after Milo gate-1 GREEN on K5 (`rowan/kernel`
//! @ `4c48fab`, room 1 2026-11-01 ~09:28) — the same queue rule K5
//! followed after K4's gate. `kernel/Cargo.lock` is STILL absent on
//! main (checked this run: absent from the live main tree at
//! `83e6c3a`), there is still no K1 boot log and no `os-build`
//! branch, so Q1 is still unanswered and Q12 below is still open.
//!
//! What this module does about that, honestly, following the
//! R2/R3/K4/K5 precedent:
//!
//! - It does NOT import any bootloader type, any `x86_64` crate
//!   type, or any K2/K3/K4/K5 type, and it does NOT depend on any
//!   external crate. Every structure below is local and uses `core`
//!   only, no `alloc`, so it cannot drag a dependency question
//!   into R5.
//! - It does NOT assert a syscall transport. The shape document
//!   leaves the transport OPEN (interrupt vector vs the `syscall`
//!   instruction) as the handler-ABI question already open as Q9;
//!   this module asserts no vector number, no `STAR`/`LSTAR` value,
//!   no segment selector, and no privilege level. The trap entry
//!   that calls `dispatch` is R5's job, under Q12.
//! - It does NOT dereference a user address. A real syscall passes
//!   a buffer address; this module never touches that address. The
//!   R5 trap entry copies the user bytes first (copy rules are
//!   Q12's business) and hands `dispatch` the copied slice. A
//!   `bytes` slice here is already kernel-owned. No address in
//!   this file is ever read through, so none can be a wrong
//!   userspace pointer here; the copy is where that correctness
//!   lives, and the copy is R5's job.
//! - It does NOT assert a binary format, a load address, or a
//!   BootInfo pointer convention. The shape document leaves all
//!   three OPEN (Q1/Q5). `UserTaskStart` and `BootInfoBlock` carry
//!   plain addresses and validated geometry; the R5 adapter fills
//!   them from the resolved build, under Q12.
//! - It does NOT route between services. The shape document says
//!   no service-to-service IPC at K6, and nothing in this module
//!   addresses one service from another: `dispatch` has no service
//!   target, only the calling service's own trap.
//! - It does NOT restart a failed service. The shape document says
//!   failure is final at K6. `dispatch` reports `Exit` and `Fault`
//!   outcomes; `record_end` turns them into the final record the
//!   R5 wiring logs to serial before ending the K5 task. No
//!   restart policy exists in this file, and none is implied.
//!
//! Check note (exact words): this module was checked on this VM with
//! standalone `rustc 1.99.1` (`rustc --edition 2021 --crate-type
//! lib`, host target, warnings denied) plus a host test harness in
//! `/tmp` (not shipped) exercising the syscall number table, unknown
//! numbers, oversize writes, short-write counts, read-key bytes and
//! the empty-ring sentinel, tick passthrough, yield, exit codes,
//! end-record mapping, start-block validation, and framebuffer
//! geometry validation below. That is standalone-clean plus
//! host-exercised logic. It is NOT a kernel crate compile (no
//! `no_std` target, no bootloader crate linked), NOT a trap that has
//! been taken, and NOT a boot verdict. The Mac build + QEMU log
//! remain the proof.
//!
//! Wiring contract (for the R5 commit): `main.rs` gains
//! `mod syscalls;` and a trap entry (vector or `syscall`
//! instruction, per the Q9/Q12 answer) that (a) copies the user's
//! write buffer into kernel memory, (b) calls `dispatch` with the
//! syscall number, the exit code or other scalar argument, and the
//! copied bytes, (c) on `Outcome::Return` resumes the service with
//! the value, (d) on `Outcome::Yield` runs the K5 scheduler before
//! resuming any service, (e) on `Outcome::Exit` or
//! `Outcome::Fault` calls `record_end`, logs the record to serial
//! (the K1 serial path), and ends the K5 task. R5 also fills a
//! `BootInfoBlock` from the K2 framebuffer geometry, the K4 memory
//! summary, and the K3 tick rate, and builds each service's
//! `UserTaskStart` from the loaded binary's entry and stack. This
//! file needs no other crate item.
//!
//! No mocks (KERNEL_SPEC.md rule 6): every function below moves
//! real dispatch or validation state or refuses. An unknown syscall
//! number faults the service, never a faked success. An oversize
//! write faults, never a silent truncation. A short device write
//! reports its real count. No task, byte, or tick is invented.

// ---------------------------------------------------------------------------
// Syscall numbers (DRAFT, per os-build/layer1/K6_SERVICE_SHAPE.md item 3)
// ---------------------------------------------------------------------------

/// Service exit. Argument: the exit code. No bytes are read.
pub const SYS_EXIT: u64 = 0;
/// Write bytes to the serial port. Bytes: the copied user buffer.
pub const SYS_WRITE_SERIAL: u64 = 1;
/// Write bytes to the console. Bytes: the copied user buffer.
pub const SYS_WRITE_CONSOLE: u64 = 2;
/// Read one key byte from the K3 PS/2 ring buffer. No bytes are read.
pub const SYS_READ_KEY: u64 = 3;
/// Read the K3 tick counter. No bytes are read.
pub const SYS_TICKS: u64 = 4;
/// Yield the processor to the K5 scheduler. No bytes are read.
pub const SYS_YIELD: u64 = 5;
/// The syscall surface v0 has six calls, no more (shape item 3).
pub const NUM_SYSCALLS: u64 = 6;

/// Maximum bytes accepted in one write call: one K4 page (4096).
/// A longer write faults the service (see `FaultReason`), it is
/// never silently truncated. Chunking longer output into several
/// calls is the service's job at K6.
pub const MAX_WRITE_BYTES: usize = 4096;

/// `read_key` return value when the K3 ring buffer is empty. A real
/// key byte is 0..=255, so this sentinel is unambiguous. The call
/// is non-blocking at K6: an empty ring is a value, not a wait.
pub const NO_KEY: u64 = u64::MAX;

// ---------------------------------------------------------------------------
// Kernel services: the device side, supplied by the R5 adapter
// ---------------------------------------------------------------------------

/// The device operations a syscall needs. The R5 adapter implements
/// this over the real K2 console, the K1 serial port, the K3 ring
/// buffer, and the K3 tick counter. The host harness implements it
/// over buffers. A write returns the number of bytes actually
/// written, so a short write is reported honestly to the service
/// instead of claimed complete.
pub trait KernelServices {
    /// Write bytes to the serial port. Returns bytes written.
    fn write_serial(&mut self, bytes: &[u8]) -> usize;
    /// Write bytes to the console. Returns bytes written.
    fn write_console(&mut self, bytes: &[u8]) -> usize;
    /// Read one key byte, or `None` when the ring buffer is empty.
    fn read_key(&mut self) -> Option<u8>;
    /// Current tick count (K3 `ticks()`).
    fn ticks(&self) -> u64;
}

/// Why a service ended in fault. The fault is final (shape item 5):
/// the caller logs it via `record_end` and ends the task.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum FaultReason {
    /// The syscall number is not one of the six v0 calls.
    UnknownSyscall(u64),
    /// A write call carried more than `MAX_WRITE_BYTES` bytes.
    WriteTooLong(usize),
}

/// What the caller must do after a syscall. `Return` resumes the
/// service with the value. `Yield` means: do not resume this service
/// yet, run the K5 scheduler first. `Exit` and `Fault` end the
/// service; the caller records and logs them before ending the task.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Outcome {
    /// Resume the service with this value (tick count, key byte,
    /// `NO_KEY`, or bytes actually written).
    Return(u64),
    /// Reschedule before resuming any service.
    Yield,
    /// The service exited with this code.
    Exit {
        /// Exit code, taken from the syscall argument.
        code: u64,
    },
    /// The service faulted. Failure is final at K6.
    Fault {
        /// Why it faulted.
        reason: FaultReason,
    },
}

/// Route one syscall. `number` is the syscall number, `arg` is the
/// scalar argument (the exit code for `SYS_EXIT`; ignored by every
/// other call), `bytes` is the kernel-owned copy of the user's
/// buffer (meaningful only for the two write calls; ignored by the
/// others), and `services` is the R5 device adapter. This function
/// never touches a user address, never blocks, and never invents a
/// value: unknown numbers and oversize writes fault.
pub fn dispatch<S: KernelServices>(
    number: u64,
    arg: u64,
    bytes: &[u8],
    services: &mut S,
) -> Outcome {
    match number {
        SYS_EXIT => Outcome::Exit { code: arg },
        SYS_WRITE_SERIAL => {
            if bytes.len() > MAX_WRITE_BYTES {
                return Outcome::Fault {
                    reason: FaultReason::WriteTooLong(bytes.len()),
                };
            }
            Outcome::Return(services.write_serial(bytes) as u64)
        }
        SYS_WRITE_CONSOLE => {
            if bytes.len() > MAX_WRITE_BYTES {
                return Outcome::Fault {
                    reason: FaultReason::WriteTooLong(bytes.len()),
                };
            }
            Outcome::Return(services.write_console(bytes) as u64)
        }
        SYS_READ_KEY => match services.read_key() {
            Some(byte) => Outcome::Return(byte as u64),
            None => Outcome::Return(NO_KEY),
        },
        SYS_TICKS => Outcome::Return(services.ticks()),
        SYS_YIELD => Outcome::Yield,
        other => Outcome::Fault {
            reason: FaultReason::UnknownSyscall(other),
        },
    }
}

// ---------------------------------------------------------------------------
// Service end: the final record (shape item 5)
// ---------------------------------------------------------------------------

/// How a service ended, for the serial log. `Exited` carries the
/// service's own exit code; `Faulted` carries the fault reason.
/// There is no restart: this record is the last word on the service.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum EndState {
    /// The service called `SYS_EXIT` with this code.
    Exited(u64),
    /// The service faulted for this reason.
    Faulted(FaultReason),
}

/// The record the R5 wiring logs to serial when a service ends:
/// the service's name (bytes, as the loader recorded it) and how it
/// ended. Logging itself is R5's job — this module touches no port.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct ServiceRecord<'a> {
    /// Service name bytes (not necessarily UTF-8; logged as bytes).
    pub name: &'a [u8],
    /// How the service ended.
    pub state: EndState,
}

/// Turn a syscall outcome into the final record, if it ends the
/// service. `Return` and `Yield` keep the service alive, so they
/// produce no record. The caller logs the returned record to serial
/// and then ends the K5 task; it never resumes a recorded service.
pub fn record_end<'a>(name: &'a [u8], outcome: &Outcome) -> Option<ServiceRecord<'a>> {
    match *outcome {
        Outcome::Exit { code } => Some(ServiceRecord {
            name,
            state: EndState::Exited(code),
        }),
        Outcome::Fault { reason } => Some(ServiceRecord {
            name,
            state: EndState::Faulted(reason),
        }),
        Outcome::Return(_) | Outcome::Yield => None,
    }
}

// ---------------------------------------------------------------------------
// Start block: what the kernel hands a service at start (shape item 2)
// ---------------------------------------------------------------------------

/// Pixel channel order, mirroring the K2 `PixelFormat` variants
/// (`Rgb`, `Bgr`, `Gray`) without importing them. The R5 adapter
/// translates the K2 value into this one field by field.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum PixelFormatMirror {
    /// Red, green, blue in memory order (plus an opaque pad byte at 4 bpp).
    Rgb,
    /// Blue, green, red in memory order (plus an opaque pad byte at 4 bpp).
    Bgr,
    /// One byte per pixel, luminance only.
    Gray,
}

/// Framebuffer geometry for the start block, mirroring the K2
/// `FramebufferInfo` fields without importing them: `stride` is in
/// pixels, `bytes_per_pixel` is the format width, `byte_len` is the
/// buffer length in bytes.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct BootFramebuffer {
    /// Width in pixels.
    pub width: usize,
    /// Height in pixels.
    pub height: usize,
    /// Stride in pixels (not bytes).
    pub stride: usize,
    /// Bytes per pixel: 1 for gray, 3 or 4 for RGB/BGR.
    pub bytes_per_pixel: usize,
    /// Channel order.
    pub format: PixelFormatMirror,
    /// Buffer length in bytes.
    pub byte_len: usize,
}

/// Why a start block (or its framebuffer) failed validation.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum BootInfoError {
    /// Width is zero, height is zero, or stride is below width.
    BadFramebufferGeometry,
    /// The (format, bytes-per-pixel) pair is not one K2 supports.
    BadFramebufferFormat,
    /// `height * stride * bytes_per_pixel` overflowed, or the
    /// buffer is shorter than the geometry requires.
    FramebufferOverflow,
    /// The tick rate is zero, so no tick count converts to time.
    ZeroTickRate,
    /// A boot milestone carries empty text; the bootlog service
    /// would print nothing for it.
    EmptyMilestoneText,
}

impl BootFramebuffer {
    /// The five (format, bytes-per-pixel) pairs K2's console
    /// supports: `(Gray, 1)`, `(Rgb, 3)`, `(Bgr, 3)`, `(Rgb, 4)`,
    /// `(Bgr, 4)`. Anything else is a geometry the console cannot
    /// draw, so the start block refuses it here rather than letting
    /// a service start against an undrawable screen.
    pub fn is_valid_combo(&self) -> bool {
        matches!(
            (self.format, self.bytes_per_pixel),
            (PixelFormatMirror::Gray, 1)
                | (PixelFormatMirror::Rgb, 3)
                | (PixelFormatMirror::Bgr, 3)
                | (PixelFormatMirror::Rgb, 4)
                | (PixelFormatMirror::Bgr, 4)
        )
    }

    /// Validate the geometry: nonzero dimensions, stride at least
    /// the width, a supported format pair, and a buffer long enough
    /// for the whole frame, with checked arithmetic throughout.
    pub fn validate(&self) -> Result<(), BootInfoError> {
        if self.width == 0 || self.height == 0 || self.stride < self.width {
            return Err(BootInfoError::BadFramebufferGeometry);
        }
        if !self.is_valid_combo() {
            return Err(BootInfoError::BadFramebufferFormat);
        }
        let row_bytes = self
            .stride
            .checked_mul(self.bytes_per_pixel)
            .ok_or(BootInfoError::FramebufferOverflow)?;
        let needed = row_bytes
            .checked_mul(self.height)
            .ok_or(BootInfoError::FramebufferOverflow)?;
        if self.byte_len < needed {
            return Err(BootInfoError::FramebufferOverflow);
        }
        Ok(())
    }
}

/// One boot milestone for the first service to print: an id and
/// its text. The bootlog service (shape item 6) prints these to
/// serial and console, then exits. The list itself is built by the
/// R5 wiring from the boot path; this module only carries it.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct BootMilestone<'a> {
    /// Milestone id (K1..K6 numbering, or a later milestone's id).
    pub id: u32,
    /// Milestone text bytes (not necessarily UTF-8).
    pub text: &'a [u8],
}

/// The block the kernel hands a service at start (shape item 2):
/// framebuffer geometry in the K2 module's local shape, a
/// memory-map summary, the PIT tick rate from the K3 module, and
/// the boot milestones. The register or memory location that
/// carries the pointer to this block is NOT stated here: that
/// convention is set at R5/K6 wiring time (shape item 2, OPEN),
/// and Q12 asks for it.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct BootInfoBlock<'a> {
    /// Framebuffer geometry, K2 shape mirrored.
    pub framebuffer: BootFramebuffer,
    /// Usable memory in bytes, summarized from the K4 memory map.
    /// Carried, not validated here: the map translation is Q10's
    /// business, and this module must not second-guess it.
    pub usable_memory_bytes: u64,
    /// PIT tick rate in Hz, as programmed by the K3 module. Must be
    /// nonzero so a tick count converts to time.
    pub tick_rate_hz: u32,
    /// Boot milestones for the bootlog service to print.
    pub milestones: &'a [BootMilestone<'a>],
}

impl<'a> BootInfoBlock<'a> {
    /// Validate the start block: the framebuffer geometry, a
    /// nonzero tick rate, and nonempty milestone text throughout.
    /// The usable-memory figure is carried, not checked (see above).
    pub fn validate(&self) -> Result<(), BootInfoError> {
        self.framebuffer.validate()?;
        if self.tick_rate_hz == 0 {
            return Err(BootInfoError::ZeroTickRate);
        }
        for milestone in self.milestones {
            if milestone.text.is_empty() {
                return Err(BootInfoError::EmptyMilestoneText);
            }
        }
        Ok(())
    }
}

// ---------------------------------------------------------------------------
// Userspace task start: the loaded service as a K5 task
// ---------------------------------------------------------------------------

/// Why a userspace task start was refused.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum StartError {
    /// The entry address is zero: there is nowhere to enter.
    ZeroEntry,
    /// The stack top is zero: there is no stack.
    ZeroStackTop,
    /// The stack top is not 16-byte aligned (the K5 entry
    /// alignment rule, enforced by `Context::initial`).
    MisalignedStackTop,
    /// The BootInfo block address is zero: the service would
    /// start with no start block.
    ZeroBootInfo,
}

/// A service loaded as a K5 task: its task id, entry address,
/// stack top, and BootInfo block address, all as plain `u64`
/// boundary values in K4/K5 units. Page mapping of the entry and
/// stack (K4's `Mapper`), the privilege transition into userspace,
/// and the binary format that produced the entry address are all
/// R5/Q12 business — none is asserted here. In particular this
/// struct carries no privilege level, no segment selector, and no
/// kernel-stack address: a userspace entry without those answers
/// would be a guess, and this module does not guess.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct UserTaskStart {
    /// Task id, in the K5 `TaskId` units (a raw `u64`).
    pub task_id: u64,
    /// Entry address of the loaded service binary.
    pub entry: u64,
    /// Top of the service's stack (grows down from here).
    pub stack_top: u64,
    /// Address of the service's `BootInfoBlock`.
    pub boot_info_addr: u64,
}

impl UserTaskStart {
    /// Validate the start: nonzero entry, nonzero 16-byte-aligned
    /// stack top, nonzero BootInfo address. Mapping, privilege,
    /// and binary-format correctness are the R5 adapter's checks,
    /// not this one's.
    pub fn validate(&self) -> Result<(), StartError> {
        if self.entry == 0 {
            return Err(StartError::ZeroEntry);
        }
        if self.stack_top == 0 {
            return Err(StartError::ZeroStackTop);
        }
        if self.stack_top % 16 != 0 {
            return Err(StartError::MisalignedStackTop);
        }
        if self.boot_info_addr == 0 {
            return Err(StartError::ZeroBootInfo);
        }
        Ok(())
    }
}
