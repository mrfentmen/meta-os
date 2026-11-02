// services/tests/t73_shell_hard.goose
//
// B-L1-88 — BF4-14: argument-parser hardening, round 2.
//
// Status: RUNS — tests/t73_shell_hard: 46 checks, 0 failures. Measured 2026-11-02 by audit_status.py.sh.
//
// THE SPEC IS ALREADY WRITTEN, AND THIS FILE TESTS IT
// ---------------------------------------------------
// `services/common/args/args.goose` states the rules in its header: quoted words,
// three escape contexts, E_SYNTAX on an unterminated quote, E_NOROOM above
// ARG_MAX arguments or ARG_TEXT_MAX bytes, and "on any error the argv is empty and
// count is 0". That last clause is the one worth testing hardest: a parser that
// returns half a command on error lets the shell run a truncated version of what
// the user typed, which is how a quoting mistake becomes a different command.
//
// Round 1 (t66) covered the common cases through the shell. This round is the
// adversary's set: exactly at each limit and one past it, quotes meeting quotes,
// escapes in the wrong context, CRLF, and the bytes that only look like syntax.
//
// WHAT THIS CANNOT PROVE
// ----------------------
// Nothing here is about a terminal: input is a byte slice, so there is no history,
// no line editing, no signal handling, and no interactive echo.

import common.args.args;
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

fn eq(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

// Parse and assert both the code and that a failure emptied the argv.
fn parse(line: const u8[:]) -> Argv, i64 {
    let a, code = args_parse(line);
    return a, code;
}

fn fails_cleanly(line: const u8[:], code_want: i64) -> bool {
    let a, code = args_parse(line);
    if code != code_want { return false; }
    return args_count(a) == 0;
}

fn only_arg(a: Argv&) -> bool { return args_count(a) == 1; }

fn main() {
    say("t73 argument parser hardening\n");

    // --- the shapes that must work ---
    let a1, c1 = parse("echo hello");
    check("two words", c1 == CODE_OK && args_count(a1) == 2);
    check("word 0 is the command", args_is(a1, 0, "echo"));
    check("word 1 is the argument", args_is(a1, 1, "hello"));

    // A quoted run in the middle of a word is part of that word, not a new one.
    let a2, c2 = parse("a\"b c\"d");
    check("a quote inside a word does not start a new word", c2 == CODE_OK && args_count(a2) == 1);
    check("the quoted bytes are spliced in", args_is(a2, 0, "ab cd"));

    let a3, c3 = parse("'' \"\"");
    check("two empty arguments survive", c3 == CODE_OK && args_count(a3) == 2);
    check("both are zero-length", args_get(a3, 0).len == 0 && args_get(a3, 1).len == 0);

    let a4, c4 = parse("a''");
    check("an empty quoted run keeps the word alive", c4 == CODE_OK && args_count(a4) == 1 && args_is(a4, 0, "a"));

    // --- escapes, one context at a time ---
    let a5, _c5 = parse("\"\\d\"");
    check("an unknown double-quote escape keeps both bytes", only_arg(a5) && eq(args_get(a5, 0), "\\d"));
    let a6, _c6 = parse("\"a\\nb\"");
    check("\\n in double quotes is a newline", only_arg(a6) && args_get(a6, 0).len == 3 && args_get(a6, 0)[1] == '\n');
    let a7, _c7 = parse("\"a\\tb\"");
    check("\\t in double quotes is a tab", only_arg(a7) && args_get(a7, 0)[1] == '\t');
    let a8, _c8 = parse("\"a\\\"b\"");
    check("\\\" in double quotes is a quote", only_arg(a8) && eq(args_get(a8, 0), "a\"b"));
    let a9, _c9 = parse("\"a\\\\b\"");
    check("\\\\ in double quotes is one backslash", only_arg(a9) && eq(args_get(a9, 0), "a\\b"));

    let a10, _c10 = parse("'a\\nb'");
    check("single quotes are literal: no escape processing", only_arg(a10) && args_get(a10, 0).len == 4);

    let a11, _c11 = parse("a\\ b");
    check("an escaped space outside quotes is one argument", only_arg(a11) && eq(args_get(a11, 0), "a b"));
    let a12, _c12 = parse("a\\\"b");
    check("an escaped quote outside quotes is a quote", only_arg(a12) && eq(args_get(a12, 0), "a\"b"));
    let a13, _c13 = parse("a\\\\b");
    check("an escaped backslash outside quotes is one backslash", only_arg(a13) && eq(args_get(a13, 0), "a\\b"));

    // A quote inside the other kind of quote is content.
    let a14, _c14 = parse("\"a'b\"");
    check("a single quote inside double quotes is content", only_arg(a14) && eq(args_get(a14, 0), "a'b"));
    let a15, _c15 = parse("'a\"b'");
    check("a double quote inside single quotes is content", only_arg(a15) && eq(args_get(a15, 0), "a\"b"));

    // --- the syntax errors, and what the argv looks like afterwards ---
    check("unterminated double quote is E_SYNTAX and empty", fails_cleanly("echo \"unterminated", E_SYNTAX));
    check("unterminated single quote is E_SYNTAX and empty", fails_cleanly("echo 'unterminated", E_SYNTAX));
    check("trailing backslash is E_SYNTAX and empty", fails_cleanly("echo x\\", E_SYNTAX));
    check("a lone backslash is E_SYNTAX", fails_cleanly("\\", E_SYNTAX));
    check("a syntax error late in the line still empties the argv", fails_cleanly("a b c 'd", E_SYNTAX));
    check("a quote closed by the WRONG quote is a syntax error", fails_cleanly("\"a'", E_SYNTAX));

    // --- limits: at the limit, and one past it ---
    // ARG_MAX is 8. Eight words three bytes apart is exactly the cap.
    let a16, c16 = parse("a b c d e f g h");
    check("eight arguments parse", c16 == CODE_OK && args_count(a16) == 8);
    check("the eighth is there", args_is(a16, 7, "h"));
    check("a ninth is E_NOROOM, not a truncated eight", fails_cleanly("a b c d e f g h i", E_NOROOM));
    check("a ninth quoted argument is refused too", fails_cleanly("a b c d e f g \"h i\" j", E_NOROOM));

    // ARG_TEXT_MAX is 192 bytes of unescaped text across all arguments.
    var big: u8[>..] = [];
    var i: i64 = 0;
    while i < 192 { big.push('x'); i = i + 1; }
    let a17, c17 = parse(big[..]);
    check("192 bytes in one argument parses", c17 == CODE_OK && args_count(a17) == 1 && args_get(a17, 0).len == 192);
    big.push('x');
    check("193 bytes is E_NOROOM and empty", fails_cleanly(big[..], E_NOROOM));

    // The text cap counts UNESCAPED bytes: 192 escaped pairs is 96 bytes of text
    // and must fit. This is the case a naive byte-count would get wrong.
    var esc: u8[>..] = [];
    var j: i64 = 0;
    while j < 96 { esc.push('\\'); esc.push('a'); j = j + 1; }
    let a18, c18 = parse(esc[..]);
    check("192 source bytes of escapes are 96 text bytes", c18 == CODE_OK && args_get(a18, 0).len == 96);

    // --- separators ---
    let a19, c19 = parse("a\tb\r\nc");
    check("tabs, CR and LF all separate", c19 == CODE_OK && args_count(a19) == 3);
    check("no \\r is left on an argument", eq(args_get(a19, 1), "b"));
    let a20, c20 = parse("   \t \r\n  ");
    check("a blank line is zero arguments", c20 == CODE_OK && args_count(a20) == 0);
    let a21, c21 = parse("");
    check("an empty line is zero arguments", c21 == CODE_OK && args_count(a21) == 0);

    // --- what is deliberately NOT syntax ---
    // '|', '>', ';', '#', '$' and '*' are ordinary bytes at this layer; the shell
    // refuses the first three by name (t66), and no expansion exists at all.
    let a22, c22 = parse("a | b");
    check("a pipe is three ordinary arguments here", c22 == CODE_OK && args_count(a22) == 3 && args_is(a22, 1, "|"));
    let a23, c23 = parse("echo $HOME");
    check("no variable expansion: '$HOME' arrives as written", c23 == CODE_OK && args_is(a23, 1, "$HOME"));
    let a24, c24 = parse("echo *.goose");
    check("no globbing: '*.goose' arrives as written", c24 == CODE_OK && args_is(a24, 1, "*.goose"));
    let a25, c25 = parse("# not a comment");
    check("'#' is not a comment to the parser", c25 == CODE_OK && args_count(a25) == 4);

    // --- lookups out of range are empty, not a crash ---
    check("args_get past the end is empty", args_get(a1, 9).len == 0);
    check("args_get before the start is empty", args_get(a1, -1).len == 0);
    check("args_is past the end is false", !args_is(a1, 9, "echo"));
    check("args_is is exact, not a prefix match", !args_is(a1, 0, "ech"));

    // --- the parser does not alias the caller's line ---
    // The argv owns a copy, so reusing the line buffer must not change a parsed
    // argument. Simulated the way a shell does it: parse, overwrite the source,
    // then read the argument back.
    var line: u8[>..] = [];
    let _ = append_str(line, 32, "cat file.txt");
    let a26, _c26 = parse(line[..]);
    var k: i64 = 0;
    while k < line.len { line[k] = 'z'; k = k + 1; }
    check("a parsed argument survives the line buffer being reused", eq(args_get(a26, 1), "file.txt"));

    // --- a long line of many small words, parsed twice, is stable ---
    let a27, _ = parse("x x x x x x x x");
    let b27, _ = parse("x x x x x x x x");
    check("parsing the same line twice agrees", args_count(a27) == args_count(b27) && args_count(a27) == 8);

    say("t73 done  pass=");
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
