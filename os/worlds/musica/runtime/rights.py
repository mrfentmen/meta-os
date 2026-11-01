"""musica rights log (HN-035).

Only own, Creative Commons, or public-domain material enters the
catalogue. Every track's rights line must be filled; a track with
an empty or unrecognised rights line is rejected, never exported.

check_catalogue(session_dir) validates catalogue.json and writes
rights.json (per-track pass/fail). With enforce=True, violating
tracks are removed from catalogue.json and listed as rejected in
rights.json. Keeper audio for a rejected track stays on disk but
is no longer catalogued.
"""

import json
import os
import sys


def rights_ok(licence):
    """A rights line passes when it names own, CC, or public domain."""
    if not isinstance(licence, str) or not licence.strip():
        return False
    text = licence.lower()
    return ("own" in text or "cc-" in text or "cc0" in text
            or "public domain" in text or "public-domain" in text)


def check_catalogue(session_dir, enforce=False):
    """Validate a session catalogue's rights lines. Returns violations."""
    import datetime
    catalogue_path = os.path.join(session_dir, "catalogue.json")
    with open(catalogue_path, encoding="utf-8") as fh:
        catalogue = json.load(fh)
    violations = []
    kept = []
    for track in catalogue.get("tracks", []):
        if rights_ok(track.get("licence")):
            kept.append(track)
        else:
            violations.append({
                "take_id": track.get("take_id"),
                "title": track.get("title"),
                "licence": track.get("licence"),
                "reason": "empty or unrecognised rights line",
            })
    if enforce and violations:
        catalogue["tracks"] = kept
        with open(catalogue_path, "w", encoding="utf-8") as fh:
            json.dump(catalogue, fh, indent=2, sort_keys=True)
    rights = {
        "session_id": catalogue.get("session_id",
                                    os.path.basename(
                                        os.path.abspath(session_dir))),
        "checked": datetime.datetime.now(
            datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "tracks_checked": len(catalogue.get("tracks", [])) + len(violations),
        "passed": len(kept),
        "rejected": violations,
    }
    with open(os.path.join(session_dir, "rights.json"), "w",
              encoding="utf-8") as fh:
        json.dump(rights, fh, indent=2, sort_keys=True)
    return violations


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Musica rights check")
    parser.add_argument("session_dir")
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args(argv)
    violations = check_catalogue(args.session_dir, args.enforce)
    print("rights violations=%d enforced=%s"
          % (len(violations), args.enforce))
    return 0


if __name__ == "__main__":
    sys.exit(main())
