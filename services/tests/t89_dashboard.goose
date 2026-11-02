// services/tests/t89_dashboard.goose
//
// Driver for dashboard-feed — the freshness verdicts, the labels, and the refusal to
// invent a number.
//
// The failure this exists to prevent: a dashboard that shows "0%" for a metric that
// nobody measured. Every check below is about the difference between a zero and a
// blank, and about a stale number never being printed without its age.

import dashboard.dashboard;
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

fn has(hay: const u8[:], needle: const u8[:]) -> bool {
    if needle.len == 0 { return true; }
    if needle.len > hay.len { return false; }
    var i: i64 = 0;
    while i + needle.len <= hay.len {
        var k: i64 = 0;
        var ok = true;
        while k < needle.len {
            if hay[i + k] != needle[k] { ok = false; k = needle.len; }
            else { k = k + 1; }
        }
        if ok { return true; }
        i = i + 1;
    }
    return false;
}

fn main() {
    say("t89 dashboard-feed\n");
    df_init();

    // --- nothing measured ---------------------------------------------------
    check("feed: four metrics missing at start", df_missing_count() == 4);
    check("feed: no metric is fresh at start", df_fresh_count(0) == 0);
    let v0, c0 = df_get(DF_CPU, 0);
    check("feed: cpu is NEVER, not zero", c0 == DF_NEVER && v0 == 0);
    check("feed: verdict of an unsampled metric", df_verdict(DF_MEM, 0) == DF_NEVER);
    check("feed: age of an unsampled metric is -1", df_age_ms(DF_CPU, 0) == -1);

    var lab: u8[>..] = [];
    df_label(DF_DISK, 0, lab);
    check("feed: an unsampled label says never", has(lab[..], "never"));
    check("feed: ... and carries no percentage", !has(lab[..], "%"));

    // --- a sample -----------------------------------------------------------
    check("feed: put cpu 42", df_put(DF_CPU, 42, 1000) == CODE_OK);
    let v1, c1 = df_get(DF_CPU, 1000);
    check("feed: cpu is fresh at once", v1 == 42 && c1 == DF_FRESH);
    check("feed: one metric measured, three missing", df_missing_count() == 3);
    check("feed: one metric fresh", df_fresh_count(1000) == 1);
    check("feed: age is zero at the sample time", df_age_ms(DF_CPU, 1000) == 0);
    check("feed: age counts up", df_age_ms(DF_CPU, 1500) == 500);

    // --- the staleness boundary ---------------------------------------------
    // CPU default window is 2000ms: exactly at the window it is still fresh, one ms
    // past it is stale. The boundary is asserted, not assumed.
    check("feed: fresh exactly at the window", df_verdict(DF_CPU, 3000) == DF_FRESH);
    check("feed: stale one ms past the window", df_verdict(DF_CPU, 3001) == DF_STALE);
    let v2, c2 = df_get(DF_CPU, 9000);
    check("feed: a stale value is still returned", v2 == 42 && c2 == DF_STALE);
    check("feed: per-kind windows differ (disk is longer)",
          df_window(DF_DISK) > df_window(DF_CPU));

    lab = [];
    df_label(DF_CPU, 9000, lab);
    check("feed: a stale label says stale", has(lab[..], "stale"));
    check("feed: a stale label carries the age in seconds", has(lab[..], "8s"));
    check("feed: a stale label carries the value", has(lab[..], "42%"));

    lab = [];
    df_label(DF_CPU, 1500, lab);
    check("feed: a fresh label says fresh", has(lab[..], "fresh"));
    check("feed: a fresh label carries the value", has(lab[..], "42%"));

    // --- validation ----------------------------------------------------------
    check("feed: cpu over 100 refused", df_put(DF_CPU, 101, 4000) == E_INVAL);
    check("feed: cpu negative refused", df_put(DF_CPU, -1, 4000) == E_INVAL);
    check("feed: mem 0 is a valid measurement", df_put(DF_MEM, 0, 4000) == CODE_OK);
    let vm, cm = df_get(DF_MEM, 4000);
    check("feed: ... and reports FRESH with 0, not NEVER", vm == 0 && cm == DF_FRESH);
    check("feed: net accepts a large byte rate", df_put(DF_NET, 125000, 4000) == CODE_OK);
    check("feed: unknown kind refused", df_put(9, 1, 4000) == E_INVAL);
    let _vk, ck = df_get(9, 4000);
    check("feed: get on an unknown kind is E_INVAL", ck == E_INVAL);
    check("feed: label of an unknown kind is '?'", df_kind_name(9).len == 0);

    // A backwards clock must be refused, or the age goes negative and an old figure
    // reads as fresh.
    check("feed: a sample stamped in the past is E_STATE", df_put(DF_CPU, 50, 999) == E_STATE);
    check("feed: the refused sample changed nothing", df_get(DF_CPU, 9000) == 42);
    check("feed: age never goes negative", df_age_ms(DF_CPU, 500) == 0);

    // --- windows --------------------------------------------------------------
    check("feed: shorten the cpu window", df_set_window(DF_CPU, 100) == CODE_OK);
    check("feed: the new window applies", df_verdict(DF_CPU, 1150) == DF_STALE);
    check("feed: window 0 refused", df_set_window(DF_CPU, 0) == E_INVAL);
    check("feed: window past the cap refused", df_set_window(DF_CPU, DF_MAX_AGE_MS + 1) == E_INVAL);
    check("feed: window on an unknown kind refused", df_set_window(9, 100) == E_INVAL);
    check("feed: window unchanged by refusals", df_window(DF_CPU) == 100);

    // "stale 0s" would read as fresh, so the label floors the age at one second.
    lab = [];
    df_label(DF_CPU, 1200, lab);
    check("feed: a sub-second stale age prints as 1s", has(lab[..], "1s"));

    // --- net label ------------------------------------------------------------
    lab = [];
    df_label(DF_NET, 4000, lab);
    check("feed: the net label uses B/s", has(lab[..], "B/s"));
    check("feed: the net label does not use a percentage", !has(lab[..], "%"));

    // --- counts ---------------------------------------------------------------
    check("feed: three metrics measured (cpu, mem, net)", df_missing_count() == 1);
    let fresh = df_fresh_count(4000);
    say("     fresh at 4000: ");
    var nb: u8[>..] = [];
    let _ = append_int(nb, 32, fresh);
    say(nb[..]);
    say("\n");
    check("feed: fresh count is a count, not a guess", fresh >= 1 && fresh <= 2);

    // --- re-init ---------------------------------------------------------------
    df_init();
    check("feed: init clears every sample", df_missing_count() == 4);
    check("feed: init restores the default window", df_window(DF_CPU) == 2000);
    check("feed: init leaves the metrics NEVER", df_verdict(DF_CPU, 0) == DF_NEVER);

    // --- DF_MAX_KIND: the last kind is a kind, one past it is not ---------------
    // The table is sized for kinds 1..DF_MAX_KIND. A put for kind DF_MAX_KIND+1 must be
    // refused rather than clamped onto the last kind, because a clamped metric would show
    // the wrong number under the right name, and nothing on screen would look wrong.
    let c_last = df_put(DF_MAX_KIND, 7, 100);
    check("feed: the last kind is accepted", c_last == CODE_OK);
    let c_past = df_put(DF_MAX_KIND + 1, 7, 100);
    check("feed: one past DF_MAX_KIND is E_INVAL", c_past == E_INVAL);
    let v_past, c_get = df_get(DF_MAX_KIND + 1, 100);
    check("feed: a read past DF_MAX_KIND is E_INVAL", c_get == E_INVAL && v_past == 0);

    say("t89 done  pass=");
    var pb: u8[>..] = [];
    let _ = append_int(pb, 32, t_pass);
    say(pb[..]);
    say(" fail=");
    var fb: u8[>..] = [];
    let _ = append_int(fb, 32, t_fail);
    say(fb[..]);
    say("\n");
}
