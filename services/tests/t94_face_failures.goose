// services/tests/t94_face_failures.goose
//
// The six face services, driven into the failure each one would fail quietly with.
//
// WHY THIS FILE EXISTS
// --------------------
// t86…t93 drive the happy path and the obvious refusals. The failures left over are the
// ones nobody notices in a demo: a table that fills up one entry later than the docs say,
// an import that applies the first four lines and drops the fifth, a clock that goes
// backwards and makes an old reading look fresh, a STOP file that arrives *after* an
// update was offered and is therefore never consulted.
//
// Each section names the property, drives the failure, and then asserts the state did not
// move. "Refused" on its own is not enough: the defect is a refusal that leaves half of
// something behind.
//
// Status: RUNS — set by `audit_status.py` from the runner's row, not by hand.

import settings.settings;
import wallpaper.wallpaper;
import dock.dock;
import dashboard.dashboard;
import board.board;
import updater_client.updater_client;
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

// Load a literal into a fixed buffer and return its length, so a test can hand a service
// exactly the bytes it wants it to refuse — including the malformed ones.
fn load(data: const u8[:], out: u8[..512]&) -> i64 {
    var i: i64 = 0;
    while i < data.len { out[i] = data[i]; i = i + 1; }
    return data.len;
}

fn main() {
    say("t94 face service failures\n");

    // ======================================================================
    // 1. settings — a write out of range, and an import that must apply nothing
    // ======================================================================
    st_init();
    // The wallpaper index is checked against the registry's ceiling at the write, so a
    // settings file can never hold an index nothing can select.
    check("settings: wallpaper 8 is refused", st_put_int(SK_WALLPAPER, 8) == E_INVAL);
    check("settings: a colour above 0xffffff is refused",
          st_put_int(SK_BG, 0x1000000) == E_INVAL);
    check("settings: a negative colour is refused", st_put_int(SK_BG, -1) == E_INVAL);
    check("settings: mode 9 is refused", st_put_int(SK_MODE, 9) == E_INVAL);
    check("settings: a 32-byte hostname is refused (31 is the largest)",
          st_put_text(SK_HOSTNAME, str("aaaaabbbbbcccccdddddeeeeefffffgg")[..32]) == E_NOROOM);
    check("settings: a hostname with a space is refused",
          st_put_text(SK_HOSTNAME, str("two words")[..9]) == E_INVAL);
    check("settings: an unknown key id is refused", st_put_int(9, 1) == E_INVAL);

    // A refused write is not a change, so the dirty count is still zero. This is checked
    // before the accepted write below, because an accepted write is a change.
    check("settings: no refused write dirtied an entry", st_dirty_count() == 0);
    check("settings: wallpaper 7 is accepted", st_put_int(SK_WALLPAPER, 7) == CODE_OK);

    // Atomic import. The blob is valid up to its last line and corrupt in it; a parser
    // that committed as it went would leave the hostname changed and the wallpaper lost.
    let _cs = st_put_text(SK_HOSTNAME, str("keep")[..4]);
    let _cw = st_put_int(SK_WALLPAPER, 2);
    check("settings: two writes are dirty before the import", st_dirty_count() == 2);
    var bad: u8[..512] = [0; 512];
    let badn = load("1=5\n6=changed\n9=1\n", bad);        // 9 is not a key
    check("settings: an import with an unknown key is refused", st_import(bad[..badn]) == E_CORRUPT);
    let wall_after, _g1 = st_get_int(SK_WALLPAPER);
    check("settings: the refused import changed no wallpaper", wall_after == 2);
    check("settings: the refused import changed no hostname",
          st_get_text(SK_HOSTNAME) == str("keep")[..4]);

    var range: u8[..512] = [0; 512];
    let rangen = load("1=5\n4=9\n", range);               // mode 9 does not exist
    check("settings: an out-of-range value in the file is refused",
          st_import(range[..rangen]) == E_CORRUPT);
    let wall_range, _g2 = st_get_int(SK_WALLPAPER);
    check("settings: the in-range line before it was not applied", wall_range == 2);

    var blank: u8[..512] = [0; 512];
    let blankn = load("1=3\n\n", blank);                  // an empty line
    check("settings: a blank line is refused, not skipped", st_import(blank[..blankn]) == E_CORRUPT);

    // ======================================================================
    // 2. wallpaper — the registry at its ceiling, and a select that must not blank
    // ======================================================================
    wl_init();
    let _d0, cd0 = wl_register(str("a")[..1], WL_KIND_STATIC, 0);
    let _d1, cd1 = wl_register(str("b")[..1], WL_KIND_LIVE, 60);
    let _f1, cf1 = wl_register(str("fast")[..4], WL_KIND_LIVE, 61);
    check("wallpaper: fps above the ceiling is refused", cf1 == E_INVAL);
    let _f2, cf2 = wl_register(str("slow")[..4], WL_KIND_LIVE, 0);
    check("wallpaper: a live wallpaper with no budget is refused", cf2 == E_INVAL);
    let _f3, cf3 = wl_register(str("mix")[..3], WL_KIND_STATIC, 30);
    check("wallpaper: a static wallpaper with an fps is refused", cf3 == E_INVAL);
    let _f4, cf4 = wl_register(str("aaaaaaaaaaaaaaaaaaaa")[..20], WL_KIND_STATIC, 0);
    check("wallpaper: a name of exactly WL_NAME_MAX is refused", cf4 == E_NOROOM);
    let _f5, cf5 = wl_register(str("a")[..1], WL_KIND_STATIC, 0);
    check("wallpaper: a duplicate name is refused", cf5 == E_STATE);
    let _ = cf1; let _ = cf2; let _ = cf3; let _ = cf4; let _ = cf5;

    // Fill to WL_MAX (8). Six more after a and b.
    let _d2, cd2 = wl_register(str("c")[..1], WL_KIND_STATIC, 0);
    let _d3, cd3 = wl_register(str("d")[..1], WL_KIND_STATIC, 0);
    let _d4, cd4 = wl_register(str("e")[..1], WL_KIND_STATIC, 0);
    let _d5, cd5 = wl_register(str("f")[..1], WL_KIND_STATIC, 0);
    let _d6, cd6 = wl_register(str("g")[..1], WL_KIND_STATIC, 0);
    let _d7, cd7 = wl_register(str("h")[..1], WL_KIND_STATIC, 0);
    check("wallpaper: eight register", wl_count_() == 8);
    check("wallpaper: registration refusals did not consume an id", cd7 == CODE_OK);
    let n9, cn9 = wl_register(str("i")[..1], WL_KIND_STATIC, 0);
    check("wallpaper: the ninth is E_NO_SPACE", cn9 == E_NO_SPACE && n9 == WL_NEVER);
    check("wallpaper: still eight after the refusal", wl_count_() == 8);
    let _ = cd0; let _ = cd1; let _ = cd2; let _ = cd3;
    let _ = cd4; let _ = cd5; let _ = cd6;

    // Selecting nothing must not blank the screen: the previous wallpaper stays current.
    check("wallpaper: select a real one", wl_select(1, 100) == CODE_OK);
    check("wallpaper: select an unregistered id is E_NOTFOUND",
          wl_select(9, 200) == E_NOTFOUND);
    check("wallpaper: the unregistered select did not change what is drawn",
          same(wl_current_name(), str("b")[..1]));
    check("wallpaper: select -1 is E_NOTFOUND", wl_select(WL_NEVER, 300) == E_NOTFOUND);

    // ======================================================================
    // 3. settings -> wallpaper: the index the store holds, and what happens when the
    //    registry cannot honour it
    // ======================================================================
    st_init();
    // A fresh registry with two entries: id 7 is inside the store's range and inside the
    // registry's ceiling, but this registry has no id 7 in it. The screen must show the
    // last wallpaper, not a blank.
    wl_init();
    let _k0, ck0 = wl_register(str("dunes")[..5], WL_KIND_STATIC, 0);
    let _k1, ck1 = wl_register(str("aurora")[..6], WL_KIND_LIVE, 30);
    check("wallpaper: the small registry has two entries", ck0 == CODE_OK && ck1 == CODE_OK);
    check("wallpaper: select the second", wl_select(1, 300) == CODE_OK);
    let cfg_wall, _cw3 = st_get_int(SK_WALLPAPER);         // the default index
    check("settings: the default wallpaper index is inside the registry ceiling",
          cfg_wall >= 0 && cfg_wall <= SET_WALLPAPER_MAX);
    let _ = st_put_int(SK_WALLPAPER, 7);
    let want, _cw4 = st_get_int(SK_WALLPAPER);
    check("settings: 7 is storable", want == 7);
    check("wallpaper: a stored index the registry does not have is refused",
          wl_select(want, 400) == E_NOTFOUND);
    check("wallpaper: the screen still shows the last good wallpaper",
          same(wl_current_name(), str("aurora")[..6]));

    // ======================================================================
    // 4. dock — a result nobody asked for, and a dock at its ceiling
    // ======================================================================
    dk_init();
    let p1, cp1 = dk_pin(str("notes")[..5]);
    check("dock: pin one", cp1 == CODE_OK && p1 == 1);
    check("dock: launch an id that does not exist is E_NOTFOUND",
          dk_launch(99, 1000) == E_NOTFOUND);
    check("dock: a result for a launch never requested is E_STATE",
          dk_result(p1, true) == E_STATE);
    check("dock: the bogus result did not start the app", !dk_running_at(0));
    check("dock: a launch nobody answers expires",
          dk_launch(p1, 2000) == CODE_OK && dk_expire(2000 + DK_LAUNCH_TIMEOUT_MS) == 1);
    check("dock: an expiry is a failure", dk_failures_of(p1) == 1);

    // Fill to DK_MAX (12): eleven more pins. Duplicate and long names are refused on the
    // way, and neither may add an entry.
    let dp1, cdp1 = dk_pin(str("notes")[..5]);
    check("dock: a duplicate pin is E_STATE", cdp1 == E_STATE && dp1 < 0);
    let dp2, cdp2 = dk_pin(str("aaaaaaaaaaaaaaaa")[..16]);
    check("dock: a name of exactly DK_NAME_MAX is refused", cdp2 == E_NOROOM && dp2 < 0);
    check("dock: the refusals added nothing", dk_count() == 1);
    let _q2, dq2 = dk_pin(str("p02")[..3]);
    let _q3, dq3 = dk_pin(str("p03")[..3]);
    let _q4, dq4 = dk_pin(str("p04")[..3]);
    let _q5, dq5 = dk_pin(str("p05")[..3]);
    let _q6, dq6 = dk_pin(str("p06")[..3]);
    let _q7, dq7 = dk_pin(str("p07")[..3]);
    let _q8, dq8 = dk_pin(str("p08")[..3]);
    let _q9, dq9 = dk_pin(str("p09")[..3]);
    let _q10, dq10 = dk_pin(str("p10")[..3]);
    let _q11, dq11 = dk_pin(str("p11")[..3]);
    let _q12, dq12 = dk_pin(str("p12")[..3]);
    let _ = dq2; let _ = dq3; let _ = dq4; let _ = dq5; let _ = dq6;
    let _ = dq7; let _ = dq8; let _ = dq9; let _ = dq10; let _ = dq11; let _ = dq12;
    check("dock: twelve pins fill it", dk_count() == 12);
    let dp13, cdp13 = dk_pin(str("p13")[..3]);
    check("dock: the thirteenth is E_NO_SPACE", cdp13 == E_NO_SPACE && dp13 < 0);
    check("dock: still twelve", dk_count() == 12);

    // A restart wipes the pins. The ids restart at 1, which is why a launch result that
    // arrives after a restart must be matched to the request, not to the number.
    dk_init();
    check("dock: a restart leaves an empty dock", dk_count() == 0);
    let r1, cr1 = dk_pin(str("notes")[..5]);
    check("dock: ids restart at 1 after a restart", cr1 == CODE_OK && r1 == 1);
    check("dock: nothing is running after a restart", dk_running_count() == 0);

    // ======================================================================
    // 5. dashboard — a clock that goes backwards, and a producer that restarts
    // ======================================================================
    df_init();
    check("feed: cpu 140% is refused", df_put(DF_CPU, 140, 1000) == E_INVAL);
    check("feed: a negative byte rate is refused", df_put(DF_NET, -1, 1000) == E_INVAL);
    check("feed: a kind outside the four is refused", df_put(DF_MAX_KIND + 1, 1, 1000) == E_INVAL);
    check("feed: a zero window is refused", df_set_window(DF_CPU, 0) == E_INVAL);
    check("feed: a window past the ceiling is refused",
          df_set_window(DF_CPU, DF_MAX_AGE_MS + 1) == E_INVAL);
    check("feed: a sample at 5000 is accepted", df_put(DF_CPU, 12, 5000) == CODE_OK);
    check("feed: a sample stamped in the past is refused",
          df_put(DF_CPU, 99, 4000) == E_STATE);
    let cpu_v, vcpu = df_get(DF_CPU, 5000);
    check("feed: the refused sample did not land", cpu_v == 12 && vcpu == DF_FRESH);
    // Time going backwards on the *read* side cannot fabricate a negative age; the age
    // floors at zero, and a value is never reported fresh from the future.
    check("feed: a read at a backwards clock reports age 0",
          df_age_ms(DF_CPU, 1000) == 0);

    // A producer that restarts forgets. Nothing may come back from the previous run.
    df_init();
    let _, vgone = df_get(DF_CPU, 5000);
    check("feed: a restart leaves no sample at all", vgone == DF_NEVER);
    check("feed: a restart leaves all four missing", df_missing_count() == 4);

    // ======================================================================
    // 6. board — an import that must apply nothing, and a record it does not know
    // ======================================================================
    bd_init();
    let g, cg = bd_room_add(str("general")[..7]);
    let bp1, cb1 = bd_post(g, str("first")[..5], 1000);
    check("board: one room and one post to protect", cg == CODE_OK && cb1 == CODE_OK);

    // The file format carries no version byte, so a file from a different build shows up
    // as a record kind this build does not know. It must refuse the whole file.
    var ver: u8[..512] = [0; 512];
    let vern = load("R,1,imported\nV,2\n", ver);
    check("board: an unknown record kind refuses the import", bd_import(ver[..vern]) == E_CORRUPT);
    check("board: the room before it was not applied", bd_room_count() == 1);
    check("board: the live room is still general", same(bd_room_name_at(0), str("general")[..7]));
    check("board: the post survived the refused import", bd_post_total() == 1);

    // A post in a room the file does not define is refused, not dropped.
    var orphan: u8[..512] = [0; 512];
    let orphann = load("R,1,general\nP,9,7,1000,orphan\n", orphan);
    check("board: a post in an undefined room refuses the import",
          bd_import(orphan[..orphann]) == E_CORRUPT);
    check("board: the board is unchanged", bd_post_total() == 1 && bd_room_count() == 1);

    // A record that parses up to a bad field is still a corrupt file.
    var shortln: u8[..512] = [0; 512];
    let shortn = load("R,1,general\nP,2,1,1000\n", shortln);   // no text field
    check("board: a post with no text refuses the import", bd_import(shortln[..shortn]) == E_CORRUPT);
    check("board: the id counter did not move", bd_post_total() == 1);
    let nextp, cnx = bd_post(g, str("second")[..6], 2000);
    check("board: a post after the refusals still takes the next id",
          cnx == CODE_OK && nextp == bp1 + 1);

    // The ceilings: rooms at BD_MAX_ROOMS, posts at BD_MAX_POSTS.
    let _r2, cr2 = bd_room_add(str("beta")[..4]);
    let _r3, cr3 = bd_room_add(str("gamma")[..5]);
    let _r4, cr4 = bd_room_add(str("delta")[..5]);
    let _ = cr2; let _ = cr3; let _ = cr4;
    check("board: four rooms fill it", bd_room_count() == BD_MAX_ROOMS);
    let r5, cr5 = bd_room_add(str("epsilon")[..7]);
    check("board: the fifth room is E_NO_SPACE", cr5 == E_NO_SPACE && r5 < 0);

    // ======================================================================
    // 7. updater_client — a STOP file that arrives after the update was offered
    // ======================================================================
    uc_init(0);
    check("updater: 1.4 is offered",
          uc_check(false, 14, true, true, 100000) == UC_AVAILABLE);
    check("updater: the offer is recorded", uc_available_version() == 14);
    // The operator drops a STOP file in before the apply runs. STOP wins over everything,
    // including an offer already on the table: there is nothing available to apply once
    // the machine has been told to stop.
    check("updater: the next check reports STOP",
          uc_check(true, 14, true, true, 200000) == UC_REFUSED_STOP);
    check("updater: the STOP cancelled the offer", uc_available_version() == 0);
    let st1, code1 = uc_status();
    check("updater: the client is idle again", st1 == UC_S_IDLE && code1 == UC_REFUSED_STOP);
    check("updater: apply with no offer is E_STATE", uc_apply(true) == E_STATE);
    check("updater: nothing was applied", uc_applied_version() == 0);
    check("updater: the applied count is still zero", uc_applied_total() == 0);
    check("updater: the STOP was counted", uc_stop_count() == 1);
    // With the file removed the offer can be made again, in the same window, because a
    // STOP refusal does not advance the rate clock.
    check("updater: with STOP gone the offer returns",
          uc_check(false, 14, true, true, 200000) == UC_AVAILABLE);
    check("updater: and it applies", uc_apply(true) == CODE_OK && uc_applied_version() == 14);

    // The rate clock: a check inside UC_MIN_INTERVAL_MS is refused, and a backwards clock
    // is inside the window, because refusing is the safe direction.
    check("updater: a second check a minute early is rate limited",
          uc_check(false, 15, true, true, 200000 + UC_MIN_INTERVAL_MS - 1) == UC_REFUSED_RATE);
    check("updater: a backwards clock is inside the window",
          uc_check(false, 15, true, true, 1000) == UC_REFUSED_RATE);
    check("updater: the rate refusals are counted", uc_rate_count() == 2);
    let st2, code2 = uc_status();
    check("updater: neither refusal moved the client out of DONE",
          st2 == UC_S_DONE && uc_applied_version() == 14);
    let _ = code2;

    say("t94 done  pass=");
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
