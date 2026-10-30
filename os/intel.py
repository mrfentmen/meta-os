#!/usr/bin/env python3
"""intel.py — Relay Intelligence CLI (FND-016, BRF-009/011/024).

Subcommands:
  brief    Hana's lane (BRF-009/011/024/026, OS-049): --list, --show, --morning,
           --ondemand, --boot with --since windows. Reads and prints stored
           brief records; nothing invented.
  dispatch plain-English goal -> plan (DSP workstream). The dry-run
           is landed (DSP-006): dispatch --goal '...' --dry-run
           --plan <Spark plan JSON file> validates the plan through
           every gate and prints the full plan, posting nothing.
           The approval gate is landed (DSP-007): a dispatch
           without --dry-run validates the plan, runs the secret
           guard, and then requires a human approval — the
           --approve flag, or an interactive y/yes answer at the
           prompt on a real tty. Without approval it refuses
           loudly and posts nothing. With approval the poster
           (DSP-008) posts the plan through jobs.py in topological
           order, rewrites plan-key deps to real job ids, stores
           the dispatch record, and prints the key -> id mapping;
           a failed post exits 2 naming the failed job, and jobs
           already posted stay posted. Signing is landed
           (DSP-009): --secret-file signs every posted job with
           the crew keyring's HMAC (jobs.py verify then reports
           OK), and --crew-mode refuses an unsigned post
           outright; without either flag the CLI posts unsigned
           with a loud stderr WARNING. Size guardrail landed
           (DSP-013): a plan over 12 jobs or 40 files prints
           its guard message in the dry-run, and posting it
           needs a second confirmation -- the --confirm-large
           flag alongside --approve, or a second y/yes at the
           prompts; without it the CLI refuses and posts
           nothing.
           Announcement line is landed (DSP-010):
           intel.dispatch.format_dispatch_announcement builds
           the frozen DISPATCH:<id> -> <n> jobs line from a
           stored dispatch record, and dispatch --announce
           prints that line after a post. The line is printed
           only, never pushed to the bus: bus posting stays
           held under GOV-002 until Dale approves posting,
           and without --announce the CLI prints no line.
           Undo is landed (DSP-011): dispatch --undo <dispatch
           id> cancels every still-open job from that posted
           plan through jobs.py cancel, leaves claimed jobs and
           finished jobs untouched, and prints the report
           (cancelled, untouched claimed with claim nick,
           untouched other with status, missing); the report
           is also stored on the dispatch record. An unknown
           dispatch id exits 2 with nothing touched.
           Demo goal is landed (DSP-015): hackathon/demo_goal.py
           dry-runs the DEMO.md demo goal plan 5 times and writes
           hackathon/demo_goal_stability.md; the plan file is
           hackathon/demo_goal_plan.json, the hand-authored G5
           draft, not Spark output (live Spark transport is
           blocked, GOV-001).
           Plan diff view is landed (DSP-016): dispatch --show
           <dispatch id> prints the posted plan next to each
           job's current state (open, claimed, done, blocked,
           cancelled, failed-final, or missing), with the claim
           nick for claimed jobs and a per-status count; it
           reads only, never posts, claims, cancels, or writes
           the dispatch record. An unknown dispatch id exits
           2 with nothing touched.
           Spark failure fallback is landed (DSP-017, library
           only, no CLI Spark call while GOV-001 blocks live
           transport): intel.dispatch.plan_from_spark retries
           one malformed JSON answer, and a second malformed
           answer in a row yields one FALLBACK job carrying
           the raw goal as its spec, with a loud stderr
           warning; nothing malformed is posted, and the
           fallback still needs DSP-007 approval to post.
  watch    watchdog tick (WDG workstream, Milo). Routing from this
           CLI to the watchdog loop is still pending, so this
           subcommand refuses loudly.
  alerts   alert records via intel.store (FND-004): --show --id,
           plus the WDG-014 lifecycle: --ack --id (open ->
           acknowledged) and --resolve --id (open/acknowledged
           -> resolved), plus the WDG-023 history query:
           alerts [--room <room>] [--since <ts>] [--kind <kind>]
           lists matching records oldest first with no --id.
  snapshot read-only relay snapshot (FND-014): prints the ingest
           snapshot {room, messages, jobs, presence, caps} as JSON.

Usage for briefs:
    python3 intel.py brief --list --room <room>
    python3 intel.py brief --show --room <room> --ts <timestamp>
    python3 intel.py brief --show --room <room> --ts <timestamp> --announce
    python3 intel.py brief --morning --room <room>
        --snapshot <fixture.json> [--dry-run]
    python3 intel.py brief --ondemand --room <room> --since 2h
        --snapshot <fixture.json> [--now <ts>] [--dry-run]
    python3 intel.py brief --boot --room <room>
        --snapshot <fixture.json> [--dry-run]

Usage for dispatch dry-run:
    python3 intel.py dispatch --goal '...' --dry-run --plan plan.json
        (prints the full validated plan; posts nothing. --plan is
        the Spark-produced plan JSON: the live goal -> plan Spark
        step is DSP-015's work, so until then the plan file is the
        draft under review, never an invented one.)

--ondemand (BRF-024) builds an ad hoc ondemand brief scoped to
the --since window (2h, 30m, 7d, 1h30m); without --since it uses
the default 500-message / 24h window. --since also scopes a
--morning brief. A bad --since value is a CLI error, not a
silently wrong window.

--boot (OS-049) builds the boot brief the relay-brief.service
unit generates: morning format with the boot flag, so the
previous-session digest (OS-051) opens it and the BRF-028
guard does not hand back the previous session's brief.

--announce (BRF-010) with --show prints only the frozen BRIEF:
line for the stored brief, never the full record and never a
post: posting stays held under GOV-002 until Dale rules on the
room and the wire format, so the printed line is for verifying
the exact line a room post would carry, not a post itself.
--announce needs --show; with any other brief mode it is a
usage error.

Exit codes: 0 ok, 1 record not found, 2 usage error or engine not
yet implemented. Failures print RELAY_ERROR, repo style.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intel import brief as _brief  # noqa: E402


def _unimplemented(feature, task):
    """Loud refusal for a subcommand whose engine has not landed."""
    print(f"RELAY_ERROR: {feature} UNIMPLEMENTED ({task})",
          file=sys.stderr)
    return 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    brief_parser = sub.add_parser("brief")
    brief_parser.add_argument("--list", action="store_true")
    brief_parser.add_argument("--show", action="store_true")
    brief_parser.add_argument("--announce", action="store_true")
    brief_parser.add_argument("--morning", action="store_true")
    brief_parser.add_argument("--ondemand", action="store_true")
    brief_parser.add_argument("--boot", action="store_true")
    brief_parser.add_argument("--since", default=None)
    brief_parser.add_argument("--room", default="main")
    brief_parser.add_argument("--ts", type=int, default=None)
    brief_parser.add_argument("--snapshot", default=None)
    brief_parser.add_argument("--now", type=int, default=None)
    brief_parser.add_argument("--dry-run", action="store_true")
    dispatch_parser = sub.add_parser("dispatch")
    dispatch_parser.add_argument("--goal", default=None)
    dispatch_parser.add_argument("--room", default="main")
    dispatch_parser.add_argument("--dry-run", action="store_true")
    dispatch_parser.add_argument("--plan", default=None)
    dispatch_parser.add_argument("--approve", action="store_true")
    dispatch_parser.add_argument("--secret-file", default=None)
    dispatch_parser.add_argument("--crew-mode", action="store_true")
    dispatch_parser.add_argument("--confirm-large",
                                 action="store_true")
    dispatch_parser.add_argument("--announce", action="store_true",
                                 help="print the DSP-010 "
                                 "DISPATCH:<id> -> <n> jobs line "
                                 "after posting; the line is "
                                 "printed only, never pushed "
                                 "to the bus")
    dispatch_parser.add_argument("--undo", default=None,
                                 help="undo a posted dispatch: "
                                 "cancel its still-open jobs, "
                                 "leave claimed/finished jobs "
                                 "untouched, print the report")
    dispatch_parser.add_argument("--show", default=None,
                                 help="show a posted dispatch: "
                                 "plan as posted next to each "
                                 "job's current state, read only")
    watch_parser = sub.add_parser("watch")
    watch_parser.add_argument("--room", default="main")
    alerts_parser = sub.add_parser("alerts")
    alerts_parser.add_argument("--show", action="store_true")
    alerts_parser.add_argument("--ack", action="store_true")
    alerts_parser.add_argument("--resolve", action="store_true")
    alerts_parser.add_argument("--id", default=None)
    alerts_parser.add_argument("--room", default=None,
                               help="WDG-023 history filter: room")
    alerts_parser.add_argument("--since", default=None,
                               help="WDG-023 history filter: unix "
                                    "timestamp or ISO 8601 time")
    alerts_parser.add_argument("--kind", default=None,
                               help="WDG-023 history filter: alert kind")
    snapshot_parser = sub.add_parser("snapshot")
    snapshot_parser.add_argument("--room", default="main")
    args = parser.parse_args(argv)
    if args.command == "brief":
        if args.announce and not args.show:
            parser.error("--announce needs --show")
        if args.boot or args.morning or args.ondemand:
            snapshot = {}
            if args.snapshot:
                with open(args.snapshot) as handle:
                    snapshot = json.load(handle)
            try:
                # OS-079 follow-up: the brief path fills the
                # memory_budget record first, so a snapshot
                # that only carries a budgets list (and, when
                # the caller states them, settled decisions
                # or a down memory service) still carries
                # the settled-decisions and spend lines; a
                # snapshot that hand-states one keeps it,
                # and one that states nothing usable keeps
                # its exact old shape.
                snapshot = _brief.with_memory_budget(
                    snapshot, now=args.now)
                if args.boot or args.morning:
                    # OS-075 follow-up: the morning path fills
                    # the daily record first, so a snapshot
                    # that only carries a jobs list (and, when
                    # the caller states them, overnight results
                    # or needs-word questions) still carries
                    # the Daily brief section; a snapshot that
                    # hand-states one keeps it, and one that
                    # states nothing usable keeps its exact old
                    # shape. Ondemand briefs are left alone:
                    # the daily section belongs to the
                    # morning/daily brief, not to an ad hoc
                    # window brief.
                    snapshot = _brief.with_daily(
                        snapshot, now=args.now)
                    # OS-092 follow-up: the morning path fills
                    # the memory_depth record too, so a snapshot
                    # that only carries stated aged decisions,
                    # due commitments, or fresh-agent context
                    # (or a down memory service) still carries
                    # the Long-term memory section; a snapshot
                    # that hand-states one keeps it, and one
                    # that states nothing usable keeps its exact
                    # old shape. Ondemand briefs are left alone:
                    # the depth section belongs to the
                    # morning/daily brief, not to an ad hoc
                    # window brief.
                    snapshot = _brief.with_memory_depth(
                        snapshot, now=args.now)
                    # OS-117 follow-up: the morning path fills
                    # the federation record too, so a snapshot
                    # that only carries a joined-machines list
                    # (and, when the caller states them, trust
                    # events) still carries the Federation
                    # section; a snapshot that hand-states one
                    # keeps it, and one that states fewer than
                    # two usable machines keeps its exact old
                    # shape. Ondemand briefs are left alone:
                    # the federation section belongs to the
                    # morning/daily brief, not to an ad hoc
                    # window brief.
                    snapshot = _brief.with_federation(
                        snapshot, now=args.now)
                    # INT-027 follow-up: the morning path fills
                    # the priority_order record too, so a snapshot
                    # that only carries a priority_ids list still
                    # carries the Priority order section; a snapshot
                    # that hand-states one keeps it, and one that
                    # states no usable id keeps its exact old
                    # shape. Ondemand briefs are left alone:
                    # the priority section belongs to the
                    # morning/daily brief, not to an ad hoc
                    # window brief.
                    snapshot = _brief.with_priority_order(
                        snapshot, now=args.now)
                    # INT-027 follow-up: the morning path fills
                    # the blocked_contacts record too, so a
                    # snapshot that only carries a stated
                    # blocked_contact_entries list still
                    # carries the Blocked contacts section; a
                    # snapshot that hand-states one keeps it,
                    # and one that states no usable entry keeps
                    # its exact old shape. No nick is ever read
                    # from the jobs list: a blocked job carries
                    # no owner field (jobs.py deletes the claim
                    # on block), so the ask nick comes only
                    # from the stated entries. Ondemand briefs
                    # are left alone: the contacts section
                    # belongs to the morning/daily brief, not
                    # to an ad hoc window brief.
                    snapshot = _brief.with_blocked_contacts(
                        snapshot, now=args.now)
                    # INT-027 follow-up: the morning path fills
                    # the held_decisions record too, so a snapshot
                    # that only carries a stated
                    # held_decision_entries list still carries
                    # the Held decisions section; a snapshot that
                    # hand-states one keeps it, and one that
                    # states no usable question keeps its exact old
                    # shape. No question is ever read from the jobs
                    # list: a blocked reason or a job title is not
                    # a question waiting on Dale's word, so the
                    # question comes only from the stated entries.
                    # Ondemand briefs are left alone: the held
                    # section belongs to the morning/daily brief,
                    # not to an ad hoc window brief.
                    snapshot = _brief.with_held_decisions(
                        snapshot, now=args.now)
                    # BRF-019 follow-up: the morning path fills
                    # the previous_brief record too, so a snapshot
                    # that only carries a stated
                    # previous_brief_entries list still carries
                    # the Since your last brief section; a snapshot
                    # that hand-states one keeps it, and one that
                    # states no usable id keeps its exact old
                    # shape. No previous status is ever read from
                    # the current jobs list: comparing the window
                    # against itself would report nothing changed,
                    # always. Ondemand briefs are left alone: the
                    # since-last-brief section belongs to the
                    # morning/daily brief, not to an ad hoc
                    # window brief.
                    snapshot = _brief.with_previous_brief(
                        snapshot, now=args.now)
                if args.boot:
                    # OS-049: the unit's boot path. Morning
                    # format (OS-048) with the boot flag, so
                    # the previous-session digest opens it
                    # (OS-051) and the BRF-028 guard does not
                    # hand back the previous session's brief.
                    # OS-103 follow-up: the launch path fills
                    # the environment record first, so a bare
                    # launch snapshot still carries live repo,
                    # bus, jobs, and budget lines; a snapshot
                    # that hand-states one keeps it.
                    snapshot = _brief.with_boot_environment(
                        snapshot, room=args.room, now=args.now)
                    # OS-051 follow-up: the boot path fills
                    # the previous_session record too, so a
                    # boot snapshot that states its last
                    # brief and its shutdown job list still
                    # carries the digest line; a snapshot
                    # that hand-states one keeps it, and
                    # one that states nothing usable keeps
                    # its exact old shape. Boot only: the
                    # digest belongs to the boot brief,
                    # never to a morning or ondemand brief.
                    snapshot = _brief.with_previous_session(snapshot)
                    # OS-127 follow-up: the boot path fills
                    # the recovery record too, so a boot
                    # snapshot that states the lease sweep's
                    # own outcome (recovered jobs, sweep
                    # count, corrupted jobs) still carries
                    # the one recovery line; a snapshot
                    # that hand-states one keeps it, and
                    # one that states no sweep outcome
                    # keeps its exact old shape. Boot
                    # only: the recovery line belongs to
                    # the boot brief, never to a morning
                    # or ondemand brief.
                    snapshot = _brief.with_recovery(
                        snapshot, now=args.now)
                    # OS-062 follow-up: the boot path fills
                    # the system_state record too, so a boot
                    # snapshot that states its drivers,
                    # gateway health, and skill apps as flat
                    # lists still carries the three system
                    # lines with values; a snapshot that
                    # hand-states one keeps it, and one that
                    # states nothing usable keeps its exact
                    # old shape. Boot only: the system lines
                    # belong to the boot brief, never to a
                    # morning or ondemand brief.
                    snapshot = _brief.with_system_state(
                        snapshot, now=args.now)
                    text, record = _brief.generate_brief(
                        snapshot, args.room, kind="morning",
                        since=args.since, now=args.now,
                        dry_run=args.dry_run, boot=True)
                elif args.morning and args.since is None:
                    text, record = _brief.generate_morning_brief(
                        snapshot, args.room, now=args.now,
                        dry_run=args.dry_run)
                else:
                    text, record = _brief.generate_brief(
                        snapshot, args.room,
                        kind="morning" if args.morning else "ondemand",
                        since=args.since, now=args.now,
                        dry_run=args.dry_run)
            except ValueError as exc:
                parser.error(str(exc))
            except Exception as exc:  # noqa: BLE001 - INT-009:
                # a dead store (or any engine failure) is a loud
                # RELAY_ERROR with exit 2, never a traceback:
                # the operator needs the failure named, not a
                # stack trace, when Redis is down.
                print(f"RELAY_ERROR: brief generation failed ({exc})",
                      file=sys.stderr)
                return 2
            print(text)
            print(f"brief id: {args.room}:{record['generated_at']}"
                  + (" (dry run, not stored)" if args.dry_run else ""))
            return 0
        if args.list:
            try:
                entries = _brief.list_briefs(args.room)
            except Exception as exc:  # noqa: BLE001 - INT-009,
                # same surface rule as generation above
                print(f"RELAY_ERROR: brief list failed ({exc})",
                      file=sys.stderr)
                return 2
            if not entries:
                # BRF-026: a room with no briefs at all gets the
                # canned no_data line, not empty output.
                print(_brief.brief_failure_line("no_data"))
            for entry in entries:
                print(f"{entry.get('ts')} {entry.get('kind')} "
                      f"{entry.get('generated_at')}")
            return 0
        if args.show:
            if args.ts is None:
                parser.error("--show needs --ts")
            try:
                record = _brief.get_brief(args.room, args.ts)
            except Exception as exc:  # noqa: BLE001 - INT-009,
                # same surface rule as generation above
                print(f"RELAY_ERROR: brief show failed ({exc})",
                      file=sys.stderr)
                return 2
            if record is None:
                # BRF-026: a requested brief that is not there
                # gets the canned unavailable line.
                print(_brief.brief_failure_line("unavailable"),
                      file=sys.stderr)
                return 1
            if args.announce:
                # BRF-010: the frozen line only, never a post.
                line = _brief.format_brief_announcement(record)
                if line is None:
                    print("RELAY_ERROR: stored brief cannot carry "
                          "a BRIEF: line", file=sys.stderr)
                    return 1
                print(line)
                return 0
            print(json.dumps(record, indent=2, sort_keys=True))
            return 0
        parser.error(
            "brief needs --list, --show, --morning, --ondemand, or --boot")
    if args.command == "dispatch":
        if args.show is not None:
            # DSP-016 show: no goal and no plan needed, the
            # dispatch record names the jobs. An unknown id
            # exits 2 with nothing touched; the show itself
            # reads only and writes nothing.
            from intel import dispatch as _dispatch  # noqa: E402
            try:
                report = _dispatch.show_dispatch(args.show)
            except _dispatch.ShowError as exc:
                print(f"RELAY_ERROR: dispatch show failed ({exc})",
                      file=sys.stderr)
                return 2
            except Exception as exc:  # noqa: BLE001 - INT-009:
                # a dead store under show_dispatch is a loud
                # RELAY_ERROR with exit 2, never a traceback
                print(f"RELAY_ERROR: dispatch show failed ({exc})",
                      file=sys.stderr)
                return 2
            print(_dispatch.render_dispatch_show(report))
            return 0
        if args.undo is not None:
            # DSP-011 undo: no goal and no plan needed, the
            # dispatch record names the jobs. An unknown id
            # exits 2 with nothing touched.
            from intel import dispatch as _dispatch  # noqa: E402
            try:
                report = _dispatch.undo_dispatch(args.undo)
            except _dispatch.UndoError as exc:
                print(f"RELAY_ERROR: dispatch undo failed ({exc})",
                      file=sys.stderr)
                return 2
            except Exception as exc:  # noqa: BLE001 - INT-009:
                # a dead store under undo_dispatch is a loud
                # RELAY_ERROR with exit 2, never a traceback
                print(f"RELAY_ERROR: dispatch undo failed ({exc})",
                      file=sys.stderr)
                return 2
            print(f"undone dispatch {report['id']}:")
            for entry in report["cancelled"]:
                print(f"  cancelled {entry['key']} -> {entry['id']}")
            for entry in report["untouched_claimed"]:
                print(f"  untouched claimed {entry['key']} -> "
                      f"{entry['id']} (claimed by "
                      f"{entry['claim']})")
            for entry in report["untouched_other"]:
                print(f"  untouched {entry['key']} -> {entry['id']} "
                      f"({entry['status']})")
            for entry in report["missing"]:
                print(f"  missing {entry['key']} -> {entry['id']}")
            return 0
        if args.goal is None:
            parser.error("dispatch needs --goal")
        if args.dry_run:
            if args.plan is None:
                print("RELAY_ERROR: dispatch --dry-run needs --plan "
                      "<Spark plan JSON file> (DSP-006: the draft "
                      "under review; no plan is invented from the "
                      "goal alone)", file=sys.stderr)
                return 2
            from intel import dispatch as _dispatch  # noqa: E402
            try:
                with open(args.plan) as handle:
                    text = handle.read()
                detail = _dispatch.dry_run_plan(text)
            except OSError as exc:
                print(f"RELAY_ERROR: dispatch dry-run cannot read "
                      f"--plan ({exc})", file=sys.stderr)
                return 2
            except _dispatch.PlanError as exc:
                print(f"RELAY_ERROR: dispatch dry-run plan invalid "
                      f"({exc})", file=sys.stderr)
                return 2
            print(f"goal: {args.goal}")
            print(detail)
            print("dry run: nothing posted")
            return 0
        if args.plan is None:
            print("RELAY_ERROR: dispatch posting needs --plan "
                  "<Spark plan JSON file> (DSP-007: the plan under "
                  "review; no plan is invented from the goal alone)",
                  file=sys.stderr)
            return 2
        from intel import dispatch as _dispatch  # noqa: E402
        try:
            with open(args.plan) as handle:
                text = handle.read()
            _dispatch.check_no_secrets(text)
            plan, order, _clamps = _dispatch.validated_plan(text)
        except OSError as exc:
            print(f"RELAY_ERROR: dispatch posting cannot read "
                  f"--plan ({exc})", file=sys.stderr)
            return 2
        except _dispatch.PlanError as exc:
            print(f"RELAY_ERROR: dispatch posting plan invalid "
                  f"({exc})", file=sys.stderr)
            return 2
        # DSP-007 gate: --approve, or an interactive y/yes on a
        # real tty. A non-interactive stdin never prompts and
        # never approves; it must pass --approve explicitly.
        # DSP-013 second confirmation: a large plan also needs
        # --confirm-large, or a second y/yes at the prompts.
        confirm = input if sys.stdin.isatty() else None
        if not _dispatch.request_approval(
                plan, approve=args.approve, confirm=confirm,
                confirm_large=args.confirm_large):
            if _dispatch.plan_size_warnings(plan) and args.approve:
                # First approval was present, so the missing
                # piece is exactly the second confirmation.
                print("RELAY_ERROR: dispatch posting needs a "
                      "second confirmation for a large plan: "
                      "pass --confirm-large with --approve "
                      "(nothing posted)", file=sys.stderr)
            else:
                print("RELAY_ERROR: dispatch posting needs "
                      "approval: pass --approve or answer y at "
                      "the prompt (nothing posted)",
                      file=sys.stderr)
            return 2
        # DSP-008 poster: topological order, plan keys rewritten
        # to real job ids, dispatch record stored. A failed post
        # leaves already-posted jobs posted; the error names the
        # failed job and the record is not stored.
        try:
            record = _dispatch.post_plan(plan, order=order,
                                         room=args.room,
                                         secret_file=args.secret_file,
                                         crew_mode=args.crew_mode,
                                         confirm_large=
                                         args.confirm_large)
        except _dispatch.PostError as exc:
            print(f"RELAY_ERROR: dispatch posting failed ({exc})",
                  file=sys.stderr)
            return 2
        print(f"posted dispatch {record['id']}:")
        for entry in record["jobs"]:
            print(f"  {entry['key']} -> {entry['id']}")
        if args.announce:
            line = _dispatch.format_dispatch_announcement(record)
            if line is not None:
                print(line)
        return 0
    if args.command == "watch":
        return _unimplemented("watch routing", "intel.py watch wiring")
    if args.command == "alerts":
        if not args.show and not args.ack and not args.resolve \
                and args.room is None and args.since is None \
                and args.kind is None:
            parser.error("alerts needs --show, --ack, or --resolve")
        from intel import store as _store  # noqa: E402
        if args.id is None and (args.room is not None
                                or args.since is not None
                                or args.kind is not None):
            # WDG-023 history query: filters with no --id list
            # matching records oldest first. A bare --show with
            # no filters still needs --id (the old contract).
            if args.ack or args.resolve:
                parser.error("alerts --ack/--resolve needs --id")
            since = None
            if args.since is not None:
                try:
                    since = int(args.since)
                except ValueError:
                    try:
                        import datetime as _dt  # noqa: E402
                        since = int(_dt.datetime.fromisoformat(
                            args.since).timestamp())
                    except ValueError:
                        parser.error("alerts --since must be a unix "
                                     "timestamp or ISO 8601 time")
            try:
                records = _store.query_alerts(room=args.room,
                                              since=since,
                                              kind=args.kind)
            except Exception as exc:  # noqa: BLE001 - surface, never trace
                print(f"RELAY_ERROR: alerts query failed ({exc})",
                      file=sys.stderr)
                return 2
            print(json.dumps(records, indent=2, sort_keys=True))
            return 0
        if args.id is None:
            parser.error("alerts --show/--ack/--resolve needs --id")
        if args.room is not None or args.since is not None \
                or args.kind is not None:
            parser.error("alerts filters need no --id; drop --id to query")
        try:
            if args.ack:
                record = _store.acknowledge_alert(args.id)
            elif args.resolve:
                record = _store.resolve_alert(args.id)
            else:
                record = _store.get_alert(args.id)
        except ValueError as exc:
            # WDG-014: acknowledging a resolved alert is a
            # refused transition, not a missing record.
            print(f"RELAY_ERROR: alerts lifecycle refused ({exc})",
                  file=sys.stderr)
            return 2
        except Exception as exc:  # noqa: BLE001 - surface, never trace
            print(f"RELAY_ERROR: alerts read failed ({exc})",
                  file=sys.stderr)
            return 2
        if record is None:
            print("no alert found", file=sys.stderr)
            return 1
        print(json.dumps(record, indent=2, sort_keys=True))
        return 0
    if args.command == "snapshot":
        from intel import ingest as _ingest  # noqa: E402
        try:
            snap = _ingest.snapshot(args.room)
        except Exception as exc:  # noqa: BLE001 - surface, never trace
            print(f"RELAY_ERROR: snapshot failed ({exc})",
                  file=sys.stderr)
            return 2
        print(json.dumps(snap, indent=2, sort_keys=True))
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
