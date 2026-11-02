# Python evidence store — behaviour record (B227)

Source: `server/queue/evidence.py` (read at 244 lines). Event-gated
person evidence: frames, face crops and the BOLO block. It is passive
by construction — nothing here runs on a baseline check, and no
identity field exists in its output.

## Inputs

- `detect_face_boxes(jpeg_bytes, detector=None)`
  (`evidence.py:60-100`): JPEG bytes; optional injected detector
  returning `{"x","y","w","h"}` boxes.
- `padded_crop_box(box, width, height, pad_ratio=0.35)`
  (`evidence.py:102-116`): one box and the frame size.
- `crop_jpeg(jpeg_bytes, box, pad_ratio=0.35)`
  (`evidence.py:118-132`): JPEG bytes plus a box.
- `extract_visible_marks(observations)` (`evidence.py:150-175`): the
  crew assessments' observation list.
- `build_bolo(record, descriptions, evidence_files, visible_marks=None)`
  (`evidence.py:177-212`): incident record, recorded descriptions,
  captured file entries, optional marks.
- `picture_refs(evidence_files)` (`evidence.py:214-233`): the
  incident's evidence file list.
- `frame_ref_name(kind, camera_id, frame_bytes)`
  (`evidence.py:235-244`): file kind, camera id, frame bytes.

## Outputs

- `detect_face_boxes` returns `(boxes, name)`: at most `MAX_FACES`
  (4) boxes sorted by area descending, and a detector name —
  `"injected"`, `"opencv-haar"` or `"unavailable"`
  (`evidence.py:60-100`). `MIN_FACE_PX` (48) is passed to the Haar
  detector only; the injected path is not size-filtered.
- `padded_crop_box` returns `(x0, y0, x1, y1)` clamped to the frame,
  or `None` when nothing of the box lies inside
  (`evidence.py:102-116`).
- `crop_jpeg` returns JPEG bytes, or `None` when the padded box is
  outside the frame (`evidence.py:118-132`).
- `extract_visible_marks` returns deduped mark strings, order kept,
  capped at `MAX_MARKS` (6), with absence reports excluded
  (`evidence.py:150-175`).
- `build_bolo` returns a dict whose key set is exactly `BOLO_KEYS`
  (`evidence.py:177-212`): the flag's division/category/camera/area/
  time, frame refs, crop count, up to 6 descriptions, up to 6 marks,
  `direction_of_travel: None` and the direction note.
- `picture_refs` returns `{"frame": ..., "evidence_crop": ...}`;
  flag-frame preferred, investigation-frame as fallback, `None` when
  neither exists (`evidence.py:214-233`).
- `frame_ref_name` returns `<kind>-<safe-camera>-<6 hex>.jpg`, with
  every non-alphanumeric camera char (except `-` and `_`) replaced by
  `-` (`evidence.py:235-244`).

## Refusals

| Situation | Behaviour | Source |
|---|---|---|
| Frame does not decode while a detector exists | `ValueError` propagates | `evidence.py:60-100` |
| No cv2 / no cascade / detector error | `([], "unavailable")`, never a guessed box | `evidence.py:60-100` |
| `crop_jpeg` cannot decode, or PIL is missing | the exception propagates; the caller records it | `evidence.py:118-132` |
| Padded box is entirely outside the frame | `None` | `evidence.py:102-116` |
| Observation is not a dict, has no string description, or is a bare `Visible marks:` prefix | contributes nothing | `evidence.py:150-175` |
| Mark line is an absence report (`no ...`, `none ...`, `not ...`, or a listed phrase) | contributes nothing | `evidence.py:134-148` |
| Evidence entry lacks a `ref` / `kind`, or `kind` is not a frame kind | excluded from `frame_files`; crops counted only for `face-crop` | `evidence.py:177-212` |

## What it writes

Nothing. Every function is pure: it returns bytes, dicts or names.
The crew is the writer (`crew.py` saves the returned bytes and files
the BOLO on the incident timeline).

## Findings (reported, not fixed)

1. **Injected boxes are not size-filtered.** `MIN_FACE_PX` applies to
   the Haar path only; an injected detector can return a 1-pixel box
   (`evidence.py:60-100`).
2. **`crop_jpeg` imports PIL inside the function.** A runtime without
   PIL fails at the first crop, not at import or startup
   (`evidence.py:118-132`).
3. **`build_bolo` does not validate its inputs.** A non-dict `record`
   raises; a `camera` value that is not a dict raises
   (`evidence.py:177-212`).
4. **Descriptions are capped at six with a literal**, while marks use
   the named `MAX_MARKS`; the two bounds can drift (`evidence.py:177-212`).
5. **`direction_of_travel` is always `None`.** That is deliberate (no
   direction from a still frame), not an unfilled field
   (`evidence.py:177-212`).

## Tests

Missing cases are in `tests/queue-python/test_evidence_store_missing.py`
(detector ordering/cap, crop-box edges, ref names, BOLO caps, picture
selection).
