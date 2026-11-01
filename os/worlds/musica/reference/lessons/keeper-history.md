# Keeper history (measured)

[source: session `take_log.jsonl` files on `hana/musica`
@ 941134f, aggregated 2026-11-01. Real numbers only. If a
number here disagrees with a take log, the take log wins.]

## Totals

- 124 takes logged, 108 keepers (87%).
- 16 rejects, all for repetition — see below.

## By session

| Session | Takes | Keepers |
|---|---|---|
| hn029-chipsynth | 12 | 11 |
| hn038-ambient | 4 | 4 |
| hn038-boom-bap | 4 | 4 |
| hn038-chipsynth | 4 | 4 |
| overnight-001 | 100 | 85 |

## By params (mode, waveform, tempo, key, bars)

| Params | Takes | Keepers |
|---|---|---|
| minor, square, 132, C, 4 | 116 | 100 (86%) |
| major, triangle, 72, F, 2 | 4 | 4 |
| minor, triangle, 90, A, 3 | 4 | 4 |

## Reject reasons (all 16)

- repetition 0.750 >= 0.75: 11 takes.
- repetition 1.000 >= 0.75: 5 takes.
- Zero rejects for duration, loudness, or silence.

## Spark assists

- The `spark_assist` field is empty on all 124 logged takes:
  these sessions ran without Spark assist mode. No lesson here
  credits Spark with any keeper. When assisted sessions exist,
  record their assist status per take before drawing any
  conclusion about assists.

## Honest caveats (read before quoting)

- The keeper bar is lenient on length, loudness, and silence:
  an 87% keeper rate says more about the bar than about taste.
  Do not present it as a quality score.
- The chipsynth sample dominates (116 of 124 takes). The
  ambient and boom-bap 4/4 results prove those briefs render
  and pass — they are not rates to quote.
- The binding constraint is repetition. A take at 1.000
  repetition is a melody that never varies; a take at 0.750
  sits exactly on the line. Both fail the same way.
- Overnight-001 is one 100-take run at one param set, not 100
  independent experiments. Treat it as one session's evidence.
