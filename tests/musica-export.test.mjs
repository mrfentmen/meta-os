// Musica catalogue export: HN-049. One command must produce a
// single bundle with tracks + catalogue + rights, and must list
// (not hide) any referenced file that is missing on disk.
import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync, rmSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const runtime = join(root, "os/worlds/musica/runtime");
const staging = join(root, "..", "staging", "musica-export-test");

function py(script, args) {
  return execFileSync("python3", [join(runtime, script), ...args], {
    encoding: "utf8",
  });
}

test("one command bundles tracks, catalogue, and rights", () => {
  rmSync(staging, { recursive: true, force: true });
  py("compose.py", ["--session-dir", staging, "--brief-id", "chipsynth",
    "--takes", "2", "--seed-base", "18000"]);
  py("keepers.py", [staging]);
  py("catalogue.py", [staging]);
  py("rights.py", [staging]);
  py("normalize.py", [staging]);
  py("midi.py", [staging]);
  py("board.py", [staging]);
  const out = join(staging, "bundle.zip");
  const printed = py("export.py", [staging, "--out", out]);
  assert.match(printed, /bundle .* members=\d+ missing=0/);
  const driver = `
import json, zipfile, sys
zf = zipfile.ZipFile(${JSON.stringify(out)})
names = zf.namelist()
assert "catalogue.json" in names, names
assert "rights.json" in names, names
assert "bundle.json" in names, names
assert any(n.startswith("keepers/") and n.endswith(".wav") for n in names), names
manifest = json.loads(zf.read("bundle.json"))
assert manifest["missing"] == [], manifest
print("BUNDLE-OK", len(names))
`;
  const result = execFileSync("python3", ["-"], { input: driver, encoding: "utf8" });
  assert.match(result, /BUNDLE-OK/);
});

test("bundle lists missing files instead of hiding them", () => {
  const catalogue = JSON.parse(readFileSync(join(staging, "catalogue.json"), "utf8"));
  const track = catalogue.tracks[0];
  assert.ok(track, "expected a catalogue track");
  rmSync(join(staging, track.file), { force: true });
  const out = join(staging, "bundle-missing.zip");
  py("export.py", [staging, "--out", out]);
  const driver = `
import json, zipfile
zf = zipfile.ZipFile(${JSON.stringify(out)})
manifest = json.loads(zf.read("bundle.json"))
assert ${JSON.stringify(track.file)} in manifest["missing"], manifest
print("MISSING-OK")
`;
  const result = execFileSync("python3", ["-"], { input: driver, encoding: "utf8" });
  assert.match(result, /MISSING-OK/);
});
