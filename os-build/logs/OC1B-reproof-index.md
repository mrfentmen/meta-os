# OC1B-199 — §8 re-proof index (one row per wave incl. wave 0)

| wave | tip sha | kernel-touching merges | gate result | serial path | verdict |
|---|---|---|---|---|---|
| 0 (WAVE3 baseline) | c7aeb162 | n/a (reference) | GREEN 7/7 (os-build/logs/WAVE3-combined-gate.log) | os-build/logs/WAVE3-combined-serial.txt | PROVEN (os-build/logs/WAVE3_KERNEL_PROOF.md) |
| combined (opencode/500 tip 94010c76 = main 3452d244 merged) | 94010c76 | NONE (empty `git log c7aeb162..HEAD -- kernel/`) | GREEN 8/8, exit 0 (os-build/logs/OC1B-reproof-combined-gate.log) | os-build/logs/OC1B-reproof-combined-serial.txt | NO REGRESSION (os-build/logs/OC1B-reproof-combined.md) |
| 1 | 3452d244 / 94010c76 checked | NONE | n/a (NO WAVE) | n/a | NO WAVE — no kernel-touching merge wave 1 landed before closeout; the prior proof stands |
| 2 | same | NONE | n/a (NO WAVE) | n/a | NO WAVE — no kernel-touching merge wave 2 landed before closeout; the prior proof stands |
| 3 | same | NONE | n/a (NO WAVE) | n/a | NO WAVE — no kernel-touching merge wave 3 landed before closeout; the prior proof stands |
| 4 | same | NONE | n/a (NO WAVE) | n/a | NO WAVE — no kernel-touching merge wave 4 landed before closeout; the prior proof stands |
| 5 | same | NONE | n/a (NO WAVE) | n/a | NO WAVE — no kernel-touching merge wave 5 landed before closeout; the prior proof stands |

## Proof files (all committed on opencode/500-s8)

- os-build/logs/OC1B-reproof-waves-tree.txt — master NO WAVE record
  (OC1B-177/181/185/189/193 tree check + OC1B-197 NO WAVE lines)
- os-build/logs/OC1B-reproof-w1-tree.txt … w5-tree.txt — byte-identical
  slot copies (md5 bbefa18b89e2f26a1da146158dd20fa4)
- os-build/logs/OC1B-reproof-combined-gate.log — gate.sh full output on
  the combined tip: GATE GREEN, 8/8, exit 0, 329 lines
- os-build/logs/OC1B-reproof-combined-serial.txt — VNC boot serial
  (1086 lines; image sha256
  cf1d49ddd3d77948ed99c912551021cd777adf7406ae32ca20c08801105fdca2)
- os-build/captures/oc1b-reproof-combined-shell.png — text-mode screen
  at shell (720x400)
- os-build/captures/oc1b-reproof-combined-fetch.png — fetch ribbon +
  Mrfentmen@metaos + OS/Kernel/Uptime/Tasks/Mem/Programs rows (720x400)
- os-build/logs/OC1B-reproof-combined.md — assertion-by-assertion
  re-proof + line-class diff vs WAVE3-combined-serial.txt, verdict
  NO REGRESSION
- os-build/logs/OC1B-queue-combined.txt — affected suite:
  `python3 -m unittest discover -s tests/queue-python`: 296 tests, OK
  (289 pre-wiring baseline + 7 new wiring tests)
- os-build/logs/OC1B-crew-model-wiring.txt — the new crew model-wiring
  test alone: 7 tests, OK (offline, stubbed; no live call, no key used)
- os-build/logs/OC1B-s8-STATUS-SNIPPET.md — OC1B-176 trigger block +
  task-by-task verdicts for the coordinator merge into
  os-build/OPENCODE1_500_STATUS.md
