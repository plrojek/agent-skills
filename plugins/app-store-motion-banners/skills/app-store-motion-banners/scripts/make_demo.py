"""Build a self-contained demo (synthetic screens and UI cards, no real app data) to smoke-test the pipeline.

usage: make_demo.py <demo_dir>      then:
  python3 make_header.py <demo_dir>/scene.json <demo_dir>/page.html
  node render.mjs <demo_dir>/page.html 1920 823 <demo_dir>/demo --stills 1.2,4.6,8.0
  python3 iphone_mock.py <demo_dir>/demo_t1.2.png <demo_dir>/iphone.png --guides"""
import json, pathlib, sys
from PIL import Image, ImageDraw, ImageFont
D = pathlib.Path(sys.argv[1]).resolve(); (D / 'crops').mkdir(parents=True, exist_ok=True); (D / 'shots').mkdir(exist_ok=True)
def font(sz):
    for p in ('/System/Library/Fonts/SFNS.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        try: return ImageFont.truetype(p, sz)
        except Exception: pass
    return ImageFont.load_default()
def rounded(w, h, r, fill):
    m = Image.new('L', (w * 4, h * 4), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w * 4 - 1, h * 4 - 1], radius=r * 4, fill=255)
    im = Image.new('RGBA', (w, h), fill); im.putalpha(m.resize((w, h), Image.LANCZOS)); return im
PAL = [(244, 114, 182), (52, 211, 153), (96, 165, 250), (251, 191, 36), (167, 139, 250), (248, 113, 113)]
def row(name, i):                                   # list row: photo square + two text lines (like a place row)
    im = rounded(1224, 275, 58, (255, 255, 255, 255)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, 390, 274], radius=58, fill=PAL[i % 6]); d.rectangle([330, 0, 390, 274], fill=PAL[i % 6])
    d.text((440, 80), name, font=font(52), fill=(14, 60, 100)); d.text((440, 160), 'Category · Detail · Detail', font=font(38), fill=(120, 140, 160))
    return im
def tile(name, i):                                  # square tile: colour block + name
    im = rounded(597, 590, 58, (255, 255, 255, 255)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, 596, 440], radius=58, fill=PAL[(i + 2) % 6]); d.rectangle([0, 380, 596, 440], fill=PAL[(i + 2) % 6])
    d.text((36, 480), name, font=font(50), fill=(14, 60, 100)); return im
def chip(text, fill, ink):
    f = font(46); w = int(ImageDraw.Draw(Image.new('L', (1, 1))).textlength(text, font=f)) + 110
    im = rounded(w, 102, 51, fill); ImageDraw.Draw(im).text((55, 24), text, font=f, fill=ink); return im
def bubble(text):
    f = font(46); w = int(ImageDraw.Draw(Image.new('L', (1, 1))).textlength(text, font=f)) + 100
    im = rounded(w, 115, 57, (14, 165, 233, 255)); ImageDraw.Draw(im).text((50, 30), text, font=f, fill=(255, 255, 255)); return im
items = {'q': bubble('Where should I go tonight?'), 'a1': row('First answer', 0), 'a2': row('Second answer', 1),
         'chipA': chip('Category A', (12, 74, 110, 255), (255, 255, 255)), 'chipB': chip('Open now', (14, 165, 233, 255), (255, 255, 255))}
for i in range(4): items[f'r{i}'] = row(f'Result {i + 1}', i + 2); items[f't{i}'] = tile(f'Tile {i + 1}', i)
for k, im in items.items(): im.save(D / 'crops' / f'{k}.png')
for i in range(3):                                  # phone screens
    s = Image.new('RGB', (1320, 2868), (240, 246, 252)); d = ImageDraw.Draw(s)
    d.rectangle([0, 0, 1320, 700], fill=PAL[i]); d.text((80, 300), f'Screen {i + 1}', font=font(120), fill=(255, 255, 255))
    for j in range(5): d.rounded_rectangle([60, 800 + j * 380, 1260, 1120 + j * 380], radius=58, fill=(255, 255, 255))
    s.save(D / 'shots' / f's{i + 1}.png')
c = 'crops/'
scene = {
  "lang": "en", "loop": 10,
  "fonts": ["https://fonts.googleapis.com/css2?family=Inter:wght@500;600&family=Outfit:wght@800&display=swap"],
  "background": "linear-gradient(180deg,#0a6fc2 0%,#1291e0 26%,#29aef2 41%,#1d9fe8 52%,#0d82d4 76%,#0866b4 100%)",
  "headline": {"text": "Your headline here.", "top": 352, "font": "800 74px/84px Outfit,sans-serif"},
  "words": {"items": ["first", "second", "third"], "top": 448},
  "acts": [
    [{"img": c + "q.png", "left": 1030, "top": 496, "width": 400, "kind": "chip"}, {"img": c + "a1.png", "left": 970, "top": 574, "width": 460},
     {"img": c + "a2.png", "left": 970, "top": 683, "width": 460}, {"img": c + "t0.png", "left": 600, "top": 520, "width": 270}],
    [{"img": c + "chipA.png", "left": 800, "top": 500, "width": 150, "kind": "chip"}, {"img": c + "chipB.png", "left": 962, "top": 500, "width": 140, "kind": "chip"}]
    + [{"img": c + f"r{i}.png", "left": 442 + (i % 2) * 524, "top": 552 + (i // 2) * 123, "width": 512} for i in range(4)],
    [{"img": c + "chipA.png", "left": 885, "top": 500, "width": 150, "kind": "chip"}]
    + [{"img": c + f"t{i}.png", "left": 454 + i * 257, "top": 552, "width": 241} for i in range(4)]],
  "skyline": {"seed": 8, "base": 345, "landmark_x": 560},
  "pins": {"count": 12},
  "phones": [{"left": -46, "top": 64, "rotate": -10, "scale": 0.92, "float": "B", "screen": "shots/s3.png"},
             {"left": 96, "top": 150, "rotate": 5, "float": "A", "strip": ["shots/s1.png", "shots/s2.png", "shots/s3.png"]},
             {"left": 1644, "top": 64, "rotate": 10, "scale": 0.92, "float": "B", "screen": "shots/s2.png"},
             {"left": 1504, "top": 150, "rotate": -5, "float": "A", "delay": -2.5, "screen": "shots/s1.png"}],
  "credit": "Demo assets, generated"}
(D / 'scene.json').write_text(json.dumps(scene, indent=1)); print('demo ready in', D)
