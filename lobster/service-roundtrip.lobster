// service-roundtrip.lobster (F1, BF4-10): one Lobster program calling a merged OS
// service. The service is ../services/echo/echo.goose, run by the Goose toolchain as a
// child process; stdin is the request, stdout is the answer. No canned reply -- the
// bytes printed below are the service's own output.
//
// Run from this directory:  lobster service-roundtrip.lobster

def call_service(exe, src, input):
    let ret, out = launch_subprocess([exe, "run", src], input)
    print "service exit: {ret}"
    print "service said: {out}"
    return out

let goose = "/Users/test/mcp-servers/toolchains/goose-src/build/goose"
let answer = call_service(goose, "../services/echo/echo.goose", "hello from lobster")
if answer == nil:
    print "FAILED: no answer"
