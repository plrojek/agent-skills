"""Generate an animated App Store product-page HEADER as a static HTML page (1920x823 CSS px, rendered at 2x =
3840x1646, the 21:9 header size). Every animation period divides the loop, so frame N flows into frame 0.

usage: make_header.py <scene.json> <out.html>

The layout follows the iPhone window measured on a device (references/iphone-window.md):
  - the iPhone shows the FULL height and only x 336-1584 of the 1920-wide artboard;
  - y < 171 is the status bar + Dynamic Island, y 186-327 holds the store's back button (left) and mute/share
    capsule (right). Nothing readable and no distinct object above y 345 inside the window;
  - put headline, words and the animated UI cards in x 430-1490, y 345-790. x < 430 and x > 1490 are iPad/Mac only.

scene.json (paths are relative to the scene file):
{
  "lang": "en", "loop": 10, "offset_hint": 1.0,
  "fonts": ["https://fonts.googleapis.com/css2?family=Inter:wght@500;600&family=Outfit:wght@800&display=swap"],
  "background": "linear-gradient(180deg,#0a6fc2 0%,#29aef2 41%,#0866b4 100%)",
  "headline": {"text": "Your headline here.", "top": 352, "font": "800 74px/84px Outfit,sans-serif", "color": "#fff"},
  "words": {"items": ["first", "second", "third"], "top": 448, "font": "600 30px/1 Inter,sans-serif",
            "text": "rgba(255,255,255,.82)", "lit_text": "#0369a1", "pill": "#fff"},
  "acts": [ [ {"img": "crops/q.png", "left": 870, "top": 500, "width": 560, "kind": "chip|card"}, ... ], ... ],
  "skyline": {"seed": 8, "base": 345, "landmark_x": 560} | null,
  "pins": {"count": 12, "accent": "#f97316", "ink": "#0284c7"} | null,
  "phones": [ {"left": 96, "top": 150, "rotate": 5, "scale": 1, "float": "A", "screen": "shots/a.png"},
              {"left": 1504, "top": 150, "rotate": -5, "float": "A", "strip": ["shots/a.png", "shots/b.png", "shots/c.png"]} ],
  "credit": "Photos: …"
}
One act per word. A phone with "strip" swipes to its next screen at each act change (give one screen per act)."""
import json, pathlib, random, sys

scene_path, OUT = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2])
C = json.loads(scene_path.read_text()); BASE_DIR = scene_path.parent
LOOP = float(C.get('loop', 10))
def uri(rel):
    p = (BASE_DIR / rel).resolve(); assert p.exists(), p; return p.as_uri()
pct = lambda s: f'{100 * s / LOOP:.3f}%'
css, layers = [], {'sky': '', 'rip': '', 'pins': '', 'phones': '', 'els': ''}
ACTS = C['acts']; N = len(ACTS); T = LOOP / N
words = C['words']['items']; assert len(words) == N, 'one act per word'
STAGGER = C.get('stagger', 0.12 if N <= 3 else 0.09)

# ---------- UI cards: one shared keyframe, shifted per element by a negative delay ----------
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
.el .in{{animation:bob 2.5s ease-in-out infinite}}
.el img{{display:block;width:100%;height:auto;filter:drop-shadow(0 12px 20px rgba(2,40,90,.30)) drop-shadow(0 3px 6px rgba(2,40,90,.18))}}
""")
rnd = random.Random(7)
for a, act in enumerate(ACTS):
    for i, e in enumerate(act):
        start = a * T + i * STAGGER
        if e.get('kind') == 'chip':
            dx, dy, rot, s0 = 0, 18, 0, 0.6
        else:
            side = -1 if e['left'] + e['width'] / 2 < 960 else 1
            dx, dy, rot, s0 = side * 70, 46, side * 5, 0.9
        layers['els'] += (f'<div class="el" style="left:{e["left"]}px;top:{e["top"]}px;width:{e["width"]}px;--dx:{dx}px;--dy:{dy}px;--rot:{rot}deg;--s0:{s0};'
                          f'animation-delay:{start - LOOP:.3f}s"><div class="in" style="animation-delay:{-rnd.choice([0, .6, 1.25, 1.9]):.2f}s">'
                          f'<img src="{uri(e["img"])}" alt=""></div></div>')

# ---------- words as tabs: the lit word gets a popping pill ----------
W = C['words']
css.append(f"""
.words{{position:absolute;left:0;top:{W.get('top', 448)}px;width:1920px;display:flex;justify-content:center;align-items:center;gap:22px;font:{W.get('font', '600 30px/1 Inter,system-ui,sans-serif')};white-space:nowrap}}
.wd{{position:relative;padding:7px 16px 8px}}
.wd .pl{{position:absolute;inset:0;border-radius:999px;background:{W.get('pill', '#fff')};box-shadow:0 6px 16px rgba(2,40,90,.25);opacity:0;animation:pill {LOOP}s linear infinite}}
.wd .tx{{position:relative;color:{W.get('text', 'rgba(255,255,255,.82)')};animation:txt {LOOP}s linear infinite}}
@keyframes pill{{0%{{opacity:0;transform:scale(.55);animation-timing-function:cubic-bezier(.2,.9,.3,1.2)}}{pct(0.30)}{{opacity:1;transform:scale(1.07)}}{pct(0.48)}{{opacity:1;transform:scale(1)}}
 {pct(T - 0.25)}{{opacity:1;transform:scale(1)}}{pct(T)}{{opacity:0;transform:scale(.8)}}100%{{opacity:0;transform:scale(.8)}}}}
@keyframes txt{{0%{{color:{W.get('text', 'rgba(255,255,255,.82)')}}}{pct(0.18)}{{color:{W.get('lit_text', '#0369a1')}}}{pct(T - 0.2)}{{color:{W.get('lit_text', '#0369a1')}}}{pct(T)}{{color:{W.get('text', 'rgba(255,255,255,.82)')}}}100%{{color:{W.get('text', 'rgba(255,255,255,.82)')}}}}}
""")
words_html = '<div class="words">' + ''.join(
    f'<span class="wd"><span class="pl" style="animation-delay:{a * T - LOOP:.3f}s"></span><span class="tx" style="animation-delay:{a * T - LOOP:.3f}s">{w}</span></span>'
    for a, w in enumerate(words)) + '</div>'

# ---------- optional skyline (frosted old-town silhouette with twinkling windows) ----------
tops = []
if C.get('skyline'):
    SK = C['skyline']; BASE = SK.get('base', 345); LX = SK.get('landmark_x', 560)
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
    def landmark(x, out, wins):
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
    r2 = random.Random(3); ws = []
    for (wx, wy) in wins:
        tw = r2.random() < 0.30; cls = ' class="tw"' if tw else ''
        ws.append(f'<rect{cls} x="{wx:.1f}" y="{wy}" width="6" height="9" rx="1"'
                  + (f' style="animation-delay:-{r2.choice([0, .625, 1.25, 1.875, 2.5, 3.125, 3.75, 4.375]):.3f}s"' if tw else '') + '/>')
    css.append('.tw{animation:tw 5s steps(1,end) infinite}@keyframes tw{0%{fill:rgba(255,255,255,.34)}40%{fill:#ffe08a}75%{fill:rgba(255,255,255,.34)}100%{fill:rgba(255,255,255,.34)}}')
    layers['sky'] = (f'<svg style="position:absolute;left:0;top:0" width="1920" height="823" viewBox="0 0 1920 823" aria-hidden="true"><defs>'
                     f'<linearGradient id="gN" x1="0" y1="190" x2="0" y2="{BASE + 6}" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#fff" stop-opacity=".30"/><stop offset="1" stop-color="#fff" stop-opacity=".07"/></linearGradient>'
                     f'<linearGradient id="gF" x1="0" y1="160" x2="0" y2="{BASE + 6}" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#fff" stop-opacity=".15"/><stop offset="1" stop-color="#fff" stop-opacity=".03"/></linearGradient></defs>'
                     f'<g fill="url(#gF)">{"".join(far)}</g><g fill="url(#gN)">{"".join(near)}</g><g fill="rgba(255,255,255,.34)">{"".join(ws)}</g></svg>')

# ---------- optional pins dropping onto rooftops (needs the skyline) ----------
ICONS = {'landmark': '<path d="M3 22h18M6 18v-7M10 18v-7M14 18v-7M18 18v-7M12 2l8 5H4z"/>',
         'food': '<path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2M7 2v20M21 15V2a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3zm0 0v7"/>',
         'scissors': '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4 8.12 15.88M14.47 14.48 20 20M8.12 8.12 12 12"/>',
         'coffee': '<path d="M10 2v2M14 2v2M6 2v2M16 8a1 1 0 0 1 1 1v8a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1h14a4 4 0 1 1 0 8h-1"/>',
         'calendar': '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
         'music': '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
         'camera': '<path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3z"/><circle cx="12" cy="13" r="3"/>',
         'chat': '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>'}
if C.get('pins') and tops:
    P = C['pins']
    def ok(x, roof):
        if 370 <= x <= 570 or 1135 <= x <= 1555: return False      # behind the store's glass buttons (narrowest iPhone)
        if 336 <= x <= 1584 and roof - 58 < 176: return False       # head would reach the status bar / island
        return -10 < x < 1930
    cands = [t for t in tops if ok(*t)]; used, pins = set(), []
    for wx in [150, 300, 600, 700, 830, 1000, 1130, 1600, 1760, 1880, 450, 1400][:P.get('count', 12)]:
        free = [c for c in cands if c not in used]
        if not free: break
        best = min(free, key=lambda c: abs(c[0] - wx)); used.add(best); pins.append(best)
    kinds = P.get('icons', list(ICONS))
    css.append(f"""
.pin{{position:absolute;width:46px;height:58px;margin-left:-23px;margin-top:-58px;transform-origin:50% 100%;opacity:0;animation:drop {LOOP}s linear infinite}}
.pin svg{{display:block;filter:drop-shadow(0 6px 8px rgba(2,40,90,.35))}}
.rip{{position:absolute;width:70px;height:22px;margin-left:-35px;margin-top:-11px;border-radius:50%;border:2px solid rgba(255,255,255,.85);opacity:0;animation:rip {LOOP}s linear infinite}}
@keyframes drop{{0%{{opacity:0;transform:translateY(-150px) scale(.9);animation-timing-function:cubic-bezier(.55,0,.9,.45)}}{pct(0.15)}{{opacity:1}}{pct(0.45)}{{opacity:1;transform:translateY(0) scale(1,1);animation-timing-function:ease-out}}
 {pct(0.55)}{{transform:translateY(0) scale(1.14,.82);animation-timing-function:ease-out}}{pct(0.72)}{{transform:translateY(-15px) scale(.95,1.06);animation-timing-function:ease-in}}
 {pct(0.88)}{{transform:translateY(0) scale(1)}}{pct(5.2)}{{opacity:1;transform:translateY(0) scale(1)}}{pct(5.6)}{{opacity:0;transform:translateY(-8px) scale(.6)}}100%{{opacity:0;transform:translateY(-8px) scale(.6)}}}}
@keyframes rip{{0%{{opacity:0;transform:scale(.2)}}{pct(0.44)}{{opacity:0;transform:scale(.2)}}{pct(0.46)}{{opacity:.95;transform:scale(.3)}}{pct(1.5)}{{opacity:0;transform:scale(2.1)}}100%{{opacity:0;transform:scale(2.1)}}}}
""")
    for k, (px, roof) in enumerate(pins):
        accent = k % 3 == 1; head = P.get('accent', '#f97316') if accent else '#ffffff'; ink = '#ffffff' if accent else P.get('ink', '#0284c7')
        d = f'{k * (LOOP / len(pins)) - LOOP:.3f}s'
        layers['rip'] += f'<div class="rip" style="left:{px:.0f}px;top:{roof:.0f}px;animation-delay:{d}"></div>'
        layers['pins'] += (f'<div class="pin" style="left:{px:.0f}px;top:{roof + 2:.0f}px;animation-delay:{d}"><svg width="46" height="58" viewBox="0 0 48 60">'
                           f'<path d="M24 58C24 58 4 37 4 22A20 20 0 0 1 44 22C44 37 24 58 24 58Z" fill="{head}"/>'
                           f'<g transform="translate(14 12) scale(.84)" fill="none" stroke="{ink}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">{ICONS[kinds[k % len(kinds)]]}</g></svg></div>')

# ---------- optional side phones (iPad/Mac decoration) ----------
if C.get('phones'):
    css.append(f"""
.phone{{position:absolute;width:320px;height:672px;border-radius:54px;background:linear-gradient(150deg,#47515d 0%,#1c2128 16%,#0e1217 58%,#262d36 100%);box-shadow:0 40px 80px rgba(1,30,60,.45),0 12px 26px rgba(1,30,60,.35),inset 0 0 0 2px #545f6b,inset 0 0 0 4px #0a0d11}}
.scr{{position:absolute;left:10px;top:10px;width:300px;height:652px;border-radius:45px;overflow:hidden;background:#000}}
.scr img{{display:block;width:300px;height:652px}}
.isl{{position:absolute;left:50%;top:18px;width:88px;height:26px;margin-left:-44px;border-radius:13px;background:#000}}
.floatA{{animation:floatA 5s ease-in-out infinite}}.floatB{{animation:floatB 5s ease-in-out infinite}}
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
            imgs = [uri(s) for s in ph['strip']]; assert len(imgs) == N, 'a strip needs one screen per act'
            inner = f'<div class="strip" style="width:{300 * (N + 1)}px">' + ''.join(f'<img src="{s}" alt="">' for s in imgs + imgs[:1]) + '</div>'
        else:
            inner = f'<img src="{uri(ph["screen"])}" alt="">'
        layers['phones'] += (f'<div class="phone float{ph.get("float", "A")}" style="left:{ph["left"]}px;top:{ph["top"]}px;rotate:{ph.get("rotate", 0)}deg;'
                             f'scale:{ph.get("scale", 1)};animation-delay:{ph.get("delay", 0)}s"><div class="scr">{inner}</div><div class="isl"></div></div>')

# ---------- assemble ----------
H = C['headline']
fonts = ''.join(f'<link rel="stylesheet" href="{f}">' for f in C.get('fonts', []))
page = f"""<!doctype html><html lang="{C.get('lang', 'en')}"><head><meta charset="utf-8"><title>App Store header</title>{fonts}
<style>
html,body{{margin:0;background:#000;overflow:hidden}}
.stage{{position:relative;width:1920px;height:823px;overflow:hidden;font-family:Inter,system-ui,sans-serif;background:{C.get('background', 'linear-gradient(180deg,#0a6fc2,#29aef2 41%,#0866b4)')}}}
.glow{{position:absolute;left:260px;top:120px;width:1400px;height:470px;border-radius:50%;background:radial-gradient(closest-side,rgba(255,255,255,.26),rgba(255,255,255,0))}}
.blob{{position:absolute;border-radius:50%;background:radial-gradient(circle,rgba(255,255,255,.20) 0%,rgba(255,255,255,0) 62%)}}
.orbit{{animation:orbit {LOOP}s linear infinite}}.orbitR{{animation:orbitR {LOOP}s linear infinite}}
@keyframes orbit{{from{{transform:rotate(0deg) translateX(150px) rotate(0deg)}}to{{transform:rotate(360deg) translateX(150px) rotate(-360deg)}}}}
@keyframes orbitR{{from{{transform:rotate(360deg) translateX(120px) rotate(-360deg)}}to{{transform:rotate(0deg) translateX(120px) rotate(0deg)}}}}
.head{{position:absolute;left:0;top:{H.get('top', 352)}px;width:1920px;text-align:center;font:{H.get('font', '800 74px/84px system-ui,sans-serif')};color:{H.get('color', '#fff')};letter-spacing:-.5px;text-shadow:0 4px 22px rgba(2,50,110,.30)}}
.credit{{position:absolute;left:0;bottom:9px;width:1920px;text-align:center;font:500 13px/1 Inter,sans-serif;color:rgba(255,255,255,.78)}}
{''.join(css)}
</style></head><body><div class="stage">
<div class="orbit" style="position:absolute;left:180px;top:-460px;width:1000px;height:1000px"><div class="blob" style="left:0;top:0;width:1000px;height:1000px"></div></div>
<div class="orbitR" style="position:absolute;left:880px;top:260px;width:1100px;height:1100px"><div class="blob" style="left:0;top:0;width:1100px;height:1100px;opacity:.7"></div></div>
<div class="glow"></div>
{layers['sky']}{layers['rip']}{layers['pins']}
<div class="head">{H['text']}</div>
{words_html}
{layers['phones']}{layers['els']}
<div class="credit">{C.get('credit', '')}</div>
</div></body></html>"""
OUT.write_text(page); print('wrote', OUT, f'{len(page) // 1024} KB', f'{N} acts x {T:.3f} s')
