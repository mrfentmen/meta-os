# Round 11 — the 43 unblocked tasks, finished (2026-11-02)

Scope: the 43 tasks from `BUFFY_TASKS_ROUND11.md` that needed no OSV server, no external
network, no Pax ruling, no Hana contract and no program outside this repo. The 14 blocked tasks
are listed at the end and are **not** claimed here.

Verification for every row is a command run in this session; the test file named is the one that
fails if the behaviour regresses.

## Part 2 — Aegis (5)

| task | what was built | evidence | test |
|---|---|---|---|
| R11-233 unicode-confusable scan | `aegis/confusables.mjs`: Latin-lookalike table (Cyrillic/Greek/dashes/zero-width), position + code point; scans gateway prefixes and tray tools | `os-build/aegis/r11/hosted-receipt.json` (`confusables.scanned=31, findings=0`) | `tests/aegis-r11.test.mjs` |
| R11-235 Aegis hosted agent | `aegis/hosted.mjs`, registry entry `aegis` with `repo:node`, real ledger run | `os-build/aegis/runs.jsonl` (`hosted-local-start/done`), receipt above | `tests/agents-r11.test.mjs` |
| R11-236 findings lifecycle | `aegis/lifecycle.mjs`: append-only open → acknowledge → close; illegal steps refused and recorded | `os-build/aegis/r11/lifecycle-drill.jsonl` | `tests/aegis-r11.test.mjs` |
| R11-238 alarm split | `aegis/alarm.mjs`: low/info = quiet note, medium+ = full alarm | receipt (`alarm {small:"quiet", big:"alarm"}`) | `tests/aegis-r11.test.mjs` |
| R11-239 Aegis README true | `os-build/aegis/README.md` rewritten against the run records; blocked OSV, unscanned history and missing KEV stated | the README names each report path | — (document) |

## Part 3 — Hands-Free (9)

| task | what was built | evidence |
|---|---|---|
| R11-241 order intake | `validateOrder()` with four named refusals; CLI `handsfree/intake.mjs` | `tests/handsfree-r11.test.mjs` |
| R11-242 brief speaker | `handsfree/speak.mjs`: whole sentences only; fallback is itself a sentence | same |
| R11-243 duplicate approval | `approval.mjs`: second answer appended as `approval-duplicate`, state unchanged | `tests/handsfree.test.mjs` C3.2 |
| R11-244 hosted Hands-Free | registry `handsfree-intake/brief/approval`, command `handsfree/hosted.mjs <role>`, all exit 0 | `tests/agents-r11.test.mjs`; `os-build/handsfree/*` |
| R11-245 refusal catalogue | `handsfree/refusals.mjs`: money, send, delete; enforced by test | `tests/handsfree-r11.test.mjs` |
| R11-246 latency record | `handsfree/latency.mjs` + `handsfree/drill.mjs` host-path drill | `os-build/handsfree/drill-receipt.json`: 2 jobs, 2 measured, **median 50 ms** (min 49, max 50) |
| R11-247 failure voice | `handsfree/voice.mjs`: names the service and says orders are not running | `tests/handsfree-r11.test.mjs` |
| R11-248 session record | `handsfree/session.mjs`: `replay()` recomposes the brief; mismatch is a refusal | same |
| R11-249 Hands-Free README | `handsfree/README.md` written with "not voice, not a service" in the open | — (document) |

## Part 4 — hosted loops (8)

| task | what was built | evidence |
|---|---|---|
| R11-254 Aegis sweep hosted | hosted loop runs the local Aegis passes; the OSV sweep is explicitly not claimed | `tests/agents-r11.test.mjs`, `runs.jsonl` |
| R11-255 Nervus stub hosted | `nervus/hosted.mjs` drives all five STUB operations | `os-build/nervus/hosted-receipt.json` |
| R11-256 relay job/result | watchman `resultDir` support; result lands on the outbox with `finishedAt` | `tests/agents-r11.test.mjs` |
| R11-257 timer-sweep fallback | job that lands while the daemon is down runs once on restart | same |
| R11-258 baton across loops | continuation brief + one shared artifact, exactly two lines, one `baton-pass` | same |
| R11-259 budget kill | runtime writes `budget-receipt` and `receipt.json` before the stop | same |
| R11-260 STOP drill | `agents/hosted.mjs` checks a per-agent STOP before spawn; drilled on all 5 loops | same |
| R11-261 zero placeholders | registry: 5 hosted entries with real commands; 23 draft entries each carry `draftReason` | `agents/registry.json`, test above |

## Part 5 — Nervus (9)

| task | what was built | evidence |
|---|---|---|
| R11-262 model inspector | `nervus/inspect.mjs` reads config + weight file sizes, refuses a missing config | `tests/nervus-r11.test.mjs` |
| R11-263 layer-map record | `nervus/layermap.mjs`; shape-only unless per-layer sizes are supplied | same |
| R11-264 reduction planner | `nervus/planner.mjs`; every cut names the before/after proof it needs | same |
| R11-265 dose rules | executable contract test over inert/persona/collapse with a sourced window fixture | same |
| R11-266 probe rules | effect without a probe is refused; subspace scope handled | same + `tests/nervus-contracts.test.mjs` |
| R11-267 tray vs gateway | `validateTray` against the real `mcp-gateway/backends.json` | same |
| R11-268 sweep contract | `runAndFile("sweep")` → valid record, marked STUB | same |
| R11-269 steer/ablate | same for both operations | same |
| R11-270 evaluate-delta | `nervus/delta.mjs`: signed delta, both hashes required, absolute words refused | same |

## Part 6 — OS/kernel (3)

| task | what was built | evidence |
|---|---|---|
| R11-278 ABI worked examples | 8 examples (calls 0–5, reserved, bad number) in `os-build/USERSPACE_ABI.md`, labelled **not executed this round** | `tests/os-docs-r11.test.mjs` |
| R11-282 boot-log index | `os-build/layer1/BOOTLOG_INDEX.md` generated by `gen_bootlog_index.mjs`; all 37 committed logs, serial vs display, markers found, no verdict claimed | same |
| R11-283 gap-fill | one unreadable `package.json` used to abort the whole Aegis plan; it is now a named skip (`plan.unreadable`) and the rest of the plan builds | `tests/aegis-r11.test.mjs` |

## Part 7 — chaos pack (9)

All in `tests/chaos-pack.test.mjs`, one test named for its failure:

R11-285 missing picture · R11-286 contradictory readings · R11-287 network cut mid-sweep ·
R11-288 malformed job · R11-289 double claim · R11-290 corrupt lessons line ·
R11-291 clock jump · R11-292 disk full · R11-293 the suite itself (9/9 present, run green).

## Verification actually run

```
node --test <6 new files> <20 existing affected files>   -> 123 tests, 123 pass, 0 fail
node handsfree/drill.mjs                                 -> 2 jobs, 2 measured, median 50 ms
node aegis/hosted.mjs                                    -> exit 0, receipt written
node nervus/hosted.mjs                                   -> exit 0, 5 stub records
node os-build/layer1/gen_bootlog_index.mjs               -> 37 logs indexed
```

Every hosted command above is a **host-side Node program**. None of it runs on Meta OS, and no
kernel or boot claim is made by this round.

## The 14 still blocked (unchanged)

| task | blocker |
|---|---|
| R11-229, 234, 240 | no OSV server/credentials; 234 and 240 are downstream of 229 |
| R11-231 | external certificate-transparency/DNS access and the four domain names |
| R11-237 | no watch-target list authored, and "still ours / still live" needs network |
| R11-250–253 | Imperium, Musica, Officina, Cadence are not in this repo; registry entries are marked draft |
| R11-271 | needs Hana's face/surface contract |
| R11-272–274 | syscall-number ruling, no IPC in the kernel, boot proof belongs to OpenCode's lane |
| R11-284 | "each hosted loop" includes the four programs that are not here |
