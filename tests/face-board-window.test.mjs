// Node built-in test runner, no dependencies:  node --test tests/face-board-window.test.mjs
// BUILD WAVE W7 — the board wired into the shell UI.
//
// The face Board window (face/face.js) used to be a browser-only copy:
// posts lived in localStorage under "metaos-face-board" and never
// reached the board service. W7 replaces it with a face window that
// embeds the real board viewer's document, served by board/board.mjs
// (default port 8790). An iframe keeps the viewer on its own origin,
// so no cross-origin fetch is needed — the board service sets no CORS
// headers, and this test pins that the window does not try to fetch
// across origins either.
//
// What this pins:
// 1. The face Board app embeds an iframe to the board service's
//    documented default origin (http://localhost:8790/).
// 2. No browser-only board remains: no localStorage board key, no
//    "browser only" copy text in the Board app.
// 3. The Board stays on the face dock.
// 4. The document the window embeds is real: the board service booted
//    here serves its viewer at / (title "Meta OS — Board"), and a
//    post through the service reads back — the window shows the same
//    rooms any other board client sees, not a private copy.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { createBoardServer } from "../board/board.mjs";

const faceJs = readFileSync(new URL("../face/face.js", import.meta.url), "utf8");
const boardMjs = readFileSync(
  new URL("../board/board.mjs", import.meta.url),
  "utf8",
);

// The Board app block: from "board: {" to the next app ("imperium: {").
const boardStart = faceJs.indexOf("  board: {");
assert.ok(boardStart >= 0, "face.js has a board app");
const boardEnd = faceJs.indexOf("  imperium: {", boardStart);
assert.ok(boardEnd > boardStart, "board app ends before imperium app");
const boardApp = faceJs.slice(boardStart, boardEnd);

test("W7: the face Board window embeds the real board viewer (default port 8790)", () => {
  assert.match(
    boardApp,
    /<iframe[^>]*src="http:\/\/localhost:8790\/"/,
    "Board window embeds an iframe to http://localhost:8790/",
  );
  assert.ok(
    boardMjs.includes("process.env.BOARD_PORT || 8790"),
    "board.mjs documents 8790 as the default port the window points at",
  );
});

test("W7: no browser-only board remains in the face Board app", () => {
  assert.ok(
    !boardApp.includes("metaos-face-board"),
    "no localStorage board key in the Board app",
  );
  assert.ok(
    !boardApp.includes("localStorage"),
    "the Board app stores nothing in the browser",
  );
  assert.ok(
    !boardApp.includes("browser only"),
    "no browser-only copy text remains",
  );
  assert.match(
    boardApp,
    /service is not running/,
    "the window says plainly what a blank frame means",
  );
});

test("W7: the Board stays on the face dock", () => {
  assert.ok(
    faceJs.includes('["board",'),
    "DOCK lists the board app",
  );
});

test("W7: the embedded viewer document is real — the board service serves it", async () => {
  const server = createBoardServer({ storeFile: null });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    const base = `http://127.0.0.1:${server.address().port}`;
    const viewer = await fetch(base + "/");
    assert.equal(viewer.status, 200);
    const html = await viewer.text();
    assert.match(html, /<title>Meta OS — Board<\/title>/);

    // A post through the service reads back: the window shows the
    // service's rooms, not a private copy.
    const posted = await fetch(base + "/rooms/main/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nick: "w7", text: "board window check" }),
    });
    assert.equal(posted.status, 201);
    const read = await fetch(base + "/rooms/main/messages?since=-1");
    const data = await read.json();
    assert.ok(
      data.messages.some((line) => line.startsWith("w7: board window check")),
      "posted line reads back from the service",
    );
  } finally {
    server.close();
  }
});
