# Meta Hands-Free eval — first slice

Hands-Free was already hosted on main (agents/registry.json holds
handsfree-intake, handsfree-brief and handsfree-approval, each running
handsfree/hosted.mjs) but eval/ had no handsfree harness, so there was
no Hands-Free baseline for "whatever raises eval scores" to be measured
against. This is that first harness: a replay of the text path's own
rules through the real modules.

## What it scores: the text path's rules, not voice performance

There is no microphone, wake word or synthesis anywhere in this path,
and nothing here is evidence about spoken audio. The harness checks
that the committed modules do what their own docs and R11 tests say:

| source | what the harness checks |
|---|---|
| handsfree/hosted.mjs shipped inbox | both standing orders file, inbox empties |
| handsfree/intake.mjs + intake_cases invariants | malformed lines are refused with a reason, never silently dropped; refused lines stay in the inbox |
| handsfree/refusals.mjs catalogue | money, send, delete refused by voice; a plain question allowed |
| handsfree/brief.mjs | numbers first; a stopped run is "was stopped", never "success" |
| handsfree/speak.mjs | over-cap briefs keep whole sentences; a single over-cap sentence falls back to one whole sentence |
| handsfree/approval.mjs | one request, one answer; the second answer is a duplicate in the ledger, not a count |
| handsfree/latency.mjs | latency from filedAt/finishedAt on the record; a backwards clock is 0 ms plus a jump flag, never negative |
| handsfree/voice.mjs | a down service is named as down; an unknown state is "not answering", never "something went wrong" |
| handsfree/session.mjs | a session record recomposes its own brief; tampering is caught |
| agents/registry.json | the three Hands-Free entries are hosted with real commands |

## What it is not

- Not a voice eval. The modules produce the text a voice layer would
  say; no audio is recorded, played or scored here.
- Not a dispatch. No order is run, no money moved, nothing sent or
  deleted. The refusal catalogue is exercised as data, and the approval
  check answers a drill request in a tmp dir, never a real run.
- Not a live run. The harness never runs handsfree/hosted.mjs or
  handsfree/drill.mjs: the hosted entry writes under
  os-build/handsfree/ and the drill clears and rewrites that workspace,
  so running either would move the workspace being scored. Every
  file-writing check runs in its own fresh tmp dir, deleted afterwards;
  the tmp-only guard in adapter.test.mjs proves os-build/handsfree/ is
  byte-identical before and after a run.

## How to run

```
node eval/handsfree/run.mjs            # real modules, exits 1 on any fail
node eval/handsfree/run.mjs --baseline # empty-outcome fixture, always exits 0
node --test eval/handsfree/adapter.test.mjs
```

## Baseline: the empty-outcome reader

A fixture that predicts nothing happened for every scenario. It passes
exactly the two scenarios whose honest answer IS the empty outcome
(HF-INTAKE-EMPTY-01, HF-BRIEF-EMPTY-01) and fails every scenario that
requires a real module: 2/13. An empty outcome is not a verification.
The real run passes 13/13 by running the modules; see
baseline-run-report.md for the baseline table.

## Results (this slice, main af457ebd)

- Real run: 13/13 (exit 0).
- Baseline: 2/13 (the two empty rows by chant).
- Adapter tests: 5/5.
- Existing R11 Hands-Free + agents tests still pass (no handsfree/
  module was touched; this slice only adds eval/handsfree/ and one
  test-script token).
