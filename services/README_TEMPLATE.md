# `<service>` — Layer 4, service N

**Status: NOT BUILT | DESIGNED | WRITTEN | COMPILED.**
Use exactly one of those four words, and nothing invented. If it is WRITTEN but
not COMPILED, say that in this line.

## What it does

One paragraph, plain language, no marketing. What goes in, what comes out, who
calls it. If it can be said in one sentence, say one sentence.

## Contract

- **Entry:** `export "svc_entry" fn service_main(...) -> i32`, returning `0` on a
  clean stop (`os-build/layer1/SERVICE_CONTRACT.md` §2). Note any deviation here,
  including the `BootInfo` argument question (Q-B-L1-4).
- **Kernel surface:** the exact `extern fn` declarations this service uses, or
  "none" if it only talks to other services.
- **Needs from Layers 1–3:** which milestone (K2/K3/K5/K6) and which requirement
  IDs from `os-build/layer1/BOUNDARIES.md`.
- **Offers to Layers 5–6:** the calls or records another layer may rely on. If
  nothing may rely on it yet, say so.

## Dependencies

- **Libraries:** `common/*` modules imported, and what for.
- **Services:** names resolved through `registry` (never service IDs).
- **Data it owns:** state that survives a restart, where it lives, who may read
  it. "None" is a valid and common answer.

## Failure behaviour

- Which codes it returns (`common/err`) and in what conditions.
- What it does when a dependency is missing at start-up: refuses to start
  (non-zero exit) or degrades. Pick one and say which.
- What it writes to the log when it fails. A service that fails silently is a bug
  (B-L1-62 audits for it).

## Verification

Every symbol and form used in the source, with where it was checked. Table form,
because a reviewer has to be able to re-run each line:

| Symbol / form | Source |
|---|---|
| `extern fn` with a C symbol | `spec#40`, `reference#106` |
| _(add one row per construct — no construct ships without a row)_ | |

## Not verified

What could not be checked from this machine, stated plainly. With no Goose
toolchain, "compilation" is always on this list. Add the specific doubts: a
signature guessed from a name, a construct whose exact form was not in the docs,
a kernel behaviour assumed rather than proven.

## Deviations

Anything this service does differently from its task text or from
`SERVICE_CONTRACT.md`, and why. A deviation written down is a decision; a
deviation found later is a bug.

---

## Template rules

1. **One status word, from the four.** "Mostly done" is not a status.
2. **Every construct gets a verification row.** If a line of source cannot be
   traced to a `goose__` section or a bundled sample, either find the evidence or
   remove the construct.
3. **No mock described as working.** If a backend is absent, the README says the
   backend is absent (work order rule 1, `KERNEL_SPEC.md` rule 6).
4. **Sections are never deleted, only filled.** An empty "Failure behaviour" is
   information; a missing one is a gap nobody can see.
5. **Update the status line in the same commit that changes the status.** A README
   that lags its source is a README nobody can trust.
