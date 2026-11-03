# Meta Nervus eval — baseline run report

Command: `node eval/nervus/run.mjs --baseline`
Source: baseline label-only reader (fixture) — claims every record set
is "stub" and reads nothing: no counts, no hashes, no ramp, no receipt
rows, no dose windows, no curve points, no gap text, no registry lane.

Result: 2/10 scenarios passed, 8 failed.

| scenario | baseline result |
|---|---|
| NER-STUB-01 (every record stub:true) | PASS — label matches by chant |
| NER-STUB-02 (stub probe + STUB source) | PASS — label matches by chant |
| NER-OPS-01 (receipt, five ops, all ok) | fail — this scenario needs a read |
| NER-HASH-01 (one stub hash, 65 records) | fail — this scenario needs a read |
| NER-SWEEP-01 (sweep = stub ramp) | fail — this scenario needs a read |
| NER-STEER-01 (steer inert, never measured) | fail — this scenario needs a read |
| NER-DELTA-01 (delta zero, fixed hashes) | fail — this scenario needs a read |
| NER-CURVE-01 (four curve points, no interpolation) | fail — this scenario needs a read |
| NER-GAP-01 (face gap named, not filled) | fail — this scenario needs a read |
| NER-REG-01 (registry honest: STUB, no model) | fail — this scenario needs a read |

Comparison: the real-records run (`node eval/nervus/run.mjs`)
passes 10/10 against the same scenario set and the same harness.
These are fixture numbers, not model performance: the baseline's two
passes are the label rows, and beating 2/10 on those rows alone proves
nothing. A real run must replay all ten. No model is loaded, no model
is scored, and the face feed gap stays named, not filled.
