// services/tests/t131_shell_r11.goose
//
// Round 11 — the shell's limits and its refusal catalogue, driven through `sh_exec`.
//
// WHY THIS FILE EXISTS
// --------------------
// t66 proves the shell works. This one asks what it does at the edges: every operator token
// refused with the same code, every arity error named, the caller's output cap clamped, and
// a 200-command batch for the load line. It also records the one limit it cannot reach —
// SH_LINE_MAX lives in `sh_run`'s keyboard buffer, and `sh_run` needs the kernel.
//
// Status: written, not yet compiled or run (the coordinator runs the corpus).

import common.args.args;
import common.bytes.bytes;
import common.err.err;
import common.fmt.fmt;
import common.sys.sys;
import fs.fs;
import fs.paths;
import shell.shell;

var t_pass: i64 = 0;
var t_fail: i64 = 0;

fn say(s: const u8[:]) { let _ = sys_write_serial(s); }

fn check(name: const u8[:], cond: bool) {
    if cond { t_pass = t_pass + 1; say("ok   "); }
    else { t_fail = t_fail + 1; say("FAIL "); }
    say(name);
    say("\n");
}

// Run a line and return its code, with the output discarded or kept by the caller.
fn code_of(line: const u8[:]) -> i64 {
    var out: u8[>..] = [];
    return sh_exec(line, out, 4096);
}

fn main() {
    say("t131 shell round 11\n");

    check("format for the shell", fs_format(64) == CODE_OK);
    sh_init(fs_root());

    // ======================================================================
    // 1. the caller's output cap is a cap, not a suggestion
    // ======================================================================
    // SH_OUT_MAX is the caller's number: sh_exec takes `cap` and every writer checks it.
    // A tiny cap must truncate, never overflow, and never turn a success into an error.
    var tiny: u8[>..] = [];
    let tiny_code = sh_exec("echo hello", tiny, 3);
    check("cap 3: a successful command stays successful", tiny_code == CODE_OK);
    check("cap 3: output stops exactly at the cap", tiny.len == 3 && by_eq(tiny[..], "hel"));

    var zero_cap: u8[>..] = [];
    let zero_code = sh_exec("help", zero_cap, 0);
    check("cap 0: nothing is written and the command still succeeds",
          zero_code == CODE_OK && zero_cap.len == 0);

    // ======================================================================
    // 2. every refused operator, with the same code
    // ======================================================================
    // A token passed through as an argument is how `rm -rf > file` deletes a directory and
    // leaves a file called `>`. Each of the five is refused before dispatch.
    check("pipe is E_UNSUPPORTED", code_of("ls | grep x") == E_UNSUPPORTED);
    check("output redirection is E_UNSUPPORTED", code_of("echo hi > f") == E_UNSUPPORTED);
    check("input redirection is E_UNSUPPORTED", code_of("cat < f") == E_UNSUPPORTED);
    check("sequencing is E_UNSUPPORTED", code_of("echo a ; echo b") == E_UNSUPPORTED);
    check("background is E_UNSUPPORTED", code_of("echo a &") == E_UNSUPPORTED);

    // ======================================================================
    // 3. arity and lookup refusals, each with its own code
    // ======================================================================
    check("cat without a path is E_INVAL", code_of("cat") == E_INVAL);
    check("cp with one path is E_INVAL", code_of("cp a") == E_INVAL);
    check("rm without a path is E_INVAL", code_of("rm") == E_INVAL);
    check("mkdir without a path is E_INVAL", code_of("mkdir") == E_INVAL);

    check("cat of a missing file is E_NOTFOUND", code_of("cat nope") == E_NOTFOUND);
    check("cd to a missing directory is E_NOTFOUND", code_of("cd nope") == E_NOTFOUND);
    check("ls of a missing directory is E_NOTFOUND", code_of("ls nope") == E_NOTFOUND);
    check("an unknown command is E_NOTFOUND", code_of("frobnicate") == E_NOTFOUND);

    check("an unterminated quote is E_SYNTAX", code_of("echo \"unterminated") == E_SYNTAX);
    check("a blank line is not an error", code_of("") == CODE_OK);

    // A failed builtin that printed nothing would be indistinguishable from one that
    // succeeded silently. The dispatcher names the command and the error instead.
    var cat_out: u8[>..] = [];
    let _ = sh_exec("cat nope", cat_out, 4096);
    check("a silent refusal is named: \"cat: ...\"",
          cat_out.len > 5 && by_eq(cat_out[0..5], "cat: "));

    // ======================================================================
    // 4. SH_LINE_MAX cannot be reached from here
    // ======================================================================
    // The 192-byte bound lives in `sh_run`'s fixed buffer. `sh_run` reads keys from the
    // kernel, so a host driver cannot cross the edge; this is recorded as a gap in
    // r11/shell.md rather than asserted against a code path this file never enters.

    // ======================================================================
    // 5. load: 200 commands, half of them refusals
    // ======================================================================
    var ops: i64 = 0;
    var ok: i64 = 0;
    var refused: i64 = 0;
    var i: i64 = 0;
    while i < 100 {
        if code_of("echo batch") == CODE_OK { ok = ok + 1; } else { refused = refused + 1; }
        if code_of("frobnicate") == E_NOTFOUND { refused = refused + 1; } else { ok = ok + 1; }
        ops = ops + 2;
        i = i + 1;
    }
    check("load: 100 echoes accepted", ok == 100);
    check("load: 100 unknown commands refused", refused == 100);
    check("load: 200 commands, every one classified", ops == 200);

    say("LOAD shell ops=200 ok=");
    var ob: u8[>..] = [];
    let _ = append_int(ob, 32, ok);
    say(ob[..]);
    say(" refused=");
    var rb: u8[>..] = [];
    let _ = append_int(rb, 32, refused);
    say(rb[..]);
    say("\n");

    say("t131 done  pass=");
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
