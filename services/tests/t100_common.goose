// services/tests/t100_common.goose
//
// The shared libraries, driven from the outside: the JSON writer and reader, the sorts, the key
// table, span trimming, UTF-8 validation and hex.
//
// WHY THIS FILE EXISTS
// --------------------
// The census listed eight JSON entry points nothing calls (`json_begin`, `json_kv_str`,
// `json_kv_int`, `json_kv_bool`, `json_end`, `json_find`, `json_bool`, `json_is_null`), all four
// sorts, three table functions, `text_trim`, `utf8_validate` and `hex_value`. These are the
// modules every service is built on, which makes them the worst place for a wrong branch: one
// bad escape in the writer and every record the OS emits is unparseable by anything else.
//
// The writer and the reader are tested against each other on purpose. A writer tested only
// against a hand-written expected string, and a reader tested only against a hand-written input,
// can agree with their authors and disagree with each other.
//
// Status: RUNS — set by `audit_status.py` from the runner's row, not by hand.

import common.json.json;
import common.sort.sort;
import common.table.table;
import common.text.text;
import common.enc.enc;
import common.bytes.bytes;
import common.err.err;
import common.fmt.fmt;
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

fn lit(s: const u8[:], out: u8[>..]&) -> i64 {
    var i: i64 = 0;
    while i < s.len { out.push(s[i]); i = i + 1; }
    return s.len;
}

fn same_len(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn main() {
    say("t100 shared libraries\n");

    // ======================================================================
    // 1. JSON: the writer produces the documented shape, separators included
    // ======================================================================
    const WANT: const u8[:] = "{\"svc\":\"netd\",\"pid\":-7,\"up\":true}";
    var want: u8[>..] = [];
    let wl = lit(WANT, want);

    var doc: u8[>..] = [];
    var ok = json_begin(doc, 256);
    ok = ok && json_kv_str(doc, 256, true, "svc", "netd");
    ok = ok && json_kv_int(doc, 256, false, "pid", -7);
    ok = ok && json_kv_bool(doc, 256, false, "up", true);
    ok = ok && json_end(doc, 256);
    check("json writer: writes an object", ok);
    check("json writer: the exact bytes, commas and all", doc.len == wl && same_len(doc[..], want[..]));

    // `first` is the caller's bookkeeping and the only thing that puts a comma in the right
    // place: the second call must not have one, the third must.
    var two: u8[>..] = [];
    let _ = json_begin(two, 64);
    let _ = json_kv_int(two, 64, true, "a", 1);
    let _ = json_kv_int(two, 64, false, "b", 2);
    let _ = json_end(two, 64);
    var two_want: u8[>..] = [];
    let twl = lit("{\"a\":1,\"b\":2}", two_want);
    check("json writer: separators follow the flag", two.len == twl && same_len(two[..], two_want[..]));

    // A cap that cannot hold the next field fails rather than writing half a document.
    var tiny: u8[>..] = [];
    check("json writer: a cap that cannot hold the field is refused",
          !json_kv_str(tiny, 8, true, "abcdef", "ghijkl"));

    // Escaping: the four escapes that matter, and a control byte that has no short spelling.
    var esc: u8[>..] = [];
    let _ = json_begin(esc, 256);
    let _ = json_kv_str(esc, 256, true, "s", "a\"b\\c\nd\te");
    let _ = json_kv_str(esc, 256, false, "ctl", "x\x01y");
    let _ = json_end(esc, 256);
    var esc_want: u8[>..] = [];
    let ewl = lit("{\"s\":\"a\\\"b\\\\c\\nd\\te\",\"ctl\":\"x\\u0001y\"}", esc_want);
    check("json writer: quote, backslash, newline and tab are escaped",
          esc.len == ewl && same_len(esc[..], esc_want[..]));

    // ======================================================================
    // 2. JSON: the reader reads what the writer wrote
    // ======================================================================
    let j, jc = json_parse(doc[..]);
    check("json_parse: the writer's own output parses", jc == CODE_OK);

    let si = json_find(j, doc[..], "svc");
    var sv: u8[>..] = [];
    let svn, svc = json_str(j, doc[..], si, sv, 64);
    check("json_find: a key is found", si != JSON_NONE);
    check("json_str: the value comes back", svc == CODE_OK && svn == 4 && same_len(sv[..], "netd"[..4]));

    let pi = json_find(j, doc[..], "pid");
    let pv, pscale, pok = json_int(j, pi);
    check("json_int: a negative integer", pok && pv == -7 && pscale == 0);

    let ui = json_find(j, doc[..], "up");
    let ub, ubok = json_bool(j, ui);
    check("json_bool: true is true", ubok && ub);
    check("json_is_null: a boolean is not null", !json_is_null(j, ui));

    check("json_find: a missing key is JSON_NONE", json_find(j, doc[..], "nope") == JSON_NONE);
    // A prefix must not match: "sv" is not "svc".
    check("json_find: a prefix of a key does not match", json_find(j, doc[..], "sv") == JSON_NONE);

    // Out-of-range indices are refused, not read.
    let _, _, bad_int = json_int(j, 999);
    let bad_bool, bad_bool_ok = json_bool(j, 999);
    check("json accessors: an out-of-range index is refused",
          !bad_int && !bad_bool_ok && !bad_bool && !json_is_null(j, 999));

    // A kind mismatch reports "not that kind" instead of a converted value.
    let pv2, pb = json_bool(j, pi);
    check("json_bool: an integer is not a boolean", !pb && !pb && !pv2);

    // Null and false, the two values a truthiness test gets wrong.
    let nulls, nullc = json_parse("{\"a\":null,\"b\":false}"[..20]);
    check("json_parse: null and false parse", nullc == CODE_OK);
    let ai = json_find(nulls, "{\"a\":null,\"b\":false}"[..20], "a");
    let bi = json_find(nulls, "{\"a\":null,\"b\":false}"[..20], "b");
    check("json_is_null: null is null", ai != JSON_NONE && json_is_null(nulls, ai));
    let fb, fbok = json_bool(nulls, bi);
    check("json_bool: false is false, not absent", fbok && !fb);

    // ======================================================================
    // 3. JSON: the round trip through the escaping path
    // ======================================================================
    // The writer escaped the value; the reader must give back the original bytes.
    let ej, ejc = json_parse(esc[..]);
    check("json round trip: the escaped document parses", ejc == CODE_OK);
    let esi = json_find(ej, esc[..], "s");
    var esv: u8[>..] = [];
    let esn, esc_ok = json_str(ej, esc[..], esi, esv, 64);
    var esv_want: u8[>..] = [];
    let eswl = lit("a\"b\\c\nd\te", esv_want);
    check("json round trip: escapes survive the trip",
          esc_ok == CODE_OK && esn == eswl && same_len(esv[..], esv_want[..]));

    // ======================================================================
    // 4. sort: integers, payloads, lookup, and byte strings
    // ======================================================================
    var nums: i64[..64] = [0; 64];
    nums[0] = 5; nums[1] = -3; nums[2] = 5; nums[3] = 0; nums[4] = 42;
    check("sort_i64: sorts", sort_i64(nums, 5, 64) == CODE_OK);
    check("sort_i64: ascending, duplicates kept",
          nums[0] == -3 && nums[1] == 0 && nums[2] == 5 && nums[3] == 5 && nums[4] == 42);
    check("sort_i64: an empty range is not an error", sort_i64(nums, 0, 64) == CODE_OK);
    check("sort_i64: a count past the capacity is refused", sort_i64(nums, 65, 64) == E_INVAL);
    check("sort_i64: a negative count is refused", sort_i64(nums, -1, 64) == E_INVAL);

    var fidx, ffnd = sort_find(nums, 5, 42);
    check("sort_find: finds what is there", ffnd && fidx == 4);
    var fidx2, ffnd2 = sort_find(nums, 5, 7);
    check("sort_find: reports what is not there", !ffnd2);

    var keys: i64[..64] = [0; 64];
    var payload: i64[..64] = [0; 64];
    keys[0] = 3; payload[0] = 300;
    keys[1] = 1; payload[1] = 100;
    keys[2] = 2; payload[2] = 200;
    check("sort_pairs: sorts", sort_pairs(keys, payload, 3, 64) == CODE_OK);
    check("sort_pairs: the payload follows its key",
          keys[0] == 1 && payload[0] == 100 && keys[1] == 2 && payload[1] == 200
          && keys[2] == 3 && payload[2] == 300);

    // Byte-string spans: a directory listing in one buffer.
    var buf: u8[>..] = [];
    let _ = lit("pearapplefig", buf);
    var offs: i64[..64] = [0; 64];
    var lens: i64[..64] = [0; 64];
    offs[0] = 0; lens[0] = 4;      // pear
    offs[1] = 4; lens[1] = 5;      // apple
    offs[2] = 9; lens[2] = 3;      // fig
    check("sort_spans: sorts", sort_spans(offs, lens, 3, buf[..], 64) == CODE_OK);
    check("sort_spans: lexicographic, by content not by position",
          offs[0] == 4 && offs[1] == 9 && offs[2] == 0);
    check("sort_spans: a count past the capacity is refused",
          sort_spans(offs, lens, 65, buf[..], 64) == E_INVAL);

    // ======================================================================
    // 5. table: put, has, get, and a stable walk
    // ======================================================================
    var t = tbl_new();
    let s1, c1 = tbl_put(t, "console", 1);
    let s2, c2 = tbl_put(t, "logd", 2);
    let _, c3 = tbl_put(t, "console", 9);      // overwrite, not a second row
    check("tbl_put: two keys", c1 == CODE_OK && c2 == CODE_OK && c3 == CODE_OK);
    check("tbl_put: an overwrite replaces the value", t.count == 2);
    let v1, f1 = tbl_get(t, "console");
    check("tbl_get: the overwritten value is the new one", f1 && v1 == 9);
    check("tbl_has: a present key", tbl_has(t, "logd"));
    check("tbl_has: an absent key", !tbl_has(t, "time"));
    let _, emptyc = tbl_put(t, "", 0);
    check("tbl_put: an empty key is refused", emptyc == E_INVAL);

    // Walking the table by slot is how it is dumped; the walk must terminate at -1 and copy the
    // key at every slot it hands back.
    var slot = tbl_next_slot(t, 0);
    var seen: i64 = 0;
    var keys_seen: i64 = 0;
    while slot >= 0 {
        var kb: u8[>..] = [];
        if tbl_key_copy(t, slot, kb, 64) { keys_seen = keys_seen + 1; }
        seen = seen + 1;
        slot = tbl_next_slot(t, slot + 1);
    }
    check("tbl_next_slot: the walk finds every row once", seen == 2 && keys_seen == 2);
    var kb2: u8[>..] = [];
    check("tbl_key_copy: an empty slot has no key", !tbl_key_copy(t, 999, kb2, 64));

    // ======================================================================
    // 6. text: trimming a span in place
    // ======================================================================
    var txt: u8[>..] = [];
    let _ = lit("  \t hello world \n ", txt);
    let a, l = text_trim(txt[..], 0, txt.len);
    var trimmed: u8[>..] = [];
    var ti: i64 = a;
    while ti < a + l { trimmed.push(txt[ti]); ti = ti + 1; }
    check("text_trim: trims spaces, tabs and newlines at both ends",
          same_len(trimmed[..], "hello world"[..11]));
    let a2, l2 = text_trim(txt[..], 0, 4);         // all whitespace
    check("text_trim: an all-whitespace span trims to nothing", l2 == 0);
    let a3, l3 = text_trim(txt[..], 5, 2);         // backwards
    check("text_trim: a backwards span is empty, not negative", l3 == 0 && a3 == 5);
    let a4, l4 = text_trim(txt[..], -5, 999);      // out of range both ways
    check("text_trim: out-of-range offsets are clamped", l4 == 11 && a4 == 4);

    // ======================================================================
    // 7. UTF-8: the four invalid shapes the validator exists to refuse
    // ======================================================================
    var ascii: u8[>..] = [];
    let _ = lit("plain", ascii);
    let ap, ac = utf8_validate(ascii[..]);
    check("utf8_validate: ascii is valid", ac == CODE_OK && ap == 5);

    var e2: u8[>..] = [];
    e2.push(0xC3); e2.push(0xA9);                  // e-acute
    let ep, ec = utf8_validate(e2[..]);
    check("utf8_validate: a two-byte sequence is one code point", ec == CODE_OK && ep == 1);

    var overlong: u8[>..] = [];
    overlong.push(0xC0); overlong.push(0x80);      // overlong NUL
    let _, oc = utf8_validate(overlong[..]);
    check("utf8_validate: an overlong form is refused", oc == E_INVAL);

    var surrogate: u8[>..] = [];
    surrogate.push(0xED); surrogate.push(0xA0); surrogate.push(0x80);   // U+D800
    let _, sc = utf8_validate(surrogate[..]);
    check("utf8_validate: a surrogate is refused", sc == E_INVAL);

    var truncated: u8[>..] = [];
    truncated.push(0xE2); truncated.push(0x82);    // three-byte lead, two bytes only
    let _, tc = utf8_validate(truncated[..]);
    check("utf8_validate: a truncated sequence is refused", tc == E_INVAL);

    var beyond: u8[>..] = [];
    beyond.push(0xF5); beyond.push(0x80); beyond.push(0x80); beyond.push(0x80);
    let _, bc = utf8_validate(beyond[..]);
    check("utf8_validate: a lead past U+10FFFF is refused", bc == E_INVAL);

    var lone: u8[>..] = [];
    lone.push(0x80);                               // continuation with no lead
    let _, lc = utf8_validate(lone[..]);
    check("utf8_validate: a lone continuation byte is refused", lc == E_INVAL);

    // The count is what the caller gets to keep even on failure: how much of it was fine.
    let prefix: u8[>..] = [];
    let _ = lit("ab", prefix);
    prefix.push(0xFF);
    let pp, pc = utf8_validate(prefix[..]);
    check("utf8_validate: the valid prefix is counted before the refusal", pc == E_INVAL && pp == 2);

    // ======================================================================
    // 8. hex_value: the one helper the parsers share
    // ======================================================================
    check("hex_value: digits", hex_value('0') == 0 && hex_value('9') == 9);
    check("hex_value: lower and upper", hex_value('a') == 10 && hex_value('F') == 15);
    check("hex_value: not a hex digit", hex_value('g') == -1 && hex_value(' ') == -1);

    say("t100 done  pass=");
    var pb: u8[>..] = [];
    let _ = append_int(pb, 32, t_pass);
    say(pb[..]);
    say(" fail=");
    var fb2: u8[>..] = [];
    let _ = append_int(fb2, 32, t_fail);
    say(fb2[..]);
    say("\n");
    if t_fail > 0 { sys_exit(1); }
}
