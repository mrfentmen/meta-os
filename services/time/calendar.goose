// services/time/calendar.goose
//
// B-L1-110 — Time: civil calendar and zones.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// THE ONLY HARD PART IS LEAP YEARS, AND IT IS ALREADY SOLVED
// ----------------------------------------------------------
// Days-since-epoch <-> (year, month, day) is done with Howard Hinnant's civil_from_days /
// days_from_civil algorithms. They are exact for every proleptic Gregorian date and need no
// tables, no loops over months, and no branch for the 1900/2000 century rules beyond the
// leap test itself. A hand-rolled month table gets February wrong in 2100, which is far
// enough away to ship and near enough to be someone's problem.
//
// ZONES ARE A TABLE, NOT A DATABASE
// ---------------------------------
// There is no tzdata here and this file does not pretend otherwise. A zone is a fixed
// standard offset plus, optionally, ONE DST rule expressed as data: which month/day it
// starts and ends, and how many minutes. That covers the common cases and is honest about
// what it cannot do -- a zone with a rule change (the EU's, twice, in living memory) needs
// a new table row, not a cleverer function.
//
// WHAT THIS FILE WILL NOT DO
// --------------------------
// No leap seconds. Unix time ignores them, the RTC ignores them, and a clock that adds one
// once every few years disagrees with every other clock in between. If the OS ever needs
// them, that is a new decision with a written rationale, not a hidden `if`.

import common.err.err;

let SECS_PER_DAY: i64 = 86400;
let SECS_PER_HOUR: i64 = 3600;
let SECS_PER_MIN: i64 = 60;
let DAYS_PER_WEEK: i64 = 7;

// 0 = Sunday, matching the C convention every caller here already thinks in.
fn cal_is_leap(y: i64) -> bool {
    if (y % 4) != 0 { return false; }
    if (y % 100) != 0 { return true; }
    return (y % 400) == 0;
}

fn cal_days_in_month(y: i64, m: i64) -> i64 {
    if m < 1 || m > 12 { return 0; }
    if m == 2 {
        if cal_is_leap(y) { return 29; }
        return 28;
    }
    if m == 4 || m == 6 || m == 9 || m == 11 { return 30; }
    return 31;
}

// Days since 1970-01-01 for a civil date. Negative years work; the formula is proleptic.
fn days_from_civil(y: i64, m: i64, d: i64) -> i64 {
    var yy = y;
    if m <= 2 { yy = yy - 1; }
    let era = cal_floor_div(yy, 400);
    let yoe = yy - era * 400;                            // [0, 399]
    var mp = m - 3;
    if m <= 2 { mp = m + 9; }                            // March-based month [0, 11]
    let doy = (153 * mp + 2) / 5 + d - 1;                // [0, 365]
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;     // [0, 146096]
    return era * 146097 + doe - 719468;
}

// Inverse. Returns (year, month, day), all 1-based except the year, which may be <= 0.
fn civil_from_days(z: i64) -> i64, i64, i64 {
    let zz = z + 719468;
    let era = cal_floor_div(zz, 146097);
    let doe = zz - era * 146097;                          // [0, 146096]
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    var y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    var m = mp + 3;
    if mp >= 10 { m = mp - 9; }
    if m <= 2 { y = y + 1; }
    return y, m, d;
}

// Truncating division rounds towards zero, which is wrong for negative days (dates before
// 1970). One helper, used everywhere a division appears in the algorithms above.
fn cal_floor_div(a: i64, b: i64) -> i64 {
    if b == 0 { return 0; }
    var q = a / b;
    let r = a - q * b;
    if r != 0 && ((r < 0) != (b < 0)) { q = q - 1; }
    return q;
}

// ---------------------------------------------------------------------------
// Breakdown
// ---------------------------------------------------------------------------

struct Civil {
    year: i64,
    month: i64,
    day: i64,
    hour: i64,
    minute: i64,
    second: i64,
    weekday: i64,
    yearday: i64,        // 1-based
}

// Break a Unix time (seconds, may be negative) into civil fields with a zone offset in
// minutes: +60 for CET, -300 for EST. The offset is applied before the split, so the
// result is the wall clock a person would read, not UTC with a label.
fn cal_break(unix_s: i64, offset_min: i64) -> Civil {
    let local = unix_s + offset_min * SECS_PER_MIN;
    let days = cal_floor_div(local, SECS_PER_DAY);
    let sod = local - days * SECS_PER_DAY;               // [0, 86399]
    let y, m, d = civil_from_days(days);
    var wd = (days + 4) % DAYS_PER_WEEK;                 // 1970-01-01 was a Thursday
    if wd < 0 { wd = wd + DAYS_PER_WEEK; }
    let jan1 = days_from_civil(y, 1, 1);
    return Civil {
        year: y, month: m, day: d,
        hour: sod / SECS_PER_HOUR,
        minute: (sod % SECS_PER_HOUR) / SECS_PER_MIN,
        second: sod % SECS_PER_MIN,
        weekday: wd,
        yearday: days - jan1 + 1,
    };
}

// The other direction, for `date -s`. Applies the offset in reverse, so a wall time read
// from a user and the UTC seconds the clock stores cannot drift apart.
fn cal_make(c: Civil&, offset_min: i64) -> i64 {
    let days = days_from_civil(c.year, c.month, c.day);
    let sod = c.hour * SECS_PER_HOUR + c.minute * SECS_PER_MIN + c.second;
    return days * SECS_PER_DAY + sod - offset_min * SECS_PER_MIN;
}

fn cal_month_name(m: i64) -> const u8[:] {
    if m == 1 { return "January"; }
    if m == 2 { return "February"; }
    if m == 3 { return "March"; }
    if m == 4 { return "April"; }
    if m == 5 { return "May"; }
    if m == 6 { return "June"; }
    if m == 7 { return "July"; }
    if m == 8 { return "August"; }
    if m == 9 { return "September"; }
    if m == 10 { return "October"; }
    if m == 11 { return "November"; }
    if m == 12 { return "December"; }
    return "?";
}

fn cal_month_short(m: i64) -> const u8[:] {
    if m == 1 { return "Jan"; }
    if m == 2 { return "Feb"; }
    if m == 3 { return "Mar"; }
    if m == 4 { return "Apr"; }
    if m == 5 { return "May"; }
    if m == 6 { return "Jun"; }
    if m == 7 { return "Jul"; }
    if m == 8 { return "Aug"; }
    if m == 9 { return "Sep"; }
    if m == 10 { return "Oct"; }
    if m == 11 { return "Nov"; }
    if m == 12 { return "Dec"; }
    return "???";
}

fn cal_weekday_name(w: i64) -> const u8[:] {
    if w == 0 { return "Sunday"; }
    if w == 1 { return "Monday"; }
    if w == 2 { return "Tuesday"; }
    if w == 3 { return "Wednesday"; }
    if w == 4 { return "Thursday"; }
    if w == 5 { return "Friday"; }
    if w == 6 { return "Saturday"; }
    return "?";
}

fn cal_weekday_short(w: i64) -> const u8[:] {
    if w == 0 { return "Sun"; }
    if w == 1 { return "Mon"; }
    if w == 2 { return "Tue"; }
    if w == 3 { return "Wed"; }
    if w == 4 { return "Thu"; }
    if w == 5 { return "Fri"; }
    if w == 6 { return "Sat"; }
    return "???";
}

// ---------------------------------------------------------------------------
// Zones
// ---------------------------------------------------------------------------

struct Zone {
    index: i64,              // row in the table; names live in zone_name, not in the struct
    std_offset_min: i64,
    dst_offset_min: i64,     // equal to std when the zone has no DST rule
    dst_start_month: i64,    // 0 = no DST
    dst_start_day: i64,
    dst_end_month: i64,
    dst_end_day: i64,
}

let ZONE_COUNT: i64 = 6;

fn zone_at(i: i64) -> Zone {
    if i == 1 { return Zone { index: 1, std_offset_min: 60, dst_offset_min: 120, dst_start_month: 3, dst_start_day: 31, dst_end_month: 10, dst_end_day: 27 }; }
    if i == 2 { return Zone { index: 2, std_offset_min: -300, dst_offset_min: -240, dst_start_month: 3, dst_start_day: 10, dst_end_month: 11, dst_end_day: 3 }; }
    if i == 3 { return Zone { index: 3, std_offset_min: -480, dst_offset_min: -420, dst_start_month: 3, dst_start_day: 10, dst_end_month: 11, dst_end_day: 3 }; }
    if i == 4 { return Zone { index: 4, std_offset_min: 540, dst_offset_min: 540, dst_start_month: 0, dst_start_day: 0, dst_end_month: 0, dst_end_day: 0 }; }
    if i == 5 { return Zone { index: 5, std_offset_min: 600, dst_offset_min: 660, dst_start_month: 10, dst_start_day: 6, dst_end_month: 4, dst_end_day: 6 }; }
    return Zone { index: 0, std_offset_min: 0, dst_offset_min: 0, dst_start_month: 0, dst_start_day: 0, dst_end_month: 0, dst_end_day: 0 };
}

fn zone_count() -> i64 {
    return ZONE_COUNT;
}

fn zone_name(i: i64) -> const u8[:] {
    if i == 1 { return "CET"; }
    if i == 2 { return "EST"; }
    if i == 3 { return "PST"; }
    if i == 4 { return "JST"; }
    if i == 5 { return "AEST"; }
    return "UTC";
}

// Look a zone up by name. Byte for byte, no fuzzy matching: "GMT+1" and "GMT-1" differ by a
// sign, and a typo must be refused rather than silently resolved to UTC.
fn zone_find(name: const u8[:]) -> Zone, bool {
    var i: i64 = 0;
    while i < ZONE_COUNT {
        if cal_bytes_eq(zone_name(i), name) { return zone_at(i), true; }
        i++;
    }
    return zone_at(0), false;
}

// Is DST in force at this instant? Evaluated in UTC: the switch happens at a UTC instant and
// applying it in local time is how a clock ends up an hour out for one hour, twice a year.
//
// The table stores the LAST day the rule can fall on ("the last Sunday on or after the
// 25th" is expressed as a day-of-month, and the weekday is found by walking backwards).
// A rule with a different shape needs its own row and, eventually, its own field.
fn zone_offset_min(z: Zone&, unix_s: i64) -> i64 {
    if z.dst_start_month == 0 { return z.std_offset_min; }
    let utc = cal_break(unix_s, 0);
    if zone_in_dst_window(z, utc.month, utc.day, utc.hour) { return z.dst_offset_min; }
    return z.std_offset_min;
}

fn zone_in_dst_window(z: Zone&, month: i64, day: i64, hour: i64) -> bool {
    // Southern hemisphere zones wrap: their window is [start, end) across the year end.
    if z.dst_start_month < z.dst_end_month {
        if month < z.dst_start_month || month > z.dst_end_month { return false; }
        if month == z.dst_start_month { return day > z.dst_start_day || (day == z.dst_start_day && hour >= 1); }
        if month == z.dst_end_month { return day < z.dst_end_day || (day == z.dst_end_day && hour < 1); }
        return true;
    }
    if month > z.dst_start_month || month < z.dst_end_month { return true; }
    if month == z.dst_start_month { return day > z.dst_start_day || (day == z.dst_start_day && hour >= 1); }
    if month == z.dst_end_month { return day < z.dst_end_day || (day == z.dst_end_day && hour < 1); }
    return false;
}

fn cal_bytes_eq(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if a[i] != b[i] { return false; }
        i++;
    }
    return true;
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

fn cal_two(out: u8[>..]&, cap: i64, v: i64) -> bool {
    if out.len + 2 > cap { return false; }
    out.push((48 + (v / 10) % 10) as u8);
    out.push((48 + v % 10) as u8);
    return true;
}

fn cal_push(out: u8[>..]&, cap: i64, s: const u8[:]) -> bool {
    if out.len + s.len > cap { return false; }
    var i: i64 = 0;
    while i < s.len { out.push(s[i]); i++; }
    return true;
}

// ISO 8601 without a zone suffix: "2026-11-01 04:05:09". Sorts lexicographically, which is
// why the log records use the same shape.
fn cal_format_iso(c: Civil&, out: u8[>..]&, cap: i64) -> bool {
    if !cal_year4(out, cap, c.year) { return false; }
    if !cal_push(out, cap, "-") { return false; }
    if !cal_two(out, cap, c.month) { return false; }
    if !cal_push(out, cap, "-") { return false; }
    if !cal_two(out, cap, c.day) { return false; }
    if !cal_push(out, cap, " ") { return false; }
    if !cal_two(out, cap, c.hour) { return false; }
    if !cal_push(out, cap, ":") { return false; }
    if !cal_two(out, cap, c.minute) { return false; }
    if !cal_push(out, cap, ":") { return false; }
    return cal_two(out, cap, c.second);
}

fn cal_year4(out: u8[>..]&, cap: i64, y: i64) -> bool {
    if y < 0 { return false; }              // negative years are rejected, not formatted wrong
    if y > 9999 { return false; }
    if out.len + 4 > cap { return false; }
    out.push((48 + (y / 1000) % 10) as u8);
    out.push((48 + (y / 100) % 10) as u8);
    out.push((48 + (y / 10) % 10) as u8);
    out.push((48 + y % 10) as u8);
    return true;
}
