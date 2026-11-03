// Tests for agents/notify.mjs — a real file sink, a stubbed desktop binary and
// a real loopback HTTP server for the webhook. No network leaves the machine.
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";

import { notify, WINDOW_MS, noticeFile } from "../agents/notify.mjs";

function tmp() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "meta-notify-"));
}

function lines(root) {
  const file = noticeFile(root);
  if (!fs.existsSync(file)) return [];
  return fs.readFileSync(file, "utf8").trim().split("\n").filter(Boolean).map((l) => JSON.parse(l));
}

test("a notice is appended as one JSONL line", async () => {
  const root = tmp();
  const record = await notify({ root, severity: "note", title: "job done", body: "j1" });
  assert.deepEqual(record.delivered, ["journal"]);
  const stored = lines(root);
  assert.equal(stored.length, 1);
  assert.equal(stored[0].title, "job done");
  assert.equal(stored[0].severity, "note");
});

test("a bad severity or missing title is refused", async () => {
  const root = tmp();
  await assert.rejects(() => notify({ root, severity: "loud", title: "x" }), /severity/);
  await assert.rejects(() => notify({ root, title: "" }), /title/);
});

test("the same alarm does not ring twice inside the window", async () => {
  const root = tmp();
  const first = await notify({ root, severity: "alarm", key: "queue-down", title: "queue down" });
  const second = await notify({
    root, severity: "alarm", key: "queue-down", title: "queue down",
    now: Date.now() + 1000,
  });
  assert.equal(first.suppressed, false);
  assert.equal(second.suppressed, true);
  assert.equal(lines(root).length, 2, "both runs are recorded, one is silent");
});

test("the same alarm rings again after the window", async () => {
  const root = tmp();
  const base = Date.now();
  await notify({ root, severity: "alarm", key: "k", title: "t", now: base });
  const later = await notify({
    root, severity: "alarm", key: "k", title: "t", now: base + WINDOW_MS + 1,
  });
  assert.equal(later.suppressed, false);
});

test("quiet notes are never suppressed, even with the same key", async () => {
  const root = tmp();
  await notify({ root, severity: "note", key: "k", title: "t", now: 1000 });
  const second = await notify({ root, severity: "note", key: "k", title: "t", now: 1001 });
  assert.equal(second.suppressed, false);
});

test("the desktop sink uses critical urgency for an alarm", async () => {
  const root = tmp();
  const calls = [];
  const deps = {
    notifySend: "notify-send",
    spawnSync: (bin, args) => {
      calls.push({ bin, args });
      return { status: 0 };
    },
  };
  const previous = process.env.DISPLAY;
  process.env.DISPLAY = ":0";
  try {
    await notify({ root, severity: "alarm", title: "queue down", body: "check", deps });
    await notify({ root, severity: "note", title: "job done", deps });
  } finally {
    if (previous === undefined) delete process.env.DISPLAY;
    else process.env.DISPLAY = previous;
  }
  assert.equal(calls.length, 2);
  assert.deepEqual(calls[0].args.slice(0, 2), ["--urgency", "critical"]);
  assert.deepEqual(calls[1].args.slice(0, 2), ["--urgency", "normal"]);
});

test("no display means no desktop call", async () => {
  const root = tmp();
  const calls = [];
  const previous = process.env.DISPLAY;
  delete process.env.DISPLAY;
  try {
    await notify({
      root, title: "t", deps: { spawnSync: () => { calls.push(1); return { status: 0 }; } },
    });
  } finally {
    if (previous !== undefined) process.env.DISPLAY = previous;
  }
  assert.equal(calls.length, 0);
});

test("the webhook posts the record to a real loopback server", async () => {
  const root = tmp();
  const received = [];
  const server = http.createServer((req, res) => {
    let body = "";
    req.on("data", (chunk) => { body += chunk; });
    req.on("end", () => {
      received.push(JSON.parse(body));
      res.writeHead(200).end("ok");
    });
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address();
  const previous = process.env.METAOS_NOTIFY_WEBHOOK;
  process.env.METAOS_NOTIFY_WEBHOOK = "http://127.0.0.1:" + port + "/hook";
  try {
    const record = await notify({
      root, severity: "alarm", title: "stopped", channels: ["journal", "webhook"],
    });
    assert.ok(record.delivered.includes("webhook"));
    assert.equal(received.length, 1);
    assert.equal(received[0].title, "stopped");
  } finally {
    if (previous === undefined) delete process.env.METAOS_NOTIFY_WEBHOOK;
    else process.env.METAOS_NOTIFY_WEBHOOK = previous;
    await new Promise((resolve) => server.close(resolve));
  }
});

test("a dead webhook does not throw and is not reported as delivered", async () => {
  const root = tmp();
  const previous = process.env.METAOS_NOTIFY_WEBHOOK;
  process.env.METAOS_NOTIFY_WEBHOOK = "http://127.0.0.1:1/hook";
  try {
    const record = await notify({
      root, severity: "alarm", title: "stopped", channels: ["journal", "webhook"],
    });
    assert.deepEqual(record.delivered, ["journal"]);
  } finally {
    if (previous === undefined) delete process.env.METAOS_NOTIFY_WEBHOOK;
    else process.env.METAOS_NOTIFY_WEBHOOK = previous;
  }
});

test("an unknown channel is a refusal, not a silent drop", async () => {
  const root = tmp();
  await assert.rejects(
    () => notify({ root, title: "t", channels: ["carrier-pigeon"] }),
    /unknown channel/
  );
});
