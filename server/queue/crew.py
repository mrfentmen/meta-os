"""crew.py — the Meta Imperium agent crew orchestrator.

One patrol check runs the crew's pipeline (docs/AGENT_CREW.md):

  PATROL    a snapshot from one camera is filed as a trio-assessment
            job on the existing queue and answered by the resident
            agent (real Muse Spark, existing guardrail). A baseline
            category ends the check.
  REVIEW    a flagged category earns an ADVERSARIAL second look: an
            independent second assessment of the SAME frame (a fresh
            job — new timestamp, so a distinct job id, answered
            independently). The flag survives only if the second
            reading ALSO lands outside the baseline set; a baseline
            second reading clears it as a look-alike. Both readings
            are recorded either way. Honest limit: the second reading
            uses the standard assessment prompt — the adversarial
            part is the independence and the survival rule, not a
            different prompt, and this file does not claim otherwise.
  RECORDS   a surviving flag becomes an incident record
            (crew_records.py) before anything else happens.
  INVESTIGATE
            a reported incident is investigated with a BOUNDED
            number of extra assessments (MAX_INVESTIGATION_CALLS):
            the other divisions' lenses on a fresh snapshot of the
            incident camera, then the nearest neighbour cameras
            under the origin division. Findings append to the
            incident record; they never spawn further incidents —
            recursion stops at this one level.
  RESPONSE  a brief in the v2 contract shape plus per-division
            recommended actions (recommendations for human decision,
            in observation language; requires_human_review is true)
            is packaged and sent to the SIMULATED dispatch endpoint
            only (see dispatch_url guard below).

HARD BOUNDARY — dispatch: the only dispatch target this code can
send to is the stack's own SIMULATED endpoint, and the URL is
refused unless its host is loopback. There is no configuration that
points dispatch at a real emergency service, no phone/911
integration, and no code path that contacts one. The package is
labelled simulated in its body, in the dispatch log, and in the UI.

Every external effect is an injected seam (assess, fetch_snapshot,
dispatch), so the whole pipeline is testable offline with stubs —
the same discipline as trio_agent's injected store.
"""
import hashlib
import json
import os
import time
import urllib.request
from datetime import datetime, timedelta, timezone

import crew_common
import crew_records
import trio_store

# Investigation bound, stated here once: at most this many extra
# assessment calls per reported incident (2 cross-division lenses +
# up to 3 neighbour cameras = 5 planned; the cap leaves headroom of
# exactly one and is never exceeded).
MAX_INVESTIGATION_CALLS = 6
NEIGHBOUR_SAMPLES = 3

DISPATCH_URL_ENV = "TRIO_CREW_DISPATCH_URL"
DEFAULT_DISPATCH_URL = "http://127.0.0.1:8935/dispatch-simulated"
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


class DispatchBoundaryError(RuntimeError):
    """A dispatch URL that is not the local simulated endpoint."""


def check_dispatch_url(url):
    """Refuse any dispatch target that is not loopback. The crew's
    dispatch step exists to exercise the response pipeline against
    the stack's SIMULATED endpoint; a real emergency-service
    endpoint is not a configuration option, here or anywhere."""
    from urllib.parse import urlparse
    host = urlparse(url).hostname
    if host not in LOOPBACK_HOSTS:
        raise DispatchBoundaryError(
            f"dispatch URL host {host!r} is not loopback: the crew "
            "dispatches ONLY to the local SIMULATED endpoint")
    return url


def dispatch_url():
    return check_dispatch_url(
        os.environ.get(DISPATCH_URL_ENV) or DEFAULT_DISPATCH_URL)


def http_dispatch(url):
    """Build the production dispatcher: POST the package to the
    (loopback-checked) simulated endpoint, return its receipt."""
    check_dispatch_url(url)

    def dispatch(package):
        req = urllib.request.Request(
            url, data=json.dumps(package).encode(), method="POST",
            headers={"Content-Type": "application/json",
                     "User-Agent": "MetaImperium-Crew/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    return dispatch


class QueueAssessor:
    """The production assess seam: file a trio-assessment envelope
    on the existing jobs store and poll for the resident agent's
    result envelope — the same queue + guardrail path as
    /api/assess, driven in-process. Bounded polling; a timeout is an
    error result for the caller to record, never a fabricated
    assessment."""

    def __init__(self, jobs, poll_attempts=90, poll_interval=1.0,
                 sleep=time.sleep):
        self.jobs = jobs
        self.poll_attempts = int(poll_attempts)
        self.poll_interval = float(poll_interval)
        self.sleep = sleep

    def __call__(self, product, image_bytes, timestamp):
        env = crew_common.build_job_envelope(product, timestamp,
                                             image_bytes)
        err = crew_common.envelope_error(env)
        if err:
            raise ValueError(f"crew-built envelope refused: {err}")
        self.jobs.submit(env)
        for _ in range(self.poll_attempts):
            result = self.jobs.get_result(env["id"])
            if result is not None:
                return result
            self.sleep(self.poll_interval)
        raise TimeoutError(
            f"no result for job {env['id']} after "
            f"{self.poll_attempts} polls — is trio_agent.py running?")


def _category_of(result):
    if not result or result.get("status") != "ok":
        return None
    return ((result.get("assessment") or {}).get("assessment")
            or {}).get("category")


def _summary_of(result):
    if not result or result.get("status") != "ok":
        return None
    return ((result.get("assessment") or {}).get("assessment")
            or {}).get("summary")


def _observations_of(result):
    if not result or result.get("status") != "ok":
        return []
    return (result.get("assessment") or {}).get("observations") or []


def _uncertainty_of(result):
    if not result or result.get("status") != "ok":
        return []
    return ((result.get("assessment") or {}).get("assessment")
            or {}).get("uncertainty") or []


def _distinct_timestamp(ts, other):
    """Review jobs need a timestamp distinct from the patrol job's —
    same product + same timestamp + same frame would be the SAME
    deterministic job id, and the 'second reading' would silently be
    the first one's cached result. Bump by a millisecond until
    distinct (real calls are seconds apart; this is belt and
    braces)."""
    if ts != other:
        return ts
    dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ")
    bumped = dt + timedelta(milliseconds=1)
    return bumped.strftime("%Y-%m-%dT%H:%M:%S.") + \
        f"{bumped.microsecond // 1000:03d}Z"


def recommended_actions(camera, category):
    """Per-division recommended actions for a reported incident.
    Recommendations for a human decision-maker, in observation
    language only: nothing here states that an incident or offense
    occurred, and nothing directs a dispatch — the products' own
    limitations text (js/products.js) is the rule."""
    name = camera.get("name", "the camera")
    area = camera.get("area", "")
    where = f"{name} ({area})" if area else name
    return {
        "vigiles": (
            f"For human review: examine the recorded frames from "
            f"{where}. The flagged observation category is "
            f"\"{category}\" — a visual category only; it does not "
            f"establish that an incident or offense occurred. A "
            f"human reviewer decides whether any follow-up is "
            f"warranted."),
        "ignis": (
            f"For human review: check the recorded frames from "
            f"{where} against the flagged category \"{category}\". "
            f"This system is not a certified fire-detection system; "
            f"a human reviewer decides whether any follow-up is "
            f"warranted."),
        "medicus": (
            f"For human review: look at the recorded scene from "
            f"{where}. The flagged category \"{category}\" is a "
            f"scene indicator only — no diagnosis, cause, severity, "
            f"or treatment is stated or implied. A human reviewer "
            f"decides whether any follow-up is warranted."),
    }


def build_brief(record, results):
    """The incident brief, in the v2 assessment contract shape
    (validated against js/schema.js in the crew tests): the origin
    division's product, the surviving reading's summary, the union
    of recorded uncertainties, every recorded observation, and
    requires_human_review — always true."""
    observations = []
    for result in results:
        observations.extend(_observations_of(result))
    uncertainty = []
    for result in results:
        for line in _uncertainty_of(result):
            if line not in uncertainty:
                uncertainty.append(line)
    summary = None
    for result in reversed(results):
        summary = _summary_of(result)
        if summary:
            break
    latencies = [r.get("latency_ms") for r in results
                 if isinstance(r, dict)
                 and isinstance(r.get("latency_ms"), (int, float))]
    models = [r.get("model") for r in results if isinstance(r, dict)]
    return {
        "product": record["division"],
        "timestamp": crew_common.now_iso(),
        "observations": observations,
        "assessment": {
            "category": record["category"],
            "summary": summary or
                "Recorded assessments are on the incident timeline.",
            "uncertainty": uncertainty,
            "requires_human_review": True,
        },
        "processing": {
            "model": models[-1] if models else None,
            "latency_ms": sum(latencies) if latencies else None,
        },
    }


class Crew:
    """The pipeline for one patrol check. Seams are injected;
    production wiring is Crew.production()."""

    def __init__(self, records, assess, fetch_snapshot, dispatch,
                 cameras=()):
        self.records = records
        self.assess = assess
        self.fetch_snapshot = fetch_snapshot
        self.dispatch = dispatch
        self.cameras = list(cameras)

    @classmethod
    def production(cls, records=None, cameras=()):
        store, fell_back = trio_store.open_store(
            os.environ.get(
                "TRIO_LOCAL_DB",
                os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "trio-queue-local.db")))
        if fell_back:
            print("crew: WARNING — local SQLite FALLBACK store",
                  flush=True)
        jobs = trio_store.JobStore(store)
        records = records or crew_records.CrewRecords()
        return cls(records, QueueAssessor(jobs),
                   crew_common.fetch_snapshot,
                   http_dispatch(dispatch_url()), cameras=cameras)

    # -- one patrol check ------------------------------------------------

    def check_camera(self, camera, division, at=None):
        """Patrol -> (review -> records -> investigation -> response
        when flagged). Returns an outcome dict; every step is also
        written to the records. Failures are recorded as events and
        returned, never hidden."""
        at = at or crew_common.now_iso()
        base = {"camera_id": camera["id"], "camera_name": camera["name"],
                "area": camera.get("area"), "division": division}
        try:
            frame = self.fetch_snapshot(camera)
        except Exception as e:
            event = {"at": at, "type": "patrol-check", **base,
                     "outcome": "feed-error", "error": str(e)[:200]}
            self.records.append_event(event)
            return {"outcome": "feed-error", **base}
        timestamp = crew_common.now_iso()
        try:
            result = self.assess(division, frame, timestamp)
        except Exception as e:
            event = {"at": crew_common.now_iso(), "type": "patrol-check",
                     **base, "outcome": "job-error",
                     "error": str(e)[:200]}
            self.records.append_event(event)
            return {"outcome": "job-error", **base}
        category = _category_of(result)
        if result.get("status") != "ok" or category is None:
            event = {"at": crew_common.now_iso(), "type": "patrol-check",
                     **base, "outcome": "assessment-failed",
                     "error": (result.get("error") or "")[:200],
                     "job_id": result.get("job_id")}
            self.records.append_event(event)
            return {"outcome": "assessment-failed", **base}
        flagged = crew_common.is_flagged_category(division, category)
        event = {"at": crew_common.now_iso(), "type": "patrol-check",
                 **base, "outcome": "flagged" if flagged else "baseline",
                 "category": category, "job_id": result.get("job_id"),
                 "model": result.get("model"),
                 "latency_ms": result.get("latency_ms")}
        self.records.append_event(event)
        if not flagged:
            return {"outcome": "baseline", "category": category, **base}
        return self._handle_flag(camera, division, frame, result,
                                 category, timestamp)

    # -- the flag pipeline -------------------------------------------------

    def _handle_flag(self, camera, division, frame, first_result,
                     category, first_timestamp):
        priority = crew_common.priority_for_category(division, category)
        incident_id = "incident-" + hashlib.sha256(
            first_result["job_id"].encode()).hexdigest()[:16]
        record = {
            "id": incident_id,
            "status": "flagged",
            "created_at": crew_common.now_iso(),
            "camera": {"id": camera["id"], "name": camera["name"],
                       "area": camera.get("area"),
                       "latitude": camera.get("latitude"),
                       "longitude": camera.get("longitude")},
            "division": division,
            "category": category,
            "priority": priority,
            "patrol_job_id": first_result.get("job_id"),
            "timeline": [],
        }
        self.records.create_incident(record)
        self.records.append_timeline(incident_id, {
            "at": crew_common.now_iso(), "step": "flag",
            "division": division, "category": category,
            "priority": priority, "job_id": first_result.get("job_id"),
            "model": first_result.get("model"),
            "latency_ms": first_result.get("latency_ms"),
            "summary": _summary_of(first_result),
        })
        self.records.append_event({
            "at": crew_common.now_iso(),
            "at_epoch": time.time(), "type": "flag",
            "incident_id": incident_id, "camera_id": camera["id"],
            "camera_name": camera["name"], "area": camera.get("area"),
            "division": division, "category": category,
            "priority": priority})

        # REVIEW — independent second assessment of the same frame.
        # Its timestamp must differ from the patrol job's filing
        # timestamp: same product + timestamp + frame would rebuild
        # the SAME deterministic job id and the "second reading"
        # would silently be the first one's stored result.
        review_ts = _distinct_timestamp(crew_common.now_iso(),
                                        first_timestamp)
        try:
            review = self.assess(division, frame, review_ts)
        except Exception as e:
            review = {"status": "failed", "error": str(e)[:200],
                      "job_id": None}
        review_category = _category_of(review)
        if review.get("status") == "ok" and review_category is not None \
                and not crew_common.is_flagged_category(division,
                                                        review_category):
            verdict = "cleared"
        elif review.get("status") == "ok" and review_category is not None:
            verdict = "confirmed"
        else:
            verdict = "inconclusive"
        self.records.append_timeline(incident_id, {
            "at": crew_common.now_iso(), "step": "review",
            "verdict": verdict, "category": review_category,
            "job_id": review.get("job_id"),
            "model": review.get("model"),
            "latency_ms": review.get("latency_ms"),
            "error": review.get("error"),
            "summary": _summary_of(review),
            "status": "cleared-by-review" if verdict == "cleared"
                      else None,
        })
        self.records.append_event({
            "at": crew_common.now_iso(), "type": "review",
            "incident_id": incident_id, "camera_id": camera["id"],
            "camera_name": camera["name"], "division": division,
            "verdict": verdict, "category": review_category})
        if verdict == "cleared":
            return {"outcome": "cleared-by-review",
                    "incident_id": incident_id, "category": category}
        if verdict == "inconclusive":
            # The flag is neither confirmed nor cleared. It stays on
            # the record as flagged (human review is exactly the
            # fallback the contract names); no investigation or
            # dispatch is spent on an unconfirmed flag.
            return {"outcome": "flagged-unconfirmed",
                    "incident_id": incident_id, "category": category}

        # REPORTED.
        self.records.append_timeline(incident_id, {
            "at": crew_common.now_iso(), "step": "reported",
            "status": "reported"})
        self.records.append_event({
            "at": crew_common.now_iso(), "type": "incident",
            "incident_id": incident_id, "camera_id": camera["id"],
            "camera_name": camera["name"], "area": camera.get("area"),
            "division": division, "category": category,
            "priority": priority, "status": "reported"})

        # INVESTIGATION — bounded extra calls.
        investigation = self._investigate(
            self.records.get_incident(incident_id), camera, division)
        results = [first_result, review] + \
            [e["result"] for e in investigation if e.get("result")]

        # RESPONSE — brief + SIMULATED dispatch.
        record = self.records.get_incident(incident_id)
        brief = build_brief(record, results)
        package = {
            "simulated": True,
            "kind": "imperium-dispatch-package",
            "incident_id": incident_id,
            "created_at": crew_common.now_iso(),
            "destination": "SIMULATED dispatch endpoint (local stack "
                           "route) — no real emergency service is "
                           "contacted by this system",
            "brief": brief,
            "recommended_actions": recommended_actions(camera, category),
            "requires_human_review": True,
        }
        self.records.append_timeline(incident_id, {
            "at": crew_common.now_iso(), "step": "brief",
            "brief": brief})
        try:
            receipt = self.dispatch(package)
            dispatch_step = {
                "at": crew_common.now_iso(), "step": "dispatch",
                "simulated": True,
                "receipt_id": receipt.get("receipt_id"),
                "status": "dispatched-simulated",
            }
            outcome = "dispatched-simulated"
        except Exception as e:
            dispatch_step = {
                "at": crew_common.now_iso(), "step": "dispatch",
                "simulated": True, "error": str(e)[:200],
            }
            outcome = "reported"
        self.records.append_timeline(incident_id, dispatch_step)
        self.records.append_event({
            "at": crew_common.now_iso(), "type": "dispatch",
            "incident_id": incident_id, "camera_id": camera["id"],
            "camera_name": camera["name"], "division": division,
            "simulated": True,
            "receipt_id": dispatch_step.get("receipt_id"),
            "error": dispatch_step.get("error")})
        return {"outcome": outcome, "incident_id": incident_id,
                "category": category}

    # -- investigation -----------------------------------------------------

    def _investigate(self, record, camera, division):
        """Bounded: cross-division lenses on the incident camera,
        then nearest neighbours under the origin division, until
        MAX_INVESTIGATION_CALLS extra assessments are spent. Every
        attempt is recorded, including feed/job failures."""
        entries = []
        calls = 0
        others = [p for p in ("vigiles", "ignis", "medicus")
                  if p != division]

        def attempt(kind, cam, lens):
            nonlocal calls
            calls += 1
            entry = {"kind": kind, "camera_id": cam["id"],
                     "camera_name": cam["name"], "division": lens,
                     "at": crew_common.now_iso()}
            try:
                frame = self.fetch_snapshot(cam)
                result = self.assess(lens, frame,
                                     crew_common.now_iso())
                cat = _category_of(result)
                entry.update({
                    "category": cat,
                    "flagged": crew_common.is_flagged_category(
                        lens, cat) if cat else False,
                    "job_id": result.get("job_id"),
                    "model": result.get("model"),
                    "latency_ms": result.get("latency_ms"),
                    "error": result.get("error"),
                    "result": result,
                })
            except Exception as e:
                entry.update({"category": None, "flagged": False,
                              "error": str(e)[:200], "result": None})
            entries.append(entry)
            self.records.append_timeline(record["id"], {
                "at": entry["at"], "step": "investigation",
                "kind": kind, "camera_id": cam["id"],
                "camera_name": cam["name"], "division": lens,
                "category": entry["category"],
                "flagged": entry["flagged"],
                "job_id": entry.get("job_id"),
                "model": entry.get("model"),
                "latency_ms": entry.get("latency_ms"),
                "error": entry.get("error"),
                "status": "investigating" if calls == 1 else None,
            })
            return entry

        for lens in others:
            if calls >= MAX_INVESTIGATION_CALLS:
                break
            attempt("cross-lens", camera, lens)
        for near in crew_common.nearest_cameras(
                self.cameras, camera, limit=NEIGHBOUR_SAMPLES,
                exclude_id=camera["id"]):
            if calls >= MAX_INVESTIGATION_CALLS:
                break
            attempt("neighbour", near["camera"], division)
        self.records.append_event({
            "at": crew_common.now_iso(), "type": "investigation",
            "incident_id": record["id"], "camera_id": camera["id"],
            "camera_name": camera["name"], "division": division,
            "calls": calls,
            "flags_found": sum(1 for e in entries if e["flagged"])})
        return entries
