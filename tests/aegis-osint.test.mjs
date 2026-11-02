// Aegis OSINT v1 — fixtures only. No test here touches the network.
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { summarizeCt, summarizeDns, assess, runOsint, renderReport } from "../aegis/osint.mjs";

const CT_ROWS = [
  { name_value: "example.com\nwww.example.com", issuer_name: "R3", not_before: "2024-01-01T00:00:00Z", not_after: "2024-04-01T00:00:00Z" },
  { name_value: "www.example.com", issuer_name: "R3", not_before: "2025-01-01T00:00:00Z", not_after: "2099-01-01T00:00:00Z" },
  { name_value: "*.example.com", issuer_name: "E1", not_before: "2025-06-01T00:00:00Z", not_after: "2099-06-01T00:00:00Z" },
];

test("O1 CT counts certificates and distinct names separately", () => {
  const s = summarizeCt(CT_ROWS);
  assert.equal(s.certificates, 3);
  assert.equal(s.distinctNames, 3, "example.com, www.example.com, *.example.com");
  assert.equal(s.issuers, 2);
  assert.equal(s.expiredCertificates, 1);
  assert.equal(s.firstNotBefore, "2024-01-01T00:00:00.000Z");
});

test("O2 DNS counts by type and reports SPF/DMARC presence without keeping the text", () => {
  const s = summarizeDns({
    A: ["192.0.2.1"], AAAA: [], MX: [{ exchange: "mail.example.com", priority: 10 }], NS: ["ns1.example.com", "ns2.example.com"],
    TXT: [["v=spf1 include:_spf.internal.example.com -all"]], CNAME: [], CAA: [],
    DMARC_TXT: [["v=DMARC1; p=none; rua=mailto:dmarc@example.com"]],
  });
  assert.equal(s.counts.A, 1);
  assert.equal(s.counts.NS, 2);
  assert.equal(s.spf, true);
  assert.equal(s.dmarc, true);
  assert.equal(s.counts.TXT, 1);
  assert.ok(!JSON.stringify(s).includes("internal.example.com"), "the TXT text is not retained");
  assert.ok(!JSON.stringify(s).includes("dmarc@example.com"));
});

test("O3 missing DMARC and SPF become findings; present ones do not", () => {
  const dns = summarizeDns({ A: ["192.0.2.1"], TXT: [], DMARC_TXT: [] });
  const f = assess("example.com", summarizeCt(CT_ROWS), dns);
  // CT_ROWS carries one expired certificate, so the info finding belongs here too: the test
  // fixture is a domain with missing mail policy AND certificate history.
  assert.deepEqual(f.map((x) => x.severity).sort(), ["info", "low", "medium"]);
  const good = summarizeDns({ TXT: [["v=spf1 -all"]], DMARC_TXT: [["v=DMARC1; p=reject"]] });
  assert.deepEqual(assess("example.com", summarizeCt(CT_ROWS), good).map((x) => x.title), [
    "1 expired certificate(s) still published in CT for example.com",
  ]);
});

test("O4 the report prints counts, never a name or an address", () => {
  const result = {
    status: "ran", startedAt: "2026-11-02T00:00:00.000Z", findings: [],
    results: [{
      domain: "example.com", resolved: true, sharedHost: false,
      ct: { ok: true, certificates: 3, distinctNames: 3, issuers: 2, expiredCertificates: 1 },
      dns: { counts: { A: 1, AAAA: 0, MX: 1, NS: 2, TXT: 1, CNAME: 0, CAA: 0 }, spf: true, dmarc: false, missing: [] },
      findings: [],
    }],
  };
  const md = renderReport(result, { runId: "osint-run", domains: ["example.com"] });
  assert.match(md, /distinct names/);
  assert.match(md, /No name, address, or record value is printed/);
  assert.ok(!md.includes("www.example.com"));
  assert.ok(!md.includes("192.0.2.1"));
});

test("O7 a shared parent gets no mail findings, and says why", async () => {
  const { isSharedHost } = await import("../aegis/osint.mjs");
  assert.equal(isSharedHost("meta-os.pages.dev"), true);
  assert.equal(isSharedHost("pages.dev"), true);
  assert.equal(isSharedHost("clipraiders.com"), false);
  const dnsNoMail = summarizeDns({ NS: ["a"], A: ["192.0.2.1"], TXT: [], DMARC_TXT: [] });
  assert.deepEqual(assess("meta-os.pages.dev", summarizeCt([]), dnsNoMail, { sharedHost: true }), []);
  assert.equal(assess("clipraiders.com", summarizeCt([]), dnsNoMail, { sharedHost: false }).length, 2);
});

test("O5 a CT outage is a finding-free row marked unavailable, not a zero that looks clean", async () => {
  const out = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-osint-"));
  const fetchImpl = async () => { throw new Error("network down"); };
  const resolver = {
    resolve4: async () => ["192.0.2.1"], resolve6: async () => { throw new Error("none"); },
    resolveMx: async () => [], resolveNs: async () => ["ns1.example.com"], resolveTxt: async () => [],
    resolveCname: async () => { throw new Error("none"); }, resolveCaa: async () => { throw new Error("none"); },
  };
  const r = await runOsint({ domains: ["example.com"], outDir: out, runId: "osint-blocked", fetchImpl, resolver });
  assert.equal(r.results[0].ct.ok, false);
  assert.equal(r.results[0].findings.length, 0, "a source that did not answer produces no finding");
  const md = renderReport(r, { runId: "osint-blocked", domains: ["example.com"] });
  assert.match(md, /CT unavailable/);
  assert.equal(r.status, "blocked");
});

test("O9 an unresolved domain gets an info note, not mail findings about a name that cannot receive mail", async () => {
  const out = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-osint-"));
  const fetchImpl = async () => ({ ok: true, json: async () => [] });
  const resolver = {
    resolve4: async () => { throw new Error("ENOTFOUND"); }, resolve6: async () => { throw new Error("ENOTFOUND"); },
    resolveMx: async () => { throw new Error("ENOTFOUND"); }, resolveNs: async () => { throw new Error("ENOTFOUND"); },
    resolveTxt: async () => { throw new Error("ENOTFOUND"); }, resolveCname: async () => { throw new Error("ENOTFOUND"); },
    resolveCaa: async () => { throw new Error("ENOTFOUND"); },
  };
  const r = await runOsint({ domains: ["gone.example"], outDir: out, runId: "osint-missing", fetchImpl, resolver });
  assert.deepEqual(r.findings.map((f) => f.severity), ["info"]);
  assert.match(r.findings[0].title, /does not resolve/);
  assert.equal(r.findings.filter((f) => /DMARC|SPF/.test(f.title)).length, 0);
});

test("O8 when every CT query fails the report must not claim a clean mail record", () => {
  const result = {
    status: "blocked", startedAt: "2026-11-02T00:00:00.000Z", findings: [],
    results: [{
      domain: "example.com", resolved: true, sharedHost: false,
      ct: { ok: false, error: "HTTP 503", certificates: 0, distinctNames: 0, issuers: 0, expiredCertificates: 0 },
      dns: { counts: { A: 1, AAAA: 0, MX: 0, NS: 2, TXT: 0, CNAME: 0, CAA: 0 }, spf: false, dmarc: false, missing: [] },
      findings: [],
    }],
  };
  const md = renderReport(result, { runId: "blocked", domains: ["example.com"] });
  assert.match(md, /not a clean result/);
  assert.doesNotMatch(md, /every domain had DMARC and SPF published/);
  assert.match(md, /passed on 0/);
});

test("O6 a reachable CT with DNS gaps files the DMARC finding with the domain as its target", async () => {
  const out = fs.mkdtempSync(path.join(os.tmpdir(), "aegis-osint-"));
  const fetchImpl = async () => ({ ok: true, json: async () => CT_ROWS });
  const resolver = {
    resolve4: async () => ["192.0.2.1"], resolve6: async () => { throw new Error("none"); },
    resolveMx: async () => [], resolveNs: async () => ["ns1.example.com"], resolveTxt: async () => [["v=spf1 -all"]],
    resolveCname: async () => { throw new Error("none"); }, resolveCaa: async () => { throw new Error("none"); },
  };
  const r = await runOsint({ domains: ["example.com"], outDir: out, runId: "osint-run", fetchImpl, resolver });
  assert.equal(r.status, "ran");
  const dmarc = r.findings.find((f) => /DMARC/.test(f.title));
  assert.ok(dmarc, "missing DMARC is a finding");
  assert.equal(dmarc.target, "example.com");
  assert.equal(dmarc.severity, "medium");
});
