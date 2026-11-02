# Python uplink — behaviour record (B219)

Source: `os/os/uplink/relay_uplink.py` (321 lines). Unit:
`os/os/services/relay-uplink.service`. The code is the authority; every
claim cites a line range.

## What it is

The order door for one machine: it validates phone orders, deduplicates
them by order id, signs them with a caller-supplied HMAC key, and turns
each into an `ORDER` job-set intake record — or queues it while the
connection is down (`relay_uplink.py:1-92`, `:172-222`). It makes no model
call, posts no bus message, and moves no claim.

## Inputs

| Input | Shape read | Where |
|---|---|---|
| `orders` | list of dicts: `id` (required), `text` (required, non-empty), `origin` (required), `received_at` (optional, record only) | `validate_order`, `:105-116` |
| `state` | dict: `seen_ids`, `pending`, `failures`, `next_retry_at` | `empty_state`, `:101-103`; `tick`, `:172-222` |
| `now` | unix seconds, used only for backoff on a failed connection | `record_failure`, `:124-131` |
| `connected` | bool | `tick`, `:180-182` |
| `key` | signing key string or `None` | `sign_intake`, `:118-122` |
| `crew_mode` | bool; unsigned intake is refused | `_take_in`, `:162-167` |

## Outputs

`tick()` returns `(events, new_state)` and never mutates its inputs
(`:172-222`). Event types:

| Event | Meaning | Fields | Where |
|---|---|---|---|
| `intake` | order became a record | `order_id`, `record` | `:168-170`, `:154-161` |
| `queued` | connection down; valid order waits | `order_id` | `:218-221` |
| `duplicate` | id already seen or already pending | `order_id` | `:157-159`, `:208-212` |
| `rejected` | validation failed | `order_id`, `reason` | `:196-200`, `:202-206`, `:213-217` |
| `unsigned-refused` | crew mode with no key; order stays pending | `order_id`, `reason` | `:162-167` |

Intake record shape: `order_id`, `text`, `origin`, `received_at` (may be
`None`), `kind: "ORDER"`, `signed`, `signature` (HMAC-SHA256 over
`id + "\n" + text`) (`:141-152`). No `files`, no invented accept lines.

Backoff after `n` consecutive failures is `5 * 2^(n-1)` capped at 300
seconds; `n <= 0` is 0 (`:93-99`, `:124-131`). One success clears failures
and the retry time (`:133-139`).

## Refusals

| Input | Refusal | Where |
|---|---|---|
| order not a dict | `order is not an object` | `:105-107` |
| missing/falsy `id` | `order id missing` | `:108-110` |
| `text` not a str, or whitespace only | `order text empty` | `:111-113` |
| missing/falsy `origin` | `order origin missing` | `:114-116` |
| crew mode and no key | `unsigned-refused`, stays pending | `:162-167` |
| orders file is not a JSON list | CLI exits 2, no cycle | `:259-261` |
| state file is not a JSON object | CLI exits 2 | `:262-264` |
| orders/state JSON malformed | CLI exits 2 | `:224-233` |
| key file unreadable | CLI returns 2 | `:247-252` |

## Writes

- The state file is written at the end of **every** CLI cycle, even when
  no event fired (`:279-281`). `tick()` itself writes nothing.
- Pending orders are drained before new orders on a connected cycle
  (`:186-195`), in stored order; invalid pending records are rejected and
  dropped (`:190-195`).

## CLI

`--once` or `--loop` is required; `--interval` default 10; `--max-cycles 0`
means forever; `--orders-file` and `--state-file` are required;
`--key-file`, `--crew-mode`, `--disconnected`, `--now` are optional
(`:235-278`). Exit 0 on a completed cycle, 2 on bad input/usage.

## Findings (reported, not fixed)

1. **Order ids are not type-checked.** `if not order.get("id")` accepts a
   non-zero int, and a whitespace-only string `" "` is truthy
   (`:108-110`). The intake record then carries a non-string `order_id`,
   while the HMAC input stringifies it (`:118-122`, `:141-152`).
2. **`tick()` drops unknown state fields.** It rebuilds the state from
   only `seen_ids`, `pending`, `failures`, `next_retry_at` (`:180-186`),
   so any extra caller-owned key is lost on the next write.
3. **A disconnected cycle never revalidates pending orders.** Validation
   happens on drain, not on queueing: a pending record that was valid when
   queued is revalidated on reconnect and can be rejected then
   (`:190-195`). That is safe, but the rejection arrives one cycle late.
4. **No bound on `pending`.** An offline machine accepts every valid order
   into the state file (`:218-221`); there is no cap or expiry.
