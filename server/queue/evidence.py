"""evidence.py — event-gated person evidence for flagged incidents.

Del's design (2026-10-31): the system is passive. Nothing in here
runs on a baseline patrol check — evidence exists only because an
incident was flagged and survived (or is surviving) the crew's own
review pipeline. What gets captured, per flagged incident:

  * the exact frames the crew assessed (the flagging frame and the
    investigation frames), saved verbatim — evidence, not a
    re-fetch;
  * face crops: where a real face DETECTOR finds a face in a
    captured frame, the face region (padded) is cropped and saved
    alongside the frame. Detection locates a face in a frame;
    nothing here matches a face against anything, builds a
    template, or names a person — there is no identity field
    anywhere in this module's output, by construction;
  * a BOLO block for the response package: the flagged category,
    the camera, the recorded person descriptions from the crew's
    own assessments, the evidence file references, and the face
    crop count. Direction of travel is None: it is not determined
    from still frames, and this module does not invent it.

Detector honesty: the production detector is OpenCV's Haar
cascade when (and only when) cv2 is importable in the runtime.
Where it is not, detection reports "unavailable" and produces no
crops — never a guessed box. Cropping uses PIL, which the queue
runtime already carries; a frame that does not decode raises, and
the caller records the failure instead of papering over it.

Stdlib + optional cv2/PIL.
"""
import hashlib
import io

MAX_FACES = 4
MIN_FACE_PX = 48

# The BOLO's exact key set. A test pins this list: a new key is a
# deliberate schema change, and an identity-shaped key (a name, an
# id, a match) must never appear here.
BOLO_KEYS = ("division", "category", "camera_name", "area",
             "flagged_at", "frame_files", "face_crops",
             "person_descriptions", "direction_of_travel",
             "direction_note")


def detect_face_boxes(jpeg_bytes, detector=None):
    """Locate faces in one JPEG frame. Returns (boxes, name):
    boxes are {"x", "y", "w", "h"} pixel dicts, largest first, at
    most MAX_FACES; name says which detector actually ran —
    "injected" for a caller-supplied detector (tests), "opencv-haar"
    for the production cascade, "unavailable" when no detector
    exists in this runtime. A frame that does not decode raises
    ValueError: a corrupt evidence frame is a recorded failure,
    not a silent empty result."""
    if detector is not None:
        boxes = [dict(b) for b in detector(jpeg_bytes)]
        boxes.sort(key=lambda b: b["w"] * b["h"], reverse=True)
        return boxes[:MAX_FACES], "injected"
    try:
        import cv2
        import numpy as np
    except Exception:
        return [], "unavailable"
    try:
        cascade_path = (cv2.data.haarcascades
                        + "haarcascade_frontalface_default.xml")
        cascade = cv2.CascadeClassifier(cascade_path)
        if cascade.empty():
            return [], "unavailable"
        raw = np.frombuffer(jpeg_bytes, dtype=np.uint8)
        image = cv2.imdecode(raw, cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("frame does not decode as an image")
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        found = cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5,
            minSize=(MIN_FACE_PX, MIN_FACE_PX))
        boxes = [{"x": int(x), "y": int(y), "w": int(w), "h": int(h)}
                 for (x, y, w, h) in found]
        boxes.sort(key=lambda b: b["w"] * b["h"], reverse=True)
        return boxes[:MAX_FACES], "opencv-haar"
    except ValueError:
        raise
    except Exception:
        return [], "unavailable"


def padded_crop_box(box, width, height, pad_ratio=0.35):
    """The crop rectangle for a face box, padded by pad_ratio of
    the box size on every side and clamped to the frame. Returns
    (x0, y0, x1, y1) ints, or None when nothing of the box lies
    inside the frame."""
    pad_x = box["w"] * pad_ratio
    pad_y = box["h"] * pad_ratio
    x0 = max(0, int(box["x"] - pad_x))
    y0 = max(0, int(box["y"] - pad_y))
    x1 = min(width, int(box["x"] + box["w"] + pad_x))
    y1 = min(height, int(box["y"] + box["h"] + pad_y))
    if x1 <= x0 or y1 <= y0:
        return None
    return (x0, y0, x1, y1)


def crop_jpeg(jpeg_bytes, box, pad_ratio=0.35):
    """Crop one face region (padded) out of a JPEG frame and
    return the crop as JPEG bytes. Raises when the frame does not
    decode or PIL is missing — the caller records it."""
    from PIL import Image
    image = Image.open(io.BytesIO(jpeg_bytes))
    image.load()
    region = padded_crop_box(box, image.width, image.height,
                             pad_ratio)
    if region is None:
        return None
    out = io.BytesIO()
    image.crop(region).convert("RGB").save(out, "JPEG", quality=88)
    return out.getvalue()


def build_bolo(record, descriptions, evidence_files):
    """The person-evidence block carried by the response package
    and filed on the incident record. Built ONLY from what the
    crew itself recorded: the flag's category and camera, the
    observation descriptions its assessments returned (deduped,
    order kept, capped), and the evidence files it captured. The
    key set is exactly BOLO_KEYS — observation and evidence only,
    no identity field exists to fill."""
    seen = []
    for text in descriptions:
        if isinstance(text, str) and text and text not in seen:
            seen.append(text)
    files = evidence_files or []
    return {
        "division": record.get("division"),
        "category": record.get("category"),
        "camera_name": (record.get("camera") or {}).get("name"),
        "area": (record.get("camera") or {}).get("area"),
        "flagged_at": record.get("created_at"),
        "frame_files": [f["ref"] for f in files
                        if f.get("kind") in ("flag-frame",
                                             "investigation-frame")],
        "face_crops": sum(1 for f in files
                          if f.get("kind") == "face-crop"),
        "person_descriptions": seen[:6],
        "direction_of_travel": None,
        "direction_note": "Not determined from still frames.",
    }


def frame_ref_name(kind, camera_id, frame_bytes):
    """Evidence file name: kind + camera + a short frame hash, so
    two frames from the same camera never collide and the name
    itself carries no information beyond provenance."""
    digest = hashlib.sha256(frame_bytes).hexdigest()[:6]
    safe_camera = "".join(
        c if c.isalnum() or c in "-_" else "-" for c in camera_id)
    return f"{kind}-{safe_camera}-{digest}.jpg"
