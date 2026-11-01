// memory.lobster (OS-172): write a note, exit, run again, read it
// back. Two invocations = persistence proof (the log shows both).

let mem = "homes/lobster-agent/note.txt"
let old = read_file(mem)
if old == nil:
    print "first run: writing note"
    write_file(mem, "remember: K6 booted before breakfast")
else:
    print "second run: note reads back: {old}"
