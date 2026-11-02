// services/shell/shell.goose
//
// The command shell (B-L1-87, 89..92): REPL, dispatch, builtins, scripts.
//
// Status: WRITTEN (not COMPILED, not RUN). Every output line here is produced by code that
// has never run; the test program `t66_shell` is the first thing that will execute it.
//
// TWO ENTRY POINTS, ON PURPOSE
// ----------------------------
// `sh_exec(line, out, cap)` runs one line and appends its output into a caller buffer.
// `sh_run()` is the REPL: prompt, read a key at a time from the kernel, echo, execute.
//
// The split is not decoration. Everything worth testing is in `sh_exec`, and it is testable
// because it takes no console -- a shell that could only be exercised through a keyboard is
// a shell whose builtins have never been tested. `sh_run` is the thin loop that owns the
// keyboard and nothing else.
//
// EXIT CODES ARE THE POINT
// ------------------------
// Every builtin returns a code from `common/err`. `E_NOTFOUND` for a missing file,
// `E_INVAL` for a bad argument, `E_UNSUPPORTED` for a pipeline. A shell that prints
// "command not found" and returns 0 is a shell whose scripts all continue after a typo.
//
// NO PIPES, NO REDIRECTION, AND IT SAYS SO
// ----------------------------------------
// `|`, `>`, `<`, `;` are recognised and refused with E_UNSUPPORTED. Passing them through as
// ordinary arguments is how `rm -rf > file` becomes a file named `>` next to a deleted
// directory.

import common.args.args;
import common.bytes.bytes;
import common.err.err;
import common.fmt.fmt;
import common.sys.sys;
import fs.fs;
import fs.paths;
import supervisor.supervisor;
import logd.logd;
import audit.audit;
import time.time;

let SH_LINE_MAX: i64 = 192;
let SH_OUT_MAX: i64 = 4096;
let SH_CWD_MAX: i64 = 128;
let SH_HZ: i64 = 1000;               // the tick rate this shell assumes (Q-B-L1-6)

var sh_cwd: i64 = 0;                 // inode of the current directory
var sh_cwd_path: u8[..128] = [0; 128];   // its path, for the prompt
var sh_cwd_len: i64 = 0;
var sh_lines: i64 = 0;               // commands executed since start
var sh_errors: i64 = 0;
var sh_exit_requested: bool = false;

// ---------------------------------------------------------------------------
// Output helpers
// ---------------------------------------------------------------------------

fn out_str(out: u8[>..]&, cap: i64, s: const u8[:]) -> i64 {
    var i: i64 = 0;
    while i < s.len && out.len < cap {
        out.push(s[i]);
        i = i + 1;
    }
    return i;
}

fn out_nl(out: u8[>..]&, cap: i64) {
    if out.len < cap { out.push('\n'); }
}

// ---------------------------------------------------------------------------
// Current directory
// ---------------------------------------------------------------------------

fn sh_set_cwd(ino: i64) {
    sh_cwd = ino;
    sh_cwd_len = 0;
}

fn sh_init(root_ino: i64) {
    sh_cwd = root_ino;
    sh_set_path("/");
    sh_lines = 0;
    sh_errors = 0;
    sh_exit_requested = false;
}

// Copy a path into the prompt buffer, truncated rather than overflowing, and marking the
// truncation -- a prompt that silently shows half a path is a prompt that lies about where
// the next command will land.
fn sh_set_path(p: const u8[:]) {
    sh_cwd_len = 0;
    var i: i64 = 0;
    while i < p.len && i < SH_CWD_MAX - 1 {
        sh_cwd_path[i] = p[i];
        i = i + 1;
    }
    sh_cwd_len = i;
}

fn sh_cwd_slice() -> const u8[:] {
    return sh_cwd_path[..sh_cwd_len];
}

fn sh_prompt(out: u8[>..]&, cap: i64) {
    let _ = out_str(out, cap, sh_cwd_slice());
    let _ = out_str(out, cap, " > ");
}

fn path_is_absolute(p: const u8[:]) -> bool {
    return p.len > 0 && p[0] == '/';
}

// Join the cwd path and a component, for `cd`. Bounded and clamped, never allocating.
fn sh_join(dst: u8[>..]&, cap: i64, base: const u8[:], name: const u8[:]) {
    var i: i64 = 0;
    while i < base.len && dst.len < cap {
        if !(base.len == 1 && base[0] == '/') || i > 0 {
            dst.push(base[i]);
        }
        i = i + 1;
    }
    if dst.len > 0 && dst[dst.len - 1] != '/' { if dst.len < cap { dst.push('/'); } }
    var k: i64 = 0;
    while k < name.len && dst.len < cap {
        dst.push(name[k]);
        k = k + 1;
    }
}

// ---------------------------------------------------------------------------
// Builtins: system (B-L1-89)
// ---------------------------------------------------------------------------

fn bi_help(out: u8[>..]&, cap: i64) -> i64 {
    let _ = out_str(out, cap, "commands: help echo pwd cd ls cat cp rm mkdir ps uptime log audit time exit");
    out_nl(out, cap);
    let _ = out_str(out, cap, "no pipes, no redirection, no globs, no variables");
    out_nl(out, cap);
    return CODE_OK;
}

fn bi_echo(a: Argv&, out: u8[>..]&, cap: i64) -> i64 {
    var i: i64 = 1;
    while i < args_count(a) {
        if i > 1 { let _ = out_str(out, cap, " "); }
        let _ = out_str(out, cap, args_get(a, i));
        i = i + 1;
    }
    out_nl(out, cap);
    return CODE_OK;
}

fn bi_pwd(out: u8[>..]&, cap: i64) -> i64 {
    let _ = out_str(out, cap, sh_cwd_slice());
    out_nl(out, cap);
    return CODE_OK;
}

fn bi_ps(out: u8[>..]&, cap: i64) -> i64 {
    let n = sup_slot_count();
    if n == 0 {
        let _ = out_str(out, cap, "(no services registered)");
        out_nl(out, cap);
        return CODE_OK;
    }
    var i: i64 = 0;
    while i < n {
        let _ = out_str(out, cap, sup_slot_name(i));
        let _ = out_str(out, cap, "  ");
        let _ = out_str(out, cap, sup_slot_state_name(i));
        let _ = out_str(out, cap, "  restarts=");
        let _ = append_int(out, cap, sup_slot_restarts(i));
        if !sup_slot_enabled(i) { let _ = out_str(out, cap, "  disabled"); }
        out_nl(out, cap);
        i = i + 1;
    }
    return CODE_OK;
}

fn bi_uptime(out: u8[>..]&, cap: i64) -> i64 {
    // Built here rather than held in module state: the clock is a rate and nothing else,
    // and a module-level struct would be one more thing that can be initialised wrong.
    let c = clock_init(SH_HZ);
    let ms = clock_uptime_ms(c);
    let _ = out_str(out, cap, "up ");
    let _ = append_int(out, cap, ms / 1000);
    let _ = out_str(out, cap, "s  lines=");
    let _ = append_int(out, cap, sh_lines);
    let _ = out_str(out, cap, "  errors=");
    let _ = append_int(out, cap, sh_errors);
    out_nl(out, cap);
    return CODE_OK;
}

fn bi_log(out: u8[>..]&, cap: i64) -> i64 {
    let s = loss_stats();
    let _ = out_str(out, cap, "log written=");
    let _ = append_int(out, cap, s.written);
    let _ = out_str(out, cap, " full=");
    let _ = append_int(out, cap, s.full);
    let _ = out_str(out, cap, " level=");
    let _ = append_int(out, cap, s.level);
    let _ = out_str(out, cap, " long=");
    let _ = append_int(out, cap, s.long);
    out_nl(out, cap);
    // Stated here rather than implied: this layer has no record *reader* yet, so `log`
    // reports loss counters, not the tail. A `log tail` that printed nothing would look like
    // an empty log.
    let _ = out_str(out, cap, "(record reader not built: this is the loss counter)");
    out_nl(out, cap);
    return CODE_OK;
}

fn bi_audit(out: u8[>..]&, cap: i64) -> i64 {
    let _ = out_str(out, cap, "audit bytes=");
    let _ = append_int(out, cap, audit_used());
    out_nl(out, cap);
    return CODE_OK;
}

fn bi_time(out: u8[>..]&, cap: i64) -> i64 {
    let _ = out_str(out, cap, "ticks=");
    let _ = append_int(out, cap, sys_ticks());
    let _ = out_str(out, cap, " hz=");
    let _ = append_int(out, cap, SH_HZ);
    out_nl(out, cap);
    return CODE_OK;
}

// ---------------------------------------------------------------------------
// Builtins: files (B-L1-90)
// ---------------------------------------------------------------------------

fn bi_ls(a: Argv&, out: u8[>..]&, cap: i64) -> i64 {
    var target = sh_cwd;
    if args_count(a) > 1 {
        let p = args_get(a, 1);
        let ino, code = fs_resolve(sh_cwd, p, true);
        if code != CODE_OK { return code; }
        target = ino;
    }
    let n = fs_dirent_count(target);
    if n < 0 { return E_INVAL; }
    if n == 0 {
        out_nl(out, cap);
        return CODE_OK;
    }
    var i: i64 = 0;
    while i < n {
        var name: u8[>..] = [];
        let ino, kind, found = fs_readdir(target, i, name, 32);
        if !found { i = n; }
        else {
            let _ = out_str(out, cap, name[..]);
            if kind == MODE_DIR { let _ = out_str(out, cap, "/"); }
            out_nl(out, cap);
        }
        i = i + 1;
    }
    return CODE_OK;
}

fn bi_cat(a: Argv&, out: u8[>..]&, cap: i64) -> i64 {
    if args_count(a) < 2 { return E_INVAL; }
    let ino, code = fs_resolve(sh_cwd, args_get(a, 1), false);
    if code != CODE_OK { return code; }
    var buf: u8[>..] = [];
    let got, rcode = fs_read(ino, 0, buf, 4096);
    if rcode != CODE_OK { return rcode; }
    let _ = out_str(out, cap, buf[..]);
    if got > 0 && buf[got - 1] != '\n' { out_nl(out, cap); }
    return CODE_OK;
}

fn bi_cp(a: Argv&, out: u8[>..]&, cap: i64) -> i64 {
    if args_count(a) < 3 { return E_INVAL; }
    let src_ino, sc = fs_resolve(sh_cwd, args_get(a, 1), false);
    if sc != CODE_OK { return sc; }
    let dst = args_get(a, 2);
    // Existing destination: overwrite from 0 and truncate. Missing: create.
    let d_ino, d_code = fs_resolve(sh_cwd, dst, false);
    var target = d_ino;
    if d_code == E_NOTFOUND {
        let created, cc = fs_create_path(sh_cwd, dst, MODE_FILE);
        if cc != CODE_OK { return cc; }
        target = created;
    } else if d_code != CODE_OK {
        return d_code;
    } else {
        let tc = fs_truncate(target);
        if tc != CODE_OK { return tc; }
    }
    var buf: u8[>..] = [];
    let got, rcode = fs_read(src_ino, 0, buf, 4096);
    if rcode != CODE_OK { return rcode; }
    let w, wcode = fs_write(target, 0, buf[..]);
    if wcode != CODE_OK { return wcode; }
    let _ = out_str(out, cap, "copied ");
    let _ = append_int(out, cap, w);
    let _ = out_str(out, cap, " bytes");
    out_nl(out, cap);
    return CODE_OK;
}

fn bi_rm(a: Argv&, out: u8[>..]&, cap: i64) -> i64 {
    if args_count(a) < 2 { return E_INVAL; }
    let code = fs_unlink_path(sh_cwd, args_get(a, 1));
    return code;
}

fn bi_mkdir(a: Argv&, out: u8[>..]&, cap: i64) -> i64 {
    if args_count(a) < 2 { return E_INVAL; }
    let ino, code = fs_create_path(sh_cwd, args_get(a, 1), MODE_DIR);
    if code != CODE_OK { return code; }
    return CODE_OK;
}

fn bi_cd(a: Argv&, out: u8[>..]&, cap: i64) -> i64 {
    // The argument is bound at the call, not on a variable: re-binding a const
    // slice local between a literal and caller storage is rejected (§9.2).
    if args_count(a) > 1 { return bi_cd_to(args_get(a, 1), out, cap); }
    return bi_cd_to("/", out, cap);
}

fn bi_cd_to(p: const u8[:], out: u8[>..]&, cap: i64) -> i64 {
    let ino, code = fs_resolve(sh_cwd, p, true);
    if code != CODE_OK { return code; }
    sh_cwd = ino;
    // The prompt path is rebuilt from the argument when it is absolute, and from the old
    // path plus the argument when it is relative. `cd ..` shortens it, which keeps the
    // prompt honest without a getcwd syscall this kernel does not have.
    if path_is_absolute(p) {
        sh_set_path(p);
    } else if by_eq(p, "..") {
        if sh_cwd_len > 1 {
            var cut = sh_cwd_len - 1;
            if sh_cwd_path[sh_cwd_len - 1] == '/' { cut = sh_cwd_len - 2; }
            while cut > 0 && sh_cwd_path[cut] != '/' { cut = cut - 1; }
            if cut == 0 { cut = 1; }
            sh_cwd_len = cut;
        }
    } else if !by_eq(p, ".") {
        var joined: u8[>..] = [];
        sh_join(joined, SH_CWD_MAX - 1, sh_cwd_slice(), p);
        sh_set_path(joined[..]);
    }
    return CODE_OK;
}

fn bi_exit(out: u8[>..]&, cap: i64) -> i64 {
    sh_exit_requested = true;
    let _ = out_str(out, cap, "bye");
    out_nl(out, cap);
    return CODE_OK;
}

// ---------------------------------------------------------------------------
// Dispatch (B-L1-87)
// ---------------------------------------------------------------------------

// Tokens that would mean something in a real shell and silently do something else here.
fn is_refused_token(s: const u8[:]) -> bool {
    if s.len != 1 { return false; }
    let c = s[0];
    return c == '|' || c == '>' || c == '<' || c == ';' || c == '&';
}

fn sh_dispatch(a: Argv&, out: u8[>..]&, cap: i64) -> i64 {
    if args_count(a) == 0 { return CODE_OK; }        // blank line: not an error

    // Refuse the operators before they can be mistaken for arguments.
    var i: i64 = 0;
    while i < args_count(a) {
        if is_refused_token(args_get(a, i)) {
            let _ = out_str(out, cap, "unsupported: pipes/redirection are not built");
            out_nl(out, cap);
            return E_UNSUPPORTED;
        }
        i = i + 1;
    }

    let cmd = args_get(a, 0);
    if args_is(a, 0, "help") { return bi_help(out, cap); }
    if args_is(a, 0, "echo") { return bi_echo(a, out, cap); }
    if args_is(a, 0, "pwd") { return bi_pwd(out, cap); }
    if args_is(a, 0, "cd") { return bi_cd(a, out, cap); }
    if args_is(a, 0, "ls") { return bi_ls(a, out, cap); }
    if args_is(a, 0, "cat") { return bi_cat(a, out, cap); }
    if args_is(a, 0, "cp") { return bi_cp(a, out, cap); }
    if args_is(a, 0, "rm") { return bi_rm(a, out, cap); }
    if args_is(a, 0, "mkdir") { return bi_mkdir(a, out, cap); }
    if args_is(a, 0, "ps") { return bi_ps(out, cap); }
    if args_is(a, 0, "uptime") { return bi_uptime(out, cap); }
    if args_is(a, 0, "log") { return bi_log(out, cap); }
    if args_is(a, 0, "audit") { return bi_audit(out, cap); }
    if args_is(a, 0, "time") { return bi_time(out, cap); }
    if args_is(a, 0, "exit") { return bi_exit(out, cap); }

    let _ = out_str(out, cap, "unknown command: ");
    let _ = out_str(out, cap, cmd);
    out_nl(out, cap);
    return E_NOTFOUND;
}

// Run one line. Returns (code). Output goes into `out`, which the caller owns and which is
// NOT cleared here -- the REPL appends a command's output to whatever it already printed.
fn sh_exec(line: const u8[:], out: u8[>..]&, cap: i64) -> i64 {
    sh_lines = sh_lines + 1;
    let a, code = args_parse(line);
    if code != CODE_OK {
        let _ = out_str(out, cap, "syntax error");
        out_nl(out, cap);
        sh_errors = sh_errors + 1;
        return code;
    }
    let rc = sh_dispatch(a, out, cap);
    if rc != CODE_OK { sh_errors = sh_errors + 1; }
    return rc;
}

// ---------------------------------------------------------------------------
// Scripts (B-L1-92)
// ---------------------------------------------------------------------------

// Run a script file from the filesystem, one command per line.
//
// Stop-on-error is the default and is not negotiable with a flag: a script that continues
// after a failed `mkdir` runs the next command against a directory that is not there. The
// line number is reported because "a command failed" in a 40-line script is not a diagnosis.
fn sh_run_script(path: const u8[:], out: u8[>..]&, cap: i64) -> i64 {
    let ino, code = fs_resolve(sh_cwd, path, false);
    if code != CODE_OK { return code; }
    var file: u8[>..] = [];
    let got, rcode = fs_read(ino, 0, file, 4096);
    if rcode != CODE_OK { return rcode; }

    var line_no: i64 = 0;
    var pos: i64 = 0;
    while pos <= got {
        var end = pos;
        while end < got && file[end] != '\n' { end = end + 1; }
        let line = file[pos..end];
        // Skip blank lines and `#` comments without counting them as commands: a script's
        // line numbers should match what the user sees in the file.
        var trimmed = line;
        var t: i64 = 0;
        while t < trimmed.len && (trimmed[t] == ' ' || trimmed[t] == '\t') { t = t + 1; }
        line_no = line_no + 1;
        if t < trimmed.len && trimmed[t] != '#' {
            let rc = sh_exec(line, out, cap);
            if rc != CODE_OK {
                let _ = out_str(out, cap, "script stopped at line ");
                let _ = append_int(out, cap, line_no);
                let _ = out_str(out, cap, " code ");
                let _ = append_int(out, cap, rc);
                out_nl(out, cap);
                return rc;
            }
        }
        if end >= got { pos = got + 1; } else { pos = end + 1; }
    }
    return CODE_OK;
}

// ---------------------------------------------------------------------------
// The REPL (B-L1-87)
// ---------------------------------------------------------------------------
//
// The only part that touches the keyboard, and the only part with no test. It reads one key
// at a time, because that is what the kernel gives it (`read_key`, Q-B-L1-4): there is no
// blocking line read in K6, so this loop polls and yields.
fn sh_run() -> i64 {
    // A fixed line buffer with an explicit length, and growable output arrays declared
    // inside the loop. That is not a style choice: the language's growable slice has
    // `push` and `.len` (verified), and no `pop`/`clear` this layer can rely on. So the
    // line is a fixed array we shrink by moving the length, and each command's output
    // gets a fresh array by being declared per iteration.
    var line: u8[..192] = [0; 192];
    var line_len: i64 = 0;

    var prompt: u8[>..] = [];
    sh_prompt(prompt, SH_OUT_MAX);
    let _ = sys_write_console(prompt[..]);

    while !sh_exit_requested {
        var out: u8[>..] = [];
        var k: u8[>..] = [];
        if !sys_read_key(k) {
            sys_yield();          // no blocking read in K6: poll and yield
        } else if k.len > 0 {
            let c = k[0];
            if c == '\n' || c == '\r' {
                let _ = sys_write_console("\n");
                let _ = sh_exec(line[0..line_len], out, SH_OUT_MAX);
                let _ = sys_write_console(out[..]);
                line_len = 0;
                if !sh_exit_requested {
                    var next: u8[>..] = [];
                    sh_prompt(next, SH_OUT_MAX);
                    let _ = sys_write_console(next[..]);
                }
            } else if c == 8 || c == 127 {
                if line_len > 0 {
                    line_len = line_len - 1;
                    // Backspace, space, backspace. Goose has no `\b` escape, so the
                    // three bytes are written explicitly rather than smuggled through
                    // a string literal. Same effect on a VGA text console: the cursor
                    // steps back, a space covers the glyph, the cursor steps back again.
                    var bs: u8[..3] = [8, 32, 8];
                    let _ = sys_write_console(bs[..]);
                }
            } else if line_len < SH_LINE_MAX && c >= 32 {
                line[line_len] = c;
                line_len = line_len + 1;
                var echo: u8[>..] = [];
                echo.push(c);
                let _ = sys_write_console(echo[..]);
            }
        }
    }
    return CODE_OK;
}

// ---------------------------------------------------------------------------
// What the shell deliberately does NOT do
// ---------------------------------------------------------------------------
//
// - **No pipes, redirection, globs, variables or history file.** Refused explicitly (see the
//   header). Each is a language feature and half of one is worse than none.
// - **No `su`/`sudo`.** Authorization lives in `callmatrix` and the session table; a shell
//   builtin that changes identity would bypass both.
// - **No background jobs.** `&` is refused. The supervisor owns processes.
// - **No tab completion.** It needs a fuzzy match over the union of builtins and directory
//   entries, and a wrong completion that is accepted silently is how a user deletes a file
//   they did not name.
