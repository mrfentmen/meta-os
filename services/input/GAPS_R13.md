# Gap records — R13-018 input

## R13-018-G1 — no socket path

- **Claim:** `input` can be reached over the socket layer.
- **Reality:** no `socket`, `sock_`, `sys_sock`, `fd`, `connect`, `recv`, `send` or `peer`
  identifier occurs in `services/input/*.goose`. The module exposes only direct function calls
  (`input_decode`, `input_repeat`, `input_passthrough`).
- **Evidence:** the facet grep in `CONTRACT_R13.md` returns no matches.
- **Impact:** an out-of-process consumer (agent view, remote keyboard) has no endpoint. Input
  reaches the decoder only through the kernel's in-process path.
- **Owner:** input IPC binding; socket service integration.

## R13-018-G2 — `Decoder.dropped` is dead state

- **Claim:** the decoder counts dropped events.
- **Reality:** `Decoder.dropped` is declared and initialised, but `input_decode` takes no output
  buffer and no refusal path increments it. The README already records this.
- **Evidence:** `services/input/input.goose` (`dropped` field); README section “Calls”, final
  paragraph.
- **Impact:** a caller cannot learn that an event was lost, and a future socket ring has no
  back-pressure counter to expose.
- **Owner:** input decoder; socket ring integration.
