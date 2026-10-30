// Node built-in test runner:
//   node --test tests/product-limitations-live-region.test.mjs
//
// Web product-switch limitations announcements. The limitations line
// carries the safety text that is always in effect for the selected
// product — Vigiles' "does not establish that a crime has occurred",
// Ignis' "not a certified fire-detection system … never create a real
// fire", Medicus' "does not determine that a legal violation has
// occurred" — and it changes on every product switch, but it used to
// be plain text with no live region, so a screen-reader user who had
// just switched products heard the radio's new value and nothing
// about the limits that now apply, unless they hunted for the
// paragraph. It is now a polite, atomic live region, like
// camera-state and the image/video state lines: the whole sentence is
// read, not just the changed words. It changes only on a product
// switch, a user action, never on a timer, so unlike the sampler-stats
// line there is no per-second spam risk in announcing it. Only the
// limitations are announced: the radio itself announces the new
// product's name, and the category list stays out of the live regions
// — reading the full list aloud on every switch would be noise, while
// the limitations are the safety text that must reach the user at the
// moment of the switch. The native side needs the same change, not a
// label: its header only set the new limitations text silently, so a
// VoiceOver user heard the picker's new value but not the new limits.
// The new limits are now announced verbatim through a helper of their
// own: a switch touches no backend and sends no frame, so neither
// backendFailure nor captureFailure describes it.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const page = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const model = readFileSync(
  new URL(
    "../native/Sources/MetaTrio/ViewModels/AppModel.swift",
    import.meta.url,
  ),
  "utf8",
);
const announcements = readFileSync(
  new URL(
    "../native/Sources/MetaTrio/Services/AccessibilityAnnouncement.swift",
    import.meta.url,
  ),
  "utf8",
);

const limitationsTag = page.match(/<p id="product-limitations"[^>]*>/);
assert.ok(limitationsTag, "index.html is missing its product-limitations element");
const categoriesTag = page.match(/<ul id="product-categories"[^>]*>/);
assert.ok(categoriesTag, "index.html is missing its product-categories element");

test("web: product-limitations is a polite, atomic live region", () => {
  assert.match(limitationsTag[0], /aria-live="polite"/);
  assert.match(limitationsTag[0], /aria-atomic="true"/);
});

test("web: product-categories stays out of the live regions (a switch must not read the full list aloud)", () => {
  assert.doesNotMatch(categoriesTag[0], /aria-live/);
});

test("native: a product switch announces the new product's limitations", () => {
  const selectedProduct = model.match(
    /@Published var selectedProduct[\s\S]*?@Published var endpoint/,
  );
  assert.ok(selectedProduct, "AppModel is missing selectedProduct");
  assert.match(selectedProduct[0], /if oldValue != selectedProduct/);
  assert.match(
    selectedProduct[0],
    /AccessibilityAnnouncement\.productLimitations\(config\.limitations\)/,
  );
});

test("native: productLimitations posts verbatim, not as a backend or capture failure", () => {
  const helper = announcements.match(
    /static func productLimitations\(_ message: String\) \{[\s\S]*?\n    \}/,
  );
  assert.ok(helper, "AccessibilityAnnouncement is missing productLimitations");
  assert.match(helper[0], /post\(message\)/);
  assert.doesNotMatch(helper[0], /backendFailure|captureFailure/);
});
