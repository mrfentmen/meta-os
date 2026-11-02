// services/supervisor/bootorder.goose
//
// B-L1-64 — the service start order as DATA, not prose.
//
// Status: RUNS — reached by tests/t61_bootorder (24 checks, exit 0). Measured 2026-11-02 by audit_status.py. Forms verified via goose-mcp@1.1.0 (structs, fixed arrays,
// `while`/`if`, trailing-bool returns).
//
// WHY THIS IS DATA
// ----------------
// The order has to be one thing. Written as prose in a document, it and the supervisor's table
// drift within a week, and the drift shows up as a service that starts before its logger and
// logs into nothing. Here the order, each service's dependencies and whether its failure is
// fatal are one table; `bo_ready()` is the only reader, and `sup_register` calls are made from
// it in order.
//
// THE MASKS ARE SERVICE IDS
// -------------------------
// A dependency mask uses the ids from `services/callmatrix/callmatrix.goose` (1..22) so the
// matrix and the boot order cannot disagree about what a service is. If an id changes there,
// it changes here in the same commit; that is what the mask comment on each row is for.
//
// CYCLES, AND HOW THEY ARE BROKEN
// -------------------------------
// The call matrix has real cycles (bootlog/console, input/session/display, net/netcfg). The
// boot order cannot. Each cycle is broken by a rule, not by taste:
//   - bootlog starts before console: the first lines of a boot are written before there is a
//     console to write them on.
//   - log starts after console+logfmt+storage: it MIRRORS to a screen and PERSISTS to storage,
//     so both must exist first. Until then, bootlog carries the messages.
//   - netcfg starts before net: the interface is configured from data before a link exists.
//   - input starts before display and session: keys exist before there is anything to route
//     them to, and the decoder holds no references.
//
// THE ONE ENTRY THE KERNEL STARTS
// -------------------------------
// `supervisor` is `by_kernel`: the kernel starts it, and IT starts everything else. Its
// `needs` therefore describe what its TABLE wants at runtime (the call matrix), not what must
// already be running -- nothing is. Writing that as a normal dependency would put the starter
// last in its own start order, which is the kind of table that reads fine and cannot boot.
//
// WHAT A FAILURE MEANS
// --------------------
// `fatal` means the layer refuses to continue without it: no logger, no supervisor, no clock,
// no devices. Everything else degrades and reports.

import common.err.err;

let BO_MAX: i64 = 24;

struct BootEntry {
    id: i64,
    needs: i64,          // bitmask of ids that must be RUNNING before this one starts
    fatal: bool,         // its failure stops the layer rather than degrading it
    by_kernel: bool,     // started by the kernel, not by this table (the supervisor only)
    order: i64,          // position in the start sequence, 1-based
}

// The table, in start order. Read down the `needs` column and every bit is set earlier than
// the row that needs it -- that property is what `bo_order_ok()` checks at start-up.
var boot_table: BootEntry[..24] = [
    BootEntry { id: 2, needs: 0, fatal: true, by_kernel: false, order: 1 },  // bootlog
    BootEntry { id: 3, needs: 4, fatal: true, by_kernel: false, order: 2 },  // devices
    BootEntry { id: 5, needs: 8, fatal: true, by_kernel: false, order: 3 },  // time
    BootEntry { id: 4, needs: 8, fatal: true, by_kernel: false, order: 4 },  // storage
    BootEntry { id: 1, needs: 0, fatal: true, by_kernel: false, order: 5 },  // callmatrix
    BootEntry { id: 16, needs: 2, fatal: true, by_kernel: true, order: 6 },  // supervisor
    BootEntry { id: 7, needs: 4, fatal: false, by_kernel: false, order: 7 },  // console
    BootEntry { id: 6, needs: 32, fatal: false, by_kernel: false, order: 8 },  // logfmt
    BootEntry { id: 8, needs: 208, fatal: true, by_kernel: false, order: 9 },  // logd
    BootEntry { id: 14, needs: 32, fatal: false, by_kernel: false, order: 10 },  // watchdog
    BootEntry { id: 13, needs: 304, fatal: false, by_kernel: false, order: 11 },  // audit
    BootEntry { id: 9, needs: 16, fatal: false, by_kernel: false, order: 12 },  // netcfg
    BootEntry { id: 10, needs: 520, fatal: false, by_kernel: false, order: 13 },  // net
    BootEntry { id: 11, needs: 256, fatal: false, by_kernel: false, order: 14 },  // input
    BootEntry { id: 12, needs: 256, fatal: false, by_kernel: false, order: 15 },  // display
    BootEntry { id: 15, needs: 14336, fatal: false, by_kernel: false, order: 16 },  // session
    BootEntry { id: 17, needs: 1824, fatal: false, by_kernel: false, order: 17 },  // dhcp
    BootEntry { id: 18, needs: 1792, fatal: false, by_kernel: false, order: 18 },  // dns
    BootEntry { id: 19, needs: 263456, fatal: false, by_kernel: false, order: 19 },  // socket
    BootEntry { id: 20, needs: 524576, fatal: false, by_kernel: false, order: 20 },  // timesync
    BootEntry { id: 21, needs: 532784, fatal: false, by_kernel: false, order: 21 },  // updater
    BootEntry { id: 22, needs: 106768, fatal: false, by_kernel: false, order: 22 },  // agenthost
];

// Name per id, in ID order (token 1 is id 1), so a log line can name a service without the
// caller carrying a string table of its own. This is NOT the start order -- `order` in the
// table is, and the two differ the moment the sequence is tuned. Keeping one table for
// "what is it called" and another for "when does it start" is deliberate: the name table
// must stay stable because it ends up in logs people grep.
//
// Each token is the service's directory name under `services/`, exactly. `logd`, not `log`:
// a log line that names a service the manifest does not have costs an hour every time. The
// boot order data test (`os-build/layer1/bootorder_check.py`) fails on a mismatch.
let BO_NAMES: const u8[:] = "callmatrix bootlog devices storage time logfmt console logd netcfg net input display audit watchdog session supervisor dhcp dns socket timesync updater agenthost";

fn bo_count() -> i64 { return 22; }

// Copy the name of a service into the caller's buffer. Returns false for an unknown id, or
// when the name does not fit -- the caller can tell those apart with bo_count/bo_entry, and a
// truncated name is never written (a half service name in a log is worse than no name).
fn bo_name(id: i64, out: u8[>..]&, cap: i64) -> bool {
    if id < 1 || id > bo_count() { return false; }
    var token: i64 = 1;
    var i: i64 = 0;
    var len: i64 = 0;
    var start: i64 = -1;
    while i <= BO_NAMES.len {
        let at_end = i == BO_NAMES.len;
        let is_sep = at_end || BO_NAMES[i] == ' ';
        if !is_sep && start < 0 { start = i; }
        if is_sep && start >= 0 {
            if token == id {
                len = i - start;
                if out.len + len > cap { return false; }
                var k = start;
                while k < i {
                    out.push(BO_NAMES[k]);
                    k = k + 1;
                }
                return true;
            }
            token = token + 1;
            start = -1;
        }
        i = i + 1;
    }
    return false;
}

fn bo_entry(i: i64) -> BootEntry {
    if i < 0 || i >= bo_count() { return BootEntry { id: 0, needs: 0, fatal: false, by_kernel: false, order: 0 }; }
    return boot_table[i];
}

// The id at a position in the start order (1-based), or 0 past the end.
fn bo_at(order: i64) -> i64 {
    var i: i64 = 0;
    while i < bo_count() {
        if boot_table[i].order == order { return boot_table[i].id; }
        i = i + 1;
    }
    return 0;
}

fn bo_is_fatal(id: i64) -> bool {
    var i: i64 = 0;
    while i < bo_count() {
        if boot_table[i].id == id { return boot_table[i].fatal; }
        i = i + 1;
    }
    return true;    // an id not in the table is not a service this order knows: treat as fatal
}

// May this service start now? `running` is the mask of services already RUNNING.
// A service whose dependencies are all running is ready; nothing else is.
fn bo_ready(id: i64, running: i64) -> bool {
    var i: i64 = 0;
    while i < bo_count() {
        if boot_table[i].id == id {
            return (boot_table[i].needs & running) == boot_table[i].needs;
        }
        i = i + 1;
    }
    return false;
}

// The dependency mask of a service, for the error message that says what it is waiting for.
fn bo_needs(id: i64) -> i64 {
    var i: i64 = 0;
    while i < bo_count() {
        if boot_table[i].id == id { return boot_table[i].needs; }
        i = i + 1;
    }
    return 0;
}

// Which services a fatal failure takes down with it: this one, and (transitively) everything
// that depends on it. Returned as a mask, so the supervisor can mark them STOPPED in one pass
// instead of discovering the cascade one timeout at a time.
fn bo_cascade(id: i64) -> i64 {
    var doomed: i64 = 1 << id;
    var changed: bool = true;
    while changed {
        changed = false;
        var i: i64 = 0;
        while i < bo_count() {
            let dep = boot_table[i].id;
            if (doomed & (1 << dep)) == 0 && (boot_table[i].needs & doomed) != 0 {
                // Only a FATAL dependency cascades. A non-fatal one degrades; killing the
                // caller of a degraded service turns one failure into an outage.
                if bo_is_fatal(id) {
                    doomed = doomed | (1 << dep);
                    changed = true;
                }
            }
            i = i + 1;
        }
    }
    return doomed;
}

// The order is consistent if every dependency sits earlier in the sequence. Checked once at
// start-up: a table with a forward reference is a boot that deadlocks, and it should fail
// loudly at the earliest moment rather than hang at the twelfth service.
fn bo_order_ok() -> bool {
    var i: i64 = 0;
    while i < bo_count() {
        let needs = boot_table[i].needs;
        var j: i64 = 0;
        while j < bo_count() {
            if (needs & (1 << boot_table[j].id)) != 0 {
                if boot_table[j].order >= boot_table[i].order { return false; }
            }
            j = j + 1;
        }
        i = i + 1;
    }
    return true;
}

// The whole sequence as a list of ids, for the supervisor to register from. Returns the count.
fn bo_sequence(out: i64[..24]&, cap: i64) -> i64 {
    var n: i64 = 0;
    var pos: i64 = 1;
    while pos <= bo_count() && n < cap && n < 24 {
        let id = bo_at(pos);
        if id != 0 {
            out[n] = id;
            n = n + 1;
        }
        pos = pos + 1;
    }
    return n;
}
