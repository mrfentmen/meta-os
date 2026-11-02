#!/usr/bin/env python3
"""Call any MCP server named in .agents/mcp.json from the shell.

Why this exists: Section M of OPENCODE_OS_BUILD.md and BUFFY_LAYER1_TASKS.md
require every Goose/Lobster claim to be grounded in the real MCP tools, not in
memory. In a session where the MCP servers are not yet attached as tools, this
is how the grounding still happens -- it speaks stdio JSON-RPC to the same
server the client would spawn, from the same config file.

Usage:
    python3 os-build/mcp/mcp_client.py --servers
    python3 os-build/mcp/mcp_client.py goose --tools
    python3 os-build/mcp/mcp_client.py goose lookup_symbol '{"name":"print"}'
    python3 os-build/mcp/mcp_client.py goose --call overview '{}'
    python3 os-build/mcp/mcp_client.py lobster search_builtins '{"query":"string"}'

Exit code 0 on success, 1 on any failure, and the failing stage is named.
"""
import json
import os
import subprocess
import sys
import threading

CONFIG_CANDIDATES = [
    os.environ.get("MCP_CONFIG"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".agents", "mcp.json"),
    os.path.expanduser("~/.agents/mcp.json"),
]


def find_config():
    for path in CONFIG_CANDIDATES:
        if path and os.path.isfile(path):
            return os.path.abspath(path)
    return None


def load_servers(path):
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data.get("mcpServers", {})


class Stdio:
    def __init__(self, spec):
        cmd = [spec["command"]] + [str(a) for a in spec.get("args", [])]
        env = dict(os.environ)
        env.update(spec.get("env") or {})
        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
        )
        self.next_id = 1
        self.lock = threading.Lock()

    def send(self, method, params=None):
        with self.lock:
            msg_id = self.next_id
            self.next_id += 1
            payload = {"jsonrpc": "2.0", "id": msg_id, "method": method}
            if params is not None:
                payload["params"] = params
            self.proc.stdin.write(json.dumps(payload) + "\n")
            self.proc.stdin.flush()
            while True:
                line = self.proc.stdout.readline()
                if not line:
                    err = self.proc.stderr.read()[:600] if self.proc.stderr else ""
                    raise RuntimeError("server closed the pipe. stderr: %s" % err)
                line = line.strip()
                if not line:
                    continue
                try:
                    reply = json.loads(line)
                except ValueError:
                    continue  # not JSON-RPC, e.g. a stray log line
                if reply.get("id") == msg_id:
                    if "error" in reply:
                        raise RuntimeError("server error: %s" % reply["error"])
                    return reply.get("result", {})

    def notify(self, method, params=None):
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        with self.lock:
            self.proc.stdin.write(json.dumps(payload) + "\n")
            self.proc.stdin.flush()

    def close(self):
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass


def text_of(result):
    parts = []
    for item in result.get("content", []) or []:
        if isinstance(item, dict) and item.get("type") == "text":
            parts.append(item.get("text", ""))
        elif isinstance(item, dict):
            parts.append(json.dumps(item))
    if not parts and "structuredContent" in result:
        parts.append(json.dumps(result["structuredContent"]))
    return "\n".join(parts)


def open_server(name, servers):
    if name not in servers:
        print("FAIL: no server named %r in config. known: %s" % (name, ", ".join(sorted(servers))))
        sys.exit(1)
    client = Stdio(servers[name])
    client.send("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "buffy-mcp-client", "version": "1.0"},
    })
    client.notify("notifications/initialized")
    return client


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    path = find_config()
    if not path:
        print("FAIL: no .agents/mcp.json found in %s" % CONFIG_CANDIDATES)
        return 1
    servers = load_servers(path)

    if argv[0] == "--servers":
        print("config: %s" % path)
        for name in sorted(servers):
            spec = servers[name]
            print("  %-20s %s %s" % (name, spec.get("command"), " ".join(str(a) for a in spec.get("args", []))))
        return 0

    name = argv[0]
    rest = argv[1:]
    if not rest:
        print("FAIL: give --tools or a tool name")
        return 1

    client = open_server(name, servers)
    try:
        if rest[0] == "--tools":
            result = client.send("tools/list")
            for tool in result.get("tools", []):
                schema = tool.get("inputSchema", {}) or {}
                required = schema.get("required", [])
                print("%-24s %s" % (tool.get("name"), ("required: " + ",".join(required)) if required else ""))
                desc = (tool.get("description") or "").strip().split("\n")[0]
                if desc:
                    print("    %s" % desc[:160])
            return 0

        call = rest[0]
        if call == "--call":
            if len(rest) < 2:
                print("FAIL: --call needs a tool name")
                return 1
            call = rest[1]
            raw = rest[2] if len(rest) > 2 else "{}"
        else:
            raw = rest[1] if len(rest) > 1 else "{}"

        try:
            args = json.loads(raw)
        except ValueError:
            print("FAIL: arguments must be JSON, got %r" % raw)
            return 1

        result = client.send("tools/call", {"name": call, "arguments": args})
        body = text_of(result)
        print(body)
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as exc:  # noqa: BLE001 - the message is the report
        print("FAIL: %s" % exc)
        sys.exit(1)
