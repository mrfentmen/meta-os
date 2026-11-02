// services/tests/t47_cfg.goose
//
// B-L1-47 — test program for the config parser (B-L1-13).
//
// Status: RUNS — tests/t47_cfg: 16 checks, 0 failures. Measured 2026-11-02 by audit_status.py.
//
// A config parser reads a file an operator wrote by hand, so its cases are the things
// operators actually type: comments, trailing spaces, blank lines, a key repeated by
// accident, a number with a stray character, a section that is never closed. The parser
// must have a defined answer for each, and this test pins the answers down so a later
// "harmless" cleanup cannot change one silently.
//
// Note what is NOT asserted: the parser's internal offsets. The test asserts what a service
// sees -- the value, whether the key is present, the default when it is not -- because those
// are the contract. Offsets are the parser's business and testing them would freeze the
// implementation.

import common.cfg.cfg;
import common.fmt.fmt;
import common.sys.sys;

var t_pass: i64 = 0;
var t_fail: i64 = 0;

fn say(s: const u8[:]) { let _ = sys_write_serial(s); }

fn t_eq(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn check(name: const u8[:], cond: bool) {
    if cond { t_pass = t_pass + 1; say("ok   "); }
    else { t_fail = t_fail + 1; say("FAIL "); }
    say(name);
    say("\n");
}

let SAMPLE: const u8[:] =
    "# a comment line\n; another comment style\n\n[net]\n  address = 10.0.0.2   \n  prefix=24\n  dhcp = false\n[time]\nserver = pool.example\nrate = 1000\nrate = 2000\n[broken\nk = v\n";

fn main() {
    say("t47 cfg\n");

    var cfg = cfg_init(SAMPLE);

    // --- a present key, with the surrounding spaces stripped ---
    var v: u8[>..] = [];
    let got = cfg_get(cfg, "net", "address", v, 32);
    check("get net.address", got && t_eq(v, "10.0.0.2"));

    // --- no spaces around '=' ---
    let pv, p_ok = cfg_int(cfg, "net", "prefix", -1);
    check("int without spaces", pv == 24 && p_ok == true);

    // --- booleans: "false" must not be true just because it is non-empty ---
    let dv, dv_ok = cfg_bool(cfg, "net", "dhcp", true);
    check("bool false", dv == false && dv_ok == true);

    // --- absent key: the default, and ok=false ---
    let nv, nv_ok = cfg_int(cfg, "net", "mtu", 1500);
    check("absent int default", nv == 1500 && nv_ok == false);
    check("absent key not present", cfg_has(cfg, "net", "mtu") == false);
    check("present key is present", cfg_has(cfg, "net", "dhcp") == true);
    check("absent section", cfg_has(cfg, "nosuch", "dhcp") == false);

    // --- a duplicate key: last one wins, and it is deliberate ---
    // A service that made this ambiguous would behave differently depending on which
    // duplicate the parse happened to stop at.
    check("duplicate key last wins", cfg_int_ok(cfg, "time", "rate", 0, 2000));

    // --- a non-numeric value under cfg_int: default, not 0 and not garbage ---
    var bad: u8[>..] = [];
    let _ = cfg_get(cfg, "time", "server", bad, 32);
    check("string value", t_eq(bad, "pool.example"));
    let sv, sv_ok = cfg_int(cfg, "time", "server", -7);
    check("non-numeric int falls back", sv == -7 && sv_ok == false);
    let sb, sb_ok = cfg_bool(cfg, "time", "server", true);
    check("non-numeric bool falls back", sb == true && sb_ok == false);

    // --- cfg_get with a buffer too small refuses instead of truncating ---
    var small: u8[>..] = [];
    check("get refuses short buffer", cfg_get(cfg, "net", "address", small, 4) == false && small.len == 0);

    // --- a key from another section does not leak ---
    check("section is not ignored", cfg_has(cfg, "net", "server") == false);

    // --- an unterminated section header is not a section ---
    // The file is broken from "[broken" onward; the parser must still have answered every
    // question above correctly, and must not have invented that section.
    check("broken section not created", cfg_has(cfg, "broken", "k") == false);

    // --- an empty document answers every question with "absent" ---
    var empty = cfg_init("");
    check("empty doc absent", cfg_has(empty, "net", "dhcp") == false);
    let ev, ev_ok = cfg_int(empty, "net", "prefix", 8);
    check("empty doc default", ev == 8 && ev_ok == false);

    var r: u8[>..] = [];
    let _ = append_int(r, 32, t_pass);
    say("passed ");
    say(r);
    say("\n");
    if t_fail != 0 { say("FAILURES\n"); sys_exit(1); }
    say("t47 done\n");
    sys_exit(0);
}

// Two-value helper for the one case that reads better inline. Same contract as cfg_int.
fn cfg_int_ok(c: Config&, section: u8[:], key: u8[:], default: i64, want: i64) -> bool {
    let v, ok = cfg_int(c, section, key, default);
    return ok && v == want;
}
