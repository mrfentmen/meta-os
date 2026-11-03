// sleep.goose (agent-ops B1): semantic consolidation sleep cycle.
//
// When the agent is idle this daemon reads ledger JSONL lines, scores
// each record, appends one condensed record per kept line to the out
// file, and (loop mode) sleeps until a STOP file appears. Scoring
// mirrors crates/agent-ops/src/consolidate.rs: lesson 100, failure
// 80, success 70/20, retry 30, install 5, unknown min(signal,60).
//
// Usage: goose run sleep.goose <ledger> <out> <keep_at> [stopfile]
// One pass without stopfile; loop mode with. Prints kept/dropped.

import os;
import json;

fn score_line(kind: u8[:], signal: f64) -> i64 {
    if kind == "lesson" {
        return 100;
    }
    if kind == "failure" {
        return 80;
    }
    if kind == "success" {
        if signal >= 50.0 {
            return 70;
        }
        return 20;
    }
    if kind == "retry" {
        return 30;
    }
    if kind == "install" {
        return 5;
    }
    var s: i64 = signal as i64;
    if s > 60 {
        s = 60;
    }
    return s;
}

var done_lines: i64 = 0;

fn print_int(v: i64) {
    var b: u8[>..] = [];
    json::format_int(b, v);
    write_stdout(b);
}

fn one_pass(ledger: u8[:], out: u8[:], keep_at: i64) -> i64, i64 {
    var text: u8[>..] = [];
    if !read_file(ledger, text) {
        return 0, 0;
    }
    var kept: i64 = 0;
    var dropped: i64 = 0;
    var seen: i64 = 0;
    var doc: json::Node[>..] = [];
    var decoded: u8[>..] = [];
    each_split(text, '\n') {
        var line = trim(it);
        if line.len == 0 {
        } else {
        seen += 1;
        if seen > done_lines {
        var kind: u8[>..] = [];
        append(kind, "unknown");
        var signal: f64 = 0.0;
        var body: u8[>..] = [];
        append(body, line);
        let root, err = json::parse(line, doc, decoded);
        if err.len == 0 {
            let k, ok = json::as_string(json::member(root, "kind"));
            if ok {
                kind.clear();
                append(kind, k);
            }
            let s, ok2 = json::as_f64(json::member(root, "signal"));
            if ok2 {
                signal = s;
            }
            let t, ok3 = json::as_string(json::member(root, "text"));
            if ok3 {
                body.clear();
                append(body, t);
            }
        }
        if score_line(kind, signal) >= keep_at {
            append_file(out, "{\"kept\":\"");
            append_file(out, kind);
            append_file(out, "\",\"text\":\"");
            append_file(out, body);
            append_file(out, "\"}\n");
            kept += 1;
        } else {
            dropped += 1;
        }
        }
        }
    };
    done_lines = seen;
    return kept, dropped;
}

fn main() {
    var a = args();
    if a.len < 4 {
        write_stderr("usage: sleep.goose <ledger> <out> <keep_at> [stopfile]\n");
        return;
    }
    let keep, ok = parse_int(a[3]);
    if !ok {
        write_stderr("keep_at must be an integer\n");
        return;
    }
    if a.len >= 5 {
        loop {
            let k, d = one_pass(a[1], a[2], keep);
            write_stdout("pass kept=");
            print_int(k);
            write_stdout(" dropped=");
            print_int(d);
            write_stdout("\n");
            flush_stdout();
            if file_exists(a[4]) {
                break;
            }
            sleep(1.0);
        }
    } else {
        let k, d = one_pass(a[1], a[2], keep);
        write_stdout("kept=");
        print_int(k);
        write_stdout(" dropped=");
        print_int(d);
        write_stdout("\n");
        flush_stdout();
    }
}
