"""Generate an animated App Store product-page HEADER as a static HTML page (1920x823 CSS px, rendered at 2x =
3840x1646, the 21:9 header size). Every animation period divides the loop, so the last frame flows into frame 0.

usage: make_header.py <scene.json> <out.html>

The layout follows the iPhone window measured on a device (references/iphone-window.md):
  - the iPhone shows the FULL height and only x 336-1584 of the 1920-wide artboard;
  - y < 171 is the status bar + Dynamic Island (x 760-1160); y 186-327 holds the store's back button (x 389-524) and
    mute/share capsule (x 1219-1533; on the narrowest phones the buttons reach x 554 / 1147);
  - readable text goes at y >= 345 inside the window, the hero motion in x 430-1490, y 345-790;
  - x < 430 and x > 1490 show only on iPad and Mac.
The script warns about any headline or UI piece that breaks these rules.

What it builds, back to front: background and an optional soft glow; decor image layers; an optional skyline; markers
("pins") that drop onto points; the headline; the store subtitle words as tabs; optional side phones (iPad/Mac); the
acts, in which UI pieces cut from the app's screenshots fly in and leave; front decor; a credit line.
Only "acts" is required. Every colour and font comes from the scene; the defaults are neutral (slate, white, teal).

scene.json (paths are relative to the scene file; colours are any CSS colour; the notes after # are not JSON):
{
  "lang": "en", "loop": 10,
  "fonts": ["https://fonts.googleapis.com/css2?family=Inter:wght@500;600&display=swap"],
  "theme": {
    "font": "Inter,system-ui,sans-serif",  # body font: word tabs, credit, and the headline unless it sets its own
    "ink": "#ffffff",            # text on the background; use a dark ink on a light background
    "surface": "#ffffff",        # the lit word's pill and the marker heads; must stand out from the background
    "accent": "#14b8a6",         # the lit word's text, marker icons, every third marker head
    "shadow": "#0f172a",         # tints every drop shadow
    "glow": "#ffffff"            # soft light behind the headline and two slow orbiting lights; null = none
  },
  "background": "linear-gradient(180deg,#334155 0%,#1e293b 60%,#0f172a 100%)",
  "headline": {"text": "Your headline here.", "top": 352, "font": "800 74px/84px Inter,sans-serif", "color": "#fff"},
  "words": {"items": ["first", "second", "third"], "top": 448, "font": "600 30px/1 Inter,sans-serif",
            "text": "...", "lit_text": "...", "pill": "..."},          # colours default to ink (82%), accent, surface
  "acts": [ [ {"img": "crops/q.png", "left": 870, "top": 500, "width": 560, "kind": "card|chip"}, ... ], ... ],
  "stagger": 0.12,               # seconds between pieces of one act (default 0.12 for <= 3 acts, else 0.09)
  "decor": [ {"img": "motif.svg", "left": 0, "top": 0, "width": 1920, "opacity": 0.5,
              "motion": "none|drift|float|pulse|spin", "amount": 40, "period": 10, "delay": 0, "front": false} ],
  "skyline": {"seed": 8, "base": 345, "color": "<ink>", "windows": true, "twinkle": "#ffe08a",
              "landmark": "church" | null, "landmark_x": 560},
  "pins": {"count": 12, "icons": ["food", "<path d='M12 2 22 22H2z'/>"], "targets": [[x, y], ...],
           "head": "<surface>", "ink": "<accent>", "accent": "<accent>"},
  "phones": [ {"left": 96, "top": 150, "rotate": 5, "scale": 1, "float": "A|B", "delay": 0, "screen": "shots/a.png"},
              {"left": 1504, "top": 150, "rotate": -5, "strip": ["shots/a.png", "shots/b.png", "shots/c.png"]} ],
  "credit": "Photos: ..."
}
headline, words, decor, skyline, pins, phones and credit can each be left out or set to null.

- acts: with "words", one act per word (the store subtitle). Without words, any number of acts.
  "chip" pieces pop up in place; "card" pieces fly in from their side with a little rotation.
- decor: your own artwork (SVG/PNG): a brand pattern, a motif in the top band, shapes in the side strips. Motion:
  drift = sideways by "amount" px and back; float = up by "amount" px and back; pulse = grow by "amount" % and back;
  spin = one turn per period. "period" must divide the loop. "delay" shifts the phase (s). "front" draws it above the acts.
- skyline: a built-in city motif (frosted tenements with twinkling windows; "landmark": "church" adds an old-town
  church at landmark_x). For any other silhouette, use a decor layer instead.
- pins: markers that drop, squash, bounce, ripple and fade. They land on "targets" (the point the tip touches), or on
  the skyline's rooftops when there are no targets. "icons" are built-in names (landmark, food, scissors, coffee,
  calendar, music, camera, chat) or your own SVG markup for a 24x24 box, drawn as strokes. Points under the status
  bar, the island or a store button on an iPhone are skipped.
- phones: a phone with "strip" swipes to its next screen at each act change (give one screen per act)."""
import json, pathlib, random, struct, sys


def die(msg): sys.exit(f'make_header: {msg}')
def warn(msg): print(f'make_header: warning: {msg}', file=sys.stderr)


scene_path, OUT = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2])
C = json.loads(scene_path.read_text()); BASE_DIR = scene_path.parent
KNOWN = {'lang', 'loop', 'offset_hint', 'fonts', 'theme', 'background', 'headline', 'words', 'acts', 'stagger', 'decor',
         'skyline', 'pins', 'phones', 'credit'}
for key in C:
    if key not in KNOWN and not key.startswith('_'): warn(f'unknown key "{key}" ignored')
LOOP = float(C.get('loop', 10))
if not 6 <= LOOP <= 30: die('loop must be between 6 and 30 s')
TH = {'font': 'system-ui,-apple-system,"Segoe UI",Roboto,sans-serif', 'ink': '#ffffff', 'surface': '#ffffff',
      'accent': '#14b8a6', 'shadow': '#0f172a', 'glow': '#ffffff', **(C.get('theme') or {})}
SH = TH['shadow']


def mix(colour, p):                     # a CSS colour at p % opacity
    return f'color-mix(in srgb,{colour} {p}%,transparent)'


def divides(period, what):
    n = LOOP / period if period > 0 else 0
    if n < 1 or abs(n - round(n)) > 1e-6: die(f'{what}: a period of {period:g} s does not divide the {LOOP:g} s loop')


def uri(rel):
    p = (BASE_DIR / rel).resolve()
    if not p.exists(): die(f'file not found: {rel}')
    return p.as_uri()


def png_aspect(rel):                    # height/width of a PNG from its header (None for other formats)
    with open(BASE_DIR / rel, 'rb') as f: head = f.read(24)
    if head[:8] != b'\x89PNG\r\n\x1a\n': return None
    w, h = struct.unpack('>II', head[16:24]); return h / w


pct = lambda s: f'{100 * s / LOOP:.3f}%'
css, layers = [], {k: '' for k in ('decor', 'sky', 'rip', 'pins', 'phones', 'els', 'front')}
ACTS = C.get('acts') or die('"acts" is required: a list of acts, each a list of UI pieces')
N = len(ACTS); T = LOOP / N
W = C.get('words')
words = list(W['items']) if W else []
if W and len(words) != N: die(f'{len(words)} words but {N} acts: one act per word')
STAGGER = C.get('stagger', 0.12 if N <= 3 else 0.09)

# ---------- UI pieces: one shared keyframe, shifted per element by a negative delay ----------
E1, E2, X0, X1 = 0.42, 0.70, T - 0.62, T - 0.25
css.append(f"""
@keyframes pop{{
 0%{{opacity:0;transform:translate(var(--dx),var(--dy)) rotate(var(--rot)) scale(var(--s0));animation-timing-function:cubic-bezier(.22,.9,.32,1)}}
 {pct(E1)}{{opacity:1;transform:translate(0,-5px) rotate(0deg) scale(1.025);animation-timing-function:ease-in-out}}
 {pct(E2)}{{opacity:1;transform:translate(0,0) rotate(0deg) scale(1)}}
 {pct(X0)}{{opacity:1;transform:translate(0,0) rotate(0deg) scale(1);animation-timing-function:cubic-bezier(.5,0,.75,.4)}}
 {pct(X1)}{{opacity:0;transform:translate(0,-34px) rotate(0deg) scale(.94)}}
 100%{{opacity:0;transform:translate(0,-34px) rotate(0deg) scale(.94)}}}}
@keyframes bob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-4px)}}}}
.el{{position:absolute;opacity:0;animation:pop {LOOP}s linear infinite}}
.el .in{{animation:bob {LOOP / 4:g}s ease-in-out infinite}}
.el img{{display:block;width:100%;height:auto;filter:drop-shadow(0 12px 20px {mix(SH, 30)}) drop-shadow(0 3px 6px {mix(SH, 18)})}}
""")
rnd = random.Random(7)
for a, act in enumerate(ACTS):
    for i, e in enumerate(act):
        start = a * T + i * STAGGER
        aspect = png_aspect(e['img']) if (BASE_DIR / e['img']).exists() else None
        bottom = e['top'] + e['width'] * aspect if aspect else None
        where = f'act {a + 1} piece {i + 1} ({e["img"]})'
        if e['top'] < 345: warn(f'{where} starts at y {e["top"]}: under the status bar or store buttons on an iPhone')
        if e['left'] < 336 or e['left'] + e['width'] > 1584: warn(f'{where} reaches outside x 336-1584: cut off on an iPhone')
        if bottom and bottom > 815: warn(f'{where} ends at y {bottom:.0f}: below the header')
        if e.get('kind') == 'chip':
            dx, dy, rot, s0 = 0, 18, 0, 0.6
        else:
            side = -1 if e['left'] + e['width'] / 2 < 960 else 1
            dx, dy, rot, s0 = side * 70, 46, side * 5, 0.9
        layers['els'] += (f'<div class="el" style="left:{e["left"]}px;top:{e["top"]}px;width:{e["width"]}px;--dx:{dx}px;--dy:{dy}px;--rot:{rot}deg;--s0:{s0};'
                          f'animation-delay:{start - LOOP:.3f}s"><div class="in" style="animation-delay:{-rnd.choice([0, .24, .5, .76]) * LOOP / 4:.2f}s">'
                          f'<img src="{uri(e["img"])}" alt=""></div></div>')

# ---------- words as tabs: the lit word gets a popping pill ----------
words_html = ''
if W:
    txt, lit, pill = W.get('text', mix(TH['ink'], 82)), W.get('lit_text', TH['accent']), W.get('pill', TH['surface'])
    wfont = W.get('font', '600 30px/1 ' + TH['font'])
    css.append(f"""
.words{{position:absolute;left:0;top:{W.get('top', 448)}px;width:1920px;display:flex;justify-content:center;align-items:center;gap:22px;font:{wfont};white-space:nowrap}}
.wd{{position:relative;padding:7px 16px 8px}}
.wd .pl{{position:absolute;inset:0;border-radius:999px;background:{pill};box-shadow:0 6px 16px {mix(SH, 25)};opacity:0;animation:pill {LOOP}s linear infinite}}
.wd .tx{{position:relative;color:{txt};animation:txt {LOOP}s linear infinite}}
@keyframes pill{{0%{{opacity:0;transform:scale(.55);animation-timing-function:cubic-bezier(.2,.9,.3,1.2)}}{pct(0.30)}{{opacity:1;transform:scale(1.07)}}{pct(0.48)}{{opacity:1;transform:scale(1)}}
 {pct(T - 0.25)}{{opacity:1;transform:scale(1)}}{pct(T)}{{opacity:0;transform:scale(.8)}}100%{{opacity:0;transform:scale(.8)}}}}
@keyframes txt{{0%{{color:{txt}}}{pct(0.18)}{{color:{lit}}}{pct(T - 0.2)}{{color:{lit}}}{pct(T)}{{color:{txt}}}100%{{color:{txt}}}}}
""")
    words_html = '<div class="words">' + ''.join(
        f'<span class="wd"><span class="pl" style="animation-delay:{a * T - LOOP:.3f}s"></span><span class="tx" style="animation-delay:{a * T - LOOP:.3f}s">{w}</span></span>'
        for a, w in enumerate(words)) + '</div>'
    if W.get('top', 448) < 345: warn('words start above y 345: under the store buttons on an iPhone')

# ---------- decor: the user's own artwork, CSS motion only ----------
AMOUNT = {'none': 0, 'drift': 40, 'float': 14, 'pulse': 6, 'spin': 0}
if C.get('decor'):
    css.append('.dc{position:absolute}.dc img{display:block;width:100%;height:auto}'
               '@keyframes dk-drift{0%,100%{transform:translateX(0)}50%{transform:translateX(calc(var(--a) * -1px))}}'
               '@keyframes dk-float{0%,100%{transform:translateY(0)}50%{transform:translateY(calc(var(--a) * -1px))}}'
               '@keyframes dk-pulse{0%,100%{transform:scale(1)}50%{transform:scale(calc(1 + var(--a) / 100))}}'
               '@keyframes dk-spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}')
    for i, d in enumerate(C['decor']):
        m = d.get('motion', 'none')
        if m not in AMOUNT: die(f'decor[{i}]: motion "{m}" is not one of {", ".join(AMOUNT)}')
        period = float(d.get('period', LOOP))
        anim = ''
        if m != 'none':
            divides(period, f'decor[{i}]')
            anim = (f'animation:dk-{m} {period:g}s {"linear" if m == "spin" else "ease-in-out"} infinite;'
                    f'animation-delay:{-float(d.get("delay", 0)):.3f}s;')
        width = f'width:{d["width"]}px;' if 'width' in d else ''        # no width: the artwork's own size
        img_w = '' if 'width' in d else ' style="width:auto"'
        layers['front' if d.get('front') else 'decor'] += (
            f'<div class="dc" style="left:{d.get("left", 0)}px;top:{d.get("top", 0)}px;{width}opacity:{d.get("opacity", 1)};'
            f'--a:{d.get("amount", AMOUNT[m])};{anim}"><img src="{uri(d["img"])}"{img_w} alt=""></div>')

# ---------- optional skyline (built-in city motif: frosted tenements with twinkling windows) ----------
tops = []
if C.get('skyline'):
    SK = C['skyline']; BASE = SK.get('base', 345); COL = SK.get('color', TH['ink'])
    if SK.get('landmark') not in (None, 'church'): die('skyline.landmark is "church" or null; use a decor layer for other shapes')
    LX = SK.get('landmark_x', 560) if SK.get('landmark') == 'church' else None
    def hlim(x):
        if 700 <= x <= 1220: return 96          # under the island / buttons band: keep it low
        if 545 <= x <= 1380: return 118
        return 150
    def tenement(r, x, w, h, out, wins, windows):
        top = BASE - h; k = r.random()
        if k < 0.42:
            pk = w * r.uniform(0.38, 0.55); out.append(f'<path d="M{x} {BASE}V{top}L{x + w / 2:.1f} {top - pk:.1f}L{x + w} {top}V{BASE}Z"/>'); peak = top - pk
        elif k < 0.66:
            st, q = 9, w / 6; out.append(f'<path d="M{x} {BASE}V{top}H{x + q:.1f}V{top - st}H{x + 2 * q:.1f}V{top - 2 * st}H{x + 4 * q:.1f}V{top - st}H{x + 5 * q:.1f}V{top}H{x + w}V{BASE}Z"/>'); peak = top - 2 * st
        elif k < 0.84:
            m = min(10, w * 0.18); out.append(f'<path d="M{x} {BASE}V{top}L{x + m:.1f} {top - 14}H{x + w - m:.1f}L{x + w} {top}V{BASE}Z"/>'); peak = top - 14
        else:
            out.append(f'<path d="M{x} {BASE}V{top}H{x + 4}V{top - 6}H{x + w - 4}V{top}H{x + w}V{BASE}Z"/>'); peak = top - 6
        tops.append((x + w / 2, peak))
        if windows:
            cols = 2 if w < 52 else 3; gap = (w - cols * 6) / (cols + 1)
            for c in range(cols):
                for wy in range(int(top) + 14, BASE - 16, 21): wins.append((x + gap + c * (6 + gap), wy))
    def landmark(x, out, wins):             # old-town church: spire tower, nave, domed tower with a cross, hall
        t1, t2 = BASE - 132, BASE - 112
        out += [f'<path d="M{x} {BASE}V{t1}H{x + 4}V{t1 - 8}H{x + 28}V{t1}H{x + 32}V{BASE}Z"/>', f'<path d="M{x + 3} {t1 - 8}L{x + 16} {t1 - 52}L{x + 29} {t1 - 8}Z"/>',
                f'<path d="M{x + 32} {BASE}V{BASE - 78}L{x + 47} {BASE - 92}L{x + 62} {BASE - 78}V{BASE}Z"/>', f'<path d="M{x + 62} {BASE}V{t2}H{x + 92}V{BASE}Z"/>',
                f'<path d="M{x + 64} {t2}C{x + 64} {t2 - 16} {x + 90} {t2 - 16} {x + 90} {t2}Z"/><rect x="{x + 75.5}" y="{t2 - 30}" width="3" height="18"/>',
                f'<path d="M{x + 92} {BASE}V{BASE - 70}H{x + 150}V{BASE}Z"/>']
        tops.extend([(x + 16, t1 - 52), (x + 121, BASE - 70)])
    def build(seed, layer):
        r = random.Random(seed); out, wins = [], []; x = -20; done = False
        while x < 1940:
            if layer == 'near' and LX is not None and not done and x >= LX:
                landmark(x + 4, out, wins); x += 157; done = True; continue
            w = r.randint(40, 66); hm = hlim(x + w / 2) + (24 if layer == 'far' else 0)
            tenement(r, x, w, r.randint(int(hm * 0.55), int(hm)), out, wins, layer == 'near' and r.random() < 0.62)
            x += w + r.choice([0, 0, 0, 3])
        return out, wins
    saved = list(tops); far, _ = build(SK.get('seed', 8) + 13, 'far'); tops[:] = saved
    near, wins = build(SK.get('seed', 8), 'near')
    if not SK.get('windows', True): wins = []
    TW = LOOP / 2; r2 = random.Random(3); ws = []
    for (wx, wy) in wins:
        tw = r2.random() < 0.30; cls = ' class="tw"' if tw else ''
        ws.append(f'<rect{cls} x="{wx:.1f}" y="{wy}" width="6" height="9" rx="1"'
                  + (f' style="animation-delay:-{r2.randrange(8) * TW / 8:.3f}s"' if tw else '') + '/>')
    base_fill = mix(COL, 34)
    css.append(f'.tw{{animation:tw {TW:g}s steps(1,end) infinite}}@keyframes tw{{0%{{fill:{base_fill}}}40%{{fill:{SK.get("twinkle", "#ffe08a")}}}75%{{fill:{base_fill}}}100%{{fill:{base_fill}}}}}')
    layers['sky'] = (f'<svg style="position:absolute;left:0;top:0" width="1920" height="823" viewBox="0 0 1920 823" aria-hidden="true"><defs>'
                     f'<linearGradient id="gN" x1="0" y1="190" x2="0" y2="{BASE + 6}" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{COL}" stop-opacity=".30"/><stop offset="1" stop-color="{COL}" stop-opacity=".07"/></linearGradient>'
                     f'<linearGradient id="gF" x1="0" y1="160" x2="0" y2="{BASE + 6}" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{COL}" stop-opacity=".15"/><stop offset="1" stop-color="{COL}" stop-opacity=".03"/></linearGradient></defs>'
                     f'<g fill="url(#gF)">{"".join(far)}</g><g fill="url(#gN)">{"".join(near)}</g><g style="fill:{base_fill}">{"".join(ws)}</g></svg>')

# ---------- optional markers ("pins") that drop onto targets or rooftops ----------
ICONS = {'landmark': '<path d="M3 22h18M6 18v-7M10 18v-7M14 18v-7M18 18v-7M12 2l8 5H4z"/>',
         'food': '<path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2M7 2v20M21 15V2a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3zm0 0v7"/>',
         'scissors': '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4 8.12 15.88M14.47 14.48 20 20M8.12 8.12 12 12"/>',
         'coffee': '<path d="M10 2v2M14 2v2M6 2v2M16 8a1 1 0 0 1 1 1v8a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1h14a4 4 0 1 1 0 8h-1"/>',
         'calendar': '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
         'music': '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
         'camera': '<path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3z"/><circle cx="12" cy="13" r="3"/>',
         'chat': '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>'}
if C.get('pins'):
    P = C['pins']
    def ok(x, tip):
        if 370 <= x <= 570 or 1135 <= x <= 1555: return False      # behind the store's glass buttons (narrowest iPhone)
        if 336 <= x <= 1584 and tip - 58 < 176: return False        # head would reach the status bar / island
        return -10 < x < 1930
    marks = []
    for name in P.get('icons') or list(ICONS):
        if isinstance(name, str) and name.lstrip().startswith('<'): marks.append(name)
        elif name in ICONS: marks.append(ICONS[name])
        else: die(f'pins.icons: "{name}" is neither a built-in icon ({", ".join(ICONS)}) nor SVG markup starting with "<"')
    pins = []
    if P.get('targets'):
        for t in P['targets'][:P.get('count', len(P['targets']))]:
            if ok(*t): pins.append(tuple(t))
            else: warn(f'pin target {t} skipped: on an iPhone it would sit under the status bar, the island or a store button')
    elif tops:
        cands = [t for t in tops if ok(*t)]; used = set()
        for wx in [150, 300, 600, 700, 830, 1000, 1130, 1600, 1760, 1880, 450, 1400][:P.get('count', 12)]:
            free = [c for c in cands if c not in used]
            if not free: break
            best = min(free, key=lambda c: abs(c[0] - wx)); used.add(best); pins.append(best)
    else:
        die('pins need "targets" ([[x, y], ...]) or a skyline to land on')
    head, ink, acc = P.get('head', TH['surface']), P.get('ink', TH['accent']), P.get('accent', TH['accent'])
    css.append(f"""
.pin{{position:absolute;width:46px;height:58px;margin-left:-23px;margin-top:-58px;transform-origin:50% 100%;opacity:0;animation:drop {LOOP}s linear infinite}}
.pin svg{{display:block;filter:drop-shadow(0 6px 8px {mix(SH, 35)})}}
.rip{{position:absolute;width:70px;height:22px;margin-left:-35px;margin-top:-11px;border-radius:50%;border:2px solid {mix(head, 85)};opacity:0;animation:rip {LOOP}s linear infinite}}
@keyframes drop{{0%{{opacity:0;transform:translateY(-150px) scale(.9);animation-timing-function:cubic-bezier(.55,0,.9,.45)}}{pct(0.15)}{{opacity:1}}{pct(0.45)}{{opacity:1;transform:translateY(0) scale(1,1);animation-timing-function:ease-out}}
 {pct(0.55)}{{transform:translateY(0) scale(1.14,.82);animation-timing-function:ease-out}}{pct(0.72)}{{transform:translateY(-15px) scale(.95,1.06);animation-timing-function:ease-in}}
 {pct(0.88)}{{transform:translateY(0) scale(1)}}{pct(5.2)}{{opacity:1;transform:translateY(0) scale(1)}}{pct(5.6)}{{opacity:0;transform:translateY(-8px) scale(.6)}}100%{{opacity:0;transform:translateY(-8px) scale(.6)}}}}
@keyframes rip{{0%{{opacity:0;transform:scale(.2)}}{pct(0.44)}{{opacity:0;transform:scale(.2)}}{pct(0.46)}{{opacity:.95;transform:scale(.3)}}{pct(1.5)}{{opacity:0;transform:scale(2.1)}}100%{{opacity:0;transform:scale(2.1)}}}}
""")
    for k, (px, tip) in enumerate(pins):
        accent = k % 3 == 1; fill = acc if accent else head; stroke = head if accent else ink
        d = f'{k * (LOOP / len(pins)) - LOOP:.3f}s'
        layers['rip'] += f'<div class="rip" style="left:{px:.0f}px;top:{tip:.0f}px;animation-delay:{d}"></div>'
        layers['pins'] += (f'<div class="pin" style="left:{px:.0f}px;top:{tip + 2:.0f}px;animation-delay:{d}"><svg width="46" height="58" viewBox="0 0 48 60">'
                           f'<path d="M24 58C24 58 4 37 4 22A20 20 0 0 1 44 22C44 37 24 58 24 58Z" style="fill:{fill}"/>'
                           f'<g transform="translate(14 12) scale(.84)" fill="none" style="stroke:{stroke}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">{marks[k % len(marks)]}</g></svg></div>')

# ---------- optional side phones (iPad/Mac decoration) ----------
if C.get('phones'):
    css.append(f"""
.phone{{position:absolute;width:320px;height:672px;border-radius:54px;background:linear-gradient(150deg,#47515d 0%,#1c2128 16%,#0e1217 58%,#262d36 100%);box-shadow:0 40px 80px {mix(SH, 45)},0 12px 26px {mix(SH, 35)},inset 0 0 0 2px #545f6b,inset 0 0 0 4px #0a0d11}}
.scr{{position:absolute;left:10px;top:10px;width:300px;height:652px;border-radius:45px;overflow:hidden;background:#000}}
.scr img{{display:block;width:300px;height:652px}}
.isl{{position:absolute;left:50%;top:18px;width:88px;height:26px;margin-left:-44px;border-radius:13px;background:#000}}
.floatA{{animation:floatA {LOOP / 2:g}s ease-in-out infinite}}.floatB{{animation:floatB {LOOP / 2:g}s ease-in-out infinite}}
@keyframes floatA{{0%{{transform:translateY(0) rotate(0deg)}}50%{{transform:translateY(-22px) rotate(1.6deg)}}100%{{transform:translateY(0) rotate(0deg)}}}}
@keyframes floatB{{0%{{transform:translateY(-18px) rotate(-1.2deg)}}50%{{transform:translateY(8px) rotate(.8deg)}}100%{{transform:translateY(-18px) rotate(-1.2deg)}}}}
.strip{{position:absolute;left:0;top:0;height:652px;display:flex;animation:swipe {LOOP}s infinite}}
.strip img{{flex:0 0 300px}}
""")
    kf = ['0%{transform:translateX(0)}']
    for a in range(1, N + 1):
        kf.append(f'{pct(a * T - 0.53)}{{transform:translateX({-(a - 1) * 300}px);animation-timing-function:cubic-bezier(.6,0,.2,1)}}{pct(a * T)}{{transform:translateX({-a * 300}px)}}')
    css.append('@keyframes swipe{' + ''.join(kf) + '}')
    for ph in C['phones']:
        if 'strip' in ph:
            imgs = [uri(s) for s in ph['strip']]
            if len(imgs) != N: die('a phone "strip" needs one screen per act')
            inner = f'<div class="strip" style="width:{300 * (N + 1)}px">' + ''.join(f'<img src="{s}" alt="">' for s in imgs + imgs[:1]) + '</div>'
        else:
            inner = f'<img src="{uri(ph["screen"])}" alt="">'
        layers['phones'] += (f'<div class="phone float{ph.get("float", "A")}" style="left:{ph["left"]}px;top:{ph["top"]}px;rotate:{ph.get("rotate", 0)}deg;'
                             f'scale:{ph.get("scale", 1)};animation-delay:{ph.get("delay", 0)}s"><div class="scr">{inner}</div><div class="isl"></div></div>')

# ---------- assemble ----------
H = C.get('headline')
head_html = ''
if H:
    if H.get('top', 352) < 345: warn('the headline starts above y 345: it runs into the clock and the store buttons on an iPhone')
    hfont, hcol = H.get('font', '800 74px/84px ' + TH['font']), H.get('color', TH['ink'])
    css.append(f".head{{position:absolute;left:0;top:{H.get('top', 352)}px;width:1920px;text-align:center;font:{hfont};"
               f"color:{hcol};letter-spacing:-.5px;text-shadow:0 4px 22px {mix(SH, 30)}}}")
    head_html = f'<div class="head">{H["text"]}</div>'
glow_html = ''
if TH.get('glow'):
    G = TH['glow']
    css.append(f""".glow{{position:absolute;left:260px;top:120px;width:1400px;height:470px;border-radius:50%;background:radial-gradient(closest-side,{mix(G, 26)},{mix(G, 0)})}}
.blob{{position:absolute;border-radius:50%;background:radial-gradient(circle,{mix(G, 20)} 0%,{mix(G, 0)} 62%)}}
.orbit{{animation:orbit {LOOP}s linear infinite}}.orbitR{{animation:orbitR {LOOP}s linear infinite}}
@keyframes orbit{{from{{transform:rotate(0deg) translateX(150px) rotate(0deg)}}to{{transform:rotate(360deg) translateX(150px) rotate(-360deg)}}}}
@keyframes orbitR{{from{{transform:rotate(360deg) translateX(120px) rotate(-360deg)}}to{{transform:rotate(0deg) translateX(120px) rotate(0deg)}}}}""")
    glow_html = ('<div class="orbit" style="position:absolute;left:180px;top:-460px;width:1000px;height:1000px"><div class="blob" style="left:0;top:0;width:1000px;height:1000px"></div></div>'
                 '<div class="orbitR" style="position:absolute;left:880px;top:260px;width:1100px;height:1100px"><div class="blob" style="left:0;top:0;width:1100px;height:1100px;opacity:.7"></div></div>'
                 '<div class="glow"></div>')
fonts = ''.join(f'<link rel="stylesheet" href="{f}">' for f in C.get('fonts', []))
BG = C.get('background', 'linear-gradient(180deg,#334155 0%,#1e293b 60%,#0f172a 100%)')
page = f"""<!doctype html><html lang="{C.get('lang', 'en')}"><head><meta charset="utf-8"><title>App Store header</title>{fonts}
<style>
html,body{{margin:0;background:#000;overflow:hidden}}
.stage{{position:relative;width:1920px;height:823px;overflow:hidden;font-family:{TH['font']};background:{BG}}}
.credit{{position:absolute;left:0;bottom:9px;width:1920px;text-align:center;font:500 13px/1 {TH['font']};color:{mix(TH['ink'], 78)}}}
{''.join(css)}
</style></head><body><div class="stage">
{glow_html}
{layers['decor']}{layers['sky']}{layers['rip']}{layers['pins']}
{head_html}
{words_html}
{layers['phones']}{layers['els']}{layers['front']}
<div class="credit">{C.get('credit') or ''}</div>
</div></body></html>"""
OUT.write_text(page); print('wrote', OUT, f'{len(page) // 1024} KB', f'{N} acts x {T:.3f} s')
