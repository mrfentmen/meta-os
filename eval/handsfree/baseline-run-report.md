# Hands-Free eval — baseline run report (first slice)

Command: `node eval/handsfree/run.mjs --baseline` on main af457ebd.
Baseline: the empty-outcome reader (eval/handsfree/baseline.mjs) — a
fixture that predicts nothing happened for every scenario and reads
nothing. It always exits 0; this table is the fixture bar, not a
failure to investigate.

## Result: 2/13

| scenario | baseline | why |
|---|---|---|
| HF-INTAKE-01 Standing inbox files both orders | FAIL | needs the real intake |
| HF-INTAKE-02 Malformed lines are refused | FAIL | needs the real intake |
| HF-INTAKE-EMPTY-01 Empty inbox files nothing | PASS | the empty outcome, by chant |
| HF-REFUSAL-01 Money, send and delete refused | FAIL | needs the real catalogue |
| HF-BRIEF-01 Brief counts finished and failed | FAIL | needs the real brief |
| HF-BRIEF-STOPPED-01 Stopped is never success | FAIL | needs the real brief |
| HF-BRIEF-EMPTY-01 No results, one plain line | PASS | the empty outcome, by chant |
| HF-SPEAK-01 Whole sentences only | FAIL | needs the real speak module |
| HF-APPROVAL-01 One answer; second is duplicate | FAIL | needs the real approval |
| HF-LATENCY-01 Latency from the record | FAIL | needs the real latency |
| HF-VOICE-01 Down service named as down | FAIL | needs the real voice module |
| HF-SESSION-01 Session recomposes its brief | FAIL | needs the real session |
| HF-REGISTRY-01 Three entries hosted | FAIL | needs a real registry read |

Real run on the same set: 13/13 (exit 0). Chanting "nothing happened"
scores 2/13; running the modules scores 13/13.
