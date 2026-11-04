// rt_lifecycle.lobster (Lane C, R5 C10): lifecycle contract.
// States: BORN -> RUNNING -> STOPPED (terminal). Any other edge is
// refused. Current state persists in a file so a restart re-reads it.
// Run from lobster/: lobster runtime/rt_lifecycle.lobster

let STATE_FILE = "rt_state/lifecycle_agent.state"

def read_state():
    let s = read_file(STATE_FILE)
    if s == nil:
        return "NONE"
    return s

def transition(frm, to):
    if frm == "NONE" and to == "BORN":
        return "BORN"
    if frm == "BORN" and to == "RUNNING":
        return "RUNNING"
    if frm == "RUNNING" and to == "STOPPED":
        return "STOPPED"
    return "REFUSED"

def run():
    var fails = 0
    delete_file(STATE_FILE)
    if read_state() != "NONE":
        print "FAIL: fresh state should be NONE"
        fails += 1
    var st = transition(read_state(), "BORN")
    if st == "REFUSED":
        print "FAIL: NONE->BORN refused"
        fails += 1
    write_file(STATE_FILE, st)
    if read_state() != "BORN":
        print "FAIL: state file should read BORN"
        fails += 1
    if transition("BORN", "STOPPED") != "REFUSED":
        print "FAIL: BORN->STOPPED must be refused"
        fails += 1
    st = transition(read_state(), "RUNNING")
    write_file(STATE_FILE, st)
    if transition("STOPPED", "RUNNING") != "REFUSED":
        print "FAIL: STOPPED->RUNNING must be refused"
        fails += 1
    st = transition(read_state(), "STOPPED")
    write_file(STATE_FILE, st)
    if read_state() != "STOPPED":
        print "FAIL: state file should read STOPPED"
        fails += 1
    delete_file(STATE_FILE)
    if fails == 0:
        print "LIFECYCLE SELFTEST OK"
    return fails

set_exit_code(run())
