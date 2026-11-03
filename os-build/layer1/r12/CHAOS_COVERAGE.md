# Chaos coverage — hosted loops (R12-010)

Date: 2026-11-03. Drills are the Round-11 pack (`tests/chaos-pack.test.mjs`) plus the loop drills
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
| Officina faber loop | `officina-faber` (`design_loop.py`) | PASS | runtime-tested | runtime-tested | n/a (bounded loop) |
| Musica overnight | `musica-studio` (`os/worlds/musica/hosted.mjs`) | PASS | runtime-tested | runtime-tested | n/a (one session) |
| Science Lab duties | `research-archivist`, `research-director`, `scientific-critic`, `independent-verifier`, `scientific-analyst`, `literature-researcher`, `computational-scientist` | PASS | runtime-tested | runtime-tested | n/a (one duty) |

## Named NOT COVERED

- **Officina — NOT COVERED by the chaos pack.** Its loop is hosted and its STOP path is drilled
  with every other hosted entry, but the pack has no Officina-specific fault case.

Musica is no longer in this list: `musica-studio` is a hosted entry that runs the real overnight
pipeline, and the pre-spawn STOP drill covers it like every other hosted loop.

## What "PASS" means here

The loop is a real registry entry with a real command, and it refuses to spawn when its per-agent
STOP file exists (`agents/hosted.mjs`, drilled on every hosted entry). The in-run STOP and budget
paths are proven on the runtime with a deliberately long command, not by killing a loop that
finishes in 50 ms before the 100 ms poll can see the marker. That distinction is stated because
"STOP works" is easy to claim and the fast-loop case cannot prove it.
