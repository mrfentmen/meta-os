# Musica MCP server

A small keyless local MCP server for the Musica agent. It exposes
the reference corpus and the session history as tools, so an
agent searches notes and take logs instead of grepping files by
hand. Standard library only, no network calls, no credentials,
no API keys.

## Connect

Transport: stdio, JSON-RPC 2.0 with Content-Length headers
(the MCP stdio framing).

```
python3 os/worlds/musica/mcp/server.py
```

By default the server roots itself at the pack dir it lives in
(`mcp/`'s parent). Override with an env var when the pack
lives elsewhere:

```
MUSICA_ROOT=/path/to/os/worlds/musica \
  python3 os/worlds/musica/mcp/server.py
```

Corpus is read from `<root>/reference`, sessions from
`<root>/sessions`. If a tree is missing, the tool returns a
plain error naming the expected path — it never invents data.

## Tools

| Tool | Arguments | What it returns |
|---|---|---|
| `search_reference` | `query` (required), `style` (optional genre-note filter) | matching note files with one snippet line each (max 20) |
| `read_reference` | `path` (relative to the corpus root, e.g. `genres/chipsynth.md`) | the note file's full content |
| `list_sessions` | — | sessions with take and keeper counts from their take logs |
| `read_take_log` | `session` (required), `verdict` (optional: keeper/reject/pending), `limit` (default 100) | take records: id, verdict, reason, params, duration, file, seed |
| `list_keepers` | `session` (optional; all sessions when omitted) | keeper takes with session, id, file, params |

Paths are guarded: `read_reference` refuses any path that
escapes the corpus root, and session names may not contain `/`.

## Example session (framing abbreviated)

Client sends `initialize`, then `tools/list`, then calls:

```json
{"jsonrpc": "2.0", "id": 3, "method": "tools/call",
 "params": {"name": "search_reference",
            "arguments": {"query": "square", "style": "chipsynth"}}}
```

The server answers with the tool result as MCP content
(`content[0].text` holds a JSON string). Notifications from
the client get no response.

## Test it

Run the scripted stdio round-trip (staging script, not shipped):

```
python3 ~/workspace/staging/mcp-test.py
```

It starts the server against a staging overlay (corpus from
this branch, sessions from the `hana/musica` pack checkout),
sends initialize + tools/list + one call per tool, and asserts
the results — including the path-traversal refusal.

## Gateway later (not on this VM yet)

`~/workspace/mcp-gateway/` does NOT exist on this VM, so this
server is not registered with any gateway — that is a plain
fact, not a gap in the server. When a gateway exists, register
this command as a stdio server with `MUSICA_ROOT` set to the
repo's pack dir. Nothing about the server changes: still no
network, no keys, no credentials. The skill
(`~/workspace/custom-skills/musica-composer/SKILL.md`) already
teaches agents to use these tools; the gateway only changes
how the agent reaches the server, not what the server does.
