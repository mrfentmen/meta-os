// Node built-in test runner, no dependencies:
//   node --test tests/still-image-assess-button.test.mjs
//
// Still-image Assess button vs an assessment in flight. Choosing a
// still image reads it asynchronously, and every place that set the
// button directly tested only the data URL — so a new image chosen
// while a request was out, its read finishing mid-request, re-enabled
// the button under that request, and a tap was then silently dropped
// by the assessing guard. That is the assessment-in-flight mirror of
// the video button bug (see video-assess-button.test.mjs), and the
// native button already gates on exactly this: disabled when the image
// is nil or when an assessment is in flight. One helper now owns the
// web button with the same rule. No browser exists in this suite, so
// these are static checks on the shipped wiring, in the same style as
// the other Agent 1 tests. The read-in-flight window needs no change
// here: the data URL is null while a read is in flight, so a read
// settle already enables only a truly ready image.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const app = readFileSync(
  new URL("../js/app.js", import.meta.url),
  "utf8",
);
const model = readFileSync(
  new URL("../native/Sources/MetaTrio/ViewModels/AppModel.swift", import.meta.url),
  "utf8",
);

const stillSection = app.slice(app.indexOf("let stillImageDataUrl = null;"));

test("still-image: one helper owns the Assess button, requiring a data URL and no assessment in flight", () => {
  assert.match(
    stillSection,
    /function refreshStillImageAssessButton\(\) \{\s*els\.btnImageAssess\.disabled = !stillImageDataUrl \|\| stillImageAssessing;\s*\}/,
  );
});

test("still-image: no read, clear, or settle path sets the button directly, bypassing the helper", () => {
  assert.doesNotMatch(stillSection, /btnImageAssess\.disabled = false;/);
  assert.doesNotMatch(stillSection, /btnImageAssess\.disabled = true;/);
  assert.doesNotMatch(stillSection, /btnImageAssess\.disabled = !stillImageDataUrl;/);
});

test("still-image: Clear (and therefore Reset) refreshes through the helper", () => {
  const clearBody = stillSection.slice(
    stillSection.indexOf("function clearStillImageInput() {"),
    stillSection.indexOf("els.btnImageClear.addEventListener"),
  );
  assert.match(clearBody, /stillImageDataUrl = null;/);
  assert.match(clearBody, /refreshStillImageAssessButton\(\);/);
});

test("still-image: a read finishing refreshes through the helper, so a mid-request choice cannot enable the button under the request", () => {
  const readBody = stillSection.slice(
    stillSection.indexOf('els.imageInput.addEventListener("change"'),
    stillSection.indexOf('els.btnImageAssess.addEventListener("click"'),
  );
  const refreshCount = (readBody.match(/refreshStillImageAssessButton\(\);/g) || []).length;
  // Choice start, read success, and read failure.
  assert.ok(
    refreshCount >= 3,
    `expected at least 3 refresh calls in the image-choice handler, found ${refreshCount}`,
  );
});

test("still-image: the Assess tap and its settle path refresh through the helper", () => {
  const clickBody = stillSection.slice(
    stillSection.indexOf('els.btnImageAssess.addEventListener("click"'),
  );
  const refreshCount = (clickBody.match(/refreshStillImageAssessButton\(\);/g) || []).length;
  assert.ok(
    refreshCount >= 2,
    `expected at least 2 refresh calls in the Assess handler, found ${refreshCount}`,
  );
  assert.match(
    clickBody,
    /if \(!stillImageDataUrl \|\| stillImageAssessing\) return;/,
  );
});

test("native: the still-image button is already gated on nil image or assessing, so no native change is needed", () => {
  const view = readFileSync(
    new URL("../native/Sources/MetaTrio/Views/ContentView.swift", import.meta.url),
    "utf8",
  );
  assert.match(view, /\.disabled\(model\.stillImage == nil \|\| model\.stillImageAssessing\)/);
  assert.match(model, /guard let dataURL = stillImageDataURL, !stillImageAssessing else/);
});
