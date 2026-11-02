# Hands-Free — the three service shapes (Round 8, C)

Greenlit 2026-11-02. Voice comes later; these are the shapes, text-first, each doing one job and
each leaving a record.

## C1 — order intake (`handsfree/intake.mjs`)

A text inbox, one order per line, the agent's name before a colon:

    # tonight
    worker: sweep the board
    runner: check the gate

`dropOrders` writes one `<id>.job.json` per order into the watchman's jobs directory, atomically
(tmp + rename), and appends the taken lines to `inbox.done`. A line it cannot read stays IN the
inbox and is reported with its line number. Silently deleting a typo would turn a mistake into a
lost order; guessing at it would run the wrong one.

## C2 — brief speaker (`handsfree/brief.mjs`)

Results become one speakable block: numbers first, short sentences, no jargon, one plain outcome
per run.

    3 orders ran.
    1 finished, 1 stopped, 1 failed.
    worker finished.
    runner was stopped.
    crashy failed (code 3).

"Stopped" is never folded into "finished": a run a budget or a STOP ended is its own outcome, and
a brief that calls it success is the first lie the program tells. A torn result file is skipped,
not invented.

## C3 — approval inbox (`handsfree/approval.mjs`)

Where the announce-before-send rule applies, the boss's word is required and goes into the RUN'S
OWN LEDGER, not a side flag:

- `requestApproval(runDir, {run, what, why})` records the question; nothing acts.
- `dropApproval(runDir, "yes" | "no", {by})` appends `{event:"approval", decision, by, at, what}`
  to `runDir/ledger.jsonl` and writes `approval.json` for the next reader.
- `mayAct(runDir)` is the only gate. One request, one answer; a second answer is refused and
  writes nothing.

## What is NOT built

Voice. Wake-by-voice, speech output and a microphone path are not in this tree; the shapes above
are the layer voice would call, and saying they are voice-ready is a claim nobody has tested.
