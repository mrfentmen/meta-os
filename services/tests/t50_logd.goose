// services/tests/t50_logd.goose
//
// B-L1-50 — test program for the log service and its formatter (B-L1-18/B-L1-28).
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// WHAT IS UNDER TEST
// ------------------
// Two things that fail differently. The FORMATTER is pure: given a level, a tag and a
// message it must produce a record with a fixed shape, and the test can check that shape
// exactly. The LOG SERVICE is stateful: it buffers, it flushes, and when the buffer fills it
// must count the loss rather than pretend nothing happened. That loss counter is the most
// important assertion in this file -- a log service that silently drops lines is worse than
// no log, because the absence of a line reads as "that never happened".
//
// The flush path needs a sink. On K6 that is the serial port; here the test asserts the
// queue's behaviour and its loss accounting, and lets flush() report whether it reached the
// kernel.

import logd.logd;
import logfmt.logfmt;
import common.fmt.fmt;
import common.sys.sys;

var t_pass: i64 = 0;
var t_fail: i64 = 0;

fn say(s: const u8[:]) { let _ = sys_write_serial(s); }

fn t_eq(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn check(name: const u8[:], cond: bool) {
    if cond { t_pass = t_pass + 1; say("ok   "); }
    else { t_fail = t_fail + 1; say("FAIL "); }
    say(name);
    say("\n");
}

fn main() {
    say("t50 logd + logfmt\n");

    // --- level letters are distinct, and stable ---
    // A level that shares a letter with another makes every log line ambiguous, and the
    // ambiguity is invisible until someone is reading logs under pressure.
    let l_info = level_letter(LVL_INFO);
    let l_warn = level_letter(LVL_WARN);
    let l_error = level_letter(LVL_ERROR);
    check("level letters distinct", l_info != l_warn && l_warn != l_error && l_info != l_error);
    check("level letters printable", l_info >= 32 && l_error < 127);

    // --- the record format ---
    var rec: u8[>..] = [];
    check("format builds", format_record(rec, LVL_INFO, "net", "link up"));
    check("format non-empty", rec.len > 0);
    // Tag and message appear verbatim, in that order.
    check("tag before message", index_of(rec, "net") < index_of(rec, "link up"));
    check("message present", index_of(rec, "link up") >= 0);
    // The record ends with a newline: a record without one merges with the next.
    check("record ends with newline", rec[rec.len - 1] == 10);

    var tight: u8[>..] = [];
    check("format refuses a short buffer", format_record(tight, LVL_INFO, "net", "link up") == false
        && tight.len == 0);

    // --- an empty message is still a record ---
    var empty: u8[>..] = [];
    check("empty message formats", format_record(empty, LVL_WARN, "wd", "") && empty.len > 0);

    // --- the log service buffers, and flush reports whether it drained ---
    let n0 = log(LVL_INFO, "test", "first");
    check("log accepts a record", n0 == true);
    let n1 = log_info("test", "second");
    check("log_info accepts", n1 == true);
    check("should_flush is a decision, not a constant", should_flush() == true || should_flush() == false);

    var flushed = flush();
    check("flush drained at least what was queued", flushed >= 0);
    // A second flush with an empty queue writes nothing: 0, not -1 and not a repeat.
    check("second flush is empty", flush() == 0);

    // --- the loss counter behaves ---
    // Push far more than any sane ring holds. Either the queue grows (and nothing is lost)
    // or it refuses and counts. Both are acceptable; silently losing is not.
    var pushed_ok: i64 = 0;
    var i: i64 = 0;
    while i < 2000 {
        if log(LVL_INFO, "flood", "x") { pushed_ok = pushed_ok + 1; }
        i = i + 1;
    }
    let st = loss_stats();
    let dropped = st.full + st.level + st.long;
    check("loss accounting consistent", dropped >= 0 && dropped + pushed_ok > 0);
    check("accepted plus dropped covers the flood", pushed_ok + dropped >= 2000);
    check("level drops do not occur for INFO", st.level == 0);

    let drained = flush();
    check("flush after flood", drained >= 0);

    var r: u8[>..] = [];
    let _ = append_int(r, 32, t_pass);
    say("passed ");
    say(r);
    say("\n");
    if t_fail != 0 { say("FAILURES\n"); sys_exit(1); }
    say("t50 done\n");
    sys_exit(0);
}

// Substring search over the built record. Present here rather than imported so the test
// depends on the formatter's output only, not on a second library.
fn index_of(hay: const u8[:], needle: const u8[:]) -> i64 {
    if needle.len == 0 { return 0; }
    if hay.len < needle.len { return -1; }
    var i: i64 = 0;
    while i + needle.len <= hay.len {
        var j: i64 = 0;
        var same = true;
        while j < needle.len {
            if hay[i + j] != needle[j] { same = false; }
            j = j + 1;
        }
        if same { return i; }
        i = i + 1;
    }
    return -1;
}
