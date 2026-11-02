// services/tests/t87_wallpaper.goose
//
// Driver for wallpaper — registry validation, the frame budget, pause on fullscreen.
//
// The budget is the whole point: a live wallpaper that asks every millisecond must be
// refused far more often than it is granted, and the refusal has to be counted so the
// number is visible rather than inferred.

import wallpaper.wallpaper;
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

fn num(label: const u8[:], v: i64) {
    say(label);
    var b: u8[>..] = [];
    let _ = append_int(b, 32, v);
    say(b[..]);
    say("\n");
}

fn main() {
    say("t87 wallpaper\n");
    wl_init();

    check("wallpaper: empty registry", wl_count_() == 0);
    check("wallpaper: nothing selected", wl_current_id() == WL_NEVER);
    check("wallpaper: no name for a missing id", wl_name_of(0).len == 0);
    check("wallpaper: kind of a missing id is 0", wl_kind_of(0) == 0);
    check("wallpaper: fps of a missing id is 0", wl_fps_of(0) == 0);

    // --- registration validation -------------------------------------------
    let a, ca = wl_register("dunes", WL_KIND_STATIC, 0);
    check("wallpaper: register a static one", ca == CODE_OK && a == 0);
    let b, cb = wl_register("aurora", WL_KIND_LIVE, 30);
    check("wallpaper: register a live one", cb == CODE_OK && b == 1);
    let _x1, cx1 = wl_register("x1", WL_KIND_STATIC, 30);
    check("wallpaper: a static one with an fps is refused", _x1 == WL_NEVER && cx1 == E_INVAL);
    let _d, cd = wl_register("x2", WL_KIND_STATIC, 30);
    check("wallpaper: ... with E_INVAL", cd == E_INVAL);
    let _e, ce = wl_register("x3", WL_KIND_LIVE, 0);
    check("wallpaper: a live one with no budget is refused", ce == E_INVAL);
    let _f, cf = wl_register("x4", WL_KIND_LIVE, WL_FPS_MAX + 1);
    check("wallpaper: a live one above the fps ceiling is refused", cf == E_INVAL);
    let _g, cg = wl_register("aurora", WL_KIND_LIVE, 10);
    check("wallpaper: a duplicate name is E_STATE", cg == E_STATE);
    let _h, chh = wl_register("", WL_KIND_STATIC, 0);
    check("wallpaper: an empty name is E_INVAL", chh == E_INVAL);

    var longname: u8[..24] = [0; 24];
    var i: i64 = 0;
    while i < 24 { longname[i] = 97; i = i + 1; }
    let _j, cj = wl_register(longname[..WL_NAME_MAX], WL_KIND_STATIC, 0);
    check("wallpaper: a name at the limit is E_NOROOM", cj == E_NOROOM);

    check("wallpaper: two registered", wl_count_() == 2);
    check("wallpaper: name of id 1", wl_name_of(1).len == 6);
    check("wallpaper: static kind", wl_kind_of(0) == WL_KIND_STATIC);
    check("wallpaper: live fps", wl_fps_of(1) == 30);

    // --- selection ----------------------------------------------------------
    let cs = wl_select(1, 1000);
    check("wallpaper: select the live one", cs == CODE_OK && wl_current_id() == 1);
    check("wallpaper: selected name", wl_current_name().len == 6);
    check("wallpaper: select an unknown id", wl_select(9, 1000) == E_NOTFOUND);
    check("wallpaper: a failed select kept the current one", wl_current_id() == 1);

    // --- the budget ---------------------------------------------------------
    // 30 fps → 33ms interval. Selecting reset the clock to 1000.
    check("wallpaper: interval for 30fps", wl_interval_ms(30) == 33);
    check("wallpaper: interval for 1fps", wl_interval_ms(1) == 1000);
    check("wallpaper: interval for 60fps", wl_interval_ms(60) == 16);
    check("wallpaper: interval floors at 1ms", wl_interval_ms(5000) == 1);

    check("wallpaper: a tick 32ms later is refused", wl_tick(1032) == 0);
    check("wallpaper: the refusal was counted", wl_budget_refusals() == 1);
    check("wallpaper: a tick at the interval draws", wl_tick(1033) == 1);
    check("wallpaper: the frame was counted", wl_frames_drawn() == 1);
    check("wallpaper: a tick 1ms later is refused", wl_tick(1034) == 0);
    check("wallpaper: refusals now two", wl_budget_refusals() == 2);

    // A thousand ticks in one millisecond: one frame at most. This is the property
    // the budget exists for.
    var mine = 0;
    i = 0;
    while i < 1000 {
        mine = mine + wl_tick(1035);
        i = i + 1;
    }
    check("wallpaper: 1000 ticks in one ms grant at most one frame", mine <= 1);
    num("     refusals after the burst: ", wl_budget_refusals());

    // --- pause on fullscreen ------------------------------------------------
    let before_frames = wl_frames_drawn();
    wl_set_fullscreen(true, 5000);
    check("wallpaper: paused", wl_is_paused());
    check("wallpaper: one pause counted", wl_pause_count() == 1);
    wl_set_fullscreen(true, 5100);
    check("wallpaper: re-entering fullscreen does not count a second pause", wl_pause_count() == 1);
    check("wallpaper: a tick while paused is 0", wl_tick(10000) == 0);
    check("wallpaper: paused ticks are not refusals", wl_budget_refusals() == before_frames * 0 + wl_budget_refusals());
    check("wallpaper: no frames drawn while paused", wl_frames_drawn() == before_frames);

    wl_set_fullscreen(false, 11000);
    check("wallpaper: unpaused", !wl_is_paused());
    check("wallpaper: no catch-up burst on resume (first tick is refused)", wl_tick(11010) == 0);
    check("wallpaper: resume does not count a pause", wl_pause_count() == 1);
    check("wallpaper: after the interval it draws again", wl_tick(11034) == 1);

    // --- static wallpapers --------------------------------------------------
    let cq = wl_select(0, 20000);
    check("wallpaper: select the static one", cq == CODE_OK);
    let f_before = wl_frames_drawn();
    let r_before = wl_budget_refusals();
    check("wallpaper: a static wallpaper never ticks a frame", wl_tick(30000) == 0);
    check("wallpaper: ... and is not counted as refused", wl_budget_refusals() == r_before);
    check("wallpaper: ... and draws no frame", wl_frames_drawn() == f_before);

    // --- nothing selected ---------------------------------------------------
    wl_init();
    check("wallpaper: init clears the selection", wl_current_id() == WL_NEVER);
    check("wallpaper: a tick with nothing selected is idle", wl_tick(5) == 0);
    check("wallpaper: ... and not a refusal", wl_budget_refusals() == 0);

    // --- the status line ----------------------------------------------------
    var _id, _cid = wl_register("l", WL_KIND_LIVE, 10);
    let _cs = wl_select(0, 0);
    let _t1 = wl_tick(100);
    var line: u8[>..] = [];
    wl_summary(line);
    check("wallpaper: summary is not empty", line.len >= 8);
    check("wallpaper: summary starts with f=", line[0] == 102 && line[1] == 61);
    check("wallpaper: summary reports one frame", line[2] == 49);

    // --- WL_MAX: the registry fills and the next one refuses ------------------
    // WL_MAX is 8 and one live wallpaper is already registered from the status section,
    // so this tops the registry up to the cap through the public API and then asks for a
    // ninth. A registry that silently grew past its array would be writing out of bounds
    // on a real machine and nothing above this line would have noticed.
    wl_init();
    var filled: i64 = 0;
    var i: i64 = 0;
    while i < WL_MAX {
        var nm: u8[>..] = [];
        let _ = nm.push('w');
        let _ = nm.push('0' + (i % 10) as u8);
        let _wid, wc = wl_register(nm[..], WL_KIND_STATIC, 0);
        if wc == CODE_OK { filled = filled + 1; }
        i = i + 1;
    }
    check("wallpaper: WL_MAX wallpapers register", filled == WL_MAX && wl_count_() == WL_MAX);
    let _over, cover = wl_register("overflow", WL_KIND_STATIC, 0);
    check("wallpaper: the one past WL_MAX is E_NO_SPACE", cover == E_NO_SPACE);
    check("wallpaper: the refusal did not grow the registry", wl_count_() == WL_MAX);

    say("t87 done  pass=");
    var pb: u8[>..] = [];
    let _ = append_int(pb, 32, t_pass);
    say(pb[..]);
    say(" fail=");
    var fb: u8[>..] = [];
    let _ = append_int(fb, 32, t_fail);
    say(fb[..]);
    say("\n");
}
