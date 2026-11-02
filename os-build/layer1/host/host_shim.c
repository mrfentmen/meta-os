// os-build/layer1/host/host_shim.c
//
// The syscall surface, implemented by a host process instead of a kernel.
//
// WHAT THIS IS FOR
// ----------------
// BF4-01: run the services natively, one at a time. The corpus binds kernel
// calls through `extern fn ... = "sys_*"` in services/common/sys/sys.goose, so a
// Goose program can be built and run on this Mac the moment something defines
// those ten C symbols. That is this file. Nothing in `services/` changes to use
// it.
//
// WHAT IT PROVES, AND WHAT IT DOES NOT
// ------------------------------------
// It proves the *service logic* — parsers, tables, state machines, format
// strings, error paths — against real memory and a real clock. It proves nothing
// about the kernel: there is no scheduler, no address space and no frame buffer
// here. Every refusal below is deliberate and named, because a shim that fakes a
// capability makes a run look green for a reason that does not exist.
//
// THE ABI, AS CODEGEN ACTUALLY EMITS IT
// -------------------------------------
// The comment in sys.goose guesses the shim takes `(const uint8_t *s, int64_t len)`.
// It does not. Goose passes the slice as a struct by value, and a builder
// reference as a pair of pointers. Taken from the generated C (goose b781587):
//
//   gs_i64  sys_write_serial(sl_u8)      sl_u8 = { uint8_t *data; int64_t len; }
//   gs_i64  sys_write_console(sl_u8)
//   uint8_t sys_read_key(gs_rref)        gs_rref = { gs_rhdr *hdr; gs_stack *stk; }
//   gs_i64  sys_ticks(void)
//   void    sys_yield(void)
//   void    sys_exit(gs_i32)
//   gs_u64  sys_spawn(gs_u64, gs_i64, gs_i64)
//   gs_i32  sys_kill(gs_i64)
//   gs_i64  sys_net_send(gs_i64, sl_u8)
//   gs_i64  sys_net_recv(gs_i64, r_l1514_u8)
//
// The struct layouts are copied from the generated header, including the
// `#pragma pack(1)`, so a change in the compiler's layout breaks this file
// loudly (a wrong `len` shows up as garbage output on the first run) rather than
// silently.

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

typedef int64_t gs_i64;
typedef int32_t gs_i32;
typedef uint64_t gs_u64;

#pragma pack(push, 1)
typedef struct { uint8_t *data; int64_t len; } sl_u8;
typedef struct { uint8_t *base; int64_t len; } gs_rhdr;
typedef struct { gs_rhdr *hdr; void *stk; } gs_rref;
typedef struct { uint8_t *data; } r_l1514_u8;
#pragma pack(pop)

// ---------------------------------------------------------------------------
// The clock: monotonic milliseconds since the first call, which is what a tick
// count is for. The rate is deliberately NOT the kernel's — BootInfo publishes
// that, and nothing in this layer may assume it, so a test that assumed 100 Hz
// would fail here, which is the point.
// ---------------------------------------------------------------------------

static struct timespec host_t0;
static int host_t0_set = 0;

static int64_t host_now_ms(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    if (!host_t0_set) { host_t0 = t; host_t0_set = 1; }
    return (int64_t)(t.tv_sec - host_t0.tv_sec) * 1000
         + (int64_t)(t.tv_nsec - host_t0.tv_nsec) / 1000000;
}

// ---------------------------------------------------------------------------
// Output. Both writes go to stdout, in call order, on purpose: a transcript
// that interleaves two streams out of order is worse than one that cannot tell
// them apart, and the point of the transcript is to be readable as a sequence.
// The console/serial distinction is a kernel fact; here it is recorded as
// [console] / [serial] only when HOST_TAG_STREAMS=1.
// ---------------------------------------------------------------------------

static int host_tag_streams(void) {
    static int cached = -1;
    if (cached < 0) {
        const char *v = getenv("HOST_TAG_STREAMS");
        cached = (v && v[0] == '1') ? 1 : 0;
    }
    return cached;
}

static gs_i64 host_write(sl_u8 s, const char *tag) {
    if (s.len < 0 || (s.len > 0 && s.data == NULL)) { return -1; }
    if (host_tag_streams()) { fputs(tag, stdout); }
    if (s.len > 0) { fwrite(s.data, 1, (size_t)s.len, stdout); }
    fflush(stdout);
    return s.len;
}

gs_i64 sys_write_serial(sl_u8 s) { return host_write(s, "[serial] "); }
gs_i64 sys_write_console(sl_u8 s) { return host_write(s, "[console] "); }

// ---------------------------------------------------------------------------
// no such thing on a host: no keyboard, and no second process.
// ---------------------------------------------------------------------------

// Contract: true = an event is in the buffer, false = nothing pending. There is
// no keyboard on a host process, so "nothing pending" is the truthful answer, and
// it is the answer the contract distinguishes from end-of-input. A service that
// polls will spin here exactly as it would on a kernel with no key pressed --
// which is the behaviour under test, not a shim defect.
uint8_t sys_read_key(gs_rref out) {
    (void)out;
    return 0;
}

// No scheduler, no image loader. Returning a fake pid would let supervisor tests
// go green over a process that never existed, so this refuses and says so.
gs_u64 sys_spawn(gs_u64 image, gs_i64 len, gs_i64 priority) {
    (void)image; (void)len; (void)priority;
    return 0;                      // 0 is not a valid pid: nothing was spawned
}

gs_i32 sys_kill(gs_i64 pid) {
    (void)pid;
    return -1;
}

// No NIC, and no loopback link: the protocol pack talks to itself through
// tests/harness/link.goose instead, which is why that harness exists.
gs_i64 sys_net_send(gs_i64 link, sl_u8 frame) {
    (void)link; (void)frame;
    return -1;
}

gs_i64 sys_net_recv(gs_i64 link, r_l1514_u8 out) {
    (void)link; (void)out;
    return -1;
}

// ---------------------------------------------------------------------------
// The calls the scheduler would provide. A yield with nothing to yield to is a
// no-op; it is still called in every wait loop, so the loops are exercised.
// ---------------------------------------------------------------------------

gs_i64 sys_ticks(void) { return host_now_ms(); }

void sys_yield(void) { }

void sys_exit(gs_i32 code) {
    fflush(stdout);
    fflush(stderr);
    exit((int)code);
}
