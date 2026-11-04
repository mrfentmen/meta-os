// rt_audit.lobster (Lane C, R5 C12 + C15): audit-record contract.
// Two modes across TWO PROCESSES (restart durability, C15):
//   lobster runtime/rt_audit.lobster -- write <nonce>
//   lobster runtime/rt_audit.lobster -- verify <nonce>
// write appends one line "AUDIT <ts> lane-c <event-nonce>" to the log;
// verify reads the log back and requires that line to be present.
// A single process never sees both sides: the file is the memory.
// Run from lobster/.

let AUDIT_FILE = "rt_state/audit.log"

def run():
    let args = command_line_arguments()
    if args.length != 2:
        print "usage: rt_audit.lobster -- write|verify <nonce>"
        return 2
    let mode = args[0]
    let nonce = args[1]
    if mode == "write":
        let line = "AUDIT {date_time_string()} lane-c event-{nonce}\n"
        let old = read_file(AUDIT_FILE)
        if old == nil:
            write_file(AUDIT_FILE, line)
        else:
            write_file(AUDIT_FILE, old + line)
        print "AUDIT WROTE event-{nonce}"
        return 0
    if mode == "verify":
        let log = read_file(AUDIT_FILE)
        if log == nil:
            print "AUDIT FAIL: no log file (write phase missing?)"
            return 1
        if find_string(log, "event-{nonce}") >= 0:
            print "AUDIT DURABLE OK event-{nonce}"
            return 0
        print "AUDIT FAIL: event-{nonce} not in log"
        return 1
    print "usage: rt_audit.lobster -- write|verify <nonce>"
    return 2

set_exit_code(run())
