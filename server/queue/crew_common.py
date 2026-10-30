"""crew_common.py — shared core for the Meta Imperium agent crew.

The crew (patrol -> review -> investigation -> records -> response,
see docs/AGENT_CREW.md) reuses the stack's own sources of truth
instead of copying their values:

  * flag rule tables (baseline categories, incident priorities) are
    loaded from js/command-flag.js — the same module the Command
    view uses — via node, exactly the way trio_repo.py loads
    js/products.js. There is no Python-side copy of those tables.
  * job envelopes are built to the exact buildQueueJob shape in
    server/queue.mjs (version 1, kind "trio-assessment", the same
    deterministic id), so a crew-filed job is indistinguishable from
    a server-filed one and is verified by the queue service's own
    validate_envelope before it is filed in tests.
  * the camera list comes from the NYCTMC public API when it is
    reachable, else from the verbatim offline subset in
    js/camera-fallback.js — the same fallback the UI uses, labelled
    as such wherever the source is reported.

Stdlib only.
"""
import base64
import hashlib
import json
import math
import os
import subprocess
import urllib.request
from datetime import datetime, timezone

QUEUE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(QUEUE_DIR, "..", ".."))
COMMAND_FLAG_PATH = os.path.join(REPO_ROOT, "js", "command-flag.js")
CAMERA_FALLBACK_PATH = os.path.join(REPO_ROOT, "js", "camera-fallback.js")

_cache = {}


def now_iso():
    return datetime.now(timezone.utc).isoformat(
        timespec="milliseconds").replace("+00:00", "Z")


# -- js sources of truth, loaded through node (trio_repo pattern) ------

def _node_dump():
    if "dump" in _cache:
        return _cache["dump"]
    script = (
        f'import {{ BASELINE_CATEGORIES, CATEGORY_PRIORITY }} from '
        f'"file://{COMMAND_FLAG_PATH}";\n'
        f'import {{ CAMERA_API_URL, FALLBACK_CAMERAS }} from '
        f'"file://{CAMERA_FALLBACK_PATH}";\n'
        "console.log(JSON.stringify({ baselines: BASELINE_CATEGORIES,"
        " priorities: CATEGORY_PRIORITY, cameraApiUrl: CAMERA_API_URL,"
        " fallbackCameras: FALLBACK_CAMERAS }));\n"
    )
    p = subprocess.run(["node", "--input-type=module", "-e", script],
                       capture_output=True, text=True, timeout=30)
    if p.returncode != 0:
        raise RuntimeError(
            f"could not load js crew sources: {p.stderr.strip()[:300]}")
    _cache["dump"] = json.loads(p.stdout)
    return _cache["dump"]


def baseline_categories():
    """{product_id: [baseline category, ...]} from js/command-flag.js."""
    return _node_dump()["baselines"]


def category_priorities():
    """{product_id: {category: priority}} from js/command-flag.js."""
    return _node_dump()["priorities"]


def is_flagged_category(product, category):
    """Mirror of isFlaggedCategory in js/command-flag.js: a real
    category string, for a known product, outside that product's
    baseline set. Anything else never flags."""
    if not isinstance(category, str) or not category:
        return False
    baselines = baseline_categories()
    if product not in baselines:
        return False
    return category not in baselines[product]


def priority_for_category(product, category):
    """Mirror of priorityForCategory: None when the category does
    not flag; else the mapped priority, defaulting to "low"."""
    if not is_flagged_category(product, category):
        return None
    return category_priorities().get(product, {}).get(category, "low")


# -- cameras -------------------------------------------------------------

def normalize_camera(raw):
    """Mirror of normalizeCamera in js/command-flag.js: the record
    must carry a usable id, name, borough, image URL, and finite
    coordinates, or it is dropped — a camera is never plotted or
    sampled on guessed data."""
    if not isinstance(raw, dict):
        return None
    cam = {k: raw.get(k) for k in
           ("id", "name", "latitude", "longitude", "area", "isOnline",
            "imageUrl")}
    for field in ("id", "name", "area", "imageUrl"):
        if not isinstance(cam[field], str) or not cam[field]:
            return None
    for field in ("latitude", "longitude"):
        if not isinstance(cam[field], (int, float)) or \
                isinstance(cam[field], bool) or \
                not math.isfinite(cam[field]):
            return None
    return cam


def is_camera_online(camera):
    return bool(camera) and camera.get("isOnline") in ("true", True)


def _fetch_json(url, timeout=10):
    req = urllib.request.Request(
        url, headers={"User-Agent": "MetaImperium-Crew/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_cameras(fetch=None):
    """(cameras, source): the NYCTMC live list when fetchable, else
    the offline subset from js/camera-fallback.js. Source is
    "nyctmc-live" or "fallback-subset" and is reported wherever the
    crew's state is shown — a fallback is never dressed as live.
    Only online cameras are returned."""
    fetch = fetch or _fetch_json
    dump = _node_dump()
    try:
        raw = fetch(dump["cameraApiUrl"])
        if not isinstance(raw, list):
            raise ValueError("camera API did not return a list")
        cameras = [c for c in (normalize_camera(r) for r in raw)
                   if c is not None and is_camera_online(c)]
        if not cameras:
            raise ValueError("camera API returned no usable cameras")
        return cameras, "nyctmc-live"
    except Exception:
        cameras = [c for c in
                   (normalize_camera(r) for r in dump["fallbackCameras"])
                   if c is not None and is_camera_online(c)]
        return cameras, "fallback-subset"


def fetch_snapshot(camera, fetch_bytes=None, timeout=12):
    """One JPEG snapshot from the camera's published image URL, with
    a cache-buster so the frame is current. Raises on any failure —
    a feed error is recorded by the caller, never papered over with
    an older or invented frame."""
    url = camera["imageUrl"]
    sep = "&" if "?" in url else "?"
    busted = f"{url}{sep}t={int(datetime.now(timezone.utc).timestamp() * 1000)}"
    if fetch_bytes is not None:
        raw = fetch_bytes(busted)
    else:
        req = urllib.request.Request(
            busted, headers={"User-Agent": "MetaImperium-Crew/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
    if not raw or raw[0:2] != b"\xff\xd8":
        raise ValueError("snapshot is not a JPEG (magic bytes missing)")
    return raw


# -- job envelopes (buildQueueJob mirror) --------------------------------

def job_id_for(product, timestamp, frame_bytes):
    """buildQueueJob's deterministic id (server/queue.mjs):
    "trio-" + sha256(product \\0 timestamp \\0 frame bytes)[:32]."""
    digest = hashlib.sha256(
        f"{product}\0{timestamp}\0".encode() + frame_bytes).hexdigest()
    return f"trio-{digest[:32]}"


def build_job_envelope(product, timestamp, frame_bytes):
    """The exact envelope buildQueueJob returns. The frame bytes are
    the snapshot as fetched; byteLength and SHA-256 are computed
    over them here and verified again by the queue service."""
    return {
        "version": 1,
        "kind": "trio-assessment",
        "id": job_id_for(product, timestamp, frame_bytes),
        "product": product,
        "timestamp": timestamp,
        "image": {
            "mediaType": "image/jpeg",
            "byteLength": len(frame_bytes),
            "sha256": hashlib.sha256(frame_bytes).hexdigest(),
            "dataUrl": "data:image/jpeg;base64,"
                       + base64.b64encode(frame_bytes).decode(),
        },
    }


def envelope_error(env):
    """Local mirror of queue_service.validate_envelope's checks, for
    the in-process filing path (patrol files through the JobStore,
    not HTTP). Returns an error string or None."""
    if not isinstance(env, dict):
        return "envelope is not a JSON object"
    if env.get("version") != 1 or env.get("kind") != "trio-assessment":
        return "not a trio-assessment v1 envelope"
    if not isinstance(env.get("id"), str) or not env["id"]:
        return "envelope has no job id"
    if not isinstance(env.get("timestamp"), str) or not env["timestamp"]:
        return "envelope has no timestamp"
    image = env.get("image")
    if not isinstance(image, dict):
        return "envelope has no image object"
    data_url = image.get("dataUrl")
    if not isinstance(data_url, str) or \
            not data_url.startswith("data:image/jpeg;base64,"):
        return "image.dataUrl is not a JPEG data URL"
    try:
        raw = base64.b64decode(data_url.split(",", 1)[1], validate=True)
    except Exception:
        return "image.dataUrl does not base64-decode"
    if image.get("byteLength") != len(raw):
        return "image.byteLength does not match the decoded frame"
    if image.get("sha256") != hashlib.sha256(raw).hexdigest():
        return "image.sha256 does not match the decoded frame"
    return None


# -- geography (haversine mirror of js/command-flag.js) -------------------

def distance_meters(a, b):
    """Great-circle distance in meters between two
    {latitude, longitude} points — the same math as distanceMeters
    in js/command-flag.js."""
    R = 6371000
    d_lat = math.radians(b["latitude"] - a["latitude"])
    d_lng = math.radians(b["longitude"] - a["longitude"])
    lat1 = math.radians(a["latitude"])
    lat2 = math.radians(b["latitude"])
    h = math.sin(d_lat / 2) ** 2 + \
        math.cos(lat1) * math.cos(lat2) * math.sin(d_lng / 2) ** 2
    return 2 * R * math.asin(min(1, math.sqrt(h)))


def nearest_cameras(cameras, point, limit=3, exclude_id=None):
    """Cameras nearest to the point, nearest first, each as
    {camera, distance_m}. Computed from the loaded list only."""
    out = []
    for cam in cameras:
        if exclude_id is not None and cam["id"] == exclude_id:
            continue
        d = distance_meters(cam, point)
        if math.isfinite(d):
            out.append({"camera": cam, "distance_m": round(d, 1)})
    out.sort(key=lambda e: e["distance_m"])
    return out[:limit]
