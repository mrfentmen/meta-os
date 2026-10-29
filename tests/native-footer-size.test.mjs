// Node built-in test runner, no dependencies:
//   node --test tests/native-footer-size.test.mjs
//
// IGNIS-UI-23 (Del UI push, Oct 29): native footer disclaimer size
// parity. The web frontend carries its prototype disclaimer as a
// <footer class="footer"> on every page — styles.css sets .footer at
// 13px in --muted — but the native window's equivalent disclaimer
// below the status bar used .caption (12pt), so it read one point
// smaller than the web footer while the Latest-panel notes (UI-21)
// already matched their own 13px web rule. The fix gives the footer
// disclaimer a 13pt system font, keeping its muted color, wrapping,
// padding, and the web footer's words verbatim. No Swift toolchain
// exists in this sandbox, so these are static checks on the shipped
// Swift.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const content = readFileSync(
  new URL(
    "../native/Sources/MetaTrio/Views/ContentView.swift",
    import.meta.url,
  ),
  "utf8",
);

const footerStart = content.indexOf('Text("Experimental prototype');
assert.ok(footerStart >= 0, "footer disclaimer exists");
const footer = content.slice(footerStart, footerStart + 1200);
assert.ok(footer.length > 0, "footer block exists");

const disclaimer =
  "Experimental prototype for staged, consenting scenarios. Not an operational law-enforcement, fire-detection, or enforcement system. This app never contacts police or emergency services, performs no face recognition or identity inference, and never dispatches or cites automatically.";

test("native footer: web contract — .footer at 13px muted", () => {
  const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");
  assert.match(
    css,
    /\.footer \{\s+padding: 12px 16px 20px;\s+max-width: 1240px;\s+margin: 0 auto;\s+color: var\(--muted\);\s+font-size: 13px;/,
    "web .footer is 13px muted",
  );
});

test("native footer: web footer carries the same disclaimer words", () => {
  const html = readFileSync(new URL("../index.html", import.meta.url), "utf8");
  assert.ok(
    html.includes(`<footer class="footer">`) &&
      html.includes(`<p>${disclaimer}</p>`),
    "web footer carries the disclaimer verbatim",
  );
});

test("native footer: disclaimer takes the 13pt system font", () => {
  assert.match(
    footer,
    /Text\("Experimental prototype[\s\S]{0,400}?\.font\(\.system\(size: 13\)\)/,
    "footer disclaimer takes the 13pt font",
  );
});

test("native footer: no caption font left on the disclaimer", () => {
  const disclaimerBlock = footer.slice(0, footer.indexOf(".frame(maxWidth"));
  assert.doesNotMatch(
    disclaimerBlock,
    /\.font\(\.caption\)/,
    "no caption font left on the footer disclaimer",
  );
  assert.match(
    disclaimerBlock,
    /\.foregroundStyle\(\.secondary\)/,
    "footer disclaimer keeps its muted color",
  );
  assert.ok(
    disclaimerBlock.includes(disclaimer),
    "footer disclaimer keeps the web footer's words verbatim",
  );
});
