// Surfaces boards (HN-056…HN-070): pure renderers for the boards page.
// Every renderer takes data and returns an HTML string; nothing here
// fetches, guesses, or invents records. A board with no records renders
// an honest empty state, never a placeholder row. All text is escaped.

export function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// HN-056 Lab board: experiments list reading the lab's records.
// Rule (V3): no level is EVER shown higher than the record's cap. When
// a record claims a level above its cap, the board shows the cap value
// with a "(capped)" marker and never prints the higher number anywhere.
export function labBoard(records) {
  const rows = Array.isArray(records) ? records : [];
  if (rows.length === 0) {
    return `<p class="empty-state">No lab experiments recorded yet.</p>`;
  }
  const items = rows.map((r) => {
    const level = Number(r?.ladder_level);
    const cap = Number(r?.cap);
    const shown = Number.isFinite(level) && Number.isFinite(cap)
      ? Math.min(level, cap)
      : (Number.isFinite(level) ? level : null);
    const capped = Number.isFinite(level) && Number.isFinite(cap) && level > cap;
    const levelText = shown === null ? "—" : `Level ${shown}${capped ? " (capped)" : ""}`;
    return `<li class="lab-row" data-lab-id="${escapeHtml(r?.id ?? "")}">`
      + `<span class="lab-hypothesis">${escapeHtml(r?.hypothesis ?? "—")}</span> `
      + `<span class="lab-level">${escapeHtml(levelText)}</span> `
      + `<span class="lab-status">${escapeHtml(r?.status ?? "—")}</span></li>`;
  }).join("");
  return `<ul class="lab-list">${items}</ul>`;
}
