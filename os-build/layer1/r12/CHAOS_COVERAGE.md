# Chaos coverage — hosted loops (R12-010)

Date: 2026-11-02. Drills are the Round-11 pack (`tests/chaos-pack.test.mjs`) plus the loop drills
in `tests/agents-r11.test.mjs`; this file states which loops they actually cover.

| loop | registry entry | STOP (pre-spawn) | in-run STOP | budget receipt | baton |
|---|---|---|---|---|---|
| Aegis local passes | `aegis` | PASS | runtime-tested | runtime-tested | n/a (single pass) |
| Nervus STUB run | `nervus` | PASS | runtime-tested | runtime-tested | n/a (single pass) |
| Hands-Free intake | `handsfree-intake` | PASS | runtime-tested | runtime-tested | n/a (single pass) |
| Hands-Free brief | `handsfree-brief` | PASS | runtime-tested | runtime-tested | n/a (single pass) |
| Hands-Free approval | `handsfree-approval` | PASS | runtime-tested | runtime-tested | n/a (single pass) |
| Cadence watch | `watch` (`agents/watchman.mjs --once`) | PASS | runtime-tested | runtime-tested | n/a (one drain) |
| Imperium queue stack | `imperium-patrol` (`server/queue/hosted_imperium.py`) | PASS | n/a (one pass) | n/a (one pass) | n/a (one pass) |
| Aegis unattended cycle | `aegis-cycle` (`aegis/cycle.mjs`) | PASS | runtime-tested | runtime-tested | n/a (sweep → KEV → ledger) |

## Named NOT COVERED

- **Musica — NOT COVERED.** Draft entry, no in-tree command.
- **Officina — NOT COVERED.** Draft entry, no in-tree command.

## What "PASS" means here

The loop is a real registry entry with a real command, and it refuses to spawn when its per-agent
STOP file exists (`agents/hosted.mjs`, drilled on every hosted entry). The in-run STOP and budget
paths are proven on the runtime with a deliberately long command, not by killing a loop that
finishes in 50 ms before the 100 ms poll can see the marker. That distinction is stated because
"STOP works" is easy to claim and the fast-loop case cannot prove it.
