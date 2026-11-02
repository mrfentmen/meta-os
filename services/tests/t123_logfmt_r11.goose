// services/tests/t123_logfmt_r11.goose
//
// Round 11 driver for `logfmt`: the record's three limits (tag, message, line), the
// truncation marker, the parser's refusals, and the round trip.
//
// Why these assertions: a log line is read at 3am by a person and a parser, and both
// fail quietly. The truncation marker is the only difference between "the message
// ended" and "the message was cut"; a parser that half-fills a record invents audit
// data. Both are asserted to the byte.
//
// Status: WRITTEN (Round 11 worker). Not compiled or run here; the coordinator runs it.

import logfmt.logfmt;
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

fn same(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn main() {
    say("t123 logfmt record shape\n");

    // ======================================================================
    // 1. the rendered line
    // ======================================================================
    var r = logfmt_make(LV_INFO, "cons", "ready", 42300);
    check("logfmt_make: level is kept", r.level == LV_INFO);
    check("logfmt_make: tag length is the tag", r.tag_len == 4);
    check("logfmt_make: message is kept", r.msg_len == 5 && r.msg[0] == 0x72);

    var out: u8[..200] = [0; 200];
    let n = logfmt_render(r, out);
    check("logfmt_render: a record renders", n > 0);
    check("logfmt_render: seconds and millis are fixed width", same(out[..8], "0042.300"));
    check("logfmt_render: one letter level follows", out[9] == 0x49);
    check("logfmt_render: the tag column is padded", same(out[11..15], "cons"));
    // Four spaces between tag and message: three pad the tag column to TAG_MAX-1, one is
    // the separator. Counting the literal by eye gave five; the render's index arithmetic
    // (tag at 11, pad 15..17, space 18, message 19) gives four.
    check("logfmt_render: the message ends the line", same(out[..n], "0042.300 I cons    ready\n"));

    // ======================================================================
    // 2. the three limits
    // ======================================================================
    // Tag: at most TAG_MAX-1 bytes survive, because the array keeps a terminator.
    var longtag = logfmt_make(LV_INFO, "abcdefghij", "m", 0);
    check("logfmt_make: a tag past TAG_MAX-1 is cut", longtag.tag_len == TAG_MAX - 1);

    // Message: MSG_MAX bytes including the three-dot marker, never a silent cut.
    var huge: u8[..220] = [0x41; 220];
    var cut = logfmt_make(LV_INFO, "t", huge[..], 0);
    check("logfmt_make: an oversize message keeps MSG_MAX bytes", cut.msg_len == MSG_MAX);
    check("logfmt_make: the cut is marked", cut.msg[MSG_MAX - 3] == 0x2E
          && cut.msg[MSG_MAX - 2] == 0x2E && cut.msg[MSG_MAX - 1] == 0x2E);

    // Leading spaces cannot survive the padded tag column, so the writer trims them.
    var spaced = logfmt_make(LV_INFO, "t", "  hi", 0);
    check("logfmt_make: leading spaces are trimmed", spaced.msg_len == 2 && spaced.msg[0] == 0x68);

    // Level is clamped into the five that exist; unknown is never invented.
    var lo = logfmt_make(-5, "t", "m", 0);
    var hi = logfmt_make(99, "t", "m", 0);
    check("logfmt_make: a level below DEBUG clamps", lo.level == LV_DEBUG);
    check("logfmt_make: a level above FATAL clamps", hi.level == LV_FATAL);

    // Uptime past four digits grows the field instead of truncating the number.
    var late = logfmt_make(LV_INFO, "t", "m", 12345678);
    var lout: u8[..200] = [0; 200];
    let ln = logfmt_render(late, lout);
    check("logfmt_render: a five-digit uptime grows the field",
          ln > 0 && same(lout[..10], "12345.678 "));

    // ======================================================================
    // 3. the parser: round trip, then refusals
    // ======================================================================
    var back = logfmt_make(LV_DEBUG, "x", "y", 0);
    check("logfmt_parse: a rendered line parses", logfmt_parse(out[..n], back));
    check("logfmt_parse: uptime round trips", back.uptime_ms == 42300);
    check("logfmt_parse: level round trips", back.level == LV_INFO);
    check("logfmt_parse: tag round trips", back.tag_len == 4 && back.tag[0] == 0x63);
    check("logfmt_parse: message round trips", back.msg_len == 5 && same(back.msg[..5], "ready"));

    // A failed parse must leave the caller's record exactly as it was.
    var keep = logfmt_make(LV_WARN, "keep", "intact", 5);
    check("logfmt_parse: a short line is refused", !logfmt_parse("0042.30", keep));
    check("logfmt_parse: an unknown level is refused", !logfmt_parse("0042.300 X cons msg\n", keep));
    check("logfmt_parse: a missing message separator is refused",
          !logfmt_parse("0042.300 I\n", keep));
    check("logfmt_parse: a bad millisecond field is refused",
          !logfmt_parse("0042.30x I cons msg\n", keep));
    check("logfmt_parse: a refusal changes nothing",
          keep.msg_len == 6 && same(keep.msg[..6], "intact") && keep.level == LV_WARN);

    // ======================================================================
    // 4. load: render and parse a batch, ten times a normal one
    // ======================================================================
    var ops: i64 = 0;
    var ok: i64 = 0;
    var refused: i64 = 0;
    var line: u8[..200] = [0; 200];
    var dst = logfmt_make(LV_DEBUG, "z", "z", 0);
    while ops < 300 {
        var rr = logfmt_make(LV_INFO, "load", "a load line", ops * 10);
        let ln2 = logfmt_render(rr, line);
        if ln2 > 0 && logfmt_parse(line[..ln2], dst) { ok = ok + 1; } else { refused = refused + 1; }
        ops = ops + 1;
    }
    say("LOAD logfmt ops=");
    var ob: u8[>..] = [];
    let _ = append_int(ob, 32, ops);
    say(ob[..]);
    say(" ok=");
    var kb: u8[>..] = [];
    let _ = append_int(kb, 32, ok);
    say(kb[..]);
    say(" refused=");
    var rb: u8[>..] = [];
    let _ = append_int(rb, 32, refused);
    say(rb[..]);
    say("\n");

    say("t123 done  pass=");
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
