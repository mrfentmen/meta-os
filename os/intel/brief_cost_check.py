#!/usr/bin/env python3
"""BRF-027: brief generation cost on a busy fixture, inside the cap.

Runnable as ``python3 intel/brief_cost_check.py`` from the repo root.
It makes NO Spark call, posts NOTHING to the bus, and touches no
network: every input size below is measured from the real
extractors over a hand-written busy snapshot in the BRF-017 shape
(22 jobs: 10 claimed, 6 open, 3 blocked, 3 done; 6 owners;
4 marker messages; 2 alerts), and every price comes from the
client's own estimate rates, via INT-007's builders.

What is measured, and what each number is:

- Template actual: the brief the repo can actually generate
  today, via compose_brief with no Spark client (BRF-008
  template fallback). It makes no Spark call, so its actual
  spend is $0 and its brief record carries spend_id null
  (FND-032). That is the run's real spend.
- Spark estimate: what the same brief WOULD cost as one
  Spark call over HTTP. The prompt is built exactly as
  compose_brief builds it (INT-007's brief_prompt, same
  sections repr); expected output is the template brief for
  the same snapshot, trimmed to the morning budget (the
  same word budget a Spark brief is trimmed to); worst-case
  output is 1024 tokens, the default max_tokens every call
  site passes. Two variants are measured: the scored
  2-word-title busy snapshot (BRF-017, 186 words) and the
  long-title stress variant from the same BRF-017 trial
  shape (9-word titles; the trial's untrimmed template ran
  over the budget, and this variant's raw template runs
  401 words before the compose_brief trim brings it to
  218), because the budget pass depends on title length.
- The cap: there is no per-brief spend cap constant in
  this repo (Milo's OS-085 budget config has not landed),
  so the check uses the only stated money caps: the $150
  credit and the $75 reserved half (GOV-001, same constants
  as INT-007). A single busy brief must stay under both,
  expected and worst case, in both variants.

Honesty limits (read before quoting a total):

- The rates are intel.spark_client's estimate rates. The
  client source labels the defaults, verbatim, "Planning
  placeholders for cost estimates only -- NOT pricing
  facts." So this check does NOT prove a live brief costs
  this much. What it proves is the headroom shape: at
  placeholder rates even the worst case is a tiny fraction
  of the reserved half, and the breakeven multiplier says
  how many times higher real rates would have to be before
  the reserved half is breached by one busy brief.
- On the primary agent transport the API spend is $0 by
  the client's own rule (agent calls carry no API cost;
  est_cost is null unless the agent reports counts). The
  dollar totals below are therefore the HTTP fallback
  case: what a busy brief costs IF it runs over HTTP.
- No spend-ledger entry is written by this script. The
  ledger records actual Spark spend (FND-007); this run
  made no Spark call, so there is no actual to record,
  and writing an estimate into the ledger as if it were
  spend would misstate it. The numbers live in this
  script's output and in the BRF-027 eval log entry, not
  in the ledger. A live Spark brief's ledger entry is
  still owed when real Spark transport lands (GOV-001
  stays unnamed), and it must then be re-checked
  against the same caps.
- This scores a template brief's expected output, not a
  Spark-composed brief, and not a brief on Buffy's busy
  fixture (FND-023, not in this repo yet). Both re-checks
  are still owed when they land.

Assertions: worst case under $75 reserved half and under
the $150 credit, in both variants; exit code 0 on pass,
1 on breach.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

from intel import brief as _brief
from intel.cost_check import (CREDIT_USD, RESERVED_HALF_USD,
                              WORST_OUTPUT_TOKENS, brief_prompt,
                              rates)
from intel.spark_client import _estimate_tokens

# Claimed jobs per owner, matching the BRF-017 manifest:
# milo 2, rowan 2, buffy 2, del 2, hana 1, pax 1 = 10 claimed.
_CLAIMS = [("milo", "brief panel"), ("milo", "dispatch poster"),
            ("rowan", "watchdog drill"), ("rowan", "viewer stub"),
            ("buffy", "cost table"), ("buffy", "alert polish"),
            ("del", "job sweep"), ("del", "plan preview"),
            ("hana", "crew board"), ("pax", "status page")]
_OPEN = ["demo script", "help text", "panel stub",
         "queue view", "lease sweep", "board chips"]
_BLOCKED = [("waiting on the real Spark endpoint",
             "spark client"),
            ("waiting on the test image", "boot service"),
            ("waiting on the busy fixture", "eval rerun")]
_DONE = ["morning schedule", "failure copy", "owners list"]


def busy_snapshot(long_titles=False):
    """BRF-017-shape busy snapshot; long_titles=True is the
    9-word-title stress variant from the BRF-017 trial."""
    def title(base):
        if not long_titles:
            return base
        return base + " with a long descriptive title here now"
    jobs = []
    for i, (nick, base) in enumerate(_CLAIMS):
        jobs.append({"id": str(i + 1), "title": title(base),
                     "status": "claimed", "claim": nick,
                     "claimed_at": 1000})
    for j, base in enumerate(_OPEN):
        jobs.append({"id": str(11 + j), "title": title(base),
                     "status": "open"})
    for k, (note, base) in enumerate(_BLOCKED):
        jobs.append({"id": str(17 + k), "title": title(base),
                     "status": "blocked", "note": note})
    for k, base in enumerate(_DONE):
        jobs.append({"id": str(20 + k), "title": title(base),
                     "status": "done"})
    return {
        "messages": [
            {"nick": "pax",
             "text": "DECISION: ship the brief panel first"},
            {"nick": "milo",
             "text": "DECISION: keep the 2s core poll"},
            {"nick": "del", "text": "DONE: morning schedule shipped"},
            {"nick": "rowan",
             "text": "BLOCKED: boot service waits on the test image"},
        ],
        "jobs": jobs,
        "alerts": [{"id": "ALERT-1", "summary": "stall on job 2"},
                   {"id": "ALERT-2", "summary": "stall on job 7"}],
        "presence": ["pax", "del", "mute", "milo", "rowan", "buffy"],
        "source_window": "2026-10-27 08:00 ET onward, last 24 hours",
    }


def _cost(tokens_in, tokens_out, rate_in, rate_out):
    return round(tokens_in * rate_in / 1_000_000
                 + tokens_out * rate_out / 1_000_000, 6)


def measure(long_titles=False):
    """One row: template actual ($0) plus Spark-call estimate
    (expected and worst case) for one busy variant."""
    rate_in, rate_out, sources = rates()
    snapshot = busy_snapshot(long_titles=long_titles)
    prompt = brief_prompt(snapshot, "morning")
    tokens_in = _estimate_tokens(prompt)
    # Expected Spark output: the template brief for the same
    # snapshot, trimmed to the morning budget by compose_brief
    # with no client, the same trim a Spark brief gets.
    template = _brief.compose_brief(snapshot, kind="morning")
    tokens_out = _estimate_tokens(template)
    return {
        "variant": ("long-title stress" if long_titles
                    else "scored 2-word titles"),
        "jobs": len(snapshot["jobs"]),
        "template_words": len(template.split()),
        "template_actual_usd": 0.0,
        "tokens_in": tokens_in,
        "tokens_out_expected": tokens_out,
        "tokens_out_worst": WORST_OUTPUT_TOKENS,
        "cost_expected": _cost(tokens_in, tokens_out,
                               rate_in, rate_out),
        "cost_worst": _cost(tokens_in, WORST_OUTPUT_TOKENS,
                            rate_in, rate_out),
        "rate_sources": sources,
    }, rate_in, rate_out


def build_rows():
    """Both variants, measured, no Spark call."""
    rows = []
    rate_in = rate_out = None
    for long_titles in (False, True):
        row, rate_in, rate_out = measure(long_titles=long_titles)
        rows.append(row)
    return rows, rate_in, rate_out


def render(rows, rate_in, rate_out):
    """The cost table, as text."""
    sources = rows[0]["rate_sources"]
    worst = max(row["cost_worst"] for row in rows)
    breakeven = (math.floor(RESERVED_HALF_USD / worst)
                 if worst > 0 else 0)
    passed = all(row["cost_worst"] < RESERVED_HALF_USD
                 and row["cost_worst"] < CREDIT_USD for row in rows)
    lines = [
        "BRF-027 busy-fixture brief cost check",
        f"rates: in ${rate_in}/Mtok ({sources['in']}), "
        f"out ${rate_out}/Mtok ({sources['out']}) -- "
        "client defaults are planning placeholders, NOT pricing "
        "facts (see module docstring)",
        "transport note: primary agent transport carries no API "
        "cost; totals below are the HTTP fallback case",
        "ledger note: no ledger entry written -- this run made "
        "no Spark call, so there is no actual spend to record",
        "",
        f"{'variant':22} {'jobs':>4} {'tmpl_words':>10} "
        f"{'tok_in':>7} {'tok_out_exp':>11} {'$exp':>9} {'$worst':>9}",
    ]
    for row in rows:
        lines.append(
            f"{row['variant']:22} {row['jobs']:>4} "
            f"{row['template_words']:>10} {row['tokens_in']:>7} "
            f"{row['tokens_out_expected']:>11} "
            f"{row['cost_expected']:>9.4f} {row['cost_worst']:>9.4f}")
    lines += [
        "",
        "template actual (both variants): $0.0000 "
        "(no Spark call, spend_id null)",
        f"worst single busy brief: ${worst:.4f}",
        f"reserved half (GOV-001): ${RESERVED_HALF_USD:.2f}; "
        f"credit: ${CREDIT_USD:.2f}; real rates would have to "
        f"exceed placeholder rates by {breakeven}x before one "
        f"busy brief breaches the reserved half",
        "PASS" if passed else "FAIL",
    ]
    return "\n".join(lines) + "\n", passed


def main():
    """Run the check, print the table, return the summary."""
    rows, rate_in, rate_out = build_rows()
    text, passed = render(rows, rate_in, rate_out)
    sys.stdout.write(text)
    summary = {"rows": rows, "passed": passed}
    return summary, 0 if passed else 1


if __name__ == "__main__":
    _summary, _code = main()
    sys.exit(_code)
