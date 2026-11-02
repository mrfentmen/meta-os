# intel — behaviour record (B169)

Scope: `crates/intel/`. Six subtrees: `b09_core` (core records,
capability, gate, ladder, ingest), `b10_brief` (brief, dispatch, push,
alerts, baton, forecast, notify, wake, window, sections), `b11_spark`
(mind images, skills loader, Spark client), `b12a_drills` (drill and
check code), `b13_devpack` (dashboard payload shaping), `b14_trust`
(trust gate, timer sweep, launch run).

Every claim below is read from the code as written. Status words:
LIVE (reached from a public function), BUILDER (produces a value, no
I/O), UNPORTED (named in `intel-gaps.md`).

## 1. What the crate does

### b09_core

- **Records and keys.** `store::brief_key`, `alert_key`,
  `alert_index_key`, `notify_key`, `notify_index_key`, `dispatch_key`
  build the `<prefix>:intel:*` layout from `MUSE_RELAY_KEY_PREFIX`
  (default `muse-bus`) — `store.rs:14-35`. The Rust `Store` is
  in-memory (`store.rs:75-113`).
- **Alert lifecycle.** `write_alert` validates the WDG-010 shape,
  defaults `last_seen` to `created_at` and `status` to `open`, keeps an
  acknowledged alert acknowledged on re-fire, and rebuilds the index
  entry — `store.rs:89-113`. `acknowledge_alert` only moves an `open`
  alert (`store.rs:122-131`); `resolve_alert` resolves any existing id
  (`store.rs:132-140`); `auto_resolve_cleared` resolves every
  unresolved alert whose dedupe key is not firing (`store.rs:141-152`).
- **Spend ledger.** `record_spend` appends `ts:cents:label` lines to
  one string; `spend_total` sums the second colon field, ignoring
  unparsable lines — `store.rs:153-170`.
- **Capability enforcement.** `check_action` judges four actions
  (`bus_post`, `spend`, `network`, `write_file`) against a grant, in a
  fixed order: unknown action → no decision; missing/identity-less
  grant → refused; flag not exactly true → refused; `write_file`
  without a path or outside the grant prefixes → refused
  (`capability.rs:12, 89-168`). `normalize_path` refuses absolute,
  empty, and `..`-escaping paths (`capability.rs:37-59`).
- **Gate.** `gate_tick` parks a job when its attempt budget is spent or
  its `blocker_kind` is one of `money|permission|direction`, and emits
  a parked record plus an escalation record; an already-parked id
  yields nothing — `gate.rs:10, 94-127`. `as_int` treats bools, floats,
  decimal strings, and negatives as unusable (`gate.rs:30-48`).
- **Ladder.** `classify` maps a stall to `nudge` (registered and
  present), `restart` (registered, absent), or `reassign` (unregistered
  claimer); malformed stalls and unknown jobs yield no action —
  `ladder.rs:44-56`. `baton_for` copies title/progress/files forward
  (`ladder.rs:58-69`).
- **Ingest.** `store_messages` skips empty and duplicate ids
  (`ingest.rs:24-38`); `messages_from_cursor` pages at `PAGE = 100`
  from an id cursor (`ingest.rs:7, 40-49`).

### b10_brief

- **Brief records.** `BriefRecord` is room + ts + text + kind
  (`brief.rs:12-17`). `parse_since` accepts `all`, a non-negative unix
  timestamp, or `<n>m|h|d` (`brief.rs:24-45`). `validate_brief_record`
  requires room, non-negative ts, non-empty text, and a kind from a
  five-name list (`brief.rs:47-60`). `brief_budget` knows three kinds
  only (`brief.rs:81-92`). `trim_to_budget` drops bullet lines from the
  end, then truncates by words with ` (trimmed)` (`brief.rs:111-141`).
  `redact_secrets` redacts `KEY=value` lines whose key contains
  SECRET, TOKEN, or KEY (`brief.rs:203-216`).
- **Dispatch gates.** `parse_plan` requires a goal, rejects unknown
  fields, and requires each job to carry a key and title
  (`dispatch.rs:39-55`). `check_file_overlap` refuses two unordered
  jobs touching one file (`dispatch.rs:57-74`). `check_dep_graph`
  refuses unknown deps and cycles and returns a topological order
  (`dispatch.rs:76-119`). `clamp_attempt_budgets` maps ≤0 to 3 and >10
  to 10 (`dispatch.rs:121-130`). `check_no_secrets` refuses three
  literal markers (`dispatch.rs:132-140`).
- **Push.** `build_done_push` needs status `done`, the verified stamp,
  `verification.ok`, and every check ok (`push.rs:58-73`).
  `build_blocked_push` needs status `blocked` and a non-empty question
  or stored note, quoted verbatim (`push.rs:75-92`). `PushLedger`
  emits each (job id, type) once (`push.rs:114-127`).
- **Forecast.** `usable_number` refuses non-finite and negative values;
  projection needs all three inputs (`forecast.rs:7-17`). Preemption
  trips only when projected **>** cap (`forecast.rs:31-33`).

### b11_spark

- `TransportKind::from_env` accepts exactly `agent` or `http`
  (`spark_client.rs:50-58`). `complete` refuses HTTP calls at or above
  the spend cap before touching the transport
  (`spark_client.rs:128-141`). `result_body_for` parses a JSON text
  envelope or returns the body as plain text with null token counts
  (`spark_client.rs:84-98`). `StubTransport` is test-only
  (`spark_client.rs:143-152`).

### b12a_drills

- Drill reports are a named list of `PhaseResult` plus a `PASS`/`FAIL`
  line (`b12a_drills/mod.rs:34-80`). State is fixture data on
  `value::Value`; sibling surfaces are traits in `deps`
  (`b12a_drills/mod.rs:1-32`). No network or Redis in a drill.

### b13_devpack

- `brief_entry` requires an int `generated_at` and an int `as_of`, then
  copies the record and adds `as_of` + `age_seconds`
  (`b13_devpack/mod.rs:51-64`).
- `plan_preview` requires the posting order to cover exactly the plan's
  job keys and sums the attempt budgets (`b13_devpack/mod.rs:94-110`).
- `alerts_feed` sorts newest first and breaks ties on id
  (`b13_devpack/mod.rs:118-123`).

### b14_trust

- The trust gate judges only open jobs, in a fixed order: absent
  signature, non-v2 signature, untrusted kid, bad recompute, expiry;
  badges are clamped to `allowed_badges` and every drop is named —
  `trust.rs:1-31`.
- `recompute_sig` is an FNV-1a stand-in labelled `v2`, not HMAC-SHA256;
  the module says it must match Python before PORTED
  (`trust.rs:44-58`).

## 2. Refusals (exact text)

| Surface | Condition | Text |
|---|---|---|
| `dispatch::parse_plan` | empty goal | `plan: missing goal` |
| `dispatch::parse_plan` | unknown fields | `plan: unknown fields: <list>` |
| `dispatch::parse_plan` | empty key/title | `plan: job needs key + title` |
| `dispatch::check_file_overlap` | unordered shared file | `plan: file overlap on <f>: <a> vs <b>` |
| `dispatch::check_dep_graph` | dep not in plan | `plan: unknown dep <d> in <key>` |
| `dispatch::check_dep_graph` | cycle | `plan: dependency cycle` |
| `dispatch::check_no_secrets` | marker present | `plan: plan carries a possible secret` |
| `brief::parse_since` | bad window | `bad --since: <s>` |
| `brief::validate_brief_record` | room/ts/text | `brief: missing room` / `brief: bad ts` / `brief: empty text` |
| `brief::validate_brief_record` | unknown kind | `brief: unknown kind <k>` |
| `brief::failure_copy_for_kind` | unknown kind | `unknown brief failure kind: '<k>'` |
| `push::build_push` | unknown type | `unknown push type: <k>` |
| `push::validate_push` | bad type / missing fields | `bad push type: <k>` / `push missing job/text` |
| `store::validate_alert` | missing id/kind/explanation/dedupe | `alert: missing <field>` |
| `capability::check_action` | no grant / not granted / no path / outside grant | `no capability grant on file` / `capability not granted` / `no file path given` / `write path outside grant` |
| `join::validate_*` | bad input | `bad machine name` / `bad room address` / `room key too short` / `empty trusted kid` |
| `explanations::render` | unknown key / missing field | `unknown template: <k>` / `missing placeholder: <name>` |
| `spark_client::TransportKind::from_env` | unknown transport | `spark not configured: unknown SPARK_TRANSPORT: <v>` |
| `spark_client::complete` | HTTP at/over cap | `spark budget: spend cap reached: <spent> >= <cap>` |

An unknown capability action returns `None` (no decision) rather than a
refusal — `capability.rs:89-93`.

## 3. What it writes

- Store keys: brief, alert, alert index, notify, notify index, dispatch
  (`store.rs:18-35`), spend (`store.rs:153-160`).
- In-memory: `Store.strings`, `Store.zindex`, `Store.alerts`
  (`store.rs:75-80`).
- Brief records (`brief.rs:12-17`), journal records (`gate.rs:85-92`),
  push records (`push.rs:34-39`), drill reports
  (`b12a_drills/mod.rs:34-80`).
- Devpack payload shapes (`b13_devpack/mod.rs:18-23, 51-131`).

## 4. Findings (B172 — reported, not silently fixed)

1. **`validate_brief_record` accepts two kinds Python refuses.**
   Rust accepts `morning|ondemand|boot|onjoin|daily`
   (`brief.rs:47-60`); Python's `BRIEF_KINDS` is
   `("morning", "onjoin", "ondemand")` and validation rejects the rest
   (`os/intel/brief.py:146, 695-713`). The Rust file also contradicts
   itself: `BRIEF_KINDS` at `brief.rs:76` has three entries. A record
   with kind `boot` or `daily` validates in Rust and is refused in
   Python.
2. **`cap_snapshot_window` can panic on multibyte text.** It slices
   `&text[..budget]` by bytes (`brief.rs:195-201`); a budget landing
   inside a multi-byte character panics. Python slices characters.
3. **Two different budget units.** `trim_to_budget` counts words
   (`brief.rs:111-141`) while `brief_exceeds_budget` compares bytes
   (`brief.rs:222-224`), so a text can be "over budget" to one function
   and unchanged by the other.
4. **`Store::query_alerts` sorts oldest-first** (`store.rs:117-120`)
   while `b13_devpack::alerts_feed` sorts newest-first
   (`b13_devpack/mod.rs:118-123`). Two reader surfaces disagree on
   order.
5. **The resolved→open re-fire branch is empty.** `write_alert` has an
   `if prev.status == "resolved" && r.status == "open" { }` block with
   only a comment (`store.rs:99-102`); it describes an occurrence reset
   that no code performs.
6. **Ingest summary is weaker than its doc claimed.** `snapshot`
   returned only `snapshot: <n> messages` while the comment promised
   room counts and the latest timestamp (`ingest.rs:50-52`). Doc fixed
   to the code.
7. **The gate's escalation record is not a validated push.** The module
   comment said it carried the built blocked-push payload; the Rust
   record carries the question text only (`gate.rs:1-8, 94-127`). Doc
   fixed to the code.
8. **`trust::recompute_sig` is not a signature check yet.** It is an
   FNV-1a stand-in formatted as `v2:<hex>` (`trust.rs:44-58`), so a
   forged signature with the same hash would pass the order tests but
   not a real HMAC gate. The module states this; it stays a finding
   until gate 2.
9. **`done_summary` can say "no acceptance criteria were recorded"**
   when `verification.checks` is empty even though `verification.ok`
   is true (`push.rs:41-56`); the push is allowed, but the sentence
   reads as a gap in evidence.
