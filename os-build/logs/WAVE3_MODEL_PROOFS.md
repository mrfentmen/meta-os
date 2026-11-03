# WAVE3_MODEL_PROOFS.md — Section 3, tasks 17-28 (tip 6524ebaf era tree, run 2026-11-02)

17. Read server/queue/models.py + MODEL_INTEGRATION.md: done.
    chat_text(model, prompt)->(text, model, ms); segment->record
    with region or ValueError (never invents); generate_image->
    (bytes, fmt, model, ms); transcribe raises
    EndpointUnresolvedError (voice untouched).
18. Queue suite BEFORE live work: 277 tests, OK (grew from 141;
    new judge/model tests landed).
19. chat_text muse-wonder-1.0 "Reply WONDEROK" -> "WONDEROK",
    live. Receipt logged.
20. segment on test-footage/frames/ignis-fire-1.jpg: no box
    returned (ValueError path), recorded as-is — no region
    invented. Same result on two prompts.
21. Live Spark reading (spark_gen.generate, muse-spark-1.3):
    category "structure fire", obs "single-story wooden
    structure burning..." saved to wave3-model-proofs/.
    Compare vs doc's captured SAM region (x13 y0 w985 h753):
    no numeric SAM box today, so agreement UNPROVEN;
    both readings agree it is fire.
22. generate_image "blue ribbon logo": webp 43924 bytes, real
    magic, muse-image-1.0, saved to wave3-model-proofs/.
23. Judge incident TRIO_JUDGE_MODEL=1, Ignis staged flame, wave3
    tree: outcome dispatched-simulated, receipt on file.
    judge_mode came back DETERMINISTIC (named fallback, empty
    Spark reply xN). Model-mode UNPROVEN, reason recorded.
24. Timeline excerpt: review step judged_by imperium-judge,
    judge_mode deterministic + fallback reasons (filed).
25. Flag-off shape: combine() default, deterministic by design.
    Side-by-side: model path attempted, fallback path taken.
26. Fallback: PROVEN (named reasons in timeline each run).
    Direct judge-prompt call works (224 chars), so failure is
    run-context, not prompt shape — crew-lane follow-up, no
    more retries from this lane.
27. Artifacts: os-build/logs/wave3-model-proofs/ (gen webp,
    spark reading, receipts, drill.log, incident.json,
    package-sent.json, receipt.txt).
28. Spend: $0.0216 total across all logged live calls today
    (Spark only; wonder/SAM/image carry usage, est null).
    Caps untouched ($20 wave / $75 guardrail).
