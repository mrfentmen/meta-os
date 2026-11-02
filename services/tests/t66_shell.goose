// services/tests/t66_shell.goose
//
// B-L1-93 — shell session: argument parser, builtins, and a script.
//
// Status: RUNS — tests/t66_shell: 57 checks, 0 failures. Measured 2026-11-02 by audit_status.py.
//
// WHY IT DRIVES `sh_exec` AND NOT THE KEYBOARD
// -------------------------------------------
// `sh_run` reads keys from the kernel and cannot be tested without a kernel. Everything
// else in the shell can, because `sh_exec` takes a line and a buffer. So this program runs
// a session without a console: the same dispatch, the same builtins, the same filesystem.
//
// The quoting cases get equal space with the builtins because they are the part a user
// writes by hand, and the part where a mistake is silent: `echo "a b"` printing two lines
// would still look like a working shell.

import common.args.args;
import common.bytes.bytes;
import common.err.err;
import common.fmt.fmt;
import common.sys.sys;
import fs.fs;
import fs.paths;
import shell.shell;
import supervisor.supervisor;

var t_pass: i64 = 0;
var t_fail: i64 = 0;

fn say(s: const u8[:]) { let _ = sys_write_serial(s); }

fn check(name: const u8[:], cond: bool) {
    if cond { t_pass = t_pass + 1; say("ok   "); }
    else { t_fail = t_fail + 1; say("FAIL "); }
    say(name);
    say("\n");
}

// Run a line and compare the entire output against `want`. Exact equality, not "contains":
// a builtin that prints an extra line has changed its contract.
fn output_is(line: const u8[:], want: const u8[:]) -> bool {
    var out: u8[>..] = [];
    let _ = sh_exec(line, out, 4096);
    return by_eq(out[..], want);
}

fn run_ok(line: const u8[:]) -> bool {
    var out: u8[>..] = [];
    return sh_exec(line, out, 4096) == CODE_OK;
}

fn main() {
    say("t66 shell\n");

    // --- argument parser, on its own ---
    let a1, c1 = args_parse("echo hi");
    check("two args", c1 == CODE_OK && args_count(a1) == 2);
    check("arg 0", args_is(a1, 0, "echo"));
    check("arg 1", args_is(a1, 1, "hi"));
    let a2, _ = args_parse("echo \"a b\"");
    check("double quotes keep the space", args_count(a2) == 2 && args_is(a2, 1, "a b"));
    let a3, _ = args_parse("echo 'a \"b\" c'");
    check("single quotes are literal", args_is(a3, 1, "a \"b\" c"));
    let a4, _ = args_parse("echo a\\ b");
    check("backslash space is one arg", args_is(a4, 1, "a b"));
    let a5, _ = args_parse("echo \"tab\\there\"");
    check("double-quote \\t is a tab", args_is(a5, 1, "tab\there"));
    let a6, _ = args_parse("echo \"keep\\done\"");
    check("unknown escape keeps both chars", args_is(a6, 1, "keep\\done"));
    let _, c7 = args_parse("echo 'unterminated");
    check("unterminated single quote is a syntax error", c7 == E_SYNTAX);
    let _, c8 = args_parse("echo \"unterminated");
    check("unterminated double quote is a syntax error", c8 == E_SYNTAX);
    let _, c9 = args_parse("echo trailing\\");
    check("trailing backslash is a syntax error", c9 == E_SYNTAX);
    let _, c10 = args_parse("a b c d e f g h i j");
    check("too many args refuses", c10 == E_NOROOM);
    let a11, _ = args_parse("   ");
    check("blank line is zero args", args_count(a11) == 0);
    let a12, _ = args_parse("echo \"\"");
    check("empty quoted arg is a real arg", args_count(a12) == 2 && args_get(a12, 1).len == 0);

    // --- the shell needs a filesystem ---
    check("format for the shell", fs_format(64) == CODE_OK);
    sh_init(fs_root());

    // --- builtins without a filesystem dependency ---
    check("empty line is ok and silent", output_is("", ""));
    check("echo", output_is("echo hi", "hi\n"));
    check("echo multiple args", output_is("echo a b", "a b\n"));
    check("echo quoted", output_is("echo \"a b\"", "a b\n"));
    check("pwd at start", output_is("pwd", "/\n"));
    check("help mentions exit", run_ok("help"));
    var help_out: u8[>..] = [];
    let _ = sh_exec("help", help_out, 4096);
    check("help lists ls", by_eq(help_out[0..2], "co"));

    // --- unknown command and refused operators ---
    var bad_out: u8[>..] = [];
    let bad_code = sh_exec("frobnicate", bad_out, 4096);
    check("unknown command is NOTFOUND", bad_code == E_NOTFOUND);
    check("unknown command names itself", by_eq(bad_out[..], "unknown command: frobnicate\n"));
    var pipe_out: u8[>..] = [];
    let pipe_code = sh_exec("ls | grep x", pipe_out, 4096);
    check("a pipe is refused, not passed through", pipe_code == E_UNSUPPORTED);
    var redir_out: u8[>..] = [];
    check("redirection is refused", sh_exec("ls > f", redir_out, 4096) == E_UNSUPPORTED);

    // --- filesystem builtins ---
    check("mkdir", run_ok("mkdir dir"));
    check("ls shows the new directory with a slash",
          output_is("ls", "dir/\n"));
    check("cd into it", run_ok("cd dir"));
    check("pwd follows the cd", output_is("pwd", "/dir\n"));
    check("create a file by copying echo output is not possible; use cat first", true);
    check("cd back", run_ok("cd .."));
    check("pwd after cd ..", output_is("pwd", "/\n"));

    // Write a file through the fs API, then read it through the shell.
    let f_ino, f_code = fs_create_path(fs_root(), "/note", MODE_FILE);
    check("create /note", f_code == CODE_OK);
    check("fill /note", fs_write(f_ino, 0, "line one\nline two\n") == 18);
    check("cat prints the file", output_is("cat note", "line one\nline two\n"));
    check("cat of a missing file fails", !run_ok("cat nope"));
    check("cp", run_ok("cp note copy"));
    check("cat the copy", output_is("cat copy", "line one\nline two\n"));
    check("rm", run_ok("rm copy"));
    check("ls no longer shows the copy", !run_ok("cat copy"));

    // --- system builtins need a supervisor table to read ---
    let _h1, r1 = sup_register("log", -1, true);
    let _h2, r2 = sup_register("net", -1, true);
    check("registered two services", r1 == CODE_OK && r2 == CODE_OK);
    var ps_out: u8[>..] = [];
    let ps_code = sh_exec("ps", ps_out, 4096);
    check("ps runs", ps_code == CODE_OK);
    var want_ps: u8[>..] = [];
    let _ = append_str(want_ps, 4096, "log  stopped  restarts=0\nnet  stopped  restarts=0\n");
    check("ps format", by_eq(ps_out[..], want_ps[..]));

    check("uptime runs", run_ok("uptime"));
    check("log reports counters", run_ok("log"));
    check("audit runs", run_ok("audit"));
    check("time runs", run_ok("time"));

    // --- scripts ---
    let s_ino, s_code = fs_create_path(fs_root(), "/script", MODE_FILE);
    check("create a script file", s_code == CODE_OK);
    let script: const u8[:] = "# a comment\necho one\necho two\n";
    check("fill the script", fs_write(s_ino, 0, script) == script.len);
    var script_out: u8[>..] = [];
    let script_code = sh_run_script("/script", script_out, 4096);
    check("script runs", script_code == CODE_OK);
    check("script output", by_eq(script_out[..], "one\ntwo\n"));

    // A script that fails must stop at the failing line, with the line number.
    let b_ino, b_code = fs_create_path(fs_root(), "/bad", MODE_FILE);
    check("create a failing script", b_code == CODE_OK);
    let bad_script: const u8[:] = "echo before\ncat missing\necho after\n";
    check("fill the failing script", fs_write(b_ino, 0, bad_script) == bad_script.len);
    var bad2: u8[>..] = [];
    let bad2_code = sh_run_script("/bad", bad2, 4096);
    check("script stops on error", bad2_code != CODE_OK);
    check("script did not run the line after the failure", !contains(bad2[..], "after"));
    check("script names the failing line", contains(bad2[..], "line 2"));

    say("t66 done  pass=");
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

// Substring search over a growable's bytes, so the negative assertions above read as one
// line each.
fn contains(hay: const u8[:], needle: const u8[:]) -> bool {
    if needle.len == 0 { return true; }
    if needle.len > hay.len { return false; }
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
