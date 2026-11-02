// shim.lobster (OS-176): the first PROGRAM shim — a real repo
// program (the OS build scoreboard) driven from Lobster end to end:
// read, excerpt, print. No mocks: the file is the repo's own.

var board = read_file("../os-build/SCOREBOARD.md")
if board == nil:
    // running from a different CWD: try the worktree path
    board = read_file("/tmp/os-build/os-build/SCOREBOARD.md")
if board == nil:
    print "scoreboard not found (run from /tmp/os-build/lobster)"
else:
    print "--- scoreboard head ---"
    print substring(board, 0, 400)
