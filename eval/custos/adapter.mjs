// Meta Custos eval adapter (first slice).
//
// Custos was already built and pinning-tested on main (os/worlds/custos/
// runtime/patrol.py, scheduler.py, dedup.py, false_positives.py, and
// tests/custos/), but eval/ had no custos harness, so there was no
// Custos baseline for "whatever raises eval scores" to be measured
// against. This is that first harness: a replay of the patrol's own
// rules through the real code.
//
// Two mechanisms, both real code, both tmp-only, never a live host:
//   - CLI scenarios spawn the real patrol.py / scheduler.py entry
//     points with fixture feed files (--kev-file, --ct-file,
//     --dns-file) and a tmp state dir. With hosts [] there is no
//     probe at all; with fixture feeds there is no feed fetch.
//   - Probe scenarios spawn eval/custos/probe_driver.py, which calls
//     patrol.run_patrol directly with every signal injected — the
//     same method tests/custos/ uses (fake feeds, fake probes).
//     Host checks (cert, liveness, exposure, headers, TLS,
//     subdomains, dedup) cannot run through the CLI without real
//     network, so they run here, labelled injected in the evidence.
//   - The pack scenario runs the real world validator
//     (os/worlds/validate_pack.py) on the Custos manifest.
//
// What it is not:
//   - Not a live patrol. No watched host is probed, no real KEV/CT/
//     DNS feed is fetched, nothing is patched, restarted, or
//     reconfigured, and no escalation ever leaves the SIMULATED
//     endpoint — the harness asserts exactly that.
//   - Not a registry check. Custos has no agents/registry.json entry
//     on main (its pack agents are patrol-runner, watch-scribe and
//     escalation-messenger, not registry agents); that gap is noted
//     in the README, not scored here, and no registry entry is
//     invented to make a scenario pass.
//   - Not a scheduler replacement proof. The scheduler scenario pins
//     the cycle contract (due sources run, the immediate next cycle
//     runs nothing but still writes its cycle record); the committed
//     runs/scheduler-cycle-proof.jsonl is the fixture-cycle proof,
//     not something this harness rewrites — runs/ is byte-identical
//     before and after, asserted in adapter.test.mjs.

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.dirname(path.dirname(here));
const PATROL = path.join(root, "os", "worlds", "custos", "runtime", "patrol.py");
const SCHEDULER = path.join(root, "os", "worlds", "custos", "runtime", "scheduler.py");
const DRIVER = path.join(here, "probe_driver.py");
const VALIDATOR = path.join(root, "os", "worlds", "validate_pack.py");
const PACK = path.join(root, "os", "worlds", "custos", "pack.json");

const KEV_OPENSSL = { cveID: "CVE-2014-0160", vendorProject: "OpenSSL", product: "OpenSSL", dateAdded: "2022-05-04" };
const KEV_APACHE_OLD = { cveID: "CVE-2021-42013", vendorProject: "Apache", product: "HTTP Server", dateAdded: "2021-11-03" };
const KEV_OPENSSL_NEW = { cveID: "CVE-2024-0001", vendorProject: "OpenSSL", product: "OpenSSL", dateAdded: "2024-05-01" };
const KEV_WIDGET = { cveID: "CVE-2024-9999", vendorProject: "Acme", product: "Widget", dateAdded: "2024-05-02" };
const CT_LETSENCRYPT = { id: 123456789, common_name: "letsencrypt.org", issuer_name: "Let's Encrypt Authority X3", not_before: "2019-05-01T00:00:00Z", not_after: "2019-07-30T00:00:00Z" };
const ALL_HEADERS = ["strict-transport-security", "content-security-policy", "x-frame-options", "x-content-type-options", "referrer-policy"];
const STRONG_TLS = { version: "TLSv1.3", cipher: "TLS_AES_256_GCM_SHA384" };

function check(cond, evidence) {
  return { pass: Boolean(cond), evidence };
}

function withTmp(fn) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "custos-eval-"));
  try {
    return fn(dir);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

function writeJson(dir, name, value) {
  const p = path.join(dir, name);
  fs.writeFileSync(p, JSON.stringify(value, null, 2) + "\n");
  return p;
}

function readRecords(p) {
  if (!fs.existsSync(p)) return [];
  return fs.readFileSync(p, "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l));
}

function runPy(args) {
  const r = spawnSync("python3", args, { encoding: "utf8" });
  return { status: r.status, stdout: r.stdout || "", stderr: r.stderr || "" };
}

function obs(records, category) {
  return records.filter((r) => r.record_type === "observation" && r.category === category);
}

function summaryOf(records) {
  return records.find((r) => r.record_type === "patrol-summary");
}

function escalationsOf(records) {
  return records.filter((r) => r.record_type === "escalation");
}

function baseConfig(extra) {
  return {
    hosts: [],
    inventory: ["openssl"],
    cert_warn_days: 21,
    kev_age_red_days: 30,
    sensitive_ports: [22, 3306, 5432, 6379, 9200, 27017],
    ...extra,
  };
}

// One CLI patrol run in a tmp dir. Returns { records, summary, status, stderr }.
function cliPatrol(dir, name, config, feeds) {
  const configPath = writeJson(dir, name + "-config.json", config);
  const recordsPath = path.join(dir, name + "-records.jsonl");
  const statePath = path.join(dir, name + "-state.json");
  const args = ["run", "--config", configPath, "--records", recordsPath, "--state", statePath];
  if (feeds.kev) args.push("--kev-file", writeJson(dir, name + "-kev.json", { vulnerabilities: feeds.kev }));
  if (feeds.ct) args.push("--ct-file", writeJson(dir, name + "-ct.json", feeds.ct));
  if (feeds.dns) args.push("--dns-file", writeJson(dir, name + "-dns.json", feeds.dns));
  if (feeds.review) args.push("--review", feeds.review);
  const r = runPy([PATROL, ...args]);
  const records = readRecords(recordsPath);
  return { records, summary: summaryOf(records), status: r.status, stderr: r.stderr, statePath, recordsPath };
}

function cliPatrolSharedState(dir, name, config, feeds, statePath) {
  const configPath = writeJson(dir, name + "-config.json", config);
  const recordsPath = path.join(dir, name + "-records.jsonl");
  const args = ["run", "--config", configPath, "--records", recordsPath, "--state", statePath];
  if (feeds.kev) args.push("--kev-file", writeJson(dir, name + "-kev.json", { vulnerabilities: feeds.kev }));
  if (feeds.ct) args.push("--ct-file", writeJson(dir, name + "-ct.json", feeds.ct));
  if (feeds.dns) args.push("--dns-file", writeJson(dir, name + "-dns.json", feeds.dns));
  if (feeds.review) args.push("--review", feeds.review);
  const r = runPy([PATROL, ...args]);
  const records = readRecords(recordsPath);
  return { records, summary: summaryOf(records), status: r.status, stderr: r.stderr, recordsPath };
}

function driverRun(dir, name, spec) {
  const specPath = writeJson(dir, name + "-spec.json", spec);
  const r = runPy([DRIVER, specPath]);
  if (r.status !== 0) return { error: r.stderr.trim() || "driver exit " + r.status, runs: [] };
  return JSON.parse(r.stdout);
}

function assessKev01() {
  return withTmp((dir) => {
    const { records, summary, status } = cliPatrol(dir, "kev", baseConfig({}), { kev: [KEV_OPENSSL, KEV_WIDGET] });
    const kev = obs(records, "known-exploited vulnerability present");
    const esc = escalationsOf(records);
    const good = status === 0 && kev.length === 1 && kev[0].tier === "red" &&
      kev[0].detail.cve === "CVE-2014-0160" && esc.length === 1 &&
      esc[0].endpoint === "SIMULATED" &&
      JSON.stringify(esc[0].steps) === JSON.stringify(["record", "notify", "page", "ticket"]) &&
      summary && summary.escalations === 1 && summary.errors.length === 0;
    return check(good, "KEV obs " + kev.length + " (CVE-2014-0160, red), escalations " + esc.length +
      " to " + (esc[0] ? esc[0].endpoint : "none") + ", summary errors " + (summary ? summary.errors.length : "?"));
  });
}

function assessKevDedupe01() {
  return withTmp((dir) => {
    const config = baseConfig({});
    const statePath = path.join(dir, "shared-state.json");
    const run1 = cliPatrolSharedState(dir, "d1", config, { kev: [KEV_OPENSSL] }, statePath);
    const run2 = cliPatrolSharedState(dir, "d2", config, { kev: [KEV_OPENSSL] }, statePath);
    const good = obs(run1.records, "known-exploited vulnerability present").length === 1 &&
      obs(run2.records, "known-exploited vulnerability present").length === 0;
    return check(good, "run1 KEV obs " + obs(run1.records, "known-exploited vulnerability present").length +
      ", run2 KEV obs " + obs(run2.records, "known-exploited vulnerability present").length);
  });
}

function assessKevAge01() {
  return withTmp((dir) => {
    const { records } = cliPatrol(dir, "age",
      baseConfig({ inventory: ["openssl", "apache http server"] }),
      { kev: [KEV_OPENSSL_NEW, KEV_APACHE_OLD] });
    const kev = obs(records, "known-exploited vulnerability present");
    const good = kev.length === 2 &&
      kev[0].detail.date_added === "2021-11-03" &&
      kev[1].detail.date_added === "2024-05-01" &&
      kev.every((k) => k.detail.aged === true && k.detail.days_since_listing > 30);
    return check(good, "KEV order " + kev.map((k) => k.detail.date_added).join(",") +
      ", aged " + kev.map((k) => String(k.detail.aged)).join(","));
  });
}

function assessCt01() {
  return withTmp((dir) => {
    const { records, summary } = cliPatrol(dir, "ct",
      baseConfig({ ct_domains: ["letsencrypt.org"] }), { kev: [], ct: [CT_LETSENCRYPT] });
    const ct = obs(records, "certificate issued");
    const good = ct.length === 1 && ct[0].tier === "yellow" && ct[0].detail.ct_id === 123456789 &&
      escalationsOf(records).length === 0 && summary && summary.escalations === 0;
    return check(good, "CT obs " + ct.length + " (id 123456789, yellow), escalations " + escalationsOf(records).length);
  });
}

function assessCtDedupe01() {
  return withTmp((dir) => {
    const config = baseConfig({ ct_domains: ["letsencrypt.org"] });
    const statePath = path.join(dir, "shared-state.json");
    const run1 = cliPatrolSharedState(dir, "c1", config, { kev: [], ct: [CT_LETSENCRYPT] }, statePath);
    const run2 = cliPatrolSharedState(dir, "c2", config, { kev: [], ct: [CT_LETSENCRYPT] }, statePath);
    const good = obs(run1.records, "certificate issued").length === 1 &&
      obs(run2.records, "certificate issued").length === 0;
    return check(good, "run1 CT obs " + obs(run1.records, "certificate issued").length +
      ", run2 CT obs " + obs(run2.records, "certificate issued").length);
  });
}

function assessDns01() {
  return withTmp((dir) => {
    const config = baseConfig({ dns_domains: ["example.org"] });
    const statePath = path.join(dir, "shared-state.json");
    const snap1 = { "example.org": { A: ["93.184.216.34"], AAAA: [], MX: [], TXT: [] } };
    const snap2 = { "example.org": { A: ["93.184.216.35"], AAAA: [], MX: [], TXT: [] } };
    const run1 = cliPatrolSharedState(dir, "n1", config, { kev: [], dns: snap1 }, statePath);
    const run2 = cliPatrolSharedState(dir, "n2", config, { kev: [], dns: snap2 }, statePath);
    const drift = obs(run2.records, "dns drift");
    const good = obs(run1.records, "dns drift").length === 0 && drift.length === 1 &&
      drift[0].tier === "yellow" &&
      JSON.stringify(drift[0].detail.added.A) === JSON.stringify(["93.184.216.35"]) &&
      JSON.stringify(drift[0].detail.removed.A) === JSON.stringify(["93.184.216.34"]);
    return check(good, "run1 drift " + obs(run1.records, "dns drift").length +
      ", run2 drift " + drift.length + " added " + JSON.stringify(drift[0] ? drift[0].detail.added : null) +
      " removed " + JSON.stringify(drift[0] ? drift[0].detail.removed : null));
  });
}

function assessFp01() {
  return withTmp((dir) => {
    const reviewPath = path.join(dir, "review.jsonl");
    const d = runPy([PATROL, "dismiss", "--review", reviewPath,
      "--category", "known-exploited vulnerability present",
      "--key", "CVE-2014-0160", "--reason", "test dismissal: recorded verdict fixture"]);
    const { records, summary } = cliPatrol(dir, "fp", baseConfig({}),
      { kev: [KEV_OPENSSL], review: reviewPath });
    const kev = obs(records, "known-exploited vulnerability present");
    const dismissed = records.filter((r) => r.record_type === "dismissed");
    const good = d.status === 0 && kev.length === 0 && escalationsOf(records).length === 0 &&
      summary && summary.false_positives_suppressed === 1 && dismissed.length === 1;
    return check(good, "dismiss exit " + d.status + ", KEV obs " + kev.length +
      ", dismissed records " + dismissed.length + ", suppressed " +
      (summary ? summary.false_positives_suppressed : "?"));
  });
}

function hostSpec(hosts, probes, extra) {
  return {
    config: baseConfig({
      hosts,
      inventory: [],
      ...extra,
    }),
    kev_feed: [],
    ct_feed: [],
    dns_feed: null,
    runs: 1,
    probes,
  };
}

function assessCert01() {
  return withTmp((dir) => {
    const hosts = [
      { host: "up.example", port: 443, expected_ports: [443] },
      { host: "expired.example", port: 443, expected_ports: [443] },
      { host: "healthy.example", port: 443, expected_ports: [443] },
    ];
    const { runs, error } = driverRun(dir, "cert", hostSpec(hosts, {
      cert_days: { "up.example": 10, "expired.example": -5, "healthy.example": 90 },
      ports: { "up.example:443": true, "expired.example:443": true, "healthy.example:443": true },
      headers: { "up.example": ALL_HEADERS, "expired.example": ALL_HEADERS, "healthy.example": ALL_HEADERS },
      tls: { "up.example": STRONG_TLS, "expired.example": STRONG_TLS, "healthy.example": STRONG_TLS },
      subdomains: {},
    }));
    if (error) return check(false, "driver error: " + error);
    const records = runs[0];
    const cert = records.filter((r) => r.source === "cert");
    const byHost = Object.fromEntries(cert.map((r) => [r.host, r.category]));
    const esc = escalationsOf(records);
    const good = byHost["up.example"] === "certificate expiring" &&
      byHost["expired.example"] === "certificate expired" &&
      byHost["healthy.example"] === "baseline normal" &&
      esc.length === 1 && esc[0].for_category === "certificate expired";
    return check(good, "injected probes: cert " + JSON.stringify(byHost) + ", escalations " + esc.length);
  });
}

function assessExposure01() {
  return withTmp((dir) => {
    const hosts = [
      { host: "exposed.example", port: 443, expected_ports: [443] },
      { host: "down.example", port: 443, expected_ports: [443] },
    ];
    const { runs, error } = driverRun(dir, "exp", hostSpec(hosts, {
      cert_days: { "exposed.example": 90 },
      ports: { "exposed.example:443": true, "exposed.example:3306": true, "down.example:443": false },
      headers: { "exposed.example": ALL_HEADERS },
      tls: { "exposed.example": STRONG_TLS },
      subdomains: {},
    }));
    if (error) return check(false, "driver error: " + error);
    const records = runs[0];
    const exp = obs(records, "anomalous exposure");
    const down = obs(records, "service down");
    const esc = escalationsOf(records);
    const good = exp.length === 1 && exp[0].tier === "yellow" && exp[0].detail.port === 3306 &&
      down.length === 1 && down[0].tier === "red" && esc.length === 1;
    return check(good, "injected probes: exposure " + exp.length + " (port " +
      (exp[0] ? exp[0].detail.port : "?") + ", yellow), service down " + down.length + ", escalations " + esc.length);
  });
}

function assessHeaders01() {
  return withTmp((dir) => {
    const hosts = [
      { host: "gapped.example", port: 443, expected_ports: [443] },
      { host: "clean.example", port: 443, expected_ports: [443] },
    ];
    const { runs, error } = driverRun(dir, "hdr", hostSpec(hosts, {
      cert_days: { "gapped.example": 90, "clean.example": 90 },
      ports: { "gapped.example:443": true, "clean.example:443": true },
      headers: { "gapped.example": ["strict-transport-security", "x-frame-options"], "clean.example": ALL_HEADERS },
      tls: { "gapped.example": STRONG_TLS, "clean.example": STRONG_TLS },
      subdomains: {},
    }));
    if (error) return check(false, "driver error: " + error);
    const records = runs[0];
    const hdr = records.filter((r) => r.source === "headers");
    const byHost = Object.fromEntries(hdr.map((r) => [r.host, r]));
    const good = byHost["gapped.example"] && byHost["gapped.example"].category === "security headers missing" &&
      byHost["gapped.example"].tier === "yellow" &&
      JSON.stringify(byHost["gapped.example"].detail.missing) ===
        JSON.stringify(["content-security-policy", "x-content-type-options", "referrer-policy"]) &&
      byHost["clean.example"] && byHost["clean.example"].category === "baseline normal";
    return check(good, "injected probes: gapped missing " +
      JSON.stringify(byHost["gapped.example"] ? byHost["gapped.example"].detail.missing : null) +
      ", clean " + (byHost["clean.example"] ? byHost["clean.example"].category : "?"));
  });
}

function assessTls01() {
  return withTmp((dir) => {
    const hosts = [
      { host: "weak.example", port: 443, expected_ports: [443] },
      { host: "strong.example", port: 443, expected_ports: [443] },
    ];
    const { runs, error } = driverRun(dir, "tls", hostSpec(hosts, {
      cert_days: { "weak.example": 90, "strong.example": 90 },
      ports: { "weak.example:443": true, "strong.example:443": true },
      headers: { "weak.example": ALL_HEADERS, "strong.example": ALL_HEADERS },
      tls: {
        "weak.example": { version: "TLSv1.1", cipher: "TLS_RSA_WITH_AES_128_CBC_SHA" },
        "strong.example": STRONG_TLS,
      },
      subdomains: {},
    }));
    if (error) return check(false, "driver error: " + error);
    const records = runs[0];
    const tls = records.filter((r) => r.source === "tls");
    const byHost = Object.fromEntries(tls.map((r) => [r.host, r]));
    const good = byHost["weak.example"] && byHost["weak.example"].category === "tls configuration drift" &&
      byHost["weak.example"].tier === "yellow" &&
      byHost["strong.example"] && byHost["strong.example"].category === "baseline normal";
    return check(good, "injected probes: weak " + (byHost["weak.example"] ? byHost["weak.example"].category : "?") +
      " (" + (byHost["weak.example"] ? byHost["weak.example"].detail.grade_reason : "?") + "), strong " +
      (byHost["strong.example"] ? byHost["strong.example"].category : "?"));
  });
}

function assessSubdomain01() {
  return withTmp((dir) => {
    const spec = {
      config: baseConfig({
        inventory: [],
        ct_domains: ["example.org"],
        subdomain_expected_networks: { "example.org": ["203.0.113.0/24"] },
      }),
      kev_feed: [],
      ct_feed: [
        { id: 1, common_name: "api.example.org", not_before: "2026-01-01T00:00:00Z" },
        { id: 2, common_name: "www.example.org", not_before: "2026-01-01T00:00:00Z" },
      ],
      dns_feed: null,
      runs: 1,
      probes: { cert_days: {}, ports: {}, headers: {}, tls: {}, subdomains: { "api.example.org": ["198.51.100.7"], "www.example.org": ["203.0.113.5"] } },
    };
    const { runs, error } = driverRun(dir, "sub", spec);
    if (error) return check(false, "driver error: " + error);
    const records = runs[0];
    const sub = records.filter((r) => r.source === "subdomain");
    const byHost = Object.fromEntries(sub.map((r) => [r.host, r]));
    const good = byHost["api.example.org"] && byHost["api.example.org"].category === "subdomain unexpected network" &&
      byHost["api.example.org"].tier === "yellow" &&
      JSON.stringify(byHost["api.example.org"].detail.unexpected_addresses) === JSON.stringify(["198.51.100.7"]) &&
      byHost["www.example.org"] && byHost["www.example.org"].category === "baseline normal";
    return check(good, "injected probes: api " + (byHost["api.example.org"] ? byHost["api.example.org"].category : "?") +
      ", www " + (byHost["www.example.org"] ? byHost["www.example.org"].category : "?"));
  });
}

function assessDedup01() {
  return withTmp((dir) => {
    const spec = hostSpec(
      [{ host: "gapped.example", port: 443, expected_ports: [443] }],
      {
        cert_days: { "gapped.example": 90 },
        ports: { "gapped.example:443": true },
        headers: { "gapped.example": ["strict-transport-security", "x-frame-options"] },
        tls: { "gapped.example": STRONG_TLS },
        subdomains: {},
      },
      { dedup_window_seconds: 86400 },
    );
    spec.runs = 2;
    const { runs, error } = driverRun(dir, "dedup", spec);
    if (error) return check(false, "driver error: " + error);
    const run1Hdr = obs(runs[0], "security headers missing").length;
    const run2Hdr = obs(runs[1], "security headers missing").length;
    const run2Summary = summaryOf(runs[1]);
    const good = run1Hdr === 1 && run2Hdr === 0 && run2Summary && run2Summary.dedup_suppressed >= 1;
    return check(good, "injected probes: run1 headers-missing " + run1Hdr + ", run2 " + run2Hdr +
      ", run2 dedup_suppressed " + (run2Summary ? run2Summary.dedup_suppressed : "?"));
  });
}

function assessSched01() {
  return withTmp((dir) => {
    const config = baseConfig({
      inventory: ["openssl"],
      cadence: { kev: "24h", ct: "1h", dns: "6h", subdomain: "6h", hosts: "15m" },
    });
    const configPath = writeJson(dir, "sched-config.json", config);
    const kevPath = writeJson(dir, "sched-kev.json", { vulnerabilities: [KEV_OPENSSL] });
    const statePath = path.join(dir, "sched-state.json");
    const schedStatePath = path.join(dir, "sched-sched.json");
    const runCycle = (name) => {
      const recordsPath = path.join(dir, name + "-records.jsonl");
      const r = runPy([SCHEDULER, "run", "--config", configPath, "--records", recordsPath,
        "--state", statePath, "--scheduler-state", schedStatePath, "--kev-file", kevPath]);
      return { records: readRecords(recordsPath), status: r.status, stderr: r.stderr };
    };
    const c1 = runCycle("c1");
    const c2 = runCycle("c2");
    const cycle1 = c1.records.find((r) => r.record_type === "scheduler-cycle");
    const cycle2 = c2.records.find((r) => r.record_type === "scheduler-cycle");
    const good = c1.status === 0 && c2.status === 0 &&
      cycle1 && cycle1.sources_run.includes("kev") &&
      c2.records.every((r) => r.record_type === "scheduler-cycle") &&
      cycle2 && cycle2.sources_run.length === 0;
    return check(good, "cycle1 sources_run " + JSON.stringify(cycle1 ? cycle1.sources_run : null) +
      ", cycle2 records " + c2.records.length + " (all cycle records), cycle2 sources_run " +
      JSON.stringify(cycle2 ? cycle2.sources_run : null));
  });
}

function assessPack01() {
  const r = runPy([VALIDATOR, PACK]);
  const pack = JSON.parse(fs.readFileSync(PACK, "utf8"));
  const sends = (pack.cross_world && pack.cross_world.sends) || [];
  const good = r.status === 0 && pack.status === "partial" &&
    sends.length >= 1 && sends.every((s) => Array.isArray(s.never_carries) && s.never_carries.length > 0);
  return check(good, "validator exit " + r.status + ", pack status " + pack.status +
    ", cross-world sends " + sends.length + ", never_carries " +
    JSON.stringify(sends.map((s) => s.never_carries.length)));
}

function assessEmpty01() {
  return withTmp((dir) => {
    const { records, summary, status } = cliPatrol(dir, "empty", baseConfig({ inventory: [] }), { kev: [] });
    const good = status === 0 && records.length === 1 && summary &&
      summary.escalations === 0 && summary.errors.length === 0 &&
      Object.values(summary.observations).every((v) => v === 0);
    return check(good, "records " + records.length + " (summary only), escalations " +
      (summary ? summary.escalations : "?") + ", errors " + (summary ? summary.errors.length : "?"));
  });
}

const CHECKS = {
  "CU-KEV-01": () => assessKev01(),
  "CU-KEV-DEDUPE-01": () => assessKevDedupe01(),
  "CU-KEV-AGE-01": () => assessKevAge01(),
  "CU-CT-01": () => assessCt01(),
  "CU-CT-DEDUPE-01": () => assessCtDedupe01(),
  "CU-DNS-01": () => assessDns01(),
  "CU-FP-01": () => assessFp01(),
  "CU-CERT-01": () => assessCert01(),
  "CU-EXPOSURE-01": () => assessExposure01(),
  "CU-HEADERS-01": () => assessHeaders01(),
  "CU-TLS-01": () => assessTls01(),
  "CU-SUBDOMAIN-01": () => assessSubdomain01(),
  "CU-DEDUP-01": () => assessDedup01(),
  "CU-SCHED-01": () => assessSched01(),
  "CU-PACK-01": () => assessPack01(),
  "CU-EMPTY-01": () => assessEmpty01(),
};

export function assessCustos(scenario) {
  const fn = CHECKS[scenario.id];
  if (!fn) return { pass: false, evidence: "no checker for scenario " + scenario.id };
  try {
    return fn();
  } catch (err) {
    return { pass: false, evidence: "error: " + err.message };
  }
}

export function runCustosEval(scenarios, assess) {
  return scenarios.map((s) => {
    let result;
    try {
      result = assess(s);
    } catch (err) {
      result = { pass: false, evidence: "error: " + err.message };
    }
    return { id: s.id, title: s.title, pass: result.pass === true, evidence: result.evidence || "" };
  });
}
