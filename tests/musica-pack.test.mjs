// Musica pack manifest: HN-026. The pack must validate green and the
// registry must list it with an honest status.
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

test("musica pack validates green", () => {
  const out = execFileSync(
    "python3",
    [join(root, "os/worlds/validate_pack.py"), join(root, "os/worlds/musica/pack.json")],
    { encoding: "utf8" },
  );
  assert.match(out, /musica\/pack\.json: OK/);
});

test("musica pack status is honest partial at HN-045", () => {
  const pack = JSON.parse(readFileSync(join(root, "os/worlds/musica/pack.json"), "utf8"));
  assert.equal(pack.pack, "musica");
  assert.equal(pack.status, "partial");
  assert.equal(pack.version, "0.1.0");
});

test("musica PACK.md states proven and unproven honestly", () => {
  const doc = readFileSync(join(root, "os/worlds/musica/PACK.md"), "utf8");
  assert.match(doc, /PARTIAL/);
  assert.match(doc, /overnight-001 \(100\n  takes, 85 keepers, 15 rejects/);
  assert.match(doc, /Spark-assisted composition live/);
});

test("worlds registry lists musica", () => {
  const readme = readFileSync(join(root, "os/worlds/README.md"), "utf8");
  assert.match(readme, /\| musica \| Music studio \| PARTIAL/);
});
