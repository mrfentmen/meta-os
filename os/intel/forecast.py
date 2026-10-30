"""intel/forecast.py — budget forecasting + preemption (OS-091, Milo).

Phase B task built on the OS-085 gate: the watchdog can see a
breach coming hours ahead instead of reporting it after the
silence, and it can pause (never kill) a low-priority spender
approaching a cap so the lane survives until budget frees.

Forecasting is one division, stated openly: the ledger rate so
far (spent over elapsed hours of the day) projected to the end
of a 24-hour day. Projected spend = spent * day_hours /
elapsed_hours. A forecast is only as good as the ledger behind
it, so every forecast carries its confidence basis in plain
words: the elapsed hours the rate comes from, and a confidence
word derived from them alone — low under 4 hours, medium from
4 to under 12, high at 12 or more. Nothing else feeds the
confidence: no lane history, no day-of-week guess, no Spark
judgment. A forecast with under an hour of ledger, or with no
usable spent/cap figures, is not made at all — the entry
returns None and the brief line for that lane is skipped,
never a guessed number.

Preemption is pause, not kill, and only for low-priority
work: a running job whose priority is exactly "low", in a lane
currently at warning (the OS-085 band, spent at threshold but
below cap), is paused — its progress field is untouched, so
resuming it later repeats no work. A high-priority job in the
same lane is never preempted, and a job already paused is
never preempted twice. Resumption is the mirror: a paused job
whose lane has dropped back below the warning threshold
(budget freed — a new period, a raised cap, spend corrected)
resumes to running with its progress exactly as it was. At
cap the lane's new claims are already held by the OS-085
gate; preemption is about the work already running, so the
decision is taken in the warning band, not after the hold.

Everything here is judgment over caller-supplied figures:
this module never reads a live ledger, never pauses a live
worker, and never posts to the bus. The drill
(intel/drills/budget_forecast.py) proves the decisions on a
fake queue with the same shapes; wiring a preempt decision
into a real worker pause, and a forecast line into a daily
brief actually run by the brief pipeline, are owed on those
callers and are named as NOT proven in the OS-091 eval doc.
The brief lines this module renders (forecast_lines) are
plain lines, not bullets, so the BRF-007 trim keeps them
like the OS-079 budget lines.
"""

__all__ = ["project_end_of_day", "confidence_for", "forecast_entry",
           "forecast_lines", "preempt_decision", "preempt_record"]

DAY_HOURS = 24
LOW_CONFIDENCE_BELOW = 4
HIGH_CONFIDENCE_AT = 12


def _usable_number(value):
    return (isinstance(value, (int, float))
            and not isinstance(value, bool))


def project_end_of_day(spent, elapsed_hours, day_hours=DAY_HOURS):
    """Projected end-of-day spend, or None when unprojectable.

    Unprojectable means: spent is negative or not a number,
    elapsed_hours is not positive, or day_hours is not
    positive. Elapsed hours at or past the full day project
    to spent itself — the day is already over, no rate to
    extend. The result is a float; callers round for display.
    """
    if not _usable_number(spent) or spent < 0:
        return None
    if not _usable_number(elapsed_hours) or elapsed_hours <= 0:
        return None
    if not _usable_number(day_hours) or day_hours <= 0:
        return None
    if elapsed_hours >= day_hours:
        return float(spent)
    return float(spent) * day_hours / elapsed_hours


def confidence_for(elapsed_hours):
    """The confidence word for a forecast, from elapsed hours alone.

    Low under 4 hours, medium from 4 to under 12, high at 12
    or more. Unusable elapsed hours give "unknown", and no
    forecast is made from them — the word is never attached
    to a number it did not come from.
    """
    if not _usable_number(elapsed_hours) or elapsed_hours <= 0:
        return "unknown"
    if elapsed_hours < LOW_CONFIDENCE_BELOW:
        return "low"
    if elapsed_hours < HIGH_CONFIDENCE_AT:
        return "medium"
    return "high"


def forecast_entry(lane, spent, cap, elapsed_hours,
                   day_hours=DAY_HOURS):
    """One lane's forecast, or None when it cannot be made.

    The entry carries lane, spent, cap, projected end-of-day
    spend (float), over_cap (projected past cap), confidence,
    and basis — the basis sentence naming the elapsed hours
    the rate comes from, so the brief line can state it
    verbatim instead of asking the reader to trust a number.
    A lane with no usable cap, or with unprojectable spend,
    yields None: an absent budget is not a zero budget, and
    a forecast from no ledger is a guess.
    """
    if not (isinstance(lane, str) and lane):
        return None
    if not _usable_number(cap) or cap <= 0:
        return None
    if not _usable_number(spent) or spent < 0:
        return None
    projected = project_end_of_day(spent, elapsed_hours, day_hours)
    if projected is None:
        return None
    confidence = confidence_for(elapsed_hours)
    return {
        "lane": lane,
        "spent": spent,
        "cap": cap,
        "projected": projected,
        "over_cap": projected > cap,
        "confidence": confidence,
        "basis": ("based on %s hours of ledger in a %s-hour day"
                  % (_format_hours(elapsed_hours), _format_hours(day_hours))),
    }


def _format_hours(value):
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def forecast_lines(entries):
    """Plain brief lines for a list of forecast entries.

    Each usable entry yields one line: lane, spent, cap,
    projected end-of-day spend (rounded down to a whole
    number — a forecast is an estimate, and rounding up
    would overstate it), the basis sentence, and the
    confidence word, plus "breach expected before end of
    day" when the projection passes the cap, or "within
    cap" when it does not. Unusable entries are skipped,
    never guessed; an empty input yields no lines, so a
    brief with no ledger carries no forecast section at all
    instead of a made-up one. Lines are not bullets, so
    the BRF-007 trim never drops them ahead of a watch item.
    """
    lines = []
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        forecast = forecast_entry(entry.get("lane"), entry.get("spent"),
                                  entry.get("cap"),
                                  entry.get("elapsed_hours"),
                                  entry.get("day_hours", DAY_HOURS))
        if forecast is None:
            continue
        projected = int(forecast["projected"])
        verdict = ("breach expected before end of day"
                   if forecast["over_cap"] else "within cap")
        lines.append(
            "Budget forecast for lane %s: %s spent of %s cap, "
            "projected %s by end of day, %s (%s confidence) - %s."
            % (forecast["lane"], forecast["spent"], forecast["cap"],
               projected, forecast["basis"], forecast["confidence"],
               verdict))
    return lines


def preempt_decision(job, lane_state):
    """"pause", "resume", or None for one job in one lane state.

    `job` is a dict with "priority" and "status" ("running"
    or "paused"); `lane_state` is one of the OS-085 budget
    states ("warning", "capped", "ok", "unbudgeted"). Pause
    only when the job is running, low priority, and the lane
    is at warning — approaching the cap, not past it, and
    not a lane with no budget at all. Resume only when the
    job is paused and the lane is back below warning ("ok"
    or "unbudgeted": budget freed or the budget gone). At
    cap, running work is left alone by this decision — the
    gate already holds new claims, and killing or pausing
    running work at cap is a separate call this module does
    not make. Anything else — high priority, already paused
    (for pause), running (for resume), malformed job — yields
    None, never a guessed action.
    """
    if not isinstance(job, dict):
        return None
    status = job.get("status")
    priority = job.get("priority")
    if status == "running" and priority == "low" \
            and lane_state == "warning":
        return "pause"
    if status == "paused" and lane_state in ("ok", "unbudgeted"):
        return "resume"
    return None


def preempt_record(job_id, lane, action, reason):
    """A journal record for a pause or resume, nothing more.

    The record names the job, the lane, the action ("paused"
    or "resumed"), and the reason in plain words — the
    journal entry the next brief can quote. It performs no
    pause and no resume; the caller applies the decision and
    files this record beside it.
    """
    return {"job": job_id, "lane": lane, "action": action,
            "reason": reason}
