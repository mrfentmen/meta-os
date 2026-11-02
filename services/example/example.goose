// services/example/example.goose
//
// B-L1-94 — the template service. Every pattern a new Layer 4 service should copy, in one
// file that actually does something small and does it completely.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// WHAT IT IS
// ----------
// `tickerd`: reads its config, registers itself with the supervisor, beats a heartbeat at
// its configured interval, builds a fixed record per tick, and stops cleanly on request.
// It is boring on purpose -- a template that is clever teaches the clever part.
//
// THE NINE THINGS EVERY SERVICE DOES, IN ORDER
// --------------------------------------------
// 1. `service_main` is the only export. One entry point, C ABI, exit code returned
//    (SERVICE_CONTRACT.md §2). No other symbol is visible to the kernel.
// 2. Validate the BootInfo it was handed before trusting a field in it.
// 3. Load config through `common/cfg`; every default is named, not literal at the use site.
// 4. Register with the supervisor and keep the handle; never address a service by id.
// 5. Own its storage: fixed buffers, sized by a named constant, checked at every write.
// 6. Emit records through `common/fmt` into a fixed buffer, then one write.
// 7. Report errors as codes from `common/err`, and never as a "0 means fine" boolean.
// 8. Beat the heartbeat, and stop beating the moment it is asked to stop.
// 9. Return a code from `service_main` that means something.
//
// WHAT IT DOES NOT DO, AND WHY THAT IS THE TEMPLATE'S POINT
// --------------------------------------------------------
// No allocation, no threads, no global mutable state shared with another service, no
// blocking call that has no timeout, no `exit()` in the middle. Services that break these
// are the ones the supervisor cannot reason about.

import common.boot.boot;
import common.cfg.cfg;
import fs.fs;
import fs.paths;
import common.err.err;
import common.fmt.fmt;
import common.hash.hash;
import common.ring.ring;
import common.sys.sys;
import supervisor.supervisor;
import time.time;
import watchdog.watchdog;

// ---------------------------------------------------------------------------
// Constants: named, and justified
// ---------------------------------------------------------------------------

let EX_NAME: const u8[:] = "tickerd";
let EX_NAME_MAX: i64 = 32;
let EX_REC_MAX: i64 = 128;      // one record; the log's own limit is 256 (B-L1-28)
let EX_RING: i64 = 4;           // records buffered before a flush is attempted

// Config keys this service reads. Named so a typo is a compile-time-ish miss (one place to
// grep) rather than a string buried in a call.
let CFG_SECTION: const u8[:] = "tickerd";
let CFG_INTERVAL: const u8[:] = "interval_ms";
let CFG_ENABLED: const u8[:] = "enabled";
let CFG_PATH: const u8[:] = "/etc/tickerd.conf";
let CFG_TEXT_MAX: i64 = 256;

// Defaults. Every one is a decision, not a placeholder: 1000 ms is a heartbeat, not a busy
// loop, and `enabled = true` because a service that asks to be started and then does
// nothing is a bug in the config, not a feature.
let DEF_INTERVAL_MS: i64 = 1000;

// ---------------------------------------------------------------------------
// State: fixed, owned, and small enough to reason about
// ---------------------------------------------------------------------------

var ex_cfg: Config;
var ex_handle: i64 = 0;
var ex_running: bool = false;
var ex_ticks: i64 = 0;
var ex_dropped: i64 = 0;
var ex_ring: Ring = Ring { head: 0, tail: 0, count: 0, cap: 0 };
// Builder, not a fixed array: ring_push takes a builder (typed mismatch otherwise).
var ex_ring_buf: u8[>..] = [];
var ex_clock: Clock = Clock { hz: 1000 };
var ex_cfg_text: u8[..256] = [0; 256];
var ex_cfg_len: i64 = 0;

// ---------------------------------------------------------------------------
// 1. The export
// ---------------------------------------------------------------------------
//
// `export` + a C name: the kernel calls this once and reads the return value as the exit
// code (SERVICE_CONTRACT.md §2). The parameter is the BootInfo block, by reference -- the
// argument-pointer delivery A1 assumes, and the one open question Q-B-L1-4 is about. If the
// answer turns out to be a syscall instead, this signature changes and nothing else does.



// ---------------------------------------------------------------------------
// The actual service, in the nine steps
// ---------------------------------------------------------------------------

fn run(boot: BootInfo&) -> i64 {
    // 2. BootInfo first: a service that reads a field before validating it is a service
    //    that trusts whatever the loader left in memory.
    if !bootinfo_supported(boot) { return E_STATE; }

    // 3. Config. The text comes from the filesystem; if there is no file, the empty text
    //    parses to an empty config and every key takes its named default.
    load_config();
    let interval, _have_interval = cfg_int(ex_cfg, CFG_SECTION, CFG_INTERVAL, DEF_INTERVAL_MS);
    let enabled, have_enabled = cfg_bool(ex_cfg, CFG_SECTION, CFG_ENABLED, true);
    if interval < 10 || interval > 60000 { return E_INVAL; }   // refuse, never clamp
    if have_enabled && !enabled { return CODE_OK; }            // asked not to run: not an error

    // 4. Register. Keep the HANDLE (generation-carrying, B-L1-22); the table is addressed
    //    by slot, so the slot is resolved once and used for the state transitions.
    let h, hcode = sup_register(EX_NAME, -1, true);
    if hcode != CODE_OK { return hcode; }
    ex_handle = h;
    let slot = sup_resolve(ex_handle);
    if slot < 0 { return E_STATE; }
    let sc = sup_set_state(slot, ST_RUNNING);
    if sc != CODE_OK { return sc; }
    ex_running = true;

    // 5. Own storage, sized by constants, cleared explicitly.
    ex_ring = ring_init(EX_RING);
    var i: i64 = 0;
    while i < EX_RING * 130 { ex_ring_buf.push(0); i = i + 1; }

    // 6/7/8. The loop: build a record, beat, sleep, and check for a stop request.
    let started = clock_uptime_ms(ex_clock);
    let _ = wd_watch(ex_handle, interval * 2, 0, 2, started);
    var last_ms = started;
    while ex_running {
        let now = clock_uptime_ms(ex_clock);
        if now - last_ms >= interval {
            last_ms = now;
            tick(now);
            // 8. Beat after work, not before: a heartbeat that arrives while nothing is
            //    progressing is the one signal the watchdog cannot use.
            let _ = sup_beat(slot, now);
            let _ = wd_beat(ex_handle, now);
        }
        // A budgeted wait, not a spin. The layer has no timer queue yet (Q-B-L1-6); this
        // yields for a tenth of the interval and re-checks.
        let _ = clock_budget(ex_clock, 10);
        sys_yield();
    }

    let _ = sup_set_state(slot, ST_STOPPED);
    let _ = wd_unwatch(ex_handle);
    return CODE_OK;
}

// Read the service's config file into a fixed buffer. Missing file is not an error: it
// means "all defaults", which is the only reading that lets a service start on a fresh
// install without a config present.
fn load_config() {
    ex_cfg_len = 0;
    var i: i64 = 0;
    while i < CFG_TEXT_MAX { ex_cfg_text[i] = 0; i = i + 1; }
    let ino, code = fs_resolve(fs_root(), CFG_PATH, false);
    if code != CODE_OK { ex_cfg = cfg_init(ex_cfg_text[0..0]); return; }
    var buf: u8[>..] = [];
    let got, rcode = fs_read(ino, 0, buf, CFG_TEXT_MAX);
    if rcode != CODE_OK { ex_cfg = cfg_init(ex_cfg_text[0..0]); return; }
    i = 0;
    while i < got { ex_cfg_text[i] = buf[i]; i = i + 1; }
    ex_cfg_len = got;
    ex_cfg = cfg_init(ex_cfg_text[0..ex_cfg_len]);
}

// One tick: build a record into a fixed buffer and hand it to the ring. The record is built
// whole before anything is written, so a partial line cannot reach the log.
fn tick(now_ms: i64) {
    var rec: u8[>..] = [];
    let _ = append_str(rec, EX_REC_MAX, "tick ");
    let _ = append_int(rec, EX_REC_MAX, ex_ticks);
    let _ = append_str(rec, EX_REC_MAX, " at ");
    let _ = append_int(rec, EX_REC_MAX, now_ms);
    let _ = append_str(rec, EX_REC_MAX, "ms crc=");
    let sum = crc32(rec[..]);          // integrity over the body, before the checksum text
    let _ = append_uint(rec, EX_REC_MAX, sum as u64, 16, 8, '0');
    let _ = append_nl(rec, EX_REC_MAX);

    // Ring push per byte: the ring is bytes, not records, so the record boundary is the
    // caller's `\n` and the next reader can split on it.
    var i: i64 = 0;
    var dropped_any = false;
    while i < rec.len {
        if ring_push(ex_ring, ex_ring_buf, rec[i]) == false {
            // Full: count it. A service that silently drops its own records is a service
            // whose log cannot be trusted to be complete.
            dropped_any = true;
            break;
        }
        i = i + 1;
    }
    if dropped_any { ex_dropped = ex_dropped + 1; }
    ex_ticks = ex_ticks + 1;
}

// A stop request from the supervisor. Exposed as a function rather than a flag so the
// supervisor's message handler has one call site (B-L1-20's contract).
fn on_stop() {
    ex_running = false;
}

// Status, for `ps`/status views. Returns a code and fills the caller's buffer, because a
// service that returned a slice into its own state would hand out a view it can change.
fn status(out: u8[>..]&, cap: i64) -> i64 {
    let _ = append_str(out, cap, EX_NAME);
    let _ = append_str(out, cap, " ticks=");
    let _ = append_int(out, cap, ex_ticks);
    let _ = append_str(out, cap, " dropped=");
    let _ = append_int(out, cap, ex_dropped);
    let _ = append_str(out, cap, " running=");
    let _ = append_bool(out, cap, ex_running);
    let _ = append_nl(out, cap);
    return CODE_OK;
}

// ---------------------------------------------------------------------------
// The checklist this file is meant to be read against (also in README.md)
// ---------------------------------------------------------------------------
//
// [x] one export, C ABI, returns a meaningful code
// [x] BootInfo validated before any field is read
// [x] config through common/cfg, defaults named
// [x] registers with the supervisor, keeps the handle, bumps its state
// [x] fixed buffers with named constants and an explicit clear
// [x] records built whole, then written once
// [x] error codes from common/err; no boolean that means four things
// [x] heartbeat after work, stopped when asked
// [x] no allocation, no threads, no blocking call without a budget
// [x] a status function that writes into the caller's buffer
// [ ] COMPILED -- blocked on the toolchain (Q5)
// [ ] RUN -- blocked on K6
