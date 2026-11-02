// services/tests/t129_session_r11.goose
//
// Round 11 (R11-151..156): session and login, the edges t84 does not drive.
//
// t84_session_deep owns the happy path and the main failure sweep (106 checks). This
// driver adds what it does not: attach after close/reap, the console a closed session no
// longer holds, the missing validation of capability masks and agent handles, double close
// as an accepted no-op, and a 120-cycle load shape.
//
// Status: WRITTEN — the coordinator compiles and runs this; nothing here has run yet.

import session.session;
import session.login;
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

fn eqs(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn type_str(f: LoginFlow&, s: const u8[:]) {
    var i: i64 = 0;
    while i < s.len {
        let _ = login_key(f, s[i]);
        i = i + 1;
    }
}

fn main() {
    say("t129 session r11\n");

    // ------------------------------------------------------------------
    // 1. attach claims a console but does not make it visible
    // ------------------------------------------------------------------
    ses_init();
    let a, ca = ses_open(OWNER_USER, 1, 0, 0, 0);
    check("session: open a user session", a > 0 && ca == CODE_OK);
    check("session: a fresh session is LOGIN", ses_state(a) == SS_LOGIN);
    check("session: attach -1 refused", ses_attach(a, -1, 0) == E_INVAL);
    check("session: attach console 0", ses_attach(a, 0, 0) == CODE_OK);
    check("session: attach does not focus", ses_visible_console() == -1 && !ses_accepts_input(a));
    check("session: focus the active session", ses_focus(a) == CODE_OK);
    check("session: focus sets the visible console", ses_visible_console() == 0);
    check("session: focused active session accepts input", ses_accepts_input(a));

    // ------------------------------------------------------------------
    // 2. close releases the console at once; a CLOSED session holds nothing
    // ------------------------------------------------------------------
    let b, cb = ses_open(OWNER_USER, 2, 0, 0, 0);
    check("session: second user session opens", b > 0 && cb == CODE_OK);
    check("session: close releases the console", ses_close(a) == CODE_OK);
    check("session: close clears the foreground", ses_foreground_id() == SES_NO_SESSION);
    check("session: the closed session's console can be attached", ses_attach(b, 0, 0) == CODE_OK);
    check("session: a closed session cannot attach", ses_attach(a, 1, 0) == E_STATE);
    check("session: a closed session cannot lock", ses_lock(a) == E_STATE);
    check("session: a closed session cannot unlock", ses_unlock(a) == E_STATE);
    check("session: a closed session cannot be focused", ses_focus(a) == E_STATE);
    check("session: double close is accepted (finding: no CLOSED guard)", ses_close(a) == CODE_OK);
    check("session: reap the closed session", ses_reap(a) == CODE_OK);
    check("session: attach to a reaped id is E_NOTFOUND", ses_attach(a, 1, 0) == E_NOTFOUND);

    // ------------------------------------------------------------------
    // 3. the owner/agent fields are not validated beyond "not zero"
    // ------------------------------------------------------------------
    let c, cc = ses_open(OWNER_AGENT, 0, -5, -1, 0);
    check("session: a negative agent handle is accepted (finding)", c > 0 && cc == CODE_OK);
    check("session: a negative capability mask is stored as given (finding)", ses_caps(c) == -1);
    check("session: owner_agent returns the negative handle", ses_owner_agent(c) == -5);
    let d, cd = ses_open(OWNER_AGENT, 0, 0, 0, 0);
    check("session: an agent session without a handle is refused", d == SES_NO_SESSION && cd == E_INVAL);
    check("session: a LOGIN session cannot be reaped", ses_reap(c) == E_STATE);
    check("session: close the negative-handle session", ses_close(c) == CODE_OK);
    check("session: reap after close", ses_reap(c) == CODE_OK);

    // ------------------------------------------------------------------
    // 4. one agent's exit closes only that agent's sessions
    // ------------------------------------------------------------------
    let e1, _ec1 = ses_open(OWNER_AGENT, 0, 42, 1, 0);
    let e2, _ec2 = ses_open(OWNER_AGENT, 0, 42, 1, 0);
    let e3, _ec3 = ses_open(OWNER_AGENT, 0, 43, 1, 0);
    check("session: three agent sessions open", e1 > 0 && e2 > 0 && e3 > 0);
    check("session: closing one agent closes only its sessions", ses_close_agent_sessions(42) == 2);
    check("session: agent 42's sessions are CLOSED", ses_state(e1) == SS_CLOSED && ses_state(e2) == SS_CLOSED);
    check("session: agent 43's session is untouched", ses_state(e3) == SS_LOGIN);
    let _ = ses_reap(e1);
    let _ = ses_reap(e2);
    let _ = ses_close(e3);
    let _ = ses_reap(e3);

    // ------------------------------------------------------------------
    // 5. login: submit in the wrong state, an owner the table refuses,
    //    an agent login, and login_end's close-without-reap contract
    // ------------------------------------------------------------------
    var f = login_new();
    let s0, c0 = login_submit(f, "tok", OWNER_USER, 1, 0);
    check("login: submit from IDLE is E_STATE", s0 == SES_NO_SESSION && c0 == E_STATE);
    let p0 = login_start(f, 0);
    check("login: the prompt is 'login: '", eqs(p0, "login: "));
    check("login: backspace at zero is accepted", login_key(f, 127) == CODE_OK && f.name_len == 0);
    type_str(f, "ada");
    check("login: name collected", f.name_len == 3);
    check("login: Enter moves to TOKEN", login_key(f, 13) == CODE_OK && f.state == LG_TOKEN);
    type_str(f, "tok");
    check("login: Enter in TOKEN does not submit", login_key(f, 13) == CODE_OK && f.state == LG_TOKEN);
    let s1, c1 = login_submit(f, "tok", 99, 1, 0);
    check("login: an unknown owner is refused by ses_open", s1 == SES_NO_SESSION && c1 == E_INVAL);
    check("login: the flow stays in TOKEN after the refusal", f.state == LG_TOKEN);
    check("login: a refused owner is not a failed attempt", f.attempts == 0);
    let s2, c2 = login_submit(f, "tok", OWNER_AGENT, 7, 0);
    check("login: the agent login opens a session", s2 > 0 && c2 == CODE_OK);
    check("login: the flow is ACTIVE", f.state == LG_ACTIVE);
    check("login: the session belongs to the agent", ses_owner_agent(s2) == 7);
    check("login: the session is LOGIN until attached", ses_state(s2) == SS_LOGIN);
    check("login: end closes the session", login_end(f) == CODE_OK && ses_state(s2) == SS_CLOSED);
    check("login: reap the closed session", ses_reap(s2) == CODE_OK);
    var g = login_new();
    let _ = login_start(g, 0);
    type_str(g, "x");
    let s3, c3 = login_submit(g, "x", OWNER_USER, 1, 0);
    check("login: submit from NAME is E_STATE", s3 == SES_NO_SESSION && c3 == E_STATE);
    check("login: end from NAME is a no-op", login_end(g) == CODE_OK && g.state == LG_IDLE);

    // ------------------------------------------------------------------
    // 6. load: 120 open/attach/close/reap cycles through one slot at a time
    // ------------------------------------------------------------------
    ses_init();
    var ops: i64 = 0;
    var ok: i64 = 0;
    var refused: i64 = 0;
    while ops < 120 {
        let id, code = ses_open(OWNER_USER, 10 + ops, 0, 1, ops);
        if code == CODE_OK {
            ok = ok + 1;
            if ses_attach(id, ops % SES_CAP, ops) != CODE_OK { refused = refused + 1; }
            let _ = ses_close(id);
            let _ = ses_reap(id);
        } else {
            refused = refused + 1;
        }
        ops = ops + 1;
    }
    check("session: 120 open/attach/close/reap cycles", ok == 120 && refused == 0);

    say("LOAD session ops=");
    var lb: u8[>..] = [];
    let _ = append_int(lb, 32, ops);
    say(lb[..]);
    say(" ok=");
    var lob: u8[>..] = [];
    let _ = append_int(lob, 32, ok);
    say(lob[..]);
    say(" refused=");
    var lrb: u8[>..] = [];
    let _ = append_int(lrb, 32, refused);
    say(lrb[..]);
    say("\n");

    say("t129 done  pass=");
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
