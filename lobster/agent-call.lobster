// agent-call.lobster (OS-170): an agent script that calls one MCP
// tool from OS-163 and prints the result. The host runs as a child
// process; the request goes over its stdin, the answer comes back
// on stdout (launch_subprocess stdin support). No mocks: a real
// Goose process answers.
//
// Workaround, stated: Lobster string literals cannot contain JSON
// braces (interpolation uses {}) and \" is not an escape, so the
// requests live in req-*.json files composed by the agent's tooling
// (here: shell heredocs standing in for the composing step).

def call_tool(reqfile):
    let req = read_file(reqfile)
    let ret, out = launch_subprocess(["/Users/test/mcp-servers/toolchains/goose-src/build/goose", "run", "/tmp/os-build/services/mcp-host/host.goose"], req)
    print "host exit: {ret}"
    print "host said: {out}"
    return out

call_tool("req-list.json")
call_tool("req-echo.json")
