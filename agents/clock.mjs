// Meta OS agent layer — clock arithmetic that survives a host clock jump (R11-291).
//
// `Date.now()` is not monotonic. A host that corrects itself backwards makes every duration
// computed from wall time negative, and a budget computed that way either goes negative (a run
// that can never be stopped) or flips sign and becomes infinite work. These helpers make the
// jump explicit instead of letting it leak into a number that looks measured.
export class ClockJumpError extends Error {}

// A backward jump is not "zero elapsed" in reality, so the caller is told it happened. The
// return shape keeps the duration usable for the record while the flag keeps it honest.
export function elapsedMs(startMs, endMs) {
  const raw = Number(endMs) - Number(startMs);
  if (!Number.isFinite(raw)) return { ms: 0, jumped: true, reason: "non-finite-clock" };
  if (raw < 0) return { ms: 0, jumped: true, reason: "clock-went-backwards", raw };
  return { ms: raw, jumped: false, reason: null };
}

// Remaining budget in [0, cap]. A cap of null/undefined means "no cap" and stays Infinity; a
// negative remain is clamped to 0 rather than carried, because "-5 ms left" is a state no
// caller can act on and it silently reads as permission to keep going.
export function budgetRemainingMs({ capMs, spentMs }) {
  if (capMs == null) return { remaining: Infinity, capped: false, overrun: false };
  const cap = Number(capMs);
  if (!Number.isFinite(cap) || cap <= 0) throw new ClockJumpError("budget: cap must be a positive finite number");
  const spent = Number(spentMs);
  if (!Number.isFinite(spent) || spent < 0) return { remaining: 0, capped: true, overrun: true, reason: "bad-spend" };
  const remaining = Math.max(0, cap - spent);
  return { remaining, capped: true, overrun: spent > cap };
}
