// Meta Aegis — CISA KEV cross-check (R12-002).
//
// A dependency finding is not "exploited in the wild" until the KEV catalogue says so. This file
// makes that a field, never an inference: every finding is looked up by the CVEs in its id and
// its published aliases, and the result is one of `kev: true` (with the KEV row), `kev: false`
// (checked, not listed), or `kev: null` (no CVE to check — the source published only an advisory
// id). Null is not a pass.
export const KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json";

export function indexKev(doc) {
  const rows = new Map();
  for (const v of (doc && doc.vulnerabilities) || []) {
    if (v && v.cveID) rows.set(String(v.cveID).toUpperCase(), {
      cveID: v.cveID,
      vendorProject: v.vendorProject || null,
      product: v.product || null,
      name: v.vulnerabilityName || null,
      dateAdded: v.dateAdded || null,
      ransomware: v.knownRansomwareCampaignUse || "Unknown",
    });
  }
  return { rows, count: rows.size, catalogVersion: doc && doc.catalogVersion, dateReleased: doc && doc.dateReleased };
}

const CVE = /\bCVE-\d{4}-\d{4,}\b/gi;

export function cvesIn(finding) {
  const text = [finding.title, finding.evidence, finding.target].filter(Boolean).join(" ");
  return [...new Set((text.match(CVE) || []).map((c) => c.toUpperCase()))];
}

export function kevStatus(finding, kev) {
  const cves = cvesIn(finding);
  if (!cves.length) {
    return { kev: null, reason: "no CVE in the finding (advisory id only); KEV cannot be checked", cves };
  }
  for (const cve of cves) {
    const hit = kev.rows.get(cve);
    if (hit) return { kev: true, cve, row: hit, cves };
  }
  return { kev: false, reason: "checked against KEV, not listed", cves };
}

export function crossCheck(findings, kev) {
  const rows = findings.map((f) => ({ finding: f, ...kevStatus(f, kev) }));
  return {
    checked: rows.length,
    flagged: rows.filter((r) => r.kev === true).length,
    unchecked: rows.filter((r) => r.kev === null).length,
    rows,
    catalog: { count: kev.count, version: kev.catalogVersion, released: kev.dateReleased, source: KEV_URL },
  };
}

export function renderKev(result, { runId } = {}) {
  const lines = [];
  lines.push("# Aegis KEV cross-check — " + (result.flagged ? result.flagged + " exploited-in-the-wild" : "no exploited-in-the-wild findings"));
  lines.push("");
  lines.push("Run `" + runId + "`. Catalogue: " + result.catalog.count + " entries, released " + (result.catalog.released || "unknown") + ", from " + KEV_URL + ".");
  lines.push("");
  lines.push("| item | count |");
  lines.push("|---|---|");
  lines.push("| findings checked | " + result.checked + " |");
  lines.push("| flagged KEV | " + result.flagged + " |");
  lines.push("| not checked (no CVE) | " + result.unchecked + " |");
  if (result.excludedNonSweep != null) lines.push("| non-sweep records excluded | " + result.excludedNonSweep + " |");
  lines.push("");
  if (!result.checked) {
    lines.push("**Zero findings to check.** That is a real result only if the sweep ran; if the sweep was");
    lines.push("blocked, this file says nothing about the dependencies.");
  } else {
    lines.push("| finding | KEV | CVE |");
    lines.push("|---|---|---|");
    for (const r of result.rows) {
      lines.push("| " + r.finding.title.replace(/\|/g, "\\|") + " | " +
        (r.kev === true ? "**YES**" : r.kev === false ? "no" : "unchecked") + " | " +
        (r.cves.length ? r.cves.join(", ") : "—") + " |");
    }
    lines.push("");
    if (result.unchecked) lines.push(result.unchecked + " finding(s) carry no CVE and are recorded as **unchecked**, not clean.");
  }
  lines.push("");
  return lines.join("\n");
}
