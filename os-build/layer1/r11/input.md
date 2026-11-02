# input — Round 11 record

Source: `services/input/input.goose`, `services/input/keymaps2.goose` ·
Test: `services/tests/t121_input_r11.goose` · Status: RUNS (t56 49 checks, t102 38 checks); t121 written, run pending

## 1. Limits — PROVEN

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `KEY_CAPSLOCK` | `0x3A` | `input.goose` | **not a limit**: a key id, matched by the LIMITS heuristic. Driven by `tests/t56_input_display` as a name; t121 asserts the latch behaviour on that scancode | LIMITS.md; t121 §3 (pending run) |
| `MOD_CAPS` | `8` | `input.goose` | **not a limit**: a bit flag (`MOD_*`). No caller can exceed a mask; t121 asserts caps+shift XOR | LIMITS.md "Not limits" |

There is no numeric capacity in this service: the keymap is an if-chain, not a table, and the
only per-call state is the `Decoder`. The two numbers that do behave like limits are the floors
in `input_init` — `repeat_delay_ms >= 250` and `repeat_rate_ms >= 16`. They are clamps, not
refusals, so they are driven as behaviour: t121 shows silence at 249 ms and a repeat at 250,
silence at 15 ms after a repeat and one repeat at 16.

## 2. Refusals — NAMED GAP

| refusal | code | the assertion | status |
|---|---|---|---|
| scancode below 0 | `got_event = false` | t121 `decode: -1 is refused` | pending run |
| scancode above 255 | `got_event = false` | t121 `decode: 256 is refused` | pending run |
| unknown dead key | `compose_arm == false` | t121 `an unknown dead key is refused` | pending run |
| NUL fed to the composer | `E_NOKEY`, `emit = false` | t121 `a NUL byte is E_NOKEY` | pending run |
| repeat with nothing held | `got_event = false` | t121 `a release with no press leaves nothing to repeat` | pending run |

**Finding — `Decoder.dropped` is a dead field.** It is declared and initialised to 0 in
`input.goose`, and no function in the file reads or increments it. The comment calls it "events
refused because no buffer was offered", but `input_decode` takes no output buffer, so there is
no path that could refuse for that reason. This is a field that describes a mechanism the
service does not have. It is recorded here; removing it or implementing the buffer contract is
a decision for the owner, not a silent edit in a documentation round.

## 3. Restart — NAMED GAP

The decoder's entire state is module globals: modifiers, the held key, the next repeat time and
the repeat floors. A supervisor restart resets them to `input_init` values; nothing is persisted
and nothing is meant to be. The loss is one held key and a caps latch at the moment of the
restart — a user-visible change of modifier state, not data. No supervisor restart of this
service has been run, so this is stated, not proven.

## 4. Contract — PROVEN

`input.goose` imports `common.err.err` and nothing else; `keymaps2.goose` imports the same and
`input.input`. The matrix row `SVC_INPUT` is `session | display | log`.

| direction | other service | call | in the matrix? |
|---|---|---|---|
| in | `session`, `display` | consume `KeyEvent` from `input_decode` / `input_repeat` | yes — both bits set on `SVC_INPUT`'s row |
| out | `session`, `display` | none — the decoder calls nobody | **declared but dormant**: the bits describe who may call input, not what input calls |
| out | `log` | none in the source | **declared but dormant** — no import, no call |

No call the matrix does not know. No finding for room 1 in this service.

## 5. Load — NAMED GAP

The load loop is 200 decodes of one arrow scancode — ten times a normal batch of 20 key events —
and approaches no limit: the decoder has no queue and drops nothing, which is exactly the gap
`Decoder.dropped` describes. The number below comes from the coordinator's run.

RUNS pass=33 fail=0 · `LOAD input ops=200 ok=200 refused=0`

## 6. README truth pass — PROVEN

- **Status line:** said `WRITTEN (not COMPILED — no Goose toolchain on this Mac)`. It now says
  RUNS, names `t56_input_display` (49 checks) and `t102_keycompose` (38), and cites the rows.
- **Closing line:** `Not compiled, not run.` was false and is gone.
- **Calls table:** already accurate for the four entry points. Added the repeat floors as
  behaviour (250 ms / 16 ms) rather than "defaults", because `input_init` clamps them.
- **New honest sentence:** the `Decoder.dropped` field is declared but nothing writes it; the
  README now says so instead of leaving a reader to infer a refused-event path that does not exist.
- **Keymap section:** unchanged and true — US is an if-chain, unmapped keys return 0.
