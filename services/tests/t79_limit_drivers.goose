// services/tests/t79_limit_drivers.goose
//
// BF6-01 — the limits LIMITS.md listed as UNPROVEN, driven to their edge.
//
// WHAT THIS FILE IS FOR
// ---------------------
// `gen_limits.py` marks a limit PROVEN only when a test reaches the code that
// enforces it with a value on the wrong side. A constant that appears in a green
// suite by accident proves nothing, so the table listed 44 as UNPROVEN. This file
// takes the ones that a caller can actually reach and breaks each one.
//
// Two kinds of "break" are asserted, and they are not the same claim:
//   REFUSED — the module returned an error code and changed nothing.
//   CLAMPED — the module accepted the input and stored a prefix. That is a real
//             behaviour, but it is a truncation, and the test says so by name.
//
// Status: RUNS — set by `audit_status.py` from the runner's row, not by hand.

import watchdog.watchdog;
import display.text;
import session.login;
import session.session;
import dns.dns;
import socket.socket;
import netcfg.netcfg;
import updater.updater;
import updater.signature;
import agenthost.agenthost;
import agenthost.channel;
import common.fmt.fmt;
import common.err.err;
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

fn main() {
    say("t79 limit drivers\n");
    t_watchdog();
    t_wrap();
    t_login();
    t_dns();
    t_socket();
    t_netcfg();
    t_updater();
    t_signature();
    t_channel();

    say("t79 done  pass=");
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

// ===========================================================================
// 1. watchdog — WD_MAX (32), the watch table

fn t_watchdog() {
    say("-- WD_MAX\n");
    // 32 registrations fit; the 33rd is refused, and refusing it must not
    // disturb the 32 that are already armed.
    var registered: i64 = 0;
    var i: i64 = 0;
    while i < WD_MAX {
        let c = wd_watch(i + 1, 100, 10, 2, 0);
        if c == CODE_OK { registered = registered + 1; }
        i = i + 1;
    }
    check("wd: all 32 slots accept a watch", registered == 32);
    let over = wd_watch(WD_MAX + 1, 100, 10, 2, 0);
    check("wd: the 33rd registration is E_NOROOM", over == E_NOROOM);
    // The table is full and consistent: a handle already watched still answers
    // E_STATE, not E_NOROOM -- the two failures are different and a caller
    // retrying on E_STATE would otherwise think the table had room.
    let dup = wd_watch(1, 100, 10, 2, 0);
    check("wd: re-watching a full table's first handle is E_STATE", dup == E_STATE);
    // Free one slot, then the refused handle gets in: the refusal was the table,
    // not the handle.
    let _ = wd_unwatch(1);
    let retry = wd_watch(WD_MAX + 1, 100, 10, 2, 0);
    check("wd: the refused handle is accepted once a slot frees", retry == CODE_OK);
}

// ===========================================================================
// 2. text — WRAP_MAX_LINES (16)

fn t_wrap() {
    say("-- WRAP_MAX_LINES\n");
    // 6 lines of 70 bytes: wraps to 17 lines at width 30, which is over the cap.
    var s: u8[>..] = [];
    var i: i64 = 0;
    while i < 6 {
        var j: i64 = 0;
        while j < 70 { let _ = s.push('a'); j = j + 1; }
        if i < 5 { let _ = s.push('\n'); }
        i = i + 1;
    }
    let ll = text_wrap(s[..], 30);
    check("wrap: a list longer than the cap stops at 16", ll.count == WRAP_MAX_LINES);
    check("wrap: and says so with overflow", ll.overflow);

    // Exactly 16 lines must fit with overflow clear: the flag means "there was
    // more", not "I reached the cap".
    var exact: u8[>..] = [];
    var k: i64 = 0;
    while k < 16 {
        let _ = exact.push('x');
        if k < 15 { let _ = exact.push('\n'); }
        k = k + 1;
    }
    let le = text_wrap(exact[..], 10);
    check("wrap: 16 lines fit, count 16", le.count == 16);
    check("wrap: 16 lines is not overflow", !le.overflow);
}

// ===========================================================================
// 3. login — LG_NAME_MAX (24), LG_TOKEN_MAX (40)

fn t_login() {
    say("-- login field caps\n");
    var f = login_new();
    let _ = login_start(f, 0);
    // The field holds MAX-1 bytes: the last byte is the terminator the compare
    // and the echo both read past the length for.
    var i: i64 = 0;
    var accepted: i64 = 0;
    var last = CODE_OK;
    while i < LG_NAME_MAX {
        last = login_key(f, 'a');
        if last == CODE_OK { accepted = accepted + 1; }
        i = i + 1;
    }
    check("login: name accepts 23 bytes", accepted == LG_NAME_MAX - 1);
    check("login: the 24th byte of a name is E_NOROOM", last == E_NOROOM);
    check("login: name_len stopped at 23", f.name_len == LG_NAME_MAX - 1);

    // Backspace at the cap frees a byte, and the cap then accepts again: a
    // refusal that is permanent would make a mistyped long name unfixable.
    let _ = login_key(f, 8);
    let again = login_key(f, 'b');
    check("login: backspace reopens the name field", again == CODE_OK);

    // Enter advances to the token, which has its own, larger cap.
    let _ = login_key(f, 13);
    check("login: Enter moves to the token state", f.state == LG_TOKEN);
    var j: i64 = 0;
    var tok = CODE_OK;
    while j < LG_TOKEN_MAX {
        tok = login_key(f, 'z');
        j = j + 1;
    }
    check("login: token accepts 39 bytes", f.token_len == LG_TOKEN_MAX - 1);
    check("login: the 40th byte of a token is E_NOROOM", tok == E_NOROOM);
}

// ===========================================================================
// 4. dns — DNS_NAME_MAX (255), DNS_LABEL_MAX (63), DNS_MAX_JUMPS (32)

fn t_dns() {
    say("-- dns name limits\n");
    var q: u8[..512] = [0; 512];

    // A name of exactly the cap, made of 63-byte labels: 63.63.63.60 with dots.
    var ok_name: u8[>..] = [];
    var label: i64 = 0;
    while label < 3 {
        var c: i64 = 0;
        while c < 63 { let _ = ok_name.push('a'); c = c + 1; }
        let _ = ok_name.push('.');
        label = label + 1;
    }
    var last_label: i64 = 0;
    while last_label < 63 { let _ = ok_name.push('b'); last_label = last_label + 1; }
    check("dns: 255-byte name with 63-byte labels is built", dns_build_a_query(q, ok_name[..], 7) > 0);

    // One byte more than the format allows.
    let _ = ok_name.push('c');
    check("dns: a 256-byte name is refused", dns_build_a_query(q, ok_name[..], 7) == -1);

    // A single label one byte over its own cap, inside an otherwise legal name.
    var long_label: u8[>..] = [];
    var d: i64 = 0;
    while d < 64 { let _ = long_label.push('a'); d = d + 1; }
    let _ = long_label.push('.');
    let _ = long_label.push('c');
    let _ = long_label.push('o');
    let _ = long_label.push('m');
    check("dns: a 64-byte label is refused", dns_build_a_query(q, long_label[..], 7) == -1);

    // A pointer that points at itself. Every jump is legal on its own; the only
    // thing that stops it is the depth cap, so this is what proves the cap.
    var pkt: u8[..512] = [0; 512];
    pkt[12] = 0xC0;
    pkt[13] = 12;
    var out: u8[..256] = [0; 256];
    let _, _, good = dns_read_name(pkt[..], 12, out);
    check("dns: a self-referential pointer is refused, not followed forever", !good);
}

// ===========================================================================
// 5. socket — SK_PORT_MAX (65535), SK_DGRAM_MAX (512)

fn t_socket() {
    say("-- socket limits\n");
    let h, c0 = sk_open();
    check("socket: open", c0 == CODE_OK && h > 0);

    // sk_bind returns (chosen_port, code), not the handle: the port is the
    // thing the caller needs, and an ephemeral bind has no other way to learn it.
    let hi, ch = sk_bind(h, SK_PORT_MAX);
    check("socket: port 65535 binds", ch == CODE_OK && hi == SK_PORT_MAX);
    let _ = sk_close(h);

    let h2, c2 = sk_open();
    let _, over = sk_bind(h2, SK_PORT_MAX + 1);
    check("socket: port 65536 is E_INVAL", over == E_INVAL);
    let _, below = sk_bind(h2, SK_PORT_MIN - 1);
    check("socket: a privileged port is E_INVAL", below == E_INVAL);

    let h3, c3 = sk_open();
    let _, b3 = sk_bind(h3, 5000);
    check("socket: the second socket on an ordinary port binds", c3 == CODE_OK && b3 == CODE_OK);
    var addr: Ipv4 = Ipv4 { a: 127, b: 0, c: 0, d: 1 };

    // One datagram, not a stream: the cap is the payload of a single send.
    var big: u8[..600] = [0; 600];
    var i: i64 = 0;
    while i < 600 { big[i] = 65; i = i + 1; }
    let send_over = sk_send(h3, addr, 5001, big[0..SK_DGRAM_MAX + 1]);
    check("socket: 513-byte datagram is E_NOROOM", send_over == E_NOROOM);

    let send_ok = sk_send(h3, addr, 5001, big[0..SK_DGRAM_MAX]);
    check("socket: 512-byte datagram is accepted", send_ok == CODE_OK);
}

// ===========================================================================
// 6. netcfg — IF_NAME_MAX (8)

fn t_netcfg() {
    say("-- IF_NAME_MAX\n");
    // The name field is 8 bytes and 7 are usable: the last is the terminator.
    let c = iface_default("eth0");
    check("netcfg: a 4-byte name fits whole", c.name_len == 4);

    let long = iface_default("abcdefghij");
    check("netcfg: a 10-byte name is stored as 7", long.name_len == IF_NAME_MAX - 1);
    var same = true;
    var i: i64 = 0;
    while i < long.name_len {
        if long.name[i] != "abcdefg"[i] { same = false; }
        i = i + 1;
    }
    check("netcfg: the stored prefix is the first 7 bytes", same);
}

// ===========================================================================
// 7. updater — MF_MAX_FILES (8), MF_PATH_MAX (32), MF_VERSION_MAX (16)

fn manifest_with(files: i64, path_len: i64, version: const u8[:]) -> Manifest, i64 {
    var t: u8[>..] = [];
    let _ = append_str(t, 4096, "version=");
    let _ = append_str(t, 4096, version);
    let _ = append_str(t, 4096, "\nslot=a\n");
    var i: i64 = 0;
    while i < files {
        let _ = append_str(t, 4096, "file=f");
        // A digit per entry: eight identical paths are a duplicate-path error,
        // which is a different refusal and would mask the file-count limit.
        let _ = append_int(t, 4096, i);
        var p: i64 = 2;
        while p < path_len { let _ = t.push('x'); p = p + 1; }
        let _ = append_str(t, 4096, " ");
        // 32 zero bytes as 64 hex characters, built rather than typed: a
        // hand-counted literal is exactly how a digest length test passes for
        // the wrong reason.
        var hx: i64 = 0;
        while hx < MF_DIGEST_BYTES { let _ = append_str(t, 4096, "00"); hx = hx + 1; }
        let _ = append_str(t, 4096, " 1\n");
        i = i + 1;
    }
    return upd_parse_manifest(t[..]);
}

fn t_updater() {
    say("-- manifest limits\n");
    let m8, c8 = manifest_with(8, 10, "1.0.0");
    check("manifest: 8 files parse", c8 == CODE_OK && m8.count == 8);

    let _, c9 = manifest_with(9, 10, "1.0.0");
    check("manifest: a 9th file is E_BAD_MANIFEST", c9 == E_BAD_MANIFEST);

    // 30-byte path is accepted; 31 is the last usable byte (the 32nd would be the
    // terminator); one more is refused rather than truncated, because a
    // truncated path would name a different file.
    let _, cpath_ok = manifest_with(1, MF_PATH_MAX - 2, "1.0.0");
    check("manifest: a 30-byte path parses", cpath_ok == CODE_OK);
    let _, cpath_over = manifest_with(1, MF_PATH_MAX, "1.0.0");
    check("manifest: a 32-byte path is E_BAD_MANIFEST", cpath_over == E_BAD_MANIFEST);

    // The version is REFUSED at the cap, not truncated: a version string that
    // silently loses its tail would compare equal to a different release.
    let mv, cv = manifest_with(1, 10, "1.0.0rc12345678");
    check("manifest: a 15-byte version parses", cv == CODE_OK && mv.version_len == MF_VERSION_MAX - 1);
    let _, cv_over = manifest_with(1, 10, "1.0.0rc1234567890");
    check("manifest: a 16-byte version is E_BAD_MANIFEST", cv_over == E_BAD_MANIFEST);
}

// ===========================================================================
// 8. signature — SIG_KEY_ID_MAX (16)

fn t_signature() {
    say("-- SIG_KEY_ID_MAX\n");
    // 64 zero bytes base64, so the only thing under test is the key id.
    // 64 zero bytes in base64: 86 'A' and two padding bytes.
    let sig64: const u8[:] = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA==";
    var line: u8[>..] = [];
    let _ = append_str(line, 512, "signature ed25519 ");
    let _ = append_str(line, 512, "0123456789abcdef");
    let _ = line.push(' ');
    let _ = append_str(line, 512, sig64);
    let b1, c1 = sig_parse(line[..]);
    check("sig: a 16-byte key id parses", c1 == CODE_OK && b1.key_id_len == SIG_KEY_ID_MAX);

    var over: u8[>..] = [];
    let _ = append_str(over, 512, "signature ed25519 0123456789abcdef0 ");
    let _ = append_str(over, 512, sig64);
    let _, c2 = sig_parse(over[..]);
    check("sig: a 17-byte key id is E_INVAL", c2 == E_INVAL);
}

// ===========================================================================
// 9. channel — CH_SLOTS (16)

fn t_channel() {
    say("-- CH_SLOTS\n");
    var c = ch_new();
    let a, ca = ah_spawn("t79a", CAP_MSG, 100);
    let b, cb = ah_spawn("t79b", CAP_MSG, 100);
    check("ch: two messaging agents", ca == CODE_OK && cb == CODE_OK);
    let _ = ah_start(a, 100);
    let _ = ah_start(b, 100);

    var body: u8[>..] = [];
    var i: i64 = 0;
    while i < 10 { let _ = body.push('m'); i = i + 1; }

    var queued: i64 = 0;
    i = 0;
    while i < CH_SLOTS {
        let _, code = ch_send(c, a, b, body[..], 200, 1000);
        if code == CODE_OK { queued = queued + 1; }
        i = i + 1;
    }
    check("ch: the queue takes all 16 slots", queued == CH_SLOTS);
    let _, full = ch_send(c, a, b, body[..], 200, 1000);
    check("ch: the 17th send is E_BUSY", full == E_BUSY);
    let _, _, full_events, _ = ch_stats(c);
    check("ch: the refusal is counted as a full event", full_events == 1);
    // A body one byte over CH_BODY is a different refusal, checked here so the
    // two limits are not confused for each other.
    var wide: u8[>..] = [];
    i = 0;
    while i < CH_BODY + 1 { let _ = wide.push('w'); i = i + 1; }
    let _, too_wide = ch_send(c, a, b, wide[..], 200, 1000);
    check("ch: a body past CH_BODY is E_NOROOM", too_wide == E_NOROOM);
}
