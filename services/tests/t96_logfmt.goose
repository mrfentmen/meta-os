// services/tests/t96_logfmt.goose
//
// The record format, driven for the first time: build, render, parse, and the round trip
// between them.
//
// WHY THIS FILE EXISTS
// --------------------
// `services/logfmt` is the shape every service logs through, and until this file no driver
// imported it: the dead-code census listed `logfmt_make`, `logfmt_render`, `logfmt_parse` and
// `logfmt_level_name` as functions nothing calls. A formatter that nothing formats with is the
// most expensive kind of code to be wrong, because the wrongness shows up as a column that
// shifts at 10 seconds in every log anyone reads.
//
// The property under test is the round trip: anything `logfmt_make` builds must survive
// `logfmt_render` and `logfmt_parse` unchanged. Everything else here is a boundary of that.
//
// Status: RUNS — set by `audit_status.py` from the runner's row, not by hand.

import logfmt.logfmt;
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

// A literal and its length, so a rendered buffer can be compared byte for byte with what the
// format is supposed to be. `str` alone loses the length, and a comparison that stopped at the
// first zero byte would pass on a truncated line.
fn lit(s: const u8[:], out: u8[..256]&) -> i64 {
    var i: i64 = 0;
    while i < s.len { out[i] = s[i]; i = i + 1; }
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

fn msg_of(r: Record&, out: u8[..256]&) -> i64 {
    var i: i64 = 0;
    while i < r.msg_len { out[i] = r.msg[i]; i = i + 1; }
    return r.msg_len;
}

fn tag_of(r: Record&, out: u8[..256]&) -> i64 {
    var i: i64 = 0;
    while i < r.tag_len { out[i] = r.tag[i]; i = i + 1; }
    return r.tag_len;
}

fn main() {
    say("t96 logfmt\n");

    // ======================================================================
    // 1. levels: one letter each, and an unknown one is visible
    // ======================================================================
    check("level: debug is D", logfmt_level_letter(LV_DEBUG) == 0x44);
    check("level: info is I", logfmt_level_letter(LV_INFO) == 0x49);
    check("level: warn is W", logfmt_level_letter(LV_WARN) == 0x57);
    check("level: error is E", logfmt_level_letter(LV_ERROR) == 0x45);
    check("level: fatal is F", logfmt_level_letter(LV_FATAL) == 0x46);
    check("level: an unknown level renders as ?, not as silence",
          logfmt_level_letter(9) == 0x3F);
    check("level: ? is not a level, so it parses to -1", logfmt_level_of(0x3F) == -1);
    check("level: letters map back", logfmt_level_of(0x57) == LV_WARN);
    check("level: names", same_len(logfmt_level_name(LV_FATAL), "fatal"[..5])
          && same_len(logfmt_level_name(LV_DEBUG), "debug"[..5])
          && same_len(logfmt_level_name(9), "unknown"[..7]));

    // ======================================================================
    // 2. make: clamping, truncation, and the marker that says a message was cut
    // ======================================================================
    let low = logfmt_make(-5, "svc", "x", 0);
    check("make: a level below debug clamps to debug", low.level == LV_DEBUG);
    let high = logfmt_make(99, "svc", "x", 0);
    check("make: a level above fatal clamps to fatal", high.level == LV_FATAL);

    let t8 = logfmt_make(LV_INFO, "abcdefghij", "x", 0);
    check("make: a tag longer than the column is cut to 7", t8.tag_len == TAG_MAX - 1);

    // A message past MSG_MAX keeps its start and ends with the cut marker: the difference
    // between "the message ended" and "the message was cut" is three dots.
    var long_msg: u8[..256] = [0; 256];
    var i: i64 = 0;
    while i < MSG_MAX + 20 { long_msg[i] = 97; i = i + 1; }     // 'a'
    let cut = logfmt_make(LV_INFO, "svc", long_msg[..(MSG_MAX + 20)], 0);
    var cutmsg: u8[..256] = [0; 256];
    let cutn = msg_of(cut, cutmsg);
    check("make: an overlong message is marked, not refused",
          cutn == MSG_MAX && cutmsg[cutn - 1] == 0x2E && cutmsg[cutn - 2] == 0x2E
          && cutmsg[cutn - 3] == 0x2E);

    // ======================================================================
    // 3. render: the exact line, including the column that must never shift
    // ======================================================================
    var buf: u8[..200] = [0; 200];
    var want: u8[..256] = [0; 256];

    let r1 = logfmt_make(LV_INFO, "cons", "ready", 42300);
    let n1 = logfmt_render(r1, buf);
    let w1 = lit("0042.300 I cons    ready\n", want);
    check("render: 42.3 s is a four-digit field", n1 == w1);
    check("render: the line is exactly the documented shape", same_len(buf[..n1], want[..w1]));
    // The column is fixed for the first 10000 s: 9.999 s, 10 s and 999 s all occupy the same
    // four characters, which is the whole reason the field is padded.
    let a9 = logfmt_make(LV_INFO, "cons", "m", 9999);
    let n9 = logfmt_render(a9, buf);
    let w9 = lit("0009.999 I cons    m\n", want);
    check("render: 9.999 s pads to four digits", same_len(buf[..n9], want[..w9]));
    let a10 = logfmt_make(LV_INFO, "cons", "m", 10000);
    let n10 = logfmt_render(a10, buf);
    let w10 = lit("0010.000 I cons    m\n", want);
    check("render: 10 s is still four digits", same_len(buf[..n10], want[..w10]));
    let a999 = logfmt_make(LV_INFO, "cons", "m", 999900);
    let n999 = logfmt_render(a999, buf);
    let w999 = lit("0999.900 I cons    m\n", want);
    check("render: 999.9 s is still four digits", same_len(buf[..n999], want[..w999]));
    // Past 10000 s the field grows rather than truncating the uptime.
    let big = logfmt_make(LV_INFO, "cons", "m", 12345600);
    let nbig = logfmt_render(big, buf);
    let wbig = lit("12345.600 I cons    m\n", want);
    check("render: past 10000 s the field grows", same_len(buf[..nbig], want[..wbig]));

    // Zero is "0000.000", not ".000" and not "0.000".
    let z = logfmt_make(LV_DEBUG, "svc", "start", 0);
    let nz = logfmt_render(z, buf);
    let wz = lit("0000.000 D svc     start\n", want);
    check("render: uptime zero is padded too", same_len(buf[..nz], want[..wz]));

    // A full-width tag takes the whole column and no padding, so the message starts one
    // space later than usual -- which is what the format says, not a drift.
    let full = logfmt_make(LV_ERROR, "abcdefg", "m", 0);
    let nf = logfmt_render(full, buf);
    let wf = lit("0000.000 E abcdefg m\n", want);
    check("render: a 7-char tag fills the column", same_len(buf[..nf], want[..wf]));

    // The widest record the struct can hold must fit the line budget, or `render` has a
    // -1 path that real logging can reach -- and a dropped log line is a missing log line.
    // Widest legal record: seconds to the parser's 9-digit limit, .mmm, level, 7-char tag,
    // 160-char message. This is an invariant between two constants, checked as one.
    var wide: u8[..200] = [0; 200];
    var widest = Record { uptime_ms: 999999999000, level: LV_WARN, tag: [0; 8], tag_len: 7, msg: [0; 160], msg_len: 160 };
    var h: i64 = 0;
    while h < 160 { widest.msg[h] = 97; h = h + 1; }
    widest.tag[0] = 0x61;
    widest.tag[1] = 0x62;
    widest.tag[2] = 0x63;
    widest.tag[3] = 0x64;
    widest.tag[4] = 0x65;
    widest.tag[5] = 0x66;
    widest.tag[6] = 0x67;
    let nw = logfmt_render(widest, wide);
    check("render: the widest record the struct allows still fits the line budget",
          nw > 0 && nw <= LINE_MAX);
    // And it is still a parseable line: the format does not break at its own boundary.
    var wout = Record { uptime_ms: 0, level: 0, tag: [0; 8], tag_len: 0, msg: [0; 160], msg_len: 0 };
    check("render: the widest record parses back", logfmt_parse(wide[..nw], wout)
          && wout.msg_len == 160 && wout.tag_len == 7 && wout.level == LV_WARN);

    // ======================================================================
    // 4. parse: the round trip, field by field
    // ======================================================================
    var out = Record { uptime_ms: 0, level: 0, tag: [0; 8], tag_len: 0, msg: [0; 160], msg_len: 0 };
    let ok1 = logfmt_parse(buf[..nf], out);
    check("parse: the rendered line parses", ok1);
    check("parse: the uptime survived", out.uptime_ms == 0);
    check("parse: the level survived", out.level == LV_ERROR);
    check("parse: the tag survived", out.tag_len == 7);
    var rtag: u8[..256] = [0; 256];
    let rtn = tag_of(out, rtag);
    check("parse: the tag bytes survived", same_len(rtag[..rtn], "abcdefg"[..7]));
    var rmsg: u8[..256] = [0; 256];
    let rmn = msg_of(out, rmsg);
    check("parse: the message survived", same_len(rmsg[..rmn], "m"[..1]));

    // The whole round trip over the values that made the column interesting.
    let rt = logfmt_make(LV_WARN, "net", "link down after 3 retries", 987654);
    let nrt = logfmt_render(rt, buf);
    let okrt = logfmt_parse(buf[..nrt], out);
    check("round trip: parses", okrt);
    check("round trip: uptime to the millisecond", out.uptime_ms == 987654);
    check("round trip: level", out.level == LV_WARN);
    let rmn2 = msg_of(out, rmsg);
    check("round trip: message with spaces", same_len(rmsg[..rmn2], "link down after 3 retries"[..25]));
    let rtn2 = tag_of(out, rtag);
    check("round trip: tag", same_len(rtag[..rtn2], "net"[..3]));

    // A message that was truncated at make time survives the round trip AS truncated: the
    // dots are part of the record, not a rendering artifact.
    let ncut = logfmt_render(cut, buf);
    let okcut = logfmt_parse(buf[..ncut], out);
    check("round trip: a truncated message keeps its marker", okcut && out.msg_len == MSG_MAX);

    // The padding bug, stated as a check: a 3-char tag pads the column by four spaces, and
    // the reader must skip them rather than hand them to the message. Before this was fixed,
    // `svc` + "m" parsed as "    m" and a 160-char message came back as 160 bytes of shifted
    // text with three of its own bytes cut off the end.
    let shorttag = logfmt_make(LV_INFO, "svc", "m", 0);
    let nst = logfmt_render(shorttag, buf);
    var sout = Record { uptime_ms: 0, level: 0, tag: [0; 8], tag_len: 0, msg: [0; 160], msg_len: 0 };
    let okst = logfmt_parse(buf[..nst], sout);
    check("parse: the padded tag column is not part of the message",
          okst && sout.msg_len == 1 && sout.msg[0] == 0x6D);

    // A writer cannot smuggle in leading spaces either: the format has no way to say them.
    let indented = logfmt_make(LV_INFO, "svc", "   indented", 0);
    var imsg: u8[..256] = [0; 256];
    let imn = msg_of(indented, imsg);
    check("make: leading spaces are trimmed, not rendered as part of the message",
          imn == 8 && same_len(imsg[..imn], "indented"[..8]));

    // ======================================================================
    // 5. parse: what it must refuse
    // ======================================================================
    check("parse: an empty line is refused", !logfmt_parse(""[..0], out));
    check("parse: a line shorter than the minimum is refused", !logfmt_parse("0.000 I t"[..9], out));
    check("parse: a missing dot is refused", !logfmt_parse("0042,300 I cons    m\n"[..19], out));
    check("parse: two-digit milliseconds are refused",
          !logfmt_parse("0042.30 I cons    m\n"[..18], out));
    check("parse: a non-digit in the milliseconds is refused",
          !logfmt_parse("0042.3x0 I cons    m\n"[..19], out));
    check("parse: an unknown level letter is refused",
          !logfmt_parse("0042.300 Z cons    m\n"[..19], out));
    check("parse: a missing space after the level is refused",
          !logfmt_parse("0042.300 Icons     m\n"[..19], out));
    check("parse: a tag past the column is refused",
          !logfmt_parse("0042.300 I abcdefgh m\n"[..21], out));
    var nonl: u8[..256] = [0; 256];
    let wnl = lit("0042.300 I cons    m", nonl);
    check("parse: no newline at all still parses (a last line may lack one)",
          logfmt_parse(nonl[..wnl], out) && out.msg_len == 1);
    check("parse: seconds above nine digits are refused",
          !logfmt_parse("1234567890.300 I cons    m\n"[..25], out));

    // A refused line must fill NOTHING. The parser writes as it goes, so this is the property
    // that catches a half-filled record handed to an audit trail as if it were data.
    var keep = Record { uptime_ms: 7, level: LV_FATAL, tag: [0; 8], tag_len: 3, msg: [0; 160], msg_len: 2 };
    keep.tag[0] = 107; keep.tag[1] = 101; keep.tag[2] = 112;      // "kep"
    keep.msg[0] = 111; keep.msg[1] = 107;                          // "ok"
    // A line whose tag ends at the end of the line: the tag is complete, the separator is
    // missing. Everything the parser read before the failure must stay out of `keep`.
    let bad = logfmt_parse("0042.300 I tagx"[..15], keep);
    check("parse: a bad line reports false", !bad);
    check("parse: a bad line does not touch the caller's record",
          keep.uptime_ms == 7 && keep.level == LV_FATAL && keep.tag_len == 3 && keep.msg_len == 2);

    // ======================================================================
    // 6. the line a shell would print, built by the service that owns the shape
    // ======================================================================
    let demo = logfmt_make(LV_INFO, "notify", "3 unread", 1500);
    let nd = logfmt_render(demo, buf);
    say("     ");
    say(buf[..nd]);
    check("the demo line is a log line", nd > 0 && buf[nd - 1] == 0x0A);

    say("t96 done  pass=");
    var pb: u8[>..] = [];
    let _ = append_int(pb, 32, t_pass);
    say(pb[..]);
    say(" fail=");
    var fb: u8[>..] = [];
    let _ = append_int(fb, 32, t_fail);
    say(fb[..]);
    say("\n");
    if t_fail > 0 { sys_exit(1); }
}
