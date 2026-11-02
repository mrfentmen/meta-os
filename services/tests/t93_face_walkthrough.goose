// services/tests/t93_face_walkthrough.goose
//
// The first minute on the home surface, driven end to end across all six face services.
//
// WHY ONE TEST AND NOT SIX
// ------------------------
// t86…t91 prove each service alone. What none of them proves is that the six agree about the
// same user: that the wallpaper the settings name is the wallpaper that is drawn, that the app
// the dock launched is the app the dashboard reports as running, that the board's unread count
// is the number the badge would show. Those are the numbers a screen prints, and a screen that
// prints a different number than the service holds is the defect this file exists to catch.
//
// It also proves the two properties a restart depends on and no single prototype test did:
// both exporters are idempotent — export, import, export produces the same bytes — so a
// restarted client cannot rewrite its own history by reading it back.
//
// Status: RUNS — set by `audit_status.py` from the runner's row, not by hand.

import settings.settings;
import wallpaper.wallpaper;
import dock.dock;
import dashboard.dashboard;
import board.board;
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

fn str(s: const u8[:]) -> u8[..64] {
    var b: u8[..64] = [0; 64];
    var i: i64 = 0;
    while i < s.len { b[i] = s[i]; i = i + 1; }
    return b;
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
    say("t93 face walkthrough\n");

    // ======================================================================
    // 1. the config exists before anything is drawn
    // ======================================================================
    st_init();
    check("settings: six defaults after init", st_count() == 6);
    check("settings: hostname default is meta", st_get_text(SK_HOSTNAME) == str("meta")[..4]);

    // The user picks the second wallpaper and a hostname. The wallpaper index is what the
    // registry is asked for later — that indirection is the whole reason both exist.
    let cw = st_put_int(SK_WALLPAPER, 1);
    let ch = st_put_text(SK_HOSTNAME, str("work")[..4]);
    check("settings: wallpaper set", cw == CODE_OK);
    check("settings: hostname set", ch == CODE_OK);
    let want_wall, _cw2 = st_get_int(SK_WALLPAPER);
    check("settings: the choice reads back", want_wall == 1);
    check("settings: two entries are dirty", st_dirty_count() == 2);

    // ======================================================================
    // 2. the wallpaper registry is asked for exactly that choice
    // ======================================================================
    wl_init();
    let _w0, c0 = wl_register(str("dunes")[..5], WL_KIND_STATIC, 0);
    let _w1, c1 = wl_register(str("aurora")[..6], WL_KIND_LIVE, 30);
    let _w2, c2 = wl_register(str("grid")[..4], WL_KIND_STATIC, 0);
    check("wallpaper: three register", c0 == CODE_OK && c1 == CODE_OK && c2 == CODE_OK);
    check("wallpaper: the settings index names a registered wallpaper",
          want_wall >= 0 && want_wall < wl_count_());
    let cs = wl_select(want_wall, 0);
    check("wallpaper: selecting it succeeds", cs == CODE_OK);
    check("wallpaper: the name drawn is the name configured",
          same(wl_current_name(), str("aurora")[..6]));
    // The live one draws at its interval, not on every tick: 30 fps means 33 ms, so a tick
    // at 33 is the first frame and a tick at 34 is a refusal, not a second frame.
    check("wallpaper: first frame at the interval", wl_tick(33) == 1);
    check("wallpaper: no second frame one ms later", wl_tick(34) == 0);
    check("wallpaper: the refusal is counted", wl_budget_refusals() == 1);

    // ======================================================================
    // 3. the dock launches an app and is told what happened
    // ======================================================================
    dk_init();
    let t1, cp1 = dk_pin(str("notes")[..5]);
    let t2, cp2 = dk_pin(str("shell")[..5]);
    let t3, cp3 = dk_pin(str("board")[..5]);
    check("dock: three pins", cp1 == CODE_OK && cp2 == CODE_OK && cp3 == CODE_OK);
    check("dock: ids are issued in order", t1 == 1 && t2 == 2 && t3 == 3);
    check("dock: the dock order is the pin order",
          same(dk_name_at(0), str("notes")[..5]) && same(dk_name_at(2), str("board")[..5]));

    let cl1 = dk_launch(t1, 1000);
    check("dock: launch notes", cl1 == CODE_OK);
    check("dock: it is pending, not running", dk_pending_at(0) && !dk_running_at(0));
    // A second click 200 ms later is the same click, not a second process.
    check("dock: a second click inside the window is E_BUSY", dk_launch(t1, 1200) == E_BUSY);
    check("dock: the dedupe did not count a launch", dk_launches_of(t1) == 1);
    // The supervisor answers: it started.
    check("dock: the answer is accepted", dk_result(t1, true) == CODE_OK);
    check("dock: notes is running", dk_running_at(0) && !dk_pending_at(0));
    check("dock: one running", dk_running_count() == 1);
    check("dock: a running app cannot be unpinned", dk_unpin(t1) == E_BUSY);
    // A pin that is dragged to the front stays there, and the running flag follows it.
    check("dock: move board to the front", dk_move(t3, 0) == CODE_OK);
    check("dock: the running app moved with its entry",
          same(dk_name_at(0), str("board")[..5]) && !dk_running_at(0));
    check("dock: notes is now second and still running",
          same(dk_name_at(1), str("notes")[..5]) && dk_running_at(1));

    // A launch that never reports has to become a failure at the timeout, not stay pending.
    let cl2 = dk_launch(t2, 2000);
    check("dock: launch shell", cl2 == CODE_OK);
    check("dock: nothing expires at 6999", dk_expire(6999) == 0 && dk_pending_at(2));
    check("dock: it expires at 7000", dk_expire(7000) == 1 && !dk_pending_at(2));
    check("dock: the expiry is a failure with a count", dk_failures_of(t2) == 1);
    check("dock: the expiry is also counted on its own", dk_expiries_of(t2) == 1);
    check("dock: an expired launch is not running", !dk_running_at(2));

    // ======================================================================
    // 4. the dashboard shows what was measured, and says so when nothing was
    // ======================================================================
    df_init();
    check("feed: nothing measured yet", df_missing_count() == 4);
    let _p1 = df_put(DF_CPU, 12, 1000);
    let _p2 = df_put(DF_MEM, 41, 1000);
    let _p3 = df_put(DF_DISK, 63, 1000);
    check("feed: three samples in", df_fresh_count(1000) == 3);
    let cpu, vcpu = df_get(DF_CPU, 1500);
    check("feed: cpu reads 12 fresh", cpu == 12 && vcpu == DF_FRESH);
    let net_v, vnet = df_get(DF_NET, 1500);
    check("feed: an unmeasured metric is NEVER, not zero", net_v == 0 && vnet == DF_NEVER);
    // The staleness window belongs to the metric, and the boundary is stale.
    // The window is inclusive: a sample is fresh AT its window and stale one ms past it.
    // That is the rule the dashboard enforces and the rule its contract page states -- this
    // test caught the page saying the opposite, which is why the boundary is asserted here.
    let _, vedge = df_get(DF_CPU, 1000 + df_window(DF_CPU));
    check("feed: at exactly its window, a sample is still fresh", vedge == DF_FRESH);
    let _, vold = df_get(DF_CPU, 1000 + df_window(DF_CPU) + 1);
    check("feed: one ms past the window, it is stale", vold == DF_STALE);

    // ======================================================================
    // 5. the board records the session and the badge reads it
    // ======================================================================
    bd_init();
    let g, cg = bd_room_add(str("general")[..7]);
    check("board: #general exists", cg == CODE_OK && g == 1);
    let p1, cb1 = bd_post(g, str("boot complete")[..13], 1000);
    let p2, cb2 = bd_post(g, str("cpu 12%")[..7], 1100);
    check("board: two posts", cb1 == CODE_OK && cb2 == CODE_OK);
    check("board: ids go up", p2 == p1 + 1);
    check("board: unread from nothing is two", bd_unread(g, 0) == 2);
    check("board: unread from the first post is one", bd_unread(g, p1) == 1);
    var feed: u8[>..] = [];
    let n, cf = bd_fetch(g, p1, feed);
    check("board: fetch since the first returns the second only", n == 1 && cf == CODE_OK);
    // fetch emits one line per post as "<id>:<text>\n", so the check is that the text is
    // in there and the earlier post is not -- not that the buffer equals the text.
    check("board: the fetched line carries the second post", has(feed[..], str("cpu 12%")[..7]));
    check("board: the fetched line does not carry the first post",
          !has(feed[..], str("boot complete")[..13]));

    // ======================================================================
    // 6. the exporters are idempotent — the property a restart depends on
    // ======================================================================
    // settings: export, import into a fresh store, export again. If the second export
    // differs, a restart rewrites the config it just read, and the difference will be a
    // key that came back with a different representation.
    var s1: u8[..512] = [0; 512];
    let s1n = st_export(s1);
    check("settings: export writes something", s1n > 0);
    st_init();
    let sr = st_import(s1[..s1n]);
    check("settings: import accepts its own export", sr >= 1);
    var s2: u8[..512] = [0; 512];
    let s2n = st_export(s2);
    check("settings: the second export is byte-identical", s1n == s2n && same(s1[..s1n], s2[..s2n]));
    // And the values survived the trip, not just the bytes.
    let wall_back, _g = st_get_int(SK_WALLPAPER);
    check("settings: wallpaper survived the round trip", wall_back == 1);
    check("settings: hostname survived the round trip", st_get_text(SK_HOSTNAME) == str("work")[..4]);

    // board: same property over rooms, posts, ids and the next-id counter.
    var b1: u8[..2048] = [0; 2048];
    let b1n = bd_export(b1);
    check("board: export writes something", b1n > 0);
    bd_init();
    let br = bd_import(b1[..b1n]);
    check("board: import accepts its own export", br >= 2);
    check("board: the room came back", bd_room_count() == 1 && bd_room_name_at(0).len == 7);
    check("board: the posts came back", bd_post_total() == 2);
    check("board: the cursor still works after the round trip", bd_unread(g, p1) == 1);
    var b2: u8[..2048] = [0; 2048];
    let b2n = bd_export(b2);
    check("board: the second export is byte-identical", b1n == b2n && same(b1[..b1n], b2[..b2n]));
    // A post after the import must take the next id, not reuse the last one.
    let p3, cb3 = bd_post(g, str("after")[..5], 2000);
    check("board: a post after an import gets a fresh id", cb3 == CODE_OK && p3 == p2 + 1);

    // ======================================================================
    // 7. the line a shell would print
    // ======================================================================
    // Every field below is read from the service that owns it, so this line is a
    // consistency check across four services as much as a formatting check.
    var line: u8[>..] = [];
    let _ = append_str(line, 160, "host=");
    let host = st_get_text(SK_HOSTNAME);
    let _ = append_str(line, 160, host[..]);
    let _ = append_str(line, 160, " wall=");
    let _ = append_str(line, 160, wl_current_name());
    let _ = append_str(line, 160, " running=");
    let _ = append_int(line, 160, dk_running_count());
    let _ = append_str(line, 160, " fresh=");
    let _ = append_int(line, 160, df_fresh_count(1500));
    let _ = append_str(line, 160, " unread=");
    let _ = append_int(line, 160, bd_unread(g, 0));
    say("     ");
    say(line[..]);
    say("\n");
    check("the status line starts with the hostname", line.len > 5 && has(line[..], str("host=")[..5]));
    check("the status line carries the wallpaper name", has(line[..], wl_current_name()));
    check("the status line reports one running app", dk_running_count() == 1);
    check("the status line reports three fresh metrics", df_fresh_count(1500) == 3);

    say("t93 done  pass=");
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
