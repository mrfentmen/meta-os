# Dispatch golden goals (DSP-022)

Twelve plain-English goals with the plan shape each one should
produce. A golden goal is a contract, not a demo: the goal text,
the expected job-count range, the files the plan must own, and
the dependency edges the plan must carry. A plan is inside its
shape when its dry-run passes every gate (DSP-002 parse, DSP-003
overlap, DSP-004 dep graph, DSP-005 budget clamp, DSP-006
dry-run) AND its job count is inside the range, it owns every
must-own file, and it carries every must-have dep edge.

Honest limit, stated plainly: the plan JSON under each goal is
hand-authored, NOT Spark output. Real Spark transport is still
blocked, so no Spark-generated plan has been scored against
these shapes yet. When transport lands, the re-run is: send
each goal to Spark, dry-run the plan Spark returns, and check
it against the same range, files, and edges below. A Spark
plan that dry-runs clean but falls outside its shape is a
DSP-024 prompt failure, not a pass. Nothing here was posted,
claimed, or announced; every plan below is a literal string
checked by the DSP-022 test, never a live dispatch.

How the test checks this file: tests/test_intel_dispatch.py
GoldenGoalsTest reads this file, takes the one JSON block in
each G-section, dry-runs it, and asserts the count, files, and
edges that section states. If a plan and its stated shape ever
disagree, the test fails. The file and the test cannot drift
apart silently.

Spec note: every job spec below carries the five DSP-026
parts in short form (goal, context, files, steps, out of
scope). DSP-026 is now done: the standard is written in
intel/prompts/dispatch.md (Spec-writing standard section) and
scored by intel/dispatch.py `score_spec_parts`, with
SpecStandardTest in tests/test_intel_dispatch.py scoring all
41 jobs in these 12 plans at 100% (every part present, in
order, with content, and the Files part naming an owned file).

Accept note: every job below also carries at least one
machine-checkable accept line. DSP-027 is now done: the
standard is written in intel/prompts/dispatch.md
(Acceptance-line standard section) and scored by
intel/dispatch.py `score_accept_lines`, with
AcceptanceStandardTest in tests/test_intel_dispatch.py scoring
all 41 jobs in these 12 plans at 100% (at least one parseable
check each; every file-exists and contains line naming an owned
file). One distinction the standard pins down: a tests-pass
line names the test module that checks the job, not an owned
file — G1, G4, and G12 carry tests-pass lines naming test
modules their jobs do not own, and those pass by design.

## G1 — brief template note

Goal: "Add a one-line uptime note to the morning brief template."

Job count: 1-2

Must-own files: intel/brief.py

Must-have deps: none

Dry-run posting order: template

```json
{
  "summary": "Add one uptime line to the morning brief template.",
  "jobs": [
    {
      "key": "template",
      "title": "Add uptime line to morning brief template",
      "spec": "Goal: one uptime line in the template. Context: the morning brief template in intel/brief.py. Files: intel/brief.py. Steps: add the line, run the brief tests. Out of scope: any new brief section.",
      "files": ["intel/brief.py"],
      "deps": [],
      "max_attempts": 3,
      "accept": ["file-exists: intel/brief.py", "contains: intel/brief.py :: TEMPLATE", "tests-pass: tests.test_intel_brief"]
    }
  ]
}
```

## G2 — window label fix, then CLI

Goal: "Fix the snapshot window label in the brief, then wire the fixed label into the CLI."

Job count: 2-3

Must-own files: intel/brief.py, intel.py

Must-have deps: label -> cli

Dry-run posting order: label -> cli

```json
{
  "summary": "Fix the window label in the brief, then wire it into the CLI.",
  "jobs": [
    {
      "key": "label",
      "title": "Fix snapshot window label in brief",
      "spec": "Goal: correct window label. Context: the brief window line. Files: intel/brief.py. Steps: fix the label, run the brief tests. Out of scope: changing the window itself.",
      "files": ["intel/brief.py"],
      "deps": [],
      "max_attempts": 3,
      "accept": ["file-exists: intel/brief.py", "contains: intel/brief.py :: Window"]
    },
    {
      "key": "cli",
      "title": "Wire fixed window label into CLI",
      "spec": "Goal: CLI shows the fixed label. Context: the brief CLI in intel.py. Files: intel.py. Steps: wire the label through, run the CLI tests. Out of scope: new CLI flags.",
      "files": ["intel.py"],
      "deps": ["label"],
      "max_attempts": 3,
      "accept": ["file-exists: intel.py", "contains: intel.py :: brief"]
    }
  ]
}
```

## G3 — threshold, alert, docs

Goal: "Add a stall threshold, the alert text that fires at it, and the operations doc line that explains it."

Job count: 3-4

Must-own files: intel/thresholds.py, intel/alerts.py, docs/mos-operations.md

Must-have deps: threshold -> alert, alert -> docs

Dry-run posting order: threshold -> alert -> docs

```json
{
  "summary": "Add a stall threshold, its alert text, and its doc line.",
  "jobs": [
    {
      "key": "threshold",
      "title": "Add stall threshold",
      "spec": "Goal: a stall threshold constant. Context: watchdog thresholds. Files: intel/thresholds.py. Steps: add the constant, run the watchdog tests. Out of scope: changing existing thresholds.",
      "files": ["intel/thresholds.py"],
      "deps": [],
      "max_attempts": 3,
      "accept": ["file-exists: intel/thresholds.py"]
    },
    {
      "key": "alert",
      "title": "Add alert text for the new threshold",
      "spec": "Goal: alert text at the new threshold. Context: the alerts module. Files: intel/alerts.py. Steps: add the text, run the alert tests. Out of scope: new alert kinds.",
      "files": ["intel/alerts.py"],
      "deps": ["threshold"],
      "max_attempts": 3,
      "accept": ["file-exists: intel/alerts.py", "contains: intel/alerts.py :: STALL"]
    },
    {
      "key": "docs",
      "title": "Document the new threshold",
      "spec": "Goal: one doc line for the threshold. Context: the operations doc. Files: docs/mos-operations.md. Steps: add the line, check the doc renders. Out of scope: rewriting the operations doc.",
      "files": ["docs/mos-operations.md"],
      "deps": ["alert"],
      "max_attempts": 3,
      "accept": ["file-exists: docs/mos-operations.md"]
    }
  ]
}
```

## G4 — snapshot view diamond

Goal: "Build the snapshot view: a snapshot module, a CLI entry, a viewer panel, and docs."

Job count: 4-5

Must-own files: intel/ingest.py, bus.html, intel/README.md

Must-have deps: snapshot -> cli, snapshot -> panel, cli -> docs, panel -> docs

Dry-run posting order: snapshot -> cli -> panel -> docs

```json
{
  "summary": "Build the snapshot view: module, CLI, panel, docs.",
  "jobs": [
    {
      "key": "snapshot",
      "title": "Build snapshot module",
      "spec": "Goal: a snapshot module. Context: the ingest layer. Files: intel/ingest.py. Steps: build the module, run the ingest tests. Out of scope: the viewer panel.",
      "files": ["intel/ingest.py"],
      "deps": [],
      "max_attempts": 3,
      "accept": ["file-exists: intel/ingest.py", "tests-pass: tests.test_intel_snapshot"]
    },
    {
      "key": "cli",
      "title": "Add CLI entry for snapshots",
      "spec": "Goal: a CLI entry over the snapshot module. Context: the intel CLI. Files: intel.py. Steps: add the entry, run the CLI tests. Out of scope: new snapshot fields.",
      "files": ["intel.py"],
      "deps": ["snapshot"],
      "max_attempts": 3,
      "accept": ["file-exists: intel.py", "contains: intel.py :: snapshot"]
    },
    {
      "key": "panel",
      "title": "Add viewer panel for snapshots",
      "spec": "Goal: a viewer panel for snapshots. Context: the viewer page. Files: bus.html. Steps: add the panel, check it renders. Out of scope: new snapshot fields.",
      "files": ["bus.html"],
      "deps": ["snapshot"],
      "max_attempts": 3,
      "accept": ["file-exists: bus.html"]
    },
    {
      "key": "docs",
      "title": "Document the snapshot view",
      "spec": "Goal: docs for the snapshot view. Context: the briefing engine README. Files: intel/README.md. Steps: add the section, check the doc renders. Out of scope: rewriting the README.",
      "files": ["intel/README.md"],
      "deps": ["cli", "panel"],
      "max_attempts": 3,
      "accept": ["file-exists: intel/README.md", "contains: intel/README.md :: snapshot"]
    }
  ]
}
```

## G5 — demo status page feature

Goal: "Build a small status page feature for the relay repo: an intel status module with tests, a viewer panel stub, docs for both, and a review pass — each as separate jobs with clear file ownership."

Job count: 5-6

Must-own files: intel/status.py, bus.html, docs/status-page.md

Must-have deps: module -> panel, module -> tests, panel -> docs, tests -> docs, docs -> review

Dry-run posting order: module -> panel -> tests -> docs -> review

```json
{
  "summary": "Build the status page: module, panel, tests, docs, review.",
  "jobs": [
    {
      "key": "module",
      "title": "Build intel status module",
      "spec": "Goal: an intel status module. Context: the intel package. Files: intel/status.py. Steps: build the module, run its tests. Out of scope: the viewer panel.",
      "files": ["intel/status.py"],
      "deps": [],
      "max_attempts": 3,
      "accept": ["file-exists: intel/status.py"]
    },
    {
      "key": "panel",
      "title": "Add viewer panel stub for status",
      "spec": "Goal: a viewer panel stub. Context: the viewer page. Files: bus.html. Steps: add the stub, check it renders. Out of scope: live status data.",
      "files": ["bus.html"],
      "deps": ["module"],
      "max_attempts": 3,
      "accept": ["file-exists: bus.html"]
    },
    {
      "key": "tests",
      "title": "Add tests for the status module",
      "spec": "Goal: tests for the status module. Context: the test suite. Files: tests/test_intel_status.py. Steps: write the tests, run them green. Out of scope: testing the panel.",
      "files": ["tests/test_intel_status.py"],
      "deps": ["module"],
      "max_attempts": 3,
      "accept": ["file-exists: tests/test_intel_status.py"]
    },
    {
      "key": "docs",
      "title": "Document the status page",
      "spec": "Goal: docs for module and panel. Context: the docs folder. Files: docs/status-page.md. Steps: write the doc, check it renders. Out of scope: rewriting other docs.",
      "files": ["docs/status-page.md"],
      "deps": ["panel", "tests"],
      "max_attempts": 3,
      "accept": ["file-exists: docs/status-page.md"]
    },
    {
      "key": "review",
      "title": "Review the status page feature",
      "spec": "Goal: a review pass over the feature. Context: the review notes folder. Files: intel/notes/status-review.md. Steps: review module, panel, tests, and docs; record the verdict. Out of scope: changing the feature in this job.",
      "files": ["intel/notes/status-review.md"],
      "deps": ["docs"],
      "max_attempts": 3,
      "accept": ["file-exists: intel/notes/status-review.md"]
    }
  ]
}
```

## G6 — two independent jobs

Goal: "Add a quiet-hours note to the alert copy and a separate note to the threshold module, as two independent jobs."

Job count: 2-3

Must-own files: intel/alerts.py, intel/thresholds.py

Must-have deps: none

Dry-run posting order: alerts -> thresholds

```json
{
  "summary": "Two independent notes: one in alerts, one in thresholds.",
  "jobs": [
    {
      "key": "alerts",
      "title": "Add quiet-hours note to alert copy",
      "spec": "Goal: a quiet-hours note in alerts. Context: the alerts module. Files: intel/alerts.py. Steps: add the note, run the alert tests. Out of scope: threshold values.",
      "files": ["intel/alerts.py"],
      "deps": [],
      "max_attempts": 3,
      "accept": ["file-exists: intel/alerts.py"]
    },
    {
      "key": "thresholds",
      "title": "Add note to threshold module",
      "spec": "Goal: a note in the threshold module. Context: watchdog thresholds. Files: intel/thresholds.py. Steps: add the note, run the watchdog tests. Out of scope: alert copy.",
      "files": ["intel/thresholds.py"],
      "deps": [],
      "max_attempts": 3,
      "accept": ["file-exists: intel/thresholds.py"]
    }
  ]
}
```

## G7 — two jobs, one summary

Goal: "Summarize the ingest and watchdog work in the README, as one summary job after two independent jobs."

Job count: 3-4

Must-own files: intel/ingest.py, intel/watchdog.py, intel/README.md

Must-have deps: ingest -> summary, watchdog -> summary

Dry-run posting order: ingest -> watchdog -> summary

```json
{
  "summary": "Two independent jobs, then one README summary over both.",
  "jobs": [
    {
      "key": "ingest",
      "title": "Tidy the ingest module",
      "spec": "Goal: a tidy-up of ingest. Context: the ingest layer. Files: intel/ingest.py. Steps: tidy, run the ingest tests. Out of scope: new ingest fields.",
      "files": ["intel/ingest.py"],
      "deps": [],
      "max_attempts": 3,
      "accept": ["file-exists: intel/ingest.py"]
    },
    {
      "key": "watchdog",
      "title": "Tidy the watchdog module",
      "spec": "Goal: a tidy-up of watchdog. Context: the watchdog layer. Files: intel/watchdog.py. Steps: tidy, run the watchdog tests. Out of scope: new alert kinds.",
      "files": ["intel/watchdog.py"],
      "deps": [],
      "max_attempts": 3,
      "accept": ["file-exists: intel/watchdog.py"]
    },
    {
      "key": "summary",
      "title": "Summarize ingest and watchdog in README",
      "spec": "Goal: one README summary over both jobs. Context: the briefing engine README. Files: intel/README.md. Steps: write the summary, check the doc renders. Out of scope: changing either module.",
      "files": ["intel/README.md"],
      "deps": ["ingest", "watchdog"],
      "max_attempts": 3,
      "accept": ["file-exists: intel/README.md"]
    }
  ]
}
```

## G8 — new alert kind end to end

Goal: "Add a new alert kind end to end: detection, plain-English explanation, panel line, and operations doc."

Job count: 4-5

Must-own files: intel/watchdog.py, intel/explanations.py, bus.html

Must-have deps: detect -> explain, explain -> panel, panel -> docs

Dry-run posting order: detect -> explain -> panel -> docs

```json
{
  "summary": "A new alert kind: detect, explain, panel, docs.",
  "jobs": [
    {
      "key": "detect",
      "title": "Detect the new alert kind",
      "spec": "Goal: detection for a new alert kind. Context: the watchdog layer. Files: intel/watchdog.py. Steps: add detection, run the watchdog tests. Out of scope: the explanation text.",
      "files": ["intel/watchdog.py"],
      "deps": [],
      "max_attempts": 3,
      "accept": ["file-exists: intel/watchdog.py"]
    },
    {
      "key": "explain",
      "title": "Explain the new alert kind in plain English",
      "spec": "Goal: plain-English explanation. Context: the explanations module. Files: intel/explanations.py. Steps: add the explanation, run the explanation tests. Out of scope: detection rules.",
      "files": ["intel/explanations.py"],
      "deps": ["detect"],
      "max_attempts": 3,
      "accept": ["file-exists: intel/explanations.py"]
    },
    {
      "key": "panel",
      "title": "Add panel line for the new alert kind",
      "spec": "Goal: a panel line for the kind. Context: the viewer page. Files: bus.html. Steps: add the line, check it renders. Out of scope: new alert kinds.",
      "files": ["bus.html"],
      "deps": ["explain"],
      "max_attempts": 3,
      "accept": ["file-exists: bus.html"]
    },
    {
      "key": "docs",
      "title": "Document the new alert kind",
      "spec": "Goal: one operations doc section. Context: the operations doc. Files: docs/mos-operations.md. Steps: add the section, check the doc renders. Out of scope: rewriting the operations doc.",
      "files": ["docs/mos-operations.md"],
      "deps": ["panel"],
      "max_attempts": 3,
      "accept": ["file-exists: docs/mos-operations.md"]
    }
  ]
}
```

## G9 — two chains, one panel, one README line

Goal: "Ship two small chains at once — ingest plus CLI, and alerts plus thresholds — then one panel and one README line over both."

Job count: 6-7

Must-own files: intel/ingest.py, intel/alerts.py, bus.html, intel/README.md

Must-have deps: ingest-a -> cli-b, alerts-c -> thresholds-d, cli-b -> panel-e, thresholds-d -> panel-e, panel-e -> readme-f

Dry-run posting order: ingest-a -> cli-b -> alerts-c -> thresholds-d -> panel-e -> readme-f

```json
{
  "summary": "Two chains, then one panel and one README line over both.",
  "jobs": [
    {
      "key": "ingest-a",
      "title": "Tidy the ingest module",
      "spec": "Goal: a tidy-up of ingest. Context: the ingest layer. Files: intel/ingest.py. Steps: tidy, run the ingest tests. Out of scope: new ingest fields.",
      "files": ["intel/ingest.py"],
      "deps": [],
      "max_attempts": 3,
      "accept": ["file-exists: intel/ingest.py"]
    },
    {
      "key": "cli-b",
      "title": "Add CLI entry over ingest",
      "spec": "Goal: a CLI entry over ingest. Context: the intel CLI. Files: intel.py. Steps: add the entry, run the CLI tests. Out of scope: new ingest fields.",
      "files": ["intel.py"],
      "deps": ["ingest-a"],
      "max_attempts": 3,
      "accept": ["file-exists: intel.py", "contains: intel.py :: snapshot"]
    },
    {
      "key": "alerts-c",
      "title": "Tidy the alerts module",
      "spec": "Goal: a tidy-up of alerts. Context: the alerts module. Files: intel/alerts.py. Steps: tidy, run the alert tests. Out of scope: new alert kinds.",
      "files": ["intel/alerts.py"],
      "deps": [],
      "max_attempts": 3,
      "accept": ["file-exists: intel/alerts.py"]
    },
    {
      "key": "thresholds-d",
      "title": "Tidy the thresholds module",
      "spec": "Goal: a tidy-up of thresholds. Context: watchdog thresholds. Files: intel/thresholds.py. Steps: tidy, run the watchdog tests. Out of scope: new threshold values.",
      "files": ["intel/thresholds.py"],
      "deps": ["alerts-c"],
      "max_attempts": 3,
      "accept": ["file-exists: intel/thresholds.py"]
    },
    {
      "key": "panel-e",
      "title": "Add panel line over both chains",
      "spec": "Goal: one panel line over both chains. Context: the viewer page. Files: bus.html. Steps: add the line, check it renders. Out of scope: new panel sections.",
      "files": ["bus.html"],
      "deps": ["cli-b", "thresholds-d"],
      "max_attempts": 3,
      "accept": ["file-exists: bus.html"]
    },
    {
      "key": "readme-f",
      "title": "Add README line over both chains",
      "spec": "Goal: one README line over both chains. Context: the briefing engine README. Files: intel/README.md. Steps: add the line, check the doc renders. Out of scope: rewriting the README.",
      "files": ["intel/README.md"],
      "deps": ["panel-e"],
      "max_attempts": 3,
      "accept": ["file-exists: intel/README.md"]
    }
  ]
}
```

## G10 — eval note, then README link

Goal: "Write the eval methodology note, then link it from the briefing engine README."

Job count: 2-3

Must-own files: intel/evals/README.md, intel/README.md

Must-have deps: note -> link

Dry-run posting order: note -> link

```json
{
  "summary": "Write the eval note, then link it from the README.",
  "jobs": [
    {
      "key": "note",
      "title": "Write eval methodology note",
      "spec": "Goal: an eval methodology note. Context: the evals folder. Files: intel/evals/README.md. Steps: write the note, check it renders. Out of scope: new evals.",
      "files": ["intel/evals/README.md"],
      "deps": [],
      "max_attempts": 3,
      "accept": ["file-exists: intel/evals/README.md"]
    },
    {
      "key": "link",
      "title": "Link the eval note from the README",
      "spec": "Goal: a README link to the eval note. Context: the briefing engine README. Files: intel/README.md. Steps: add the link, check the doc renders. Out of scope: rewriting the README.",
      "files": ["intel/README.md"],
      "deps": ["note"],
      "max_attempts": 3,
      "accept": ["file-exists: intel/README.md"]
    }
  ]
}
```

## G11 — three jobs, one summary

Goal: "Summarize three independent pieces — ingest, alerts, thresholds — in one README summary job."

Job count: 4-5

Must-own files: intel/ingest.py, intel/alerts.py, intel/thresholds.py, intel/README.md

Must-have deps: ingest -> summary, alerts -> summary, thresholds -> summary

Dry-run posting order: ingest -> alerts -> thresholds -> summary

```json
{
  "summary": "Three independent jobs, then one README summary over all three.",
  "jobs": [
    {
      "key": "ingest",
      "title": "Tidy the ingest module",
      "spec": "Goal: a tidy-up of ingest. Context: the ingest layer. Files: intel/ingest.py. Steps: tidy, run the ingest tests. Out of scope: new ingest fields.",
      "files": ["intel/ingest.py"],
      "deps": [],
      "max_attempts": 3,
      "accept": ["file-exists: intel/ingest.py"]
    },
    {
      "key": "alerts",
      "title": "Tidy the alerts module",
      "spec": "Goal: a tidy-up of alerts. Context: the alerts module. Files: intel/alerts.py. Steps: tidy, run the alert tests. Out of scope: new alert kinds.",
      "files": ["intel/alerts.py"],
      "deps": [],
      "max_attempts": 3,
      "accept": ["file-exists: intel/alerts.py"]
    },
    {
      "key": "thresholds",
      "title": "Tidy the thresholds module",
      "spec": "Goal: a tidy-up of thresholds. Context: watchdog thresholds. Files: intel/thresholds.py. Steps: tidy, run the watchdog tests. Out of scope: new threshold values.",
      "files": ["intel/thresholds.py"],
      "deps": [],
      "max_attempts": 3,
      "accept": ["file-exists: intel/thresholds.py"]
    },
    {
      "key": "summary",
      "title": "Summarize all three pieces in README",
      "spec": "Goal: one README summary over three jobs. Context: the briefing engine README. Files: intel/README.md. Steps: write the summary, check the doc renders. Out of scope: changing any module.",
      "files": ["intel/README.md"],
      "deps": ["ingest", "alerts", "thresholds"],
      "max_attempts": 3,
      "accept": ["file-exists: intel/README.md"]
    }
  ]
}
```

## G12 — brief section end to end

Goal: "Ship a brief section end to end: prompt, extractor, storage, docs, and an eval log entry."

Job count: 5-6

Must-own files: intel/prompts/brief_morning.md, intel/brief.py, intel/store.py

Must-have deps: prompt -> extract, extract -> store, store -> docs, docs -> eval

Dry-run posting order: prompt -> extract -> store -> docs -> eval

```json
{
  "summary": "A brief section end to end: prompt, extract, store, docs, eval.",
  "jobs": [
    {
      "key": "prompt",
      "title": "Write the brief section prompt",
      "spec": "Goal: a prompt for the new section. Context: the brief prompts folder. Files: intel/prompts/brief_morning.md. Steps: write the prompt, check it renders on a fixture. Out of scope: other brief kinds.",
      "files": ["intel/prompts/brief_morning.md"],
      "deps": [],
      "max_attempts": 3,
      "accept": ["file-exists: intel/prompts/brief_morning.md"]
    },
    {
      "key": "extract",
      "title": "Build the brief section extractor",
      "spec": "Goal: an extractor for the section. Context: the brief module. Files: intel/brief.py. Steps: build the extractor, run the brief tests. Out of scope: the composer.",
      "files": ["intel/brief.py"],
      "deps": ["prompt"],
      "max_attempts": 3,
      "accept": ["file-exists: intel/brief.py", "tests-pass: tests.test_intel_brief"]
    },
    {
      "key": "store",
      "title": "Store the new brief section",
      "spec": "Goal: storage for the section. Context: the store module. Files: intel/store.py. Steps: wire storage, run the store tests. Out of scope: the CLI.",
      "files": ["intel/store.py"],
      "deps": ["extract"],
      "max_attempts": 3,
      "accept": ["file-exists: intel/store.py"]
    },
    {
      "key": "docs",
      "title": "Document the new brief section",
      "spec": "Goal: docs for the section. Context: the briefing engine README. Files: intel/README.md. Steps: add the section, check the doc renders. Out of scope: rewriting the README.",
      "files": ["intel/README.md"],
      "deps": ["store"],
      "max_attempts": 3,
      "accept": ["file-exists: intel/README.md"]
    },
    {
      "key": "eval",
      "title": "Log the eval score for the new section",
      "spec": "Goal: an eval log entry. Context: the evals folder. Files: intel/evals/log.md. Steps: score the section, append the entry. Out of scope: changing the rubric.",
      "files": ["intel/evals/log.md"],
      "deps": ["docs"],
      "max_attempts": 3,
      "accept": ["file-exists: intel/evals/log.md"]
    }
  ]
}
```
