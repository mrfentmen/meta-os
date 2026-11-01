# Agent memory (OS-120)

Long-term memory lives on disk at `/agents/<name>/memory`, as
plain files in stated formats (never a daemon's private binary).
Layout: `facts/` (settled truths with dates), `log/` (append-only
daily record), `scratch/` (may be dropped any time). The agent
reads its own home fully and no other agent's home at all.

What the human sees: the same files. Open the folder, read what
the agent believes, correct it by editing text. No export tool,
no dump command — the format IS the interface.
