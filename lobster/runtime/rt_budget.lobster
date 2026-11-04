// rt_budget.lobster (Lane C, R5 C13): budget contract.
// Rule: spend(what) decrements budget_left while > 0 and returns true;
// at zero it returns false AND appends the refusal to the refusals file.
// Run from lobster/: lobster runtime/rt_budget.lobster

let REFUSALS_FILE = "rt_state/budget_refusals.txt"

var budget_left = 2

def spend(what):
    if budget_left > 0:
        budget_left -= 1
        return true
    let old = read_file(REFUSALS_FILE)
    let line = "refused: {what}\n"
    if old == nil:
        write_file(REFUSALS_FILE, line)
    else:
        write_file(REFUSALS_FILE, old + line)
    return false

def run():
    var fails = 0
    delete_file(REFUSALS_FILE)
    if spend("call-1") != true:
        print "FAIL: call-1 refused"
        fails += 1
    if spend("call-2") != true:
        print "FAIL: call-2 refused"
        fails += 1
    if spend("call-3") != false:
        print "FAIL: call-3 allowed past cap"
        fails += 1
    let rec = read_file(REFUSALS_FILE)
    if rec == nil:
        print "FAIL: refusal not recorded"
        fails += 1
    else:
        if find_string(rec, "refused: call-3") < 0:
            print "FAIL: refusal record wrong"
            fails += 1
    delete_file(REFUSALS_FILE)
    if fails == 0:
        print "BUDGET SELFTEST OK"
    return fails

set_exit_code(run())
