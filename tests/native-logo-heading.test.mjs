// Node built-in test runner, no dependencies:
//   node --test tests/native-logo-heading.test.mjs
//
// LOGO-NATIVE-3 (Del direction, Oct 30): native parity for the
// web OPS-CONSOLE panel headings, for the Logo panel: its title
// was wired into the shared PanelHeading so it carried the same
// console heading treatment as the other five panels.
//
// UPDATED 2026-11-01 (boss order): the LOGO-1 color section is
// removed everywhere, and with it the native Logo panel file
// (LogoColorPanel.swift). There is no native Logo panel title
// left to wire. What survives, and what these checks now pin:
// PanelHeading itself still carries the three web console
// branches in ContentView.swift for the remaining panels, and
// the deleted panel file stays deleted.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";

const contentView = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url),
  "utf8",
);
const panelExists = existsSync(
  new URL("../native/Sources/MetaTrio/Views/LogoColorPanel.swift", import.meta.url),
);

test("logo heading: the native Logo panel is removed with the color section", () => {
  assert.equal(panelExists, false, "LogoColorPanel.swift must stay deleted");
  assert.ok(!contentView.includes("LogoColorPanel"), "no view may reference the deleted panel");
});

test("logo heading: PanelHeading still carries the three web console branches", () => {
  // Ignis: uppercase mono 15pt bold, 1.8pt tracking, red tick.
  assert.ok(contentView.includes("Text(title.uppercased())"));
  assert.ok(contentView.includes(".font(.system(size: 15, weight: .bold, design: .monospaced))"));
  assert.ok(contentView.includes(".tracking(1.8)"));
  assert.ok(contentView.includes("Color(red: 217 / 255, green: 43 / 255, blue: 43 / 255)"));
  // Vigiles: same shape in Vigiles blue.
  assert.ok(contentView.includes("Color(red: 79 / 255, green: 126 / 255, blue: 194 / 255)"));
  // Medicus: uppercase plain 15pt bold, 1.2pt tracking, no tick branch.
  assert.ok(contentView.includes(".font(.system(size: 15, weight: .bold))"));
  assert.ok(contentView.includes(".tracking(1.2)"));
});

test("logo heading: VoiceOver still hears the plain title on the surviving panels", () => {
  assert.ok(
    contentView.includes(".accessibilityLabel(title)"),
    "PanelHeading keeps the original title as the accessibility label",
  );
});
