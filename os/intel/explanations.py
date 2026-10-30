"""intel/explanations.py — alert explanation templates (WDG-011, Milo).

One plain-English one-liner plus one suggested fix per detector
kind, filled from the alert's subjects (nick, job ids, shared
path, ages, attempt counts). Detectors in intel/watchdog.py
render through here instead of building their own strings, so
the wording a human reads is defined in exactly one place and
WDG-012's optional Spark polish pass has a single template
text to polish (and to fall back to when Spark fails).

Template placeholders are plain ``{name}`` fields filled by
render(); a template key is not the same as an alert kind:
file-collision has two templates (two claimed jobs, and a
claimed job against a done-but-unmerged branch) but both
produce kind "file-collision". dead-dep takes a
``blocking_note`` field that is either "" or
" Blocking reason: <note verbatim>" — the dep's note, when
it carries one, is the reason the crew sees.

render() raises ValueError for an unknown template key and
KeyError for a missing placeholder: a half-filled
explanation must never reach a human.

WDG-012's optional Spark polish pass is polish_explanation():
with no client, a raising client, or an empty Spark reply, the
template text comes back unchanged — the polish is an
optional clarity rewrite, never a replacement the alert
depends on, and it never invents facts (the prompt says so,
and the fallback keeps the template verbatim).
"""

TEMPLATES = {
    "presence-stall": {
        "explanation": (
            "{nick} holds claimed job {job} but has been "
            "absent from presence for over {stall_minutes} "
            "minutes with no progress on it for "
            "{age_minutes} minutes."),
        "suggested_fix": (
            "Check on {nick}; if the worker is gone, the "
            "lease sweep will requeue job {job} for "
            "another worker."),
    },
    "progress-stall": {
        "explanation": (
            "{nick} is present and holding claimed job "
            "{job}, but has made no progress on it for "
            "{age_minutes} minutes (over the {window_minutes}-"
            "minute window): the worker is alive, the work "
            "is stuck."),
        "suggested_fix": (
            "Check what {nick} is stuck on for job {job}; "
            "if the work is blocked, the lease sweep will "
            "requeue it for another worker."),
    },
    "lease-risk": {
        "explanation": (
            "Claimed job {job} held by {nick} has its lease "
            "expiring in {minutes_to_expiry} minute(s) with "
            "no heartbeat in the last {quiet_minutes} "
            "minutes: renew it or the lease sweep will "
            "requeue the job."),
        "suggested_fix": (
            "Have {nick} heartbeat job {job} to renew the "
            "lease, or let the sweep requeue it for "
            "another worker."),
    },
    "dead-dep": {
        "explanation": (
            "Job {job} cannot proceed: its dependency "
            "{dep} is {dep_status}.{blocking_note}"),
        "suggested_fix": (
            "Unblock or replace dependency {dep} "
            "(currently {dep_status}) so job {job} can "
            "proceed, or repost job {job} without that "
            "dependency."),
    },
    "missing-dep": {
        "explanation": (
            "Job {job} depends on job {dep}, which does "
            "not exist in the job index: the dependency "
            "was never posted, was deleted, or was "
            "mistyped."),
        "suggested_fix": (
            "Repost job {job} without dependency {dep}, "
            "or post the missing job {dep} first, then "
            "re-check job {job}."),
    },
    "file-collision": {
        "explanation": (
            "Jobs {job} and {other_job} both touch "
            "{shared_path}: two workers editing the same "
            "file will collide at merge time."),
        "suggested_fix": (
            "Coordinate jobs {job} and {other_job} before "
            "either finishes: split {shared_path} between "
            "them, or hold one job until the other "
            "merges."),
    },
    "file-collision-done": {
        "explanation": (
            "Claimed job {job} touches {shared_path}, "
            "which job {other_job} already finished on "
            "branch {branch}: the new claim risks redoing "
            "or clobbering finished work."),
        "suggested_fix": (
            "Coordinate jobs {job} and {other_job} before "
            "either finishes: split {shared_path} between "
            "them, or hold one job until the other "
            "merges."),
    },
    "attempt-warning": {
        "explanation": (
            "Job {job} has used {attempts} of "
            "{max_attempts} attempts: one attempt left "
            "before the job goes failed-final instead of "
            "requeueing."),
        "suggested_fix": (
            "Fix the blocker on job {job} now, or repost "
            "it with a larger attempt budget before the "
            "last attempt burns."),
    },
    "attempt-exhaustion": {
        "explanation": (
            "Job {job} has used {attempts} of "
            "{max_attempts} attempts: its attempt budget "
            "is spent and the job is failed-final, not "
            "requeued."),
        "suggested_fix": (
            "Do not requeue job {job} as-is: fix the "
            "blocker, then repost it with a fresh attempt "
            "budget."),
    },
    "silent-room": {
        "explanation": (
            "The room has claimed jobs ({claimed_ids}) but "
            "no messages for {age_minutes} minutes (over "
            "the {window_minutes}-minute window): the crew "
            "may be stuck, or heads-down in deep work."),
        "suggested_fix": (
            "No action required: this is informational "
            "only. If the crew is stuck, check on the "
            "claimed jobs; if they are heads-down, this "
            "record needs nothing."),
    },
    "rejected-dispatch": {
        "explanation": (
            "Job {job} was refused: its signature "
            "verdict is {verdict} (posted as {signed_by}, "
            "refused by {rejected_by}). The job stays "
            "open and unclaimed, and the refusal is the "
            "evidence, not an accusation against the "
            "refuser."),
        "suggested_fix": (
            "Do not claim job {job} without verifying "
            "its signature against the crew keyring. If "
            "the poster is legitimate, repost the job "
            "with a fresh signature; if it is not, leave "
            "the job open and tell the crew who posted "
            "it."),
    },
    "budget-warning": {
        "explanation": (
            "The {lane} lane has spent {spent} of its "
            "{cap} budget ({remaining} remaining): it is "
            "past the {warn_percent}% warning threshold, "
            "so the next claims could hit the cap and "
            "stop the lane silently."),
        "suggested_fix": (
            "Slow new {lane} claims, raise the lane cap, "
            "or let the lane finish its current work "
            "before posting more — at cap, new claims "
            "are held and the job stays open."),
    },
    "capability-refusal": {
        "explanation": (
            "{identity} tried {action} but its capability "
            "grant does not include {capability}."),
        "suggested_fix": (
            "Grant {capability} to {identity} in its "
            "capability file, or stop attempting {action}."),
    },
}

__all__ = ["TEMPLATES", "render", "polish_explanation"]


def render(template_key, **fields):
    """Fill one template; return (explanation, suggested_fix).

    Unknown template keys raise ValueError; a missing
    placeholder raises KeyError — never a half-filled string.
    """
    template = TEMPLATES.get(template_key)
    if template is None:
        raise ValueError(f"unknown explanation template: {template_key}")
    return (template["explanation"].format(**fields),
            template["suggested_fix"].format(**fields))


def polish_explanation(explanation, client=None):
    """WDG-012: optionally rewrite one explanation via Spark.

    `client` is a SparkClient (or any object with
    complete(prompt, system=..., lane_feature=...)), the same
    duck-typed seat intel/brief.py's composer uses. Toggle off
    (client None) returns the template text unchanged; a
    raising client or an empty/whitespace Spark reply also
    returns the template text unchanged — the alert never
    depends on Spark, and a failed polish is silent, not a
    missing explanation. The prompt forbids inventing facts:
    names, job ids, paths, and numbers in the template must
    survive the rewrite. The suggested fix is never polished
    here: it is an instruction, and a clarity rewrite must
    not soften it. Returns the polished text (stripped) or
    the input text.
    """
    if client is None:
        return explanation
    prompt = (
        "Rewrite this alert explanation for clarity, in plain "
        "English, in one sentence. Do not add, remove, or "
        "change any facts, names, job ids, paths, or "
        "numbers: " + (explanation or ""))
    try:
        text = client.complete(prompt, system=None,
                               lane_feature="watchdog")
    except Exception:
        return explanation
    if not text or not text.strip():
        return explanation
    return text.strip()
