#!/usr/bin/env python3
"""SAM-regions -> Spark-reasoning eval pipeline (agent3-models lane).

One pipeline, two labelled sets, regions in / assessment out:

  * SAM pairs  (os/intel/evals/sam/pairs.json): each half (PNG) goes
    through a segmentation step (SAM regions) and a reasoning step
    (Spark verdict build-ok / build-broken), scored against the
    manifest's ground-truth labels.
  * Ignis 20   (eval/ignis/scenarios.json, frozen benchmark): each
    scenario goes through regions + reasoning to an ignis category,
    scored against ground_truth_label / alert_expected with the
    legacy alert definition (alert only for visible smoke /
    visible flame), the same math as eval/ignis/adapter.mjs.

Providers are injectable. Two ship here:

  * fixture (OFFLINE, default): deterministic stand-ins, zero
    network, zero key. fixture_segments() maps a firing-half PNG to
    one stable box and a quiet-half PNG to no regions (by the
    pair filename convention, stated plainly below); the fixture
    reasoners map regions-present -> alert verdict. These numbers
    exercise the harness, they are not detection and not a model.
  * live (Del's runbook only): real SAM 3.1 segmentation plus real
    Muse Spark reasoning through server/queue/models.py
    (SPARK_API_KEY from the environment, spark_guardrail $75 hard
    stop inside). Raises before sending anything when no key is
    configured -- never a fabricated assessment.

Spend: every reasoning call records one entry shaped exactly like
intel.store.record_spend entries ({ts, lane_feature, tokens_in,
tokens_out, est_cost, usage}) via the injected store (the real
intel.store on a live bus, a capture fake in tests, a local-only
ledger when no bus exists). Cost estimates use the guardrail rate
card ($1.25/M input, $4.25/M output, estimates only -- the same
rates server/queue/spark_guardrail.py logs). The ledger write is
observability: a ledger failure is recorded on the run, never a
run failure (same rule as intel/spark_client.py).

Usage (offline):
  python3 os/intel/sam_spark.py --mode fixture --out <run.json>
Usage (live, Del holds SPARK_API_KEY -- see sam_spark_runbook.md):
  python3 os/intel/sam_spark.py --mode live --out <run.json>
"""

import argparse
import hashlib
import json
import os
import struct
import sys
import time

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
OS_ROOT = os.path.dirname(THIS_DIR)
REPO_ROOT = os.path.dirname(OS_ROOT)

SAM_DIR_DEFAULT = os.path.join(THIS_DIR, "evals", "sam")
IGNIS_SCENARIOS_DEFAULT = os.path.join(
    REPO_ROOT, "eval", "ignis", "scenarios.json")

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

# Legacy (frozen-benchmark) alert definition: only these fire an alert.
IGNIS_ALERT_CATEGORIES_LEGACY = ("visible smoke", "visible flame")

# Guardrail rate card (estimates only, NOT pricing facts).
RATE_IN_PER_MTOK = 1.25
RATE_OUT_PER_MTOK = 4.25

FIXTURE_SAM_MODEL = "fixture-sam-standin"
FIXTURE_SPARK_MODEL = "fixture-spark-standin"


class PipelineError(RuntimeError):
    """A pipeline failure (bad input, unparseable model reply, ...)."""


class LiveNotConfigured(PipelineError):
    """Live mode refused: no key / no transport, nothing was sent."""


# --- PNG helpers (stdlib only) -------------------------------------------

def png_size(png_bytes):
    """(width, height) from the IHDR chunk; raises on non-PNG."""
    if not png_bytes or png_bytes[:8] != PNG_MAGIC:
        raise PipelineError("image is not a PNG (magic bytes missing)")
    if len(png_bytes) < 24:
        raise PipelineError("PNG too short for an IHDR chunk")
    width, height = struct.unpack(">II", png_bytes[16:24])
    if width <= 0 or height <= 0:
        raise PipelineError("PNG has non-positive dimensions")
    return width, height


def _stable_box(seed_bytes):
    """One deterministic 0-1000 box from seed bytes (fixture only)."""
    digest = hashlib.sha256(seed_bytes).digest()
    x = int.from_bytes(digest[0:2], "big") % 801
    y = int.from_bytes(digest[2:4], "big") % 801
    w = 100 + int.from_bytes(digest[4:6], "big") % 401
    h = 100 + int.from_bytes(digest[6:8], "big") % 401
    w = min(w, 1000 - x)
    h = min(h, 1000 - y)
    return {"x": x, "y": y, "w": w, "h": h}


# --- fixture providers (OFFLINE, deterministic, no network) --------------

def fixture_segments(png_bytes, filename=""):
    """Stand-in for SAM segmentation (OFFLINE fixture, NOT SAM).

    Returns {"regions": [...], "model": ..., "image_size": {...}}.
    Rule, stated plainly: a half whose filename contains "firing"
    yields one stable box (derived from the file bytes); any other
    name yields no regions. This keys off the eval set's filename
    convention, so the offline SAM number exercises the harness
    plumbing, not detection. Raises on non-PNG bytes.
    """
    width, height = png_size(png_bytes)
    regions = []
    if "firing" in (filename or ""):
        regions = [_stable_box(png_bytes)]
    return {
        "regions": regions,
        "model": FIXTURE_SAM_MODEL,
        "image_size": {"w": width, "h": height},
    }


def fixture_regions_for_scenario(scenario):
    """Stand-in regions for an ignis scenario (OFFLINE fixture).

    alert_expected scenes yield one stable box (seeded by the
    scenario id); the rest yield no regions. Fixture only.
    """
    if not isinstance(scenario, dict) or not scenario.get("scenario_id"):
        raise PipelineError("scenario needs a scenario_id")
    if scenario.get("alert_expected"):
        seed = ("ignis:" + str(scenario["scenario_id"])).encode()
        return [_stable_box(seed)]
    return []


def fixture_reason_sam(pair_id, regions):
    """Fixture Spark verdict for a SAM half: regions in, label out.

    Any region present -> "build-broken", else "build-ok".
    Fixture only; the live path asks Muse Spark (see below).
    """
    del pair_id  # the fixture verdict keys off regions alone
    label = "build-broken" if regions else "build-ok"
    return {
        "label": label,
        "summary": ("fixture verdict: %d region(s), %s"
                    % (len(regions), label)),
        "model": FIXTURE_SPARK_MODEL,
    }


def fixture_reason_ignis(scenario, regions):
    """Fixture Spark assessment for an ignis scenario.

    Regions present -> "visible smoke", else "no hazard visible".
    Deliberately coarse (documented misses: every visible-flame
    truth is called smoke -- the alert still fires, the category
    is wrong; every non-alert non-empty truth is called quiet).
    Fixture only.
    """
    category = "visible smoke" if regions else "no hazard visible"
    return {
        "product": "ignis",
        "category": category,
        "summary": ("fixture assessment for %s: %d region(s) -> %s"
                    % (scenario.get("scenario_id"), len(regions),
                       category)),
        "requires_human_review": bool(scenario.get("review_expected")),
        "model": FIXTURE_SPARK_MODEL,
    }


# --- live providers (Del's runbook only; never called offline) -----------

def _require_live_key():
    if not os.environ.get("SPARK_API_KEY"):
        raise LiveNotConfigured(
            "SPARK_API_KEY is not set in the environment: live mode "
            "refused, nothing was sent")


def _models_module():
    sys.path.insert(0, os.path.join(REPO_ROOT, "server", "queue"))
    try:
        import models
    except ImportError as exc:
        raise LiveNotConfigured(
            "server/queue/models.py is not importable: %s" % exc)
    return models


def live_segments(image_bytes, prompt_text):
    """Real SAM 3.1 segmentation via server/queue/models.segment."""
    _require_live_key()
    models = _models_module()
    record = models.segment(image_bytes, prompt_text)
    return {
        "regions": [record["region"]] if record.get("region") else [],
        "model": record.get("model", models.SAM),
        "latency_ms": record.get("latency_ms"),
        "raw": record,
    }


def build_sam_prompt(pair_id, viewport, regions):
    """Verdict prompt for Spark over SAM regions (live path)."""
    return "\n".join([
        "You are assessing a dashboard alerts panel for a build "
        "monitor (pair %s, viewport %s)." % (pair_id, viewport),
        "SAM segmentation reports these regions of interest "
        "(0-1000 scale, possibly empty): %s."
        % json.dumps(regions, sort_keys=True),
        "Return JSON ONLY, no prose: "
        '{"label": "build-ok" or "build-broken", '
        '"summary": "<one sentence>"}.',
        'Verdict "build-broken" only when a region visibly shows '
        "firing/open alerts; an empty region list with no other "
        'evidence is "build-ok".',
    ])


def build_ignis_prompt(scenario, regions):
    """Assessment prompt for Spark over regions (live path)."""
    return "\n".join([
        "You are the visual assessment model for Meta Ignis.",
        "Scene: %s"
        % scenario.get("expected_observable_condition", ""),
        "SAM segmentation reports these regions of interest "
        "(0-1000 scale, possibly empty): %s."
        % json.dumps(regions, sort_keys=True),
        "Return JSON ONLY, no prose: "
        '{"category": "<one of: visible smoke, visible flame, '
        "no hazard visible, steam or fog, flame-like lighting, "
        'obscured or distant hazard, indeterminate>", '
        '"summary": "<one sentence>", '
        '"requires_human_review": <true|false>}.',
        "Alert only for visible smoke or visible flame. When unsure, "
        "use indeterminate with requires_human_review true.",
    ])


def _extract_json(text):
    """Tolerate fences/prose around the object; raise when no object."""
    t = (text or "").strip()
    if t.startswith("```"):
        lines = t.split("\n")[1:]
        t = "\n".join(lines).strip()
        if t.endswith("```"):
            t = t[:-3].strip()
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise PipelineError(
            "model reply carried no JSON object: %r" % (text or "")[:120])
    try:
        obj = json.loads(t[start:end + 1])
    except ValueError as exc:
        raise PipelineError("model reply is not JSON: %s" % exc)
    if not isinstance(obj, dict):
        raise PipelineError("model reply is not a JSON object")
    return obj


def live_reason_sam(pair_id, viewport, regions, image_bytes=None):
    """Real Spark verdict over SAM regions (live path)."""
    _require_live_key()
    models = _models_module()
    prompt = build_sam_prompt(pair_id, viewport, regions)
    if image_bytes is not None:
        text, model, latency = models.chat_image(
            models.SPARK, prompt, image_bytes)
    else:
        text, model, latency = models.chat_text(models.SPARK, prompt)
    obj = _extract_json(text)
    if obj.get("label") not in ("build-ok", "build-broken"):
        raise PipelineError(
            "model verdict has no build-ok/build-broken label: %r"
            % (obj.get("label"),))
    return {"label": obj["label"],
            "summary": obj.get("summary", ""),
            "model": model, "latency_ms": latency,
            "usage": {"prompt_chars": len(prompt),
                      "reply_chars": len(text)}}


def live_reason_ignis(scenario, regions):
    """Real Spark assessment over regions (live path, text-only)."""
    _require_live_key()
    models = _models_module()
    prompt = build_ignis_prompt(scenario, regions)
    text, model, latency = models.chat_text(models.SPARK, prompt)
    obj = _extract_json(text)
    allowed = ("visible smoke", "visible flame", "no hazard visible",
               "steam or fog", "flame-like lighting",
               "obscured or distant hazard", "indeterminate")
    if obj.get("category") not in allowed:
        raise PipelineError(
            "model assessment has no ignis category: %r"
            % (obj.get("category"),))
    return {"product": "ignis", "category": obj["category"],
            "summary": obj.get("summary", ""),
            "requires_human_review": bool(
                obj.get("requires_human_review", True)),
            "model": model, "latency_ms": latency,
            "usage": {"prompt_chars": len(prompt),
                      "reply_chars": len(text)}}


# --- spend ---------------------------------------------------------------

def estimate_tokens(chars):
    """Rough token estimate (~4 chars/token); never zero for text."""
    if not chars:
        return 0
    return max(1, (int(chars) + 3) // 4)


def estimate_cost(tokens_in, tokens_out):
    """Guardrail rate-card estimate (estimates only, NOT pricing)."""
    return round(tokens_in / 1_000_000 * RATE_IN_PER_MTOK
                 + tokens_out / 1_000_000 * RATE_OUT_PER_MTOK, 6)


def record_call_spend(store_mod, lane_feature, tokens_in, tokens_out,
                      usage="estimated", now=None):
    """One ledger entry per served call; returns (entry, ledger_ok).

    store_mod is intel.store (or a test capture fake). The write is
    observability: a ledger failure keeps the entry run-local and
    reports ledger_ok False instead of failing the run.
    """
    entry = {
        "ts": int(time.time() if now is None else now),
        "lane_feature": lane_feature,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "est_cost": estimate_cost(tokens_in or 0, tokens_out or 0),
        "usage": usage,
    }
    try:
        store_mod.record_spend(entry)
    except Exception:
        return entry, False
    return entry, True


def _default_store():
    """The real intel.store, or None when it cannot load here.

    store.py needs relay_common (the live bus), which is absent in
    an offline checkout: returning None keeps fixture runs working
    with a run-local ledger instead of crashing the import.
    """
    try:
        from intel import store
    except Exception:
        return None
    return store


# --- runners ---------------------------------------------------------------

def load_sam_pairs(sam_dir):
    with open(os.path.join(sam_dir, "pairs.json")) as fh:
        manifest = json.load(fh)
    if manifest.get("set") != "sam-eval-alerts-panel-v1":
        raise PipelineError("unexpected SAM set id: %r"
                            % manifest.get("set"))
    return manifest


def load_ignis_scenarios(path):
    with open(path) as fh:
        doc = json.load(fh)
    scenarios = doc.get("scenarios")
    if not scenarios:
        raise PipelineError("ignis scenario set is missing or empty")
    return scenarios


def run_sam_pairs(sam_dir, segment_fn, reason_fn, spend,
                  lane_feature="sam-spark:sam-pairs"):
    """Regions in, verdicts out, scored vs the manifest labels."""
    manifest = load_sam_pairs(sam_dir)
    records = []
    for pair in manifest["pairs"]:
        for half_name in ("good", "bad"):
            half = pair[half_name]
            started = time.monotonic()
            error = None
            regions, predicted = [], None
            try:
                path = os.path.join(sam_dir, half["file"])
                with open(path, "rb") as fh:
                    image_bytes = fh.read()
                seg = segment_fn(image_bytes, half["file"])
                regions = seg.get("regions", [])
                verdict = reason_fn(pair["id"], regions)
                predicted = verdict.get("label")
                if predicted not in ("build-ok", "build-broken"):
                    raise PipelineError(
                        "reasoner returned no verdict label: %r"
                        % (predicted,))
            except Exception as exc:  # one bad half never stops the run
                error = "%s: %s" % (type(exc).__name__, exc)
            latency_ms = round((time.monotonic() - started) * 1000)
            entry, ledger_ok = spend(
                lane_feature, estimate_tokens(len(json.dumps(
                    regions, sort_keys=True)) or 64),
                estimate_tokens(len(predicted or "")))
            records.append({
                "pair_id": pair["id"],
                "half": half_name,
                "file": half["file"],
                "truth": half["label"],
                "predicted": predicted,
                "correct": (error is None
                            and predicted == half["label"]),
                "regions": regions,
                "latency_ms": latency_ms,
                "error": error,
                "spend": entry,
                "ledger_ok": ledger_ok,
            })
    correct = sum(1 for r in records if r["correct"])
    return {
        "records": records,
        "sample_size": len(records),
        "correct": correct,
        "accuracy": (correct / len(records)) if records else None,
        "errors": sum(1 for r in records if r["error"] is not None),
    }


def run_ignis(scenarios, region_fn, reason_fn, spend,
              lane_feature="sam-spark:ignis-20"):
    """Regions in, assessments out, scored vs scenario ground truth."""
    records = []
    for scenario in scenarios:
        started = time.monotonic()
        error = None
        actual = None
        review = None
        try:
            regions = region_fn(scenario)
            assessment = reason_fn(scenario, regions)
            actual = assessment.get("category")
            review = assessment.get("requires_human_review")
        except Exception as exc:  # one bad scenario never stops the run
            error = "%s: %s" % (type(exc).__name__, exc)
            regions = []
        latency_ms = round((time.monotonic() - started) * 1000)
        if error is not None:
            records.append({
                "scenario_id": scenario.get("scenario_id"),
                "ground_truth_label": scenario.get("ground_truth_label"),
                "alert_expected": scenario.get("alert_expected"),
                "actual_category": None,
                "alert_fired": False,
                "alert_correct": False,
                "category_correct": False,
                "requires_human_review": None,
                "latency_ms": latency_ms,
                "error": error,
                "spend": None,
                "ledger_ok": None,
            })
            continue
        alert_fired = actual in IGNIS_ALERT_CATEGORIES_LEGACY
        entry, ledger_ok = spend(
            lane_feature,
            estimate_tokens(len(scenario.get(
                "expected_observable_condition", ""))),
            estimate_tokens(len(actual or "")))
        records.append({
            "scenario_id": scenario["scenario_id"],
            "ground_truth_label": scenario["ground_truth_label"],
            "alert_expected": scenario["alert_expected"],
            "actual_category": actual,
            "alert_fired": alert_fired,
            "alert_correct": alert_fired == scenario["alert_expected"],
            "category_correct": actual == scenario["ground_truth_label"],
            "requires_human_review": review,
            "latency_ms": latency_ms,
            "error": None,
            "spend": entry,
            "ledger_ok": ledger_ok,
        })
    assessed = [r for r in records if r["error"] is None]
    tp = sum(1 for r in assessed
             if r["alert_expected"] and r["alert_fired"])
    fp = sum(1 for r in assessed
             if not r["alert_expected"] and r["alert_fired"])
    tn = sum(1 for r in assessed
             if not r["alert_expected"] and not r["alert_fired"])
    fn = sum(1 for r in assessed
             if r["alert_expected"] and not r["alert_fired"])
    cat = sum(1 for r in assessed if r["category_correct"])
    metrics = {
        "sample_size": len(records),
        "true_positives": tp,
        "false_positives": fp,
        "true_negatives": tn,
        "false_negatives": fn,
        "precision": (tp / (tp + fp)) if (tp + fp) else None,
        "recall": (tp / (tp + fn)) if (tp + fn) else None,
        "false_positive_rate": (fp / (fp + tn)) if (fp + tn) else None,
        "false_negative_rate": (fn / (fn + tp)) if (fn + tp) else None,
        "category_accuracy": (cat / len(records)) if records else None,
        "errors": {
            "count": sum(1 for r in records if r["error"] is not None),
            "scenario_ids": [r["scenario_id"] for r in records
                              if r["error"] is not None],
        },
    }
    return {"records": records, "metrics": metrics}


def run_all(sam_dir, scenarios_path, segment_fn, region_fn, reason_sam,
            reason_ignis, store_mod, mode_label, ledger_name="unknown"):
    """Both sets, one spend ledger; returns the JSON-serializable run."""
    store_mod = store_mod if store_mod is not None else _LocalLedger()

    def spend(lane_feature, tokens_in, tokens_out, usage="estimated"):
        return record_call_spend(store_mod, lane_feature, tokens_in,
                                 tokens_out, usage)

    sam = run_sam_pairs(sam_dir, segment_fn, reason_sam, spend)
    ignis = run_ignis(load_ignis_scenarios(scenarios_path), region_fn,
                      reason_ignis, spend)
    entries = [r["spend"] for r in sam["records"] if r["spend"]]
    entries += [r["spend"] for r in ignis["records"] if r["spend"]]
    total = round(sum(e["est_cost"] for e in entries), 6)
    ledger_ok = sum(1 for r in sam["records"] + ignis["records"]
                    if r.get("ledger_ok"))
    return {
        "mode": mode_label,
        "ledger": ledger_name,
        "sam": sam,
        "ignis": ignis,
        "spend": {
            "entries": len(entries),
            "total_est_cost_usd": total,
            "ledger_ok": ledger_ok,
            "ledger_missed": len(entries) - ledger_ok,
        },
    }


class _LocalLedger:
    """Run-local spend ledger when no bus exists (offline checkout).

    Same entry shape as intel.store.record_spend; entries stay in
    memory and ride along in the run JSON as spend evidence.
    """

    def __init__(self):
        self.entries = []

    def record_spend(self, entry):
        self.entries.append(dict(entry))
        return entry


def format_report(run):
    """One-page text report for the console (numbers only, no hype)."""
    sam, ignis, spend = run["sam"], run["ignis"], run["spend"]
    m = ignis["metrics"]
    fmt = lambda v: "n/a" if v is None else ("%.3f" % v)
    lines = [
        "SAM-regions -> Spark-reasoning eval — mode: %s" % run["mode"],
        "",
        "SAM pairs: %d/%d correct (accuracy %s), errors %d"
        % (sam["correct"], sam["sample_size"], fmt(sam["accuracy"]),
           sam["errors"]),
    ]
    for r in sam["records"]:
        lines.append(
            "  %s/%s: truth=%s predicted=%s correct=%s regions=%d%s"
            % (r["pair_id"], r["half"], r["truth"], r["predicted"],
               r["correct"], len(r["regions"]),
               (" error=" + r["error"]) if r["error"] else ""))
    lines += [
        "",
        "Ignis 20: TP=%d FP=%d TN=%d FN=%d" % (
            m["true_positives"], m["false_positives"],
            m["true_negatives"], m["false_negatives"]),
        "  precision=%s recall=%s fpr=%s fnr=%s category_accuracy=%s"
        % (fmt(m["precision"]), fmt(m["recall"]),
           fmt(m["false_positive_rate"]), fmt(m["false_negative_rate"]),
           fmt(m["category_accuracy"])),
        "  errors=%d%s" % (m["errors"]["count"],
                           (" (%s)" % ", ".join(m["errors"]["scenario_ids"]))
                           if m["errors"]["scenario_ids"] else ""),
        "",
        "Spend (%s): %d calls, est $%.6f, ledger_ok=%d ledger_missed=%d"
        % (run.get("ledger", "unknown"), spend["entries"], spend["total_est_cost_usd"],
           spend["ledger_ok"], spend["ledger_missed"]),
    ]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="SAM-regions -> Spark-reasoning eval pipeline")
    parser.add_argument("--mode", choices=("fixture", "live"),
                        default="fixture")
    parser.add_argument("--sam-dir", default=SAM_DIR_DEFAULT)
    parser.add_argument("--scenarios", default=IGNIS_SCENARIOS_DEFAULT)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    if args.mode == "fixture":
        segment_fn = fixture_segments
        region_fn = fixture_regions_for_scenario
        reason_sam = lambda pair_id, regions: fixture_reason_sam(  # noqa: E731
            pair_id, regions)
        reason_ignis = lambda scenario, regions: fixture_reason_ignis(  # noqa: E731
            scenario, regions)
        store_mod = _LocalLedger()
        label = "fixture (offline, no model)"
    else:
        try:
            _require_live_key()
        except LiveNotConfigured as exc:
            print("live mode refused: %s" % exc, file=sys.stderr)
            return 2
        sam_prompt = "the alerts panel: segment any alert cards or rows"

        def segment_fn(image_bytes, filename=""):  # noqa: E731
            del filename
            return live_segments(image_bytes, sam_prompt)

        def region_fn(scenario):  # noqa: E731
            # Scenarios are text (no frames): regions seed from the
            # description so the live Spark call still reasons over
            # explicit regions; Del's frame-backed pass replaces
            # this with live SAM on real footage.
            seed = ("live-text-seed:" + str(scenario.get(
                "scenario_id"))).encode()
            if scenario.get("alert_expected"):
                return [_stable_box(seed)]
            return []

        def reason_sam(pair_id, regions):  # noqa: E731
            return live_reason_sam(pair_id, "panel", regions)

        def reason_ignis(scenario, regions):  # noqa: E731
            return live_reason_ignis(scenario, regions)

        store_mod = _default_store() or _LocalLedger()
        label = ("live-model run (real SAM + Spark; "
                 "see sam_spark_runbook.md)")

    run = run_all(args.sam_dir, args.scenarios, segment_fn, region_fn,
                  reason_sam, reason_ignis, store_mod, label,
                  ledger_name=("intel.store spend ledger"
                               if not isinstance(store_mod, _LocalLedger)
                               else "local-only (no bus in offline checkout; "
                                    "entries ride in this run JSON)"))
    print(format_report(run))
    if args.out:
        with open(args.out, "w") as fh:
            json.dump(run, fh, indent=2, sort_keys=True)
            fh.write("\n")
        print("Wrote %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
