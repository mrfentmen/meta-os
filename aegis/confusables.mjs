// Meta Aegis — D4, the unicode-confusable scan (R11-233).
//
// A name that renders like another name is a spoof with a Unicode character in it. This scans the
// shipped MCP server names and tool prefixes for characters from outside Latin that have a Latin
// lookalike, and for invisible format characters. It reports position and code point; it never
// "normalises" the name, because a scanner that rewrites its subject hides the thing it found.
export const CONFUSABLES = new Map([
  ["\u0430", "a"], ["\u0435", "e"], ["\u043e", "o"], ["\u0440", "p"], ["\u0441", "c"],
  ["\u0443", "y"], ["\u0445", "x"], ["\u0455", "s"], ["\u0456", "i"], ["\u0458", "j"],
  ["\u04bb", "h"], ["\u0501", "d"], ["\u051b", "q"], ["\u051d", "w"],
  ["\u03b1", "a"], ["\u03b2", "b"], ["\u03b5", "e"], ["\u03b9", "i"], ["\u03ba", "k"],
  ["\u03bd", "v"], ["\u03bf", "o"], ["\u03c1", "p"], ["\u03c4", "t"], ["\u03c5", "u"],
  ["\u03c7", "x"], ["\u03f2", "c"], ["\u03f3", "j"],
  ["\u2010", "-"], ["\u2011", "-"], ["\u2012", "-"], ["\u2013", "-"], ["\u2212", "-"],
  ["\u200b", ""], ["\u200c", ""], ["\u200d", ""], ["\u2060", ""], ["\ufeff", ""],
]);

export const INVISIBLE = new Set(["\u200b", "\u200c", "\u200d", "\u2060", "\ufeff"]);

export function scanName(name) {
  const text = String(name == null ? "" : name);
  const hits = [];
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (!CONFUSABLES.has(ch)) continue;
    hits.push({
      index: i,
      char: ch,
      codePoint: "U+" + ch.codePointAt(0).toString(16).toUpperCase().padStart(4, "0"),
      looksLike: CONFUSABLES.get(ch),
      invisible: INVISIBLE.has(ch),
    });
  }
  const scripts = new Set();
  for (const ch of text) {
    if (/[A-Za-z]/.test(ch)) scripts.add("Latin");
    else if (/[\u0400-\u04ff]/.test(ch)) scripts.add("Cyrillic");
    else if (/[\u0370-\u03ff]/.test(ch)) scripts.add("Greek");
  }
  return { name: text, hits, mixedScript: scripts.size > 1, scripts: [...scripts] };
}

// names: [{ name, kind }]. Only a non-Latin character that looks Latin is a finding; a wholly
// Cyrillic name is not a spoof of an English one, it is just another name.
export function scanNames(names) {
  const findings = [];
  for (const n of names) {
    const r = scanName(n.name);
    if (r.hits.length) findings.push({ ...n, ...r });
  }
  return { scanned: names.length, findings };
}
