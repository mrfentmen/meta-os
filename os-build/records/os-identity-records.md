# Record shapes — crates/os-identity (B054)

The crate writes two Redis shapes and reads a third. One worked example of
each, annotated field by field. Concrete values are a real registration
(`register("milo", ["Python"," testing ","python"], "builder", 2,
"dm-abc", "on mac")` under the default config) so the example can be
reproduced from the code.

## 1. Agent hash — `<ns>:<nick>` (written by `register`, `touch`)

Key: `muse-bus:cap:milo` (`Config::key_for`, `lib.rs:98-101`).

```text
caps      "python,testing"
roles     "builder"
max_jobs  "2"
host      "relay-1"
updated   "1762100000"
dm        "dm-abc"
info      "on mac"
```

| Field | Type on the wire | Written by | Default on read | Omitted when | Source |
|---|---|---|---|---|---|
| `caps` | string, comma-joined, sorted, lowercased, unique | `register` | `""` | never by `register` (validation requires ≥1) | `lib.rs:324-336`, `344`; `from_fields` 127 |
| `roles` | string | `register` | `None` | `roles == ""` | `lib.rs:345`, `145-147` |
| `max_jobs` | decimal string of `i64` | `register` | `"1"` | caller-built record with `""` | `lib.rs:346`, `149`; `from_fields` 129 |
| `host` | string (constructor arg) | `register` | `""` | `host == ""` | `lib.rs:347`, `150` |
| `updated` | decimal string, Unix seconds | `register`, `touch` | `"0"` | caller-built record with `""` | `lib.rs:348`, `151`, `368`; `from_fields` 130 |
| `dm` | string (DM dead-drop secret) | `register` | `None` | `dm_secret == ""` | `lib.rs:349`, `152-154` |
| `info` | string | `register` | `None` | `info == ""` | `lib.rs:350`, `155-157` |

Reading back: `AgentRecord::from_fields` (`lib.rs:126-137`) sets the
defaults above for missing fields and ignores unknown ones. A record with
only `caps` reads as `max_jobs="1"`, `updated="0"`, `host=""`, options
`None`.

## 2. Index entry — `<ns>:index` (written by `register`, `touch`; removed by `unregister`)

Key: `muse-bus:cap:index` (`Config::index`, `lib.rs:103-105`).

```text
ZADD muse-bus:cap:index 1762100000 milo
```

| Part | Meaning | Source |
|---|---|---|
| key | `<capns>:index` | `lib.rs:103-105` |
| score | `updated` as Unix seconds | `lib.rs:355`, `369` |
| member | nick, exactly as passed (transport quotes it) | `lib.rs:355` |

Ordering: `agents()` consumes `zrange` order (`lib.rs:399`); `MemoryStore`
sorts `(score, member)` (`lib.rs:557-569`). Re-registering updates the
score, so `zadd` is an upsert, not a duplicate (`lib.rs:354-355`: `hset`
then `zadd`). `unregister` removes the member (`lib.rs:378`); a missing
member is not an error (`MemoryStore::zrem`, `lib.rs:546-551`).

## 3. Job claim — read-only input to `active_claims`

The crate does not write jobs. It reads one `JobClaim` per job
(`lib.rs:190-196`) and counts the pair that means "this agent holds it".

```text
status  "claimed"
claim   "milo"
```

| Field | Type | Counted when | Source |
|---|---|---|---|
| `status` | string | `== "claimed"` exactly (case-sensitive) | `lib.rs:414-421` |
| `claim` | string | `== nick` exactly | `lib.rs:414-421` |

A job with `status="done"` or `claim="rowan"` does not count
(`lib.rs:414-421`; pinned by the in-crate test
`find_for_ignores_non_claimed_and_other_agents_jobs`, `lib.rs:823-836`).
Any `job_claims` read error collapses the whole count to 0
(`lib.rs:415-422`) — see the deviation in F1 of the behaviour record.

## 4. Error shape returned to callers

`StoreError` is a one-field newtype whose `Display` prefixes
`store error: ` (`lib.rs:178-187`). `RegistryError::Store` forwards that
string (`lib.rs:247-255`), and `From<StoreError>` is the only automatic
conversion (`lib.rs:258-261`). Validation errors carry Python's exact
wording (`lib.rs:226-236`):

```text
register("", [...])        -> "nick required"
register("milo", ["  "])   -> "at least one capability required"
store.hset failing         -> "store error: <inner>"
```
