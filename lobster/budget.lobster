// budget.lobster (OS-175): spend enforced as a rule, not a promise.
// The spend() gate holds the cap; the 4th call is refused AND
// recorded (refusals.txt). Stated scope: script-level pattern; the
// OS-level rule arrives with the Layer 5 runtime (OS-126).

var budget_left = 3

def spend(what):
    var ok = false
    if budget_left > 0:
        budget_left -= 1
        print "spent on {what}"
        ok = true
    else:
        print "REFUSED: {what} (budget exhausted)"
    return ok

def record_refusal(what):
    write_file("homes/lobster-agent/refusals.txt", "refused: {what}")

spend("call-1")
spend("call-2")
spend("call-3")
let fourth = spend("call-4")
if fourth == false:
    record_refusal("call-4")
    print "refusal recorded"
