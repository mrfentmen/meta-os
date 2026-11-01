# Fresh-reader runbook log (NC-161..NC-170)

## Top-5 stumbles (NC-168)

1. `python3 -m unittest discover -s tests/queue-python` (README's own
   command) does NOT yield the claimed 110 — it collects 29 tests and
   4 modules error on `dynamic_credentials`. The 110 number needs
   pytest, which the README never mentions. A new reader follows the
   README and concludes the suite is red.
2. README test numbers disagree with the branch: badges + table say
   node 1933/1877/56; measured 1999/1943/56 (Custo/UI waves landed
   since). The 56-fail line still holds exactly.
3. `bash run-stack.sh` dies at the queue step on a plain Mac (same
   dynamic_credentials import); the README never says the queue needs
   the sandbox skill path. Relay comes up; Trio server never starts.
4. `timeout 120` in my own probe attempt: no `timeout` on macOS zsh —
   unrelated to the repo, noted so nobody copies it.
5. Combined `pytest tests/custos/ tests/officina/` collides (duplicate
   test_pack.py basenames); suites pass individually (48/48, 49/49).

## Word-for-word run (NC-161/162)

- Fresh clone https://github.com/mrfentmen/meta-os.git (tip 31518ba),
  `python3 -m http.server 8000`: / and /index.html both 200. Clone to
  first app screen: ~1 min (clone dominates).
- `bash run-stack.sh` (no key): "WARNING: SPARK_API_KEY is not set —
  generation is NOT CONFIGURED" (as documented), relay up, queue
  FAILED (ModuleNotFoundError, same root cause). Trio server never
  started by the script.

## Test commands (NC-163)

- `npm test`: works as written — 1999/1943/56 on the fresh clone.
- `python3 -m unittest discover -s tests/queue-python`: RUNS but does
  not match the book: 29 collected, 25 pass, 4 import errors. The 110
  needs `pytest tests/queue-python/` (verified 110/110 with the
  Section-B patch on throwaway; unpatched it does not collect).
- `cargo test --workspace`: works — 1412 pass, 0 fail on the fresh clone.

## Spark table (NC-164)

- Base URL https://api.meta.ai/v1 — present (server/model.mjs:49).
- Model muse-spark-1.3 — present (server/model.mjs:50).
- API key via SPARK_API_KEY — present; unset produces the labelled
  NOT CONFIGURED mode (observed). No key value printed anywhere.
- $75 guardrail — present (server/budget.mjs TEST_BUDGET_USD = 75.0).

## Sandbox assumptions (NC-165)

- The queue's `/opt/muse/skills/...` import (Section B diagnosis).
- Nothing else hit during the literal run path.

## Links (NC-166)

- README relative links: 2 found, 0 dead.

## Numbers check (NC-167)

- Badges/table (1933/1877/56) vs measured (1999/1943/56): run/pass
  counts moved on (new suites landed); the 56-fail line matches exactly.
