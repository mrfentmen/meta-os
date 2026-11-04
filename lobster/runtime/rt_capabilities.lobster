// rt_capabilities.lobster (Lane C, R5 C11): capability contract.
// Rule: call(token_caps, cap, arg) runs ONLY if cap is in the token's
// granted list; otherwise the string "REFUSED". No ambient authority.
// Run from lobster/: lobster runtime/rt_capabilities.lobster

def granted(caps, cap):
    for (caps) c:
        if c == cap:
            return true
    return false

def call(caps, cap):
    if granted(caps, cap):
        return "OK:{cap}"
    return "REFUSED"

def run():
    var fails = 0
    let token = [ "read_note", "bus_send" ]
    if call(token, "read_note") != "OK:read_note":
        print "FAIL: granted cap refused"
        fails += 1
    if call(token, "spend") != "REFUSED":
        print "FAIL: ungranted cap allowed"
        fails += 1
    if call([ ], "read_note") != "REFUSED":
        print "FAIL: empty token allowed"
        fails += 1
    if call(token, "READ_NOTE") != "REFUSED":
        print "FAIL: case variant allowed"
        fails += 1
    if fails == 0:
        print "CAPABILITIES SELFTEST OK"
    return fails

set_exit_code(run())
