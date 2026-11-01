# Agent identity (OS-119)

An agent is a citizen with a NAME, a KEY, and a HOME. Debian has
users; we need both, because an agent is not a login — it is a
resident with continuity obligations (its memory, its jobs).

- Name: unique, human-readable, assigned once (`pax`, `milo`).
- Key: the agent's credential for the bus, tools, and records.
  Never a password; rotation is an OS operation with a record.
- Home: `/agents/<name>` — memory, config, private state. Only
  the agent and explicit grants enter (see sandboxing OS-127).

What the human sees: a roster — which agents live here, what
each one may touch, when each one's key last rotated. One screen,
no daemonology.
