# Section P — Hands-Free intake cases (R13-376..400)

Run: `node --test handsfree/intake_cases.test.mjs`. Machine record: `P_CASES.json`.

Counts: {"total":25,"filed_ok":21,"refused":2,"fences_checked":3,"findings":14}

Every case runs the real `parseInbox`/`dropOrders`; the two loop cases ask the real `spawnHosted` gate. A finding is the measured behaviour — several of them are fences that were expected to exist and do not.

| task | case | filed | refused | finding |
|---|---|---|---|---|
| R13-376 | plain text order intake | 1 | 0 |  |
| R13-377 | multi-line intake | 3 | 0 |  |
| R13-378 | empty intake | 0 | 0 |  |
| R13-379 | whitespace-only intake | 0 | 0 |  |
| R13-380 | oversized intake (over the cap) | 1 | 0 | no size cap exists: the whole 200 KB order is filed as one job |
| R13-381 | intake with control characters | 1 | 0 |  |
| R13-382 | intake with unicode text | 1 | 0 |  |
| R13-383 | intake with a URL | 1 | 0 | the intake does not inspect URLs; the order is filed verbatim |
| R13-384 | intake with a file path | 1 | 0 | the intake does not inspect paths; an absolute path is prose in the order |
| R13-385 | intake naming a loop that is draft | 1 | 0 |  |
| R13-386 | intake naming a loop that is real | 1 | 0 |  |
| R13-387 | intake with an urgent flag | 1 | 0 | the job record has no priority field: 'URGENT' stays prose inside orders |
| R13-388 | intake with a budget note | 1 | 0 | a budget named in text is prose; the job record carries no budget field |
| R13-389 | intake with a STOP request | 1 | 0 | a spoken STOP is filed as a job; the intake never writes a STOP file |
| R13-390 | intake with a status question | 0 | 1 |  |
| R13-391 | intake with two jobs | 2 | 0 |  |
| R13-392 | intake repeating a finished job | 2 | 0 | the same order filed twice becomes two jobs with different ids; no duplicate check exists at the intake |
| R13-393 | intake contradicting a standing fence | 1 | 0 | the intake does not know the kernel fence; the order is filed with an agent that cannot legally do it |
| R13-394 | intake with a dispatch request | 1 | 0 | the refusal catalogue catches 'send', but intake.mjs never calls it: the order is still filed |
| R13-395 | intake in all caps | 1 | 0 | agent names are not case-normalised: 'AEGIS' will not match the 'aegis' registry entry |
| R13-396 | intake with punctuation only | 0 | 3 |  |
| R13-397 | intake with a pasted log | 2 | 0 | every colon-bearing line becomes an order: '12' and '12' are read as agent names |
| R13-398 | intake with a pasted error | 1 | 0 | a pasted stack or error line is filed as an order for an agent named 'Error' |
| R13-399 | intake with a date and time | 1 | 0 | the timestamp before the colon becomes the agent name; the real agent is buried in orders |
| R13-400 | intake with no verb | 1 | 0 | there is no verb check: an order with no action is filed like any other |
