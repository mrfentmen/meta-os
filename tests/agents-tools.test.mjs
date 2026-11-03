import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import http from "node:http";
import os from "node:os";
import path from "node:path";
import { canFinish, loadContract } from "../agents/contract.mjs";
import { createToolGateway, receiptEvidence, ToolError } from "../agents/tools.mjs";

const NODE = process.execPath;
const TMP = () => fs.mkdtempSync(path.join(os.tmpdir(), "agent-tools-"));
const FIXTURE = path.join(import.meta.dirname, "fixtures", "contract-done.json");

function grantsFor(dir, port = null) {
  return {
    read: [path.join(dir, "inside")],
    write: [path.join(dir, "inside")],
    commands: [NODE],
    hosts: port ? [{ host: "127.0.0.1", ports: [port] }] : [],
    maxSpendUsd: 2,
    maxWallMs: 5000,
  };
}

test("tools: the shared contract fixture is done on the Node side", () => {
  const contract = loadContract(FIXTURE);
  assert.equal(contract.status, "done");
  assert.equal(canFinish(contract).ok, true);
  assert.equal(contract.done_checks[0].seq > contract.steps[0].result.closed_seq, true);
});

test("tools: a write, append and read each leave a receipt", async () => {
  const dir = TMP();
  fs.mkdirSync(path.join(dir, "inside"));
  const gateway = createToolGateway({
    grants: grantsFor(dir),
    root: dir,
    runDir: path.join(dir, "run"),
    runId: "run-1",
    agent: "milo",
    contract: loadContract(FIXTURE),
  });

  const write = await gateway.call({ kind: "write", path: "inside/a.txt", data: "hello" });
  assert.equal(write.receipt.ok, true);
  assert.equal(write.receipt.bytes, 5);
  assert.equal(write.receipt.sha256.length, 64);
  assert.equal(write.receipt.contract.length, 16);

  const append = await gateway.call({ kind: "append", path: "inside/a.txt", text: "!" });
  assert.equal(append.receipt.ok, true);

  const read = await gateway.call({ kind: "read", path: "inside/a.txt" });
  assert.equal(read.result.data.toString(), "hello!");
  assert.equal(read.receipt.bytes, 6);

  const receipts = gateway.receipts();
  assert.equal(receipts.length, 3);
  assert.deepEqual(receipts.map((receipt) => receipt.kind), ["write", "append", "read"]);
  assert.match(receiptEvidence(read.receipt), /^tool:tool-\d+-[0-9a-f]+ sha256:[0-9a-f]{64}$/);
});

test("tools: an out-of-grant write is refused before it creates a file, and leaves a refusal receipt", async () => {
  const dir = TMP();
  const inside = path.join(dir, "inside");
  const outside = path.join(dir, "outside");
  fs.mkdirSync(inside);
  fs.mkdirSync(outside);
  const gateway = createToolGateway({ grants: grantsFor(dir), root: dir, runDir: path.join(dir, "run") });

  await assert.rejects(
    () => gateway.call({ kind: "write", path: path.join(outside, "pwn.txt"), data: "no" }),
    (error) => error instanceof ToolError && error.code === "path-outside-grant" && error.receipt.ok === false,
  );
  assert.equal(fs.existsSync(path.join(outside, "pwn.txt")), false);
  assert.equal(gateway.receipts().filter((receipt) => receipt.ok === false).length, 1);
});

test("tools: exec runs a granted program and refuses an ungranted one", async () => {
  const dir = TMP();
  fs.mkdirSync(path.join(dir, "inside"));
  const gateway = createToolGateway({ grants: grantsFor(dir), root: dir, runDir: path.join(dir, "run") });
  const ran = await gateway.call({ kind: "exec", argv: [NODE, "-e", "process.stdout.write('hi')"] });
  assert.equal(ran.result.exit, 0);
  assert.equal(ran.result.stdout, "hi");
  assert.equal(ran.receipt.ok, true);

  await assert.rejects(
    () => gateway.call({ kind: "exec", argv: ["/bin/sh", "-c", "true"] }),
    (error) => error instanceof ToolError && error.code === "command-not-granted",
  );
});

test("tools: network is host+port gated and a redirect is not followed", async () => {
  const dir = TMP();
  const server = http.createServer((request, response) => {
    if (request.url === "/redirect") {
      response.writeHead(302, { Location: "/ok" });
      response.end();
      return;
    }
    response.writeHead(200, { "content-type": "text/plain" });
    response.end("hello");
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = server.address().port;
  try {
    const gateway = createToolGateway({
      grants: grantsFor(dir, port),
      root: dir,
      runDir: path.join(dir, "run"),
    });
    const ok = await gateway.call({ kind: "network", url: "http://127.0.0.1:" + port + "/ok" });
    assert.equal(ok.result.status, 200);
    assert.equal(ok.result.body, "hello");
    assert.equal(ok.receipt.sha256.length, 64);

    await assert.rejects(
      () => gateway.call({ kind: "network", url: "http://127.0.0.1:" + port + "/redirect" }),
      (error) => error instanceof ToolError && error.code === "network-redirect",
    );
    const withQuery = await gateway.call({ kind: "network", url: "http://127.0.0.1:" + port + "/ok?token=secret" });
    assert.equal(withQuery.receipt.url, "http://127.0.0.1:" + port + "/ok");
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
});

test("tools: spend is stateful within the run and the cap is enforced", async () => {
  const dir = TMP();
  fs.mkdirSync(path.join(dir, "inside"));
  const gateway = createToolGateway({ grants: grantsFor(dir), root: dir, runDir: path.join(dir, "run") });
  const first = await gateway.call({ kind: "spend", usd: 1.5, reason: "model call" });
  assert.equal(first.result.spentUsd, 1.5);
  await assert.rejects(
    () => gateway.call({ kind: "spend", usd: 1, reason: "another call" }),
    (error) => error instanceof ToolError && error.code === "spend-cap",
  );
  assert.equal(gateway.spentUsd(), 1.5);
  assert.equal(gateway.receipts().filter((receipt) => receipt.kind === "spend" && !receipt.ok).length, 1);
});

test("tools: the wall cap is checked against the gateway's own clock", async () => {
  const dir = TMP();
  fs.mkdirSync(path.join(dir, "inside"));
  let clock = 0;
  const gateway = createToolGateway({
    grants: { ...grantsFor(dir), maxWallMs: 5 },
    root: dir,
    runDir: path.join(dir, "run"),
    now: () => clock,
  });
  await gateway.call({ kind: "wall" });
  clock = 10;
  await assert.rejects(
    () => gateway.call({ kind: "wall" }),
    (error) => error instanceof ToolError && error.code === "wall-cap",
  );
});
