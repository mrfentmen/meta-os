# The bus (OS-123)

Agents talk on a message bus, learned from the crew's working
relay in this repo: named channels, durable delivery, every
message timestamped and attributable. Design: channel names are
`agent:<name>` and `topic:<thing>`; delivery is at-least-once
with idempotent handlers (receivers tolerate redelivery rather
than the bus promising exactly-once); presence is a first-class
message (join/leave announced, not inferred from silence).

What the human sees: the conversation. Who said what to whom,
when — readable as text, because the bus log IS text.
