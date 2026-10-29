// Node built-in test runner, no dependencies:
//   node --test tests/native-header-flame-chip-size.test.mjs
//
// IGNIS-UI-42 (Del UI push, Oct 29): native header flame chip type
// parity. The web header carries its accent pill as .product-badge
// — styles.css sets it at 13px, weight 700, letter-spacing 0.04em —
// but the native header's Ignis-only flame chip used .caption
// (12pt) semibold with no tracking, so it read one point smaller,
// one step lighter, and tighter than the web badge while the
// department and tagline beside it (UI-41) already matched their
// own web rules. The fix gives the chip a 13pt system font, bold
// weight, and 0.52pt tracking (0.04em of its own 13pt size),
// keeping its accent color, padding, corner radius, icon, and
// wording. No Swift toolchain exists in this sandbox, so these are
// static checks on the shipped Swift.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const content = readFileSync(
  new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url),
  "utf8",
);

function blockAfter(marker, length = 600) {
  const start = content.indexOf(marker);
  assert.ok(start >= 0, `${marker} exists`);
  return content.slice(start, start + length);
}

const chip = blockAfter('Label("Flame"');

test("native flame chip: web contract — .product-badge at 13px, 700, 0.04em tracking", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.product-badge \{\s+margin: 0;\s+font-size: 13px;\s+font-weight: 700;\s+letter-spacing: 0\.04em;/,
    "web .product-badge is 13px, weight 700, letter-spacing 0.04em",
  );
});

test("native flame chip: Ignis-only, wording and icon unchanged", () => {
  assert.match(
    content,
    /if model\.selectedProduct == \.ignis \{\s+Label\("Flame", systemImage: "flame\.fill"\)/,
    "chip stays Ignis-only with Flame wording and flame icon",
  );
});

test("native flame chip: takes 13pt bold with 0.52pt tracking, no caption left", () => {
  assert.match(
    chip,
    /\.font\(\.system\(size: 13\)\)/,
    "chip takes 13pt",
  );
  assert.doesNotMatch(chip, /\.font\(\.caption\)/, "no caption left on chip");
  assert.match(
    chip,
    /\.fontWeight\(\.bold\)/,
    "chip takes bold weight",
  );
  assert.match(
    chip,
    /\.tracking\(0\.52\)/,
    "chip takes 0.52pt tracking",
  );
});

test("native flame chip: accent pill styling unchanged", () => {
  assert.match(
    chip,
    /\.foregroundStyle\(accentColor\)/,
    "chip keeps accent color",
  );
  assert.match(
    chip,
    /\.padding\(\.horizontal, 8\)/,
    "chip keeps horizontal padding",
  );
  assert.match(
    chip,
    /\.cornerRadius\(999\)/,
    "chip keeps pill corner radius",
  );
});
