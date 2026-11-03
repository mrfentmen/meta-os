// CB-062..070 — face test files only. No face source edits.
// These read the real face.js / index.html and, for the board window, boot the
// real board service so the record shape is exercised end to end.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { createBoardServer } from "../board/board.mjs";

const ROOT = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), "..");
const FACE = path.join(ROOT, "face");
const faceJs = fs.readFileSync(path.join(FACE, "face.js"), "utf8");
// The shell's answers moved to the pure module in CB2-415..417, so a rule about
// the help text has to be read where the text now lives.
const faceLogic = fs.readFileSync(path.join(FACE, "logic.mjs"), "utf8");
const indexHtml = fs.readFileSync(path.join(FACE, "index.html"), "utf8");
const logoJs = fs.readFileSync(path.join(FACE, "logo-background.js"), "utf8");

const appsStart = faceJs.indexOf("var APPS = {");
const appsEnd = faceJs.indexOf("/* ---------- dock ---------- */");
const appsBlock = faceJs.slice(appsStart, appsEnd);
const appIds = [...appsBlock.matchAll(/^  ([a-z]+): \{/gm)].map((m) => m[1]);

const dockStart = faceJs.indexOf("var DOCK = [");
const dockEnd = faceJs.indexOf("DOCK.forEach");
const dockBlock = faceJs.slice(dockStart, dockEnd);
const dockIds = [...dockBlock.matchAll(/\["([a-z]+)",/g)].map((m) => m[1]);

test("CB-062 every dock entry maps to an app that exists", () => {
  assert.ok(appIds.length >= 13, "read the real APPS table");
  assert.ok(dockIds.length >= 13, "read the real DOCK table");
  for (const id of dockIds) assert.ok(appIds.includes(id), "dock id has an app: " + id);
});

test("CB-063 opening the same app twice focuses, never duplicates", () => {
  assert.match(faceJs, /if \(openWins\[id\]\) \{[\s\S]*?focusWin\(w\);[\s\S]*?return;/, "early focus branch");
  assert.equal((faceJs.match(/windowsEl\.appendChild\(node\)/g) || []).length, 1, "one append path");
  assert.match(faceJs, /openWins\[id\] = node/, "the app id is claimed after the single append");
});

test("CB-064 settings theme values round-trip through the same storage keys", () => {
  const settingsBlock = faceJs.slice(faceJs.indexOf("var settings = {"), faceJs.indexOf("var VARIANTS"));
  const keys = [...settingsBlock.matchAll(/localStorage\.getItem\("([^"]+)"\)/g)].map((m) => m[1]);
  assert.equal(keys.length, 6, "six persisted settings");
  for (const key of keys) {
    assert.ok(faceJs.includes('localStorage.setItem("' + key + '"'), "writes the same key: " + key);
  }
  assert.match(faceJs, /settings\.mode === "light"/);
  assert.match(faceJs, /settings\.paused \? "1" : "0"/);
  assert.match(faceJs, /String\(settings\.speed\)/);
});

test("CB-065 every wallpaper id in settings exists in its table", () => {
  const variantsBlock = faceJs.slice(faceJs.indexOf("var VARIANTS"), faceJs.indexOf("var BGS"));
  const variants = [...variantsBlock.matchAll(/(\w+): "/g)].map((m) => m[1]).sort();
  const variantStart = faceJs.indexOf('id="set-variant"');
  const variantButtons = [...faceJs.slice(variantStart, faceJs.indexOf('id="set-bg"', variantStart)).matchAll(/data-v="([^"]+)"/g)]
    .map((m) => m[1]).sort();
  assert.deepEqual(variantButtons, variants);

  const bgsBlock = faceJs.slice(faceJs.indexOf("var BGS"), faceJs.indexOf("function applySettings"));
  const bgs = [...bgsBlock.matchAll(/(\w+): "/g)].map((m) => m[1]).sort();
  const bgStart = faceJs.indexOf('id="set-bg"');
  const bgButtons = [...faceJs.slice(bgStart, faceJs.indexOf("</span></div>' +", bgStart)).matchAll(/data-v="([^"]+)"/g)]
    .map((m) => m[1]).sort();
  assert.deepEqual(bgButtons, bgs);
});

test("CB-066 the board window renders the service record shape, not sample data", async () => {
  const boardStart = faceJs.indexOf("  board: {");
  const boardEnd = faceJs.indexOf("  imperium: {", boardStart);
  const boardApp = faceJs.slice(boardStart, boardEnd);
  assert.match(boardApp, /<iframe[^>]*src="http:\/\/localhost:8790\/"/);
  assert.doesNotMatch(boardApp, /localStorage|metaos-face-board|sample/i);

  const server = createBoardServer({ storeFile: null });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    const base = "http://127.0.0.1:" + server.address().port;
    const posted = await fetch(base + "/rooms/main/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nick: "code100", text: "record shape" }),
    });
    assert.equal(posted.status, 201);
    const read = await fetch(base + "/rooms/main/messages?since=-1");
    const data = await read.json();
    assert.ok(data.messages.some((line) => line.startsWith("code100: record shape")), "posted record reads back");
  } finally {
    server.close();
  }
});

test("CB-067 terminal help lists exactly the approved commands", () => {
  const text = faceJs + "\n" + faceLogic;
  const lines = [...text.matchAll(/commands: ([^"'\\]+)/g)].map((m) => m[1].trim());
  assert.ok(lines.length >= 1, "the help reply reads");
  for (const line of lines) assert.equal(line, "status help uptime mem ps");
  assert.doesNotMatch(text, /commands:.*\b(clear|ls|cat)\b/);
});

test("CB-068 dashboard record cards use fields present in the status payload", () => {
  const status = (faceJs + "\n" + faceLogic).match(/STATUS tasks (\d+) heap_total (\d+K) milestone (K\d+)/);
  assert.ok(status, "the status answer carries the payload");
  const card = faceJs.match(/Machine record<\/h4><div class="big">([^<]+)</);
  assert.ok(card, "machine record card exists");
  assert.match(card[1], new RegExp(status[2] + " heap"));
  assert.match(card[1], new RegExp(status[1] + " tasks"));
  assert.match(faceJs, /id="dash-count"/);
  assert.match(faceJs, /id="dash-up"/);
});

test("CB-069 login names Mrfentmen and has exactly one password field", () => {
  assert.equal((indexHtml.match(/type="password"/g) || []).length, 1);
  assert.match(indexHtml, /class="login-name">Mrfentmen</);
  assert.equal((indexHtml.match(/<input[^>]*type="password"/g) || []).length, 1);
});

test("CB-070 the logo is the blue ribbon and no green-M asset is referenced", () => {
  const files = fs.readdirSync(FACE);
  assert.equal(files.filter((f) => /green[-_ ]?m/i.test(f)).length, 0, "no green-M file");
  for (const file of files) {
    if (!/\.(js|html|css|md)$/.test(file)) continue;
    const text = fs.readFileSync(path.join(FACE, file), "utf8");
    assert.doesNotMatch(text, /green[-_ ]?m\b/i, "no green-M reference in " + file);
  }
  assert.match(logoJs, /ribbon/i);
  assert.match(logoJs, /#4f7ec2/i);
});
