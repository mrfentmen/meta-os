// Delayed loading + fetch error helpers for the command view
// (HN-013, HN-014). No DOM access here: the caller supplies show /
// hide, so these stay importable from node tests.
//
// Loading rule (HN-013): an async panel shows its loading row only
// if the work is still pending past the delay (default 300 ms), so
// fast loads never flicker and slow loads never look frozen. The
// timer functions are injectable so tests run without real waits.

export function createDelayedIndicator({ show, hide, delayMs = 300, setTimer = setTimeout, clearTimer = clearTimeout } = {}) {
  let timer = null;
  let shown = false;
  return {
    start() {
      if (timer !== null || shown) return;
      timer = setTimer(() => {
        timer = null;
        shown = true;
        show();
      }, delayMs);
    },
    settle() {
      if (timer !== null) {
        clearTimer(timer);
        timer = null;
      }
      if (shown) {
        shown = false;
        hide();
      }
    },
  };
}

// Error class (HN-014): the real failure kind, for the retry row.
// fetch rejects with a TypeError on network failure (server down,
// DNS, CORS); an HTTP status arrives as an Error carrying it; a
// bad body is "invalid". Anything else is "unknown" — never a
// guessed kind, and never a fabricated message.
export function errorClassFor(err) {
  if (err instanceof TypeError) return "network";
  if (err && typeof err === "object") {
    const message = typeof err.message === "string" ? err.message : "";
    if (/^HTTP \d+/.test(message)) return "http";
    if (/not valid JSON|failed schema validation|not an object|validation/i.test(message)) return "invalid";
  }
  return "unknown";
}
