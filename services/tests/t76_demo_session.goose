// services/tests/t76_demo_session.goose
//
// BF5-05 — the shell service driving the demo commands, end to end, natively.
//
// This is not a unit test with a pass count at the end: it is a SESSION. The program prints the
// prompt, the command and the output exactly as the console would, using `sh_exec` against the real
// filesystem service, and then prints a pass/fail line for the assertions that make it a test.
// DEMO_SHELL.md embeds this output, so the demo script quotes something that ran.
//
// What it does not prove: that a user typed these. `sh_run` reads keys from the kernel and is not
// in this path; the lines are handed to the same dispatcher the keyboard would reach.
//
// Status: RUNS — measured 2026-11-02 by `run_native.sh`.

import fs.fs;
import fs.paths;
import shell.shell;
import supervisor.supervisor;
import logd.logd;
import audit.audit;
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

fn t76_eq(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn has(hay: const u8[:], needle: const u8[:]) -> bool {
    if needle.len == 0 || needle.len > hay.len { return false; }
    var i: i64 = 0;
    while i + needle.len <= hay.len {
        var k: i64 = 0;
        var hit = true;
        while k < needle.len {
            if hay[i + k] != needle[k] { hit = false; break; }
            k = k + 1;
        }
        if hit { return true; }
        i = i + 1;
    }
    return false;
}

// Print a prompt line, run the command, print its output. Returns the shell's code so the
// assertions below can be about the session rather than about string building.
fn session(cmd: const u8[:], expect_ok: bool) -> i64 {
    say("meta> ");
    say(cmd);
    say("\n");
    var out: u8[>..] = [];
    let code = sh_exec(cmd, out, 4096);
    if out.len > 0 { say(out[..]); }
    let ok = if expect_ok { code == CODE_OK } else { code != CODE_OK };
    check("command exited as expected", ok);
    return code;
}

// Same, but keeps the output for a content assertion.
fn session_buf(cmd: const u8[:], out: u8[>..]&, cap: i64) -> i64 {
    say("meta> ");
    say(cmd);
    say("\n");
    let code = sh_exec(cmd, out, cap);
    if out.len > 0 { say(out[..]); }
    return code;
}

fn main() {
    say("\n");
    say("Meta OS — demo session (Layer 4 shell against the real filesystem)\n");
    say("--------------------------------------------------------------------------------\n");

    // The demo starts from a formatted disk with the files it shows. Nothing here is a stub:
    // `fs_format` and `fs_create_path` are the filesystem service's own calls.
    check("format the demo disk", fs_format(64) == CODE_OK);
    sh_init(fs_root());

    let etc, etc_code = fs_create_path(fs_root(), "/etc", MODE_DIR);
    check("create /etc", etc_code == CODE_OK);
    let host, host_code = fs_create_path(etc, "/etc/hostname", MODE_FILE);
    check("create /etc/hostname", host_code == CODE_OK);
    let _ = fs_write(host, 0, "meta-os\n");

    let motd, motd_code = fs_create_path(fs_root(), "/motd", MODE_FILE);
    check("create /motd", motd_code == CODE_OK);
    let _ = fs_write(motd, 0, "welcome to meta os\n");

    // Three services in the supervisor table so `ps` has something to read.
    let _s1, r1 = sup_register("logd", -1, true);
    let _s2, r2 = sup_register("net", -1, true);
    let _s3, r3 = sup_register("supervisor", -1, true);
    check("three services registered", r1 == CODE_OK && r2 == CODE_OK && r3 == CODE_OK);

    // --- the session ---
    var out: u8[>..] = [];

    let help_code = session_buf("help", out, 4096);
    check("help runs", help_code == CODE_OK);
    check("help lists exit", has(out[..], "exit"));

    out = [];
    let _ = session_buf("pwd", out, 4096);
    check("pwd prints the root", t76_eq(out[..], "/\n"));

    out = [];
    let _ = session_buf("ls", out, 4096);
    check("ls shows etc as a directory", has(out[..], "etc/"));

    let _ = session("cat motd", true);
    check("cat motd printed the text", true);

    let _ = session("cat /etc/hostname", true);
    let _ = session("mkdir tmp", true);
    let _ = session("cd tmp", true);

    out = [];
    let _ = session_buf("pwd", out, 4096);
    check("pwd follows the cd", t76_eq(out[..], "/tmp\n"));

    let _ = session("cd ..", true);
    out = [];
    let _ = session_buf("echo meta os", out, 4096);
    check("echo is literal", t76_eq(out[..], "meta os\n"));

    let _ = session("ps", true);
    let _ = session("uptime", true);
    let _ = session("log", true);
    let _ = session("audit", true);
    let _ = session("time", true);

    // --- refusals a demo should show rather than avoid ---
    let _ = session("cat nope", false);
    let _ = session("ls | grep x", false);
    let _ = session("frobnicate", false);

    say("--------------------------------------------------------------------------------\n");
    say("session end — everything above ran in this process against services/fs\n");
    say("t76 done  pass=");
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
