import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url));
const registry = JSON.parse(readFileSync(join(HERE, "..", "agents", "registry.json"), "utf8"));

test("every registry entry has name, owner (the badge field), and a command array", () => {
  assert.ok(Array.isArray(registry.agents));
  for (const agent of registry.agents) {
    assert.equal(typeof agent.name, "string", JSON.stringify(agent));
    assert.ok(agent.name.trim().length > 0);
    assert.equal(typeof agent.owner, "string", agent.name);
    assert.ok(Array.isArray(agent.command), agent.name);
    assert.ok(agent.command.length > 0, agent.name);
    for (const part of agent.command) assert.equal(typeof part, "string", agent.name);
    if (agent.badge !== undefined) assert.equal(typeof agent.badge, "string", agent.name);
  }
});

test("registry names are unique", () => {
  const names = registry.agents.map((agent) => agent.name);
  assert.equal(new Set(names).size, names.length);
});
