// Meta Aegis — OSINT v1 (AEGIS_SPEC.md, wing 6: "his own footprint, read the way a stranger
// reads it").
//
// Two public sources, both about the boss's own domains and nothing else:
//   - certificate transparency (crt.sh), which lists certificates naming a domain;
//   - DNS, which is public by construction.
//
// The spec's bound is the design: "Addresses and identifiers found in his own public records
// are reported as COUNTS and locations, never republished as values — main is a public repo."
// So this module counts distinct names and issuers and never returns a name, an address, or a
// TXT record's contents. A report that listed the subdomains it found would be the enumeration
// it was supposed to detect.
//
// Not in this file: no port scanning, no host probing, no resolution of anything not named
// below, no search-engine scraping, no account creation. Reading public records is the whole
// method.
import dns from "node:dns/promises";

export const DEFAULT_DOMAINS = [
  "meta-os.pages.dev",
  "muse-relay-live.pages.dev",
  "clipraiders.com",
  "watchpeoplefight.com",
];

// A site under a shared parent does not control that parent's DNS. The owner of
// meta-os.pages.dev cannot publish SPF or DMARC for pages.dev, so "no DMARC" there is not a
// finding about his practice -- filing it would be a false alarm, and false alarms are how a
// real one gets ignored.
export const SHARED_PARENTS = ["pages.dev", "github.io", "vercel.app", "netlify.app"];

export function isSharedHost(domain) {
  const d = String(domain).toLowerCase();
  return SHARED_PARENTS.some((p) => d === p || d.endsWith("." + p));
}

export const CT_URL = (domain) => "https://crt.sh/?q=%25." + encodeURIComponent(domain) + "&output=json";

/* ---------- pure summaries ---------- */

// crt.sh returns one row per certificate per name. Counting rows would count a name once for
// every certificate it appears on, so both numbers are reported: rows are certificates, and
// distinct names are the exposure surface. No name is kept.
export function summarizeCt(rows) {
  const names = new Set();
  const issuers = new Set();
  let expired = 0;
  let earliest = null;
  let latest = null;
  const now = Date.now();
  for (const r of Array.isArray(rows) ? rows : []) {
    if (r.name_value) for (const n of String(r.name_value).split("\n")) names.add(n.trim().toLowerCase());
    if (r.issuer_name) issuers.add(r.issuer_name);
    const t = Date.parse(r.not_before || "");
    if (Number.isFinite(t)) { if (earliest == null || t < earliest) earliest = t; if (latest == null || t > latest) latest = t; }
    const end = Date.parse(r.not_after || "");
    if (Number.isFinite(end) && end < now) expired += 1;
  }
  return {
    certificates: Array.isArray(rows) ? rows.length : 0,
    distinctNames: names.size,
    issuers: issuers.size,
    expiredCertificates: expired,
    firstNotBefore: earliest ? new Date(earliest).toISOString() : null,
    lastNotBefore: latest ? new Date(latest).toISOString() : null,
  };
}

// `records` is what the resolver returned, by type. Every type is attempted; a type that does
// not exist is a zero, not an error -- and the report says which types were asked.
export function summarizeDns(records) {
  const types = ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "CAA"];
  const counts = {};
  for (const t of types) counts[t] = Array.isArray(records[t]) ? records[t].length : 0;
  const txt = (records.TXT || []).map((chunks) => (Array.isArray(chunks) ? chunks.join("") : String(chunks)));
  const dmarc = (records.DMARC_TXT || []).map((chunks) => (Array.isArray(chunks) ? chunks.join("") : String(chunks)));
  return {
    counts,
    spf: txt.some((t) => /^v=spf1\b/i.test(t)),
    dmarc: dmarc.some((t) => /^v=DMARC1\b/i.test(t)),
    // The text of a TXT record is not kept: an SPF record can name internal hosts, and a
    // verification record can carry a token. Presence is the fact that matters here.
  };
}

export function assess(domain, ct, dnsSummary, { sharedHost = false, resolved = true } = {}) {
  const findings = [];
  // Mail policy is only the owner's to publish on a domain he controls, and a name that does
  // not resolve cannot receive mail at all -- "no DMARC" there would be a true sentence about
  // nothing, which is how a findings list fills up with noise nobody reads twice.
  if (resolved && !sharedHost && !dnsSummary.dmarc) {
    findings.push({
      severity: "medium",
      title: "no DMARC record published for " + domain,
      evidence: "DNS query for _dmarc." + domain + " TXT returned no v=DMARC1 record. Without it, a receiver has no policy telling it what to do with mail that fails SPF/DKIM alignment for this domain.",
    });
  }
  if (resolved && !sharedHost && !dnsSummary.spf) {
    findings.push({
      severity: "low",
      title: "no SPF record published for " + domain,
      evidence: "DNS query for " + domain + " TXT returned no v=spf1 record, so nothing states which hosts may send mail as this domain.",
    });
  }
  if (ct.expiredCertificates > 0) {
    findings.push({
      severity: "info",
      title: ct.expiredCertificates + " expired certificate(s) still published in CT for " + domain,
      evidence: "Certificate transparency is append-only, so an expired entry is history and not a live exposure. Counted because a certificate issued for a name nobody remembers owning is worth a look.",
    });
  }
  return findings;
}

/* ---------- the sources ---------- */

async function getJson(url, fetchImpl, timeoutMs = 20000) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetchImpl(url, { signal: ctrl.signal, headers: { "user-agent": "meta-aegis-osint/1" } });
    if (!res.ok) throw new Error("HTTP " + res.status);
    return await res.json();
  } finally { clearTimeout(timer); }
}

export async function queryCt(domain, { fetchImpl = fetch, retryDelayMs = 1500 } = {}) {
  let last = null;
  // crt.sh rate-limits and returns 5xx under load. One retry after a pause is not a fallback to
  // another source; it is the same source asked twice, and a second failure is reported.
  for (let attempt = 0; attempt < 2; attempt++) {
    try { return { ok: true, rows: await getJson(CT_URL(domain), fetchImpl) }; }
    catch (err) {
      last = err;
      if (attempt === 0) await new Promise((r) => setTimeout(r, retryDelayMs));
    }
  }
  return { ok: false, error: String(last && last.message || last).slice(0, 200) };
}

const RESOLVERS = {
  A: (r, d) => r.resolve4(d),
  AAAA: (r, d) => r.resolve6(d),
  MX: (r, d) => r.resolveMx(d),
  NS: (r, d) => r.resolveNs(d),
  TXT: (r, d) => r.resolveTxt(d),
  CNAME: (r, d) => r.resolveCname(d),
  CAA: (r, d) => r.resolveCaa(d),
};

export async function queryDns(domain, { resolver = dns } = {}) {
  const records = {};
  const missing = [];
  for (const [type, fn] of Object.entries(RESOLVERS)) {
    try { records[type] = await fn(resolver, domain); }
    catch { records[type] = []; missing.push(type); }
  }
  try { records.DMARC_TXT = await resolver.resolveTxt("_dmarc." + domain); }
  catch { records.DMARC_TXT = []; }
  return { records, missing };
}

/* ---------- the run ---------- */

export async function runOsint({ domains = DEFAULT_DOMAINS, outDir, client, runId, fetchImpl = fetch, resolver = dns, now = () => new Date() }) {
  const { appendFinding } = await import("./findings.mjs");
  const fs = await import("node:fs");
  const path = await import("node:path");
  fs.mkdirSync(outDir, { recursive: true });
  const startedAt = now().toISOString();
  const results = [];
  const allFindings = [];

  for (const domain of domains) {
    const ctRes = await queryCt(domain, { fetchImpl });
    const ct = ctRes.ok ? summarizeCt(ctRes.rows) : { certificates: 0, distinctNames: 0, issuers: 0, expiredCertificates: 0, firstNotBefore: null, lastNotBefore: null };
    const dnsRes = await queryDns(domain, { resolver });
    const dnsSummary = summarizeDns(dnsRes.records);
    const sharedHost = isSharedHost(domain);
    const resolved = !dnsRes.missing.includes("NS");
    const findings = ctRes.ok ? assess(domain, ct, dnsSummary, { sharedHost, resolved }) : [];
    if (!resolved) {
      findings.unshift({
        severity: "info",
        title: domain + " does not resolve in DNS",
        evidence: "No NS answer from the resolver for " + domain + ". A domain in the boss's own list that does not resolve is worth knowing about (expired, unregistered, or mis-typed); mail findings are deliberately not filed for it because a name that cannot resolve cannot receive mail.",
      });
    }
    const row = {
      domain, sharedHost,
      // No NS answer is the closest thing to "this name does not exist"; it is reported as
      // absence rather than as a set of zeroes that reads like a clean record.
      resolved,
      ct: { ok: ctRes.ok, error: ctRes.error || null, ...ct },
      dns: { ...dnsSummary, missing: dnsRes.missing }, findings,
    };
    results.push(row);
    for (const f of findings) {
      allFindings.push(appendFinding(path.join(outDir, "findings.jsonl"), {
        severity: f.severity, title: f.title, evidence: f.evidence,
        source: "crt.sh certificate transparency + DNS (public records), via aegis/osint.mjs",
        run: runId, target: domain,
      }));
    }
  }
  return { status: results.some((r) => r.ct.ok) ? "ran" : "blocked", results, findings: allFindings, startedAt, finishedAt: now().toISOString() };
}

/* ---------- the report ---------- */

export function renderReport(result, { runId, domains = DEFAULT_DOMAINS } = {}) {
  const lines = [];
  lines.push("# Aegis OSINT v1 — public footprint, counts only");
  lines.push("");
  lines.push("Run `" + runId + "`, " + result.startedAt + ". Domains named by the boss: " + domains.map((d) => "`" + d + "`").join(", ") + ".");
  lines.push("");
  lines.push("Sources: **crt.sh** certificate transparency (public log) and **DNS** (public by construction). No host was contacted, no port was probed, and nothing outside these four names was resolved.");
  lines.push("");
  lines.push("## Per domain");
  lines.push("");
  lines.push("| domain | resolves | CT certs | distinct names | issuers | expired | A | AAAA | MX | NS | TXT | CAA | SPF | DMARC |");
  lines.push("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|");
  for (const r of result.results) {
    const c = r.dns.counts;
    lines.push("| `" + r.domain + "`" + (r.ct.ok ? "" : " (CT unavailable)") + " | " + (r.resolved ? "yes" : "**no**") +
      " | " + r.ct.certificates + " | " + r.ct.distinctNames +
      " | " + r.ct.issuers + " | " + r.ct.expiredCertificates + " | " + c.A + " | " + c.AAAA + " | " + c.MX +
      " | " + c.NS + " | " + c.TXT + " | " + c.CAA + " | " + (r.dns.spf ? "yes" : "no") + " | " + (r.dns.dmarc ? "yes" : "no") + " |");
  }
  lines.push("");
  const notes = [];
  for (const r of result.results) {
    if (r.resolved === false) notes.push("- `" + r.domain + "` got no NS answer: that row is absence, not a clean record.");
    if (r.sharedHost) notes.push("- `" + r.domain + "` is under a shared parent, so SPF and DMARC are not the site owner's to publish and are not filed as findings.");
    if (!r.ct.ok) notes.push("- `" + r.domain + "`: certificate transparency was unavailable, so that column is unknown, not zero.");
  }
  if (notes.length) {
    lines.push("## Notes on this footprint");
    lines.push("");
    for (const n of notes) lines.push(n);
    lines.push("");
  }
  lines.push("");
  lines.push("**No name, address, or record value is printed.** The counts are the finding; the names behind them are one query away for anyone who owns the domain, and publishing them here would do the enumerator's work.");
  lines.push("");
  lines.push("## Findings");
  lines.push("");
  if (!result.findings.length) {
    // The sentence has to follow the data. An earlier version said "every domain had DMARC and
    // SPF published" even when CT was down and the mail columns read "no" -- a clean bill of
    // health assembled out of missing answers. That is the exact failure this report exists to
    // avoid, so the claim is now computed, and when the source did not answer it says so.
    const total = result.results.length;
    const ctUnknown = result.results.filter((r) => !r.ct.ok).length;
    const mailChecked = result.results.filter((r) => !r.sharedHost && r.resolved !== false).length;
    const mailOk = result.results.filter((r) => !r.sharedHost && r.resolved !== false && r.dns.spf && r.dns.dmarc).length;
    if (ctUnknown === total) {
      lines.push("**No findings, and not a clean result.** Certificate transparency was unavailable for all " + total +
        " domain(s), so that column is unknown; mail policy was checked on " + mailChecked + " domain(s) and passed on " + mailOk + ".");
    } else {
      lines.push("None filed. Certificate transparency answered for " + (total - ctUnknown) + " of " + total +
        " domain(s); mail policy passed on " + mailOk + " of " + mailChecked + " where it is the owner's to publish.");
    }
  } else {
    for (const f of result.findings) lines.push("- **" + f.severity + "** — " + f.title);
  }
  lines.push("");
  lines.push("## What this does not claim");
  lines.push("");
  lines.push("- CT counts are what crt.sh returned at this time; the log is append-only but the index is not instant.");
  lines.push("- A \"distinct name\" is a name on a certificate, not a name that resolves, and not a host that is up.");
  lines.push("- No search-index, store-listing, or repository-metadata review is in this run.");
  lines.push("- No mail authentication was tested by sending anything; SPF/DMARC presence is a DNS fact only.");
  lines.push("");
  return lines.join("\n");
}
