"""Musica MCP server (keyless, local only, stdio transport).

Exposes the Musica reference corpus and session history to an
agent over the standard MCP protocol, using only the Python
standard library. No network calls, no credentials, no API keys.

Tools:
  search_reference  search corpus notes by keyword (and style)
  read_reference    read one corpus note file
  list_sessions     sessions with take/keeper counts
  read_take_log     take records for a session (optional verdict)
  list_keepers      keeper takes, one session or all

Root resolution (first match wins):
  1. MUSICA_ROOT environment variable
  2. The pack dir this file lives in: <pack>/mcp/server.py
     -> root is <pack>
Corpus lives at <root>/reference, sessions at <root>/sessions.
If a tree is missing, the tool returns a plain error naming the
expected path instead of inventing data.

Run:
  python3 os/worlds/musica/mcp/server.py
  MUSICA_ROOT=/path/to/os/worlds/musica python3 server.py

Protocol: JSON-RPC 2.0 over stdio with Content-Length headers
(the MCP stdio framing). Supported: initialize, ping,
tools/list, tools/call. Notifications get no response.
"""

import glob
import json
import os
import sys

SERVER_NAME = "musica"
SERVER_VERSION = "1.0.0"
PROTOCOL_VERSION = "2024-11-05"


def pack_root():
    env = os.environ.get("MUSICA_ROOT")
    if env:
        return os.path.abspath(env)
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(here)


def corpus_root():
    return os.path.join(pack_root(), "reference")


def sessions_root():
    return os.path.join(pack_root(), "sessions")


def _read_jsonrpc():
    """Read one Content-Length-framed message. None on EOF."""
    length = None
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        line = line.strip()
        if not line:
            break
        if line.lower().startswith(b"content-length:"):
            try:
                length = int(line.split(b":", 1)[1].strip())
            except ValueError:
                return None
    if length is None:
        return None
    body = sys.stdin.buffer.read(length)
    if not body:
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None


def _send(obj):
    data = json.dumps(obj).encode("utf-8")
    sys.stdout.buffer.write(b"Content-Length: %d\r\n\r\n" % len(data))
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def _result(req_id, result):
    _send({"jsonrpc": "2.0", "id": req_id, "result": result})


def _error(req_id, code, message):
    _send({"jsonrpc": "2.0", "id": req_id,
           "error": {"code": code, "message": message}})


def _tool_error(text):
    return {"content": [{"type": "text", "text": text}], "isError": True}


def _tool_text(text):
    return {"content": [{"type": "text", "text": text}]}


TOOLS = [
    {"name": "search_reference",
     "description": "Search Musica reference notes by keyword, "
     "optionally limited to one style (a genre note name). "
     "Returns matching files with a snippet line each.",
     "inputSchema": {"type": "object",
                     "properties": {
                         "query": {"type": "string"},
                         "style": {"type": "string"}},
                     "required": ["query"]}},
    {"name": "read_reference",
     "description": "Read one reference note file by its path relative "
     "to the corpus root (e.g. genres/chipsynth.md).",
     "inputSchema": {"type": "object",
                     "properties": {"path": {"type": "string"}},
                     "required": ["path"]}},
    {"name": "list_sessions",
     "description": "List Musica sessions with take and keeper counts "
     "from their take logs.",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "read_take_log",
     "description": "Read take records for one session, optionally "
     "filtered by verdict (keeper, reject, pending).",
     "inputSchema": {"type": "object",
                     "properties": {
                         "session": {"type": "string"},
                         "verdict": {"type": "string"},
                         "limit": {"type": "integer"}},
                     "required": ["session"]}},
    {"name": "list_keepers",
     "description": "List keeper takes, for one session or all "
     "sessions when session is omitted.",
     "inputSchema": {"type": "object",
                     "properties": {"session": {"type": "string"}}}},
]


def _corpus_files():
    root = corpus_root()
    if not os.path.isdir(root):
        return None, root
    files = sorted(glob.glob(os.path.join(root, "**", "*.md"),
                             recursive=True))
    return files, root


def tool_search_reference(args):
    query = (args.get("query") or "").strip().lower()
    if not query:
        return _tool_error("query must not be empty")
    style = (args.get("style") or "").strip().lower()
    files, root = _corpus_files()
    if files is None:
        return _tool_error("corpus not found at %s" % root)
    hits = []
    for path in files:
        rel = os.path.relpath(path, root)
        if style and style not in rel.lower():
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                lines = fh.read().splitlines()
        except OSError:
            continue
        for line in lines:
            if query in line.lower():
                hits.append({"file": rel, "snippet": line.strip()})
                break
        if len(hits) >= 20:
            break
    return _tool_text(json.dumps({"matches": hits}, indent=2))


def tool_read_reference(args):
    rel = (args.get("path") or "").strip()
    if not rel:
        return _tool_error("path must not be empty")
    root = corpus_root()
    if not os.path.isdir(root):
        return _tool_error("corpus not found at %s" % root)
    target = os.path.realpath(os.path.join(root, rel))
    if os.path.commonpath([target, os.path.realpath(root)]) != \
            os.path.realpath(root):
        return _tool_error("path escapes the corpus root: %s" % rel)
    if not os.path.isfile(target):
        return _tool_error("note not found: %s" % rel)
    try:
        with open(target, encoding="utf-8") as fh:
            content = fh.read()
    except OSError as exc:
        return _tool_error("cannot read %s: %s" % (rel, exc))
    return _tool_text(json.dumps({"path": rel, "content": content},
                                 indent=2))


def _load_log(session):
    if not session or "/" in session or session in (".", ".."):
        return None, "invalid session name: %r" % session
    path = os.path.join(sessions_root(), session, "take_log.jsonl")
    if not os.path.isfile(path):
        return None, "take log not found for session %r" % session
    records = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    except (OSError, ValueError) as exc:
        return None, "cannot read take log: %s" % exc
    return records, None


def tool_list_sessions(_args):
    root = sessions_root()
    if not os.path.isdir(root):
        return _tool_error("sessions not found at %s" % root)
    out = []
    for name in sorted(os.listdir(root)):
        sdir = os.path.join(root, name)
        if not os.path.isdir(sdir):
            continue
        records, _err = _load_log(name)
        if records is None:
            continue
        keepers = sum(1 for r in records
                      if r.get("verdict") == "keeper")
        out.append({"session": name, "takes": len(records),
                    "keepers": keepers})
    return _tool_text(json.dumps({"sessions": out}, indent=2))


def _slim(record):
    return {"take_id": record.get("take_id"),
            "verdict": record.get("verdict"),
            "reason": record.get("reason", ""),
            "params": record.get("params", {}),
            "duration_s": record.get("duration_s"),
            "file": record.get("file", ""),
            "seed": record.get("seed")}


def tool_read_take_log(args):
    records, err = _load_log(args.get("session", ""))
    if records is None:
        return _tool_error(err)
    verdict = (args.get("verdict") or "").strip()
    if verdict:
        records = [r for r in records if r.get("verdict") == verdict]
    limit = args.get("limit", 100)
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 100
    records = records[:max(0, limit)]
    return _tool_text(json.dumps({"takes": [_slim(r) for r in records]},
                                 indent=2))


def tool_list_keepers(args):
    session = (args.get("session") or "").strip()
    sessions = [session] if session else None
    if sessions is None:
        root = sessions_root()
        if not os.path.isdir(root):
            return _tool_error("sessions not found at %s" % root)
        sessions = sorted(n for n in os.listdir(root)
                          if os.path.isdir(os.path.join(root, n)))
    keepers = []
    for name in sessions:
        records, err = _load_log(name)
        if records is None:
            if session:
                return _tool_error(err)
            continue
        for r in records:
            if r.get("verdict") == "keeper":
                item = _slim(r)
                item["session"] = name
                keepers.append(item)
    return _tool_text(json.dumps({"keepers": keepers}, indent=2))


DISPATCH = {
    "search_reference": tool_search_reference,
    "read_reference": tool_read_reference,
    "list_sessions": tool_list_sessions,
    "read_take_log": tool_read_take_log,
    "list_keepers": tool_list_keepers,
}


def handle(msg):
    method = msg.get("method", "")
    req_id = msg.get("id")
    if method.startswith("notifications/"):
        return
    if method == "initialize":
        _result(req_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME,
                           "version": SERVER_VERSION}})
    elif method == "ping":
        _result(req_id, {})
    elif method == "tools/list":
        _result(req_id, {"tools": TOOLS})
    elif method == "tools/call":
        params = msg.get("params", {}) or {}
        name = params.get("name", "")
        args = params.get("arguments", {}) or {}
        fn = DISPATCH.get(name)
        if fn is None:
            _error(req_id, -32602, "unknown tool: %s" % name)
        else:
            _result(req_id, fn(args))
    else:
        if req_id is not None:
            _error(req_id, -32601, "method not found: %s" % method)


def main():
    while True:
        msg = _read_jsonrpc()
        if msg is None:
            return 0
        if isinstance(msg, dict):
            handle(msg)


if __name__ == "__main__":
    sys.exit(main())
