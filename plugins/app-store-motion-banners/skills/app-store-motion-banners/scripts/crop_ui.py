"""Cut UI pieces (cards, chips, bubbles) out of real app screenshots into transparent PNGs with rounded corners.

usage: crop_ui.py <spec.json> <out_dir>   (see references/crops.example.json)
spec: {"base": "<dir with screenshots>", "crops": {"name": {"src": "file.png", "box": [x0,y0,x1,y1],
       "r": 58, "r_br": 12 (optional per-corner radius), "pad_bottom": 0 (white rows added below, then the
       bottom corners are rounded too)}}}
Coordinates are screenshot pixels. Find them with a grid overlay (grid.py) or by scanning a column/row
for background-coloured runs: cards sit on a flat background, so their edges are exact."""
import json, pathlib, sys
from PIL import Image, ImageDraw
spec = json.loads(pathlib.Path(sys.argv[1]).read_text()); out = pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
base = pathlib.Path(spec['base']).expanduser()
SS = 4  # supersampling for anti-aliased corners
for name, c in spec['crops'].items():
    im = Image.open(base / c['src']).convert('RGB').crop(tuple(c['box']))
    if c.get('pad_bottom'):
        fill = tuple(c.get('pad_fill', (255, 255, 255)))
        ext = Image.new('RGB', (im.width, im.height + c['pad_bottom']), fill); ext.paste(im, (0, 0)); im = ext
    w, h = im.size; r = c.get('r', 58)
    radii = {k: c.get(f'r_{k}', r) for k in ('tl', 'tr', 'br', 'bl')}
    m = Image.new('L', (w * SS, h * SS), 0); d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], radius=max(radii.values()) * SS, fill=255)
    for k, (cx, cy) in {'tl': (0, 0), 'tr': (w * SS, 0), 'br': (w * SS, h * SS), 'bl': (0, h * SS)}.items():
        rk = radii[k] * SS; R = max(radii.values()) * SS
        if rk < R:  # square off this corner, then round it with its own smaller radius
            x0 = 0 if cx == 0 else cx - R; y0 = 0 if cy == 0 else cy - R
            d.rectangle([x0, y0, x0 + R, y0 + R], fill=255)
            if rk > 0:
                bx0 = 0 if cx == 0 else cx - 2 * rk; by0 = 0 if cy == 0 else cy - 2 * rk
                cut = Image.new('L', (2 * rk, 2 * rk), 0); ImageDraw.Draw(cut).ellipse([0, 0, 2 * rk - 1, 2 * rk - 1], fill=255)
                corner = Image.new('L', (rk, rk), 0)
                ox = 0 if cx == 0 else rk; oy = 0 if cy == 0 else rk
                corner.paste(cut.crop((ox, oy, ox + rk, oy + rk)), (0, 0))
                px = 0 if cx == 0 else cx - rk; py = 0 if cy == 0 else cy - rk
                m.paste(corner, (px, py))
    rgba = im.convert('RGBA'); rgba.putalpha(m.resize((w, h), Image.LANCZOS))
    rgba.save(out / f'{name}.png'); print(f'{name}: {w}x{h}')
