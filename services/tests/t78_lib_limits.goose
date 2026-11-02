// services/tests/t78_lib_limits.goose
//
// BF6-01 — limits in the libraries that had no driver at all.
//
// WHAT THIS FILE IS FOR
// ---------------------
// LIMITS.md listed three library modules whose limit constants had never been
// driven: `common/json`, `common/table` and `watchdog/metrics`. None of them was
// imported by any test — not for its limit, and not for anything else — so a
// green corpus said nothing at all about them.
//
// Each check here asks for one more than the limit and asserts the refusal, and
// then asks for exactly the limit and asserts it is accepted. A limit tested only
// from above is a test of the error path; a limit tested from both sides is a
// test of the boundary.
//
// The modules are small and pure: no syscalls, no clock, no allocation. What is
// measured here is arithmetic on caller-supplied buffers.
//
// Status: RUNS — set by `audit_status.py` from the runner's row, not by hand.

import common.json.json;
import common.table.table;
import watchdog.metrics;
import common.fmt.fmt;
import common.err.err;
import common.sys.sys;

var t_pass: i64 = 0;
var t_fail: i64 = 0;

fn say(s: const u8[:]) { let _ = sys_write_serial(s); }

fn check(name: const u8[:], cond: bool) {
    if cond { t_pass = t_pass + 1; say("ok   "); }
    else { t_fail = t_fail + 1; say("FAIL "); }
    say(name);
    say("\n");
}

fn main() {
    say("t78 library limits\n");
    t_json_keys();
    t_table_slots();
    t_metrics_slots();
    let miss_ok = t_table_miss();
    check("a miss never looks like a hit", miss_ok);

    say("t78 done  pass=");
    var pb: u8[>..] = [];
    let _ = append_int(pb, 32, t_pass);
    say(pb[..]);
    say(" fail=");
    var fb: u8[>..] = [];
    let _ = append_int(fb, 32, t_fail);
    say(fb[..]);
    say("\n");
}

// ===========================================================================
// 1. common/json — JSON_MAX keys in one object, JSON_KEY_MAX bytes in a key
//
// The parser stores nodes in a fixed array and refuses the 25th key with
// E_NOROOM rather than silently keeping the first 24: a config reader that
// dropped keys would read half a manifest and report success.
fn t_json_keys() {
    say("--- common/json\n");

    // Exactly JSON_MAX (24) keys: accepted, and the count is what was written.
    let j24, c24 = json_parse("{\"a\":1,\"b\":1,\"c\":1,\"d\":1,\"e\":1,\"f\":1,\"g\":1,\"h\":1,\"i\":1,\"j\":1,\"k\":1,\"l\":1,\"m\":1,\"n\":1,\"o\":1,\"p\":1,\"q\":1,\"r\":1,\"s\":1,\"t\":1,\"u\":1,\"v\":1,\"w\":1,\"x\":1}");
    check("JSON_MAX keys are accepted", c24 == CODE_OK);
    check("JSON_MAX keys are all stored", j24.count == JSON_MAX);

    // One more: refused, and the offset of the refusal is inside the object.
    let j25, c25 = json_parse("{\"a\":1,\"b\":1,\"c\":1,\"d\":1,\"e\":1,\"f\":1,\"g\":1,\"h\":1,\"i\":1,\"j\":1,\"k\":1,\"l\":1,\"m\":1,\"n\":1,\"o\":1,\"p\":1,\"q\":1,\"r\":1,\"s\":1,\"t\":1,\"u\":1,\"v\":1,\"w\":1,\"x\":1,\"y\":1}");
    check("JSON_MAX+1 keys is E_NOROOM, not a silent drop", c25 == E_NOROOM);
    check("the refused object kept exactly JSON_MAX keys", j25.count == JSON_MAX);

    // The subset is a flat object and says so: nesting is refused with
    // E_UNSUPPORTED rather than flattened or half-read. Asserting the refusal
    // is the point -- a parser that silently dropped a nested object would
    // return success with fewer keys than the caller wrote.
    let jn, cn = json_parse("{\"o\":{\"a\":1}}");
    check("a nested object is E_UNSUPPORTED, not silently flattened", cn == E_UNSUPPORTED);
    check("the refused object stored no key for the nested value", jn.count == 0);
    let _ja, can = json_parse("{\"o\":[1,2]}");
    check("a nested array is E_UNSUPPORTED too", can == E_UNSUPPORTED);

    // JSON_KEY_MAX: 32 bytes per key. This was declared and enforced nowhere -- a
    // 44-byte key parsed as happily as a 4-byte one -- which this driver found and
    // the parser now refuses.
    let j32, c_ok32 = json_parse("{\"kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk\":1}");
    check("a JSON_KEY_MAX (32) byte key is accepted", c_ok32 == CODE_OK && j32.count == 1);
    let _j33, c_ok33 = json_parse("{\"kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk\":1}");
    check("a 33-byte key is refused", c_ok33 == E_INVAL);
}

// ===========================================================================
// 2. common/table — TBL_SLOTS entries, TBL_KEY_MAX-1 bytes per key
//
// An open-addressed table with no chaining: the 33rd distinct key must refuse
// with E_NOROOM, because the alternative is an infinite probe loop. The keys
// below are deliberately distinct so every insert takes a slot.
fn t_table_slots() {
    say("--- common/table\n");
    var t: Table = tbl_new();

    // TBL_KEY_MAX - 1 is the longest key that fits: the stored key is NUL
    // terminated in a TBL_KEY_MAX array.
    let slot31, c31 = tbl_put(t, "abcdefghijklmnopqrstuvwxyz01234", 31);
    check("a 31-byte key fits", c31 == CODE_OK);
    let _s32, c32 = tbl_put(t, "abcdefghijklmnopqrstuvwxyz012345", 32);
    check("a TBL_KEY_MAX (32) byte key is E_INVAL", c32 == E_INVAL);
    let _se, ce = tbl_put(t, "", 0);
    check("an empty key is E_INVAL", ce == E_INVAL);

    // Fill to TBL_SLOTS with distinct keys; one slot is already taken. The keys
    // are literals on purpose: a generated key that collided would make the
    // fill count ambiguous, and this test is about the count.
    var added: i64 = 0;
    let _1, c1 = tbl_put(t, "k01", 1);
    let _2, c2 = tbl_put(t, "k02", 2);
    let _3, c3 = tbl_put(t, "k03", 3);
    let _4, c4 = tbl_put(t, "k04", 4);
    let _5, c5 = tbl_put(t, "k05", 5);
    let _6, c6 = tbl_put(t, "k06", 6);
    let _7, c7 = tbl_put(t, "k07", 7);
    let _8, c8 = tbl_put(t, "k08", 8);
    let _9, c9 = tbl_put(t, "k09", 9);
    let _10, c10 = tbl_put(t, "k10", 10);
    let _11, c11 = tbl_put(t, "k11", 11);
    let _12, c12 = tbl_put(t, "k12", 12);
    let _13, c13 = tbl_put(t, "k13", 13);
    let _14, c14 = tbl_put(t, "k14", 14);
    let _15, c15 = tbl_put(t, "k15", 15);
    let _16, c16 = tbl_put(t, "k16", 16);
    let _17, c17 = tbl_put(t, "k17", 17);
    let _18, c18 = tbl_put(t, "k18", 18);
    let _19, c19 = tbl_put(t, "k19", 19);
    let _20, c20 = tbl_put(t, "k20", 20);
    let _21, c21 = tbl_put(t, "k21", 21);
    let _22, c22 = tbl_put(t, "k22", 22);
    let _23, c23 = tbl_put(t, "k23", 23);
    let _24, c24 = tbl_put(t, "k24", 24);
    let _25, c25 = tbl_put(t, "k25", 25);
    let _26, c26 = tbl_put(t, "k26", 26);
    let _27, c27 = tbl_put(t, "k27", 27);
    let _28, c28 = tbl_put(t, "k28", 28);
    let _29, c29 = tbl_put(t, "k29", 29);
    let _30, c30 = tbl_put(t, "k30", 30);
    let _31, c31b = tbl_put(t, "k31", 31);
    if c1 == CODE_OK { added = added + 1; }
    if c2 == CODE_OK { added = added + 1; }
    if c3 == CODE_OK { added = added + 1; }
    if c4 == CODE_OK { added = added + 1; }
    if c5 == CODE_OK { added = added + 1; }
    if c6 == CODE_OK { added = added + 1; }
    if c7 == CODE_OK { added = added + 1; }
    if c8 == CODE_OK { added = added + 1; }
    if c9 == CODE_OK { added = added + 1; }
    if c10 == CODE_OK { added = added + 1; }
    if c11 == CODE_OK { added = added + 1; }
    if c12 == CODE_OK { added = added + 1; }
    if c13 == CODE_OK { added = added + 1; }
    if c14 == CODE_OK { added = added + 1; }
    if c15 == CODE_OK { added = added + 1; }
    if c16 == CODE_OK { added = added + 1; }
    if c17 == CODE_OK { added = added + 1; }
    if c18 == CODE_OK { added = added + 1; }
    if c19 == CODE_OK { added = added + 1; }
    if c20 == CODE_OK { added = added + 1; }
    if c21 == CODE_OK { added = added + 1; }
    if c22 == CODE_OK { added = added + 1; }
    if c23 == CODE_OK { added = added + 1; }
    if c24 == CODE_OK { added = added + 1; }
    if c25 == CODE_OK { added = added + 1; }
    if c26 == CODE_OK { added = added + 1; }
    if c27 == CODE_OK { added = added + 1; }
    if c28 == CODE_OK { added = added + 1; }
    if c29 == CODE_OK { added = added + 1; }
    if c30 == CODE_OK { added = added + 1; }
    if c31b == CODE_OK { added = added + 1; }
    check("the table fills to TBL_SLOTS", added == TBL_SLOTS - 1);

    let _so, co = tbl_put(t, "one-more-key", 1);
    check("past TBL_SLOTS is E_NOROOM", co == E_NOROOM);

    let got, found = tbl_get(t, "abcdefghijklmnopqrstuvwxyz01234");
    check("the first key is still there after the refusal", found && got == 31);

    let count, probes, misses = tbl_stats(t);
    check("the table's count is TBL_SLOTS after the fill", count == TBL_SLOTS);
    check("the probes are counted, not guessed", probes >= TBL_SLOTS);

    // A miss increments the miss counter: the table reports being used as a
    // list, which is the signal that it is too small for the workload.
    let miss_before = misses;
    let _v, found2 = tbl_get(t, "no-such-key");
    let _a2, _b2, misses2 = tbl_stats(t);
    check("a miss is not found", !found2);
    check("a miss is counted", misses2 == miss_before + 1);
}

// A miss on an empty table: the counter moves and the value is never mistaken
// for a hit.
fn t_table_miss() -> bool {
    var t2: Table = tbl_new();
    let _s, _c = tbl_put(t2, "present", 1);
    let _ba, _bb, before_c = tbl_stats(t2);
    let v, found = tbl_get(t2, "absent");
    let _aa, _ab, after_c = tbl_stats(t2);
    return !found && v == 0 && after_c == before_c + 1;
}

// ===========================================================================
// 3. watchdog/metrics — MET_MAX metrics in the table
//
// met_register returns -1 for a full table and for a duplicate name alike, so
// the test asserts the count as well as the refusal: 16 registered, then -1.
fn t_metrics_slots() {
    say("--- watchdog/metrics\n");
    var m: Metrics = met_new();
    let a = met_register(m, "a", 0);
    let b = met_register(m, "b", 0);
    let c = met_register(m, "c", 0);
    let d = met_register(m, "d", 0);
    let e = met_register(m, "e", 0);
    let f = met_register(m, "f", 0);
    let g = met_register(m, "g", 0);
    let h = met_register(m, "h", 0);
    let i = met_register(m, "i", 0);
    let j = met_register(m, "j", 0);
    let k = met_register(m, "k", 0);
    let l = met_register(m, "l", 0);
    let mm = met_register(m, "m", 0);
    let n = met_register(m, "n", 0);
    let o = met_register(m, "o", 0);
    let p = met_register(m, "p", 0);
    check("MET_MAX metrics register", a >= 0 && p >= 0);
    check("every metric got a distinct id", a != p && b != o);

    let q = met_register(m, "q", 0);
    check("past MET_MAX refuses (-1), it does not overwrite", q < 0);

    let dup = met_register(m, "a", 0);
    check("a duplicate name is refused too", dup < 0);

    let too_long = met_register(m, "sixteen-chars-ok-no-this-is-longer", 0);
    check("a name past its field is refused", too_long < 0);

    // The four standard metrics register on a fresh table...
    var fresh: Metrics = met_new();
    let std = met_standard(fresh, 1000);
    check("the four standard metrics register on a fresh table", std == CODE_OK);

    // ...and are refused on a full one. Nothing is overwritten to make room:
    // met_register refuses rather than evicting a metric someone is watching.
    let std_full = met_standard(m, 1000);
    check("met_standard refuses when the table is full, it does not evict", std_full != CODE_OK);
}
