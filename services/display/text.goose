// services/display/text.goose
//
// B-L1-112 — Display text helpers: wrapping, clipping, and scroll regions.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// WHY THESE ARE PURE FUNCTIONS
// ----------------------------
// display.goose owns the virtual consoles and moves a cursor. Everything in this file
// answers a question about *text and a width* and touches nothing: which spans of a string
// fit on which line, what a clipped fragment looks like, which row a scroll region covers.
// That is what makes it testable without a framebuffer, and it is the difference between a
// console that wraps sensibly and one that wraps "however the loop happened to be written".
//
// BYTES TODAY, COLUMNS TOMORROW
// -----------------------------
// Width here is bytes, because the framebuffer contract in K2 is one byte per cell. When
// the display learns UTF-8, the callers swap in common.enc's utf8_columns and the span
// arithmetic stays identical -- which is exactly why wrapping returns spans (offsets into
// the caller's string) and not copies. A copy-based wrapper would have to be rewritten.
//
// NO ALLOCATION, NO HIDDEN BUFFER
// -------------------------------
// A wrapped line is (offset, length) into the string the caller already has. Sixteen lines
// per call is the cap; a caller that needs more wraps in chunks and says so.

let WRAP_MAX_LINES: i64 = 16;
let ELLIPSIS: const u8[:] = "...";

struct Span {
    off: i64,
    len: i64,
}

struct LineList {
    spans: Span[..16] = [Span { .. }; 16],
    count: i64,
    overflow: bool,     // more lines existed than WRAP_MAX_LINES: the caller got a prefix
}

// ---------------------------------------------------------------------------
// Wrapping
// ---------------------------------------------------------------------------

// Greedy wrap at `width` bytes, preferring the last space before the limit.
//
// The three decisions that make wrapping look right and are usually gotten wrong:
//   1. A word longer than the width is broken at the width, not emitted at full length.
//      A console that lets one long token run past the edge loses the rest of the line.
//   2. The space at a break is consumed, not carried to the start of the next line. Leading
//      spaces on continuation lines are the classic "wrapped text is indented" bug.
//   3. A newline in the input starts a new span and is itself consumed. Nothing downstream
//      has to know that '\n' exists.
//
// width <= 0 returns an empty list with overflow=false, which the caller can tell apart
// from "the text did not fit".
fn text_wrap(s: const u8[:], width: i64) -> LineList {
    var out: LineList = LineList { spans: [], count: 0, overflow: false };
    out.count = 0;
    out.overflow = false;
    var i: i64 = 0;
    while i < WRAP_MAX_LINES { out.spans[i] = Span { off: 0, len: 0 }; i = i + 1; }
    if width <= 0 { return out; }
    if s.len == 0 { return out; }        // no text, no lines

    var start: i64 = 0;
    var at: i64 = 0;
    var n: i64 = 0;
    while at <= s.len {
        let at_end = at == s.len;
        let is_nl = !at_end && s[at] == '\n';
        if !at_end && !is_nl && (at - start) < width {
            at = at + 1;
            continue;
        }
        // Either the line is full, or we hit a newline or the end.
        var end = at;
        if !at_end && !is_nl {
            // Full: back up to the last space in [start, at) if there is one.
            var back = at;
            var found = false;
            while back > start {
                if s[back - 1] == ' ' { found = true; break; }
                back = back - 1;
            }
            if found {
                end = back - 1;         // the space is consumed, not carried
                at = back;
            }
        }
        if n >= WRAP_MAX_LINES {
            out.overflow = true;
            return out;
        }
        out.spans[n] = Span { off: start, len: end - start };
        n = n + 1;
        out.count = n;

        if is_nl {
            at = at + 1;                    // the newline is consumed, not part of any span
            start = at;
            if at >= s.len { break; }   // a trailing newline does not create an empty last line
        } else if at_end {
            break;
        } else {
            start = at;
        }
    }
    return out;
}

// How many lines `s` takes at `width`, without building the spans. Used by callers that
// only need to know whether something will fit on the screen.
fn text_line_count(s: const u8[:], width: i64) -> i64 {
    let w = text_wrap(s, width);
    if w.overflow { return WRAP_MAX_LINES + 1; }   // a bound, not a lie about the exact count
    return w.count;
}

// ---------------------------------------------------------------------------
// Clipping
// ---------------------------------------------------------------------------

// Copy at most `width` bytes of `s`, with an ellipsis when anything was cut.
//
// The ellipsis is counted INSIDE the width: clipping to 5 and then appending "..." makes a
// fragment 8 columns wide, which is how a "fits" check passes and the text still overruns.
// Width smaller than the ellipsis degrades to a plain prefix -- three dots in one column is
// not possible, and producing two dots would be worse than producing none.
fn text_clip(s: const u8[:], width: i64, out: u8[>..]&, cap: i64) -> i64, bool {
    if width <= 0 { return 0, s.len > 0; }
    if s.len <= width {
        if s.len > cap { return 0, true; }
        var i: i64 = 0;
        while i < s.len { out.push(s[i]); i = i + 1; }
        return s.len, false;
    }

    if width <= ELLIPSIS.len {
        var short: i64 = 0;
        while short < width && short < cap {
            out.push(s[short]);
            short = short + 1;
        }
        return short, true;
    }

    let keep = width - ELLIPSIS.len;
    if width > cap { return 0, true; }
    var k: i64 = 0;
    while k < keep { out.push(s[k]); k = k + 1; }
    var e: i64 = 0;
    while e < ELLIPSIS.len { out.push(ELLIPSIS[e]); e = e + 1; }
    return width, true;
}

// ---------------------------------------------------------------------------
// Scroll regions
// ---------------------------------------------------------------------------

// A rectangular band of rows that scrolls on its own: the status bar stays put while the
// text above it moves. Rows are screen rows, 0-based, inclusive top and bottom.
struct ScrollRegion {
    top: i64,
    bottom: i64,
    rows: i64,          // 0 = nothing visible
    lines_pushed: i64,
}

// Returns (region, code). An empty or inverted region is E_INVAL, not a silently swapped
// pair: a region with top > bottom scrolls in the wrong direction forever.
fn scroll_new(top: i64, bottom: i64) -> ScrollRegion, i64 {
    if top < 0 || bottom < top { return ScrollRegion { top: 0, bottom: 0, rows: 0, lines_pushed: 0 }, E_INVAL; }
    return ScrollRegion { top: top, bottom: bottom, rows: bottom - top + 1, lines_pushed: 0 }, CODE_OK;
}

fn scroll_contains(r: ScrollRegion&, row: i64) -> bool {
    if r.rows == 0 { return false; }
    return row >= r.top && row <= r.bottom;
}

// Push one line in at the bottom. Returns the first row that must be repainted, or E_INVAL
// when the region is empty. A repaint from the first visible row is deliberate: the cheap
// answer (repaint only the last row) leaves the framebuffer inconsistent after a partial
// write, and consistency is worth one line of pixels.
fn scroll_push(r: ScrollRegion&, n_in: i64) -> i64, i64 {
    var n = n_in;
    if r.rows == 0 { return 0, E_INVAL; }
    if n <= 0 { return r.bottom, CODE_OK; }
    if n > r.rows { n = r.rows; }      // pushing more than a screenful scrolls a screenful
    r.lines_pushed = r.lines_pushed + n;
    return r.bottom - n + 1, CODE_OK;
}

// The row where line `i` of the content is drawn, given how many lines have been pushed.
// -1 when the line has scrolled off the top.
fn scroll_row_for(r: ScrollRegion&, i: i64) -> i64 {
    if r.rows == 0 { return -1; }
    if i < r.lines_pushed { return -1; }
    let row = r.top + (i - r.lines_pushed);
    if row > r.bottom { return -1; }   // below the region: not visible yet
    return row;
}

// Resize the region in place, keeping the pushed count. Rows that no longer exist are simply
// not visible; nothing is thrown away, because a resize during a scroll is not a reason to
// lose text the user has not read.
fn scroll_resize(r: ScrollRegion&, top: i64, bottom: i64) -> i64 {
    if top < 0 || bottom < top { return E_INVAL; }
    r.top = top;
    r.bottom = bottom;
    r.rows = bottom - top + 1;
    return CODE_OK;
}
