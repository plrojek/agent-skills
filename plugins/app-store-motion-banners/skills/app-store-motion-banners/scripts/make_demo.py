"""Build two self-contained demo apps that look nothing alike (synthetic screens, UI pieces and artwork; no real app
data), to smoke-test the pipeline and to show the range of the scene generator.

usage: make_demo.py <demo_dir>      writes <demo_dir>/light/scene.json and <demo_dir>/dark/scene.json, then for each:
  python3 make_header.py <demo_dir>/light/scene.json <demo_dir>/light/page.html
  node render.mjs <demo_dir>/light/page.html 1920 823 <demo_dir>/light/still --stills 1.2,4.6,8.0
  python3 iphone_mock.py <demo_dir>/light/still_t1.2.png <demo_dir>/light/iphone.png --guides

light: a to-do app on warm cream, a serif headline, a dark pill, a drifting dot pattern and side phones.
dark:  a stats app on deep indigo, star and bolt markers dropping onto a line chart, pulsing rings in the side strips."""
import json, pathlib, random, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(sys.argv[1]).resolve()


def font(sz, bold=False):
    paths = ['/System/Library/Fonts/SFNS.ttf'] + (['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'] if bold else []) \
        + ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
    for p in paths:
        try:
            f = ImageFont.truetype(p, sz)
        except Exception:
            continue
        if bold:
            try: f.set_variation_by_name('Bold')
            except Exception: pass
        return f
    return ImageFont.load_default()


def tw(text, f): return int(ImageDraw.Draw(Image.new('L', (1, 1))).textlength(text, font=f))


def rounded(w, h, r, fill, outline=None, width=0):     # anti-aliased rounded card
    m = Image.new('L', (w * 4, h * 4), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w * 4 - 1, h * 4 - 1], radius=r * 4, fill=255)
    im = Image.new('RGBA', (w, h), fill)
    if outline: ImageDraw.Draw(im).rounded_rectangle([width // 2, width // 2, w - 1 - width // 2, h - 1 - width // 2], radius=r, outline=outline, width=width)
    im.putalpha(m.resize((w, h), Image.LANCZOS)); return im


def chip(text, fill, ink):
    f = font(46, True); im = rounded(tw(text, f) + 110, 102, 51, fill); ImageDraw.Draw(im).text((55, 24), text, font=f, fill=ink); return im


def save(d, items):
    (d / 'crops').mkdir(parents=True, exist_ok=True)
    for k, im in items.items(): im.save(d / 'crops' / f'{k}.png')


def cp(name, items, top=506, k=0.57):                # a chip piece, centred, every chip at the same scale
    w = round(items[name].width * k); return {"img": f"crops/{name}.png", "left": round(960 - w / 2), "top": top, "width": w, "kind": "chip"}


def grid4(names, top, w=512, h=None, left=452, gap=12):  # two columns x two rows in the iPhone's hero zone
    return [{"img": f"crops/{n}.png", "left": left + (i % 2) * (w + gap), "top": top + (i // 2) * (h + gap), "width": w} for i, n in enumerate(names)]


# ---------------------------------------------------------------- light: a to-do app
L = ROOT / 'light'; INK, MUTED, ACC, SOFT, WHITE = (67, 20, 7), (130, 112, 100), (234, 88, 12), (255, 237, 213), (255, 255, 255)


def task(title, sub, done):
    im = rounded(1224, 230, 52, WHITE); d = ImageDraw.Draw(im)
    if done:
        d.ellipse([69, 69, 161, 161], fill=ACC); d.line([(92, 117), (109, 134), (140, 98)], fill=WHITE, width=12)
    else:
        d.ellipse([69, 69, 161, 161], outline=(222, 210, 200), width=9)
    d.text((205, 50), title, font=font(52, True), fill=MUTED if done else INK)
    if done: d.line([(205, 84), (205 + tw(title, font(52, True)), 84)], fill=MUTED, width=4)
    d.text((205, 128), sub, font=font(38), fill=MUTED); return im


def progress(title, n, total):
    im = rounded(597, 430, 52, WHITE); d = ImageDraw.Draw(im)
    d.text((44, 44), title, font=font(50, True), fill=INK); d.text((44, 116), f'{n} of {total} done', font=font(38), fill=MUTED)
    d.rounded_rectangle([44, 222, 553, 258], radius=18, fill=(246, 238, 230)); d.rounded_rectangle([44, 222, 44 + int(509 * n / total), 258], radius=18, fill=ACC)
    for i in range(total):
        x = 44 + i * 64; d.ellipse([x, 312, x + 42, 354], fill=ACC if i < n else (240, 230, 220))
    return im


def reminder(time, title, sub):
    im = rounded(1224, 230, 52, WHITE); d = ImageDraw.Draw(im)
    d.rounded_rectangle([40, 50, 262, 180], radius=36, fill=SOFT); f = font(50, True)
    d.text((151 - tw(time, f) / 2, 86), time, font=f, fill=ACC)
    d.text((300, 50), title, font=font(52, True), fill=INK); d.text((300, 128), sub, font=font(38), fill=MUTED); return im


def shared(title, sub, n):
    im = rounded(1224, 230, 52, WHITE); d = ImageDraw.Draw(im)
    d.text((60, 50), title, font=font(52, True), fill=INK); d.text((60, 128), sub, font=font(38), fill=MUTED)
    cols = [(251, 146, 60), (244, 114, 182), (96, 165, 250), (52, 211, 153)]
    for i in range(n):
        x = 1100 - i * 78; d.ellipse([x - 4, 61, x + 108, 173], fill=WHITE); d.ellipse([x, 65, x + 104, 169], fill=cols[i % 4])
    return im


def screen_light(title, rows):
    s = Image.new('RGB', (1320, 2868), (255, 247, 237)); d = ImageDraw.Draw(s)
    d.text((90, 250), title, font=font(130, True), fill=INK)
    for j, (t, done) in enumerate(rows):
        y = 520 + j * 330; d.rounded_rectangle([60, y, 1260, y + 280], radius=60, fill=WHITE)
        if done: d.ellipse([110, y + 90, 210, y + 190], fill=ACC)
        else: d.ellipse([110, y + 90, 210, y + 190], outline=(222, 210, 200), width=10)
        d.text((260, y + 105), t, font=font(64, True), fill=MUTED if done else INK)
    return s


LI = {
    'today': chip('Today', INK, (255, 247, 237)), 'week': chip('This week', INK, (255, 247, 237)), 'shared': chip('Shared', INK, (255, 247, 237)),
    'task0': task('Buy oat milk', 'Groceries · done', True), 'task1': task('Call the plumber', 'Today · 18:00', False),
    'prog0': progress('Groceries', 4, 7), 'prog1': progress('Work', 2, 5),
    'rem0': reminder('09:30', 'Dentist', 'Thursday'), 'rem1': reminder('12:00', 'Pay the rent', 'Friday'),
    'rem2': reminder('17:45', 'Pick up the bike', 'Saturday'), 'rem3': reminder('19:00', 'Swimming', 'Sunday'),
    'sh0': shared('Weekend trip', '12 items · 3 people', 3), 'sh1': shared('Flat chores', '8 items · 2 people', 2),
    'sh2': shared('Book club', '5 items · 4 people', 4), 'sh3': shared('Garden', '9 items · 2 people', 2)}
save(L, LI)
(L / 'shots').mkdir(exist_ok=True)
for i, (t, rows) in enumerate([('Today', [('Buy oat milk', True), ('Call the plumber', False), ('Water plants', False), ('Gym', True)]),
                               ('This week', [('Dentist', False), ('Pay the rent', False), ('Swimming', False), ('Laundry', True)]),
                               ('Shared', [('Weekend trip', False), ('Flat chores', True), ('Book club', False), ('Garden', False)])]):
    screen_light(t, rows).save(L / 'shots' / f's{i + 1}.png')
(L / 'decor').mkdir(exist_ok=True)
r = random.Random(4); dots = []
for _ in range(260):
    x, y = r.uniform(0, 2040), r.uniform(10, 330); rad = r.uniform(3, 8); op = 0.42 * (1 - y / 360) + 0.05
    dots.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rad:.1f}" fill="{r.choice(["#ea580c", "#431407", "#fb923c"])}" fill-opacity="{op:.2f}"/>')
(L / 'decor' / 'dots.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="2040" height="340" viewBox="0 0 2040 340">{"".join(dots)}</svg>')
light = {
    "lang": "en", "loop": 10,
    "fonts": ["https://fonts.googleapis.com/css2?family=DM+Sans:wght@500;600&family=DM+Serif+Display&display=swap"],
    "theme": {"font": "'DM Sans',sans-serif", "ink": "#431407", "surface": "#431407", "accent": "#ea580c", "shadow": "#7c2d12", "glow": "#ffffff"},
    "background": "linear-gradient(180deg,#fffbf5 0%,#fff1e0 55%,#ffe2c2 100%)",
    "headline": {"text": "Plan less. Do more.", "top": 350, "font": "400 80px/88px 'DM Serif Display',serif"},
    "words": {"items": ["lists", "reminders", "sharing"], "top": 450, "lit_text": "#fff7ed"},
    "acts": [
        [cp('today', LI),
         {"img": "crops/task0.png", "left": 452, "top": 568, "width": 512}, {"img": "crops/task1.png", "left": 452, "top": 676, "width": 512},
         {"img": "crops/prog0.png", "left": 980, "top": 568, "width": 236}, {"img": "crops/prog1.png", "left": 1232, "top": 568, "width": 236}],
        [cp('week', LI)] + grid4(['rem0', 'rem1', 'rem2', 'rem3'], 568, h=96),
        [cp('shared', LI)] + grid4(['sh0', 'sh1', 'sh2', 'sh3'], 568, h=96)],
    "decor": [{"img": "decor/dots.svg", "left": -60, "top": 0, "width": 2040, "motion": "drift", "amount": 60}],
    "phones": [{"left": 64, "top": 150, "rotate": 6, "float": "A", "strip": ["shots/s1.png", "shots/s2.png", "shots/s3.png"]},
               {"left": 1536, "top": 150, "rotate": -6, "float": "B", "screen": "shots/s2.png"}],
    "credit": "Demo assets, generated"}
(L / 'scene.json').write_text(json.dumps(light, indent=1))

# ---------------------------------------------------------------- dark: a stats app
D = ROOT / 'dark'; CARD, EDGE, TXT, DIM, VIO, VIO2 = (30, 27, 58), (62, 56, 116), (255, 255, 255), (170, 166, 210), (167, 139, 250), (96, 84, 176)


def stat(value, label, bars):
    im = rounded(597, 500, 52, CARD, EDGE, 4); d = ImageDraw.Draw(im)
    d.text((44, 44), value, font=font(104, True), fill=TXT); d.text((44, 180), label, font=font(40), fill=DIM)
    for i, h in enumerate(bars):
        x = 44 + i * 74; d.rounded_rectangle([x, 450 - h, x + 50, 450], radius=12, fill=VIO if i == len(bars) - 1 else VIO2)
    return im


def ring(p, label):
    im = rounded(597, 500, 52, CARD, EDGE, 4); d = ImageDraw.Draw(im); box = [158, 60, 438, 340]
    d.arc(box, 0, 360, fill=(52, 47, 100), width=34); d.arc(box, -90, -90 + int(360 * p / 100), fill=VIO, width=34)
    f = font(80, True); d.text((298 - tw(f'{p}%', f) / 2, 155), f'{p}%', font=f, fill=TXT)
    f2 = font(38); d.text((298 - tw(label, f2) / 2, 400), label, font=f2, fill=DIM); return im


def compare(title, a, b):
    im = rounded(1224, 260, 52, CARD, EDGE, 4); d = ImageDraw.Draw(im); d.text((50, 34), title, font=font(46, True), fill=TXT)
    for j, (v, c, lab) in enumerate([(a, VIO, 'This week'), (b, VIO2, 'Last week')]):
        y = 112 + j * 72; d.rounded_rectangle([50, y, 850, y + 40], radius=20, fill=(46, 42, 88)); d.rounded_rectangle([50, y, 50 + int(800 * v), y + 40], radius=20, fill=c)
        d.text((890, y - 2), lab, font=font(38), fill=DIM)
    return im


def tip(title, sub, up):
    im = rounded(1224, 230, 52, CARD, EDGE, 4); d = ImageDraw.Draw(im); d.ellipse([55, 55, 175, 175], fill=(76, 29, 149))
    d.polygon([(115, 85), (145, 135), (85, 135)] if up else [(115, 145), (145, 95), (85, 95)], fill=VIO)
    d.text((215, 50), title, font=font(52, True), fill=TXT); d.text((215, 128), sub, font=font(38), fill=DIM); return im


DI = {
    'today': chip('Today', VIO, CARD), 'days': chip('7 days', VIO, CARD), 'goals': chip('Goals', VIO, CARD),
    'st0': stat('8,412', 'steps today', [120, 160, 90, 200, 150, 230, 260]), 'st1': stat('7h 40m', 'sleep', [180, 150, 210, 170, 140, 200, 220]),
    'rg0': ring(72, 'of weekly goal'), 'st2': stat('1,940', 'kcal burned', [90, 130, 170, 110, 190, 160, 210]),
    'cp0': compare('Steps', .82, .64), 'cp1': compare('Sleep', .70, .76), 'cp2': compare('Active minutes', .58, .41), 'cp3': compare('Water', .66, .60),
    'tp0': tip('Sleep +18 min', 'vs last week', True), 'tp1': tip('Walk after lunch', '+1,200 steps a day', True),
    'tp2': tip('Coffee after 16:00', 'later sleep on 3 days', False), 'tp3': tip('Rest day on Sunday', 'goal kept 4 weeks', True)}
save(D, DI)
(D / 'decor').mkdir(parents=True, exist_ok=True)
xs = [-20, 150, 290, 450, 640, 820, 1000, 1200, 1420, 1640, 1790, 1940]; ys = [300, 240, 270, 205, 262, 248, 275, 220, 250, 196, 232, 210]
line = ' '.join(f'{x},{y}' for x, y in zip(xs, ys))
(D / 'decor' / 'chart.svg').write_text(
    '<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="823" viewBox="0 0 1920 823"><defs><linearGradient id="a" x1="0" y1="180" x2="0" y2="350" gradientUnits="userSpaceOnUse">'
    '<stop offset="0" stop-color="#a78bfa" stop-opacity=".30"/><stop offset="1" stop-color="#a78bfa" stop-opacity="0"/></linearGradient></defs>'
    f'<polygon points="-20,350 {line} 1940,350" fill="url(#a)"/><polyline points="{line}" fill="none" stroke="#c4b5fd" stroke-opacity=".55" stroke-width="3" stroke-linejoin="round"/>'
    + ''.join(f'<circle cx="{x}" cy="{y}" r="5" fill="#ffffff" fill-opacity=".55"/>' for x, y in zip(xs, ys)) + '</svg>')
(D / 'decor' / 'rings.svg').write_text(
    '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300" viewBox="0 0 300 300">'
    + ''.join(f'<circle cx="150" cy="150" r="{r_}" fill="none" stroke="#a78bfa" stroke-opacity="{o}" stroke-width="{w}"/>' for r_, o, w in [(140, .18, 2), (110, .28, 3), (80, .42, 4), (50, .6, 6)])
    + '<circle cx="150" cy="150" r="22" fill="#a78bfa" fill-opacity=".8"/></svg>')
STAR = '<path d="M12 2.5l2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.4l-5.9 3.1 1.2-6.5-4.8-4.6 6.6-.9z"/>'
BOLT = '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>'
dark = {
    "lang": "en", "loop": 10,
    "fonts": ["https://fonts.googleapis.com/css2?family=Inter:wght@500;600&family=Space+Grotesk:wght@700&display=swap"],
    "theme": {"font": "Inter,sans-serif", "ink": "#ffffff", "surface": "#ffffff", "accent": "#7c3aed", "shadow": "#000000", "glow": "#8b5cf6"},
    "background": "radial-gradient(130% 100% at 50% 0%,#3b2f8f 0%,#1e1b4b 45%,#0c0a24 100%)",
    "headline": {"text": "Your week at a glance.", "top": 352, "font": "700 72px/84px 'Space Grotesk',sans-serif"},
    "words": {"items": ["track", "compare", "improve"], "top": 450},
    "acts": [
        [cp('today', DI)]
        + [{"img": f"crops/{n}.png", "left": 452 + i * 258, "top": 572, "width": 246} for i, n in enumerate(['st0', 'st1', 'rg0', 'st2'])],
        [cp('days', DI)] + grid4(['cp0', 'cp1', 'cp2', 'cp3'], 568, h=109),
        [cp('goals', DI)] + grid4(['tp0', 'tp1', 'tp2', 'tp3'], 568, h=96)],
    "decor": [{"img": "decor/chart.svg", "left": 0, "top": 0, "width": 1920},
              {"img": "decor/rings.svg", "left": 24, "top": 440, "width": 270, "motion": "pulse", "amount": 8, "period": 5},
              {"img": "decor/rings.svg", "left": 1626, "top": 410, "width": 270, "motion": "pulse", "amount": 8, "period": 5, "delay": 2.5}],
    "pins": {"icons": [STAR, BOLT], "targets": [[150, 240], [290, 270], [640, 262], [820, 248], [1000, 275], [1640, 196], [1790, 232]]},
    "credit": "Demo assets, generated"}
(D / 'scene.json').write_text(json.dumps(dark, indent=1))
print('wrote', L / 'scene.json', 'and', D / 'scene.json')
