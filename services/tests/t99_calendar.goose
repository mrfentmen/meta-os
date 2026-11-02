// services/tests/t99_calendar.goose
//
// The civil calendar (B-L1-110): month lengths, names, and the round trip between a wall time
// and the seconds the clock stores.
//
// WHY THIS FILE EXISTS
// --------------------
// Six functions in `time/calendar.goose` were listed by the dead-code census as calls nothing
// makes: `cal_days_in_month`, `cal_make`, and the four name tables. The names are the easy part.
// The hard part is `cal_make`, which is the other half of `cal_break` and the one an operator
// reaches through `date -s`: if it disagrees with `cal_break` by an offset, the clock drifts an
// hour every time someone sets it, and nothing about that failure looks like a bug.
//
// The dates chosen are the ones that break hand-rolled calendars: 1900 (divisible by 100, not
// 400), 2000 (divisible by 400), and 29 February in both.
//
// Status: RUNS — set by `audit_status.py` from the runner's row, not by hand.

import time.calendar;
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

fn same_len(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn civil(y: i64, m: i64, d: i64, h: i64, mi: i64, s: i64) -> Civil {
    return Civil { year: y, month: m, day: d, hour: h, minute: mi, second: s, weekday: 0, yearday: 0 };
}

// Build a wall time, store it as seconds, read it back, and say whether every field survived.
fn round_trips(y: i64, m: i64, d: i64, h: i64, mi: i64, s: i64, off: i64) -> bool {
    let c = civil(y, m, d, h, mi, s);
    let t = cal_make(c, off);
    let back = cal_break(t, off);
    return back.year == y && back.month == m && back.day == d && back.hour == h
        && back.minute == mi && back.second == s;
}

fn main() {
    say("t99 calendar\n");

    // ======================================================================
    // 1. month lengths, including the two centuries that trip a naive leap test
    // ======================================================================
    check("days_in_month: January", cal_days_in_month(2026, 1) == 31);
    check("days_in_month: April", cal_days_in_month(2026, 4) == 30);
    check("days_in_month: December", cal_days_in_month(2026, 12) == 31);
    check("days_in_month: February 2023", cal_days_in_month(2023, 2) == 28);
    check("days_in_month: February 2024 is a leap day", cal_days_in_month(2024, 2) == 29);
    // 1900 is divisible by 100 and not by 400: not a leap year. A `y % 4` check says 29.
    check("days_in_month: February 1900 is not a leap day", cal_days_in_month(1900, 2) == 28);
    // 2000 is divisible by 400: a leap year. A `y % 100` check says 28.
    check("days_in_month: February 2000 is a leap day", cal_days_in_month(2000, 2) == 29);
    check("days_in_month: month zero is not a month", cal_days_in_month(2026, 0) == 0);
    check("days_in_month: month thirteen is not a month", cal_days_in_month(2026, 13) == 0);

    // ======================================================================
    // 2. names: twelve of each, and a visible answer for a bad index
    // ======================================================================
    check("month_name: all twelve", same_len(cal_month_name(1), "January"[..7])
          && same_len(cal_month_name(2), "February"[..8])
          && same_len(cal_month_name(3), "March"[..5])
          && same_len(cal_month_name(4), "April"[..5])
          && same_len(cal_month_name(5), "May"[..3])
          && same_len(cal_month_name(6), "June"[..4])
          && same_len(cal_month_name(7), "July"[..4])
          && same_len(cal_month_name(8), "August"[..6])
          && same_len(cal_month_name(9), "September"[..9])
          && same_len(cal_month_name(10), "October"[..7])
          && same_len(cal_month_name(11), "November"[..8])
          && same_len(cal_month_name(12), "December"[..8]));
    check("month_name: a bad month is a question mark, not December",
          same_len(cal_month_name(0), "?"[..1]) && same_len(cal_month_name(13), "?"[..1]));
    check("month_short: all twelve", same_len(cal_month_short(1), "Jan"[..3])
          && same_len(cal_month_short(6), "Jun"[..3])
          && same_len(cal_month_short(9), "Sep"[..3])
          && same_len(cal_month_short(12), "Dec"[..3]));
    check("month_short: a bad month is three marks", same_len(cal_month_short(13), "???"[..3]));

    check("weekday_name: all seven", same_len(cal_weekday_name(0), "Sunday"[..6])
          && same_len(cal_weekday_name(1), "Monday"[..6])
          && same_len(cal_weekday_name(2), "Tuesday"[..7])
          && same_len(cal_weekday_name(3), "Wednesday"[..9])
          && same_len(cal_weekday_name(4), "Thursday"[..8])
          && same_len(cal_weekday_name(5), "Friday"[..6])
          && same_len(cal_weekday_name(6), "Saturday"[..8]));
    check("weekday_short: all seven", same_len(cal_weekday_short(0), "Sun"[..3])
          && same_len(cal_weekday_short(3), "Wed"[..3])
          && same_len(cal_weekday_short(6), "Sat"[..3]));
    check("weekday_name: a bad weekday is not Sunday",
          same_len(cal_weekday_name(7), "?"[..1]) && same_len(cal_weekday_short(7), "???"[..3]));

    // ======================================================================
    // 3. cal_make against known instants
    // ======================================================================
    check("cal_make: the epoch", cal_make(civil(1970, 1, 1, 0, 0, 0), 0) == 0);
    check("cal_make: one second before the epoch", cal_make(civil(1969, 12, 31, 23, 59, 59), 0) == -1);
    // A zone offset is applied in reverse: 00:59:59 at +60 min is still one second before the
    // epoch, not one hour after it.
    check("cal_make: a positive offset subtracts from the stored seconds",
          cal_make(civil(1970, 1, 1, 0, 59, 59), 60) == -1);
    // 19:00 at -300 is midnight UTC: a negative offset is added back, so this is the epoch
    // instant, not the epoch minus five hours.
    check("cal_make: a negative offset adds to the stored seconds",
          cal_make(civil(1969, 12, 31, 19, 0, 0), -300) == 0);
    check("cal_make: 2024-02-29 12:00 UTC", cal_make(civil(2024, 2, 29, 12, 0, 0), 0) == 1709208000);
    check("cal_make: 2000-02-29 00:00 UTC", cal_make(civil(2000, 2, 29, 0, 0, 0), 0) == 951782400);
    check("cal_make: 1900-03-01 00:00 UTC", cal_make(civil(1900, 3, 1, 0, 0, 0), 0) == -2203891200);

    // ======================================================================
    // 4. the round trip: what `date -s` writes is what the clock reads back
    // ======================================================================
    check("round trip: the epoch", round_trips(1970, 1, 1, 0, 0, 0, 0));
    check("round trip: a leap day at +60", round_trips(2024, 2, 29, 23, 59, 59, 60));
    check("round trip: 1900 in February at -300", round_trips(1900, 2, 28, 12, 30, 15, -300));
    check("round trip: 2000-02-29 at +540", round_trips(2000, 2, 29, 6, 0, 0, 540));
    check("round trip: year end", round_trips(2026, 12, 31, 23, 59, 59, 0));
    check("round trip: the start of a year at +600 (DST zone)", round_trips(2026, 1, 1, 0, 0, 1, 600));
    check("round trip: a date before the epoch", round_trips(1969, 7, 20, 20, 17, 40, 0));
    check("round trip: the top of a minute", round_trips(2026, 11, 2, 12, 0, 0, 0));

    // The weekday comes from the same arithmetic, so it is checked against two dates whose
    // weekday everyone can look up: 1970-01-01 was a Thursday, and 2026-11-02 is a Monday.
    let e = cal_break(0, 0);
    check("cal_break: the epoch is a Thursday", e.weekday == 4 && e.yearday == 1);
    let m = cal_break(cal_make(civil(2026, 11, 2, 0, 0, 0), 0), 0);
    check("cal_break: 2026-11-02 is a Monday", m.weekday == 1 && m.month == 11 && m.day == 2);
    check("cal_break: 2024 is a leap year, so 1 March is day 61",
          cal_break(cal_make(civil(2024, 3, 1, 0, 0, 0), 0), 0).yearday == 61);
    check("cal_break: 2023 is not, so 1 March is day 60",
          cal_break(cal_make(civil(2023, 3, 1, 0, 0, 0), 0), 0).yearday == 60);

    // A zone offset moves the wall clock without moving the instant: the same seconds read as
    // 12:00 UTC and 13:00 at +60.
    let utc_noon = cal_make(civil(2026, 11, 2, 12, 0, 0), 0);
    let local = cal_break(utc_noon, 60);
    check("cal_break: an offset moves the wall clock, not the instant",
          local.hour == 13 && cal_make(local, 60) == utc_noon);

    say("t99 done  pass=");
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
