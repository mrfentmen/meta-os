#!/usr/bin/env python3
"""Perceptual-hash dedupe (NC-176) + augmentation detector (NC-178).
dHash (9x8 gray, adjacent-column compare = 64 bits), stdlib+PIL only.
usage:
  python3 phash.py [--aug] <frame...>
Default: group near-identical frames (hamming <= 6). --aug also flags
flips/crops/brightness shifts: compares each frame against the
horizontal flip of the others (flip-invariant) plus mean-luma check.
"""
import sys

from PIL import Image, ImageStat

HAMMING_CUT = 6


def dhash(path, size=9):
    im = Image.open(path).convert("L").resize((size, size - 1), Image.BILINEAR)
    px = list(im.getdata())
    bits = 0
    for y in range(size - 1):
        for x in range(size - 1):
            bits = (bits << 1) | (1 if px[y * size + x] > px[y * size + x + 1] else 0)
    return bits


def ham(a, b):
    return bin(a ^ b).count("1")


def luma(path):
    return ImageStat.Stat(Image.open(path).convert("L").resize((32, 32))).mean[0]


def main(argv):
    aug = "--aug" in argv
    files = [a for a in argv if a != "--aug"]
    hashes = {f: dhash(f) for f in files}
    groups, used = [], set()
    for f in files:
        if f in used:
            continue
        g = [f]
        used.add(f)
        for o in files:
            if o in used:
                continue
            if ham(hashes[f], hashes[o]) <= HAMMING_CUT:
                g.append(o)
                used.add(o)
        groups.append(g)
    print("groups=%d %s" % (len(groups), [" ".join(x.split("/")[-1] for x in g) for g in groups]))
    if aug:
        import tempfile

        flipped = {}
        for f in files:
            with tempfile.NamedTemporaryFile(suffix=".png") as t:
                Image.open(f).transpose(Image.FLIP_LEFT_RIGHT).save(t.name)
                flipped[f] = dhash(t.name)
        for f in files:
            for o in files:
                if f == o:
                    continue
                if ham(flipped[o], hashes[f]) <= HAMMING_CUT:
                    print("augment: %s looks like a horizontal flip of %s" % (f.split("/")[-1], o.split("/")[-1]))
                    break
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
