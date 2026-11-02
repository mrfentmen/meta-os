# MODEL INTEGRATION — verification evidence (Bond, wave 2, 2026-11-02)

Scope: tasks 31-45. Repo HEAD `78862a5`. No model call was made: the key
file is absent. A claim is only VERIFIED if a command ran here.

## 31. The pipeline code

| Piece | Path | Status |
|---|---|---|
| Multi-model client | `server/queue/models.py` | CODE-INSPECTED |
| Judge v2 | `server/queue/judge.py` (`rule_with_model`) | CODE-INSPECTED |
| Crew wiring | `server/queue/crew.py` (`TRIO_JUDGE_MODEL`) | CODE-INSPECTED |
| Tests | `tests/queue-python/test_models.py`, `test_judge_model.py` | VERIFIED, 13 passed |

## 32. Model ids vs the served list

The registry at `server/queue/models.py:60-66` contains exactly:
`muse-spark-1.3`, `muse-wonder-1.0`, `sam-3.1`, `muse-image-1.0`,
`muse-voice-transcribe-1.0`.

A repo-wide grep over `.py/.mjs/.js/.rs/.html` found no other provider id
(no `gpt-`, `claude-`, `gemini-` in `server/` or `os/`). VERIFIED by grep.

## 33-34. Receipts

The writer exists: `models.py:83-101` appends one JSON line with `ts`,
`kind`, `model`, `surface`, `usage`, `latency_ms`, `est_cost_usd`.
Path: `METAOS_MODEL_RECEIPTS` or `server/queue/model_receipts.jsonl`.

**No receipt file is committed, and none exists beside the module.** The
only receipt names on disk are unrelated (`os-build/logs/*/receipt.txt`).
So the receipt-shape claims are CODE-INSPECTED, not VERIFIED. There is no
artifact to parse (task 33), and none to check for model id + timestamp
(task 34).

## 35. SAM 3.1

`parse_sam_text` (`models.py:188-215`) returns:
`box_px`, `image_size`, `region` (0-1000 scale), `mask`. It raises
`ValueError` when no `<|box;...|>` is present — it never invents a region.

The output is a segmentation record (box + encoded mask). No code or doc
claim was found that SAM performs language reasoning. VERIFIED by reading
the parser and its tests.

## 36. Muse Image

`generate_image` (`models.py:249-266`) returns decoded image bytes and a
format detected by magic bytes; it raises when no `image_generation_call`
result is present.

No caller in `server/` or `os/` invokes `generate_image`. The
"labelled GENERATED" statements in `os-build/MODEL_INTEGRATION.md:98,101`
describe a planned use; there is no generated image artifact in the repo.
Wiring: UNIMPLEMENTED.

## 37. Voice Transcribe

`transcribe` (`models.py:268-277`) always raises
`EndpointUnresolvedError`. There is no call, therefore no raw-audio
reference to check. UNIMPLEMENTED, stated honestly in the module.

## 38. Spend figures

`_receipt` sets `est_cost_usd` only for Muse Spark; every other model gets
`null` (`models.py:88-96`). The field name itself says estimate. VERIFIED
by reading the writer. No receipt file exists to inspect.

## 39-42. Smoke calls

`~/Desktop/hackathon key.txt` is ABSENT. No call was attempted. All four
tasks are BLOCKED-no-key. No result was invented.

## 43. Key absent

Handled above; work continued.

## 44. This file

Written from 31-43.

## 45. Models mentioned that the account does not serve

None found in executable code. Strings such as `muse-code`, `muse-binary`,
`muse-driver-`, `muse-bus` are names or prefixes, not model ids, and none
is passed to a model endpoint.

## Bottom line

- Client + registry + tests are real and green.
- Live-call evidence cited by `MODEL_INTEGRATION.md` (11 calls, judge
  smoke $0.0047) has **no receipt artifact in the repo**. It is a written
  claim, not a verifiable one here.
- SAM is segment-only; Image and Voice are not wired to any program yet.

## Evidence paths

- `os-build/bond-evidence/logs/queue-python-final.log` (277 passed)
- `tests/queue-python/test_models.py`, `test_judge_model.py` (13 passed, run in transcript)
