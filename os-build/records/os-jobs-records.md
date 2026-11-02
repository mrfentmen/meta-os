# `os-jobs` — worked record shapes, field by field

B030. One example of every record kind the crate writes. The values are
reconstructed from the code path and the crate's own tests at the
fixture clock `1_700_000_000` (`src/lib.rs:2607`); this is not a capture
from a live Upstash store, because the crate has no transport (G1 in
`os-jobs-gaps.md`). Strings are shown as the store sees them: Redis
hash/string/zset members are text, so integers are quoted.

## 1. Sequence key — `{ns}seq`

```
key:   muse-bus:tjobseq
value: "1"
```

Written by `store.incr(&seq_key(ns))` (`lib.rs:1414-1421`). The value
is the last id handed out; `post` uses it as the job id and never
decrements it. `valid_id` accepts `"1"` (all digits, not all zero,
`lib.rs:934-940`).

## 2. Job hash after `post` — `{ns}:{jid}`

```
key: muse-bus:tjob:1
fields:
  title        = "port the queue"
  room         = ""                    # clean_room("") is the default room
  branch       = "bond/os-jobs"
  base         = "4bdf3ef"
  accept       = "tests green"
  status       = "open"
  lease        = "1800"
  created_by   = "tester"
  created_host = "host-a"
  created_at   = "1700000000"
  files        = "crates/os-jobs/**"
  deps         = ""
  attempts     = "0"
  artifacts    = ""
  req          = "rust,queue"
  max_attempts = ""                    # omitted entirely when None
```

Field-by-field (writer at `lib.rs:1422-1435`):

- `status` starts `open`; only `claim` moves it to `claimed`.
- `lease` is the requested default in seconds, not the remaining time.
- `created_at` is whole Unix seconds from the queue's clock.
- `req` is normalized by `normalize_req` (lowercase, deduped, order
  kept, `lib.rs:921-932`).
- Empty optional values are **not written** at all: `JobQueue::hset`
  filters empty values (`lib.rs:984-998`), so a default post has no
  `files`, `deps`, `artifacts`, `req`, or `max_attempts` field.

## 3. Spec string — `{ns}:{jid}:spec`

```
key:   muse-bus:tjob:1:spec
value: "port the queue\n\nacceptance: cargo test -p os-jobs\n"
```

Written verbatim (`lib.rs:1436`). It is a separate key, not a hash
field, so `show` can print it after the fixed field list
(`lib.rs:1645-1647`) and `job_get` returns it alongside the hash
(`lib.rs:1035-1057`). A missing spec reads as `""`, not an error.

## 4. Index zset — `{ns}index`

```
key:    muse-bus:tjobindex
member: "1"          score: 1700000000
```

One member per posted job; score is the post time
(`lib.rs:1441-1445`). `FakeStore::zrange` sorts `(score, member)`
(`lib.rs:303-317`), so two jobs posted in the same second list in
lexicographic id order — `"1"`, `"10"`, `"2"` — not numeric order. That
ordering is pinned by `tests/edge_cases.rs`.

## 5. Claim mutex — `{ns}:{jid}:claim`

```
key:   muse-bus:tjob:1:claim
value: "tester"      TTL: 1800s
```

Written with `SET NX EX lease` (`lib.rs:1816-1823`). Exactly one worker
wins; the loser reads the holder and reports `lost the race`
(`lib.rs:1826-1833`). The mutex is separate from the hash so its TTL can
expire while the hash stays readable: `claim_or_requeue` treats a
`claimed` hash with a missing mutex as an expired lease and reopens it
(`lib.rs:1169-1187`).

## 6. Job hash after `claim`

Added/changed fields (writer at `lib.rs:1833-1844`):

```
status      = "claimed"
claim       = "tester"
claim_host  = "host-a"
claimed_at  = "1700000000"
lease_until = "1700001800"
lease       = "1800"
```

`lease_until` is `now + lease`; it is advisory for display, while the
mutex TTL is what actually expires. `done`/`blocked` delete `claim`,
`claim_host`, `claimed_at`, and `lease_until` and delete the mutex
(`lib.rs:1955-1985`, `2001-2032`).

## 7. Signature block after a signed `post`

```
sig        = "9f2c…"                  # 64 lowercase hex chars
sig_v      = "2"
sig_kid    = "main"
signed_by  = "tester"
nonce      = "0f1e2d3c4b5a6978"       # 16 hex chars
expires_at = "1700003600"             # "" when --expires was not given
```

The digest covers the canonical v2 payload (`lib.rs:623-643`) with
`created_at`/`expires_at`/`nonce` included. The key id is inside the
payload, so a signature cannot be moved to another key or job. A
missing `sig` means `UNSIGNED` (`lib.rs:1199-1204`); an unknown kid is
`BAD` (`lib.rs:1222-1227`).

## 8. Announcement tuple

```
("muse-bus:room:ops", "tester: JOB:1 port the queue")
```

The key comes from `bus_key(room)` (`lib.rs:390-399`); the text is
`"{nick}: {event}"` (`lib.rs:1156-1168`). Event shapes:

```
JOB:{jid} {title}
CLAIM:{jid} by {nick}
PROGRESS:{jid} {note}
DONE:{jid} {commit}
BLOCKED:{jid} {reason}
REQUEUE:{jid}
REJECTED:{jid} {BAD|EXPIRED} signed_by={nick} rejected_by={nick}
```

They are recorded, not sent (`lib.rs:958`, `974-981`).

## 9. Nick-claim key

```
key:   muse-bus:nickclaim:tester
value: "host-a"       TTL: 120s
```

Written with `SET NX EX NICKCLAIM_TTL` (`lib.rs:1070-1101`); the value
is the host, URL-quoted on the way in only if it contains reserved
characters (`nickclaim_key`, `lib.rs:423-427`), and URL-decoded once on
read (`nick_holder`, `lib.rs:1059-1068`). The TTL equals presence
(`PRESENCE_TTL = NICKCLAIM_TTL = 120`, `lib.rs:82-87`).

## 10. Environment jobs entry

`environment_jobs_record` accepts a jobs list and returns only entries
that are `status == "claimed"`, with a non-empty string `claim` and a
non-empty string `title` (`lib.rs:2318-2355`):

```json
{"id": "5", "title": "brief panel", "status": "claimed", "claim": "rowan"}
```

An `id` that is an int is carried as an int; an id that is missing,
empty, a bool, or another type is left out rather than invented. A
non-list input returns `None` so the record omits "jobs" and
`environment_lines` renders "Working now: not reported in this
snapshot" (`lib.rs:2479-2540`).

## 11. Command outcome triples

```
post  ok:    { code: 0, out: "JOB 1\n", err: "" }
post  bad:   { code: 2, out: "", err: "ERROR: --spec is empty\n" }
claim lost:  { code: 2, out: "", err: "ERROR: lost the race — job 1 claimed by 'other'\n" }
claim bad:   { code: 1, out: "", err: "ERROR: job 1 signature BAD — not claiming\n" }
verify ok:   { code: 0, out: "OK\n", err: "" }
verify bad:  { code: 1, out: "BAD\n", err: "" }
```

`CmdOutcome` is the only return type of a command (`lib.rs:847-864`).
Exit code 2 is a refusal or a store failure; exit 1 is a verdict
(`claim` rejected a signature, `verify` did not return `OK`).
