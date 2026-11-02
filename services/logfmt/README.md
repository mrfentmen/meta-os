# logfmt — the record shape every service logs through

Status: **RUNS** — `tests/t96_logfmt` (50 checks, exit 0) drives the format, and Round 11
adds `tests/t123_logfmt_r11` (limits, truncation marker, parser refusals, round trip).
Layer 4, service 12.

## Why one format

Three services that each format their own line produce three formats, and the tool
that reads them must know all three. Worse: when a service formats its own line the
timestamp and level are typed by the caller, so a warning logged by a helper becomes
an error and a line written after a sleep carries the time of the call, not of the
event. Here the record is a struct, time and level are filled in one place, and
nothing else in the layer logs any other way.

## The line

```
0042.300 W cons     console: 80x25 ready
^^^^^^^^ ^ ^^^^^^^^ ^^^^^^^^^^^^^^^^^^^
secs     | tag      message
        level
```

Fixed width (4-digit seconds, `.` and 3-digit milliseconds, one letter, an 8-wide
tag column) is what makes a log greppable, sortable and visually aligned without a
parser. The seconds column holds for the first 2.7 hours; past 9999 s it grows rather
than truncating an uptime, and the columns shift — deliberate, per the code. Machine-shaped records are the audit service's job (B-L1-41); this is the
format for the person reading a boot failure at 3am.

Seconds + milliseconds rather than a bare millisecond count: `0042.300` reads as
"42 s in", where `42300` needs dividing in your head.

## Decisions

| Decision | Reason |
|---|---|
| level is one letter | 40 KB of ring in a 64 KiB budget; `debug` costs 4 bytes per line |
| unknown level renders `?` | visible, never silent |
| long messages **truncate with `...`** | dropping the line loses the event entirely; the marker distinguishes "ended" from "was cut" |
| `logfmt_render` returns -1 rather than a partial line | a truncated render reads as a complete line with the end missing |
| `logfmt_parse` returns ok=false and fills nothing | a parser that guesses at a damaged line invents data for an audit trail |
| tag column padded to 8 | keeps the message aligned; `TAG_MAX - 1` reserved for the terminator |

`logfmt_parse` is strict: 1–9 second digits, exactly `.` and three millisecond
digits, space, level letter, space, tag (≤7), space, message to newline, no message
over `MSG_MAX`. Anything else is `false`, not a best guess.

Run as a host driver, not on the kernel. What is unproven is the kernel path, because no
service has run there yet.
