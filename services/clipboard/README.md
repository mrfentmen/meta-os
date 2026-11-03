# clipboard

A bounded shared clipboard: 4096 bytes, one owning session, a monotonic
generation counter. Layer 4 library, no kernel calls of its own.

Status: **TYPECHECKED** in `services/root.goose`; tests in
`services/tests/t141_clipboard.goose`. Not run on a kernel — no session store
exists to own a clipboard across processes yet.

## Contract

| call | returns | refusal |
|---|---|---|
| `clip_set(data, owner)` | `CODE_OK` | `E_NOROOM` if `data.len > 4096`; `E_INVAL` if empty or owner < 0 |
| `clip_get(out, cap)` | `(bytes, CODE_OK)` | `E_NOTFOUND` if empty; `E_NOROOM` if `cap < len` (nothing written) |
| `clip_clear(owner)` | `CODE_OK` | `E_NOTFOUND` if already empty (checked before ownership); `E_DENIED` if a different session owns it |
| `clip_generation()` | `i64` | increases on every successful set or clear |

All-or-nothing is the point: a refused set leaves the old content intact, and a
refused get writes no partial prefix. Paste must never insert half a document.

There is no "unowned content" state: `clip_set` requires an owner, so `-1` only
describes an empty clipboard, where `clip_clear` returns `E_NOTFOUND` first.

## What is deliberately absent

- Multiple formats. One byte buffer; the caller encodes.
- Push notification. Readers poll `clip_generation()`; there is no event bus yet.
- Persistence. The clipboard does not survive a reboot, by design.
