# Section M — agent runtime: STOP and budget drills (R13-301..325)

Run: `node os-build/layer1/loop_drills.mjs M`. Machine record: `LOOP_DRILLS.json`.

Counts: {"total":25,"OBSERVED-GAP":9,"OBSERVED":12,"GAP":4}

Measured cost before each row: aegis 40 ms, nervus 36 ms, handsfree 39 ms, imperium **does not terminate** (>15 s at first probe; the drill treats the 4 s ceiling as a floor and never as the run cost).

The runtime polls for STOP every 100 ms and every runnable loop finishes in under 40 ms, so the poll cannot win on these loops. Each STOP row therefore runs both arms — the pre-spawn gate in `agents/hosted.mjs` and the mid-run poll — and records which one halted.

| task | loop | mode | status | what happened |
|---|---|---|---|---|
| R13-301 | aegis | stop@start of the run | OBSERVED-GAP | halted by the pre-spawn gate (the only arm that can win at this run length); runtime poll missed a <36ms run |
| R13-302 | aegis | budget@17% of measured cost | OBSERVED | budget receipt written, kill recorded, no orphan |
| R13-303 | nervus | stop@start of the run | OBSERVED-GAP | halted by the pre-spawn gate (the only arm that can win at this run length); runtime poll missed a <32ms run |
| R13-304 | nervus | budget@31% of measured cost | OBSERVED | budget receipt written, kill recorded, no orphan |
| R13-305 | handsfree | stop@start of the run | OBSERVED-GAP | halted by the pre-spawn gate (the only arm that can win at this run length); runtime poll missed a <34ms run |
| R13-306 | handsfree | budget@45% of measured cost | OBSERVED | budget receipt written, kill recorded, no orphan |
| R13-307 | imperium | stop@start of the run | OBSERVED | halted by the runtime poll, reason recorded, no orphan |
| R13-308 | imperium | budget@59% of measured cost | OBSERVED | budget receipt written, kill recorded, no orphan |
| R13-309 | cadence | stop | GAP | no cadence entry in agents/registry.json and no cadence script in the repo |
| R13-310 | cadence | budget | GAP | no cadence entry in agents/registry.json and no cadence script in the repo |
| R13-311 | aegis | stop@during the OSV sweep call, before findings are written | OBSERVED-GAP | halted by the pre-spawn gate (the only arm that can win at this run length); runtime poll missed a <36ms run |
| R13-312 | aegis | budget@87% of measured cost | OBSERVED | budget receipt written, kill recorded, no orphan |
| R13-313 | nervus | stop@during the ledger append | OBSERVED-GAP | halted by the pre-spawn gate (the only arm that can win at this run length); runtime poll missed a <32ms run |
| R13-314 | nervus | budget@21% of measured cost | OBSERVED | budget receipt written, kill recorded, no orphan |
| R13-315 | handsfree | stop@during brief composition | OBSERVED-GAP | halted by the pre-spawn gate (the only arm that can win at this run length); runtime poll missed a <34ms run |
| R13-316 | handsfree | budget@35% of measured cost | OBSERVED | budget receipt written, kill recorded, no orphan |
| R13-317 | imperium | stop@during the review step, between patrol and judge | OBSERVED | halted by the runtime poll, reason recorded, no orphan |
| R13-318 | imperium | budget@49% of measured cost | OBSERVED | budget receipt written, kill recorded, no orphan |
| R13-319 | cadence | stop | GAP | no cadence entry in agents/registry.json and no cadence script in the repo |
| R13-320 | cadence | budget | GAP | no cadence entry in agents/registry.json and no cadence script in the repo |
| R13-321 | aegis | stop@during the findings-to-ledger write | OBSERVED-GAP | halted by the pre-spawn gate (the only arm that can win at this run length); runtime poll missed a <36ms run |
| R13-322 | aegis | budget@77% of measured cost | OBSERVED | budget receipt written, kill recorded, no orphan |
| R13-323 | nervus | stop@the final record write | OBSERVED-GAP | halted by the pre-spawn gate (the only arm that can win at this run length); runtime poll missed a <32ms run |
| R13-324 | nervus | budget@11% of measured cost | OBSERVED | budget receipt written, kill recorded, no orphan |
| R13-325 | handsfree | stop@the intake read, before any job is started | OBSERVED-GAP | halted by the pre-spawn gate (the only arm that can win at this run length); runtime poll missed a <34ms run |

