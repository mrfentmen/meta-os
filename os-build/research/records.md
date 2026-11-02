# Deterministic records (OS-124)

Everything an agent does is written in an append-only record a
user can audit: timestamp, actor, action, inputs hash, output
hash, result. Append-only means corrections are new entries, not
edits — the past never changes, disagreements are visible. The
record is the same one the updater (OS-114), the supervisor
(OS-157), and the budget rule (OS-126) write to: one record
format, many writers.

What the human sees: the whole day, answerable — "what did you
do, and why" resolves to entries, not explanations.
