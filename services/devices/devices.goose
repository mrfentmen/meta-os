// services/devices/devices.goose
//
// Layer 4, service 8: the device table. What hardware exists, what state each
// device is in, and the one query every other service uses instead of poking at
// raw facts.
//
// Status: RUNS — reached by tests/t77_gaps (73 checks, exit 0). Measured 2026-11-02 by audit_status.py. Verified via goose-mcp@1.1.0: struct with
// fixed-size fields and literals (reference#32), static arrays T[..k], fixed-size
// array members, `import` of a sibling module (same form supervisor.goose uses for
// common.err.err), multi-value returns.
//
// WHY A TABLE AND NOT DIRECT FIELD ACCESS
// ---------------------------------------
// Every service needs the framebuffer's column count, or the tick rate, or whether
// there is a serial line at all. If each one reads BootInfo directly, then a device
// that fails *after* boot (a device that faults, a line that drops) is invisible to
// all of them: they keep reading a boot-time fact as if it were a live one. The
// table adds the one thing BootInfo cannot carry -- current state.
//
// WHAT IT PROBES, AND WHAT IT CANNOT
// ----------------------------------
// Probed from BootInfo, honestly:
//   serial       <- SerialInfo.port (K1: COM1 at 0x3F8)
//   framebuffer  <- FramebufferInfo.address/cols/rows ([PROPOSED] until K2 lands)
//   timer        <- TimeInfo.tick_hz      ([PROPOSED] until K3 lands)
//
// NOT probed: the KEYBOARD. BootInfo has no keyboard field at all -- SerialInfo,
// FramebufferInfo, TimeInfo and MemoryInfo are the whole block (boot.goose:123-129).
// K3's PS/2 driver exists in Rowan's branch, but nothing publishes it to a service
// yet. This file therefore registers the keyboard as ABSENT and says why, rather
// than inventing a field to probe or quietly leaving the device out of the table.
// That is requirement A11 in os-build/layer1/BOUNDARIES.md.

import common.boot.boot;
import common.err.err;

// ---------------------------------------------------------------------------
// Vocabulary
// ---------------------------------------------------------------------------

let DEV_NONE: i64 = 0;
let DEV_SERIAL: i64 = 1;
let DEV_FRAMEBUFFER: i64 = 2;
let DEV_KEYBOARD: i64 = 3;
let DEV_TIMER: i64 = 4;
let DEV_BLOCK: i64 = 5;
let DEV_NET: i64 = 6;

// ABSENT is a real state, not a placeholder: the keyboard below is absent because
// nothing publishes it, and services that need one must find that out by querying
// rather than by assuming.
let DS_ABSENT: i64 = 0;      // not detected
let DS_DETECTED: i64 = 1;    // found, not yet usable
let DS_READY: i64 = 2;       // usable now
let DS_FAULT: i64 = 3;       // was usable, failed

let DEV_MAX: i64 = 16;       // a PC at this layer has single digits of devices

struct Device {
    kind: i64,
    state: i64,
    name: u8[..16] = [0; 16],
    name_len: i64,
    addr: u64,          // MMIO/IO base, or 0 when the device has none
    irq: i64,           // -1 when the device is polled
    // Two free numbers per device, interpreted per kind: (cols, rows) for the
    // framebuffer, (hz, 0) for the timer, (-1, -1) otherwise. A union would need
    // construction support this lane has not verified; explicit spare slots with a
    // documented meaning are the honest alternative.
    detail_a: i64,
    detail_b: i64,
}

var devices: Device[..16] = [Device { .. }; 16];
var device_count: i64 = 0;

// ---------------------------------------------------------------------------
// Registration
// ---------------------------------------------------------------------------

fn dev_add(kind: i64, name: const u8[:], addr: u64, irq: i64, a: i64, b: i64) -> i64, i64 {
    if device_count >= DEV_MAX { return -1, E_NOROOM; }
    if name.len == 0 || name.len >= 16 { return -1, E_INVAL; }
    if kind <= DEV_NONE { return -1, E_INVAL; }
    // One entry per kind: a second framebuffer would make "the framebuffer" an
    // ambiguous phrase, and every caller of dev_find would have to disambiguate.
    if dev_find(kind) >= 0 { return -1, E_STATE; }

    var i: i64 = 0;
    while i < name.len {
        devices[device_count].name[i] = name[i];
        i = i + 1;
    }
    devices[device_count].name[i] = 0;
    devices[device_count].name_len = name.len;
    devices[device_count].kind = kind;
    devices[device_count].state = DS_DETECTED;
    devices[device_count].addr = addr;
    devices[device_count].irq = irq;
    devices[device_count].detail_a = a;
    devices[device_count].detail_b = b;

    device_count = device_count + 1;
    return device_count - 1, CODE_OK;
}

fn dev_find(kind: i64) -> i64 {
    var i: i64 = 0;
    while i < device_count {
        if devices[i].kind == kind { return i; }
        i = i + 1;
    }
    return -1;
}

// ---------------------------------------------------------------------------
// Probing BootInfo
// ---------------------------------------------------------------------------
//
// Returns the number of devices registered. Called once, at start-up, before any
// other service asks a question -- which is why it is the entry's first act.
fn dev_probe_boot(boot: BootInfo&) -> i64, i64 {
    if !bootinfo_supported(boot) { return 0, E_UNSUPPORTED; }
    if device_count != 0 { return 0, E_STATE; }   // probing twice would double the table

    var ok: i64 = 0;

    // Serial: the K1 UART. port 0 means the kernel did not give us one, which is a
    // fact to record, not an error to raise.
    if boot.serial.port != 0 {
        let slot, code = dev_add(DEV_SERIAL, "serial", boot.serial.port as u64, -1,
                                 boot.serial.baud as i64, boot.serial.data_bits as i64);
        if code == CODE_OK {
            dev_mark(slot, DS_READY);   // K1 proved it by printing the boot line
            ok = ok + 1;
        }
    }

    // Framebuffer: [PROPOSED] fields. A zero address means K2 has not landed, so the
    // device is registered ABSENT rather than READY -- the console can then say
    // "no display" instead of drawing into address 0.
    if boot.framebuffer.address != 0 && boot.framebuffer.cols != 0 {
        let slot, code = dev_add(DEV_FRAMEBUFFER, "framebuffer", boot.framebuffer.address, -1,
                                 boot.framebuffer.cols as i64, boot.framebuffer.rows as i64);
        if code == CODE_OK {
            dev_mark(slot, DS_READY);
            ok = ok + 1;
        }
    } else {
        let slot, code = dev_add(DEV_FRAMEBUFFER, "framebuffer", 0, -1, 0, 0);
        if code == CODE_OK {
            dev_mark(slot, DS_ABSENT);
        }
    }

    // Timer: tick_hz 0 means no timer, and every timeout in the layer becomes
    // infinite. Recorded as a fault, because a machine with no tick cannot keep the
    // promises the other services make.
    if boot.time.tick_hz != 0 {
        let slot, code = dev_add(DEV_TIMER, "timer", 0, 0, boot.time.tick_hz as i64, 0);
        if code == CODE_OK {
            dev_mark(slot, DS_READY);
            ok = ok + 1;
        }
    } else {
        let slot, code = dev_add(DEV_TIMER, "timer", 0, 0, 0, 0);
        if code == CODE_OK {
            dev_mark(slot, DS_FAULT);
        }
    }

    // Keyboard: absent by omission from BootInfo (see the header). Registered so the
    // absence is queryable; changing this line is the whole fix once the kernel
    // publishes one.
    let kbslot, kbcode = dev_add(DEV_KEYBOARD, "keyboard", 0, -1, 0, 0);
    if kbcode == CODE_OK {
        dev_mark(kbslot, DS_ABSENT);
    }

    return ok, CODE_OK;
}

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

// Legal device moves. A device goes DETECTED -> READY once, READY -> FAULT when it
// fails, FAULT -> READY when it recovers, and anything -> ABSENT when it disappears.
// READY -> DETECTED is deliberately illegal: "became less ready without failing" is
// not a thing a driver can report, and allowing it would hide a missed FAULT.
fn dev_state_legal(from: i64, to: i64) -> bool {
    if from == to { return false; }
    if to == DS_ABSENT { return true; }                 // anything may vanish
    if from == DS_ABSENT && to == DS_DETECTED { return true; }
    if from == DS_DETECTED && to == DS_READY { return true; }
    if from == DS_DETECTED && to == DS_FAULT { return true; }
    if from == DS_READY && to == DS_FAULT { return true; }
    if from == DS_FAULT && to == DS_READY { return true; }
    if from == DS_FAULT && to == DS_DETECTED { return true; }  // re-probing after a reset
    return false;
}

fn dev_mark(slot: i64, state: i64) -> i64 {
    if slot < 0 || slot >= device_count { return E_INVAL; }
    if !dev_state_legal(devices[slot].state, state) { return E_STATE; }
    devices[slot].state = state;
    return CODE_OK;
}

// ---------------------------------------------------------------------------
// The query interface
// ---------------------------------------------------------------------------

// Is this kind of device usable right now? The question callers actually ask before
// using one -- "is there a display" -- answered by state, not by presence.
fn dev_ready(kind: i64) -> bool {
    let slot = dev_find(kind);
    if slot < 0 { return false; }
    return devices[slot].state == DS_READY;
}

// Details for a ready device. Zeroed + E_STATE when it is not ready: a caller that
// ignores the code gets zeros rather than the stale numbers of a faulted device.
fn dev_detail(kind: i64) -> i64, i64, i64 {
    let slot = dev_find(kind);
    if slot < 0 { return 0, 0, E_NOTFOUND; }
    if devices[slot].state != DS_READY { return 0, 0, E_STATE; }
    return devices[slot].detail_a, devices[slot].detail_b, CODE_OK;
}

fn dev_count_in(state: i64) -> i64 {
    var n: i64 = 0;
    var i: i64 = 0;
    while i < device_count {
        if devices[i].state == state { n = n + 1; }
        i = i + 1;
    }
    return n;
}

// A one-line summary for the boot log and the health line: how many devices are
// ready, faulted, absent. Deliberately three numbers and not a formatted string --
// formatting is common/fmt's job, and a service that formats its own diagnostics
// will disagree with the others about what a boot line looks like.
fn dev_summary() -> i64, i64, i64 {
    return dev_count_in(DS_READY), dev_count_in(DS_FAULT), dev_count_in(DS_ABSENT);
}

// ---------------------------------------------------------------------------
// Deliberately absent
// ---------------------------------------------------------------------------
//
// - No driver code. A driver belongs to Layer 3; this table records what a driver
//   reports.
// - No hot-plug yet: B-L1-113 adds the event path, and it needs the IPC transport
//   (Q-B-L1-2) to notify anyone.
// - No enumeration beyond BootInfo. Walking PCI/ACPI would be Layer 3 work
//   duplicated at Layer 4, and duplicated enumeration disagrees with itself.
