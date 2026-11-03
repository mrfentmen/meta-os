import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { validateRegistry } from "../agents/registry_validate.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const registry = JSON.parse(readFileSync(join(HERE, "..", "agents", "registry.json"), "utf8"));

test("every live entry has a command and every draft has none", () => {
  const result = validateRegistry(registry);
  assert.deepEqual(result.errors, []);
  assert.ok(result.ok);
  for (const agent of registry.agents) {
    assert.equal(typeof agent.name, "string");
    assert.ok(Array.isArray(agent.command), agent.name + " command must be an array");
    if (agent.draft !== true) {
      assert.ok(agent.command.length > 0, agent.name + " is live but has no command");
    }
    assert.equal(typeof agent.owner, "string");
  }
  const placeholder = registry.agents.filter((a) => a.command.join(" ") === "true");
  assert.deepEqual(placeholder, [], "no entry may carry the placeholder command");
});

test("a placeholder command is an error, not a draft", () => {
  const result = validateRegistry({
    agents: [{ name: "rowan", command: ["true"], owner: "boss" }],
  });
  assert.equal(result.ok, false);
  assert.ok(result.errors.some((e) => e.field === "command" && /placeholder/.test(e.message)));
});

test("duplicate agent names are reported", () => {
  const result = validateRegistry({
    agents: [
      { name: "hana", command: ["node", "a.mjs"], owner: "boss" },
      { name: "hana", command: ["node", "b.mjs"], owner: "boss" },
    ],
  });
  assert.equal(result.ok, false);
  assert.ok(result.errors.some((e) => e.field === "name" && /duplicate/.test(e.message)));
});

test("missing name, empty command, and missing owner are each named", () => {
  const result = validateRegistry({ agents: [{ command: [], owner: "" }] });
  const fields = result.errors.map((e) => e.field);
  assert.deepEqual(fields.sort(), ["command", "name", "owner"]);
});

test("badge, when present, must be a non-empty string", () => {
  const result = validateRegistry({
    agents: [{ name: "milo", command: ["node", "m.mjs"], owner: "boss", badge: 7 }],
  });
  assert.ok(result.errors.some((e) => e.field === "badge"));
});
