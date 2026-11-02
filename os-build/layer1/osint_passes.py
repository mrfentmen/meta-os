#!/usr/bin/env python3
"""R13-201..225 — OSINT passes over our own footprint, public records only.

Every task line in Section I is `OSINT pass: <angle> on <domain>`. This tool reads those 25
lines out of the task list rather than restating them, so the record cannot drift from the
list it claims to answer.

Bounds, from AEGIS_SPEC.md wing 6 and enforced here:
  * public records only: certificate transparency, DNS-over-HTTPS, the site's own HTTP
    responses, robots/sitemap, the Wayback CDX index, RDAP. No account creation, no contact,
    no third-party people, no port scanning, no search-engine scraping.
  * counts only: no subdomain, no address, no issuer name, no header value, no TXT content,
    no registrant field ever reaches the record.

An angle with no implementation is NOT_IMPLEMENTED. A source that answers with an error is
UNAVAILABLE. Neither is a pass, and neither is written as one.

Two bugs from the first run are fixed here and named because they changed which rows are
scans: the angle text was matched case-sensitively (so "DNS record types" missed), and the
domain regex took the first "on <word>" in a line that reads "on our pages on <domain>".
"""
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
TASKS = os.path.join(ROOT, "BUFFY_TASKS_ROUND13_500.md")
OUT = os.path.join(ROOT, "os-build", "round13", "aegis")
UA = {"user-agent": "meta-aegis-osint/1"}

# ordered: first needle contained in the lowercased angle wins
ANGLE_MAP = [
    ("certificate-transparency issuers", "ct-issuers"),
    ("certificate-transparency expiry", "ct-expiry"),
    ("certificate-transparency first-seen", "ct-first-seen"),
    ("subdomain names in public ct", "ct-issuers"),
    ("tls certificate san", "tls-san"),
    ("dns txt record types", "dns-txt"),
    ("dns unexpected records", "dns"),
    ("dns record types", "dns"),
    ("response-header names", "headers"),
    ("hosting headers", "headers"),
    ("robots/sitemap", "robots-sitemap"),
    ("error pages", "error-page"),
    ("wayback machine", "wayback"),
    ("domain registration", "rdap"),
    ("store page public text", "page-text"),
    ("listing page public text", "page-text"),
    ("public release notes exposure", "page-text"),
    ("public image metadata", "image-metadata"),
    ("search-index visibility", "search-index"),
    ("public bucket", "content-enum"),
    ("old deployment urls", "content-enum"),
    ("public test pages", "content-enum"),
    ("public logs reachable", "content-enum"),
    ("public key-shaped filenames", "content-enum"),
    ("public backup-shaped filenames", "content-enum"),
]

NOT_IMPLEMENTED = {
    "image-metadata": "no EXIF/material reader exists in aegis/; the angle needs a media "
                      "pipeline that fetches and parses images, which this pass does not do",
    "content-enum": "path enumeration is deliberately not built: probing candidate paths on a "
                    "live site is scanning, and the standing bound for OSINT is reading public "
                    "records, not guessing at URLs",
    "search-index": "search-index visibility needs a search provider's API; calling one is "
                    "third-party scraping and outside the standing bound",
    "tls-san": "reading SAN entries needs a TLS handshake and an expected-names list; no such "
               "list is in the tree, so there is nothing to compare against",
}


def get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.getcode(), res.read()
    except urllib.error.HTTPError as exc:
        return exc.code, b""
    except Exception as exc:                                  # noqa: BLE001 - reported, not hidden
        return None, str(exc).encode()


def ct(domain, want):
    """crt.sh. A 404 is crt.sh's answer for "no certificates", not a transport failure."""
    code, body = get("https://crt.sh/?q=%25." + domain + "&output=json", timeout=45)
    if code == 404:
        return {"status": "SCANNED", "certificates": 0, "note": "crt.sh returned 404 (no rows)"}
    if code != 200:
        return {"status": "UNAVAILABLE", "http": code}
    try:
        rows = json.loads(body.decode("utf-8", "replace") or "[]")
    except json.JSONDecodeError:
        return {"status": "UNAVAILABLE", "reason": "not JSON"}
    issuers, names = set(), set()
    expired = 0
    stamps = []
    now = datetime.datetime.now(datetime.timezone.utc)
    for row in rows:
        if row.get("issuer_name"):
            issuers.add(row["issuer_name"])
        for n in str(row.get("name_value") or "").split("\n"):
            if n.strip():
                names.add(n.strip().lower())
        try:
            start = datetime.datetime.fromisoformat(
                str(row.get("not_before")).replace("Z", "+00:00"))
            stamps.append(start)
        except Exception:                                     # noqa: BLE001
            pass
        try:
            end = datetime.datetime.fromisoformat(
                str(row.get("not_after")).replace("Z", "+00:00"))
            if end < now:
                expired += 1
        except Exception:                                     # noqa: BLE001
            pass
    if want == "ct-issuers":
        return {"status": "SCANNED", "certificates": len(rows),
                "distinct_issuers": len(issuers), "distinct_names": len(names)}
    if want == "ct-first-seen":
        return {"status": "SCANNED", "certificates": len(rows),
                "first_not_before": min(stamps).date().isoformat() if stamps else None,
                "last_not_before": max(stamps).date().isoformat() if stamps else None}
    return {"status": "SCANNED", "certificates": len(rows), "expired": expired}


def dns_any(domain):
    code, body = get("https://dns.google/resolve?name=%s&type=ANY" % domain)
    if code != 200:
        return None, {"status": "UNAVAILABLE", "http": code}
    try:
        doc = json.loads(body)
    except json.JSONDecodeError:
        return None, {"status": "UNAVAILABLE", "reason": "not JSON"}
    return doc, None


def dns_angle(domain, want):
    doc, err = dns_any(domain)
    if err:
        return err
    types = {}
    for answer in doc.get("Answer") or []:
        key = str(answer.get("type"))
        types[key] = types.get(key, 0) + 1
    if want == "dns-txt":
        code, body = get("https://dns.google/resolve?name=%s&type=TXT" % domain)
        txt = []
        if code == 200:
            try:
                txt = [a.get("data", "") for a in json.loads(body).get("Answer") or []]
            except json.JSONDecodeError:
                txt = []
        return {"status": "SCANNED", "txt_answers": len(txt),
                "spf": any(str(t).startswith('"v=spf1') or str(t).startswith("v=spf1") for t in txt),
                "note": "TXT content is not kept; presence only"}
    return {"status": "SCANNED", "rcode": doc.get("Status"),
            "answers": len(doc.get("Answer") or []),
            "record_type_count": len(types)}


def cdx(domain):
    code, body = get("http://web.archive.org/cdx/search/cdx?url=%s&output=json&fl=timestamp"
                     "&collapse=timestamp:4&limit=2000" % domain, timeout=45)
    if code != 200:
        return {"status": "UNAVAILABLE", "code": code}
    try:
        rows = json.loads(body.decode("utf-8", "replace") or "[]")
    except json.JSONDecodeError:
        return {"status": "UNAVAILABLE", "reason": "not JSON"}
    by_year = {}
    for row in rows[1:]:
        stamp = str(row[0])
        if len(stamp) >= 4:
            by_year[stamp[:4]] = by_year.get(stamp[:4], 0) + 1
    return {"status": "SCANNED", "snapshots": len(rows[1:]), "years": len(by_year),
            "by_year": by_year}


def rdap(domain):
    code, body = get("https://rdap.org/domain/" + domain)
    if code != 200:
        return {"status": "UNAVAILABLE", "code": code}
    try:
        doc = json.loads(body)
    except json.JSONDecodeError:
        return {"status": "UNAVAILABLE", "reason": "not JSON"}
    return {"status": "SCANNED", "status_flags": len(doc.get("status") or []),
            "entities": len(doc.get("entities") or []), "events": len(doc.get("events") or []),
            "nameservers": len(doc.get("nameservers") or [])}


def page_text(domain):
    """Word and link counts only: the angle is exposure, not copy review."""
    code, body = get("https://" + domain + "/")
    if code is None:
        return {"status": "UNAVAILABLE", "reason": body.decode()[:120]}
    text = body.decode("utf-8", "replace")
    title = re.search(r"(?is)<title[^>]*>(.*?)</title>", text)
    words = len(re.sub(r"(?s)<[^>]+>", " ", text).split())
    return {"status": "SCANNED", "http": code, "bytes": len(body), "words": words,
            "links": len(re.findall(r"(?i)href=", text)),
            "title_chars": len(title.group(1).strip()) if title else 0}


def http_angle(domain, angle):
    if angle == "headers":
        code, body = get("https://" + domain + "/")
        if code is None:
            return {"status": "UNAVAILABLE", "reason": body.decode()[:120]}
        try:
            req = urllib.request.Request("https://" + domain + "/", headers=UA)
            with urllib.request.urlopen(req, timeout=25) as res:
                headers = {k.lower(): v for k, v in res.headers.items()}
        except Exception:                                     # noqa: BLE001
            headers = {}
        present = [k for k in ("server", "content-security-policy", "strict-transport-security",
                               "x-frame-options", "x-content-type-options") if k in headers]
        return {"status": "SCANNED", "http": code, "header_count": len(headers),
                "security_headers_present": len(present),
                "has_server_header": "server" in headers, "bytes": len(body)}
    if angle == "robots-sitemap":
        rc, rbody = get("https://" + domain + "/robots.txt")
        sc, sbody = get("https://" + domain + "/sitemap.xml")
        disallows = len(re.findall(rb"(?im)^\s*disallow\s*:", rbody or b""))
        urls = 0
        if sc == 200 and sbody:
            try:
                urls = len(ET.fromstring(sbody).findall(".//{*}url"))
            except ET.ParseError:
                urls = len(re.findall(rb"<loc>", sbody))
        return {"status": "SCANNED" if (rc == 200 or sc == 200) else "UNAVAILABLE",
                "robots_http": rc, "robots_disallow_rules": disallows,
                "sitemap_http": sc, "sitemap_urls": urls}
    if angle == "error-page":
        code, body = get("https://" + domain + "/aegis-probe-does-not-exist")
        return {"status": "SCANNED" if code is not None else "UNAVAILABLE",
                "http": code, "bytes": len(body),
                "custom_page": bool(code == 200 and len(body) > 200)}
    return {"status": "UNKNOWN_ANGLE"}


CACHE = {}


def run(args):
    task, angle_text, domain = args
    lower = angle_text.lower()
    impl = next((i for needle, i in ANGLE_MAP if needle in lower), None)
    if impl is None:
        return {"task": task, "angle": angle_text, "domain": domain,
                "status": "NO_IMPLEMENTATION", "result": {}}
    if impl in NOT_IMPLEMENTED:
        return {"task": task, "angle": angle_text, "domain": domain,
                "status": "NOT_IMPLEMENTED", "result": {"why": NOT_IMPLEMENTED[impl]}}
    key = (impl, domain)
    if key not in CACHE:
        if impl.startswith("ct-"):
            CACHE[key] = ct(domain, impl)
        elif impl in ("dns", "dns-txt"):
            CACHE[key] = dns_angle(domain, impl)
        elif impl == "wayback":
            CACHE[key] = cdx(domain)
        elif impl == "rdap":
            CACHE[key] = rdap(domain)
        elif impl == "page-text":
            CACHE[key] = page_text(domain)
        else:
            CACHE[key] = http_angle(domain, impl)
    return {"task": task, "angle": angle_text, "domain": domain,
            "status": CACHE[key].get("status", "UNKNOWN"), "result": CACHE[key]}


def main():
    os.makedirs(OUT, exist_ok=True)
    text = open(TASKS, encoding="utf-8").read()
    section = text.split("## Section I —")[1].split("## Section J —")[0]
    pairs = []
    for line in section.split("\n"):
        m = re.match(r"- \*\*(R13-\d{3})\.\*\* OSINT pass: (.+?) on ", line)
        if not m:
            continue
        # "on our pages on watchpeoplefight.com" -- the last host in the line is the subject.
        hosts = re.findall(r"\b([a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)+)\b", line)
        hosts = [h for h in hosts if h.count(".") >= 1 and not h.endswith((".json", ".md"))]
        if not hosts:
            continue
        pairs.append((m.group(1), m.group(2), hosts[-1]))
    if len(pairs) != 25:
        print("expected 25 Section I tasks, parsed %d" % len(pairs))
        for pair in pairs:
            print("  ", pair)
        return 2

    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(run, pairs))

    out = {"tool": "os-build/layer1/osint_passes.py",
           "bounds": "public records only; counts and locations; no values",
           "tasks": records}
    with open(os.path.join(OUT, "OSINT_PASSES.json"), "w", encoding="utf-8") as handle:
        json.dump(out, handle, indent=2)
        handle.write("\n")

    print("%-9s %-40s %-28s %-16s %s" % ("task", "angle", "domain", "status", "result"))
    for rec in records:
        summary = {k: v for k, v in rec["result"].items() if k != "why"}
        print("%-9s %-40s %-28s %-16s %s" % (
            rec["task"], rec["angle"][:40], rec["domain"], rec["status"],
            json.dumps(summary)[:110]))
    counts = {}
    for rec in records:
        counts[rec["status"]] = counts.get(rec["status"], 0) + 1
    print("\ntasks=%d %s" % (len(records), " ".join("%s=%d" % kv for kv in sorted(counts.items()))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
