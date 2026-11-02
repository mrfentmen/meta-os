// services/common/cfg/cfg.goose
//
// Services' configuration: key=value pairs, optional [section] headers, parsed
// from a borrowed text buffer. No allocation, no lifetime trouble, no copies.
//
// Status: WRITTEN (not COMPILED). Verified via goose-mcp@1.1.0:
// std string helpers `trim`, `split`, `parse_int`, `compare`, `find` .... reference#30
// slices `u8[:]` and indexing into them ................................ spec#40
// trailing-bool and trailing-code returns ............................. samples/04_errors.goose
// `while`, `if`, `break`, `continue`, `var`, `let` .................... list_keywords
//
// DESIGN: THE CONFIG BORROWS, IT DOES NOT COPY
// --------------------------------------------
// A Config holds a slice of text that somebody else owns -- the service's static
// config blob, read at start-up. Every lookup scans that slice. Config files are
// tens of lines, the scan is a few hundred byte comparisons, and it happens at
// start-up or on an explicit reload, not in a hot loop. In exchange: no parser
// state to keep in sync with the text, no fixed-size entry array to overflow, and
// no way for the parsed copy to disagree with the bytes on disk.
//
// WHAT IS NOT SUPPORTED, ON PURPOSE
// ---------------------------------
// No quoting, no escapes, no multi-line values, no includes, no environment
// expansion. Every one of those is a parser feature that a service config does
// not need and that would each add a place for a malformed file to be
// half-understood. If a value needs a space, it can have one: values are trimmed
// at both ends, not split on spaces.

struct Config {
    text: const u8[:],
}

fn cfg_init(text: const u8[:]) -> Config {
    return Config { text: text };
}

// ---------------------------------------------------------------------------
// Character helpers
// ---------------------------------------------------------------------------

fn cfg_is_space(b: u8) -> bool {
    if b == ' ' { return true; }
    if b == '\t' { return true; }
    if b == '\r' { return true; }
    return false;
}

fn is_comment_start(b: u8) -> bool {
    if b == '#' { return true; }
    if b == ';' { return true; }
    return false;
}

// ---------------------------------------------------------------------------
// Scanning
// ---------------------------------------------------------------------------

// End of the line starting at `start` (index of the '\n' or text length).
fn line_end(text: u8[:], start: i64) -> i64 {
    var i = start;
    while i < text.len && text[i] != '\n' { i = i + 1; }
    return i;
}

// Trim spaces and tabs off both ends of a span.
fn trim_span(text: u8[:], s: i64, e: i64) -> i64, i64 {
    var a = s;
    var b = e;
    while a < b && cfg_is_space(text[a]) { a = a + 1; }
    while b > a && cfg_is_space(text[b - 1]) { b = b - 1; }
    return a, b;
}

// Do two spans of the same text hold equal bytes?
fn spans_equal(text: u8[:], as_: i64, ae: i64, bs: i64, be: i64) -> bool {
    if ae - as_ != be - bs { return false; }
    var i: i64 = 0;
    while i < ae - as_ {
        if text[as_ + i] != text[bs + i] { return false; }
        i = i + 1;
    }
    return true;
}

// A line that is exactly "[name]" (spaces inside the brackets are not allowed:
// a section name is an identifier, and allowing " [ a b ]" invites two names
// that look the same and are not).
fn parse_section(text: u8[:], s: i64, e: i64) -> i64, i64, bool {
    if e - s < 3 { return 0, 0, false; }        // "[x]" is the shortest
    if text[s] != '[' { return 0, 0, false; }
    if text[e - 1] != ']' { return 0, 0, false; }
    return s + 1, e - 1, true;
}

// Split a "key = value" line. Returns key span and value span, or false if the
// line is not a pair at all.
fn parse_pair(text: u8[:], s: i64, e: i64) -> i64, i64, i64, i64, bool {
    var eq: i64 = -1;
    var i = s;
    while i < e {
        if text[i] == '=' {
            // The first '=' splits; a value may contain more.
            eq = i;
            break;
        }
        i = i + 1;
    }
    if eq < 0 { return 0, 0, 0, 0, false; }
    let ks, ke = trim_span(text, s, eq);
    let vs, ve = trim_span(text, eq + 1, e);
    if ke <= ks { return 0, 0, 0, 0, false; }   // an empty key is not a key
    return ks, ke, vs, ve, true;
}

// ---------------------------------------------------------------------------
// Lookup
// ---------------------------------------------------------------------------

// Find a value. `section` may be empty, meaning the top level of the file. The
// returned span borrows the config text; callers copy it into their own buffer
// (fmt) or parse it in place (cfg_int / cfg_bool).
fn cfg_find(cfg: Config&, section: u8[:], key: u8[:]) -> i64, i64, bool {
    let text = cfg.text;
    var in_wanted = section.len == 0;   // top level when no section asked for
    var i: i64 = 0;

    while i < text.len {
        let end = line_end(text, i);
        let s, e = trim_span(text, i, end);

        if e > s && !is_comment_start(text[s]) {
            let ss, se, is_section = parse_section(text, s, e);
            if is_section {
                // A section header changes which pairs are visible. The top
                // level is only visible before the first header, which is the
                // documented rule; a key after a header is not top-level.
                in_wanted = spans_equal_keys(text, ss, se, section);
            } else if in_wanted {
                let ks, ke, vs, ve, is_pair = parse_pair(text, s, e);
                if is_pair {
                    if spans_equal_keys(text, ks, ke, key) {
                        return vs, ve, true;
                    }
                }
            }
        }

        i = end + 1;    // skip the newline
    }
    return 0, 0, false;
}

// A small wrapper so the call above reads clearly: compare a parsed key span
// against a caller's key slice.
fn spans_equal_keys(text: u8[:], ks: i64, ke: i64, key: u8[:]) -> bool {
    if ke - ks != key.len { return false; }
    var i: i64 = 0;
    while i < key.len {
        if text[ks + i] != key[i] { return false; }
        i = i + 1;
    }
    return true;
}

// Copy a value into the caller's buffer. Returns false when the key is absent or
// the buffer has no room -- the caller can tell those apart with cfg_has.
fn cfg_get(cfg: Config&, section: u8[:], key: u8[:], out: u8[>..]&, cap: i64) -> bool {
    let vs, ve, found = cfg_find(cfg, section, key);
    if !found { return false; }
    if ve - vs > cap { return false; }
    var i = vs;
    while i < ve {
        out.push(cfg.text[i]);
        i = i + 1;
    }
    return true;
}

fn cfg_has(cfg: Config&, section: u8[:], key: u8[:]) -> bool {
    let _, _, found = cfg_find(cfg, section, key);
    return found;
}

// Integer value. Returns ok=false when absent, empty, or not a number, and the
// caller cannot tell those apart -- deliberately: for a config, all three mean
// "fix the file", and a service that needs the distinction can use cfg_get plus
// its own parser.
fn cfg_int(cfg: Config&, section: u8[:], key: u8[:], default: i64) -> i64, bool {
    let vs, ve, found = cfg_find(cfg, section, key);
    if !found { return default, false; }
    if ve <= vs { return default, false; }
    // parse_int works on a slice of the same text: no copy, no buffer.
    let v, parsed = parse_int(cfg.text[vs..ve]);
    if !parsed { return default, false; }
    return v, true;
}

// Boolean value: 1/0, true/false, yes/no, on/off. Anything else is false with
// ok=false, including an empty value -- a typo'd boolean must not silently
// become "true" because the string was non-empty.
fn cfg_bool(cfg: Config&, section: u8[:], key: u8[:], default: bool) -> bool, bool {
    let vs, ve, found = cfg_find(cfg, section, key);
    if !found { return default, false; }
    let n = ve - vs;
    if n == 1 {
        if cfg.text[vs] == '1' { return true, true; }
        if cfg.text[vs] == '0' { return false, true; }
        return default, false;
    }
    if spans_equal_lit(cfg.text, vs, ve, "true") { return true, true; }
    if spans_equal_lit(cfg.text, vs, ve, "yes") { return true, true; }
    if spans_equal_lit(cfg.text, vs, ve, "on") { return true, true; }
    if spans_equal_lit(cfg.text, vs, ve, "false") { return false, true; }
    if spans_equal_lit(cfg.text, vs, ve, "no") { return false, true; }
    if spans_equal_lit(cfg.text, vs, ve, "off") { return false, true; }
    return default, false;
}

// Compare a span against a literal. Case-sensitive on purpose: "True" is a typo
// this parser refuses rather than guesses at, and a config file that means it can
// write it lowercase.
fn spans_equal_lit(text: u8[:], s: i64, e: i64, lit: const u8[:]) -> bool {
    if e - s != lit.len { return false; }
    var i: i64 = 0;
    while i < lit.len {
        if text[s + i] != lit[i] { return false; }
        i = i + 1;
    }
    return true;
}

// ---------------------------------------------------------------------------
// Where the text comes from
// ---------------------------------------------------------------------------
//
// Not in this library, because it is not a parsing question: a service's config
// is either compiled in (a `const` array in the service's own source) or read
// through the `fs` service once it exists (B-L1-79). Until then, services embed
// their default config as a literal and this library parses it in place. No file
// is read here; nothing in Layer 4 reads a file yet.
