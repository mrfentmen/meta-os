# Budgets (OS-126)

An agent's spend and compute limits are OS-level rules, not app
promises. Each agent carries a budget (calls, compute, money);
the layer that serves a request checks it BEFORE serving, and a
refusal is recorded like any other (the Section R drill proved
the pattern: a capped call says no and writes it down). Exhausted
means stopped, not slow — degradation curves are a lie told to
avoid saying no. Refills are explicit human acts with records.

What the human sees: per-agent meters and the one switch that
matters — the cap. No surprise bills, ever.
