# The appliance idea (OS-115): what Meta OS boots straight into

Borrowed from SteamOS (appliance boot) + ChromeOS (powerwash),
idea-only, no code.

For a person: power → the Meta OS banner (milestone, memory,
tasks, one line each — the K5 console banner already does this)
→ the shell prompt. No login maze, no desktop, no setup wizard
on a provisioned machine. First boot ever runs firstboot once,
then never again. Powerwash = return to the known-good
generation (OS-114) with records kept — a scared user gets one
button that cannot make things worse.

For an agent: power → the same banner as a STRUCTURED record on
serial (the `uptime Ns ticks N` line pattern already is one) →
its home, its memory, its tool list. An agent never parses a
screen; it reads the same facts in parseable form. That parity
(person sees it, agent reads it) is the rule every new surface
follows: if a fact is shown, it is also emitted structured.

What boots straight in, in one line: the shell and the agent
runtime, on the proven generation, with the records open.
