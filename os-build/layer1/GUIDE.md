# Writing a Layer 4 service (B-L1-135)

This is the guide for the next person who adds a service. Every rule below is traced to a file in
this tree that already does it, because a house style that exists only in a document dies at the
first deadline. If a rule has no file behind it, it is not in here.

Read `services/example/example.goose` first. It is the template, it does one small thing
completely, and its header lists the nine steps in order. This guide is the rest: the tables you
have to touch, the gates that will run on you, and the failures that are not obvious.

## 1. The shape of a service

```
services/<name>/
    <name>.goose      the service: state, contract functions, entry point
    <extra>.goose     optional second module (see §9 for the import rule)
    README.md         status word, contract, fixed sizes, what it refuses
    DESIGN.md         only when the layout is not obvious (see fs/DESIGN.md)
```

One directory is one service. Supporting libraries go in `services/common/<lib>/`, never into a
service another service imports — that is how the address model ended up compiled into four
services (`LINK_MAP.md`, round 1's warning).

## 2. Three tables you must join, or the service does not exist

| Table | File | What it means if you skip it |
|---|---|---|
| The worklist | `services/MANIFEST.md` | the service is not part of the layer; nothing audits it |
| The boot order | `services/supervisor/bootorder.goose` | it never starts, or starts before its dependencies |
| The permission table | `services/callmatrix/callmatrix.goose` | every call it makes fails at `cm_allows` and reads as "service did not start" |

The last one is the one people forget. `callmatrix_audit.py` exists because twelve edges in this
tree were missing from it (`CALLMATRIX_DRIFT.md`). Adding a service means appending an id —
appending, never renumbering, because the ids are also what services report to the supervisor.

## 3. No allocation, ever

Goose services allocate nothing at run time. That is not a preference; it is what makes a service
a fixed-size object the kernel can start (`BOUNDARIES.md` A10).

- Buffers are `u8[..N]` fields or caller-supplied slices `u8[>..]&` with an explicit `cap`.
- Functions that fill a buffer return `bool`: `false` means "it did not fit", never "it fit
  partly". `common/fmt/fmt.goose` states the rule and refuses to truncate.
- Size the buffer to the contract and write down the contract. `display`'s history is 32 KiB
  because `SCROLL_MAX` 256 × `LINE_MAX` 128, not because 32 KiB felt right.
- Run `size_audit.py` before you pick a number. A declaration is not a footprint: `VCon[..4]`
  costs four times its struct, and a struct name that collides with another service's is sized
  wrong without a word of warning.

## 4. Return codes, not booleans, when the reason matters

`common/err/err.goose` is the only vocabulary. Bands: `1xxx` general, `2xxx` storage, `3xxx`
network, `4xxx` agent, `5xxx` updater, `6xxx` session.

- Never `let E_SOMETHING: i64 = ...` inside a service. It compiles and it creates a second
  vocabulary no audit can see; `error_audit.py` fails the build on an undeclared code, and strips
  comments first so a code named in prose is not mistaken for a use.
- The trailing-bool convention (`fn f(...) -> T, bool`) is for "parsed / did not parse" where the
  value is meaningless on failure. When the caller has to distinguish *why*, return a code.
- A bare number where a code belongs cannot be audited. `return 42` is always a mistake.

## 5. Handles, not ids

A service that addresses another by id is one renumber away from a permission bug. The pattern,
in three places already:

```
handle = slot | (generation << k)      sup_handle / ah_handle / socket handle
```

The generation is what makes an old handle resolve to nothing instead of to the next occupant
(`services/agenthost/agenthost.goose:93`, `services/supervisor/supervisor.goose:138`). Reap frees
the slot and keeps the generation.

## 6. State machines have a legal-edge table

If your service has states, the transitions are data and one function enforces them:
`ah_transition_legal` (`agenthost:200`), `transition_legal` (`supervisor:248`),
`dev_state_legal` (`devices:191`). The reason is that an illegal transition is a bug you can
*test* (`t52_supervisor.goose`, `t59_agenthost.goose`), while a bug spread over twenty `if`s is a
bug you debug. `socket` is the counter-example worth reading: it checks its states at each use
site (`S_OPEN`/`S_CLOSED`) instead of tabulating them, which is correct only because it has two.

## 7. Count what you drop

Every refusal path increments a counter that someone can read: `logd.dropped_full`,
`logd.dropped_level`, `logd.dropped_long`, `audit.aud_dropped`, `watchdog` miss counts,
`pool.refused`. A queue that silently discards is a service whose log is a lie about what
happened. This is the same rule as Hana's `shell-formats.md` ("an unmeasured fact is omitted, a
lost one is counted") applied to the inside of a service.

## 8. Tests: one program per mechanism, not per function

`services/tests/tNN_<subject>.goose`, plus a harness when the subject needs a peer
(`tests/harness/link.goose`, `tests/peers/dhcp_peer.goose`). House rules, visible in every file:

- Header comment says what is under test *and the ways it can be wrong*. `t61_bootorder.goose`
  lists the four failure modes; a test whose header cannot name a failure mode is a test of
  nothing.
- `say(...)` for the human line, `check(cond)` for the assertion, a pass/fail count at the end.
- No ternaries (this dialect has none) and no array `pop`/`clear`.
- Hostile inputs for every parser are checked-in data plus a script that states the expected
  honest failure per input (`services/tests/hostile/hostile_check.py`).

## 9. The import rule, and the one question it raises

A sibling file in the same service imports its own module: `import socket.socket;` in
`bind.goose`. That is the pattern in eleven files and it is correct **if** a directory is one
package. If Goose instead pulls the module in twice, every symbol is defined twice at link. Filed
as Q-B-L1-21 in `K6_NEEDS.md`; until it is answered, do what the tree does and know why.

`common.*` imports are libraries: compiled in, no permission check. A service importing a service
is a runtime edge and needs a `callmatrix` row.

## 10. The gates that will run on you

All of these are mechanical and all of them take a path; none of them needs the compiler.

| Gate | Command | Fails on |
|---|---|---|
| Source audit | `python3 os-build/layer1/source_audit.py` | unbalanced braces, called-but-undefined functions, undeclared codes, double `let`, unknown keywords |
| Error registry | `python3 os-build/layer1/error_audit.py --unused` | a code used but not declared, a local code definition |
| Call matrix | `python3 os-build/layer1/callmatrix_audit.py` | an import the matrix denies, a service with no id |
| Boot order | `python3 os-build/layer1/bootorder_check.py` | a forward dependency, duplicate order, name/directory mismatch, a service in no table |
| Link map | `python3 os-build/layer1/linkmap.py` | nothing — it reports drift, and the drift is the point |
| Size audit | `python3 os-build/layer1/size_audit.py` | nothing — it reports resident bytes for review |
| Parser hardening | `python3 services/tests/hostile/hostile_check.py` | a hostile input that is accepted |

A clean run of all seven is **not** evidence the code works. It is evidence the code is
internally consistent, which is the strongest claim available without a toolchain. Say exactly
that in your report.

## 11. Docs you owe

- `README.md` from `services/README_TEMPLATE.md`: status word from the fixed four, contract,
  fixed sizes with the reason for each, and **what the service refuses** — the refusal list is
  the part reviewers actually use.
- A row in `MANIFEST.md` with the true status word. WRITTEN means source exists and every symbol
  was checked; COMPILED requires a build log, and there is none on this machine.
- An entry in `K6_NEEDS.md` if you need something from Layers 1–3, phrased as a question with the
  answer shape that would close it. "Vibes" questions are not accepted there.

## 12. When you are blocked

Write the question, name the file and function it blocks, and state the answer shape you need.
That is what `K6_NEEDS.md` and `kernel/MAC_QUESTIONS.md` are for. Do not design around a guess
and do not leave the guess implicit in the code — this layer has one already
(`supervisor` assumes `yield` reschedules) and it is written down as a requirement, not a fact.
