# Contract note — R13-014, dock failure code table

Status: **AUDITED — 2 gaps filed**.
Facet: the complete set of failure codes the dock can return, and whether each code is reachable
and documented.

## Evidence

Command:

```sh
grep -nE 'E_[A-Z]+|CODE_OK|^fn dk_' services/dock/dock.goose
```

Relevant output:

```text
103  if name.len == 0 { return -1, E_INVAL; }
104  if name.len >= DK_NAME_MAX { return -1, E_NOROOM; }
110  if dk_find_name(name) >= 0 { return -1, E_STATE; }
111  if count >= DK_MAX { return -1, E_NO_SPACE; }
139  if items[at].running { return E_BUSY; }
140  if items[at].pending { return E_BUSY; }
161  if index < 0 || index >= count { return E_INVAL; }
186  if now_ms - items[at].pending_since_ms < DK_DEDUPE_MS { return E_BUSY; }
203  if !items[at].pending { return E_STATE; }
230  if !items[at].running { return E_STATE; }
```

## Corrected contract

| Code | Reachable from | Meaning |
|---|---|---|
| `CODE_OK` | all successful mutators | accepted |
| `E_INVAL` | `dk_pin`, `dk_move` | empty/control-character name, or out-of-range index |
| `E_NOROOM` | `dk_pin` | name is `>= DK_NAME_MAX` (16) bytes |
| `E_NO_SPACE` | `dk_pin` | dock already holds `DK_MAX` items |
| `E_STATE` | `dk_pin`, `dk_result`, `dk_running_off` | duplicate name, no pending launch, or app not running |
| `E_BUSY` | `dk_unpin`, `dk_launch` | app running or launch pending; second click inside dedupe window |
| `E_NOTFOUND` | `dk_unpin`, `dk_move`, `dk_launch`, `dk_result`, `dk_running_off` | unknown id |

`dk_launch` dedupes only while `now - pending_since < DK_DEDUPE_MS`; at exactly 1500 ms it is a
new launch. `dk_expire` uses `>= DK_LAUNCH_TIMEOUT_MS`; at exactly the timeout the launch has
already expired. The README states both edges correctly.

## Mismatches

- **R13-014-G1** — no consolidated code table exists in the README.
- **R13-014-G2** — `E_NOROOM` and `E_NO_SPACE` both mean capacity exhaustion for `dk_pin`, but
  the README never distinguishes them. See `services/dock/GAPS_R13.md`.
