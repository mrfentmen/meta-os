"""livehunt.py — the bounded live-flag hunt for the Imperium crew.

WHY THIS EXISTS: the committed live-camera proof (livecams.py,
livecam_records/live-reading.json) is a genuine NYC DOT frame read
end-to-end by the production assessment — and its honest outcome was
baseline ("normal activity"), so nothing flagged and nothing was
dispatched. Demo beat 7 needs the other half: a genuinely live frame
that the crew itself flags, reviews, judges, and dispatches to the
SIMULATED endpoint, with the sim receipt on the record. This module
is that hunt, and it is deliberately small: patrol.py already cycles
cameras forever; a hunt is a BOUNDED pass with a written record.

WHAT IT DOES, per frame, in order:
  * budget governor first (patrol.py's pattern): the Spark guardrail
    state is read before every check; when the remaining test budget
    reaches the reserve (default $5) the hunt stops BEFORE spending
    and the stop is recorded, never silent.
  * one crew check (crew.Crew.check_camera) under a rotating lens
    (vigiles -> ignis -> medicus, patrol's rotation), through the
    production assessment — DirectAssessor below wraps
    spark_gen.generate, the same function livecams --assess-one
    uses, so a hunt reading is a production reading, not a new path.
  * the outcome is appended to the hunt record verbatim: baseline,
    feed-error, job-error, cleared-by-review, flagged-unconfirmed —
    all filed, none hidden.
  * the hunt stops at the FIRST check whose outcome is
    "dispatched-simulated": the incident id and the simulated
    endpoint's receipt id are read back from the incident's own
    timeline (crew_records) — a receipt is only ever reported from
    the record the dispatch step itself wrote.

FRAME SOURCES (both are seams; the record names which one ran):
  * live: crew_common.load_cameras() + crew_common.fetch_snapshot —
    the NYCTMC live list and per-camera stills, fetched directly.
  * staged: StagedFrames — stills captured from the LIVE DOT list
    minutes earlier into a local directory (manifest.json + one
    <camera-id>.jpg per camera). This exists for hosts whose direct
    egress to webcams.nyctmc.org is refused (the build sandbox is
    one; the browser on the same host reaches it fine). The frames
    are real DOT stills; the manifest carries the capture time and
    the hunt record repeats it. A staged frame is never described
    as fetched live by this process.

HARD BOUNDARY, unchanged: dispatch goes through
crew.routed_dispatch(crew.dispatch_url()) — loopback-checked,
SIMULATED endpoint only. A hunt that finds no flag files exactly
that: N live readings, no flag, no dispatch. Nothing here can
manufacture a flag; the assessment is the model's, the flag rule is
js/command-flag.js's, and the judge's ruling is the crew's own.

Run (production assessment via the DEV helper, as in livecams):
  TRIO_SPARK_VIA_HELPER=1 python3 livehunt.py --max-frames 12
  TRIO_SPARK_VIA_HELPER=1 python3 livehunt.py --staged-dir DIR \
      --max-frames 12

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import crew as crew_mod  # noqa: E402
import crew_common  # noqa: E402
import crew_records  # noqa: E402
import patrol as patrol_mod  # noqa: E402
import spark_gen  # noqa: E402
import spark_guardrail  # noqa: E402

DEFAULT_MAX_FRAMES = 12
DEFAULT_RESERVE_USD = patrol_mod.DEFAULT_BUDGET_RESERVE_USD
RECORDS_DIRNAME = "livecam_records"


class LiveHuntError(RuntimeError):
    """A hunt setup failure (bad staged dir, empty camera list)."""


# -- the production assess seam, in Crew shape -----------------------------

class DirectAssessor:
    """Adapt spark_gen.generate to the Crew assess seam.

    generate(product, image_path, timestamp) -> (contract, model,
    latency_ms) reads a JPEG from disk and raises on any failure;
    the Crew seam wants assess(product, image_bytes, timestamp) ->
    result dict. The frame bytes are written to a temp JPEG (the
    magic bytes are checked first — a non-JPEG is refused here,
    never passed to the model), generate runs, and the returned
    contract is wrapped in the queue-result shape the Crew reads
    (status / assessment / model / latency_ms / job_id, the job id
    being the same deterministic id the queue would file).
    """

    def __init__(self, generate_fn=None, tmpdir=None):
        self._generate = generate_fn or spark_gen.generate
        self._tmpdir = tmpdir

    def __call__(self, product, image_bytes, timestamp):
        if not image_bytes or image_bytes[0:2] != b"\xff\xd8":
            raise ValueError("frame is not a JPEG (magic bytes missing)")
        fd, path = tempfile.mkstemp(suffix=".jpg", dir=self._tmpdir)
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(image_bytes)
            contract, model, latency_ms = self._generate(
                product, path, timestamp)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
        if not isinstance(contract, dict):
            raise RuntimeError("assessment did not return a contract object")
        return {
            "status": "ok",
            "assessment": contract,
            "model": model,
            "latency_ms": latency_ms,
            "job_id": crew_common.job_id_for(product, timestamp,
                                             image_bytes),
        }


# -- staged live frames ------------------------------------------------------

class StagedFrames:
    """Stills captured from the live DOT list into a local directory.

    Layout: manifest.json =
      {"captured_at": iso, "note": str,
       "cameras": [camera dicts as crew_common.load_cameras returns]}
    plus one JPEG per camera named <camera-id>.jpg. The provider
    returns the staged bytes for a camera or raises — a missing
    still is a feed error on the record, never a substituted frame.
    """

    def __init__(self, directory):
        self.dir = directory
        manifest_path = os.path.join(directory, "manifest.json")
        try:
            with open(manifest_path, encoding="utf-8") as fh:
                manifest = json.load(fh)
        except Exception as exc:
            raise LiveHuntError(
                f"staged frames: cannot read {manifest_path}: {exc}")
        self.captured_at = manifest.get("captured_at")
        self.note = manifest.get("note") or ""
        self._cameras = manifest.get("cameras") or []
        if not self._cameras:
            raise LiveHuntError("staged frames: manifest lists no cameras")

    def cameras(self):
        return list(self._cameras)

    def describe(self):
        return (f"staged stills captured from the live NYC DOT list "
                f"at {self.captured_at} ({self.note})")

    def __call__(self, camera):
        path = os.path.join(self.dir, f"{camera['id']}.jpg")
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError as exc:
            raise LiveHuntError(
                f"staged frame missing for {camera['id']}: {exc}")
        if not data or data[0:2] != b"\xff\xd8":
            raise LiveHuntError(
                f"staged frame for {camera['id']} is not a JPEG")
        return data


# -- the hunt -----------------------------------------------------------------

def _dispatch_receipt(records, incident_id):
    """The simulated dispatch receipt, read from the incident's own
    timeline — the step the crew's dispatch wrote, nothing else."""
    record = records.get_incident(incident_id)
    if not record:
        return None
    for step in reversed(record.get("timeline") or []):
        if step.get("step") == "dispatch":
            if step.get("error"):
                return {"error": step["error"], "simulated": True}
            return {"receipt_id": step.get("receipt_id"),
                    "service": step.get("service"),
                    "status": step.get("status"),
                    "simulated": True}
    return None


def run_hunt(crew_obj, cameras, records, *, frame_source,
             camera_source, max_frames=DEFAULT_MAX_FRAMES,
             divisions=patrol_mod.DIVISIONS,
             guardrail_status=None, reserve_usd=DEFAULT_RESERVE_USD,
             out_path=None):
    """One bounded hunt. Returns the hunt record dict (also written
    to out_path when given). Stops at the first dispatched-simulated
    outcome, at the budget reserve, or when the frame budget / the
    camera list runs out — the record's stop_reason says which."""
    guardrail_status = guardrail_status or spark_guardrail.status
    record = {
        "kind": "imperium-live-hunt",
        "started_at": crew_common.now_iso(),
        "camera_source": camera_source,
        "frame_source": frame_source,
        "max_frames": max_frames,
        "budget_reserve_usd": reserve_usd,
        "outcomes": [],
        "flagged": None,
        "stop_reason": None,
    }
    todo = list(cameras)[:max_frames]
    for idx, camera in enumerate(todo):
        try:
            state = guardrail_status()
        except Exception:
            state = None
        if state is not None and \
                state.get("remaining_usd") is not None and \
                state["remaining_usd"] <= reserve_usd:
            record["stop_reason"] = "budget-reserve"
            record["guardrail"] = state
            break
        division = divisions[idx % len(divisions)]
        outcome = crew_obj.check_camera(camera, division)
        entry = {
            "camera_id": camera["id"],
            "camera_name": camera["name"],
            "area": camera.get("area"),
            "division": division,
            "outcome": outcome.get("outcome"),
            "category": outcome.get("category"),
            "incident_id": outcome.get("incident_id"),
        }
        record["outcomes"].append(entry)
        if outcome.get("outcome") == "dispatched-simulated":
            record["flagged"] = {
                "incident_id": outcome.get("incident_id"),
                "camera_id": camera["id"],
                "camera_name": camera["name"],
                "division": division,
                "category": outcome.get("category"),
                "dispatch": _dispatch_receipt(
                    records, outcome.get("incident_id")),
            }
            record["stop_reason"] = "flag-dispatched"
            break
    if record["stop_reason"] is None:
        record["stop_reason"] = (
            "max-frames" if len(cameras) > len(todo) else "exhausted")
    record["frames_checked"] = len(record["outcomes"])
    record["finished_at"] = crew_common.now_iso()
    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)),
                    exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=1)
    return record


def build_production_hunt(staged_dir=None, records_dir=None,
                          area=None):
    """Wire the production hunt: real cameras, the production
    assessment, the routed SIMULATED dispatch. Returns
    (crew_obj, cameras, records, frame_source, camera_source)."""
    records = crew_records.CrewRecords(records_dir)
    if staged_dir:
        staged = StagedFrames(staged_dir)
        cameras = staged.cameras()
        if area:
            cameras = [c for c in cameras
                       if (c.get("area") or "").lower() == area.lower()]
        if not cameras:
            raise LiveHuntError("staged frames: no cameras match the area")
        return (crew_mod.Crew(records, DirectAssessor(), staged,
                              crew_mod.routed_dispatch(
                                  crew_mod.dispatch_url()),
                              cameras=cameras),
                cameras, records, staged.describe(), "nyctmc-live-staged")
    cameras, source = crew_common.load_cameras()
    if area:
        cameras = [c for c in cameras
                   if (c.get("area") or "").lower() == area.lower()]
    if not cameras:
        raise LiveHuntError("no cameras available for the hunt")
    return (crew_mod.Crew(records, DirectAssessor(),
                          crew_common.fetch_snapshot,
                          crew_mod.routed_dispatch(
                              crew_mod.dispatch_url()),
                          cameras=cameras),
            cameras, records,
            "live fetch via crew_common.fetch_snapshot", source)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Bounded live-flag hunt over NYC DOT cameras: "
                    "real frames, production assessment, SIMULATED "
                    "dispatch only")
    parser.add_argument("--max-frames", type=int,
                        default=DEFAULT_MAX_FRAMES)
    parser.add_argument("--area", default=None)
    parser.add_argument("--staged-dir", default=None,
                        help="directory of staged live stills "
                             "(manifest.json + <camera-id>.jpg)")
    parser.add_argument("--records-dir", default=None,
                        help="crew records dir (default: crew-data)")
    parser.add_argument("--reserve-usd", type=float,
                        default=DEFAULT_RESERVE_USD)
    parser.add_argument("--out", default=None,
                        help="hunt record path (default: "
                             "livecam_records/hunt-<date>.json)")
    args = parser.parse_args(argv)

    crew_obj, cameras, records, frame_source, camera_source = \
        build_production_hunt(staged_dir=args.staged_dir,
                              records_dir=args.records_dir,
                              area=args.area)
    out_path = args.out
    if out_path is None:
        stamp = crew_common.now_iso()[:10]
        out_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            RECORDS_DIRNAME, f"hunt-{stamp}-{os.getpid()}.json")
    record = run_hunt(
        crew_obj, cameras, records, frame_source=frame_source,
        camera_source=camera_source, max_frames=args.max_frames,
        reserve_usd=args.reserve_usd, out_path=out_path)
    for entry in record["outcomes"]:
        print(f"{entry['camera_name']} [{entry['area']}] "
              f"{entry['division']}: {entry['outcome']}"
              f"{' / ' + entry['category'] if entry['category'] else ''}")
    print(f"frames checked: {record['frames_checked']} — "
          f"stop: {record['stop_reason']}")
    if record["flagged"]:
        print(f"FLAGGED + DISPATCHED (SIMULATED): "
              f"{record['flagged']['incident_id']} "
              f"receipt {record['flagged']['dispatch']}")
    else:
        print("no flag: no dispatch was sent; the record says so")
    print(f"hunt record: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
