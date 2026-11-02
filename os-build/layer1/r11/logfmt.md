# logfmt — Round 11 record

Source: `services/logfmt/logfmt.goose` · Test: `services/tests/t123_logfmt_r11.goose` · Status: RUNS (existing `t96`); t123 written, run pending

## 1. Limits — PROVEN (existing) / NAMED GAP (new assertions)

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `TAG_MAX` | `8` | `logfmt.goose` | already driven by `tests/t96_logfmt` (LIMITS.md); t123 crosses it | t123 passes a 10-byte tag and asserts 7 survive (`TAG_MAX - 1`) |
| `MSG_MAX` | `160` | `logfmt.goose` | already driven by `tests/t96_logfmt` (LIMITS.md); t123 crosses it | t123 passes 220 bytes and asserts `msg_len == 160` with `...` in the last three |
| `LINE_MAX` | `200` | `logfmt.goose` | already driven by `tests/t96_logfmt` (LIMITS.md); t123 asserts the fitting case only | a valid record at `TAG_MAX` + `MSG_MAX` renders to 180 bytes, so the refusal needs a caller buffer that is short — t123 does not force it (NAMED GAP) |

## 2. Refusals — PROVEN (existing) / NAMED GAP (new assertions)

| refusal | code / result | the test assertion that expects it |
|---|---|---|
| line too short to be a record | `logfmt_parse` false | t123: `"0042.30"` refused |
| unknown level letter | `logfmt_parse` false | t123: `"0042.300 X cons msg\n"` refused |
| missing separator before the message | `logfmt_parse` false | t123: `"0042.300 I\n"` refused |
| non-digit millisecond | `logfmt_parse` false | t123: `"0042.30x I cons msg\n"` refused |
| failed parse must not edit the caller's record | record unchanged | t123: after four refusals, `msg` is still `intact` and the level is still WARN |
| message past `MSG_MAX` on parse | false | not reachable with a 200-byte render buffer — the renderer refuses first; NAMED GAP |
| `logfmt_render` buffer too small | `-1` | a valid record renders in 180 bytes; a caller cannot hand a shorter buffer through the declared signature without a cast — NAMED GAP |

Truncation is deliberately **not** a refusal: an oversize message is cut to `MSG_MAX` with a
`...` marker, and t123 asserts the marker rather than a boolean.

## 3. Restart — NOT APPLICABLE

`logfmt` holds no state: every function is a pure transform over a record the caller owns. A
restart loses nothing, and there is nothing for the supervisor to preserve. This is the one
service in the round where "state proven continuous" has no meaning.

## 4. Contract — NAMED GAP

| direction | other service | call | in the matrix? |
|---|---|---|---|
| in | logd | none in code (logd does not import logfmt) | `SVC_LOG`'s row carries `SVC_LOGFMT`, so the edge is allowed and **dormant** |
| out | time | none in code — uptime is a caller-supplied parameter | `cm_set(SVC_LOGFMT, SVC_TIME)`; **dormant**, and the design is deliberate: the caller stamps the event, there is no "stamp it later" path |
| — | none | — | no call the matrix does not know |

`logfmt` imports only `common.err`. The matrix grants it one outbound call it does not make and
receives one inbound call nobody makes. Both are declared intent, not traffic.

## 5. Load — NAMED GAP

300 make/render/parse cycles: the loop exercises the full transform at a normal line length and
counts a cycle as refused if either the render or the parse fails. It should be 300/0.

RUNS pass=25 fail=0 · `LOAD logfmt ops=300 ok=300 refused=0`

## 6. README truth pass — PROVEN

- **`Status: WRITTEN (not COMPILED — no Goose toolchain)` was false.** `t96_logfmt` ran 50 checks
  and the service has a RUNS row; the README now says RUNS, names `t96` and `t123`, and drops the
  "not compiled" claim.
- **`Fixed width (4-digit seconds ...)` was only true for the first 2.7 hours.** The code grows
  the seconds field past 9999 s on purpose rather than truncating an uptime; the README now says
  the column holds for the first 2.7 hours and grows after that.
- **`Not compiled, not run.`** replaced: the host driver runs it; what is still unproven is the
  kernel path, because no service has run on the kernel.
- Kept: the line diagram, the truncation decision, the strict-parser decision, and the tag-column
  note (7 bytes plus the separator, which is the 8-wide column the reader sees).
