// services/tests/t84_session_deep.goose
//
// Round 7 B, session + login — the failure paths and the boundary of the table.
//
// t40_session proves the happy path. This file attacks it: double attach, input to a
// locked session, double close, a table with no free slot and no way to tell "free"
// from "gone", the login lockout, and what ses_init does to ids.
//
// Status: RUNS — set by `audit_status.py` from the runner's row, not by hand.

import session.session;
import session.login;
import common.err.err;
import common.fmt.fmt;
import common.sys.sys;

var t_pass: i64 = 0;
var t_fail: i64 = 0;
var t_s2: i64 = 0;   // the session left open between (a) and (b)

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

fn letters(n: i64) -> u8[>..] {
    var s: u8[>..] = [];
    var i: i64 = 0;
    while i < n { let _ = s.push(65 + (i % 26) as u8); i = i + 1; }
    return s;
}

fn type_str(f: LoginFlow&, s: const u8[:]) {
    var i: i64 = 0;
    while i < s.len {
        let _ = login_key(f, s[i]);
        i = i + 1;
    }
}

// ===========================================================================
// (a) Failure injection — session table

fn t_inject() {
    say("-- (a) failure injection\n");

    // Before anything opens a session the table is not initialised, and every
    // query must answer "no" rather than read uninitialised storage.
    check("ses: resolve before init", ses_resolve(1) == SES_NO_SESSION);
    check("ses: state before init reads free", ses_state(1) == SS_FREE);
    check("ses: accepts_input before init is false", !ses_accepts_input(1));

    // Owner discipline: a user session needs a user id, an agent session needs a
    // handle, and an unknown owner is not a session at all.
    let bad, cbad = ses_open(99, 1, 0, 0, 0);
    check("ses: unknown owner refused", bad == SES_NO_SESSION && cbad == E_INVAL);
    let nouser, cnouser = ses_open(OWNER_USER, 0, 0, 0, 0);
    check("ses: user session without a user id refused", nouser == SES_NO_SESSION && cnouser == E_INVAL);
    let noagent, cnoagent = ses_open(OWNER_AGENT, 0, 0, 0, 0);
    check("ses: agent session without a handle refused", noagent == SES_NO_SESSION && cnoagent == E_INVAL);

    let s1, c1 = ses_open(OWNER_USER, 7, 0, 5, 1000);
    check("ses: open user session", s1 > 0 && c1 == CODE_OK);
    check("ses: starts in LOGIN, not ACTIVE", ses_state(s1) == SS_LOGIN);
    check("ses: no console yet", ses_visible_console() == -1);

    check("ses: attach with console -1 refused", ses_attach(s1, -1, 1100) == E_INVAL);
    check("ses: attach console 0", ses_attach(s1, 0, 1100) == CODE_OK);
    check("ses: attach makes it ACTIVE", ses_state(s1) == SS_ACTIVE);
    check("ses: double attach refused", ses_attach(s1, 0, 1200) == E_STATE);

    let s2, c2 = ses_open(OWNER_USER, 8, 0, 5, 1300);
    t_s2 = s2;
    check("ses: open second session", s2 > s1 && c2 == CODE_OK);
    check("ses: second attach to a live console is E_BUSY", ses_attach(s2, 0, 1400) == E_BUSY);
    check("ses: the busy attach claimed nothing", ses_state(s2) == SS_LOGIN);

    // Foreground: only ACTIVE, only for a session that exists.
    check("ses: focus unknown id", ses_focus(9999) == E_NOTFOUND);
    check("ses: focus a LOGIN session refused", ses_focus(s2) == E_STATE);
    check("ses: focus the active session", ses_focus(s1) == CODE_OK);
    check("ses: foreground is the focused session", ses_foreground_id() == s1);
    check("ses: visible console is the focused one", ses_visible_console() == 0);
    check("ses: focused and active accepts input", ses_accepts_input(s1));

    // Lock: the input gate has to close, and it is the only gate.
    check("ses: lock an ACTIVE session", ses_lock(s1) == CODE_OK);
    check("ses: locked session does not accept input", !ses_accepts_input(s1));
    check("ses: locking a LOGIN session refused", ses_lock(s2) == E_STATE);
    ses_note_input(s1, 2000);
    check("ses: input time does not reopen the gate", !ses_accepts_input(s1));
    check("ses: unlock", ses_unlock(s1) == CODE_OK);
    check("ses: unlocked session accepts input again", ses_accepts_input(s1));
    check("ses: double unlock refused", ses_unlock(s1) == E_STATE);
    // note_input on an unknown id must be a no-op, not a write through a bad slot.
    ses_note_input(9999, 2000);
    check("ses: unknown id still refuses", !ses_accepts_input(9999));

    // Close: from any state, and the id is not reused.
    let caps_before = ses_caps(s1);
    check("ses: caps before close", caps_before == 5);
    check("ses: close", ses_close(s1) == CODE_OK);
    check("ses: closed state", ses_state(s1) == SS_CLOSED);
    check("ses: close clears caps", ses_caps(s1) == 0);
    check("ses: close clears the foreground", ses_foreground_id() == SES_NO_SESSION);
    check("ses: closed session does not accept input", !ses_accepts_input(s1));
    check("ses: close unknown id", ses_close(9999) == E_NOTFOUND);

    // A second close is accepted. That is what the code does: the state is CLOSED
    // and the function does not refuse it. Named here so nobody reads the first
    // close as idempotent-by-refusal.
    let cclose = ses_close(s1);
    check("ses: double close is accepted (finding: no CLOSED guard)", cclose == CODE_OK);

    // A closed session still occupies its slot until it is reaped: close is the
    // record, reap is the release. Nothing in this corpus calls ses_reap except a
    // test, which means the supervisor's exit path has to.
    check("ses: closed session still resolves", ses_state(s1) == SS_CLOSED);
    check("ses: reap writes the session off", ses_reap(s1) == CODE_OK);
    check("ses: reaped id resolves to free", ses_state(s1) == SS_FREE);
    check("ses: reaping twice is E_NOTFOUND", ses_reap(s1) == E_NOTFOUND);
    check("ses: reap a live session refused", ses_reap(s2) == E_STATE);

    // ss_free is the same value for "the id is gone" and "this slot is unused", so a
    // caller cannot tell a stale id from a free slot through the accessors. Recorded
    // as observed, not as a fix: every accessor returns a 0/empty answer for both.
    check("ses: a reaped id and a never-issued id are indistinguishable", ses_state(s1) == ses_state(9999));
}

// ===========================================================================
// (b) Boundary sweep — SES_CAP, consoles, ids

fn t_bounds() {
    say("-- (b) boundary sweep\n");

    // Fill the table. s2 is still open and attached to console 0.
    var ids: i64[8] = [0; 8];
    var n: i64 = 0;
    ids[0] = t_s2;
    n = 1;
    while n < SES_CAP {
        let id, c = ses_open(OWNER_USER, 100 + n, 0, 1, 3000);
        if c != CODE_OK { say("FAIL ses: fill refused early\n"); t_fail = t_fail + 1; return; }
        ids[n] = id;
        n = n + 1;
    }
    check("ses: table filled to SES_CAP", n == SES_CAP);
    let over, cover = ses_open(OWNER_USER, 200, 0, 1, 3100);
    check("ses: SES_CAP+1 refused with E_NO_SPACE", over == SES_NO_SESSION && cover == E_NO_SPACE);
    num("     sessions open: ", n);

    // Console index is not the limit: a high index is a valid console. Only a
    // negative one is refused.
    check("ses: attach console 0x3f (63) is a valid console", ses_attach(ids[1], 63, 3200) == CODE_OK);
    check("ses: attach console -2 refused", ses_attach(ids[2], -2, 3200) == E_INVAL);
    check("ses: two sessions cannot share console 63", ses_attach(ids[2], 63, 3200) == E_BUSY);

    // Closing frees nothing on its own: eight closed sessions are still eight used
    // slots. This is the single most important boundary in the file, because the
    // boot path opens one session per login and a close without a reap leaks.
    var i: i64 = 0;
    while i < SES_CAP { let _ = ses_close(ids[i]); i = i + 1; }
    let stillfull, cstill = ses_open(OWNER_USER, 300, 0, 1, 4000);
    check("ses: SES_CAP closed sessions still fill the table", stillfull == SES_NO_SESSION && cstill == E_NO_SPACE);

    i = 0;
    while i < SES_CAP { let _ = ses_reap(ids[i]); i = i + 1; }
    let after, cafter = ses_open(OWNER_USER, 301, 0, 1, 4100);
    check("ses: reaping the closed sessions frees the table", after > 0 && cafter == CODE_OK);

    // Ids are monotonic and never reused, including across close/reap cycles. A
    // stale id from a closed session must not reach a session opened later.
    let _ = ses_close(after);
    let _ = ses_reap(after);
    var prev = after;
    var mono = true;
    var k: i64 = 0;
    while k < 6 {
        let id, c = ses_open(OWNER_USER, 400 + k, 0, 1, 4200 + k);
        if c != CODE_OK || id <= prev { mono = false; break; }
        prev = id;
        let _ = ses_close(id);
        let _ = ses_reap(id);
        k = k + 1;
    }
    check("ses: ids strictly increase across close and reap", mono);
    let stale = ses_state(after);
    check("ses: an id from before the cycles does not resolve to a live session", stale == SS_FREE);

    // Agent sessions: closing an agent takes its sessions with it, and they land in
    // CLOSED, not FREE — the supervisor still has to reap them.
    let a1, ca1 = ses_open(OWNER_AGENT, 0, 77, 3, 5000);
    let a2, ca2 = ses_open(OWNER_AGENT, 0, 77, 3, 5001);
    check("ses: open two agent sessions", a1 > 0 && a2 > a1 && ca1 == CODE_OK && ca2 == CODE_OK);
    check("ses: owner_agent reports the agent", ses_owner_agent(a2) == 77);
    let closed_n = ses_close_agent_sessions(77);
    check("ses: agent exit closes both sessions", closed_n == 2);
    check("ses: agent sessions are CLOSED and need a reap", ses_state(a1) == SS_CLOSED && ses_state(a2) == SS_CLOSED);
    check("ses: agent with no sessions closes none", ses_close_agent_sessions(1234) == 0);
    check("ses: agent handle 0 closes nothing", ses_close_agent_sessions(0) == 0);
}

// ===========================================================================
// (c) Restart semantics — what ses_init resets, and what it does not

fn t_restart() {
    say("-- (c) restart semantics\n");

    // ses_init wipes the table and the foreground. It deliberately does NOT reset
    // ses_next_id, so an id issued before a restart cannot be reissued after it.
    let before, cbefore = ses_open(OWNER_USER, 900, 0, 1, 6000);
    check("ses: session before init", before > 0 && cbefore == CODE_OK);

    ses_init();
    check("ses: init frees every slot", ses_state(before) == SS_FREE);
    check("ses: init clears the foreground", ses_foreground_id() == SES_NO_SESSION);
    check("ses: init leaves the table usable", ses_open(OWNER_USER, 901, 0, 1, 6100) > 0);

    let after, cafter = ses_open(OWNER_USER, 902, 0, 1, 6200);
    check("ses: ids continue after init (not reused)", after > before && cafter == CODE_OK);
    num("     last id after init: ", after);
    check("ses: the pre-init id does not point at a live session", ses_state(before) == SS_FREE);

    // ses_open initialises on first use, so a service that forgot ses_init is not
    // a service that writes into a zeroed table by accident -- it gets a table.
    check("ses: open after init is stable", ses_state(after) == SS_LOGIN);
}

// ===========================================================================
// (d) login — the lockout, the field limits, the empty-token refusal

fn t_login() {
    say("-- (d) login flow\n");

    var f = login_new();
    check("login: new flow is idle", f.state == LG_IDLE);
    check("login: idle prompt is empty", login_prompt(f).len == 0);
    check("login: idle echoes nothing", !login_echo(f));
    check("login: a keystroke while idle is E_STATE", login_key(f, 65) == E_STATE);

    let prompt = login_start(f, 7000);
    check("login: prompt is 'login: '", prompt.len == 7);
    check("login: start moves to NAME", f.state == LG_NAME);
    check("login: NAME echoes", login_echo(f));

    // An empty name is not a name.
    check("login: Enter on an empty name refused", login_key(f, 13) == E_INVAL);
    check("login: still NAME after the refusal", f.state == LG_NAME);

    // Backspace at zero stays at zero rather than underflowing the length.
    check("login: backspace at zero", login_key(f, 8) == CODE_OK && f.name_len == 0);

    // Name field: LG_NAME_MAX-1 is the longest that fits.
    type_str(f, letters(LG_NAME_MAX - 1));
    check("login: name of LG_NAME_MAX-1 accepted", f.name_len == LG_NAME_MAX - 1);
    check("login: name at LG_NAME_MAX refused", login_key(f, 65) == E_NOROOM);
    check("login: length unchanged after refusal", f.name_len == LG_NAME_MAX - 1);
    check("login: a control byte is E_INVAL", login_key(f, 3) == E_INVAL);
    check("login: Enter advances to TOKEN", login_key(f, 13) == CODE_OK && f.state == LG_TOKEN);
    check("login: TOKEN does not echo", !login_echo(f));
    check("login: TOKEN prompt", login_prompt(f).len == 7);

    // Token field: same boundary, LG_TOKEN_MAX-1.
    type_str(f, letters(LG_TOKEN_MAX - 1));
    check("login: token of LG_TOKEN_MAX-1 accepted", f.token_len == LG_TOKEN_MAX - 1);
    check("login: token at LG_TOKEN_MAX refused", login_key(f, 65) == E_NOROOM);

    // An empty expected token refuses every login: a config that failed to load
    // must not become a login that accepts anything.
    let empty_tok: u8[..0] = [];
    let sid, csub = login_submit(f, empty_tok[..], OWNER_USER, 7, 7100);
    check("login: empty expected token refuses", sid == SES_NO_SESSION && csub == E_AUTH);
    check("login: failure is counted", f.attempts == 1);
    check("login: failure returns to NAME", f.state == LG_NAME);

    // Three failures and the flow stays failed. It does not delay or rate-limit;
    // the comment says so and the code matches.
    var round: i64 = 0;
    while round < 2 {
        type_str(f, letters(3));
        let _ = login_key(f, 13);
        type_str(f, letters(3));
        let id2, c2 = login_submit(f, letters(5), OWNER_USER, 7, 7200);
        if round == 0 {
            check("login: a wrong token is E_AUTH", id2 == SES_NO_SESSION && c2 == E_AUTH);
            check("login: second failure counted", f.attempts == 2);
        }
        round = round + 1;
    }
    check("login: third failure locks the flow", f.state == LG_FAILED);
    check("login: failed flow refuses keystrokes", login_key(f, 65) == E_STATE);
    check("login: failed flow has no prompt", login_prompt(f).len == 0);

    // A fresh flow on the same object: login_end resets attempts.
    check("login: end from failed", login_end(f) == CODE_OK);
    check("login: end resets attempts", f.attempts == 0);
    check("login: end returns to idle", f.state == LG_IDLE);

    // The success path, and the session it opens.
    let _ = login_start(f, 8000);
    type_str(f, letters(4));
    let _ = login_key(f, 13);
    type_str(f, letters(6));
    let id3, c3 = login_submit(f, letters(6), OWNER_USER, 7, 8100);
    check("login: correct token opens a session", id3 > 0 && c3 == CODE_OK);
    check("login: flow is ACTIVE", f.state == LG_ACTIVE);
    check("login: session is the one the flow opened", f.session == id3);
    check("login: the session exists", ses_state(id3) == SS_LOGIN);

    // login_end closes the session but does not reap it: same contract as ses_close.
    check("login: end closes the session", login_end(f) == CODE_OK);
    check("login: session is CLOSED after end", ses_state(id3) == SS_CLOSED);
    check("login: end from idle is a no-op", login_end(f) == CODE_OK);

    // The compare itself: whole-buffer, no early exit, and equal buffers are equal.
    check("login: compare equal", login_token_eq(letters(4), letters(4)));
    check("login: compare unequal", !login_token_eq(letters(4), letters(5)));
    check("login: compare length mismatch", !login_token_eq(letters(4), letters(6)));
}

fn main() {
    say("t84 session deep\n");
    t_inject();
    t_bounds();
    t_restart();
    t_login();

    say("t84 done  pass=");
    var pb: u8[>..] = [];
    let _ = append_int(pb, 32, t_pass);
    say(pb[..]);
    say(" fail=");
    var fb: u8[>..] = [];
    let _ = append_int(fb, 32, t_fail);
    say(fb[..]);
    say("\n");
}
