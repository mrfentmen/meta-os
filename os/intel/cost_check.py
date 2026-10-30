"""INT-007: demo-day Spark cost check (PAX lane).

Runnable as ``python3 intel/cost_check.py`` from the repo root.
It makes NO Spark call, posts NOTHING to the bus, and touches no
network: every input size below is measured from files and code
already in this repo, and every price comes from the client's own
estimate rates.

Demo-day call inventory (plan/DEMO.md shot list):

- Morning brief, Shot 2: 1 brief call, kind=morning, 220-word budget.
- Dispatch plan, Shot 5: 1 plan call for the locked demo goal
  (DEM-001/DEM-025: 5 jobs). plan_from_spark retries once on
  malformed JSON, so the worst case counts 2 plan calls.
- Closing brief, Shot 11: 1 brief call, kind=morning, 220 words.
- Alert polish, Shots 8/8b (WDG-012): 1 polish call per alert
  explanation, 2 in the base demo (stall + capability refusal);
  the worst case adds Shot 10's optional collision alert, 3 total.
- Boot brief, Shot 0: 1 brief call, kind=morning, ONLY if OS-004
  rules go at the Nov 1 checkpoint. It is NOT in the headline
  total; it is shown as a separate "with boot brief" total.

Token model (the client's own, not a new one):

- Input tokens: intel.spark_client._estimate_tokens (about 4
  chars per token) applied to the exact text a call would send.
  The brief prompt is built exactly as intel.brief.compose_brief
  builds it (instruction + sections repr from the real
  extractors over a demo snapshot shaped like the demo state).
  The dispatch input is intel/prompts/dispatch.md plus the
  locked demo goal: the caller's exact assembly is not in this
  repo (plan_from_spark takes a caller-supplied complete), so
  the documented prompt file plus goal is the measured proxy,
  stated here, not hidden.
- Expected output tokens: the template brief for the same demo
  snapshot (compose_template_brief, measured, same word budget
  a Spark brief is trimmed to); a dispatch plan JSON of the
  golden shape is not measured here, so dispatch expected
  output uses the brief-style proxy of 300 tokens and is
  labeled as such; a polish output is one sentence, measured
  from the template explanation it rewrites.
- Worst-case output tokens: 1024 per call, the default
  max_tokens every call site in this repo passes to complete()
  (no call site overrides it).

Rates and the honesty limit (read this before quoting a total):

- The rates are intel.spark_client's estimate rates
  (DEFAULT_RATE_IN_PER_MTOK / DEFAULT_RATE_OUT_PER_MTOK),
  or the META_MODEL_API_*_USD_PER_MTOK env overrides when set.
  The client source labels the defaults, verbatim, "Planning
  placeholders for cost estimates only -- NOT pricing facts."
  So this check does NOT prove demo day fits the $150 credit
  as a fact. What it proves is the headroom shape: at
  placeholder rates the worst case is a tiny fraction of the
  $75 reserved half (GOV-001: $75 build/testing + $75 reserved
  for the presentation), and the breakeven multiplier says how
  many times higher real rates would have to be before the
  $75 half is breached. GOV-001 itself (which endpoint/key)
  stays unnamed and is NOT unblocked by this check.
- Primary transport note: the agent transport is primary per
  GOV-001 as amended, and the client states agent calls carry
  no API cost (est_cost is null unless the agent reports
  counts). The dollar totals below are therefore the HTTP
  fallback case: what demo day costs IF every call runs over
  HTTP. On the primary agent transport the API spend is $0
  by that rule, and the HTTP totals are the contingency.

Assertions: worst case with boot brief under $75 reserved half
and under the $150 credit; exit code 0 on pass, 1 on breach.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

from intel import brief as _brief
from intel.spark_client import (
    DEFAULT_RATE_IN_PER_MTOK,
    DEFAULT_RATE_OUT_PER_MTOK,
    _estimate_tokens,
)

CREDIT_USD = 150.0
RESERVED_HALF_USD = 75.0
WORST_OUTPUT_TOKENS = 1024
DISPATCH_EXPECTED_OUTPUT_TOKENS = 300

DEMO_GOAL = (
    "Build a small status page feature for the relay repo: an "
    "intel status module with tests, a viewer panel stub, docs "
    "for both, and a review pass -- each as separate jobs with "
    "clear file ownership."
)

DEMO_JOBS = [
    {"id": "1", "title": "intel status module", "status": "claimed",
     "claim": "milo", "claimed_at": 1000},
    {"id": "2", "title": "status module tests", "status": "claimed",
     "claim": "mute", "claimed_at": 1000},
    {"id": "3", "title": "viewer panel stub", "status": "blocked",
     "note": "waits on intel/status.py from job 1"},
    {"id": "4", "title": "docs for status module and panel",
     "status": "open"},
    {"id": "5", "title": "review pass over the status feature",
     "status": "open"},
]

DEMO_ALERTS = [
    {"id": "presence-stall:milo:1",
     "explanation": "milo claimed job 1 and has not progressed it "
                    "for 90 seconds."},
    {"id": "capability-refusal:worker:1",
     "explanation": "a crew process tried to post to the bus "
                    "without a posting grant and was refused."},
]

COLLISION_ALERT = {
    "id": "collision:plan:1",
    "explanation": "two jobs in the staged plan claim the same "
                   "file intel/status.py.",
}


def demo_snapshot():
    """Demo state: 5 jobs, 1 blocked, 2 alerts, marker messages."""
    return {
        "messages": [
            "pax: DECISION: status page goes in intel/status.py",
            "milo: DONE: stall drill seeded",
            "del: BLOCKED: viewer panel stub waits on "
            "intel/status.py",
        ],
        "jobs": [dict(job) for job in DEMO_JOBS],
        "alerts": [dict(alert) for alert in DEMO_ALERTS],
        "presence": ["pax", "del", "mute", "milo"],
    }


def brief_prompt(snapshot, kind="morning"):
    """The exact prompt compose_brief sends, built its way."""
    budget = _brief.BRIEF_BUDGETS[kind]
    sections = {
        "Decisions": _brief.extract_decisions(snapshot),
        "Blocked": _brief.extract_blocked(snapshot),
        "Owners": _brief.extract_owners(snapshot),
        "Alerts": snapshot.get("alerts") or [],
    }
    return (
        f"Write a {kind} brief from this section data only. "
        f"Do not invent facts. Keep it under {budget} words. "
        f"Sections: {sections!r}"
    )


def polish_prompt(explanation):
    """The exact prompt polish_explanation sends, built its way."""
    return (
        "Rewrite this alert explanation for clarity, in plain "
        "English, in one sentence. Do not add, remove, or "
        "change any facts, names, job ids, paths, or "
        "numbers: " + (explanation or "")
    )


def _rate(env_name, default):
    raw = os.environ.get(env_name, "").strip()
    if not raw:
        return default, "default"
    try:
        return float(raw), "env:" + env_name
    except ValueError:
        return default, "default"


def rates():
    """(in_rate, out_rate, sources) from env overrides or defaults."""
    rate_in, src_in = _rate("META_MODEL_API_INPUT_USD_PER_MTOK",
                            DEFAULT_RATE_IN_PER_MTOK)
    rate_out, src_out = _rate("META_MODEL_API_OUTPUT_USD_PER_MTOK",
                              DEFAULT_RATE_OUT_PER_MTOK)
    return rate_in, rate_out, {"in": src_in, "out": src_out}


def _cost(tokens_in, tokens_out, rate_in, rate_out):
    return round(
        tokens_in * rate_in / 1_000_000
        + tokens_out * rate_out / 1_000_000, 6)


def build_rows():
    """One row per demo-day call class, measured, no Spark call."""
    rate_in, rate_out, sources = rates()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "intel", "prompts",
                           "dispatch.md")) as handle:
        dispatch_prompt = handle.read() + "\n" + DEMO_GOAL
    snapshot = demo_snapshot()
    prompt = brief_prompt(snapshot, "morning")
    brief_in = _estimate_tokens(prompt)
    template = _brief.compose_template_brief(snapshot)
    brief_out = _estimate_tokens(template)
    polish_rows = []
    for alert in DEMO_ALERTS + [COLLISION_ALERT]:
        text = polish_prompt(alert["explanation"])
        polish_rows.append((_estimate_tokens(text),
                            _estimate_tokens(alert["explanation"])))
    rows = [
        {"call": "morning brief (Shot 2)", "count_base": 1,
         "count_worst": 1, "tokens_in": brief_in,
         "tokens_out_expected": brief_out,
         "tokens_out_worst": WORST_OUTPUT_TOKENS},
        {"call": "dispatch plan (Shot 5)", "count_base": 1,
         "count_worst": 2,
         "tokens_in": _estimate_tokens(dispatch_prompt),
         "tokens_out_expected": DISPATCH_EXPECTED_OUTPUT_TOKENS,
         "tokens_out_worst": WORST_OUTPUT_TOKENS},
        {"call": "closing brief (Shot 11)", "count_base": 1,
         "count_worst": 1, "tokens_in": brief_in,
         "tokens_out_expected": brief_out,
         "tokens_out_worst": WORST_OUTPUT_TOKENS},
        {"call": "alert polish (Shots 8/8b)", "count_base": 2,
         "count_worst": 3,
         "tokens_in": polish_rows[0][0],
         "tokens_out_expected": polish_rows[0][1],
         "tokens_out_worst": WORST_OUTPUT_TOKENS},
        {"call": "boot brief (Shot 0, OS-004 go only)",
         "count_base": 0, "count_worst": 1, "tokens_in": brief_in,
         "tokens_out_expected": brief_out,
         "tokens_out_worst": WORST_OUTPUT_TOKENS},
    ]
    for row in rows:
        row["cost_expected"] = _cost(
            row["tokens_in"] * row["count_base"],
            row["tokens_out_expected"] * row["count_base"],
            rate_in, rate_out)
        row["cost_worst"] = _cost(
            row["tokens_in"] * row["count_worst"],
            row["tokens_out_worst"] * row["count_worst"],
            rate_in, rate_out)
    return rows, rate_in, rate_out, sources


def totals(rows):
    """Headline totals; boot brief kept out of the headline."""
    core = [row for row in rows if row["count_base"] > 0]
    expected = round(sum(row["cost_expected"] for row in core), 6)
    worst = round(sum(row["cost_worst"] for row in core), 6)
    boot = [row for row in rows if row["count_base"] == 0][0]
    worst_with_boot = round(worst + boot["cost_worst"], 6)
    breakeven = (math.floor(RESERVED_HALF_USD / worst_with_boot)
                 if worst_with_boot > 0 else 0)
    return {
        "expected_usd": expected,
        "worst_usd": worst,
        "worst_with_boot_usd": worst_with_boot,
        "reserved_half_usd": RESERVED_HALF_USD,
        "credit_usd": CREDIT_USD,
        "headroom_vs_reserved_usd": round(
            RESERVED_HALF_USD - worst_with_boot, 6),
        "breakeven_multiplier_vs_reserved": breakeven,
        "passed": (worst_with_boot < RESERVED_HALF_USD
                   and worst_with_boot < CREDIT_USD),
    }


def render(rows, summary, rate_in, rate_out, sources):
    """The cost table, as text."""
    lines = [
        "INT-007 demo-day Spark cost check",
        f"rates: in ${rate_in}/Mtok ({sources['in']}), "
        f"out ${rate_out}/Mtok ({sources['out']}) -- "
        "client defaults are planning placeholders, NOT pricing "
        "facts (see module docstring)",
        "transport note: primary agent transport carries no API "
        "cost; totals below are the HTTP fallback case",
        "",
        f"{'call':38} {'base':>4} {'worst':>5} "
        f"{'tok_in':>7} {'tok_out_exp':>11} {'$exp':>9} {'$worst':>9}",
    ]
    for row in rows:
        lines.append(
            f"{row['call']:38} {row['count_base']:>4} "
            f"{row['count_worst']:>5} {row['tokens_in']:>7} "
            f"{row['tokens_out_expected']:>11} "
            f"{row['cost_expected']:>9.4f} {row['cost_worst']:>9.4f}")
    lines += [
        "",
        f"expected demo day: ${summary['expected_usd']:.4f}",
        f"worst demo day: ${summary['worst_usd']:.4f}",
        f"worst with boot brief: "
        f"${summary['worst_with_boot_usd']:.4f}",
        f"reserved half (GOV-001): "
        f"${summary['reserved_half_usd']:.2f}; headroom: "
        f"${summary['headroom_vs_reserved_usd']:.4f}",
        f"credit: ${summary['credit_usd']:.2f}; real rates "
        f"would have to exceed placeholder rates by "
        f"{summary['breakeven_multiplier_vs_reserved']}x before "
        "the reserved half is breached",
        "PASS" if summary["passed"] else "FAIL",
    ]
    return "\n".join(lines) + "\n"


def main():
    """Run the check, print the table, return the summary."""
    rows, rate_in, rate_out, sources = build_rows()
    summary = totals(rows)
    sys.stdout.write(render(rows, summary, rate_in, rate_out,
                            sources))
    if not summary["passed"]:
        return summary, 1
    return summary, 0


if __name__ == "__main__":
    _summary, _code = main()
    sys.exit(_code)
