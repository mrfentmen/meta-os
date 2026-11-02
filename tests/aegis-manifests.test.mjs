import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { collectManifests, CollectorError, MANIFESTS } from "../aegis/manifests.mjs";

function tree(files) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-manifests-"));
  for (const [p, body] of Object.entries(files)) {
    const full = path.join(root, p);
    fs.mkdirSync(path.dirname(full), { recursive: true });
    fs.writeFileSync(full, body || "");
  }
  return root;
}

test("collects every known manifest with its ecosystem, sorted, posix paths", () => {
  const root = tree({
    "a/package.json": "{}",
    "b/Cargo.toml": "",
    "c/pyproject.toml": "",
    "c/requirements.txt": "",
    "d/go.mod": "",
    "e/Gemfile": "",
    "f/composer.json": "{}",
    "g/pom.xml": "",
    "README.md": "",
    "a/notes.txt": "",
  });
  const r = collectManifests(root);
  assert.equal(r.counts.total, 8);
  assert.deepEqual(r.manifests.map((m) => m.path), [
    "a/package.json", "b/Cargo.toml", "c/pyproject.toml", "c/requirements.txt",
    "d/go.mod", "e/Gemfile", "f/composer.json", "g/pom.xml",
  ]);
  assert.deepEqual(r.counts.byEcosystem, { npm: 1, cargo: 1, pypi: 2, go: 1, gem: 1, packagist: 1, maven: 1 });
  assert.ok(r.manifests.every((m) => !m.path.includes("\\")));
  assert.ok(r.manifests.every((m) => MANIFESTS[m.manifest] === m.ecosystem));
});

test("skips caches and VCS metadata, and says so", () => {
  const root = tree({
    "node_modules/x/package.json": "{}",
    ".git/package.json": "{}",
    "target/Cargo.toml": "",
    ".venv/pyproject.toml": "",
    "src/package.json": "{}",
  });
  const r = collectManifests(root);
  assert.deepEqual(r.manifests.map((m) => m.path), ["src/package.json"]);
  assert.equal(r.skipped.count, 4);
  assert.deepEqual(r.skipped.sample.map((s) => s.path).sort(), [".git", ".venv", "node_modules", "target"]);
  assert.ok(r.skipped.sample.every((s) => s.reason === "cache-or-vcs"));
});

test("does not follow symlinks, and counts them", () => {
  const root = tree({ "real/package.json": "{}" });
  fs.symlinkSync(path.join(root, "real"), path.join(root, "link"), "dir");
  const r = collectManifests(root);
  assert.deepEqual(r.manifests.map((m) => m.path), ["real/package.json"]);
  assert.equal(r.symlinksSkipped, 1);
});

test("depth cap is reported, not silent", () => {
  const root = tree({ "a/b/c/package.json": "{}" });
  const capped = collectManifests(root, { maxDepth: 1 });
  assert.equal(capped.counts.total, 0);
  assert.equal(capped.capped.count, 1);
  assert.deepEqual(capped.capped.sample, ["a/b"]);
  const full = collectManifests(root, { maxDepth: 3 });
  assert.deepEqual(full.manifests.map((m) => m.path), ["a/b/c/package.json"]);
  assert.equal(full.capped.count, 0);
});

test("missing or non-directory root is an error, not an empty inventory", () => {
  assert.throws(() => collectManifests("/nonexistent/aegis/root"), CollectorError);
  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "aegis-file-")), "package.json");
  fs.writeFileSync(file, "{}");
  assert.throws(() => collectManifests(file), CollectorError);
});

test("two runs over the same tree are identical", () => {
  const root = tree({ "a/package.json": "{}", "b/Cargo.toml": "", "x/node_modules/y/package.json": "{}" });
  assert.deepEqual(collectManifests(root), collectManifests(root));
});

test("the collector imports no network or process module", () => {
  const src = fs.readFileSync(new URL("../aegis/manifests.mjs", import.meta.url), "utf8");
  for (const banned of ["node:http", "node:https", "node:net", "node:dns", "node:child_process", "fetch("]) {
    assert.ok(!src.includes(banned), "collector must not use " + banned);
  }
});
