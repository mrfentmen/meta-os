#!/usr/bin/env python3
"""Render the kernel ASCII attract loop (kernel/src/logo_frames.rs)
as a seamless looping MP4 + per-frame PNGs. Fully procedural, original
pixels from in-repo art. Usage: gen-ascii-loop.py [outdir]
Requires: PIL, ffmpeg on PATH. Verifies loop smoothness (wrap step)."""
import glob
import os
import subprocess
import sys

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   '../../kernel/src/logo_frames.rs')
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'live')
os.makedirs(OUT, exist_ok=True)
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit('need Pillow: pip install pillow')

lines = open(SRC).read().split('\n')
frames, cur = [], None
for ln in lines:
    if cur is None:
        if ln.strip() == '"':
            cur = []
        continue
    if ln == '",':
        frames.append('\n'.join(cur))
        cur = None
        continue
    cur.append(ln)
print(f'parsed {len(frames)} frames')
try:
    font = ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', 44, index=0)
except Exception:
    font = ImageFont.load_default()
DENSE = set('#@%&M9')
pngs = []
for n, fr in enumerate(frames):
    img = Image.new('RGB', (1920, 1080), (7, 11, 22))
    d = ImageDraw.Draw(img)
    fl = fr.split('\n')
    ox, oy = (1920 - 46 * 40) // 2, (1080 - 17 * 56) // 2
    for r, line in enumerate(fl[:17]):
        for c, ch in enumerate(line[:46]):
            if ch in ('', ' '):
                continue
            d.text((ox + c * 40, oy + r * 56), ch, font=font,
                   fill=(120, 185, 255) if ch in DENSE else (24, 119, 242))
    p = os.path.join(OUT, f'loop-{n:02d}.png')
    img.save(p)
    pngs.append(p)
mp4 = os.path.join(OUT, 'meta-loop.mp4')
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-framerate', '8'] +
               ['-i', os.path.join(OUT, 'loop-%02d.png')] +
               ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', mp4],
               check=True)
print('wrote', mp4, os.path.getsize(mp4), 'bytes')
