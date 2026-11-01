// Reduced-motion decision for the command view (HN-017). Pure:
// the caller supplies a matchMedia function, so node tests run
// without a browser. Absent matchMedia, or a matchMedia that
// throws, means "no preference stated" — motion stays on, never
// a guessed preference.

export function prefersReducedMotion(matchMediaFn = null) {
  const fn =
    matchMediaFn ??
    (typeof window !== "undefined" && typeof window.matchMedia === "function"
      ? window.matchMedia.bind(window)
      : null);
  if (typeof fn !== "function") return false;
  try {
    return fn("(prefers-reduced-motion: reduce)").matches === true;
  } catch {
    return false;
  }
}
