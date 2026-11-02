"""Live public camera source for the Imperium patrol: NYC DOT traffic cameras.

Del's order 2026-11-02 ("add ip cams like earth cam"). Source decision,
recorded in os-build/LIVE_CAMS.md: NYC DOT publishes its traffic cameras
as public data — a JSON camera list plus a per-camera still image that
refreshes. That is a real live input the patrol can assess. EarthCam and
similar networks license their feeds for their own player only, so they
are embed-only and are NOT pulled into this pipeline.

API shape verified live on 2026-11-02 (Pax, from the published endpoint):
  GET https://webcams.nyctmc.org/api/cameras
    -> [{"id": ..., "name": "Bay Pkwy @ 78 St (Kings Hwy)",
         "latitude": 40.60632, "longitude": -73.989087,
         "area": "Brooklyn", "isOnline": "true",
         "imageUrl": "https://webcams.nyctmc.org/api/cameras/<id>/image"}]
The still at imageUrl is a JPEG of the street right now. Polling stills
is the model: fetch, assess, record — the same shape as a patrol snapshot.

Every network call is an injectable seam (`fetch`) so tests run offline.
A frame is only ever returned after its bytes check out as an image;
an error page is never passed downstream as a frame.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import urllib.request
from datetime import datetime, timezone

API_URL = "https://webcams.nyctmc.org/api/cameras"
_USER_AGENT = "meta-os-imperium-livecams/1.0"
_TIMEOUT_S = 20

_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


class LiveCamError(RuntimeError):
    """A live-camera fetch or parse failed; no frame is produced."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def default_fetch(url: str) -> bytes:
    """GET a URL and return its bytes. file:// works too (tests, fixtures)."""
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with opener.open(req, timeout=_TIMEOUT_S) as resp:
        return resp.read()


def is_image_bytes(data: bytes) -> bool:
    return data.startswith(_JPEG_MAGIC) or data.startswith(_PNG_MAGIC)


def parse_cameras_report(payload: bytes):
    """Parse the DOT camera list into (cameras, skipped counts).
    Online cameras need an id, an image URL, and finite coordinates;
    anything else is counted and skipped, never plotted on a guess."""
    try:
        raw = json.loads(payload.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise LiveCamError(f"camera list is not JSON: {exc}") from exc
    if not isinstance(raw, list):
        raise LiveCamError("camera list payload is not a list")
    cameras = []
    skipped = {"not_object": 0, "offline": 0, "missing_id_or_url": 0,
               "missing_coordinates": 0}
    for entry in raw:
        if not isinstance(entry, dict):
            skipped["not_object"] += 1
            continue
        if str(entry.get("isOnline", "")).lower() != "true":
            skipped["offline"] += 1
            continue
        if not entry.get("id") or not entry.get("imageUrl"):
            skipped["missing_id_or_url"] += 1
            continue
        latitude = entry.get("latitude")
        longitude = entry.get("longitude")
        if (isinstance(latitude, bool) or
                not isinstance(latitude, (int, float)) or
                isinstance(longitude, bool) or
                not isinstance(longitude, (int, float)) or
                not math.isfinite(latitude) or
                not math.isfinite(longitude)):
            skipped["missing_coordinates"] += 1
            continue
        cameras.append({
            "id": entry["id"],
            "name": entry.get("name") or entry["id"],
            "area": entry.get("area") or "",
            "latitude": latitude,
            "longitude": longitude,
            "imageUrl": entry["imageUrl"],
            "source": "NYC DOT public traffic camera",
        })
    return cameras, skipped


def parse_cameras(payload: bytes) -> list[dict]:
    """Parse the DOT camera list. Only online cameras with an image URL
    and finite coordinates are returned; a malformed payload raises."""
    return parse_cameras_report(payload)[0]


def list_cameras(fetch=default_fetch, api_url: str = API_URL) -> list[dict]:
    return parse_cameras(fetch(api_url))


def pick(cameras: list[dict], area: str | None = None,
         name_contains: str | None = None, count: int = 1) -> list[dict]:
    """Deterministic selection: filter, sort by name, take the first N.
    Offline cameras are dropped here too, so a raw list never yields
    one; records from parse_cameras carry no isOnline field and are
    already online-only, so a missing flag means online."""
    chosen = [c for c in cameras
              if str(c.get("isOnline", "true")).lower() == "true"]
    if area:
        chosen = [c for c in chosen if c["area"].lower() == area.lower()]
    if name_contains:
        needle = name_contains.lower()
        chosen = [c for c in chosen if needle in c["name"].lower()]
    chosen.sort(key=lambda c: c["name"])
    return chosen[:count]


def fetch_snapshot(camera: dict, fetch=default_fetch) -> bytes:
    """Fetch one camera's current still. Raises unless the bytes are an
    image — an error page must never become a patrol frame."""
    data = fetch(camera["imageUrl"])
    if not is_image_bytes(data):
        raise LiveCamError(
            f"snapshot for {camera['name']!r} is not an image "
            f"({len(data)} bytes, starts {data[:16]!r})")
    return data


class LiveCamSource:
    """Round-robin live frame source in the patrol's fetch_snapshot shape.

    frame() -> (camera, image_bytes, timestamp_iso). Raises LiveCamError
    when no camera can produce a frame; the caller records the failure
    instead of inventing one.
    """

    def __init__(self, fetch=default_fetch, api_url: str = API_URL,
                 area: str | None = None, name_contains: str | None = None,
                 now=None):
        self._fetch = fetch
        self._now = now or (lambda: datetime.now(timezone.utc).isoformat())
        self._cameras = pick(list_cameras(fetch, api_url), area=area,
                             name_contains=name_contains, count=10_000)
        if not self._cameras:
            raise LiveCamError("no online cameras match the filter")
        self._idx = 0

    def cameras(self) -> list[dict]:
        return list(self._cameras)

    def frame(self):
        last_error = None
        for _ in range(len(self._cameras)):
            camera = self._cameras[self._idx % len(self._cameras)]
            self._idx += 1
            try:
                image = fetch_snapshot(camera, self._fetch)
            except Exception as exc:  # one dead camera must not kill the source
                last_error = exc
                continue
            stamp = self._now()
            return camera, image, stamp
        raise LiveCamError(f"every selected camera failed: {last_error}")


def _frame_record(camera: dict, image: bytes, stamp: str) -> dict:
    return {
        "camera_id": camera["id"],
        "camera_name": camera["name"],
        "area": camera["area"],
        "latitude": camera["latitude"],
        "longitude": camera["longitude"],
        "source": camera["source"],
        "image_url": camera["imageUrl"],
        "fetched_at": stamp,
        "image_sha256": hashlib.sha256(image).hexdigest(),
        "image_bytes": len(image),
        "live": True,
    }


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="NYC DOT live cameras for the Imperium patrol")
    parser.add_argument("--api-url", default=os.environ.get(
        "LIVECAMS_API_URL", API_URL))
    parser.add_argument("--area", default=None)
    parser.add_argument("--name", default=None, help="name substring filter")
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--list", action="store_true",
                        help="list matching online cameras and exit")
    parser.add_argument("--out", default=None,
                        help="directory to write snapshot JPEGs + records")
    parser.add_argument("--assess-one", action="store_true",
                        help="run ONE live frame through the production "
                             "assessment (spark_gen) and record the reading")
    parser.add_argument("--division", default="vigiles",
                        help="division lens for --assess-one")
    return parser


def main(argv=None) -> int:
    args = build_arg_parser().parse_args(argv)

    cameras = list_cameras(api_url=args.api_url)
    chosen = pick(cameras, area=args.area, name_contains=args.name,
                  count=args.count if not args.list else 10_000)
    if args.list:
        for cam in chosen:
            print(f"{cam['name']} [{cam['area']}] {cam['imageUrl']}")
        print(f"{len(chosen)} online cameras")
        return 0
    if not chosen:
        print("no online cameras match the filter", file=sys.stderr)
        return 1

    out_dir = args.out or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "livecam_records")
    os.makedirs(out_dir, exist_ok=True)

    if args.assess_one:
        source = LiveCamSource(api_url=args.api_url, area=args.area,
                               name_contains=args.name)
        camera, image, stamp = source.frame()
        frame_path = os.path.join(out_dir, "live-frame.jpg")
        with open(frame_path, "wb") as fh:
            fh.write(image)
        import spark_gen  # production assessment path (helper or direct)
        result = spark_gen.generate(args.division, frame_path, stamp)
        record = {"frame": _frame_record(camera, image, stamp),
                  "reading": result}
        record_path = os.path.join(out_dir, "live-reading.json")
        with open(record_path, "w", encoding="utf-8") as fh:
            json.dump(record, fh, indent=1)
        print(f"live frame: {camera['name']} [{camera['area']}] "
              f"{len(image)} bytes -> {frame_path}")
        print(f"reading recorded: {record_path}")
        return 0

    for camera in chosen:
        image = fetch_snapshot(camera)
        stamp = datetime.now(timezone.utc).isoformat()
        slug = camera["name"].lower()
        for ch in " @()/":
            slug = slug.replace(ch, "-")
        while "--" in slug:
            slug = slug.replace("--", "-")
        path = os.path.join(out_dir, f"{slug.strip('-')}.jpg")
        with open(path, "wb") as fh:
            fh.write(image)
        rec = _frame_record(camera, image, stamp)
        print(f"{camera['name']} [{camera['area']}] "
              f"{rec['image_bytes']} bytes sha256 {rec['image_sha256'][:12]} "
              f"-> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
