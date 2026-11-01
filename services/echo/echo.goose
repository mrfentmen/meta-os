// echo.goose (OS-159): echo service over the dev-carrier contract.
// Reads stdin lines, writes "echo: <line>" per line. The contract
// (os-build/research/goose-ipc.md): stdio JSON-lines on the dev
// carrier today, the kernel syscall channel when K6 lands.

import os;

fn main() {
    var line: u8[>..] = [];
    loop {
        write_stdout("> ");
        flush_stdout();
        line.clear();
        guard read_line(line) else {
            break;
        }
        write_stdout("echo: ");
        write_stdout(line);
        write_stdout("\n");
        flush_stdout();
    }
}
