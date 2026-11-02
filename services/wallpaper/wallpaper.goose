// services/wallpaper/wallpaper.goose
//
// Layer 5, face service 2: the wallpaper registry and its frame budget.
//
// WHAT THIS IS
// ------------
// A fixed registry of wallpapers — static or live — plus the one rule that keeps a
// live wallpaper from eating the machine: a frame is granted only when the
// wallpaper's own interval has elapsed. The budget is enforced on the *tick*, not
// inside a wallpaper's renderer, because a renderer that is asked to throttle itself
// is a renderer that can decide not to.
//
// PAUSE ON FULLSCREEN
// -------------------
// A fullscreen window is someone working. The tick returns zero while paused, and the
// pause is counted once (on entry), not once per tick: a counter that incremented
// every tick would read as "the wallpaper failed 600 times" after ten seconds of
// fullscreen.
//
// WHAT IT DOES NOT DO
// -------------------
// It does not decode an image, allocate a framebuffer, or talk to the display service.
// It answers "may this wallpaper draw now, and what is selected" — the two facts the
// compositor needs before it does any of that.
//
// Status: RUNS — reached by tests/t87_wallpaper (exit 0). Measured 2026-11-02 by audit_status.py.

import common.err.err;

let WL_MAX: i64 = 8;
let WL_NAME_MAX: i64 = 20;
let WL_KIND_STATIC: i64 = 1;
let WL_KIND_LIVE: i64 = 2;
let WL_FPS_MAX: i64 = 60;
let WL_NEVER: i64 = -1;

struct Wallpaper {
    id: i64,
    name: u8[..20] = [0; 20],
    name_len: i64,
    kind: i64,
    fps: i64,
    used: bool,
}

var wl_list: Wallpaper[..8] = [Wallpaper { .. }; 8];
var wl_count: i64 = 0;
var wl_current: i64 = WL_NEVER;
var wl_paused: bool = false;
var wl_last_frame_ms: i64 = 0;
var wl_frames: i64 = 0;
var wl_refusals: i64 = 0;
var wl_pauses: i64 = 0;

fn wl_init() {
    var i: i64 = 0;
    while i < WL_MAX {
        wl_list[i].used = false;
        wl_list[i].id = 0;
        wl_list[i].kind = 0;
        wl_list[i].fps = 0;
        wl_list[i].name_len = 0;
        var j: i64 = 0;
        while j < WL_NAME_MAX { wl_list[i].name[j] = 0; j = j + 1; }
        i = i + 1;
    }
    wl_count = 0;
    wl_current = WL_NEVER;
    wl_paused = false;
    wl_last_frame_ms = 0;
    wl_frames = 0;
    wl_refusals = 0;
    wl_pauses = 0;
}

fn wl_find(id: i64) -> i64 {
    var i: i64 = 0;
    while i < wl_count {
        if wl_list[i].used && wl_list[i].id == id { return i; }
        i = i + 1;
    }
    return -1;
}

fn wl_find_name(s: const u8[:]) -> i64 {
    var i: i64 = 0;
    while i < wl_count {
        if wl_list[i].used && wl_name_eq(i, s) { return i; }
        i = i + 1;
    }
    return -1;
}

fn wl_name_eq(i: i64, s: const u8[:]) -> bool {
    if wl_list[i].name_len != s.len { return false; }
    var k: i64 = 0;
    while k < s.len {
        if wl_list[i].name[k] != s[k] { return false; }
        k = k + 1;
    }
    return true;
}

// Register a wallpaper. The id is the index, stable for the life of the process: a
// settings key stores this number, so it must not move when another wallpaper is
// added.
fn wl_register(name: const u8[:], kind: i64, fps: i64) -> i64, i64 {
    if name.len == 0 { return WL_NEVER, E_INVAL; }
    if name.len >= WL_NAME_MAX { return WL_NEVER, E_NOROOM; }
    if kind != WL_KIND_STATIC && kind != WL_KIND_LIVE { return WL_NEVER, E_INVAL; }
    // A static wallpaper with an fps is a caller that thinks it is live; a live one
    // with no budget is a wallpaper that would ask to draw every tick forever.
    if kind == WL_KIND_STATIC && fps != 0 { return WL_NEVER, E_INVAL; }
    if kind == WL_KIND_LIVE && (fps < 1 || fps > WL_FPS_MAX) { return WL_NEVER, E_INVAL; }
    if wl_find_name(name) >= 0 { return WL_NEVER, E_STATE; }
    if wl_count >= WL_MAX { return WL_NEVER, E_NO_SPACE; }

    var i: i64 = 0;
    while i < name.len {
        if name[i] < 32 || name[i] > 126 { return WL_NEVER, E_INVAL; }
        i = i + 1;
    }
    let n = wl_count;
    wl_list[n].id = n;
    wl_list[n].kind = kind;
    wl_list[n].fps = fps;
    wl_list[n].used = true;
    i = 0;
    while i < WL_NAME_MAX { wl_list[n].name[i] = 0; i = i + 1; }
    i = 0;
    while i < name.len {
        wl_list[n].name[i] = name[i];
        i = i + 1;
    }
    wl_list[n].name_len = name.len;
    wl_count = wl_count + 1;
    return wl_list[n].id, CODE_OK;
}

fn wl_count_() -> i64 { return wl_count; }

fn wl_name_of(id: i64) -> const u8[:] {
    let at = wl_find(id);
    if at < 0 { return ""; }
    return wl_list[at].name[..wl_list[at].name_len];
}

fn wl_kind_of(id: i64) -> i64 {
    let at = wl_find(id);
    if at < 0 { return 0; }
    return wl_list[at].kind;
}

fn wl_fps_of(id: i64) -> i64 {
    let at = wl_find(id);
    if at < 0 { return 0; }
    return wl_list[at].fps;
}

// The interval between granted frames. 1000 / fps, floored, and never below 1ms: an
// fps above the ceiling is refused at registration, so this cannot be 0.
fn wl_interval_ms(fps: i64) -> i64 {
    if fps <= 0 { return 1000; }
    let v = 1000 / fps;
    if v < 1 { return 1; }
    return v;
}

// Select what is on screen. Selecting resets the frame clock so the new wallpaper
// draws immediately rather than waiting out the old one's interval.
fn wl_select(id: i64, now_ms: i64) -> i64 {
    let at = wl_find(id);
    if at < 0 { return E_NOTFOUND; }
    wl_current = id;
    wl_last_frame_ms = now_ms;
    return CODE_OK;
}

fn wl_current_id() -> i64 { return wl_current; }

fn wl_current_name() -> const u8[:] {
    if wl_current == WL_NEVER { return ""; }
    return wl_name_of(wl_current);
}

// Fullscreen on/off. Entering fullscreen counts a pause; leaving it resets the frame
// clock so the wallpaper does not try to catch up with the frames it missed.
fn wl_set_fullscreen(on: bool, now_ms: i64) {
    if on && !wl_paused { wl_pauses = wl_pauses + 1; }
    if !on && wl_paused { wl_last_frame_ms = now_ms; }
    wl_paused = on;
}

fn wl_is_paused() -> bool { return wl_paused; }

// May the selected wallpaper draw now? Returns 1 for "draw this frame", 0 for "not
// now". A refusal is counted only when there IS something to draw and the budget says
// no; while paused or with nothing selected, the tick is idle, not refused.
fn wl_tick(now_ms: i64) -> i64 {
    if wl_paused { return 0; }
    if wl_current == WL_NEVER { return 0; }
    let at = wl_find(wl_current);
    if at < 0 { return 0; }
    // A static wallpaper is drawn by the compositor on selection and on resize, not
    // on a clock. Returning 1 here would make it redraw every tick for no reason.
    if wl_list[at].kind == WL_KIND_STATIC { return 0; }

    let interval = wl_interval_ms(wl_list[at].fps);
    if now_ms - wl_last_frame_ms < interval {
        wl_refusals = wl_refusals + 1;
        return 0;
    }
    wl_last_frame_ms = now_ms;
    wl_frames = wl_frames + 1;
    return 1;
}

fn wl_frames_drawn() -> i64 { return wl_frames; }
fn wl_budget_refusals() -> i64 { return wl_refusals; }
fn wl_pause_count() -> i64 { return wl_pauses; }

// What the status line reports: one line, three numbers, no adjectives.
fn wl_summary(out: u8[>..]&) {
    let _ = out.push(102);   // 'f'
    let _ = out.push(61);    // '='
    let _ = append_i(out, wl_frames);
    let _ = out.push(32);
    let _ = out.push(114);   // 'r'
    let _ = out.push(61);
    let _ = append_i(out, wl_refusals);
    let _ = out.push(32);
    let _ = out.push(112);   // 'p'
    let _ = out.push(61);
    let _ = append_i(out, wl_pauses);
}

fn append_i(out: u8[>..]&, v: i64) -> bool {
    if v == 0 { let _ = out.push(48); return true; }
    var tmp: u8[..24] = [0; 24];
    var n: i64 = 0;
    var x = v;
    while x > 0 {
        tmp[n] = (48 + (x % 10)) as u8;
        x = x / 10;
        n = n + 1;
    }
    var i: i64 = 0;
    while i < n {
        let _ = out.push(tmp[n - 1 - i]);
        i = i + 1;
    }
    return true;
}
