// services/dashboard/dashboard.goose
//
// Layer 5, face service 4: the dashboard feed (CPU, memory, storage, network).
//
// WHAT THIS IS
// ------------
// A sample table for the four numbers the dashboard shows, with the one rule that
// makes a dashboard honest: **a value is never invented**. A metric that has never
// been sampled reports `DF_NEVER`; one older than its staleness window reports
// `DF_STALE` with its age. Neither is reported as 0, because 0% CPU is a fact and
// "nobody measured" is not.
//
// WHY THE CALLER PASSES THE CLOCK
// -------------------------------
// There is no global clock in this layer and no ambient `now`: every call that needs
// a time is given one. A feed that read a clock itself could not be replayed, and the
// stale labels are exactly the part worth replaying.
//
// WHY STALENESS IS PER METRIC
// ---------------------------
// A disk figure that is ten seconds old is fine; a CPU figure that is ten seconds old
// is a lie about right now. Each kind carries its own window, and the default is on
// the kind, not on the caller.
//
// Status: RUNS — reached by tests/t89_dashboard (exit 0). Measured 2026-11-02 by audit_status.py.

import common.err.err;

let DF_CPU: i64 = 1;
let DF_MEM: i64 = 2;
let DF_DISK: i64 = 3;
let DF_NET: i64 = 4;
let DF_MAX_KIND: i64 = 4;

// Freshness verdicts, returned instead of being folded into the value.
let DF_FRESH: i64 = 0;
let DF_STALE: i64 = 1;
let DF_NEVER: i64 = 2;

let DF_MAX_AGE_MS: i64 = 60000;

struct Sample {
    value: i64,
    taken_ms: i64,
    have: bool,
    stale_after_ms: i64,
}

var samples: Sample[..5] = [Sample { .. }; 5];
var df_inited: bool = false;

fn df_kind_name(kind: i64) -> const u8[:] {
    if kind == DF_CPU { return "cpu"; }
    if kind == DF_MEM { return "mem"; }
    if kind == DF_DISK { return "disk"; }
    if kind == DF_NET { return "net"; }
    return "";
}

fn df_kind_ok(kind: i64) -> bool {
    return kind >= 1 && kind <= DF_MAX_KIND;
}

// The window each kind gets by default. CPU is the one people watch, so it is short.
fn df_default_window(kind: i64) -> i64 {
    if kind == DF_CPU { return 2000; }
    if kind == DF_MEM { return 5000; }
    if kind == DF_DISK { return 30000; }
    if kind == DF_NET { return 2000; }
    return 5000;
}

fn df_init() {
    var k: i64 = 0;
    while k <= DF_MAX_KIND {
        samples[k].value = 0;
        samples[k].taken_ms = 0;
        samples[k].have = false;
        samples[k].stale_after_ms = df_default_window(k);
        k = k + 1;
    }
    df_inited = true;
}

fn df_ensure() {
    if !df_inited { df_init(); }
}

// A sample the producer just measured. Ranges are checked here so the UI never has to
// defend against 140% CPU or a negative byte rate.
fn df_put(kind: i64, value: i64, now_ms: i64) -> i64 {
    df_ensure();
    if !df_kind_ok(kind) { return E_INVAL; }
    if kind == DF_NET {
        if value < 0 { return E_INVAL; }
    } else {
        if value < 0 || value > 100 { return E_INVAL; }
    }
    // Time does not go backwards. A sample stamped in the past would make the next
    // stale check subtract a negative age and call an old figure fresh.
    if samples[kind].have && now_ms < samples[kind].taken_ms { return E_STATE; }
    samples[kind].value = value;
    samples[kind].taken_ms = now_ms;
    samples[kind].have = true;
    return CODE_OK;
}

fn df_set_window(kind: i64, ms: i64) -> i64 {
    df_ensure();
    if !df_kind_ok(kind) { return E_INVAL; }
    if ms < 1 || ms > DF_MAX_AGE_MS { return E_INVAL; }
    samples[kind].stale_after_ms = ms;
    return CODE_OK;
}

fn df_window(kind: i64) -> i64 {
    df_ensure();
    if !df_kind_ok(kind) { return 0; }
    return samples[kind].stale_after_ms;
}

// Age in ms, or -1 when there is no sample. Negative ages cannot occur: df_put
// refuses a backwards clock.
fn df_age_ms(kind: i64, now_ms: i64) -> i64 {
    df_ensure();
    if !df_kind_ok(kind) { return -1; }
    if !samples[kind].have { return -1; }
    let age = now_ms - samples[kind].taken_ms;
    if age < 0 { return 0; }
    return age;
}

// The value and its verdict. The value is returned even when stale: a stale number
// with a label is more useful than a blank, as long as the label is honest.
fn df_get(kind: i64, now_ms: i64) -> i64, i64 {
    df_ensure();
    if !df_kind_ok(kind) { return 0, E_INVAL; }
    if !samples[kind].have { return 0, DF_NEVER; }
    let age = df_age_ms(kind, now_ms);
    if age > samples[kind].stale_after_ms { return samples[kind].value, DF_STALE; }
    return samples[kind].value, DF_FRESH;
}

fn df_verdict(kind: i64, now_ms: i64) -> i64 {
    let _v, code = df_get(kind, now_ms);
    return code;
}

// The bar label: "<kind> <value><unit> <verdict>", where the verdict carries the age
// when stale and says "never" when there is nothing. No unit is invented for a
// missing sample, and a stale one is never printed without its age.
//
// Examples: "cpu 42% fresh", "mem 61% stale 7s", "disk never"
fn df_label(kind: i64, now_ms: i64, out: u8[>..]&) {
    df_ensure();
    if !df_kind_ok(kind) {
        df_put_str(out, "?");
        return;
    }
    let name = df_kind_name(kind);
    var i: i64 = 0;
    while i < name.len { let _ = out.push(name[i]); i = i + 1; }
    let _ = out.push(32);

    if !samples[kind].have {
        df_put_str(out, "never");
        return;
    }
    let age = df_age_ms(kind, now_ms);
    let v = samples[kind].value;
    df_put_int(out, v);
    if kind == DF_NET {
        df_put_str(out, "B/s");
    } else {
        let _ = out.push(37);          // '%'
    }
    let _ = out.push(32);
    if age > samples[kind].stale_after_ms {
        df_put_str(out, "stale ");
        // Age in seconds, floored, and never 0s: "stale 0s" reads as fresh.
        var secs = age / 1000;
        if secs < 1 { secs = 1; }
        df_put_int(out, secs);
        let _ = out.push(115);         // 's'
    } else {
        df_put_str(out, "fresh");
    }
}

fn df_put_str(out: u8[>..]&, s: const u8[:]) {
    var i: i64 = 0;
    while i < s.len {
        let _ = out.push(s[i]);
        i = i + 1;
    }
}

fn df_put_int(out: u8[>..]&, v: i64) {
    if v == 0 {
        let _ = out.push(48);
        return;
    }
    var tmp: u8[..24] = [0; 24];
    var n: i64 = 0;
    var x = v;
    while x > 0 {
        tmp[n] = (48 + (x % 10)) as u8;
        x = x / 10;
        n = n + 1;
    }
    var i: i64 = 0;
    while i < n {
        let _ = out.push(tmp[n - 1 - i]);
        i = i + 1;
    }
}

fn df_fresh_count(now_ms: i64) -> i64 {
    df_ensure();
    var n: i64 = 0;
    var k: i64 = 1;
    while k <= DF_MAX_KIND {
        if df_verdict(k, now_ms) == DF_FRESH { n = n + 1; }
        k = k + 1;
    }
    return n;
}

fn df_missing_count() -> i64 {
    df_ensure();
    var n: i64 = 0;
    var k: i64 = 1;
    while k <= DF_MAX_KIND {
        if !samples[k].have { n = n + 1; }
        k = k + 1;
    }
    return n;
}
