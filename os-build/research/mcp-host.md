# MCP host (OS-122)

The OS speaks MCP natively. The host lives in the Goose services
layer (OS-163 builds the smallest real one): it starts, lists
one tool, answers one call, all logged. Tools are processes the
host supervises, not libraries it links — a crashing tool cannot
take the host down. Every call and every refusal lands in the
deterministic record (OS-124).

What the human sees: which tools are up, which calls happened,
which failed — one live view, no log archaeology.
