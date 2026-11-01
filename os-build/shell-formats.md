# Shell formats as data (H2)

Branch: `hana/os-shell`. Companion data file: `shell-formats.json`
(the same strings and fields, machine-readable). The test
`tests/os-shell-formats.test.mjs` checks the two agree on the
exact strings. If they ever disagree, the JSON is wrong until
fixed — the doc does not silently win.

Status: FORMAT SPEC ONLY. Defining a format is not emitting it.
No kernel or service in this branch emits any of these strings.
Emission is NOT BUILT until a QEMU boot log shows it.

## Shared rules

- One fact, two forms. The console line and the agent record
  carry the same fact. They are defined together and must never
  disagree.
- Unmeasured facts are never faked. On the console, a line whose
  fact is not yet measurable is OMITTED — never printed with a
  guessed number, a zero, or a question mark. In the agent
  record, an unmeasured field is JSON `null`.
- `memory_kib` becomes measurable when the kernel sums the boot
  memory map (targeted: K2 console). `tasks` becomes measurable
  at K5 (scheduling). `ticks` becomes measurable at K3 (timer).
  `heap` becomes measurable at K4 (heap). Until then: omitted
  on console, `null` in the record.
- The word OS is used only for the layered system. Programs are
  called programs (OPENCODE OS-221).

## Banner (console, from K2)

Four lines maximum, one fact each, in this exact order. Lines
for unmeasured facts are omitted (see shared rules).

```
META OS
milestone K<n>
memory <total_kib> KiB
tasks <count>
```

- Line 1 is exactly `META OS` (uppercase, one space).
- Line 2 is `milestone ` followed by `K` and the milestone
  number, for example `milestone K1`.
- Line 3 is `memory ` followed by an integer count of KiB,
  followed by ` KiB`, for example `memory 1048576 KiB`.
- Line 4 is `tasks ` followed by an integer count, for
  example `tasks 3`.
- At K2 the banner is 3 lines (tasks omitted until K5).
  At K1 there is no banner at all — only the alive line
  `META OS KERNEL - alive (K1)` on serial.

## Agent record (serial, JSON, one object per line)

One JSON object, one line, on the serial port. Field order in
the object is fixed as listed. `record` says which kind it is.

```json
{
  "record": "boot",
  "os": "Meta OS",
  "milestone": "K1",
  "kernel_version": "0.1.0",
  "memory_kib": null,
  "tasks": null,
  "ticks": null,
  "heap_used_kib": null,
  "heap_total_kib": null,
  "status": "alive"
}
```

- `record`: `"boot"` for the boot record, `"status"` for a
  status answer. Always present.
- `os`: exactly `"Meta OS"`. Always present.
- `milestone`: `"K1"` through `"K6"`. Always present.
- `kernel_version`: the kernel crate version from
  `kernel/Cargo.toml` (currently `"0.1.0"`). Always present.
- `memory_kib`: integer, or `null` until measurable (K2).
- `tasks`: integer, or `null` until measurable (K5).
- `ticks`: integer, or `null` until measurable (K3).
- `heap_used_kib`, `heap_total_kib`: integers, or `null`
  until measurable (K4).
- `status`: `"alive"` when the alive line printed, `"panic"`
  when the panic line printed. No other values. Always present.

The agent never scrapes the console to learn these facts. It
reads this record.

## Status command (console, from K3/K4/K5 as noted)

Command: `status`. Output is one line per measured fact, in
this order. Unmeasured lines are omitted.

```
tasks <count>
ticks <count>
heap <used_kib>/<total_kib> KiB
```

- `tasks <count>` appears from K5 only.
- `ticks <count>` appears from K3 only.
- `heap <used_kib>/<total_kib> KiB` appears from K4 only,
  for example `heap 128/4096 KiB`.
- Before K3, `status` is NOT BUILT as a running command and
  prints nothing, because no shell exists yet.

The agent form of a status answer is the agent record above
with `"record": "status"`.

## Help command

Command: `help`. It prints one line per REAL command, in this
format:

```
<name> - <one-line description>
```

It lists ONLY real commands. It never lists unbuilt commands.
With zero real commands — which is the truth today, because no
shell exists yet — it prints exactly:

```
commands: (none yet)
```

That line is the honest empty state. It is not a placeholder
screen and it promises nothing.

## Shell prompt

When the shell waits for input, it prints exactly:

```
metaos> 
```

That is `metaos`, `>`, and one trailing space. The prompt
itself is NOT BUILT: no shell exists yet to print it.

## Bad input (OS-211)

The shell survives bad input. Each case is handled, never
crashing the shell:

- Unknown command: prints `unknown command: <first-token>`,
  where `<first-token>` is the first word typed, truncated to
  64 characters. The rest of the line is dropped, never echoed.
- Long line (over 256 characters): prints
  `line too long, ignored`. The input is dropped, nothing
  from it is echoed.
- Empty line: no output, no error. It is ignored.

All three cases are NOT BUILT as running behavior: no shell
exists yet to handle them. The strings above are the specified
handling, not observed behavior.

## Limits (exact numbers)

- Maximum console input line: 256 characters.
- Maximum echoed token in `unknown command:`: 64 characters.
- Serial: COM1, 38400 baud, 8N1 (from K1 source).
- Agent record: one JSON object per line, UTF-8, no trailing
  text after the closing brace on that line.
