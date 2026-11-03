# OC1B §9 section proof — model pipeline live proofs (tree 94010c76, Mac, 2026-11-02)

Queue baseline OC1B-201: 296 ran OK. After-live OC1B-222: 296 ran OK. No drift.

| Task | Call | Model | Receipt / artifact |
|---|---|---|---|
| 203 wonder chat_text | "Reply with exactly the word WONDEROK" -> 'WONDEROK', model-reported muse-wonder-1.0, 2655ms | muse-wonder-1.0 | os-build/logs/oc1b-model-proofs/wonder-chat.txt |
| 204 | receipt line quoted in wonder-chat.txt | — | server/queue/model_receipts.jsonl (untracked runtime state) |
| 205 SAM segment | test-footage/frames/ignis-fire-1.jpg, prompt "the burning building engulfed in flames" -> box_px 10,0-599,353 on 600x470, mask 71,049 chars | sam-3.1 | os-build/logs/oc1b-model-proofs/sam-direct.json |
| 206 SAM vs Spark | SAM region x17 y0 w982 h751 vs Spark structure-fire x200 y545 w435 h210 / flame x140 y525 w500 h170 / smoke x15 y0 w975 h600 | both | os-build/logs/oc1b-model-proofs/sam-vs-spark.md |
| 207 generate_image | "a small blue ribbon logo on black" -> 112,320 bytes, RIFF....WEBP magic | muse-image-1.0 | os-build/logs/oc1b-model-proofs/oc1b-gen.webp |
| 207 receipt | kind=image:muse-image-1.0 latency=16225 est_cost_usd=null | — | {"ts": "2026-11-02T16:06:30.090747+00:00", "kind": "image:muse-image-1.0", "model": "muse-image-1.0", "surface": "responses", "usage": {"input_tokens": 17101, "input_tokens_details": {"cached_tokens": 14080}, "output_tokens": 1203, "output_tokens_details": {"reasoning_tokens": 345}, "total_tokens": 18304}, "latency_ms": 16225, "est_cost_usd": null}
| 208 SAM patrol | live segment step in patrol-path timeline, region x243 y600 w388 h198, model sam-3.1, no error | sam-3.1 | os-build/logs/oc1b-model-proofs/sam-patrol-timeline.json |
| 209 segment prompt | "Single-story structure actively burning with flames along roofline" = first observation's description | — | prompt field: "Single-story structure actively burning with flames along roofline"
| 210 SAM failure | key withheld -> segment step error "SPARK_API_KEY is not set in the environment: no model transport is configured", NO region key | sam-3.1 | os-build/logs/oc1b-model-proofs/sam-failure-timeline.json |
| 211 flag pipeline in failure run | final outcome dispatched-simulated (stub loopback dispatch), incident stands on its assessments | — | incident timeline end state in sam-failure-timeline.json |
| 212 Wonder review | UNPROVEN (see defect below): specified path yields reader "spark" + named fallback; Wonder returns no content at crew.py's default max_tokens=1600 (1598/1600 reasoning tokens measured live, finish=length) | muse-wonder-1.0 | os-build/logs/oc1b-model-proofs/wonder-review-timeline.json |
| 213 Wonder verdict | UNPROVEN (depends on 212): review category/latency on the step are the Spark queue reading's, honestly labelled reader "spark" | — | same file |
| 214 Wonder fallback | key withheld -> reader "spark", reader_fallback "Wonder review unavailable (SPARK_API_KEY is not set ...); Spark queue reading used" | — | os-build/logs/oc1b-model-proofs/wonder-fallback-timeline.json |
| 215 judge model | UNPROVEN (see defect below): TRIO_JUDGE_MODEL=1 live judge call made; muse-spark-1.3 spent 1198/1200 tokens on reasoning, finish=length, no content -> judge_mode "deterministic" + named fallback | muse-spark-1.3 | os-build/logs/oc1b-model-proofs/judge-model-timeline.json |
| 216 judge off | judge_mode "deterministic", verdict confirmed, reasons ["two independent readings agree on 'structure fire'"] | — | os-build/logs/oc1b-model-proofs/judge-deterministic-timeline.json |
| 217 judge fallback | PROVEN forced: key withheld -> reasons ["model judge unavailable (SPARK_API_KEY is not set ...); deterministic ruling used", ...]; natural starvation (215) is second evidence | — | os-build/logs/oc1b-model-proofs/judge-fallback-timeline.json |
| 218 all-flags | SAM live region + Wonder-attempt + judge-attempt in one incident, outcome dispatched-simulated | all | os-build/logs/oc1b-model-proofs/all-flags-timeline.json |
| 219 all-flags dispatch | dispatch step simulated=true service="fire department" receipt sim-localhost-001 over REAL loopback HTTP (server saw POST /fire; package simulated=true, destination "SIMULATED fire department endpoint (local stack route)") | — | receipt: {"at": "2026-11-02T16:11:04.296Z", "step": "dispatch", "simulated": true, "service": "fire department", "receipt_id": "sim-localhost-001", "status": "dispatched-simulated"}
| 220 transcribe | EndpointUnresolvedError, seam untouched (no crew/patrol wiring references transcribe) | voice | os-build/logs/oc1b-model-proofs/transcribe-unresolved.txt |

## OC1B-221 spend (from server/queue/model_receipts.jsonl + spark_guardrail_state.json; 18 receipt lines, all this session)
- Spark at published rates: assess:ignis reading $0.015317 + 4 judge chat calls $0.022639 = $0.037956 (~$0.038)
- Other models at Spark rates (ESTIMATES, labelled): muse-image-1.0 $0.026489; muse-wonder-1.0 $0.032554 over 6 calls; sam-3.1 $0.0 (images_processed only)
- Guardrail total counted: $0.097 of $75. No pressure on the budget.

## OC1B-224 failures / honest results (a failed call is a result, never a deleted line)
1. Wonder chat_text first attempt with max_tokens=50: reasoning consumed 48/50 tokens, finish=length, content null -> RuntimeError, receipt kept (line 0). Succeeded at default budget: 'WONDEROK'.
2. SAM models.segment prompt "visible flame": empty output text -> ValueError, no region invented (matches wave-3's two no-box prompts on this frame). Prompt "the burning building engulfed in flames" returns a box. Prompt shape matters; all three calls receipted.
3. Wonder review (crew specified path, max_tokens=1600): no message content -> fallback named on the step (two live evidences: key-present starvation + key-withheld).
4. Judge model call (specified path, max_tokens=1200): no message content -> fallback named on the step (two live evidences likewise).
5. DEFECT REPORT for crew lane (not fixed here): crew.py `_run_review` calls models.chat_image with default max_tokens=1600 and `_run_review`'s judge calls models.chat_text with default 1200; both reasoning models exhaust those budgets on reasoning tokens (measured live: 1598/1600, 1198/1200, finish=length). With max_tokens=4000 Wonder answers the SAME assessment prompt with a valid v2 ignis reading (category "structure fire", 5 observations, verified parsing). Fix belongs to the crew/model lane (raise budgets or set reasoning effort); the specified-path proofs above stand as measured.

## Verdicts
- PROVEN live: 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 214, 216, 217, 218, 219, 220, 221, 222, 223, 224.
- UNPROVEN with named reason: 212, 213 (Wonder reader on specified path — token-budget starvation, defect filed above), 215 (judge_mode "model" — same class, Spark reasoning starvation; deterministic fallback PROVEN in its place).
