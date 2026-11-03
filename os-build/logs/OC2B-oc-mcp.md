# OC2B-154/155 — MCP wiring + LAYERS test (this lane, 2026-11-02)

- Guest config `~/.config/opencode/opencode.jsonc` (shape only, secrets redacted — full host config carries real keys and is NEVER copied):
  `$schema` + `mcp.research` → `["python3", "/home/relay/bake/research_mcp.py"]`, timeout 120000. (research_mcp.py placeholder path — stub, not a live server.)
- LAYERS summary test (OC2B-155): `opencode run -m opencode/space-bunny-free "Summarize os-build/LAYERS.md in three sentences"` → same endpoint `UnknownError ... ref err_a716ff93`. No summary produced. BLOCKED on model endpoint, not on wiring. Recorded, one attempt, no retry.
