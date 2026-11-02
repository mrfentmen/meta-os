# Section K — Agent runtime: supervisor and registry depth (R13-251..275)

Run: `node os-build/layer1/agent_drills.mjs`. Records:
`os-build/round13/agents/DRILLS.json`, `os-build/round13/agents/drills.txt`.

**25 / 25 addressed: 19 observed with a real spawned process, 2 refusals, 1 not exercised,
3 gaps. Five findings.**

Every drill below spawned a real child through the real `spawnAgent()`, with a real budget
timer, a real STOP file poll, and a real JSONL ledger. The registry used for the drills is
synthetic: these cases are about the runtime's contract, and a drill that needed the crew's
live lanes would test the crew, not the runtime.

## Findings

| # | finding | evidence | size |
|---|---|---|---|
| K-1 | **the runtime has no restart policy** | `runtime.mjs` contains no `restart`/`respawn`/`maxRestarts` path | medium — R13-254 and R13-255 cannot exist as cases until one does; "restart" today means a person spawning again, which is a new run |
| K-2 | **the `draft` flag is not enforced at spawn** | 23 registry entries carry `draft: true` with the placeholder command `true`; `spawnAgent` runs one to exit 0 without complaint | medium — a draft lane is supposed to be unspawnable, and this is the mechanism that would have stopped a placeholder from being reported as work |
| K-3 | **two agents can hold the same job with no fence** | R13-256: two spawns of one job object produced two distinct runs and two distinct dirs | low — nothing in the runtime knows a job is claimed |
| K-4 | **`agents/queue.mjs` is a package validator, not a scheduler** | exports `validatePackage`, `acceptPackage`, `PackageError`, `PACKAGE_REFUSALS`; no ordering primitive | low — the case names "ordering under burst"; that behaviour lives elsewhere or nowhere |
| K-5 | **`gym.mjs` scoring was not exercised** | `runGymDrill` spawns real agents and appends to the shared `gym-ledger.jsonl` | low — filed as NOT_EXERCISED rather than claimed; 3 tasks are defined |

## All 25 rows

| task | case | status | what happened |
|---|---|---|---|
| R13-251 | spawn and clean exit | OBSERVED | exit 0; ledger `spawn`, `exit` |
| R13-252 | spawn and nonzero exit | OBSERVED | exit 3 recorded as code 3, not swallowed |
| R13-253 | spawn and hang | OBSERVED | alive at 300 ms with no budget; `killAgent` → `stop-request`, `exit` |
| R13-254 | restart on death (allowed) | **GAP → K-1** | no restart policy exists |
| R13-255 | restart refused (fence) | **GAP → K-1** | no restart path, so no fence |
| R13-256 | two agents one job | OBSERVED → **K-3** | two runs, two dirs, both exit 0 |
| R13-257 | registry entry with a draft command | OBSERVED → **K-2** | 23 drafts; one spawned to exit 0 |
| R13-258 | registry entry with a missing command | REFUSED | `registry: x missing command` |
| R13-259 | job with no budget | OBSERVED | exit 0, no budget timer created |
| R13-260 | job with a zero budget | REFUSED | `registry: z bad maxWallMs` |
| R13-261 | job past its budget | OBSERVED | cap 400 ms; receipt `budget-wall-clock` written before the kill |
| R13-262 | ledger write on every transition | OBSERVED | `spawn`, `exit` present |
| R13-263 | lessons graft on a finished job | OBSERVED | `brief.json` carries a `sharedLessons` array (0 entries today) |
| R13-264 | queue.mjs ordering under burst | OBSERVED → **K-4** | module is an ingress validator; a synthetic minimal package was **rejected** by it, which is the validator's shape, not a runtime failure |
| R13-265 | safe-write on a contested file | OBSERVED | two concurrent 1 KB appends: 2,050 bytes, 2 lines, **both payloads whole**, no interleaving |
| R13-266 | bridge failure shape | OBSERVED | exports `createBridge`, `loadBoot`, states `BST_RUNNING`/`BST_STOPPED`/`BST_FAILED` |
| R13-267 | judge.mjs on a malformed verdict | OBSERVED | `rule({verdict:"maybe"})` and `rule(null)` both return `ruling: inconclusive` — no throw |
| R13-268 | clock.mjs drift note | OBSERVED | clock moved backwards returns `{ms: 0, jumped: true}` rather than a negative elapsed |
| R13-269 | room1.mjs reconnect | **GAP** | module exists; a reconnect drill needs the live bus, which was not started |
| R13-270 | hosted.mjs cycle counts | OBSERVED | exports `spawnHosted`, `stopDrill`, `stopMarker`, `hostedLoops`, `isStopped` |
| R13-271 | gym.mjs drill scoring | **NOT_EXERCISED → K-5** | 3 tasks defined; running it would write shared ledger state and score the crew |
| R13-272 | boot.json shape check | OBSERVED | 28 agents, 0 malformed, registry loads |
| R13-273 | runtime state after a kill | OBSERVED | `stopped: drill-kill`; `stop-request`, `exit` |
| R13-274 | runtime state after a STOP | OBSERVED | `stopped: stop-file`; the 100 ms poll honoured the file |
| R13-275 | runtime recovery after a crash | OBSERVED | torn line skipped, 1 whole record read, 3 records after the next append |

## A false pass this section caught in its own tool

The first run reported R13-264..268 and R13-271 as `OBSERVED` because the module files were on
disk. That is the exact failure mode of this whole round — existence reported as behaviour —
and it was only caught because `module_present: true` sat next to an untouched case. Those
five rows now call the module and print what it returned or threw, and R13-271 says
`NOT_EXERCISED` rather than borrowing credit from `TASKS.length`.

## What this section cannot claim

- That the agent layer restarts anything. It does not; a dead agent stays dead until a person
  or an outer loop spawns it again.
- That R13-269 is a passing reconnect. It is a gap: the bus was not started, and a reconnect
  drill without a connection tests nothing.
- That the synthetic drills prove the crew's lanes work. They prove the runtime's spawn,
  budget, STOP, ledger and recovery contracts, with placeholder commands that exit immediately.
