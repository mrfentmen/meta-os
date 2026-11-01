// --- recv side: drain the channel, print each message
let names, sizes, times = scan_folder("bus/general", true)
if names == nil:
    print "channel empty"
else:
    for (names) n:
        let body = read_file("bus/general/" + n)
        print "got {n}: {body}"
        delete_file("bus/general/" + n)
