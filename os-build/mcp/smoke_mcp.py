#!/usr/bin/env python3
"""Smoke call an MCP server over stdio: initialize -> tools/list -> one tool call.

Section M says every wiring is proven by a call. This is the call. A config
file entry is not a wiring until this prints PASS.

Usage:
    python3 os-build/mcp/smoke_mcp.py                      # defaults to docs-rs
    python3 os-build/mcp/smoke_mcp.py npx -y @nuskey8/docs-rs-mcp@latest
    SMOKE_TOOL=docs_rs_readme SMOKE_ARGS='{"crate_name":"bootloader"}' \
        python3 os-build/mcp/smoke_mcp.py
    python3 os-build/mcp/smoke_mcp.py goose lsp             # when Goose is installed

MCP's stdio transport is newline-delimited JSON-RPC 2.0, so no framing headers
are needed. Exit code 0 means PASS, 1 means FAIL, and the FAIL line says which
stage broke: spawn, initialize, tools/list or the tool call itself.
"""
import json
import os
import subprocess
import sys
import threading

DEFAULT_CMD = ["npx", "-y", "@nuskey8/docs-rs-mcp@latest"]


def main(argv):
    cmd = argv or DEFAULT_CMD
    print("command: %s" % " ".join(cmd))

    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except FileNotFoundError as exc:
        print("VERDICT: FAIL - spawn: %s" % exc)
        return 1

    def drain_stderr():
        for line in proc.stderr:
            if line.strip():
                print("[stderr] " + line.rstrip()[:300])

    threading.Thread(target=drain_stderr, daemon=True).start()

    def send(obj):
        proc.stdin.write(json.dumps(obj) + "\n")
        proc.stdin.flush()

    def recv(want_id):
        while True:
            line = proc.stdout.readline()
            if not line:
                return None
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                print("[non-json] " + line[:200])
                continue
            if msg.get("id") == want_id:
                return msg

    send({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "meta-os-smoke", "version": "1.0"},
        },
    })
    init = recv(1)
    if init is None:
        print("VERDICT: FAIL - initialize: no response")
        return 1
    result = init.get("result", {})
    info = result.get("serverInfo", {})
    print("initialize OK: %s %s (protocol %s)"
          % (info.get("name"), info.get("version"), result.get("protocolVersion")))

    send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    listed = recv(2)
    if listed is None:
        print("VERDICT: FAIL - tools/list: no response")
        return 1
    tools = listed.get("result", {}).get("tools", [])
    print("tools (%d):" % len(tools))
    for t in tools:
        schema = t.get("inputSchema") or {}
        print("  - %s  args:%s  required:%s"
              % (t.get("name"), list(schema.get("properties") or {}),
                 schema.get("required") or []))

    tool = os.environ.get("SMOKE_TOOL")
    args = json.loads(os.environ.get("SMOKE_ARGS", "{}"))
    if not tool:
        proc.stdin.close()
        proc.terminate()
        print("VERDICT: PASS - server answered initialize and tools/list "
              "(no SMOKE_TOOL set, so no tool call was made)")
        return 0

    if not any(t.get("name") == tool for t in tools):
        print("VERDICT: FAIL - tool %r not in the server's tool list" % tool)
        return 1

    print("calling %s with %s" % (tool, json.dumps(args)))
    send({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": tool, "arguments": args},
    })
    called = recv(3)
    if called is None:
        print("VERDICT: FAIL - tool call: no response")
        return 1
    if "error" in called:
        print("tool call error: %s" % json.dumps(called["error"])[:400])
        print("VERDICT: FAIL - server up, tool call failed")
        return 1

    content = called.get("result", {}).get("content", [])
    text = content[0].get("text", "") if content else ""
    print("tool call OK: %s -> %d chars" % (tool, len(text)))
    print("  preview: %s" % text[:200].replace("\n", " "))

    proc.stdin.close()
    proc.terminate()
    print("VERDICT: PASS - initialize, tools/list and a tool call all answered")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
