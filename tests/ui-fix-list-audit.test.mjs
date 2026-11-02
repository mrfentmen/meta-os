// Node built-in test runner, no dependencies:  node --test tests/ui-fix-list-audit.test.mjs
// Covers the UI fix list audit on the live meta-sentinel surface
// (index.html + js/ served by server/server.mjs), item by item:
//
// 1. Dead buttons: every <button id="..."> in index.html is wired to a
//    click handler in js/ — via an els pair (els.key.addEventListener),
//    a direct $("id").addEventListener, or a getElementById/$ variable
//    with .addEventListener. A button added without wiring fails here
//    instead of shipping dead on the screen.
// 2. Alerts are live data: renderAlerts reads the incident queue, and
//    the queue is fed by real assessment results (cameraId: id), never
//    by a fixture list.
// 3. Scoped out, not silently missing: the old dashboard's intel
//    overlay panels (#intel-plan and friends) are NOT on this surface,
//    so there is no dead intel overlay to wire or remove here; dispatch
//    stays SIMULATED (logged inside this stack, no real endpoint), and
//    no credential field exists in the web UI — the model key lives in
//    the server environment only (server/model.mjs), never in the page.
// 4. Branding: the live surface reads Meta Imperium throughout.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";

const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const jsDir = new URL("../js/", import.meta.url);
const jsFiles = readdirSync(jsDir).filter((f) => f.endsWith(".js"));
const jsByFile = new Map(
  jsFiles.map((f) => [f, readFileSync(new URL(f, jsDir), "utf8")]),
);
const commandMap = jsByFile.get("command-map.js");
const commandLoop = jsByFile.get("command-loop.js");

const buttonIds = [
  ...html.matchAll(/<button[^>]*\bid="([^"]+)"/g),
].map((m) => m[1]);

function isWired(id) {
  for (const src of jsByFile.values()) {
    // els pair: key: $("id")  +  els.key.addEventListener
    for (const m of src.matchAll(/(\w+):\s*\$\("([^"]+)"\)/g)) {
      if (m[2] === id && src.includes(`els.${m[1]}.addEventListener`)) return true;
    }
    // direct: $("id").addEventListener / $("id")?.addEventListener
    if (
      src.includes(`$("${id}").addEventListener`) ||
      src.includes(`$("${id}")?.addEventListener`)
    )
      return true;
    // variable: var|const|let v = getElementById("id") or $("id"), then v.addEventListener
    const vm = src.match(
      new RegExp(
        `(?:var|const|let)\\s+(\\w+)\\s*=\\s*(?:document\\.getElementById|\\$)\\("${id}"\\)`,
      ),
    );
    if (vm && src.includes(`${vm[1]}.addEventListener`)) return true;
  }
  return false;
}

test("no dead buttons: every button id in index.html has a click handler in js/", () => {
  assert.ok(buttonIds.length > 0, "index.html has buttons to check");
  const dead = buttonIds.filter((id) => !isWired(id));
  assert.deepEqual(dead, [], `unwired buttons: ${dead.join(", ")}`);
});

test("class-wired controls: product chips and mode buttons have click handlers", () => {
  assert.ok(
    commandMap.includes('document.querySelectorAll("[data-cmd-product]")'),
    "product chips are bound",
  );
  assert.ok(
    commandMap.includes('document.querySelectorAll("[data-cmd-mode]")'),
    "mode buttons are bound",
  );
  assert.ok(
    commandMap.includes('btn.addEventListener("click", () => setMode(btn.dataset.cmdMode))'),
    "mode buttons call setMode",
  );
});

test("Alerts are live data: renderAlerts reads the incident queue fed by real assessments", () => {
  assert.ok(
    commandMap.includes("const items = state.queue.list();"),
    "renderAlerts renders the live queue",
  );
  assert.ok(
    commandMap.includes("state.queue.add({"),
    "assessments feed the queue",
  );
  assert.ok(
    commandMap.includes("cameraId: id,"),
    "queued incidents carry the assessed camera, not a fixture",
  );
  assert.ok(
    jsByFile.get("command-flag.js").includes("class IncidentQueue"),
    "the queue is the IncidentQueue class",
  );
});

test("scoped out: no intel overlay panels on this surface, dispatch stays simulated", () => {
  for (const id of ["intel-plan", "intel-overlay", "intel-post"]) {
    assert.ok(!html.includes(`id="${id}"`), `no #${id} on the live surface`);
  }
  assert.ok(
    commandLoop.includes("Dispatch (SIMULATED)"),
    "loop feed dispatch lines say SIMULATED",
  );
  assert.ok(
    commandLoop.includes("no real service contacted"),
    "loop feed dispatch lines disclaim real contact",
  );
  for (const src of jsByFile.values()) {
    assert.ok(!src.includes("/api/dispatch"), "no real dispatch endpoint in js/");
  }
});

test("scoped out: no credential field in the web UI — the key stays server-side", () => {
  assert.ok(!html.includes('type="password"'), "no password input in the page");
  for (const src of jsByFile.values()) {
    assert.ok(!src.includes("SPARK_API_KEY"), "no model key reference in page js");
  }
});

test("branding: the live surface reads Meta Imperium", () => {
  assert.ok(html.includes("<title>Meta Imperium"), "title brands Meta Imperium");
  assert.ok(html.includes("<h1>Meta Imperium</h1>"), "header brands Meta Imperium");
  assert.ok(html.includes("IMPERIUM COMMAND"), "command view wordmark present");
});
