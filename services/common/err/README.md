# `common/err` — the layer's error vocabulary

**Status: WRITTEN.** Not COMPILED (no Goose toolchain).

## The convention

A call that can fail returns its value first and the code last:

```goose
let n, code = read_sector(7, buf);
if err.failed(code) { ... }
```

`err.ok(code)` means success. This is Goose's own idiom — a trailing bool or code
says whether the rest is meaningful (`samples/04_errors.goose`) — generalised so
a service can say *why*, not just *that*.

Codes cross service boundaries. **Strings never do**: a string would carry a
pointer into the sender's memory and cannot be compared or counted. `name(code)`
turns a code into text at the one place text belongs, a log line or the console.

## Ranges

| Range | Domain |
|---|---|
| `0` | success |
| `1xxx` | any service: bad argument, no room, not found, busy, timeout, io, corrupt, unsupported, denied, wrong state, rate, no-key |
| `2xxx` | storage: no space, no device, bad block, read-only |
| `3xxx` | network: no link, no address, resolve, refused, unreachable |
| `4xxx` | agent host and audit: no agent, no capability, quota, audit full |
| `5xxx` | updater: bad manifest, bad signature, verify, rollback |
| `6xxx` | session and shell: no session, auth, syntax |

**Never renumber.** A code in last month's audit record must mean the same thing
today. New codes go at the end of their domain's block; B-L1-137 freezes the
registry.

## Predicates

`ok`, `failed`, `transient` (busy, timeout, rate, no-link — worth retrying),
`domain` (code / 1000, for routing to the right handler).

Encoding the retry judgement once is the point: every retry loop in the layer
then agrees, instead of one service retrying an `E_INVAL` forever.

## Rules this module puts on services

1. A service returns a code, never a string, across its boundary.
2. A service that exits after failing returns non-zero **and** writes one log
   record naming the code. Silent failure is a bug, and B-L1-62 audits for it.
3. Codes are appended, never reused. Tests compare codes, never names.

## Verification

| Form | Source |
|---|---|
| trailing `-> T, code` and `let v, c = ...` | `samples/04_errors.goose` |
| `const u8[:]` return with a literal | `spec#41` |
| top-level globals | `reference#5` |
| `if` / `return` | `list_keywords` |

## Not verified

Compilation. `name()` is deliberately an `if` chain rather than `match` — `match`
is a Goose keyword (`list_keywords`) but the constant-pattern form is not
something I verified, and this file only uses constructs with evidence.
