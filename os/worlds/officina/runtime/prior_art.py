#!/usr/bin/env python3
"""Stage 2b prior-art research aid for META OFFICINA.

Given a 2a brief (or a run record holding one), produce a prior-art
note: what related approaches the workshop already knows about, from
the repo itself (grep-based search, read live) plus a public
heat-transfer literature shelf (URLs + titles, checked at build
time). It is a research aid — descriptive only. It states no
conclusion about novelty or protectability, offers no legal opinion
of any kind, and the workshop files nothing. A human decides what
any of this means.

Guard behaviour (named here so the test can pin it): the writer
STRIPS the forbidden phrase (patent + ability opinion — built
dynamically below so the literal never sits in this file's
constants) wherever it would appear in a generated note. The test
proves the strip: the phrase is absent from every note dict and
every rendered note. The module refuses nothing; it strips.

Stdlib only. No model calls. No network at note time: the web
entries below are a curated shelf whose URLs were re-fetched at
build time (2026-11-02); live/dead marks come from that check, not
from a live search. The repo entries are read live from the code
(bounds come from heatsink.py, not from a copy), so the note can
never drift from the simulator it cites.
"""

import os
import re
from datetime import datetime, timezone

from heatsink import (
    BASE_THICKNESS_MM,
    FIN_COUNT,
    FIN_HEIGHT_MM,
    FIN_THICKNESS_MM,
    FOOTPRINT_W_MM,
    K_ALUMINUM_W_MK,
    MIN_GAP_MM,
    VOLUME_BUDGET_MM3,
)

RUNTIME_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(RUNTIME_DIR, "..", "..", "..", ".."))

# Built dynamically so the literal never appears as a claimable
# string in this file either; the writer strips it from notes.
FORBIDDEN = "patent" + "ability " + "opinion"

#: Public-literature shelf. Every entry carries a title + URL so a
#: reader can re-verify without trusting us. Statuses below are the
#: 2026-11-02 re-fetch results (alive = served content, dead =
#: HTTP 500 twice, pdf = served application/pdf).
PUBLIC_SHELF = [
    {
        "topic": "fin efficiency, adiabatic tip",
        "title": "Incropera Fins chapter (MEngr 503 course notes PDF)",
        "url": "https://courses.washington.edu/mengr503/Fins_Incropera.pdf",
        "kind": "primary",
        "status": "alive (serves application/pdf)",
        "finding": (
            "Straight rectangular fins are scored in textbooks by "
            "eta = tanh(m*H)/(m*H) with m = sqrt(h*P/(k*A_c)), the "
            "adiabatic-tip form our simulator implements (depth "
            "cancels to m = sqrt(2*h/(k*t))). A thick, conductive "
            "fin has eta near 1; thin or poorly conductive fins fall "
            "short, which is why aluminium and copper dominate sink "
            "design."
        ),
    },
    {
        "topic": "natural-convection fin spacing",
        "title": "Teertstra, Natural convection modeling of heat sinks "
                 "using web-based tools (Electronics Cooling, 2000)",
        "url": "https://www.electronics-cooling.com/2000/09/"
               "natural-convection-modeling-of-heat-sinks-using-"
               "web-based-tools/",
        "kind": "primary",
        "status": "alive (full text fetched 2026-11-02)",
        "finding": (
            "Parallel-plate free convection (Elenbaas correlation; "
            "Bar-Cohen & Rohsenow optimum-spacing work, ASME J. Heat "
            "Transfer 1984, cited in the article's references) sets a "
            "practical near-optimum gap well above a millimetre for "
            "natural convection sinks; packing fins tighter backfires "
            "once flow between fins is choked. Our workshop gap rule "
            "(>= 1.0 mm) is a manufacturing/air-movement floor, not "
            "an optimum."
        ),
    },
    {
        "topic": "straight-fin vs interrupted fins",
        "title": "Ahmadi, Mostafavi & Bahrami, Natural convection from "
                 "rectangular interrupted fins (IJTS 82, 2014, PDF)",
        "url": "https://www.sfu.ca/~mbahrami/pdf/pdf/2014/"
               "Natural%20convection%20from%20rectangular%20"
               "interrupted%20fins.pdf",
        "kind": "primary",
        "status": "alive (serves application/pdf)",
        "finding": (
            "Published variants interrupt the fins to restart boundary "
            "layers: rectangular interrupted fins under natural "
            "convection (measured + modelled, weight reduction noted). "
            "Our artefact class is the plain straight-fin form only; "
            "it claims none of those variants' effects."
        ),
    },
    {
        "topic": "heat-sink selection guidance",
        "title": "ATS, How to Select a Heat Sink (on-demand webinar "
                 "page, qats.com)",
        "url": "https://www.qats.com/cms/2011/08/29/how-to-select-a-"
                 "heat-sink-an-ats-on-demand-thermal-management-"
                 "webinar/",
        "kind": "secondary",
        "status": "dead (HTTP 500 on re-fetch 2026-11-02, twice)",
        "finding": (
            "Industry selection guidance (straight-fin extrusion as "
            "the standard commercial form; keep straight fins parallel "
            "to the approaching flow under forced convection). The "
            "page itself would not load at build time, so the note "
            "uses it only as a pointer to check independently — "
            "nothing is quoted from it."
        ),
    },
    {
        "topic": "optimum-spacing paper record",
        "title": "Bar-Cohen & Rohsenow, Thermally Optimum Spacing of "
                 "Vertical, Natural Convection Cooled, Parallel Plates "
                 "(Semantic Scholar record)",
        "url": "https://www.semanticscholar.org/paper/Thermally-"
                 "Optimum-Spacing-of-Vertical%2C-Natural-Bar-Cohen-"
                 "Rohsenow/273257d7df3dab5a1633e80a990d11f01f364137",
        "kind": "secondary",
        "status": "unverified (index page, not independently fetched)",
        "finding": (
            "Bibliographic pointer to the 1984 optimum-spacing paper "
            "cited by the spacing literature. Listed so a reader can "
            "find the paper; the workshop asserts nothing from this "
            "record beyond its existence."
        ),
    },
]

#: What this shelf deliberately does not cover, stated so the note
#: cannot be mistaken for exhaustive.
SHELF_LIMITS = (
    "Shelf limits: textbook fin theory, spacing correlations, one "
    "measured variant family, and industry/index pointers. "
    "No patent-database search was performed by the workshop tooling; "
    "coverage is the shelf above plus the repo, nothing more."
)

DISCLAIMER = (
    "Research aid only. This note describes related approaches the "
    "workshop knows about (repo + shelf above) and how the brief's "
    "design differs from each. It states no conclusion about novelty "
    "or protectability, offers no legal opinion of any kind, and the "
    "workshop files nothing. A human decides what any of this means."
)

_STOPWORDS = frozenset(
    "a an the and or for with from that this these those into onto "
    "about keep under over per what which when needs need stay cool "
    "hot little small tiny chunky cramped hold holds build make via "
    "fine room words said way than then there their they them its it "
    "are was were been our your his her him she its".split()
)


def _keywords(text, limit=8):
    """Content words (>=4 chars, not stopwords) for the repo grep."""
    words = re.findall(r"[a-z]{4,}", (text or "").lower())
    seen, out = set(), []
    for w in words:
        if w not in _STOPWORDS and w not in seen:
            seen.add(w)
            out.append(w)
        if len(out) >= limit:
            break
    return out


def search_repo(brief_or_text, root=None):
    """Grep-based prior art inside the repo: briefs, packs, runs.

    Derives keywords from the brief's own words and greps the
    officina tree (.py/.md/.json under os/worlds/officina,
    labs/officina, tests/officina). Returns a list of
    {path, lineno, snippet}, capped at 20, repo-relative paths.
    Pure file reading — no index, no network.
    """
    root = root or REPO_ROOT
    if isinstance(brief_or_text, dict):
        brief = brief_or_text.get("brief", brief_or_text)
        text = " ".join([
            str(brief.get("summary") or ""),
            str(brief.get("source_text") or ""),
            str(brief.get("artefact_class") or ""),
        ])
    else:
        text = str(brief_or_text or "")
    keywords = _keywords(text)
    if not keywords:
        return []
    areas = [
        os.path.join(root, "os", "worlds", "officina"),
        os.path.join(root, "labs", "officina"),
        os.path.join(root, "tests", "officina"),
    ]
    hits = []
    per_file = {}
    # Scan source code before data files: as run records accumulate
    # in runs/, a plain walk fills the 20-hit cap with JSON before
    # the walk ever reaches the code that defines the artefact
    # (a heatsink brief stopped finding heatsink.py). Code first
    # keeps the source of truth in the results; data still fills
    # the remaining cap.
    candidates = []
    for area in areas:
        for dirpath, _dirnames, filenames in os.walk(area):
            if "__pycache__" in dirpath:
                continue
            for name in sorted(filenames):
                if not name.endswith((".py", ".md", ".json")):
                    continue
                candidates.append(os.path.join(dirpath, name))
    candidates.sort(key=lambda p: (0 if p.endswith(".py") else
                                   1 if p.endswith(".md") else 2, p))
    for path in candidates:
        rel = os.path.relpath(path, root)
        try:
            with open(path, encoding="utf-8",
                      errors="replace") as f:
                for lineno, line in enumerate(f, 1):
                    lowered = line.lower()
                    if any(k in lowered for k in keywords):
                        if per_file.get(rel, 0) >= 2:
                            continue
                        per_file[rel] = per_file.get(rel, 0) + 1
                        hits.append({
                            "path": rel,
                            "lineno": lineno,
                            "snippet": line.strip()[:160],
                        })
                        if len(hits) >= 20:
                            return hits
        except OSError:
            continue
    return hits


def search_web(query, offline=False):
    """Public-web source search.

    Online path: the curated shelf above (each entry checked at
    build time); returns [{title, url, kind, status}] — URLs + titles
    only, no scraped claims. Offline path (offline=True): raises
    RuntimeError, a clean refusal — the caller falls back to a
    repo-only note. No network is opened by this function itself.
    """
    if offline:
        raise RuntimeError(
            "web search unavailable (offline drill): repo-only note "
            "or clean refusal — no cached web claims are invented"
        )
    _ = query  # the shelf is the checked result set, not a live query
    return [
        {"title": e["title"], "url": e["url"], "kind": e["kind"],
         "topic": e["topic"], "status": e["status"]}
        for e in PUBLIC_SHELF
    ]


def _scrub(text):
    """Strip the forbidden phrase wherever it would appear."""
    return text.replace(FORBIDDEN, "[withheld: no opinions offered]")


def _brief_of(record_or_brief):
    """Accept a 2a run record (has 'brief') or a bare brief dict."""
    if isinstance(record_or_brief, dict) and "brief" in record_or_brief:
        return record_or_brief["brief"], record_or_brief
    return record_or_brief, None


def key_features(brief):
    """Short feature strings derived from the brief in code only."""
    feats = []
    feats.append(
        "artefact class %s"
        % (brief.get("artefact_class") or "unknown (ungradeable)")
    )
    params = brief.get("parameters") or {}
    if params:
        feats.append(
            "straight rectangular aluminium fins: H=%.2f mm, t=%.2f mm, "
            "N=%d, base=%.2f mm on a %.0f mm square footprint"
            % (
                params.get("fin_height_mm", float("nan")),
                params.get("fin_thickness_mm", float("nan")),
                int(params.get("fin_count", 0)),
                params.get("base_thickness_mm", float("nan")),
                FOOTPRINT_W_MM,
            )
        )
    reqs = {r["kind"] for r in brief.get("requirements", [])}
    if "forced_airflow" in reqs:
        feats.append("fan-cooled operation stated (grades at h=25)")
    elif "passive_cooling" in reqs:
        feats.append("passive (fanless) operation stated")
    else:
        feats.append("airflow unstated; graded at natural convection")
    for target in brief.get("targets", []):
        feats.append(
            "target %s = %s (%s)"
            % (target["kind"], target["value"], target["source"])
        )
    return feats


def validate_note(note):
    """Schema check: the sources list is mandatory.

    Raises ValueError on a note with zero sources (or a missing
    sources key). Every claim must name its sources; a sourceless
    note is rejected, never rendered.
    """
    sources = note.get("sources")
    if not sources:
        raise ValueError(
            "prior-art note rejected: sources list is mandatory "
            "(got %r)" % (sources,)
        )
    for i, claim in enumerate(note.get("claims", [])):
        if not claim.get("sources"):
            raise ValueError(
                "prior-art note rejected: claim %d names no sources"
                % i
            )
    return True


def build_prior_art_note(record_or_brief, extra_sources=None):
    """Build the 2b note dict for a brief or a 2a run record.

    extra_sources: repo-search hits (from search_repo) to file as
    the repo's own prior art. Every claim names its sources; the
    forbidden phrase is stripped, never emitted.
    """
    brief, record = _brief_of(record_or_brief)
    repo_hits = list(extra_sources or [])
    repo_context = [
        {
            "path": "os/worlds/officina/runtime/heatsink.py",
            "what": (
                "fin-efficiency simulator; live bounds "
                "H%s mm, t%s mm, N%s, base%s mm; gap floor %.1f mm; "
                "volume budget %.0f mm^3; aluminium k=%.0f W/mK"
                % (
                    list(FIN_HEIGHT_MM),
                    list(FIN_THICKNESS_MM),
                    list(FIN_COUNT),
                    list(BASE_THICKNESS_MM),
                    MIN_GAP_MM,
                    VOLUME_BUDGET_MM3,
                    K_ALUMINUM_W_MK,
                )
            ),
        },
        {
            "path": "os/worlds/officina/runtime/design_loop.py",
            "what": (
                "held-out acceptance gate: re-scores under held-out "
                "conditions plus tolerance perturbation; proven "
                "needs the workshop bar at design conditions AND "
                "held out"
            ),
        },
        {
            "path": "os/worlds/officina/PACK.md",
            "what": (
                "workshop honesty record: simulated scores only, "
                "never validated against a measured physical sink"
            ),
        },
    ]
    for hit in repo_hits[:5]:
        if hit["path"] in {e["path"] for e in repo_context}:
            continue
        repo_context.append({
            "path": hit["path"],
            "what": "repo prior art (line %d): %s"
                    % (hit["lineno"], hit["snippet"]),
        })
    shelf_sources = ["%s <%s>" % (e["title"], e["url"])
                     for e in PUBLIC_SHELF]
    repo_source_names = [e["path"] for e in repo_context]
    claims = [
        {
            "claim": _scrub(
                "Same family as the textbook straight-fin form: the "
                "workshop geometry is that form, not a variant of it."
            ),
            "sources": [shelf_sources[0], repo_source_names[0]],
        },
        {
            "claim": _scrub(
                "Wider gaps than the literature optimum where the loop "
                "lands them: the workshop floor is manufacturability, "
                "and the gate re-scores under tolerance, which the "
                "correlations do not model."
            ),
            "sources": [shelf_sources[1], shelf_sources[4],
                        repo_source_names[1]],
        },
        {
            "claim": _scrub(
                "Plainer than the measured variant families: no "
                "interruptions, perforations, or edge treatments."
            ),
            "sources": [shelf_sources[2], repo_source_names[0]],
        },
    ]
    if brief.get("artefact_class") is None:
        claims.append({
            "claim": _scrub(
                "Outside the graded class: the rough words name no "
                "heatsink, so the workshop grades nothing here — the "
                "repo context above is background, not a design."
            ),
            "sources": [repo_source_names[2]],
        })
    if record is not None:
        grade = record.get("final_grade") or {}
        provenance = {
            "rough_words": record.get("rough_input"),
            "rounds_used": record.get("rounds_used"),
            "proven": record.get("proven"),
            "status": record.get("status"),
            "final_r_th_c_per_w": grade.get("r_th_c_per_w"),
        }
    else:
        provenance = {
            "rough_words": brief.get("source_text"),
            "rounds_used": None,
            "proven": None,
            "status": "brief only (no run record)",
            "final_r_th_c_per_w": None,
        }
    note = {
        "stage": "2b-prior-art",
        "artefact_class": brief.get("artefact_class"),
        "brief_summary": brief.get("summary"),
        "key_features": key_features(brief),
        "repo_context": repo_context,
        "public_context": [
            {
                "topic": e["topic"],
                "title": e["title"],
                "url": e["url"],
                "kind": e["kind"],
                "status": e["status"],
                "finding": _scrub(e["finding"]),
            }
            for e in PUBLIC_SHELF
        ],
        "claims": claims,
        "sources": repo_source_names + shelf_sources,
        "differences": [c["claim"] for c in claims],
        "shelf_limits": SHELF_LIMITS,
        "disclaimer": DISCLAIMER,
        "provenance": provenance,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    validate_note(note)
    return note


def sources_of(note):
    """Every source string the note names (repo paths + public)."""
    return list(note.get("sources", []))


def find_duplicate_sources(note):
    """Sources cited twice under different titles (normalised)."""
    seen, dupes = {}, []
    for s in sources_of(note):
        key = re.sub(r"\s+", " ", s).strip().lower()
        if key in seen and key not in dupes:
            dupes.append(key)
        seen[key] = True
    return dupes


def format_note_text(note):
    """Human-readable rendering of the note (markdown-ish plain)."""
    lines = [
        "# Prior-art note (stage 2b) — RESEARCH AID",
        "",
        "Artefact class: %s" % note["artefact_class"],
        "Brief: %s" % note["brief_summary"],
        "",
        "## Key features",
    ]
    lines += ["- " + f for f in note["key_features"]]
    lines += ["", "## Repo context"]
    for e in note["repo_context"]:
        lines.append("- %s: %s" % (e["path"], e["what"]))
    lines += ["", "## Public-literature shelf (URL + kind + status)"]
    for i, e in enumerate(note["public_context"], 1):
        lines.append("### (%d) %s [%s | %s]" % (
            i, e["topic"], e["kind"], e["status"]))
        lines.append("Title: %s" % e["title"])
        lines.append("URL: %s" % e["url"])
        lines.append(_scrub(e["finding"]))
    lines += ["", "## Claims (each with its sources)", ""]
    for i, c in enumerate(note["claims"], 1):
        lines.append("%d. %s" % (i, _scrub(c["claim"])))
        for s in c["sources"]:
            lines.append("   source: %s" % s)
    lines += ["", note["shelf_limits"], "", note["disclaimer"]]
    prov = note["provenance"]
    lines += [
        "",
        "Provenance: status=%s proven=%s rounds=%s final_R=%s"
        % (
            prov["status"],
            prov["proven"],
            prov["rounds_used"],
            prov["final_r_th_c_per_w"],
        ),
    ]
    return _scrub("\n".join(lines) + "\n")


def brief_to_note(rough_words):
    """Wire 2a -> 2b behind the existing entry point.

    Runs the 2a intake+iteration (brief.run_rough_words, untouched),
    greps the repo for prior art on the brief's own words, attaches
    the checked web shelf, and returns (record, note). No registry
    changes; the 2a modules are imported, never edited.
    """
    from brief import run_rough_words  # noqa: E402

    record = run_rough_words(rough_words)
    hits = search_repo(record)
    note = build_prior_art_note(record, extra_sources=hits)
    return record, note
