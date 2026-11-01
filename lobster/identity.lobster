// identity.lobster (OS-171): an agent knows its name, reads its own
// home, and no other agent's home. Enforcement point: home_read()
// serves only the whitelisted path under the caller's own home.
// Stated limit: convention + review at script scope; OS-enforced
// homes arrive with the Layer 5 runtime.

def home_for(name):
    return "homes/" + name

def home_read(caller, name, rel):
    var result = "REFUSED"
    if name == caller:
        if rel == "note.txt":
            result = read_file(home_for(name) + "/" + rel) or "MISSING"
    return result

let me = "lobster-agent"
let own = home_read(me, me, "note.txt")
print "I am {me}, own home note: {own}"
let cross = home_read(me, "other-agent", "note.txt")
print "other home attempt: {cross}"
let esc = home_read(me, me, "../other-agent/note.txt")
print "escape attempt: {esc}"
