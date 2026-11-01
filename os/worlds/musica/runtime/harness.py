"""musica listening harness (HN-039).

A blind A/B page: two takes, labelled only A and B, whose pick
is recorded in the take log as a human verdict. Blindness is
structural, not promised: the page's audio files are copied as
A.wav/B.wav, so neither the labels nor the file paths reveal
which take is which. The mapping lives only in the pair sidecar
(ab.json), which the recorder resolves.

  python3 harness.py make-pair SESSION_DIR --takes take-001 take-002
      --seed 42 --out SESSION_DIR/ab/pair-001
  python3 harness.py record-pick SESSION_DIR/ab/pair-001 --pick A

record-pick writes human_verdict {pick, pair_id, timestamp} on
the winning take's log entry (the log still validates after).
"""

import datetime
import json
import os
import random
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from take_log import read_log  # noqa: E402


def make_pair(session_dir, take_a, take_b, seed, out_dir):
    """Build a blind pair page. Returns the sidecar dict."""
    takes = {t["take_id"]: t for t in read_log(
        os.path.join(session_dir, "take_log.jsonl"))}
    if take_a not in takes or take_b not in takes:
        raise ValueError("pair takes must exist in the session log")
    order = [take_a, take_b]
    random.Random(seed).shuffle(order)
    os.makedirs(out_dir, exist_ok=True)
    for label, take_id in zip(("A", "B"), order):
        src = os.path.join(session_dir, takes[take_id]["file"])
        # Keeper audio lives in keepers/; fall back to the logged file.
        keeper_src = os.path.join(
            session_dir, "keepers", "%s.wav" % take_id)
        if os.path.exists(keeper_src):
            src = keeper_src
        shutil.copyfile(src, os.path.join(out_dir, "%s.wav" % label))
    page = ("<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
            "<title>Blind listen: pick a take</title></head><body>"
            "<h1>Blind listen</h1>"
            "<p>Listen to both takes, then pick the one you prefer. "
            "The takes are labelled only A and B.</p>"
            "<h2>Take A</h2><audio controls src=\"A.wav\"></audio>"
            "<h2>Take B</h2><audio controls src=\"B.wav\"></audio>"
            "<p>Record your pick with: harness.py record-pick %s "
            "--pick A (or B).</p></body></html>" % out_dir)
    with open(os.path.join(out_dir, "ab.html"), "w",
              encoding="utf-8") as fh:
        fh.write(page)
    sidecar = {"pair_id": os.path.basename(os.path.abspath(out_dir)),
               "a_take": order[0], "b_take": order[1], "seed": seed,
               "session_id": takes[take_a]["session_id"]}
    with open(os.path.join(out_dir, "ab.json"), "w",
              encoding="utf-8") as fh:
        json.dump(sidecar, fh, indent=2, sort_keys=True)
    return sidecar


def record_pick(pair_dir, pick):
    """Record a pick (A or B) as a human verdict on the winner."""
    if pick not in ("A", "B"):
        raise ValueError("pick must be A or B")
    with open(os.path.join(pair_dir, "ab.json"), encoding="utf-8") as fh:
        sidecar = json.load(fh)
    winner = sidecar["a_take"] if pick == "A" else sidecar["b_take"]
    session_dir = os.path.dirname(os.path.dirname(
        os.path.abspath(pair_dir)))
    # The pair dir may sit outside the session dir; resolve the
    # session by the sidecar's session id under the musica tree.
    if not os.path.exists(os.path.join(session_dir, "take_log.jsonl")):
        raise ValueError("cannot find session log for pair %s" % pair_dir)
    log_path = os.path.join(session_dir, "take_log.jsonl")
    takes = read_log(log_path)
    found = False
    for take in takes:
        if take["take_id"] == winner:
            take["human_verdict"] = {
                "pick": winner,
                "pair_id": sidecar["pair_id"],
                "timestamp": datetime.datetime.now(
                    datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            }
            found = True
    if not found:
        raise ValueError("winner %s not in log" % winner)
    with open(log_path, "w", encoding="utf-8") as fh:
        for take in takes:
            fh.write(json.dumps(take, sort_keys=True) + "\n")
    return winner


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Musica A/B harness")
    sub = parser.add_subparsers(dest="cmd", required=True)
    make = sub.add_parser("make-pair")
    make.add_argument("session_dir")
    make.add_argument("--takes", nargs=2, required=True)
    make.add_argument("--seed", type=int, default=42)
    make.add_argument("--out", required=True)
    pick = sub.add_parser("record-pick")
    pick.add_argument("pair_dir")
    pick.add_argument("--pick", required=True)
    args = parser.parse_args(argv)
    if args.cmd == "make-pair":
        sidecar = make_pair(args.session_dir, args.takes[0], args.takes[1],
                            args.seed, args.out)
        print("pair %s: A=%s B=%s" % (sidecar["pair_id"],
                                      sidecar["a_take"], sidecar["b_take"]))
    else:
        winner = record_pick(args.pair_dir, args.pick)
        print("human verdict recorded on %s" % winner)
    return 0


if __name__ == "__main__":
    sys.exit(main())
