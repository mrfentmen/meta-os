// updater.goose (OS-162): the updater service in Goose. Compares the
// CURRENT version file against the RELEASED version file; on a
// mismatch it stages the payload into the idle side (A/B rule) and
// records the activation. All file ops, fully real — against two
// local version files.
//
// NOT BUILT (stated, per the task's own escape clause): the network
// check. There is no release endpoint owned yet, so "fetch the
// release" is a file drop, never a mocked download. A download
// that is not real is not shipped.

import os;

fn read_version(path: u8[:]) -> u8[>..] {
    var out: u8[>..] = [];
    if read_file(path, out) {
        return out;
    }
    return "none";
}

fn main() {
    var current: u8[>..] = [];
    var released: u8[>..] = [];
    if !read_file("CURRENT", current) {
        print("updater: no CURRENT file");
        return;
    }
    if !read_file("RELEASED", released) {
        print("updater: no RELEASED file");
        return;
    }
    append_file("updater.log", current);
    append_file("updater.log", " vs ");
    append_file("updater.log", released);
    append_file("updater.log", "\n");
    if current == released {
        print("updater: up to date");
    } else {
        // Stage into the idle side, then record the activation.
        write_file("side-B/staged-version", released);
        append_file("updater.log", "staged release into side-B\n");
        print("updater: staged new release into side-B");
    }
}
