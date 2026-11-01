// scheduled.lobster (OS-174): a scheduled agent. Wakes on a timer
// (seconds_elapsed busy-wait — the interpreter has no sleep call,
// stated workaround), does the memory read, sleeps again. One full
// cycle logged; the runner kills it after (patience is finite).

def wait_until(t):
    while seconds_elapsed() < t:
        1

let mem = read_file("homes/lobster-agent/note.txt")
print "wake 1: memory says: {mem}"
wait_until(seconds_elapsed() + 2.0)
let mem2 = read_file("homes/lobster-agent/note.txt")
print "wake 2 (+2s): memory says: {mem2}"
