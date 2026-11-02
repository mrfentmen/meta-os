// services/common/args/args.goose
//
// B-L1-88 — argument parsing: quoting, escapes, argv over fixed buffers.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// WHY A PARSER AND NOT A SPLIT
// ----------------------------
// `st_word` (common/str) splits on whitespace and that is right for a config line. A command
// line is not a config line: `echo "a b"` is two arguments, `echo a\ b` is two arguments,
// and `echo 'a b'` is two as well -- but the bytes that reach `echo` differ in the first
// case only. Getting that wrong is how a shell turns a filename with a space into two
// filenames, and how a "harmless" quoting bug becomes a way to smuggle an argument.
//
// THE RULES, EXACTLY
// ------------------
// - Whitespace (space, tab) separates arguments, outside quotes only.
// - Single quotes are literal: everything until the next `'` is content, including `\`.
// - Double quotes honour `\"`, `\\`, `\n`, `\t`; every other backslash pair is passed
//   through as written, so `"\d"` stays `\d` rather than losing a character.
// - Outside quotes, `\` escapes the next character (any character).
// - An unterminated quote is E_SYNTAX. It is never "best effort": a shell that silently
//   closes a quote is a shell that runs something the user did not type.
// - More than ARG_MAX arguments is E_NOROOM, and the count returned is 0 so a caller cannot
//   accidentally execute a truncated command.
//
// The parsed result owns a copy of the unescaped bytes. That copy is the point: the caller
// reuses its line buffer between commands, and a span into it would be a dangling slice the
// day someone stores an argv.

import common.err.err;

let ARG_MAX: i64 = 8;          // a Layer 4 command takes at most 7 arguments
let ARG_TEXT_MAX: i64 = 192;   // unescaped bytes available to all arguments together

struct Argv {
    text: u8[..192],
    len: i64,
    starts: i64[..8],
    ends: i64[..8],
    count: i64,
}

fn args_empty() -> Argv {
    var a: Argv = Argv { text: [], len: 0, starts: [], ends: [], count: 0 };
    a.len = 0;
    a.count = 0;
    var i: i64 = 0;
    while i < ARG_MAX {
        a.starts[i] = 0;
        a.ends[i] = 0;
        i = i + 1;
    }
    return a;
}

fn args_count(a: Argv&) -> i64 {
    return a.count;
}

// The i-th argument, as a slice of the parser's own buffer. Returns an empty slice for an
// out-of-range index rather than a code: a caller past the end has already checked
// args_count, and every builtin does.
fn args_get(a: Argv&, i: i64) -> const u8[:] {
    if i < 0 || i >= a.count { return a.text[0..0]; }
    return a.text[a.starts[i]..a.ends[i]];
}

fn args_put(a: Argv&, c: u8) -> bool {
    if a.len >= ARG_TEXT_MAX { return false; }
    a.text[a.len] = c;
    a.len = a.len + 1;
    return true;
}

// Parse `line`. Returns (argv, code). On any error the argv is empty and count is 0.
fn args_parse(line: const u8[:]) -> Argv, i64 {
    var a = args_empty();
    var i: i64 = 0;
    var in_word: bool = false;

    while i < line.len {
        let c = line[i];
        if c == ' ' || c == '\t' || c == '\r' || c == '\n' {
            if in_word {
                a.ends[a.count - 1] = a.len;
                in_word = false;
            }
            i = i + 1;
        } else if c == '\'' {
            if !in_word {
                if a.count >= ARG_MAX { return args_empty(), E_NOROOM; }
                a.starts[a.count] = a.len;
                a.count = a.count + 1;
                in_word = true;
            }
            i = i + 1;
            var closed = false;
            while i < line.len {
                if line[i] == '\'' { closed = true; i = i + 1; break; }
                if !args_put(a, line[i]) { return args_empty(), E_NOROOM; }
                i = i + 1;
            }
            if !closed { return args_empty(), E_SYNTAX; }
        } else if c == '"' {
            if !in_word {
                if a.count >= ARG_MAX { return args_empty(), E_NOROOM; }
                a.starts[a.count] = a.len;
                a.count = a.count + 1;
                in_word = true;
            }
            i = i + 1;
            var closed2 = false;
            while i < line.len {
                let d = line[i];
                if d == '"' { closed2 = true; i = i + 1; break; }
                if d == '\\' && i + 1 < line.len {
                    let e = line[i + 1];
                    if e == '"' || e == '\\' {
                        if !args_put(a, e) { return args_empty(), E_NOROOM; }
                        i = i + 2;
                    } else if e == 'n' {
                        if !args_put(a, '\n') { return args_empty(), E_NOROOM; }
                        i = i + 2;
                    } else if e == 't' {
                        if !args_put(a, '\t') { return args_empty(), E_NOROOM; }
                        i = i + 2;
                    } else {
                        // Unknown escape inside double quotes: keep both characters. The
                        // alternative is silently dropping the backslash, which changes
                        // what a path means.
                        if !args_put(a, d) { return args_empty(), E_NOROOM; }
                        i = i + 1;
                    }
                } else {
                    if !args_put(a, d) { return args_empty(), E_NOROOM; }
                    i = i + 1;
                }
            }
            if !closed2 { return args_empty(), E_SYNTAX; }
        } else if c == '\\' {
            if i + 1 >= line.len { return args_empty(), E_SYNTAX; }   // trailing backslash
            if !in_word {
                if a.count >= ARG_MAX { return args_empty(), E_NOROOM; }
                a.starts[a.count] = a.len;
                a.count = a.count + 1;
                in_word = true;
            }
            if !args_put(a, line[i + 1]) { return args_empty(), E_NOROOM; }
            i = i + 2;
        } else {
            if !in_word {
                if a.count >= ARG_MAX { return args_empty(), E_NOROOM; }
                a.starts[a.count] = a.len;
                a.count = a.count + 1;
                in_word = true;
            }
            if !args_put(a, c) { return args_empty(), E_NOROOM; }
            i = i + 1;
        }
    }

    if in_word && a.count > 0 {
        a.ends[a.count - 1] = a.len;
    }
    return a, CODE_OK;
}

// Does the i-th argument equal `lit`? Builtins dispatch on this, and it exists so the
// comparison in every builtin is the same one -- a builtin that used `starts_with` on a
// command name would accept `lsfoo`.
fn args_is(a: Argv&, i: i64, lit: const u8[:]) -> bool {
    if i < 0 || i >= a.count { return false; }
    let s = args_get(a, i);
    if s.len != lit.len { return false; }
    var k: i64 = 0;
    while k < lit.len {
        if s[k] != lit[k] { return false; }
        k = k + 1;
    }
    return true;
}

// ---------------------------------------------------------------------------
// What this parser deliberately does NOT do
// ---------------------------------------------------------------------------
//
// - **No expansion of any kind.** No `$VAR`, no `$(...)`, no globs, no `~`. Each one is a
//   language feature with its own failure modes, and a shell that half-expands is a shell
//   that runs a command against the wrong file.
// - **No pipelines, no redirection.** `|`, `>`, `;` are ordinary characters here. The shell
//   (B-L1-87) refuses them explicitly with E_UNSUPPORTED rather than passing them through
//   as arguments, so the user gets an error instead of a file named `>`.
// - **No continuation lines.** A trailing `\` is E_SYNTAX; multi-line commands are a script
//   construct (B-L1-92) and scripts here are one command per line.
