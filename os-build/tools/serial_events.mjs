#!/usr/bin/env node
// CB-091/092 — serial log to structured events. A panic anywhere makes
// the whole result PANIC; it is printed before the event list.
import fs from "node:fs";

const ANSI = /\x1b\[[0-9;?]*[A-Za-z]/g;

export function parseSerial(text) {
  const events = [];
  let banner = null;
  let panic = false;
  for (const raw of text.split(/\r?\n/)) {
    const line = raw.replace(ANSI, "").trim();
    if (!line) continue;
    let m = line.match(/META OS .*?\(K\d\)/);
    if (m) { banner = m[0]; events.push({ type: "banner", banner: m[0], line }); }
    if (/META OS KERNEL - alive/.test(line)) events.push({ type: "alive", line });
    if (/HELLO FROM USERSPACE/.test(line)) events.push({ type: "hello", line });
    m = line.match(/user exit code (\d+)/);
    if (m) events.push({ type: "exit", code: Number(m[1]), line });
    if (/INT .*page-fault/.test(line)) events.push({ type: "fault", line });
    m = line.match(/STATUS tasks[= ](\d+)/);
    if (m) events.push({ type: "status", tasks: Number(m[1]), line });
    if (/\bpanic\b/i.test(line)) {
      panic = true;
      events.push({ type: "panic", line });
    }
  }
  return { result: panic ? "PANIC" : "OK", panic, banner, events };
}

export function main(argv) {
  if (!argv[0]) { console.error("usage: serial_events.mjs <serial-log>"); process.exitCode = 2; return; }
  const parsed = parseSerial(fs.readFileSync(argv[0], "utf8"));
  console.log("RESULT: " + parsed.result);
  console.log("banner: " + (parsed.banner || "(none)"));
  console.log("events: " + parsed.events.length);
  for (const event of parsed.events) console.log("  " + event.type + " — " + event.line);
  if (parsed.panic) process.exitCode = 1;
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, "/"))) main(process.argv.slice(2));
