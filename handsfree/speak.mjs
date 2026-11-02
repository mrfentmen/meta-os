// Hands-Free C5 — speakable summaries that never cut a sentence (R11-242).
//
// A brief read aloud that stops mid-clause is worse than a shorter brief: the listener cannot
// tell a cut from a fact. So an over-cap brief is summarised by keeping WHOLE sentences, and if
// not even one fits, the speaker says one complete sentence about that instead of half of a
// real one.
const SENTENCE = /(?<=[.!?])\s+/;

export const TOO_LONG_LINE = "The brief is too long to read aloud here; read the written copy.";

export function splitSentences(text) {
  return String(text == null ? "" : text)
    .replace(/\s+/g, " ")
    .trim()
    .split(SENTENCE)
    .filter(Boolean);
}

export function speakable(text, { maxChars = 280 } = {}) {
  const full = String(text == null ? "" : text).replace(/\s+/g, " ").trim();
  if (!(maxChars > 0)) throw new Error("speakable: maxChars must be positive");
  if (full.length <= maxChars) return { text: full, summarized: false, dropped: 0 };

  const sentences = splitSentences(full);
  const kept = [];
  let used = 0;
  for (const s of sentences) {
    const add = (kept.length ? 1 : 0) + s.length;
    if (used + add > maxChars) break;
    kept.push(s);
    used += add;
  }
  // Zero whole sentences fit: say a whole sentence about the limit. Never a fragment.
  if (kept.length === 0) return { text: TOO_LONG_LINE, summarized: true, dropped: sentences.length };
  return { text: kept.join(" "), summarized: true, dropped: sentences.length - kept.length };
}
