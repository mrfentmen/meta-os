# Sandboxing between agents (OS-127)

What one agent may never see: another agent's home. Enforcement
is path-shaped, not promise-shaped: the memory reader, the tool
runner, and the bus deliver only what the caller's capability set
names, and the default set names only its own home. Sharing is
an explicit grant (recorded, revocable, expiring), never ambient
read access because "we're all on the same machine". This is the
direct answer to rough edge #1 (one shared uid for everything).

What the human sees: grants — who shared what with whom, until
when — and a revoke button that works immediately.
