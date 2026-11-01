# shell — the command shell (B-L1-87..93)

Two entry points: `sh_exec(line, out, cap)` runs one line into a buffer (testable,
no console), and `sh_run()` is the REPL that owns the keyboard. Everything worth
testing lives in the first.

**Status: WRITTEN. Not COMPILED, not RUN.** `sh_run` has never read a key.

## Builtins

| Group | Commands |
|---|---|
| system (B-L1-89) | `ps` (supervisor table), `uptime` (clock), `log` (loss counters), `audit` (bytes), `time`, `help`, `exit` |
| files (B-L1-90) | `ls`, `cat`, `cp`, `rm`, `mkdir`, `cd`, `pwd` over MOSFS01 |
| scripts (B-L1-92) | one command per line, `#` comments, **stop on the first error** with the line number |

`echo` is a builtin. There are no external programs to run.

## What is refused, out loud

`|`, `>`, `<`, `;`, `&` return `E_UNSUPPORTED` instead of being passed through
as arguments. No globs, no variables, no `~`, no history file, no tab
completion, no `su`. Each refusal is in `shell.goose`'s header with the reason.

## Known gap, stated rather than implied

`log` prints **loss counters**, not a record tail: this layer has no log *reader*
yet. The builtin says so on its second line, because an empty `log tail` looks
exactly like an empty log.

Tests: `services/tests/t66_shell.goose` (argument parser, builtins and a script in one session).
