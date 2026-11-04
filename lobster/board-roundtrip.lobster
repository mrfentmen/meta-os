// board-roundtrip.lobster (Lane C, R5 C7): Lobster-native TCP roundtrip
// against the real board on 127.0.0.1:18935. No curl, no mocks:
// tcp.connect + tcp.send + tcp.receive speak HTTP/1.0 directly.
// JSON braces are built via unicode_to_string because {} in a string
// literal means interpolation (brace_probe.lobster fails to compile).
// Run from this directory: lobster board-roundtrip.lobster

def http_call(method, path, body):
    var sock, cerr = tcp.connect("127.0.0.1", 18935)
    if cerr or not sock:
        print "CONNECT FAILED"
        return nil
    let deadline = seconds_elapsed() + 10.0
    while true:
        if seconds_elapsed() > deadline:
            print "CONNECT TIMEOUT"
            return nil
        let ready, err = tcp.connected(sock)
        if err:
            print "CONNECT ERROR"
            return nil
        if ready: break
    var req = "{method} {path} HTTP/1.0\r\nHost: 127.0.0.1\r\nConnection: close\r\n"
    if body:
        req += "Content-Type: application/json\r\nContent-Length: {body.length}\r\n"
    req += "\r\n"
    if body:
        req += body
    var sent = 0
    while sent < req.length:
        if seconds_elapsed() > deadline:
            print "SEND TIMEOUT"
            return nil
        let n, serr = tcp.send(sock, req, sent)
        if serr:
            print "SEND ERROR"
            return nil
        sent += n
    var resp = ""
    while true:
        if seconds_elapsed() > deadline:
            print "RECV TIMEOUT"
            return nil
        let data, rerr = tcp.receive(sock, 4096)
        if rerr:
            print "RECV ERROR"
            return nil
        if data == nil:
            1
        else:
            if data.length == 0:
                break
            resp += data
    sock = nil
    return resp

let dq = unicode_to_string([ 34 ])
let lb = unicode_to_string([ 123 ])
let rb = unicode_to_string([ 125 ])
let body = lb + dq + "nick" + dq + ":" + dq + "lane-c" + dq + "," + dq + "text" + dq + ":" + dq + "lobster tcp roundtrip" + dq + rb

let post_resp = http_call("POST", "/rooms/lobster/messages", body)
var fails = 0
if post_resp == nil:
    print "BOARD ROUNDTRIP FAILED (post)"
    fails = 1
else:
    print "post head: {substring(post_resp, 0, 60)}"
    let get_resp = http_call("GET", "/rooms/lobster/messages", nil)
    if get_resp == nil:
        print "BOARD ROUNDTRIP FAILED (get)"
        fails = 1
    else:
        print "get tail: {substring(get_resp, get_resp.length - 120, 120)}"
        let ok_post = find_string(post_resp, "201") >= 0
        let ok_get = find_string(get_resp, "lane-c") >= 0
        if ok_post and ok_get:
            print "BOARD ROUNDTRIP OK"
        else:
            print "BOARD ROUNDTRIP FAILED (content)"
            fails = 1
set_exit_code(fails)
