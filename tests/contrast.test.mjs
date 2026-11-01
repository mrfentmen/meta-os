// Node built-in test runner, no dependencies:  node --test tests/contrast.test.mjs
// Covers HN-018 (contrast pass, WCAG AA = 4.5 for normal text).
// Every pair below is MEASURED here from the shipped stylesheet's
// own colors — not eyeballed. Command-view text is measured
// against the panel glass composited over the view background
// (#02040a), the solid surface text actually sits on; the map
// behind the glass is dimmed by it and is not the text background.
// Brand hexes are pinned by other tests (ignis-web-theme, logo
// palettes), so short brand pairs are fixed by moving TEXT colors
// only — the one pair that cannot be fixed without a brand change
// (the Ignis gradient's light end with white text, 3.93) is
// guarded as pinned-and-listed, and flagged for the boss in the
// HN-025 report instead of silently edited.

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");

function hexRgb(hex) {
  const clean = hex.replace("#", "");
  return {
    r: parseInt(clean.slice(0, 2), 16),
    g: parseInt(clean.slice(2, 4), 16),
    b: parseInt(clean.slice(4, 6), 16),
  };
}

function luminance({ r, g, b }) {
  const f = (c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
}

function ratio(fg, bg) {
  const l1 = luminance(fg);
  const l2 = luminance(bg);
  const [hi, lo] = l1 > l2 ? [l1, l2] : [l2, l1];
  return (hi + 0.05) / (lo + 0.05);
}

function composite(fg, alpha, bg) {
  return {
    r: alpha * fg.r + (1 - alpha) * bg.r,
    g: alpha * fg.g + (1 - alpha) * bg.g,
    b: alpha * fg.b + (1 - alpha) * bg.b,
  };
}

const BG = hexRgb("#14161a");
const VIEW_BG = hexRgb("#02040a");
const GLASS = composite(hexRgb("#03090f"), 0.86, VIEW_BG);
const PANEL = composite(hexRgb("#1d2026"), 0.68, BG);

function check(fg, bg, min, label) {
  const r = ratio(fg, bg);
  assert.ok(r >= min, `${label}: measured ${r.toFixed(2)}, need ${min}`);
  return r;
}

test("console body text, muted text, and input text pass AA", () => {
  check(hexRgb("#e6e6e6"), BG, 4.5, "body text");
  check(hexRgb("#9aa0a8"), BG, 4.5, "muted on background");
  check(hexRgb("#9aa0a8"), PANEL, 4.5, "muted on panel");
  check(hexRgb("#e6e6e6"), hexRgb("#101216"), 4.5, "input text");
});

test("console status colors pass AA", () => {
  check(hexRgb("#5da864"), BG, 4.5, "ok green");
  check(hexRgb("#c9a227"), BG, 4.5, "warn gold");
  check(hexRgb("#e07068"), BG, 4.5, "error text (fixed from #c2504a)");
});

test("fixed accent text colors pass AA; brand hexes untouched", () => {
  check(hexRgb("#6a96d8"), BG, 4.5, "vigiles text (fixed from #4f7ec2)");
  check(hexRgb("#e85545"), BG, 4.5, "ignis text (fixed from #d92b2b)");
  assert.ok(css.includes('body[data-product="vigiles"] .product-badge { color: #6a96d8; }'));
  assert.ok(css.includes('.product-option[data-product-option="vigiles"]:has(input:checked) .product-option-name { color: #6a96d8; }'));
  assert.ok(css.includes('.product-option[data-product-option="ignis"]:has(input:checked) .product-option-name { color: #e85545; }'));
  assert.ok(css.includes(".status[data-state=\"error\"],\n.camera-indicator,\n.history-error .history-head strong { color: #e07068; }"));
  // Brand hexes still present (pinned elsewhere, not shifted).
  assert.ok(css.includes("--accent: #4f7ec2;"));
  assert.ok(css.includes("--accent: #d92b2b;"));
  assert.ok(css.includes("--err: #c2504a;"));
});

test("primary button text passes AA on its real background", () => {
  check(hexRgb("#02131c"), hexRgb("#4f7ec2"), 4.5, "vigiles primary (fixed from white)");
  check(hexRgb("#02131c"), hexRgb("#79c180"), 4.5, "medicus primary light end (fixed from white)");
  check(hexRgb("#02131c"), hexRgb("#3f8f4b"), 4.5, "medicus primary dark end (fixed from white)");
  assert.ok(css.includes('body[data-product="vigiles"] .btn-primary:not(:disabled) { color: #02131c; }'));
  assert.ok(css.includes('body[data-product="medicus"] .btn-primary:not(:disabled) { color: #02131c; }'));
});

test("command-view text passes AA on the panel glass", () => {
  for (const [hex, label] of [
    ["#53c8ff", "vigiles command accent"],
    ["#ff7a3c", "ignis command accent"],
    ["#35e0a1", "medicus command accent"],
    ["#ffb3ab", "loop incident red"],
    ["#ffe27a", "loop incident yellow"],
    ["#ffd9a8", "loop dispatch"],
    ["#ff8d84", "command error"],
    ["#ff2d20", "flag"],
  ]) {
    check(hexRgb(hex), GLASS, 4.5, label);
  }
  const stepper = composite(hexRgb("#d2e6f0"), 0.66, GLASS);
  check(stepper, GLASS, 4.5, "stepper unfinished (fixed from 0.45 alpha)");
  assert.ok(css.includes("color: rgba(210, 230, 240, 0.66);"));
});

test("pinned exception, listed not hidden: Ignis gradient light end", () => {
  // White on #e54848 measures ~3.93 (short of 4.5); white on the
  // dark end #b01e1e measures ~6.88. No single text color passes
  // both ends, and the gradient is pinned by ignis-web-theme
  // tests — so it stays, and the HN-025 report flags it for a
  // brand call instead of pretending it passes.
  assert.ok(css.includes("linear-gradient(135deg, #e54848, #b01e1e)"));
  const light = ratio(hexRgb("#ffffff"), hexRgb("#e54848"));
  const dark = ratio(hexRgb("#ffffff"), hexRgb("#b01e1e"));
  assert.ok(light < 4.5 && dark >= 4.5, `gradient ends measure ${light.toFixed(2)} / ${dark.toFixed(2)}`);
});
