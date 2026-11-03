# Contract note — R13-020, logfmt env var list

Status: **AUDITED — 1 gap filed**.
Facet: every environment variable `logfmt` reads, its default, and what happens when it is absent
or malformed.

## Evidence

Commands:

```sh
grep -nEi 'getenv|env_|environ|config|cfg_|sys_env' services/logfmt/*.goose
grep -nE '^let |^const ' services/logfmt/logfmt.goose
```

Relevant output:

```text
NO MATCHES
```

```text
48  let LV_DEBUG: i64 = 0;
49  let LV_INFO:  i64 = 1;
50  let LV_WARN:  i64 = 2;
51  let LV_ERROR: i64 = 3;
52  let LV_FATAL: i64 = 4;
85  let TAG_MAX:  i64 = 8;
86  let MSG_MAX:  i64 = 160;
87  let LINE_MAX: i64 = 200;
```

## Corrected contract

`logfmt` reads no environment variables. Its entire configuration is compile-time constants:
five level ids, `TAG_MAX = 8`, `MSG_MAX = 160`, `LINE_MAX = 200`. The record shape is fixed by
`logfmt_make(level, tag, msg, uptime_ms)`; a caller cannot widen the tag or message columns at
runtime.

There is therefore no “absent”, “empty” or “malformed environment value” path. The only input
validation is in `logfmt_make` (tag/message length) and `logfmt_parse` (strict line grammar).

## Mismatches

- **R13-020-G1** — the requested env-var list is empty; configuration is not runtime-tunable.
  See `services/logfmt/GAPS_R13.md`.
