#!/usr/bin/env python3
"""screen_evidence.py — turn QEMU screendumps into reviewable evidence.

Why this exists: K2 is "the kernel draws its own text". A serial log cannot
prove that — the VGA console writes to memory that only a screen shows. QEMU's
`screendump` captures that memory, but a 640x400 PPM is not reviewable and a
"the file exists" check proves nothing.

So this reads the PPM, then reports what it actually contains:
  - size and distinct colours (a blank screen is one colour),
  - an 80x25 occupancy map: for each text cell, does it hold any non-background
    pixel? That map is the screen in text form and goes into the log,
  - occupied cell count and the rows that hold text.

It also writes a PNG next to the PPM (pure stdlib: zlib + crc32), because the
PPM is committed evidence nobody can open in a browser.

Exit: 0 when the screen has text on it, 1 when it is blank or unreadable.
Usage: screen_evidence.py <in.ppm> [more.ppm ...]
"""

import struct
import sys
import zlib


def read_ppm(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if not data.startswith(b"P6"):
        raise ValueError(f"{path}: not a binary PPM (P6)")
    # Header: magic, width, height, maxval, separated by whitespace, possibly
    # with '#' comments. Pixel data starts after the single whitespace byte
    # following maxval.
    fields = []
    i = 2
    while len(fields) < 3:
        while i < len(data) and data[i : i + 1].isspace():
            i += 1
        if i < len(data) and data[i : i + 1] == b"#":
            while i < len(data) and data[i : i + 1] != b"\n":
                i += 1
            continue
        start = i
        while i < len(data) and not data[i : i + 1].isspace():
            i += 1
        fields.append(int(data[start:i]))
    i += 1  # the whitespace byte after maxval
    width, height, maxval = fields
    if maxval != 255:
        raise ValueError(f"{path}: maxval {maxval}, expected 255")
    pixels = data[i:]
    if len(pixels) < width * height * 3:
        raise ValueError(
            f"{path}: {len(pixels)} pixel bytes, expected {width * height * 3}"
        )
    return width, height, pixels


def background_of(pixels, width, height):
    """The most common colour: the screen's background fill."""
    counts = {}
    for y in range(0, height, 2):
        row = y * width * 3
        for x in range(0, width, 2):
            idx = row + x * 3
            colour = pixels[idx : idx + 3]
            counts[colour] = counts.get(colour, 0) + 1
    return max(counts.items(), key=lambda kv: kv[1])[0]


def occupancy(pixels, width, height, bg):
    """80x25 map: True where a cell holds any pixel that is not background."""
    cols, rows = 80, 25
    cw, ch = width // cols, height // rows
    cells = []
    for row in range(rows):
        line = []
        for col in range(cols):
            found = False
            for y in range(row * ch, (row + 1) * ch):
                base = y * width * 3
                for x in range(col * cw, (col + 1) * cw):
                    idx = base + x * 3
                    if pixels[idx : idx + 3] != bg:
                        found = True
                        break
                if found:
                    break
            line.append(found)
        cells.append(line)
    return cells


def write_png(path, width, height, pixels):
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)  # filter: none
        raw += pixels[y * stride : (y + 1) * stride]

    def chunk(tag, payload):
        return (
            struct.pack(">I", len(payload))
            + tag
            + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        )

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as fh:
        fh.write(png)


def report(path):
    width, height, pixels = read_ppm(path)
    bg = background_of(pixels, width, height)
    cells = occupancy(pixels, width, height, bg)
    occupied = sum(sum(1 for c in line if c) for line in cells)
    text_rows = [r for r, line in enumerate(cells) if any(line)]

    print(f"screen: {path}")
    print(f"  size {width}x{height}, background rgb{tuple(bg)}, "
          f"cell {width // 80}x{height // 25}")
    print(f"  occupied cells: {occupied} of {80 * 25}")
    print(f"  rows holding text: {text_rows}")
    png = path.rsplit(".", 1)[0] + ".png"
    write_png(png, width, height, pixels)
    print(f"  wrote {png}")
    print("  occupancy map (# = cell holds text):")
    for line in cells:
        print("  |" + "".join("#" if c else " " for c in line) + "|")
    return occupied >= 100


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        return 2
    ok = True
    for path in argv[1:]:
        try:
            if not report(path):
                print(f"  BLANK: {path} carries no readable text", file=sys.stderr)
                ok = False
        except (OSError, ValueError) as err:
            print(f"screen: {err}", file=sys.stderr)
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
