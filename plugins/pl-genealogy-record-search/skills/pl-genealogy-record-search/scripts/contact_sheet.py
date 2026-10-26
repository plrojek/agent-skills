# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow==11.3.0"]
# ///
"""Two helpers for reading downloaded scans. Run with uv: `uv run contact_sheet.py ...`

  contact_sheet.py sheet <out.jpg> <scan> [<scan> ...] [--y 0 0.13] [--x 0 1] [--width 1500]
      Crop the same strip from many scans, label each with its file name in red and stack
      them into one image. The top ~13 % of a register page carries the year (and often the
      month and act numbers), so one sheet of 12 strips maps a dozen scans in one read.
      Birth books in landscape: try --y 0.12 0.24 --x 0.13 0.62.
  contact_sheet.py crop <scan> <out.jpg> --x 0.04 0.49 --y 0.03 0.53 [--scale 2]
      One region, upscaled with LANCZOS. Half a page at 2x makes entries legible; one row
      at 3x settles a surname.

Coordinates are fractions of the image width and height.
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont


def _box(img, xs, ys):
    w, h = img.size
    return (int(xs[0] * w), int(ys[0] * h), int(xs[1] * w), int(ys[1] * h))


def sheet(out, scans, xs, ys, width, per_sheet):
    strips = []
    for path in scans:
        with Image.open(path) as im:
            s = im.convert("RGB").crop(_box(im, xs, ys))
        s = s.resize((width, max(1, int(s.height * width / s.width))), Image.LANCZOS)
        label_w = 220
        tile = Image.new("RGB", (width + label_w, s.height), "white")
        tile.paste(s, (label_w, 0))
        d = ImageDraw.Draw(tile)
        font = ImageFont.load_default(size=max(18, min(48, s.height // 3)))
        d.text((8, 8), os.path.splitext(os.path.basename(path))[0], fill=(220, 0, 0), font=font)
        d.line([(0, s.height - 1), (tile.width, s.height - 1)], fill=(160, 160, 160), width=2)
        strips.append(tile)
    root, ext = os.path.splitext(out)
    written = []
    for n in range(0, len(strips), per_sheet):
        part = strips[n:n + per_sheet]
        canvas = Image.new("RGB", (part[0].width, sum(t.height for t in part)), "white")
        y = 0
        for t in part:
            canvas.paste(t, (0, y))
            y += t.height
        name = out if len(strips) <= per_sheet else f"{root}-{n // per_sheet + 1}{ext or '.jpg'}"
        canvas.save(name, quality=88)
        written.append(name)
    return written


def crop(src, out, xs, ys, scale):
    with Image.open(src) as im:
        c = im.convert("RGB").crop(_box(im, xs, ys))
    if scale != 1:
        c = c.resize((int(c.width * scale), int(c.height * scale)), Image.LANCZOS)
    c.save(out, quality=92)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheet")
    s.add_argument("out")
    s.add_argument("scans", nargs="+")
    s.add_argument("--x", nargs=2, type=float, default=[0.0, 1.0])
    s.add_argument("--y", nargs=2, type=float, default=[0.0, 0.13])
    s.add_argument("--width", type=int, default=1500)
    s.add_argument("--per-sheet", type=int, default=12)
    c = sub.add_parser("crop")
    c.add_argument("scan")
    c.add_argument("out")
    c.add_argument("--x", nargs=2, type=float, required=True)
    c.add_argument("--y", nargs=2, type=float, required=True)
    c.add_argument("--scale", type=float, default=2.0)
    o = ap.parse_args(argv)
    for pair in (o.x, o.y):
        if not (0 <= pair[0] < pair[1] <= 1):
            ap.error("coordinates are fractions: 0 <= start < end <= 1")
    if o.cmd == "sheet":
        for name in sheet(o.out, o.scans, o.x, o.y, o.width, o.per_sheet):
            print(name)
    else:
        print(crop(o.scan, o.out, o.x, o.y, o.scale))
    return 0


if __name__ == "__main__":
    sys.exit(main())
