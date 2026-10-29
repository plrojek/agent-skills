"""Find exact rectangles of UI elements in a screenshot.

usage:
  measure.py col  <img> <x> [y0]          runs of background / white / other down a column
  measure.py row  <img> <y>               runs across a row
  measure.py grid <img> x0 y0 x1 y1 <out.png> [step=50]   crop with a labelled coordinate grid (red y, blue x)
Cards sit on a flat background, so the run boundaries are the card edges to the pixel. Confirm with `grid`."""
import sys
from PIL import Image, ImageDraw
def cls(p):
    r, g, b = p[:3]
    if r > 250 and g > 250 and b > 250: return 'W'                         # white card
    if abs(r - g) < 8 and abs(g - b) < 10 and r > 225: return 'L'          # light page background
    return 'x'                                                              # anything else (photo, text, colour)
def runs(vals, start):
    out, prev, s = [], None, start
    for i, c in enumerate(vals):
        if c != prev:
            if prev is not None: out.append((prev, s, start + i - 1))
            prev, s = c, start + i
    out.append((prev, s, start + len(vals) - 1))
    return [r for r in out if r[2] - r[1] >= 4]
cmd, img = sys.argv[1], Image.open(sys.argv[2]).convert('RGB')
if cmd == 'col':
    x = int(sys.argv[3]); y0 = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    print(runs([cls(img.getpixel((x, y))) for y in range(y0, img.height)], y0))
elif cmd == 'row':
    y = int(sys.argv[3]); print(runs([cls(img.getpixel((x, y))) for x in range(img.width)], 0))
elif cmd == 'grid':
    x0, y0, x1, y1 = map(int, sys.argv[3:7]); out = sys.argv[7]; step = int(sys.argv[8]) if len(sys.argv) > 8 else 50
    c = img.crop((x0, y0, x1, y1)); d = ImageDraw.Draw(c)
    for y in range(y0 - y0 % step + step, y1, step):
        d.line([(0, y - y0), (c.width, y - y0)], fill=(255, 0, 0) if y % (2 * step) == 0 else (255, 160, 160)); d.text((2, y - y0 + 1), str(y), fill=(255, 0, 0))
    for x in range(x0 - x0 % step + step, x1, step):
        d.line([(x - x0, 0), (x - x0, c.height)], fill=(0, 0, 255) if x % (2 * step) == 0 else (160, 160, 255)); d.text((x - x0 + 2, 2), str(x), fill=(0, 0, 255))
    c.save(out); print('wrote', out)
else:
    sys.exit(__doc__)
