# Hands-Free — text orders in, a speakable brief out

State: **host on this machine, no kernel service.** These are Node modules with tests; nothing
here has run on Meta OS, and no agent is woken by them without the watchman.

## What is here

| module | job | tested by |
|---|---|---|
| `intake.mjs` | `agent: order` lines become `<id>.job.json`; unreadable lines stay in the inbox | `tests/handsfree.test.mjs`, `tests/handsfree-r11.test.mjs` |
| `brief.mjs` | finished results become one short brief, numbers first | same |
| `approval.mjs` | one request, one answer, appended to the run ledger; a second answer is logged as a duplicate and does not count | same |
| `speak.mjs` | over-cap briefs keep whole sentences; never a mid-sentence cut | `tests/handsfree-r11.test.mjs` |
| `refusals.mjs` | money, send and delete are refused by voice, by pattern | same |
| `latency.mjs` | order-to-brief time from `filedAt`/`finishedAt` on disk | same |
| `voice.mjs` | a down service is named as down, not "something went wrong" | same |
| `session.mjs` | a session record that recomposes its own brief on replay | same |
| `hosted.mjs` | the three hosted registry commands (`intake`, `brief`, `approval`) | `tests/agents-r11.test.mjs` |

## The commands the registry runs

```
node handsfree/hosted.mjs intake      # os-build/handsfree/inbox.txt -> jobs/
node handsfree/hosted.mjs brief       # jobs/*.result.json -> brief.txt
node handsfree/hosted.mjs approval    # one request, one yes, one duplicate
```

They write under `os-build/handsfree/`. The approval drill uses its own run directory and cannot
approve anything real.

## What this is not

- Not voice. There is no microphone, wake word, or synthesis; the modules produce the text a
  voice layer would say.
- Not a service. It has no boot entry, no kernel call, and no supervisor row.
- Not approval of anything by itself. `approval.mjs` records an answer; the caller must still
  check `mayAct()` before acting.
- Not a latency benchmark. The number is one host run's wall time, including agent start-up.
