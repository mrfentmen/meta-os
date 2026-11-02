# Attention (OS-125)

How the OS wakes an agent (events, timers, messages) and how it
lets one sleep. Rule: nothing polls. An agent sleeps until the
bus delivers a message matching its subscriptions, a timer fires,
or an event it registered for occurs. Wake carries the reason —
the agent never wakes to ask "why am I up". Idle agents cost
nothing but their home directory.

What the human sees: a sleeping house that answers instantly —
plus the wake log, so a chatty 3 AM agent is visible, not just
expensive.
