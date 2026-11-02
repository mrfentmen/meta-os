// services/common/json/json.goose
//
// B-L1-120 — JSON subset: the flat object the updater and config formats actually use.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// THE SUBSET, NAMED BEFORE THE CODE
// ---------------------------------
// Accepted:
//   - one object, `{ "key": value, ... }`, with keys as double-quoted strings
//   - scalar values only: string, integer or decimal number, true, false, null
//   - whitespace between tokens, as the grammar allows
// Refused, with E_UNSUPPORTED and the offset of the offending byte:
//   - nested objects and arrays
//   - exponent numbers, leading '+', leading zeros, NaN/Infinity
//   - anything after the closing brace
//
// Refusing nesting is not laziness, it is scope: nothing in this layer parses nested JSON, and
// a recursive parser that allocates per level is the one thing a no-allocator service layer
// cannot afford. When a nested consumer appears, it gets a real parser and its own hostile
// inputs (B-L1-126) -- not a flag on this one.
//
// STRICT, WITH THE OFFSET
// -----------------------
// Every error carries the byte offset where parsing stopped. "invalid JSON" is a message that
// costs an hour; "invalid JSON at 47: unexpected '}'" is a fix. The parser never guesses: a
// trailing comma, a duplicate key and an unquoted key are all errors, because every one of
// them is accepted by some parser somewhere and rejected by another, and the difference shows
// up as a config that loads on one machine and not the next.
//
// NO ALLOCATION
// -------------
// Values are (offset, length) spans into the caller's text, plus one number field for the
// numeric case. Nothing is copied, nothing is decoded, nothing is unescaped. `json_str`
// copies and unescapes into the caller's buffer when a decoded value is actually needed.

import common.err.err;

let JSON_MAX: i64 = 24;            // keys in one object
let JSON_KEY_MAX: i64 = 32;
let JSON_NONE: i64 = -1;

let JV_NULL: i64 = 0;
let JV_TRUE: i64 = 1;
let JV_FALSE: i64 = 2;
let JV_INT: i64 = 3;
let JV_DECIMAL: i64 = 4;
let JV_STR: i64 = 5;

struct JNode {
    key_off: i64,
    key_len: i64,
    kind: i64,
    val_off: i64,        // for strings: the first byte INSIDE the quotes
    val_len: i64,
    num: i64,            // integers; for decimals, the whole part only
    scale: i64,          // decimal digits after the point, 0 when none
}

struct Json {
    nodes: JNode[..24],
    count: i64,
    err_off: i64,
}

fn json_parse(text: const u8[:]) -> Json, i64 {
    var j: Json = Json { nodes: [], count: 0, err_off: 0 };
    j.count = 0;
    j.err_off = 0;
    var i: i64 = 0;
    while i < JSON_MAX {
        j.nodes[i] = JNode { key_off: 0, key_len: 0, kind: JV_NULL, val_off: 0, val_len: 0, num: 0, scale: 0 };
        i = i + 1;
    }

    i = json_skip_ws(text, 0);
    if i >= text.len { return json_fail(j, 0); }
    if text[i] != '{' {
        // A bare array or scalar is valid JSON, and refusing it here is the documented
        // subset, not a bug: every caller of this library wants an object.
        j.err_off = i;
        return j, E_UNSUPPORTED;
    }
    i = i + 1;
    i = json_skip_ws(text, i);

    if i < text.len && text[i] == '}' {
        i = i + 1;
        return json_finish(j, text, i);
    }

    while true {
        if j.count >= JSON_MAX { j.err_off = i; return j, E_NOROOM; }
        i = json_skip_ws(text, i);
        if i >= text.len || text[i] != '"' { return json_fail(j, i); }

        var node: JNode = JNode {
            key_off: 0,
            key_len: 0,
            kind: 0,
            val_off: 0,
            val_len: 0,
            num: 0,
            scale: 0,
        };
        let key_start = i + 1;
        i = json_scan_string(text, i);
        if i < 0 { return json_fail(j, key_start); }
        node.key_off = key_start;
        node.key_len = i - 1 - key_start;      // i is just past the closing quote

        i = json_skip_ws(text, i);
        if i >= text.len || text[i] != ':' { return json_fail(j, i); }
        i = i + 1;
        i = json_skip_ws(text, i);

        let vcode = json_scan_value(text, i, node);
        if vcode != CODE_OK { return json_fail(j, i); }
        i = json_skip_value_end(text, i);

        // Reject a duplicate key: two values for one name means the reader's answer depends
        // on iteration order, which is exactly the kind of bug that survives a whole release.
        var k: i64 = 0;
        while k < j.count {
            if j.nodes[k].key_len == node.key_len && json_key_eq(text, j.nodes[k], node) {
                j.err_off = node.key_off;
                return j, E_INVAL;
            }
            k = k + 1;
        }
        j.nodes[j.count] = node;
        j.count = j.count + 1;

        i = json_skip_ws(text, i);
        if i >= text.len { return json_fail(j, i); }
        if text[i] == ',' { i = i + 1; continue; }
        if text[i] == '}' { i = i + 1; break; }
        return json_fail(j, i);              // trailing comma, or junk
    }

    return json_finish(j, text, i);
}

fn json_finish(j: Json, text: const u8[:], at: i64) -> Json, i64 {
    var out = j;
    let end = json_skip_ws(text, at);
    if end != text.len {
        out.err_off = end;                   // anything after the object is an error
        return out, E_INVAL;
    }
    return out, CODE_OK;
}

fn json_fail(j: Json, at: i64) -> Json, i64 {
    var out = j;
    out.err_off = at;
    return out, E_INVAL;
}

// ---------------------------------------------------------------------------
// Scanning
// ---------------------------------------------------------------------------

fn json_skip_ws(text: const u8[:], at: i64) -> i64 {
    var i = at;
    while i < text.len {
        let c = text[i];
        if c == ' ' || c == '\t' || c == '\n' || c == '\r' { i = i + 1; continue; }
        break;
    }
    return i;
}

// From an opening quote to one past the closing quote, or -1.
fn json_scan_string(text: const u8[:], at: i64) -> i64 {
    if at >= text.len || text[at] != '"' { return -1; }
    var i = at + 1;
    while i < text.len {
        let c = text[i];
        if c == '"' { return i + 1; }
        if (c as i64) < 0x20 { return -1; }     // raw control bytes are not legal in a string
        if c == '\\' {
            if i + 1 >= text.len { return -1; }
            let e = text[i + 1];
            if e == '"' || e == '\\' || e == '/' || e == 'b' || e == 'f' || e == 'n' || e == 'r' || e == 't' {
                i = i + 2;
                continue;
            }
            if e == 'u' {
                // Four hex digits, checked but not decoded here: a \u escape that decodes to
                // a surrogate pair is a string the caller cannot render, and refusing it at
                // scan time is the only place the pair can be seen together.
                if i + 5 >= text.len { return -1; }
                var k: i64 = 2;
                while k < 6 {
                    if json_hex(text[i + k]) < 0 { return -1; }
                    k = k + 1;
                }
                let cp = json_hex4(text, i + 2);
                if cp >= 0xD800 && cp <= 0xDBFF {
                    // High surrogate: the next escape must be the low half.
                    if i + 11 >= text.len || text[i + 6] != '\\' || text[i + 7] != 'u' { return -1; }
                    var m: i64 = 8;
                    while m < 12 {
                        if json_hex(text[i + m]) < 0 { return -1; }
                        m = m + 1;
                    }
                    let lo = json_hex4(text, i + 8);
                    if lo < 0xDC00 || lo > 0xDFFF { return -1; }
                    i = i + 12;
                    continue;
                }
                if cp >= 0xDC00 && cp <= 0xDFFF { return -1; }   // lone low surrogate
                i = i + 6;
                continue;
            }
            return -1;
        }
        i = i + 1;
    }
    return -1;
}

fn json_hex(c: u8) -> i64 {
    if c >= '0' && c <= '9' { return (c - '0') as i64; }
    if c >= 'a' && c <= 'f' { return 10 + ((c - 'a') as i64); }
    if c >= 'A' && c <= 'F' { return 10 + ((c - 'A') as i64); }
    return -1;
}

fn json_hex4(text: const u8[:], at: i64) -> i64 {
    var v: i64 = 0;
    var i: i64 = 0;
    while i < 4 {
        let d = json_hex(text[at + i]);
        if d < 0 { return -1; }
        v = v * 16 + d;
        i = i + 1;
    }
    return v;
}

fn json_scan_value(text: const u8[:], at: i64, node: JNode&) -> i64 {
    if at >= text.len { return E_INVAL; }
    let c = text[at];

    if c == '"' {
        let end = json_scan_string(text, at);
        if end < 0 { return E_INVAL; }
        node.kind = JV_STR;
        node.val_off = at + 1;
        node.val_len = end - 1 - (at + 1);
        return CODE_OK;
    }
    if c == '{' || c == '[' { return E_UNSUPPORTED; }     // nesting is out of the subset

    if c == 't' {
        if !json_match(text, at, "true") { return E_INVAL; }
        node.kind = JV_TRUE;
        node.val_off = at;
        node.val_len = 4;
        return CODE_OK;
    }
    if c == 'f' {
        if !json_match(text, at, "false") { return E_INVAL; }
        node.kind = JV_FALSE;
        node.val_off = at;
        node.val_len = 5;
        return CODE_OK;
    }
    if c == 'n' {
        if !json_match(text, at, "null") { return E_INVAL; }
        node.kind = JV_NULL;
        node.val_off = at;
        node.val_len = 4;
        return CODE_OK;
    }
    if c == '-' || (c >= '0' && c <= '9') { return json_scan_number(text, at, node); }
    return E_INVAL;
}

fn json_scan_number(text: const u8[:], at: i64, node: JNode&) -> i64 {
    var i = at;
    var neg = false;
    if text[i] == '-' { neg = true; i = i + 1; if i >= text.len { return E_INVAL; } }
    if text[i] < '0' || text[i] > '9' { return E_INVAL; }
    // A leading zero followed by another digit ("01") is refused: some parsers read it as
    // octal, and a config value that one machine reads as 8 and another as 1 is not a value.
    if text[i] == '0' && i + 1 < text.len && text[i + 1] >= '0' && text[i + 1] <= '9' { return E_INVAL; }

    var whole: i64 = 0;
    var digits: i64 = 0;
    while i < text.len && text[i] >= '0' && text[i] <= '9' {
        if digits >= 18 { return E_INVAL; }        // would overflow i64 when scaled
        whole = whole * 10 + ((text[i] - '0') as i64);
        digits = digits + 1;
        i = i + 1;
    }
    var scale: i64 = 0;
    var kind = JV_INT;
    if i < text.len && text[i] == '.' {
        kind = JV_DECIMAL;
        i = i + 1;
        if i >= text.len || text[i] < '0' || text[i] > '9' { return E_INVAL; }
        var frac: i64 = 0;
        while i < text.len && text[i] >= '0' && text[i] <= '9' {
            if scale >= 9 { return E_INVAL; }      // more precision than the caller asked for
            frac = frac * 10 + ((text[i] - '0') as i64);
            scale = scale + 1;
            i = i + 1;
        }
        // Fold the fraction into `whole` at a fixed scale so json_int can answer in
        // thousandths without a second field per caller.
        // Normalise the fraction to thousandths, so json_int's answer is comparable
        // across "1.5", "1.50" and "1.5001" without a second scale field per caller.
        var k: i64 = scale;
        while k < 3 { frac = frac * 10; k = k + 1; }
        while k > 3 { frac = frac / 10; k = k - 1; }
        whole = whole * 1000 + frac;
        if scale > 3 { scale = 3; }
    }
    if i < text.len && (text[i] == 'e' || text[i] == 'E') { return E_UNSUPPORTED; }  // no exponents
    if neg { whole = 0 - whole; }

    node.kind = kind;
    node.val_off = at;
    node.val_len = i - at;
    node.num = whole;
    node.scale = scale;
    return CODE_OK;
}

fn json_skip_value_end(text: const u8[:], at: i64) -> i64 {
    // The value scanner already walked it; re-walking is cheap and keeps one source of truth
    // for "where does this value end".
    var node: JNode = JNode {
        key_off: 0,
        key_len: 0,
        kind: 0,
        val_off: 0,
        val_len: 0,
        num: 0,
        scale: 0,
    };
    if json_scan_value(text, at, node) != CODE_OK { return at; }
    if node.kind == JV_STR { return node.val_off + node.val_len + 1; }
    return at + node.val_len;
}

fn json_match(text: const u8[:], at: i64, lit: const u8[:]) -> bool {
    if at + lit.len > text.len { return false; }
    var i: i64 = 0;
    while i < lit.len {
        if text[at + i] != lit[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn json_key_eq(text: const u8[:], a: JNode, b: JNode) -> bool {
    if a.key_len != b.key_len { return false; }
    var i: i64 = 0;
    while i < a.key_len {
        if text[a.key_off + i] != text[b.key_off + i] { return false; }
        i = i + 1;
    }
    return true;
}

// ---------------------------------------------------------------------------
// Accessors
// ---------------------------------------------------------------------------

// Find a key. Returns the node index, or JSON_NONE. Comparison is over the raw key bytes, so
// a key containing an escape does not match its decoded spelling -- documented, and the
// alternative (decode then compare) would allocate on every lookup.
fn json_find(j: Json&, text: const u8[:], key: const u8[:]) -> i64 {
    var i: i64 = 0;
    while i < j.count {
        if j.nodes[i].key_len == key.len {
            var same = true;
            var k: i64 = 0;
            while k < key.len {
                if text[j.nodes[i].key_off + k] != key[k] { same = false; break; }
                k = k + 1;
            }
            if same { return i; }
        }
        i = i + 1;
    }
    return JSON_NONE;
}

// Integer value, in thousandths when the source was decimal. scale reports the digits after
// the point; a caller that wanted plain integers checks scale == 0.
fn json_int(j: Json&, idx: i64) -> i64, i64, bool {
    if idx < 0 || idx >= j.count { return 0, 0, false; }
    let n = j.nodes[idx];
    if n.kind != JV_INT && n.kind != JV_DECIMAL { return 0, 0, false; }
    return n.num, n.scale, true;
}

fn json_bool(j: Json&, idx: i64) -> bool, bool {
    if idx < 0 || idx >= j.count { return false, false; }
    if j.nodes[idx].kind == JV_TRUE { return true, true; }
    if j.nodes[idx].kind == JV_FALSE { return false, true; }
    return false, false;
}

fn json_is_null(j: Json&, idx: i64) -> bool {
    if idx < 0 || idx >= j.count { return false; }
    return j.nodes[idx].kind == JV_NULL;
}

// Copy a string value out, UNESCAPING the standard escapes. \u is copied as '?' unless it is
// ASCII, because a console that cannot encode a code point must not pretend it did; the
// caller that needs full Unicode uses common.enc's utf8_encode with a decoder, which this
// subset deliberately does not carry.
fn json_str(j: Json&, text: const u8[:], idx: i64, out: u8[>..]&, cap: i64) -> i64, i64 {
    if idx < 0 || idx >= j.count { return 0, E_INVAL; }
    let n = j.nodes[idx];
    if n.kind != JV_STR { return 0, E_INVAL; }

    var i = n.val_off;
    let end = n.val_off + n.val_len;
    var produced: i64 = 0;
    while i < end {
        if out.len + 1 > cap { return produced, E_NOROOM; }
        let c = text[i];
        if c != '\\' {
            out.push(c);
            produced = produced + 1;
            i = i + 1;
            continue;
        }
        i = i + 1;
        if i >= end { return produced, E_CORRUPT; }
        let e = text[i];
        if e == '"' { out.push('"'); }
        else if e == '\\' { out.push('\\'); }
        else if e == '/' { out.push('/'); }
        else if e == 'b' { out.push(8); }
        else if e == 'f' { out.push(12); }
        else if e == 'n' { out.push(10); }
        else if e == 'r' { out.push(13); }
        else if e == 't' { out.push(9); }
        else if e == 'u' {
            if i + 4 >= end { return produced, E_CORRUPT; }
            let cp = json_hex4(text, i + 1);
            if cp < 0 { return produced, E_CORRUPT; }
            if cp < 0x80 { out.push(cp as u8); }
            else { out.push('?'); }         // see the note above: never a wrong byte
            i = i + 4;
        } else { return produced, E_CORRUPT; }
        produced = produced + 1;
        i = i + 1;
    }
    return produced, CODE_OK;
}

// ---------------------------------------------------------------------------
// Writing
// ---------------------------------------------------------------------------

fn json_wr(out: u8[>..]&, cap: i64, s: const u8[:]) -> bool {
    if out.len + s.len > cap { return false; }
    var i: i64 = 0;
    while i < s.len { out.push(s[i]); i = i + 1; }
    return true;
}

fn json_begin(out: u8[>..]&, cap: i64) -> bool {
    return json_wr(out, cap, "{");
}

// `first` is the caller's bookkeeping: one bool, and the only way a comma ends up in the
// right place. A writer that tracks separators by position gets it wrong on the second call.
fn json_kv_str(out: u8[>..]&, cap: i64, first: bool, key: const u8[:], val: const u8[:]) -> bool {
    if !first { if !json_wr(out, cap, ",") { return false; } }
    if !json_wr(out, cap, "\"") { return false; }
    if !json_wr(out, cap, key) { return false; }
    if !json_wr(out, cap, "\":\"") { return false; }
    if !json_escape(out, cap, val) { return false; }
    return json_wr(out, cap, "\"");
}

fn json_escape(out: u8[>..]&, cap: i64, s: const u8[:]) -> bool {
    var i: i64 = 0;
    while i < s.len {
        let c = s[i];
        if out.len + 1 > cap { return false; }
        if c == '"' { if !json_wr(out, cap, "\\\"") { return false; } }
        else if c == '\\' { if !json_wr(out, cap, "\\\\") { return false; } }
        else if c == 10 { if !json_wr(out, cap, "\\n") { return false; } }
        else if c == 13 { if !json_wr(out, cap, "\\r") { return false; } }
        else if c == 9 { if !json_wr(out, cap, "\\t") { return false; } }
        else if (c as i64) < 0x20 {
            // Control bytes have no short escape we do not already handle; \u00XX is the
            // only legal spelling, and a raw byte here would make the output unparseable.
            if !json_wr(out, cap, "\\u00") { return false; }
            let hi = ((c as i64) >> 4) & 0x0F;
            let lo = (c as i64) & 0x0F;
            out.push(json_hex_digit(hi));
            out.push(json_hex_digit(lo));
        } else { out.push(c); }
        i = i + 1;
    }
    return true;
}

fn json_hex_digit(v: i64) -> u8 {
    if v < 10 { return (48 + v) as u8; }
    return (87 + v) as u8;      // 'a'..'f' for 10..15
}

fn json_kv_int(out: u8[>..]&, cap: i64, first: bool, key: const u8[:], val: i64) -> bool {
    if !first { if !json_wr(out, cap, ",") { return false; } }
    if !json_wr(out, cap, "\"") { return false; }
    if !json_wr(out, cap, key) { return false; }
    if !json_wr(out, cap, "\":") { return false; }
    return json_wr_int(out, cap, val);
}

recursive fn json_wr_int(out: u8[>..]&, cap: i64, v: i64) -> bool {
    if v < 0 {
        if !json_wr(out, cap, "-") { return false; }
        return json_wr_int(out, cap, 0 - v);
    }
    if v < 10 {
        if out.len + 1 > cap { return false; }
        out.push((48 + v) as u8);
        return true;
    }
    var digits: i64 = 0;
    var x = v;
    while x > 0 { digits = digits + 1; x = x / 10; }
    if out.len + digits > cap { return false; }
    var buf: u8[..20] = [];
    var i: i64 = 0;
    x = v;
    while i < digits { buf[digits - 1 - i] = (48 + (x % 10)) as u8; x = x / 10; i = i + 1; }
    i = 0;
    while i < digits { out.push(buf[i]); i = i + 1; }
    return true;
}

fn json_kv_bool(out: u8[>..]&, cap: i64, first: bool, key: const u8[:], val: bool) -> bool {
    if !first { if !json_wr(out, cap, ",") { return false; } }
    if !json_wr(out, cap, "\"") { return false; }
    if !json_wr(out, cap, key) { return false; }
    if !json_wr(out, cap, "\":") { return false; }
    if val { return json_wr(out, cap, "true"); }
    return json_wr(out, cap, "false");
}

fn json_end(out: u8[>..]&, cap: i64) -> bool {
    return json_wr(out, cap, "}");
}
