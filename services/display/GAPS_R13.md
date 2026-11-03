# Gap records — R13-012 display

## R13-012-G1 — no machine-readable output schema

- **Claim:** `display` has an output schema an agent view or remote consumer can parse.
- **Reality:** `disp_paint` emits raw console bytes one row at a time. It carries no console id,
  row index, column count or framing beyond a newline, and empty rows are omitted. The only
  machine-readable output is an `i64` return code.
- **Evidence:** `services/display/display.goose:255-272`.
- **Impact:** a second consumer (the Layer 5 agent view, or a socket-backed console) must already
  know which console is active and how many rows to expect. The README's “structured view” is
  not served by this output path.
- **Owner:** display output contract; Layer 5 agent view.

## R13-012-G2 — write failures are swallowed

- **Claim:** `disp_paint` reports the outcome of painting.
- **Reality:** both `sys_write_console` calls at lines 266-267 discard their return value. The
  function returns `CODE_OK` even when the kernel refused every byte.
- **Evidence:** `services/display/display.goose:265-271`.
- **Impact:** a caller cannot distinguish a painted console from a full or disconnected serial
  sink. This is the same class of silent-write failure the bootlog contract explicitly avoids.
- **Owner:** display paint path; kernel console write contract.
