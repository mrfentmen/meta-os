// rt_identity.lobster (Lane C, R5 C9): identity gate contract.
// Rule: home_read(caller, name, rel) serves ONLY the caller's own home
// and ONLY note.txt; every other read is the string "REFUSED".
// Self-contained: uses its own fixture home, no ambient state.
// Run from lobster/: lobster runtime/rt_identity.lobster

def home_for(name):
    return "homes/rt-selftest-" + name

def home_read(caller, name, rel):
    var result = "REFUSED"
    if name == caller:
        if rel == "note.txt":
            let body = read_file(home_for(name) + "/" + rel)
            if body == nil:
                result = "MISSING"
            else:
                result = body
    return result

def run():
    write_file(home_for("a") + "/note.txt", "secret-a")
    write_file(home_for("b") + "/note.txt", "secret-b")
    var fails = 0
    if home_read("a", "a", "note.txt") != "secret-a":
        print "FAIL: own read"
        fails += 1
    if home_read("a", "b", "note.txt") != "REFUSED":
        print "FAIL: cross read not refused"
        fails += 1
    if home_read("a", "a", "../b/note.txt") != "REFUSED":
        print "FAIL: escape not refused"
        fails += 1
    if home_read("a", "a", "refusals.txt") != "REFUSED":
        print "FAIL: wrong file not refused"
        fails += 1
    if home_read("ghost", "ghost", "note.txt") != "MISSING":
        print "FAIL: missing own note should be MISSING"
        fails += 1
    delete_file(home_for("a") + "/note.txt")
    delete_file(home_for("b") + "/note.txt")
    if fails == 0:
        print "IDENTITY SELFTEST OK"
    return fails

set_exit_code(run())
