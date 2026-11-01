// Node built-in test runner, no dependencies:  node --test tests/ui-wave-loading.test.mjs
// Covers HN-013 (loading states past 300 ms): the delayed
// indicator shows only when the work is still pending past the
// delay, never flickers on fast loads, and cancels cleanly on
// settle. The timer functions are injected, so no test waits on
// a real clock; the production default delay is asserted to be
// 300 ms, and both on-load async panels (camera list, loop feed)
// are wired to it.

import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { createDelayedIndicator } from "../js/loading.js";

const mapJs = readFileSync(new URL("../js/command-map.js", import.meta.url), "utf8");
const css = readFileSync(new URL("../styles.css", import.meta.url), "utf8");

function fakeTimers() {
  const pending = new Map();
  let next = 1;
  return {
    pending,
    setTimer(fn, ms) {
      const id = next++;
      pending.set(id, { fn, ms });
      return id;
    },
    clearTimer(id) {
      pending.delete(id);
    },
    fireAll() {
      for (const [id, entry] of [...pending]) {
        pending.delete(id);
        entry.fn();
      }
    },
  };
}

test("indicator stays hidden until the delay fires", () => {
  const timers = fakeTimers();
  let shown = 0;
  const indicator = createDelayedIndicator({
    show: () => { shown++; }, hide: () => {},
    setTimer: timers.setTimer, clearTimer: timers.clearTimer,
  });
  indicator.start();
  assert.equal(shown, 0);
  timers.fireAll();
  assert.equal(shown, 1);
});

test("settle before the delay cancels the show", () => {
  const timers = fakeTimers();
  let shown = 0;
  const indicator = createDelayedIndicator({
    show: () => { shown++; }, hide: () => {},
    setTimer: timers.setTimer, clearTimer: timers.clearTimer,
  });
  indicator.start();
  indicator.settle();
  timers.fireAll();
  assert.equal(shown, 0);
});

test("settle after showing hides exactly once", () => {
  const timers = fakeTimers();
  let hidden = 0;
  const indicator = createDelayedIndicator({
    show: () => {}, hide: () => { hidden++; },
    setTimer: timers.setTimer, clearTimer: timers.clearTimer,
  });
  indicator.start();
  timers.fireAll();
  indicator.settle();
  indicator.settle();
  assert.equal(hidden, 1);
});

test("production default delay is 300 ms", () => {
  const timers = fakeTimers();
  const indicator = createDelayedIndicator({
    show: () => {}, hide: () => {},
    setTimer: timers.setTimer, clearTimer: timers.clearTimer,
  });
  indicator.start();
  assert.equal([...timers.pending.values()][0].ms, 300);
});

test("camera list and loop feed are wired to the delayed indicator", () => {
  assert.ok(mapJs.includes('import { createDelayedIndicator, errorClassFor } from "./loading.js";'));
  assert.match(mapJs, /Loading cameras…/);
  assert.match(mapJs, /Loading crew status…/);
  assert.ok(css.includes(".cmd-loading { font-style: italic; }"));
});
