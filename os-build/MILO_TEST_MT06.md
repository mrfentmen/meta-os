# MT-06 in full detail — Nuntius relay + board round trip (PREP ONLY)

Status: PREP ONLY as of 2026-11-02 22:53 EST. This is a fixture/spec, not a
run. No MT-06 message has been posted, no round trip has been read back
under MT-06, and nothing below is a pass. Firing waits on BOTH: (1) Del
tops up Meta API billing (HTTP 402 during Pax's live hunt #3), and (2)
Del picks a key route (Route A: key placed on Milo's VM; Route B: Milo
specs, Pax executes the live run and posts the receipt, Milo verdicts
it). Pax directed 2026-11-02 22:50 EST that MT-06 comes next as PREP
ONLY, $0, no live-key call; that the MT-05 short-clock mapping to
per-take pipeline stages stands for the prep record and no literal
daemon build is in the MT chain; and that the chain closes at MT-08
gate duty, with no extra test-layer tasks invented. Spend cap $10
total for the whole directive, guardrail-tracked; cost for MT-06 is
TBD at fire time from the published Spark rates, never invented here.
Nothing dials a real service from this prep, ever.

## What the check is

One message posted through the relay, read back from the board with
matching content, per os-build/MILO_TEST_SLICE.md and
os-build/MILO_TEST_PREP.md. Proof is both sides of the round trip in
one record; a mismatch is a FAIL. On origin/main the concrete pieces
are two separate local services that speak the same line protocol but
share no bridge code (see "The bridge gap" below, read before firing):

- Meta Nuntius, the relay: `relay/relay.mjs`, run with
  `node relay/relay.mjs` (default port 8787, `RELAY_PORT` to change
  it; `RELAY_STORE_FILE` for a JSONL store of `{"room": ..., "line":
  ...}` records, reloaded on boot; unset means in-memory only).
  Zero external dependencies, Node stdlib only. Viewer at `GET /`
  (`relay/viewer.html`): room switcher (`main` and `1` quick
  buttons), 2-second watermark polling, Notifications strip surfacing
  NOTIFY lines newest-first.
- The Board, the in-OS messaging board: `board/board.mjs`, run with
  `node board/board.mjs` (default port 8790, `BOARD_PORT` to change
  it; `BOARD_STORE_FILE` for the same JSONL persistence). Zero
  dependencies. Viewer at `GET /` (`board/board.html`): room switcher,
  live message list, post box, NOTIFY lines rendered distinctly by
  severity. The face Board window (face/face.js, W7) embeds this
  viewer. The board README states `board.test.mjs` passes 9/9 against
  the real service; that is the README's claim on main, not a fresh
  MT-06 measurement.

Both services share this wire surface (relay/README.md and
board/README.md agree on every line below):

- Message line: `<nick>: <text> [ts:<epoch-seconds>]`, stamped at
  send time.
- NOTIFY line: `relay: NOTIFY:<id> <severity> [<topic>] <text>
  [ts:<epoch-seconds>]` on the relay, `board: NOTIFY:<id> ...` on the
  board. `id` = `ntf-` + the first 16 hex chars of the SHA-256 of
  `room + "\n" + topic + "\n" + severity + "\n" + text`, so the same
  payload in the same room always yields the same id. Severity is one
  of `info`, `warning`, `critical`.
- `POST /rooms/<room>/messages` with `{nick, text}` returns
  `201 {index}` — the line's 0-based position in its room.
- `POST /rooms/<room>/notify` with `{severity, topic, text}`
  returns `201 {index, id}`.
- `GET /rooms/<room>/messages?since=<n>` returns `{room, total,
  messages}` — the lines after index `n`; `since=-1` (or omitted)
  returns the whole room. The board additionally offers
  `GET /rooms` (`{rooms: [{room, count}]}`).
- `GET /health` returns `{ok: true, rooms: <count>, store:
  "memory" | "file"}`.
- Validation caps, refusals are `400` JSON errors: room name
  `[a-z0-9-]{1,32}`; nick single line, 1-40 chars, no control
  characters; text single line, 1-2000 chars; topic single line,
  1-64 chars; request body at most 16384 bytes of JSON.
- The relay's own test suite, `node --test relay/relay.test.mjs`,
  is offline (ephemeral localhost ports, temp-dir file-store test)
  and pins the append-then-poll shape: first post index 0, second
  index 1, `since=-1` returns both lines verbatim, `since=0`
  returns only the second, `since=1` returns none. The relay README
  notes this suite is not yet wired into the repo's `npm test`
  enumeration (a one-line `package.json` addition, left to the
  integrator); MT-06 does not claim `npm test` covers the relay.

## The bridge gap — read this before firing

The slice words say a message "posted through the relay is read back
from the board". In this tree there is no code that forwards a line
from the Nuntius relay (port 8787) to the Board (port 8790) or back:
`run-stack.sh` starts the relay only (plus the queue agent pointing
`TRIO_RELAY_URL` at it); no file bridges the two services, and their
stores are separate (each service's `RELAY_STORE_FILE` /
`BOARD_STORE_FILE` is its own JSONL file). So this prep defines the
check as the honest, testable version of the slice words, and names
the literal cross-service reading as a question to Pax:

- Leg A (relay round trip): post a probe message to the relay, read
  it back from the relay with matching content.
- Leg B (board round trip): post the same probe message to the
  board, read it back from the board with matching content.
- Leg C (relay NOTIFY round trip): post a NOTIFY to the relay, read
  it back with the same id, severity, topic, and text.
- The literal cross-service hop (post to the relay, read from the
  board with no second post) is NOT part of this check, because no
  bridge exists on main to carry it. If Pax wants that hop, it is a
  bridge build task outside this MT chain, and MT-06 stays with Legs
  A-C until Pax says otherwise.

Question for Pax (not a blocker on this prep): confirm Legs A-C as
the MT-06 check, or direct the bridge build first. This prep keeps
Legs A-C, so nothing is lost either way.

Second question for Pax: MT-06 runs local Node services with no
model call, so at fire time confirm whether the key-route hold
applies to it at all. Until Pax says so, this prep follows the same
hold as MT-03 and fires nothing — the hold is the safe default, and
a local-only exemption is Pax's call, not assumed here.

## The probe message

At fire time the runner posts one probe per leg, each carrying a
marker so the read-back can be matched exactly and a stale line can
never be mistaken for it:

- Room: a dedicated room, for example `mt06` (valid under
  `[a-z0-9-]{1,32}`), so the probe never pollutes `main` or `1` and
  never collides with crew traffic. The exact room is stated in the
  record.
- Nick: `milo-mt06` (valid: single line, under 40 chars).
- Text: single line, under 2000 chars, containing `MT-06` plus the
  fire-time UTC timestamp plus a short random token (for example
  `MT-06 probe 2026-11-0X ... <token>`). The exact text is recorded
  verbatim in the record, so the match is checked against the posted
  text, not against a template.
- NOTIFY leg: severity `info`, topic `mt06-probe`, text carrying the
  same `MT-06` marker plus timestamp plus token.

Nothing in the probe may name a real person, a real incident, or a
real dispatch: it is a synthetic marker, and the record says so.

## Pass rules

MT-06 passes cleanly only when all of these hold on the fired record:

1. Both services answer `GET /health` with `ok: true` before the
   posts, with the store mode (`memory` or `file`) stated in the
   record. A service that never answered health is not a pass.
2. Leg A: the relay `POST` returns `201` with an `index`, and the
   relay `GET .../messages?since=<index-1>` (or `since=-1`) returns
   a line matching `^milo-mt06: <posted text> \[ts:\d+\]$` exactly
   in nick and text, with the `ts` stamp inside the firing window.
   A line with different text, a different nick, or no line at all
   is a FAIL, reported as failed, never relabelled.
3. Leg B: the same, against the board, with the same posted text.
   A board that returns the relay's line without a board post would
   be a surprise, not a pass: the record must show the board post
   and its own index, because no bridge exists to explain a shared
   line.
4. Leg C: the relay `POST /notify` returns `201` with an `id`, and
   the read-back line carries that same id, the same severity, the
   same topic, and the same text; the id also recomputes to
   `ntf-` + the first 16 hex chars of sha256 over
   `room + "\n" + topic + "\n" + severity + "\n" + text`. An id
   that does not recompute is a FAIL.
5. A validation refusal is a FAIL of that leg, not a pass: a `400`
   on a probe that respects every cap above means the service
   misbehaves, and the record names the refused field and the
   error body verbatim.
6. The record names the main tip the run was fired from, the ports
   actually used, and the store mode of each service, so the run can
   be replayed. A record missing its ports or its main tip is
   incomplete.
7. Spend for the record is stated in actual dollars, and the running
   total against the $10 cap is updated in MILO_TEST_STATUS.md at
   fire time. A record with no spend line is incomplete. (The local
   services make no model calls, so the expected spend is $0; that
   expectation is confirmed at fire time, not claimed as a result
   here.)
8. A failure anywhere in the run is recorded as a failure with its
   cause named, never answered with fabricated data, never
   relabelled as a success, never dropped from the record.
9. No crew-bus message is part of this check. Meta Nuntius and the
   Board are repo services; the external crew bus (muse-relay) is a
   separate service that neither replaces nor shares code with
   them. Milo's room 1 completion post is a report about MT-06, not
   a leg of MT-06, and no MT-06 probe is ever posted to the crew
   bus.

A round trip in which the read-back text differs by even one
character is a mismatch, and a mismatch is a FAIL — never a pass
with a note.

## Run record shape — one record, both sides inside it

One record, landed on main by Pax (Route B) or by Milo (Route A),
for example os-build/MILO_TEST_MT06_RECORD.md (exact filename set
at fire time; what matters is that it exists and is findable from
MILO_TEST_STATUS.md). Each record contains:

- `check`: `"MT-06"`.
- `main_tip`: the origin/main commit the run was fired from.
- `route`: `"A"` or `"B"`, plus who executed the live steps and who
  issued the verdict (Route B: Pax executed, Milo verdicts from the
  receipt; Route A: Milo executed and verdicts).
- `spend_usd`: actual spend for this record; running total against
  the $10 cap is updated in MILO_TEST_STATUS.md at fire time.
- `services`: relay port + store mode, board port + store mode,
  each service's `/health` response verbatim.
- `probe`: room, nick, posted text verbatim, NOTIFY severity /
  topic / text verbatim, and the returned indexes and NOTIFY id.
- `leg_a`: relay post response + read-back line verbatim + match
  verdict.
- `leg_b`: board post response + read-back line verbatim + match
  verdict.
- `leg_c`: relay NOTIFY post response + read-back line verbatim +
  recomputed id + match verdict.
- `bridge`: a statement that no cross-service hop was run or
  claimed, citing the bridge gap above, unless Pax directed a bridge
  build first (in which case the bridge commit is named).
- `outcome`: `"pass"` | `"fail"` | `"partial"` — clean pass only
  when every rule above holds; a run that stopped early (for
  example at a budget stop) is `partial` with the record saying
  where it stopped and what never ran.
- `failures`: every failure named, none hidden.

## Firing steps, by route (same steps, different hands)

Route B (the route that works once credits exist, no key movement):
Pax starts both local services on stated ports, runs Legs A-C with
the probe above, posts the record, and Milo verdicts it against the
pass rules above, in his own words, on room 1 and in
MILO_TEST_STATUS.md.

Route A (only after Del places the key on Milo's VM): Milo runs the
same steps himself, inside the cap, posts the record, and verdicts
it the same way. (Note: the local services make no model calls, so
at fire time Pax may confirm MT-06 needs no key at all and is exempt
from the key-route hold; until Pax says so, this prep follows the
same hold as MT-03 and fires nothing.)

Either route: if the 402 is still present at fire time, the run does
not start; MT-06 stays BLOCKED and the attempt (not a result) is
noted in MILO_TEST_STATUS.md. If the cap is hit mid-run, the run
stops, the record is marked partial, and the tally is posted to
room 1. No excluded bus file is touched (bus-tools/* and
tests/test_bus_admin_e2e.py stay out of every step), and no frozen
file is edited: syscalls.rs stays frozen, kernel/src stays Rowan's
pen.

## What this prep does NOT claim

- No MT-06 run has happened. No probe message has been posted under
  MT-06, no read-back has been observed under MT-06, and no NOTIFY
  id has been issued under MT-06.
- No relay-to-board bridge exists on main, and none is claimed
  here: Legs A-C are same-service round trips, and the cross-service
  hop is a flagged question to Pax, not a verdict.
- The board README's 9/9 claim and the relay test suite's pinned
  append-then-poll shape are main's existing coverage, not fresh
  MT-06 measurements. Fresh measurements happen at fire time and may
  differ; the fresh results are what the record carries.
- Nothing here is a pass, and the bridge question and the
  key-hold-applicability question above are questions to Pax, not
  verdicts: if Pax rules differently, this file is corrected to
  match whatever Pax directs.
