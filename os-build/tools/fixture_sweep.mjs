#!/usr/bin/env node
// CB-080 — report-only sweep: files under tests/ that no suite names, and
// TODO/FIXME lines. It deletes nothing.
import fs from "node:fs";
import path from "node:path";

function walk(dir, base = dir) {
  const out = [];
  if (!fs.existsSync(dir)) return out;
  for (const name of fs.readdirSync(dir).sort()) {
    const file = path.join(dir, name);
    const st = fs.statSync(file);
    if (st.isDirectory()) out.push(...walk(file, base));
    else out.push(path.relative(base, file).split(path.sep).join("/"));
  }
  return out;
}

export function sweep(testsDir) {
  const files = walk(testsDir);
  const suites = files.filter((f) => f.endsWith(".test.mjs"));
  const haystack = suites.map((f) => fs.readFileSync(path.join(testsDir, f), "utf8")).join("\n");
  const orphans = files.filter((f) => !f.endsWith(".test.mjs") && !haystack.includes(f) && !haystack.includes(path.basename(f)));
  const todos = [];
  for (const rel of files) {
    const text = fs.readFileSync(path.join(testsDir, rel), "utf8");
    text.split(/\r?\n/).forEach((line, i) => {
      if (/\b(TODO|FIXME)\b/.test(line)) todos.push({ file: rel, line: i + 1, text: line.trim() });
    });
  }
  return { files: files.length, suites: suites.length, orphans, todos };
}

export function main(argv) {
  const dir = argv[0] || "tests";
  const result = sweep(dir);
  console.log("tests: " + result.files + " files, " + result.suites + " suites");
  console.log("unreferenced files: " + result.orphans.length);
  for (const name of result.orphans) console.log("  " + name);
  console.log("TODO/FIXME lines: " + result.todos.length);
  for (const row of result.todos) console.log("  " + row.file + ":" + row.line + " — " + row.text);
  console.log("report only: nothing was deleted");
}

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, "/"))) main(process.argv.slice(2));
