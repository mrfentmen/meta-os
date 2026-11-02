// services/session/login.goose
//
// B-L1-114 — Session login flow: name and token prompt over the console, checked against
// the session table.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// WHAT THIS IS, SAID ONCE AND PLAINLY
// -----------------------------------
// This is a *local* login: it stops a second person at the same keyboard from typing into
// someone else's console. It is NOT a security boundary and must not be described as one.
// There is no password file in this layer, no key derivation, no memory protection; the token
// is compared against a value the caller supplies, and anyone with the machine in front of
// them can read the code. Saying "login" without that sentence is how a toy becomes a claim.
//
// THE FLOW IS A STATE MACHINE WITH ONE HONEST REFUSAL
// ---------------------------------------------------
//   idle -> name -> token -> check -> active | failed
//
// - The name is echoed; the token is not (login_echo returns false for it, so the console
//   writes nothing but a newline per keystroke).
// - After `max_attempts` failures the flow returns E_AUTH and stays failed. It does not
//   slow down, lock out, or rate-limit: a delay would be a claim about brute-force
//   resistance that this layer cannot make with a constant-time compare over a string
//   supplied by the same process.
// - A successful login opens a session through session.goose and owns nothing else. The
//   session table is the record; this file is only the question and answer.
//
// TOKEN COMPARISON IS CONSTANT TIME IN THE TOKEN LENGTH
// ----------------------------------------------------
// The compare walks the whole of both buffers regardless of where they differ. Against an
// attacker who can measure the loop this is worth having; against one who can read this
// file it is worth nothing, which is why the paragraph above exists.

import common.err.err;
import session.session;

let LG_IDLE: i64 = 0;
let LG_NAME: i64 = 1;
let LG_TOKEN: i64 = 2;
let LG_ACTIVE: i64 = 3;
let LG_FAILED: i64 = 4;

let LG_NAME_MAX: i64 = 24;
let LG_TOKEN_MAX: i64 = 40;
let LG_ATTEMPTS: i64 = 3;

struct LoginFlow {
    state: i64,
    name: u8[..24],
    name_len: i64,
    token: u8[..40],
    token_len: i64,
    attempts: i64,
    session: i64,
    started_ms: i64,
    last_code: i64,
}

fn login_new() -> LoginFlow {
    var f: LoginFlow = LoginFlow {
        state: 0,
        name: [],
        name_len: 0,
        token: [],
        token_len: 0,
        attempts: 0,
        session: 0,
        started_ms: 0,
        last_code: 0,
    };
    var i: i64 = 0;
    while i < LG_NAME_MAX { f.name[i] = 0; i = i + 1; }
    i = 0;
    while i < LG_TOKEN_MAX { f.token[i] = 0; i = i + 1; }
    f.state = LG_IDLE;
    f.name_len = 0;
    f.token_len = 0;
    f.attempts = 0;
    f.session = SES_NO_SESSION;
    f.started_ms = 0;
    f.last_code = CODE_OK;
    return f;
}

// Present the prompt and move to the name state. Returns the prompt text the console should
// print, so the string lives in one place instead of at the call site.
fn login_start(f: LoginFlow&, now_ms: i64) -> const u8[:] {
    f.state = LG_NAME;
    f.name_len = 0;
    f.token_len = 0;
    f.started_ms = now_ms;
    f.last_code = CODE_OK;
    return "login: ";
}

fn login_prompt(f: LoginFlow&) -> const u8[:] {
    if f.state == LG_NAME { return "login: "; }
    if f.state == LG_TOKEN { return "token: "; }
    return "";
}

// Should the console echo what is typed? False for the token, and false after the flow ends:
// a failed login that keeps echoing is a prompt that looks alive when it is not.
fn login_echo(f: LoginFlow&) -> bool {
    if f.state == LG_NAME { return true; }
    return false;
}

// Feed one keystroke. Returns the code: CODE_OK for progress, E_AUTH when the flow has
// failed, E_STATE for a keystroke in a state that takes none.
//
// Backspace edits the current field. Enter (13 or 10) advances.
fn login_key(f: LoginFlow&, c: u8) -> i64 {
    if f.state == LG_IDLE || f.state == LG_ACTIVE || f.state == LG_FAILED { return E_STATE; }

    if c == 8 || c == 127 {
        if f.state == LG_NAME { if f.name_len > 0 { f.name_len = f.name_len - 1; } }
        else { if f.token_len > 0 { f.token_len = f.token_len - 1; } }
        return CODE_OK;
    }
    if c == 13 || c == 10 {
        if f.state == LG_NAME {
            if f.name_len == 0 { return E_INVAL; }     // an empty name is not a name
            f.state = LG_TOKEN;
            return CODE_OK;
        }
        // Enter in the token state submits; the caller runs login_submit.
        return CODE_OK;
    }
    if c < 32 || c == 127 { return E_INVAL; }          // control bytes never enter a field

    if f.state == LG_NAME {
        if f.name_len >= LG_NAME_MAX - 1 { return E_NOROOM; }
        f.name[f.name_len] = c;
        f.name_len = f.name_len + 1;
        return CODE_OK;
    }
    if f.token_len >= LG_TOKEN_MAX - 1 { return E_NOROOM; }
    f.token[f.token_len] = c;
    f.token_len = f.token_len + 1;
    return CODE_OK;
}

// Check the collected token against `expected` and, on success, open a session.
//
// `expected` is the caller's stored token. A zero-length expected token refuses every login:
// a config that failed to load must not become a login that accepts anything.
fn login_submit(f: LoginFlow&, expected: const u8[:], owner: i64, now_ms: i64) -> i64, i64 {
    if f.state != LG_TOKEN { return SES_NO_SESSION, E_STATE; }
    if expected.len == 0 { return login_fail(f, E_AUTH); }
    if !login_token_eq(f.token[..f.token_len], expected) { return login_fail(f, E_AUTH); }

    let id, code = ses_open(owner, 0, 0, 0, now_ms);
    if code != CODE_OK { f.last_code = code; return SES_NO_SESSION, code; }
    f.state = LG_ACTIVE;
    f.session = id;
    f.last_code = CODE_OK;
    return id, CODE_OK;
}

fn login_fail(f: LoginFlow&, code: i64) -> i64, i64 {
    f.attempts = f.attempts + 1;
    f.token_len = 0;
    f.last_code = code;
    if f.attempts >= LG_ATTEMPTS {
        f.state = LG_FAILED;
        return SES_NO_SESSION, E_AUTH;
    }
    // Back to the name prompt: retyping the name is deliberate. A "wrong token, try again"
    // loop that keeps the name is a nice way to learn a name from a mistyped token.
    f.state = LG_NAME;
    f.name_len = 0;
    return SES_NO_SESSION, code;
}

// Compare without an early exit. Length is compared first (a length difference is not a
// secret worth protecting), then every byte of both buffers is visited.
fn login_token_eq(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var diff: i64 = 0;
    var i: i64 = 0;
    while i < a.len {
        diff = diff | ((a[i] as i64) ^ (b[i] as i64));
        i = i + 1;
    }
    return diff == 0;
}

// Log out. Closes the session (if this flow opened one) and returns to idle, so the same
// flow object can serve the next login without a fresh allocation.
fn login_end(f: LoginFlow&) -> i64 {
    var code = CODE_OK;
    if f.state == LG_ACTIVE && f.session != SES_NO_SESSION {
        code = ses_close(f.session);
    }
    f.session = SES_NO_SESSION;
    f.state = LG_IDLE;
    f.name_len = 0;
    f.token_len = 0;
    f.attempts = 0;
    return code;
}

fn login_state_name(s: i64) -> const u8[:] {
    if s == LG_IDLE { return "idle"; }
    if s == LG_NAME { return "name"; }
    if s == LG_TOKEN { return "token"; }
    if s == LG_ACTIVE { return "active"; }
    if s == LG_FAILED { return "failed"; }
    return "?";
}
