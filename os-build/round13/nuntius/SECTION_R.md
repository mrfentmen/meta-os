# Section R — Nuntius board hardening (R13-426..450)

Run: `node --test board/board.round13.test.mjs`. Machine record: `R_CASES.json`; rendered-output evidence in `dom/` (served HTML + the JSON the page renders).

Counts: {"total":25,"ok":21,"findings":4}

The viewer renders client-side, so every render case records the static HTML that was served plus the JSON a browser would draw — that is the DOM dump.

| task | case | outcome | evidence / finding |
|---|---|---|---|
| R13-426 | post path | 201 with index 0 |  |
| R13-427 | read path | since watermark returned the later line |  |
| R13-428 | board.html render of an empty board | viewer served, empty room has 0 lines | os-build/round13/nuntius/dom/empty-board.html |
| R13-429 | render of a long thread | 60 lines served in one response | os-build/round13/nuntius/dom/long-thread.html |
| R13-430 | render of unicode text | unicode round-trips through the JSON the viewer renders | os-build/round13/nuntius/dom/unicode.html |
| R13-431 | render of a malformed record | 1 good line loaded, torn record skipped | os-build/round13/nuntius/dom/malformed-record.html |
| R13-432 | ordering of posts | post order preserved |  |
| R13-433 | duplicate post | identical text stored twice | the board has no duplicate detection; the client must dedupe by index |
| R13-434 | oversized post | 400 at 2001 chars |  |
| R13-435 | empty post | 400 for empty text |  |
| R13-436 | pagination of a long post list | since=39 returned the last 20 lines | there is no page-size cap; a full read returns every line in one response |
| R13-437 | error envelope | every refusal carried {error: string} |  |
| R13-438 | state persistence across restart | 1 line survived a restart |  |
| R13-439 | concurrent posters | 8 concurrent posts got 8 distinct indices |  |
| R13-440 | stale record handling | an index past the end returns no lines, not an error |  |
| R13-441 | timestamp display | every line ends with a second-resolution ts stamp |  |
| R13-442 | author display | the nick precedes the first colon-space |  |
| R13-443 | escaping of HTML in post text | server never reflects post text; escaping is the viewer's job | os-build/round13/nuntius/dom/html-escaping.html; board.html uses innerHTML somewhere: the viewer must escape before it renders a line |
| R13-444 | link handling | URLs are stored as text; the server builds no anchors |  |
| R13-445 | config defaults | Meta OS Board listening on port 8790 (store: memory) |  |
| R13-446 | exit codes | bad port exits nonzero |  |
| R13-447 | log line shape | Meta OS Board listening on port 0 (store: memory) | the log prints the configured port (0), not the bound port |
| R13-448 | shutdown behaviour | close() stopped accepting connections |  |
| R13-449 | restart idempotence | two restarts on one store: 2 lines, not 4 |  |
| R13-450 | fixture set completeness | the room list agrees with every room read |  |
