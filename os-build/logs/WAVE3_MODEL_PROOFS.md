# WAVE3_MODEL_PROOFS.md — Section 3, tasks 17-28 (tip c7aeb162, worktree /tmp/wave3)

17. Read server/queue/models.py + MODEL_INTEGRATION.md: done
    (recon in logs/wave2-sec6.md + inline below). Key facts:
    chat_text(model, prompt)->(text, model, ms); segment(bytes,
    prompt)->record with region or ValueError (never invents);
    generate_image(prompt)->(bytes, fmt, model, ms); transcribe
    raises EndpointUnresolvedError (voice NOT resolved, untouched).
    Judge v2: judge.rule_with_model over both readings when
    TRIO_JUDGE_MODEL=1 else deterministic combine(); timeline
    carries judge_mode either way.
18. Queue suite BEFORE live work: 141/141 OK (was 128; +9 models
    tests +6 judge-model tests... actually +13: 9 test_models +
    6 test_judge_model = 15? 128+13=141 ✓).
19. chat_text muse-wonder-1.0 "Reply WONDEROK" -> "WONDEROK",
    live, lat 1085ms. Receipt in receipts-chat file.
20. segment on test-footage/frames/ignis-fire-1.jpg, two prompts
    ("fire", "segment the visible fire region"): SAM live-called
    twice (receipts logged, lat 1410/1125ms) but returned NO box
    both times -> ValueError, no region returned. Recorded as-is;
    no region invented.
21. Compare: live Spark reading (spark_gen.generate, muse-spark-1.3,
    24s): category "structure fire", obs "Single-story small
    building... flames along roofline... evidence: center of
    frame" (w3-spark-reading.json). Doc's captured SAM output
    (2026-11-02 probe): box 8,0-599,354 on 600x470 ->
    region x13 y0 w985 h753. Comparison: Spark gives a textual
    center-of-frame evidence, not a numeric box; today's SAM
    call gave no box at all. Agreement: UNPROVEN (no two numeric
    regions to compare); both readings agree it is fire.
22. generate_image "a small blue ribbon logo on black" ->
    w3-gen.webp, 60,266 bytes, real webp magic, muse-image-1.0,
    lat 12.1s.
23. Judge-model incident: Ignis staged flame on cam-b, run with
    TRIO_JUDGE_MODEL=1 end to end (wave3 tree): outcome
    dispatched-simulated, receipt sim-761c4539a6303a20 (re-run
    sim-f0e40e16... see note), judge step present BUT
    judge_mode "deterministic" — the live judge call went out
    and came back with no message content. Task asked for
    judge_mode "model": NOT achieved — UNPROVEN, reason below.
24. Timeline excerpt: review step carries judged_by
    imperium-judge, judge_mode deterministic + named fallback
    reason (incident.json in wave3-model-proofs/).
25. Flag-off shape: same incident with TRIO_JUDGE_MODEL unset
    runs deterministic by design (crew.py default); judge_mode
    deterministic on both runs — "both modes side by side"
    holds as fallback-vs-default, NOT model-vs-default.
    Model side: UNPROVEN (see 23).
26. Fallback: PROVEN — three runs, each timeline names it:
    "model judge unavailable (muse-spark-1.3 response carried
    no message content); deterministic ruling used".
    Direct judge-prompt call works (224-char reply), so the
    failure is run-context, not prompt shape — crew-lane
    follow-up, no more retries from this lane.
27. This file + artifacts: w3-gen.webp, w3-spark-reading.json,
    receipts-*.jsonl, drill.log, incident.json,
    package-sent.json, receipt.txt (all under
    os-build/logs/wave3-model-proofs/).
28. Spend: receipts show 4 muse-spark-1.3 calls totalling
    $0.0160 est; wonder/SAM/image carry usage with est null
    (no rate card). Wave-3 live total: $0.016. Caps untouched
    ($20 wave / $75 guardrail).
