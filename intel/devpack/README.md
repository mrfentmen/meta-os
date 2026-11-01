# Payload dev pack (DSH-037, Pax)

Static example JSON for the dashboard lane (Rowan). Build panels
against these files, not against a live room. Every payload below
was produced by real producer code on fixtures, never hand-written
history: the test `tests/test_intel_devpack.py` rebuilds all four
payloads from scratch and asserts they equal these files. If that
test fails on equality, this pack is stale: regenerate it, do not
hand-edit a payload to match a panel.

Regenerate with, from the repo root:

```
python3 tests/test_intel_devpack.py --dump intel/devpack
```

No step in the build posts to a bus, calls Spark, or touches a
real Redis. The whole build runs on FakeUpstash under a frozen
clock (epoch 1793101200), so the files are byte stable.

## Files

- `brief.json`: two morning brief records from one fixture
  snapshot, built by `intel/brief.py` `generate_brief` in dry-run
  mode. `fresh` is 900 seconds old, `stale` is 12600 seconds old:
  the BRF-043 pair. Both are template briefs (`model` is
  `template`): no Spark call was made, and the panel must render
  the TEMPLATE marker for both.
- `plan_preview.json`: the demo goal plan
  (`hackathon/demo_goal_plan.json`) through `validated_plan` and
  `check_dep_graph`, reduced to the DSP-037 preview shape by
  `intel/devpack.py`. Five jobs, posting order module, panel,
  tests, docs, review.
- `alerts.json`: five WDG-010 alert records from one
  `watchdog.tick` on a stall/collision/dead-dep fixture snapshot.
  One collision alert fires per colliding pair, so the three
  claimed jobs sharing `intel/status.py` yield three collision
  records. All five are critical and open, newest first.
- `crew_board.json`: presence beats, capability registrations,
  and jobs.py posts, claim, progress, and block run on
  FakeUpstash, then read back as `presence_list`,
  `capabilities.agents`, and `list --json`. Job 1 is claimed by
  milo, job 2 is open, job 3 is blocked with its reason on the
  hash (the block reason is not a `list --json` field).

## Read this before building against the spec

`docs/DASHBOARD_SPEC.md` section 4, 5, and 6 describe contract
shapes. Where the real records differ, the real records win and
this pack shows the real shape:

1. Brief sections are capitalized string lists: `Decisions`,
   `In flight`, `Owners`, `Blocked and why`, `Watch items`. The
   spec sketches lowercase structured objects (`owners` with nick
   and job fields, `blocked` with reason fields). The panel
   renders the strings in this pack; structured brief sections
   do not exist yet.
2. Alert records carry `status`, `last_seen`,
   `acknowledged_at`, and `resolved_at` (all null here except
   `status` and `last_seen`), plus `subjects` and detector
   evidence fields (`nick`, `job`, `shared_path`, `other_job`,
   and so on). The spec names `acked_by`; no such field exists.
   Read acknowledgement from `acknowledged_at`.
3. `list --json` rows carry exactly ten keys: `id`, `title`,
   `status`, `claim`, `files`, `deps`, `req`, `attempts`,
   `lease_until`, `last_progress_at`. The `req` key arrived
   with DSP-012; a row for a job with no capability ask
   carries an empty string. The spec also lists
   `last_heartbeat_at`; that field is stored on the job
   hash but `list --json` does not emit it. Read it from
   `jobs.py show` when a panel needs it.
4. The crew board pack has no precomputed rows. Derive rows from
   the three sources, per spec section 3: a nick with caps but no
   presence renders stale, a claimed job renders its holder row
   as working, a blocked job renders its holder row as blocked.
5. Plan preview jobs carry `key`, `title`, `files`, `deps`,
   `max_attempts`, `accept`, and `req`, plus the top level `summary`,
   `posting_order`, and `budgets`. They do not carry `spec`:
   the spec text stays in the plan, not the preview.
6. Brief entries carry `as_of` and `age_seconds` computed at pack
   build time. A live reader computes age from `generated_at`
   at read time instead of trusting a stored age.

## Fixture story, and its limits

One room, `build-relay-intel`, and one shared job story: the
status page module, its tests, and its viewer stub. Brief job 1
and crew job 1 are the same logical job (claimed by milo).
Alert fixture jobs 7, 8, and 9 exist only in the alert
snapshot: they demonstrate the collision and dead-dep detectors
and are not crew board jobs. Do not join alert job ids against
the crew board jobs in this pack and expect matches beyond job
1 and job 3.

No secrets appear in this pack. Capability records carry no `dm`
field, and no spend or token field carries a real value: the
brief `spend_id` is null because a template brief makes no Spark
call.
