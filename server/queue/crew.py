"""crew.py — the Meta Imperium agent crew.

One patrol check runs the crew (docs/AGENT_CREW.md). Since the
orchestrator landed (orchestrator.py), the crew is NOT a fixed
pipeline: after a flag, every next step is chosen by the
orchestrator's deterministic decision engine from the incident's
current record — review, then a fresh decision, then investigation,
then a fresh decision, then response — with its limits enforced in
code. The stages the decisions choose between:

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
  EVIDENCE  a flagged incident — and only a flagged incident —
            captures person evidence (evidence.py): the assessed
            frames saved verbatim, face crops where a real face
            detector finds a face (detection only: locating a face
            in a frame — no matching, no template, no identity),
            and a BOLO block in the response package built from
            the crew's own recorded descriptions. An incident the
            review closes as a false positive has its evidence
            files DELETED, the deletion itself recorded
            (crew_records.purge_evidence).
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
import evidence
import orchestrator
import trio_store

# Investigation bound, stated here once: at most this many extra
# assessment calls per reported incident (2 cross-division lenses +
# up to 3 neighbour cameras = 5 planned; the cap leaves headroom of
# exactly one and is never exceeded).
MAX_INVESTIGATION_CALLS = 6
NEIGHBOUR_SAMPLES = 3

# Evidence bound, stated here once: at most this many evidence
# files (frames + face crops) are kept per incident.
MAX_EVIDENCE_FILES = 12

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
        # The brief is a single-product v2 contract (the origin
        # division's), and js/schema.js enforces that product's
        # permitted categories on every observation it carries —
        # so the brief carries the origin division's observations
        # only. Cross-division investigation findings stay on the
        # incident timeline, where they belong, and in the
        # recommended actions; they are not dropped from the
        # record, only from this one-product document.
        product = ((result.get("assessment") or {}).get("product")
                   if isinstance(result, dict) else None)
        if product is not None and product != record["division"]:
            continue
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
    """The crew for one patrol check. Seams are injected;
    production wiring is Crew.production(). The orchestrator is a
    seam too — tests may inject one bound to the same records."""

    def __init__(self, records, assess, fetch_snapshot, dispatch,
                 cameras=(), orchestrator_engine=None, detector=None):
        self.records = records
        self.assess = assess
        self.fetch_snapshot = fetch_snapshot
        self.dispatch = dispatch
        self.cameras = list(cameras)
        self.orchestrator = orchestrator_engine or \
            orchestrator.Orchestrator(records)
        # Face detector seam (evidence.py): None means the
        # production detector — OpenCV Haar when the runtime has
        # cv2, honestly "unavailable" when it does not.
        self.detector = detector

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

    # -- evidence capture ----------------------------------------------------

    def _capture_evidence(self, incident_id, kind, frame, camera_id,
                          existing_count):
        """EVIDENCE — save one assessed frame verbatim, plus a
        padded crop per face a real detector finds in it. Returns
        (entries, detector_name, error): a failure is returned for
        the caller to record, never hidden, and never breaks the
        flag pipeline — the incident stands on its assessments
        either way. Bounded by MAX_EVIDENCE_FILES per incident."""
        entries = []
        if existing_count >= MAX_EVIDENCE_FILES:
            return entries, None, "evidence file cap reached"
        try:
            name = evidence.frame_ref_name(kind, camera_id, frame)
            ref = self.records.save_evidence_file(
                incident_id, name, frame)
            entries.append({
                "ref": ref, "kind": kind,
                "sha256": hashlib.sha256(frame).hexdigest(),
                "bytes": len(frame), "camera_id": camera_id})
        except Exception as e:
            return entries, None, f"frame save failed: {str(e)[:160]}"
        detector_name = None
        try:
            boxes, detector_name = evidence.detect_face_boxes(
                frame, detector=self.detector)
            for box in boxes:
                if existing_count + len(entries) >= MAX_EVIDENCE_FILES:
                    break
                crop = evidence.crop_jpeg(frame, box)
                if crop is None:
                    continue
                crop_name = evidence.frame_ref_name(
                    "face-crop", camera_id, crop)
                ref = self.records.save_evidence_file(
                    incident_id, crop_name, crop)
                entries.append({
                    "ref": ref, "kind": "face-crop",
                    "sha256": hashlib.sha256(crop).hexdigest(),
                    "bytes": len(crop), "camera_id": camera_id,
                    "box": box})
        except Exception as e:
            return entries, detector_name, \
                f"face detection failed: {str(e)[:160]}"
        return entries, detector_name, None

    # -- the flag pipeline -------------------------------------------------

    def _handle_flag(self, camera, division, frame, first_result,
                     category, first_timestamp):
        priority = crew_common.priority_for_category(division, category)
        incident_id = "incident-" + hashlib.sha256(
            first_result["job_id"].encode()).hexdigest()[:16]
        evidence_hash = hashlib.sha256(frame).hexdigest()
        # EVIDENCE — the flag is the gate: this capture runs only
        # because a category flagged. The flagging frame is filed
        # before the record is created, and the record carries the
        # resulting file list from birth.
        entries, detector_name, capture_error = self._capture_evidence(
            incident_id, "flag-frame", frame, camera["id"], 0)
        record = {
            "id": incident_id,
            "status": "candidate",
            "evidence": {"frame_sha256": evidence_hash,
                         "detector": detector_name,
                         "files": entries},
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
            "frame_sha256": evidence_hash,
        })
        if capture_error:
            self.records.append_timeline(incident_id, {
                "at": crew_common.now_iso(), "step": "evidence-error",
                "error": capture_error})
        self.records.append_event({
            "at": crew_common.now_iso(),
            "at_epoch": time.time(), "type": "flag",
            "incident_id": incident_id, "camera_id": camera["id"],
            "camera_name": camera["name"], "area": camera.get("area"),
            "division": division, "category": category,
            "priority": priority})

        # ORCHESTRATOR LOOP — from here the sequence is chosen,
        # not scripted: the orchestrator is consulted after every
        # result lands and returns the NEXT decision from the
        # incident's current record (review first, typically — but
        # that is its decision, re-made at every step, not a
        # hardcoded order). Cleared flags close as false positives
        # (the orchestrator's call, on the record); inconclusive
        # ones hold in monitoring with no further spend; limit
        # breaches stop the incident where it stands.
        results = [first_result]
        reported = False
        while True:
            record = self.records.get_incident(incident_id)
            decision = self.orchestrator.step(
                record, evidence_hash=evidence_hash)
            name = decision["decision"]
            if name == "close_candidate":
                # A false positive keeps no person evidence: the
                # files are deleted and the deletion is recorded
                # on the incident (purge receipt + timeline step).
                self.records.purge_evidence(
                    incident_id, "closed-false-positive",
                    crew_common.now_iso())
                return {"outcome": "cleared-by-review",
                        "incident_id": incident_id,
                        "category": category}
            if name == "continue_monitoring":
                # The flag is neither confirmed nor cleared. It
                # stays on the record, open in monitoring (human
                # review is exactly the fallback the contract
                # names); no investigation or dispatch is spent on
                # an unconfirmed flag.
                return {"outcome": "flagged-unconfirmed",
                        "incident_id": incident_id,
                        "category": category}
            if name == "stop":
                return {"outcome": "stopped",
                        "incident_id": incident_id,
                        "category": category,
                        "reason": decision["reason"]}
            if name == "prepare_response":
                break
            # investigate / reconcile: execute the ordered actions,
            # then loop back and let the orchestrator replan from
            # the new state.
            for action in decision["actions"]:
                agent = action.get("agent")
                if agent == "review":
                    review, verdict = self._run_review(
                        incident_id, camera, division, frame,
                        first_timestamp)
                    if review.get("status") == "ok":
                        results.append(review)
                    if verdict == "confirmed" and not reported:
                        reported = True
                        self._mark_reported(incident_id, camera,
                                            division, category,
                                            priority)
                elif agent == "investigation":
                    lenses = None
                    if name == "reconcile":
                        # Execute the reconcile order itself: only
                        # the lens the orchestrator found missing.
                        missing = orchestrator.missing_lenses(
                            self.records.get_incident(incident_id))
                        lenses = tuple(missing) or None
                    investigation = self._investigate(
                        self.records.get_incident(incident_id),
                        camera, division, lenses=lenses)
                    results += [e["result"] for e in investigation
                                if e.get("result")]
                elif agent == "response":
                    break
        # RESPONSE — brief + SIMULATED dispatch (the orchestrator's
        # prepare_response decision brought us here).
        record = self.records.get_incident(incident_id)
        brief = build_brief(record, results)
        # EVIDENCE — the BOLO: person evidence built only from
        # what the crew recorded (its own assessments' descriptions
        # and the files it captured for this incident).
        descriptions = []
        for result in results:
            for obs in _observations_of(result):
                if isinstance(obs, dict):
                    descriptions.append(obs.get("description"))
        bolo = evidence.build_bolo(
            record, descriptions,
            (record.get("evidence") or {}).get("files"))
        package = {
            "simulated": True,
            "kind": "imperium-dispatch-package",
            "incident_id": incident_id,
            "created_at": crew_common.now_iso(),
            "destination": "SIMULATED dispatch endpoint (local stack "
                           "route) — no real emergency service is "
                           "contacted by this system",
            "brief": brief,
            "person_evidence": bolo,
            "recommended_actions": recommended_actions(camera, category),
            "requires_human_review": True,
        }
        self.records.append_timeline(incident_id, {
            "at": crew_common.now_iso(), "step": "brief",
            "brief": brief})
        self.records.append_timeline(incident_id, {
            "at": crew_common.now_iso(), "step": "bolo",
            "bolo": bolo})
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

    # -- review and reported (executed on the orchestrator's word) --------

    def _run_review(self, incident_id, camera, division, frame,
                    first_timestamp):
        """REVIEW — independent second assessment of the same frame.
        Its timestamp must differ from the patrol job's filing
        timestamp: same product + timestamp + frame would rebuild
        the SAME deterministic job id and the "second reading"
        would silently be the first one's stored result. Appends
        the review step + event; returns (review, verdict). The
        step carries no status — the orchestrator's next decision
        moves the lifecycle (close / investigate / monitoring)."""
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
            "status": None,
        })
        self.records.append_event({
            "at": crew_common.now_iso(), "type": "review",
            "incident_id": incident_id, "camera_id": camera["id"],
            "camera_name": camera["name"], "division": division,
            "verdict": verdict, "category": review_category})
        return review, verdict

    def _mark_reported(self, incident_id, camera, division, category,
                       priority):
        """A review-confirmed flag is a reported incident."""
        self.records.append_timeline(incident_id, {
            "at": crew_common.now_iso(), "step": "reported",
            "status": "reported"})
        self.records.append_event({
            "at": crew_common.now_iso(), "type": "incident",
            "incident_id": incident_id, "camera_id": camera["id"],
            "camera_name": camera["name"], "area": camera.get("area"),
            "division": division, "category": category,
            "priority": priority, "status": "reported"})

    # -- investigation -----------------------------------------------------

    def _investigate(self, record, camera, division, lenses=None):
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
            frame = None
            try:
                frame = self.fetch_snapshot(cam)
                entry["frame_sha256"] = hashlib.sha256(frame).hexdigest()
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
                "frame_sha256": entry.get("frame_sha256"),
                "job_id": entry.get("job_id"),
                "model": entry.get("model"),
                "latency_ms": entry.get("latency_ms"),
                "error": entry.get("error"),
                "status": "investigating" if calls == 1 else None,
            })
            if frame is not None:
                # EVIDENCE — investigation frames are evidence too:
                # filed under the same incident, same cap, with
                # any failure recorded, never fatal to the step.
                current = self.records.get_incident(record["id"])
                count = len(((current.get("evidence") or {})
                             .get("files")) or [])
                new_entries, _detector, cap_error = \
                    self._capture_evidence(
                        record["id"], "investigation-frame", frame,
                        cam["id"], count)
                if new_entries:
                    self.records.attach_evidence(
                        record["id"], new_entries, entry["at"])
                if cap_error:
                    self.records.append_timeline(record["id"], {
                        "at": crew_common.now_iso(),
                        "step": "evidence-error", "error": cap_error})
            return entry

        if lenses is not None:
            # A reconcile order: only the named lens/lenses, on the
            # incident camera — not a fresh full investigation.
            for lens in lenses:
                if calls >= MAX_INVESTIGATION_CALLS:
                    break
                attempt("cross-lens", camera, lens)
        else:
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
