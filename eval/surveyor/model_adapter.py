#!/usr/bin/env python3
"""Meta Surveyor — model-adapter guard and budget ledger.

This is the guard that sits in front of any model-backed verifier work
for Surveyor. It is NOT a model client: it ships no transport, no key,
and makes no network calls. The real transport lives Mac-side, where
del supplies the key at run time; this VM never holds the key and
never calls a model.

What the adapter enforces, in order, before any transport call:

1. Key present. Without a key the request is "unconfigured": no
   verdict, no charge, no fabricated answer. A missing key is never
   papered over with a mock verdict.
2. Transport present. The transport is injected by the caller (the
   Mac-side runner supplies the real one; tests inject a fake). With
   no transport the request is "no-transport": again no verdict, no
   charge, nothing invented.
3. Budget. Del's cap is under one dollar per run. The ledger refuses
   any request whose estimate would take spending past the cap, and
   refusal charges nothing. Rates are supplied by the operator from
   the provider's current price page at run time — this module ships
   NO vendor prices, so nothing here can go stale into a false quote.

What the adapter never does:

- It never publishes a reading. A model verdict is ADVISORY ONLY: it
  can help triage a flagged reading for role H, but publication still
  requires the spec's two-agent confirmation (an S reading plus an
  independent V check from a different device). The model never
  replaces the second sensor, and never counts as confirmation.
- It never stores audio or person data. Inputs are reading summaries
  (field, value, place, device class); anything carrying audio or a
  person is rejected before it reaches the guard.
- It never spends on a refused or unconfigured request.

Money uses Decimal, not float, so the ledger is exact to the cent.

Run the tests: python3 -m unittest discover -s eval/surveyor -p 'test_model_adapter.py'
Python 3 stdlib only. No dependencies, no network, no live model calls.
"""

from decimal import Decimal, InvalidOperation

TOKENS_PER_MILLION = Decimal(1_000_000)

# Del's cap: under one dollar per run.
DEFAULT_BUDGET_USD = Decimal("1.00")


class RejectedInput(Exception):
    """Input that must never reach a model call (audio, person data)."""


class BudgetExceeded(Exception):
    """Raised by charge() when an estimate would pass the cap."""


def check_summary_shape(summary):
    """Reject summaries that break the spec's hard rules outright."""
    if summary.get("audio") is not None:
        raise RejectedInput("summary carries audio; decibel level only")
    if summary.get("person") is not None:
        raise RejectedInput("summary carries person data; environment only")
    if summary.get("field") not in ("heat", "air", "flood", "noise"):
        raise RejectedInput("unknown field %r" % (summary.get("field"),))
    return True


def estimate_cost(prompt_tokens, completion_tokens,
                  prompt_rate_per_million, completion_rate_per_million):
    """Cost estimate in USD (Decimal) for a call of the given sizes.

    Rates are USD per million tokens, supplied by the operator. Token
    counts must be non-negative ints; rates must be non-negative.
    """
    for name, value in (("prompt_tokens", prompt_tokens),
                        ("completion_tokens", completion_tokens)):
        if not isinstance(value, int) or isinstance(value, bool) \
                or value < 0:
            raise ValueError("%s must be a non-negative int" % name)
    try:
        prompt_rate = Decimal(str(prompt_rate_per_million))
        completion_rate = Decimal(str(completion_rate_per_million))
    except InvalidOperation:
        raise ValueError("rates must be numeric")
    if prompt_rate < 0 or completion_rate < 0:
        raise ValueError("rates must be non-negative")
    return (Decimal(prompt_tokens) * prompt_rate
            + Decimal(completion_tokens) * completion_rate) \
        / TOKENS_PER_MILLION


class Budget:
    """A hard spending cap with an exact ledger."""

    def __init__(self, cap_usd=DEFAULT_BUDGET_USD):
        cap = Decimal(str(cap_usd))
        if cap < 0:
            raise ValueError("cap must be non-negative")
        self.cap = cap
        self.spent = Decimal("0")

    @property
    def remaining(self):
        return self.cap - self.spent

    def can_afford(self, estimate):
        return Decimal(estimate) <= self.remaining

    def charge(self, estimate):
        """Record a spend. Refuses (and charges nothing) past the cap."""
        estimate = Decimal(estimate)
        if estimate < 0:
            raise ValueError("estimate must be non-negative")
        if not self.can_afford(estimate):
            raise BudgetExceeded(
                "estimate %s exceeds remaining %s of cap %s"
                % (estimate, self.remaining, self.cap))
        self.spent += estimate
        return self.spent


class ModelAdapter:
    """Guard + ledger in front of an injected model transport.

    key_present: True only when the operator supplied a key at run
        time (Mac-side). This VM never sets it.
    transport: a callable(summary, prompt_tokens, completion_tokens)
        returning a verdict dict, or None when no transport exists.
        The real transport is Mac-side; tests inject a fake.
    """

    def __init__(self, budget=None,
                 prompt_rate_per_million=None,
                 completion_rate_per_million=None,
                 key_present=False, transport=None):
        if prompt_rate_per_million is None \
                or completion_rate_per_million is None:
            raise ValueError(
                "rates are required: operator sets them from the "
                "provider's current price page at run time")
        self.budget = budget if budget is not None else Budget()
        self.prompt_rate = prompt_rate_per_million
        self.completion_rate = completion_rate_per_million
        self.key_present = bool(key_present)
        self.transport = transport

    def request_verdict(self, summary, prompt_tokens, completion_tokens):
        """Ask the model about one flagged reading. Advisory only.

        Returns a dict with a status and, only on a real transport
        call, a verdict. Statuses: 'unconfigured', 'no-transport',
        'refused-over-budget', 'verdict'. No status except 'verdict'
        charges anything or claims any model output.
        """
        check_summary_shape(summary)
        if not self.key_present:
            return {"status": "unconfigured", "verdict": None,
                    "charged": Decimal("0"),
                    "note": "no key supplied; no call made, no verdict "
                            "fabricated"}
        if self.transport is None:
            return {"status": "no-transport", "verdict": None,
                    "charged": Decimal("0"),
                    "note": "no transport on this machine; live calls "
                            "are Mac-side only"}
        estimate = estimate_cost(prompt_tokens, completion_tokens,
                                 self.prompt_rate, self.completion_rate)
        if not self.budget.can_afford(estimate):
            return {"status": "refused-over-budget", "verdict": None,
                    "charged": Decimal("0"),
                    "estimate": estimate,
                    "remaining": self.budget.remaining,
                    "note": "cap %s would be exceeded; nothing charged"
                            % self.budget.cap}
        verdict = self.transport(summary, prompt_tokens, completion_tokens)
        self.budget.charge(estimate)
        return {"status": "verdict", "verdict": verdict,
                "charged": estimate,
                "remaining": self.budget.remaining,
                # The verdict never publishes anything on its own.
                "advisory_only": True, "publishes": False}
