// host.goose (OS-163): MCP host, smallest real version. Reads one
// JSON request line from stdin, answers one JSON line on stdout,
// logs every call to host.log. Tools: "list" (one tool: echo),
// "echo" (returns args.text). File-arg mode omitted: Lobster's
// launch_subprocess(cmdline, stdin) feeds stdin and captures
// stdout directly (OS-170).

import os;
import json;

fn answer_list() {
    write_stdout("{\"ok\":true,\"tools\":[\"echo\"]}\n");
    flush_stdout();
}

fn answer_echo(text: u8[:]) {
    write_stdout("{\"ok\":true,\"result\":\"");
    write_stdout(text);
    write_stdout("\"}\n");
    flush_stdout();
}

fn main() {
    loop {
        var line: u8[>..] = [];
        var doc: json::Node[>..] = [];
        var decoded: u8[>..] = [];
        guard read_line(line) else {
            break;
        }
        append_file("host.log", line);
        append_file("host.log", "\n");
        let root, err = json::parse(line, doc, decoded);
        if err.len > 0 {
            write_stdout("{\"ok\":false,\"error\":\"parse\"}\n");
            flush_stdout();
        } else {
            let tool_node = json::member(root, "tool");
            let tool, ok = json::as_string(tool_node);
            if !ok {
                write_stdout("{\"ok\":false,\"error\":\"no tool\"}\n");
                flush_stdout();
            } else if tool == "list" {
                answer_list();
            } else if tool == "echo" {
                let args = json::member(root, "args");
                let text_node = json::member(args, "text");
                let text, ok2 = json::as_string(text_node);
                if ok2 {
                    answer_echo(text);
                } else {
                    write_stdout("{\"ok\":false,\"error\":\"no text\"}\n");
                    flush_stdout();
                }
            } else {
                write_stdout("{\"ok\":false,\"error\":\"unknown tool\"}\n");
                flush_stdout();
            }
        }
    }
}
