# Section Q — Nuntius relay hardening (R13-401..425)

Run: `node --test relay/relay.round13.test.mjs`. Machine record: `Q_CASES.json`.

Counts: {"total":24,"ok":17,"findings":7}

Every case drives the real server on a loopback ephemeral port, or the real CLI in a child for the process-level cases. The crew bus is never a target.

| task | case | outcome | finding |
|---|---|---|---|
| R13-401 | append path | 201 with index 0 |  |
| R13-402 | poll path | since=0 returned the one later line |  |
| R13-403 | room routing | rooms isolated |  |
| R13-404 | message ordering | 5 posts kept their order |  |
| R13-405 | duplicate delivery | same id, two lines | the id is content-addressed but not a dedupe key: an identical notify is delivered twice |
| R13-406 | oversized message | 400 at 2001 chars |  |
| R13-407 | empty message | 400 for empty text |  |
| R13-408 | malformed frame | 400 with a JSON error |  |
| R13-409 | slow consumer | 50 buffered lines survived a late first read | the backlog is served in one response; nothing caps or trims it |
| R13-410 | fast producer burst | 200 accepted in 92 ms | no rate limit or backpressure: every post in the burst was accepted |
| R13-411 | viewer reconnect | watermark resumed with no gap and no repeat |  |
| R13-412 | backlog trim behaviour | no trim: 200 of 200 retained | rooms grow without bound; there is no trim, cap or eviction path in relay.mjs |
| R13-413 | nick parsing | nick 'a:b' is recorded, but a first-colon reader sees 'a' | the line format is not escaped: a colon in the nick makes the line ambiguous for any reader |
| R13-414 | colon in message body | colons in the body are preserved |  |
| R13-415 | unicode message body | unicode round-trips |  |
| R13-416 | long nick | 400 at 41 chars |  |
| R13-417 | missing nick | 400 with no nick |  |
| R13-418 | state dir watermark | server holds rooms in memory; the watermark is client-side | there is no state directory and no server-side watermark: a client that loses its index can only start over |
| R13-420 | concurrent pollers | 5 simultaneous polls agreed on total |  |
| R13-421 | error envelope | every refusal carried {error: string} |  |
| R13-422 | exit codes | bad port exits nonzero |  |
| R13-423 | log line shape | Meta Nuntius relay listening on port 0 (store: memory) | the log prints the configured port (0), not the bound port |
| R13-424 | config defaults | node:events:505 |  |
| R13-425 | shutdown behaviour | close() stopped accepting connections |  |
