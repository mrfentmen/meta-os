# `registry` — not a service (pointer)

**Status: NOT A SERVICE.** This directory holds no source and defines no entry point. It exists
so the MANIFEST row for "registry" is not a dead link.

## Where the registry actually is

The name-to-handle registry lives inside the supervisor, in
`services/supervisor/supervisor.goose`:

| Function | Answers |
|---|---|
| `sup_register` | append a named service, return its slot handle |
| `sup_lookup` | resolve a name to its current handle |
| `sup_release` | free a stopped service's slot |
| `sup_resolve` | resolve a handle to a live slot, or -1 |

It is there and not here because every caller already goes through the supervisor; a second
table would be a second answer, and the disagreement between them would be the bug.

## Why there is no separate service

- **No `SVC_REGISTRY` id.** The call matrix gives a row to services that can be called. A
  registry with no addressable entry point would be a row nobody can use.
- **No `svc_entry`.** There is nothing to start.
- **No limits or refusals of its own.** `NAME_MAX`, `MAX_SERVICES` and `HANDLE_GEN_MAX` are the
  supervisor's, listed under `supervisor` in `os-build/layer1/LIMITS.md` and driven by
  `tests/t52_supervisor`, `tests/t75_supervisor_load` and `tests/t83_sup_deep`.

## What is not proven

A supervisor restart loses every name and handle; boot re-registration is specified in
`services/supervisor/bootorder.goose` but no run has shown that handles are equivalent after a
restart. `os-build/layer1/r11/registry.md` records that gap.

## Round 11 record

`os-build/layer1/r11/registry.md` — limits, refusals, restart, contract, load, and this README's
truth pass.
