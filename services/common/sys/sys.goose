// services/common/sys/sys.goose
//
// The kernel boundary for every Layer 4 service: six calls, declared once.
//
// Status: WRITTEN (not COMPILED). Forms verified via goose-mcp@1.1.0:
// `extern fn` with an optional `= "C symbol"` (spec#40, reference#106),
// `const u8[:]` slice parameters (spec#40), `u8[>..]&` caller-supplied output
// buffers (spec#40, samples/03_strings.goose), trailing-bool convention
// (samples/04_errors.goose), i32/i64/bool/u8 keywords (list_keywords).
//
// THE TRANSPORT IS OPEN (question Q9)
//
// Nothing in this file says HOW the call reaches the kernel. Interrupt gate,
// `syscall` instruction, a call into a shared page, a capability invocation --
// that is Layers 1-3's decision, and a service that assumed one of them would
// be broken by the other three. What this file fixes is the SHAPE the services
// code against, so 24 services can be written while the kernel decides.
//
// The consequence, stated plainly: these six declarations are a REQUEST to the
// kernel. If K6 lands with different names, different argument order, or a
// different return convention, this file changes and every service follows.

// ---------------------------------------------------------------------------
// The six calls
// ---------------------------------------------------------------------------
//
// C symbol names are given explicitly (= "...") so the Goose-side name and the
// kernel-side symbol can differ without either side renaming. The `sys_` prefix
// is deliberate: it keeps the generated C clear of any name the platform
// headers might already declare, and it makes a grep for kernel calls honest.

// End the calling process. No return; the supervisor records `code`.
extern fn sys_exit(code: i32) = "sys_exit";

// Write a read-only byte slice to the serial port. Returns the number of bytes
// written, or a negative error code. Negative is a real case: a dead or
// flow-stopped UART must be visible to the log service, not silently swallowed.
extern fn sys_write_serial(s: const u8[:]) -> i64 = "sys_write_serial";

// Write to the console (framebuffer) rather than the serial line. Separate from
// serial on purpose: the log must keep working when the display does not.
extern fn sys_write_console(s: const u8[:]) -> i64 = "sys_write_console";

// Read one key event into the caller's buffer.
//
// Contract as this layer needs it: `true` with bytes written means an event is
// in the buffer; `false` means no key is pending right now -- NOT an error and
// NOT end of input. The kernel must be able to tell those apart, because
// "nothing pressed" happens constantly and must cost nothing.
//
// OPEN, Q-B-L1-1: the six-call shape has no blocking wait. Services therefore
// poll with sys_yield. If the kernel can block instead, the console stops
// burning CPU the scheduler could use, and this comment is where that changes.
extern fn sys_read_key(out: u8[>..]&) -> bool = "sys_read_key";

// Monotonic tick count. Must never go backwards, must be cheap enough to poll
// in a sleep loop, and the rate is published in BootInfo -- never assumed here.
extern fn sys_ticks() -> i64 = "sys_ticks";

// Give the CPU back to the scheduler.
//
// This is the load-bearing call for the whole layer: every wait loop is
// `while not done { sys_yield(); }`. A yield that does not actually reschedule
// turns every service into a hard spin, and no test in this repo would catch it
// before the scheduler exists. Requirement R6 in SERVICE_CONTRACT.md.
extern fn sys_yield() = "sys_yield";

// ---------------------------------------------------------------------------
// Return conventions, in one place
// ---------------------------------------------------------------------------
//
// - Byte-count calls (write_serial, write_console) return >= 0 on success and a
//   negative code on failure. A short write (count < s.len) is a full buffer,
//   not an error: the caller decides whether to retry, drop, or split.
// - Boolean calls (read_key) use true = "there is something", false = "nothing
//   this time".
// - No call blocks except sys_exit, which never returns.
// - No call allocates. Every output is a caller-supplied buffer whose capacity
//   the callee cannot exceed -- that is what `u8[>..]&` means.

// ---------------------------------------------------------------------------
// The C shim specification (what K6 must provide)
// ---------------------------------------------------------------------------
//
// Goose compiles a call to `sys_write_serial(s)` into a direct C call to the
// symbol `sys_write_serial` with a pointer and a length. The kernel side is
// therefore one file of thin wrappers, and this is the exact spec for it:
//
//   // services/common/sys/shim.c   (kernel-side; NOT written yet)
//   #include <stdint.h>
//
//   void sys_exit(int32_t code);                 // noreturn in practice
//   int64_t sys_write_serial(const uint8_t *s, int64_t len);
//   int64_t sys_write_console(const uint8_t *s, int64_t len);
//   bool sys_read_key(uint8_t *out, int64_t cap, int64_t *out_len);
//   int64_t sys_ticks(void);
//   void sys_yield(void);
//
// Three details that matter and are easy to get wrong:
//
// 1. Go's slice parameter is a POINTER PLUS COUNT, and Goose's `const u8[:]`
//    is the same shape. The shim above splits it into `(ptr, len)` so the
//    kernel never has to know Goose's internal slice layout.
// 2. `u8[>..]&` is a caller-owned buffer. The callee needs both the base
//    pointer and the CAPACITY (to refuse overflow) AND a way to report how many
//    bytes it actually wrote -- hence `cap` in, `out_len` out. A shim that
//    writes past `cap` is a kernel memory-corruption bug, not a service bug.
// 3. The generated C for Goose names program symbols with a `_g` suffix
//    (spec#40), but an `extern fn`'s symbol is used unchanged. That is why the
//    explicit `= "sys_*"` names above matter: they are the C names the shim
//    must define, exactly.
//
// NOT WRITTEN: `shim.c` belongs to the kernel side (Layers 1-3), not this lane.
// It is listed as requirement A1-A6 in os-build/layer1/BOUNDARIES.md so it has
// an owner. Writing it here would be this lane editing another layer's code,
// which the work order forbids.

// ---------------------------------------------------------------------------
// Things services must NOT assume
// ---------------------------------------------------------------------------
//
// - That a write is partial only at a buffer boundary. The shim may return a
//   short count for any reason; callers loop.
// - That ticks start at zero. `sys_ticks()` may already be large at boot;
//   services always take a delta from a starting point (see services/time).
// - That read_key returns one event per byte of buffer capacity. The event size
//   is the kernel's to define; services parse what they get.
