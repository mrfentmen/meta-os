// heartbeat.goose (OS-156): the smallest real Goose daemon. Appends
// one timestamped line per second, exits cleanly when the STOP file
// appears (no signal API in the stdlib — sentinel-file stop is the
// documented workaround, OS-166).

import os;

fn main() {
    var n = 0;
    while n < 3600 {
        if file_exists("STOP") {
            break;
        }
        append_file("heartbeat.log", "beat");
        n = n + 1;
        sleep(1.0);
    }
    print("daemon stopping cleanly");
}
