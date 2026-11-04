// rt_bus.lobster (Lane C, R5 C14): bus transport contract.
// Rule: send(channel, name, body) writes bus/<channel>/<name>; drain
// reads every message back in name order and deletes it, so a second
// drain sees an empty channel. Channel dirs live under lobster/bus/.
// Run from lobster/: lobster runtime/rt_bus.lobster

def send(channel, name, body):
    write_file("bus/" + channel + "/" + name, body)
    return name

def drain(channel):
    let names, sizes, times = scan_folder("bus/" + channel, true)
    var out = ""
    if not (names == nil):
        for (names) n:
            let body = read_file("bus/" + channel + "/" + n)
            out += "{n}={body};"
            delete_file("bus/" + channel + "/" + n)
    return out

def run():
    var fails = 0
    let ch = "rt-test"
    // start clean: whatever is there must drain away
    drain(ch)
    if drain(ch) != "":
        print "FAIL: channel not empty after drain"
        fails += 1
    send(ch, "0001.txt", "hello")
    send(ch, "0002.txt", "world")
    let got = drain(ch)
    if find_string(got, "0001.txt=hello") < 0:
        print "FAIL: msg 1 missing: {got}"
        fails += 1
    if find_string(got, "0002.txt=world") < 0:
        print "FAIL: msg 2 missing: {got}"
        fails += 1
    if drain(ch) != "":
        print "FAIL: drain did not delete"
        fails += 1
    if fails == 0:
        print "BUS SELFTEST OK"
    return fails

set_exit_code(run())
