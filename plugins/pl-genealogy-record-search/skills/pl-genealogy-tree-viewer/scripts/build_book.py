#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Family book (printable HTML + PDF) built from the tree page.

    python3 build_book.py out/tree.html                    # HTML + PDF next to the page
    python3 build_book.py out/tree.html --no-pdf           # HTML only
    python3 build_book.py out/tree.html --with-notes       # research notes too (a working copy)
    uv run --with pillow==11.3.0 python3 build_book.py …   # smaller scan crops in the PDF

Reads `const DB` and `const IMG` from the page build_tree.py wrote. Build the book from the page you
are going to share: after `publish.py --living`, run it on the published page, so the PDF holds only
what that page holds. A chapter per line (DB.lines anchors), pedigree numbering (anchor = 1, the father
of n = 2n, the mother = 2n+1), evidence marks D1…Dn, walls, hypotheses, conflicts; an appendix with every
act (scan crop, transcription, translation, what it proves) and an index of people.

The PDF is printed by Chrome without a window: CHROME=/path/to/chrome, or Google Chrome / Chromium on the
usual paths. The text of the book is Polish, like the viewer.
"""
import argparse, datetime, html, io, json, os, re, shutil, subprocess, sys, unicodedata

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("page", help="the tree page (build_tree.py output, or the published index.html)")
ap.add_argument("--out", help="book HTML (default: Ksiega-rodzinna.html next to the page)")
ap.add_argument("--no-pdf", action="store_true")
ap.add_argument("--with-notes", action="store_true", help="include the research notes")
ap.add_argument("--generations", type=int, default=12)
o = ap.parse_args()
SRC = os.path.abspath(o.page)
HERE = os.path.dirname(SRC)
OUT = os.path.abspath(o.out) if o.out else os.path.join(HERE, "Ksiega-rodzinna.html")
PDF = os.path.splitext(OUT)[0] + ".pdf"
MAX_POKOLEN = o.generations
NOTATKI = o.with_notes


def find_chrome():
    cands = [os.environ.get("CHROME"), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
             "/Applications/Chromium.app/Contents/MacOS/Chromium"]
    cands += [shutil.which(n) for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome")]
    return next((c for c in cands if c and os.path.exists(c)), None)

DB = IMG = None
with io.open(SRC, encoding="utf-8") as fh:
    PAGE = fh.read()
for line in PAGE.split("\n"):
    if line.startswith("const DB = "): DB = json.loads(line[len("const DB = "):].rstrip().rstrip(";"))
    elif line.startswith("const IMG = "): IMG = json.loads(line[len("const IMG = "):].rstrip().rstrip(";"))
if not DB: raise SystemExit("no `const DB` line in " + SRC)
P, F, A, LINES = DB["people"], DB["fams"], DB.get("acts", {}), DB.get("lines", {})
IMG = IMG or {"t": {}, "b": {}}
e = lambda s: html.escape(s or "", quote=True)

def fold(s):
    s = unicodedata.normalize("NFD", (s or "").lower().replace("ł", "l"))
    return "".join(c for c in s if not unicodedata.combining(c))

# one family = one index heading, as in the viewer's List: DB.var variants + -ska next to -ski
VMAP = {fold(v): fold(g[0]) for g in DB.get("var", []) for v in g}
SNSET = {fold(p.get("sn")) for p in P.values() if p.get("sn")}
def snkey(sn):
    k = fold(sn).strip()
    if not k: return "~"
    if k in VMAP: return VMAP[k]
    m = re.match(r"^(.*(?:s|c|dz))ka$", k)
    if m and m.group(1) + "ki" in SNSET: k = m.group(1) + "ki"
    return VMAP.get(k, k)

def life(p):
    a, b = p.get("by", ""), p.get("dy", "")
    if not a and not b: return ""
    return (a or "?") + "–" + (b or ("?" if p.get("dd") or p.get("bu") else ""))

def nm(pid): return P[pid]["n"].replace("❓ ", "")

def par(pid):
    """(father, mother, fid) from the first family with parents — like par() in the viewer."""
    for fid in P[pid]["fc"]:
        f = F.get(fid) or {}
        if f.get("h") or f.get("w"): return f.get("h"), f.get("w"), fid
    return None, None, None

def spouses(pid):
    out = []
    for fid in P[pid]["fs"]:
        f = F.get(fid) or {}
        o = f.get("w") if f.get("h") == pid else f.get("h")
        if o and P.get(o) and P[o]["t"] != "luka": out.append((o, f))
    return out

def plural(sn):
    sn = (sn or "").strip()
    for a, b in (("ska", "scy"), ("cka", "ccy"), ("ski", "scy"), ("cki", "ccy"), ("io", "iowie"), ("ek", "kowie"), ("a", "owie")):
        if sn.endswith(a): return sn[: -len(a)] + b
    return sn + "owie" if sn else "Rodzina"

# ---------------------------------------------------------------- scan crops: smaller copies when Pillow is there
CROP = {aid: a.get("c", "") for aid, a in A.items()}
try:
    from PIL import Image
    small = os.path.join(os.path.dirname(OUT), "book-scans")
    os.makedirs(small, exist_ok=True)
    for aid, c in list(CROP.items()):
        srcf = os.path.join(HERE, c) if c else ""
        if not srcf or not os.path.exists(srcf): continue
        dst = os.path.join(small, aid + "-line.jpg")
        if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(srcf):
            im = Image.open(srcf); im.thumbnail((1200, 1200)); im.convert("RGB").save(dst, quality=72, optimize=True)
        CROP[aid] = os.path.relpath(dst, os.path.dirname(OUT))
except ImportError:
    print("  (no Pillow: scan crops at full size — the PDF will be large)")

# ---------------------------------------------------------------- numbering
DN = {aid: i + 1 for i, aid in enumerate(A)}                 # act -> D1, D2 …
ch_list = [(lab, a, short) for lab, (a, short) in LINES.items() if a and a in P]
chapters, where = [], {}                                     # where[pid] = [(chapter, number)]
for ci, (lab, anchor, short) in enumerate(ch_list, 1):
    num, seen, q = {}, {}, [(1, anchor)]
    while q:
        n, pid = q.pop(0)
        if pid in seen: num[n] = ("=", seen[pid]); continue  # coinciding ancestors: a reference, no repeat
        if n >= 2 ** (MAX_POKOLEN + 1): continue
        seen[pid] = n; num[n] = pid
        f, m, _ = par(pid)
        for k, x in ((2 * n, f), (2 * n + 1, m)):
            if x and P[x]["t"] != "luka": q.append((k, x))
    chapters.append(dict(lab=lab, anchor=anchor, short=short, num=num, seen=seen))
    for pid, n in seen.items(): where.setdefault(pid, []).append((ci, n))

def ref(pid, ci=None, txt=None):
    """Name with a link to the entry (the same chapter first)."""
    w = where.get(pid) or []
    best = next((x for x in w if x[0] == ci), w[0] if w else None)
    lab = e(txt or nm(pid))
    return f'<a href="#r{best[0]}-{best[1]}">{lab}</a> <span class="nr">§{best[1]}{"" if best[0] == ci else " r." + str(best[0])}</span>' if best else lab

def dref(ids): return " ".join(f'<a class="ak" href="#d{DN[a]}">D{DN[a]}</a>' for a in ids if a in DN)

TIER = {"akt": "akt", "praw": "prawdopodobne", "hip": "hipoteza"}
POK = {1: "Rodzice", 2: "Dziadkowie", 3: "Pradziadkowie", 4: "Prapradziadkowie"}

def entry(pid, n, ci):
    p, ev = P[pid], P[pid].get("ev", {})
    h = [f'<section class="os" id="r{ci}-{n}">']
    if IMG["t"].get(pid): h.append(f'<img class="ph" src="{IMG["t"][pid]}" alt="">')
    t = TIER.get(p["t"], "")
    h.append(f'<h4><span class="nr">§{n}</span> {e(nm(pid))} <span class="ly">{e(life(p))}</span>'
             + (f' <span class="t {p["t"]}">{t}</span>' if t else "") + "</h4>")
    fk = []
    if p.get("bd") or p.get("bp"): fk.append("ur. " + e(" · ".join(x for x in (p.get("bd"), p.get("bp")) if x)) + (" " + dref(ev.get("ur", [])) if ev.get("ur") else ""))
    if p.get("dd") or p.get("dp"): fk.append("zm. " + e(" · ".join(x for x in (p.get("dd"), p.get("dp")) if x)) + (" " + dref(ev.get("zm", [])) if ev.get("zm") else ""))
    if p.get("bu"): fk.append("pochowany(-a): " + e(p["bu"]))
    if p.get("oc"): fk.append("zawód: " + e(p["oc"]))
    if p.get("re"): fk.append("mieszkał(a): " + e(p["re"]))
    if fk: h.append('<p class="fk">' + " · ".join(fk) + "</p>")
    f, m, fid = par(pid)
    hp = bool(fid and F[fid].get("hp"))
    real = [x for x in (f, m) if x and P[x]["t"] != "luka"]
    wall = next((x for x in (f, m) if x and P[x]["t"] == "luka"), None)
    if real:
        rd = ev.get("rd", {})
        h.append(f'<p><b>Rodzice{" (hipoteza)" if hp else ""}:</b> ' + " i ".join(ref(x, ci) + (" " + dref(rd[x]) if x in rd else "") for x in real) + "</p>")
    if hp and p.get("hw"): h.append(f'<div class="box hyp"><b>Dlaczego to hipoteza</b> {e(p["hw"])}</div>')
    if wall: h.append(f'<div class="box wall"><b>Rodzice nieznani — ściana.</b> {e(P[wall].get("w", ""))}</div>')
    sp = spouses(pid)
    if sp:
        parts = []
        for o, fam in sp:
            ids = (ev.get("sl", {}).get(o) or ev.get("zw", {}).get(o) or [])
            parts.append(("dziecko z: " if fam.get("um") else "") + ref(o, ci) + (f' — ślub {e(fam["md"])}' if fam.get("md") else "")
                         + (f', {e(fam["mp"])}' if fam.get("mp") else "") + (" " + dref(ids) if ids else ""))
        h.append(f'<p><b>{"Małżonkowie" if len(sp) > 1 else "Małżonek"}:</b> ' + "; ".join(parts) + "</p>")
    kids = [c for fid2 in p["fs"] for c in (F.get(fid2) or {}).get("c", []) if P.get(c) and P[c]["t"] != "luka"]
    if kids:
        dz = ev.get("dz", {})
        h.append("<p><b>Dzieci:</b> " + ", ".join(
            (ref(c, ci) if c in chapters[ci - 1]["seen"] else e(nm(c))) + (f" ({e(life(P[c]))})" if life(P[c]) else "")
            + (" " + dref(dz[c]) if c in dz else "") for c in kids) + "</p>")
    for hy in p.get("hy", []):
        h.append(f'<div class="box hyp"><b>{e(hy["q"])}</b><ul>' + "".join(
            f'<li><span class="st">{e(v["s"])}</span> {e(v["o"])}{(" — " + e(v["u"])) if v.get("u") else ""}</li>' for v in hy["v"])
            + "</ul>" + (f'<div class="r">Rozstrzygnie: {e(hy["r"])}</div>' if hy.get("r") else "") + "</div>")
    for c in p.get("cf", []):
        h.append(f'<div class="box cf"><b>Źródła podają różnie: {e(c["f"])}</b><table>' + "".join(
            f"<tr><td>{e(s)}</td><td>{e(v)}</td></tr>" for s, v in c["v"]) + f'</table><div class="r">{e(c["s"])}</div></div>')
    other = [x for x in where.get(pid, []) if x[0] != ci]
    if other: h.append('<p class="also">Także: ' + ", ".join(f'<a href="#r{a}-{b}">rozdz. {a} §{b}</a>' for a, b in other) + "</p>")
    if NOTATKI and p.get("no"):
        h.append('<div class="notes">' + "".join(f"<p>{e(x)}</p>" for x in p["no"]) + "</div>")
    h.append("</section>")
    return "\n".join(h)

# ---------------------------------------------------------------- assembly
real_people = [p for p in P.values() if p["t"] != "luka"]
ROBOTS = '<meta name="robots" content="noindex,nofollow">' if 'name="robots"' in PAGE[:4000] else ""
today = datetime.date.today()
MIES = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września", "października", "listopada", "grudnia"]
dzis = f"{today.day} {MIES[today.month - 1]} {today.year}"
META = DB.get("meta", {})
rody = META.get("subtitle") or " · ".join(dict.fromkeys(plural(P[a]["sn"]) for _, a, _ in ch_list))
out = [f"""<!doctype html><html lang="pl"><head><meta charset="utf-8">{ROBOTS}<title>Księga rodzinna</title><style>
@page {{ size: A4; margin: 16mm 15mm 18mm 15mm;
  @bottom-center {{ content: counter(page); font: 8.5pt Georgia, serif; color: #888; }} }}
@page :first {{ @bottom-center {{ content: none; }} }}
* {{ box-sizing: border-box; }}
body {{ font-family: "Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif; font-size: 10pt; line-height: 1.45; color: #1a1a1a; margin: 0; }}
a {{ color: inherit; text-decoration: none; border-bottom: 1px dotted #999; }}
.title {{ height: 255mm; display: flex; flex-direction: column; justify-content: center; text-align: center; }}
.title h1 {{ font-size: 34pt; margin: 0 0 6mm; letter-spacing: -.5px; font-weight: 600; }}
.title .rody {{ font-size: 13pt; color: #444; margin-bottom: 14mm; }}
.title .stan {{ font-size: 10pt; color: #777; }}
h2 {{ font-size: 18pt; margin: 0 0 3mm; break-before: page; font-weight: 600; }}
h2 + .lead {{ margin-bottom: 7mm; }}
h3 {{ font-size: 9pt; text-transform: uppercase; letter-spacing: 1.2px; color: #8a7f66; margin: 7mm 0 3mm; border-bottom: 1px solid #d8d0c0; padding-bottom: 1mm; break-after: avoid; }}
.lead {{ color: #444; font-size: 9.6pt; border-left: 3px solid #c8c8c8; padding-left: 4mm; }}
.os {{ break-inside: avoid; margin: 0 0 4.5mm; padding-left: 4mm; border-left: 2.5px solid #d8d0c0; overflow: hidden; }}
.os h4 {{ font-size: 11pt; margin: 0 0 1mm; }}
.os p {{ margin: 0 0 1mm; }}
.nr {{ color: #8a7f66; font-weight: 400; font-size: 8.5pt; }}
.ly {{ color: #555; font-weight: 400; }}
.fk {{ color: #333; }}
.ph {{ float: right; width: 17mm; height: 17mm; object-fit: cover; border-radius: 2mm; margin: 0 0 1mm 3mm; }}
.t {{ font-size: 7.5pt; font-weight: 700; letter-spacing: .6px; text-transform: uppercase; border: 1px solid; border-radius: 9px; padding: 0 2mm; vertical-align: 1px; }}
.t.akt {{ color: #2f7d3a; }} .t.praw {{ color: #a9761d; }} .t.hip {{ color: #3f6ea8; }}
.ak {{ font-size: 8pt; font-weight: 700; color: #2f7d3a; border: 1px solid #2f7d3a; border-radius: 8px; padding: 0 1.4mm; }}
.box {{ font-size: 9pt; border-left: 3px solid #a9761d; background: #faf7f0; padding: 1.5mm 3mm; margin: 1.5mm 0; break-inside: avoid; }}
.box.hyp {{ border-left-color: #3f6ea8; background: #f3f6fa; }}
.box.wall {{ border-left-color: #8a8378; background: #f5f4f1; }}
.box ul {{ margin: 1mm 0; padding-left: 5mm; }}
.box .st {{ font-size: 7.5pt; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; color: #555; }}
.box .r {{ color: #555; font-size: 8.8pt; }}
.box table {{ border-collapse: collapse; width: 100%; margin: 1mm 0; }}
.box td {{ border-top: 1px solid #e3ddd0; padding: .8mm 2mm .8mm 0; vertical-align: top; }}
.box td:last-child {{ font-weight: 700; width: 38%; }}
.also {{ font-size: 8.5pt; color: #666; }}
.notes {{ font-size: 8.3pt; color: #555; white-space: pre-wrap; }}
.doc {{ margin: 0 0 7mm; }}
.doc h4 {{ font-size: 10.5pt; margin: 0 0 1mm; break-after: avoid; }}
.doc img {{ width: 100%; max-height: 70mm; object-fit: contain; object-position: left; border: 1px solid #ddd; margin: 1mm 0; break-before: avoid; break-inside: avoid; }}
.doc .tr, .doc .sg {{ break-inside: avoid; }}
.doc pre {{ font-family: inherit; font-size: 8.8pt; white-space: pre-wrap; background: #f6f5f1; padding: 2mm 3mm; margin: 1mm 0; }}
.doc .sg, .doc .tr {{ font-size: 8.8pt; color: #444; }}
.idx {{ columns: 2; column-gap: 8mm; font-size: 9pt; }}
.idx p {{ margin: 0 0 .6mm; break-inside: avoid; }}
.idx .h {{ font-weight: 700; margin-top: 2.5mm; }}
.legend p {{ margin: 0 0 2mm; }}
</style></head><body>
<div class="title"><h1>Księga rodzinna</h1><div class="rody">{e(rody)}</div>
<div class="stan">{len(real_people)} osób · {len(F)} rodzin · {len(A)} aktów z transkrypcją<br>stan na {dzis}</div></div>
<h2 style="break-before:page">Jak czytać tę księgę</h2>
<div class="legend"><p>Każdy rozdział to przodkowie jednej osoby, pokolenie po pokoleniu. Osoby mają numery: osoba, od której
liczy się rozdział, to §1, jej ojciec §2, matka §3, a ogólnie ojciec osoby §n to §2n, a matka §2n+1. Numer z dopiskiem
„r.” odsyła do innego rozdziału.</p>
<p><span class="t akt">akt</span> <span class="t praw">prawdopodobne</span> <span class="t hip">hipoteza</span> — na czym opiera się
wpis: akt z sygnaturą, mocna poszlaka (indeks, rejestr, przekaz) albo trop do sprawdzenia. Osoba bez tego znaku
pochodzi z drzewa rodzinnego albo z relacji rodziny.</p>
<p><span class="ak">D12</span> przy dacie, rodzicach, małżonku albo dziecku — przepisany akt, który to potwierdza
(aneks „Dokumenty”, z wycinkiem skanu i transkrypcją).</p>
<p>Ramki: <b>ściana</b> — rodzice nieznani i co byłoby następnym krokiem; <b>hipoteza</b> — możliwe odpowiedzi, każda ze
stanem; <b>źródła podają różnie</b> — dwie wersje obok siebie.</p></div>
"""]
for ci, ch in enumerate(chapters, 1):
    nums = sorted(k for k, v in ch["num"].items() if not isinstance(v, tuple))
    akt = sum(1 for k in nums if P[ch["num"][k]]["t"] == "akt")
    walls = sum(1 for k in nums for x in par(ch["num"][k])[:2] if x and P[x]["t"] == "luka")
    deep = max(nums).bit_length() - 1
    out.append(f'<h2 id="r{ci}">{ci}. {e(ch["lab"][0].upper() + ch["lab"][1:])}</h2>'
               f'<p class="lead">{len(nums) - 1} przodków w {deep} pokoleniach wstecz od: {e(nm(ch["anchor"]))}'
               f' · {akt} z aktem · ścian: {walls}</p>')
    g = -1
    for n in nums:
        gn = n.bit_length() - 1
        if gn != g:
            g = gn
            out.append("<h3>" + ("Osoba, od której liczy się rozdział" if g == 0 else POK.get(g, f"{g}. pokolenie wstecz")) + "</h3>")
        out.append(entry(ch["num"][n], n, ci))
    dup = sorted(k for k, v in ch["num"].items() if isinstance(v, tuple))
    if dup: out.append('<p class="also">Zbieg przodków: ' + ", ".join(f"§{k} = §{ch['num'][k][1]}" for k in dup) + "</p>")

out.append('<h2 id="dok">Dokumenty</h2><p class="lead">Akty przepisane w całości, w kolejności jak w drzewie. Przy każdym: wycinek skanu, '
           'transkrypcja oryginału, tłumaczenie, sygnatura i to, co akt potwierdza.</p>')
who = {}
for pid, p in P.items():
    for aid, rola in p.get("sd", []): who.setdefault(aid, []).append((pid, rola))
for aid, a in A.items():
    img = CROP.get(aid, "")
    out.append(f'<div class="doc" id="d{DN[aid]}"><h4><span class="ak">D{DN[aid]}</span> {e(a["t"])}</h4>'
               + (f'<div class="sg">{e(a.get("d", ""))}</div>' if a.get("d") else "")
               + (f'<img src="{e(img)}" alt="">' if img and os.path.exists(os.path.join(os.path.dirname(OUT), img)) else "")
               + f'<pre>{e(a.get("x", ""))}</pre>'
               + (f'<div class="tr"><b>Tłumaczenie.</b> {e(a["p"]).replace(chr(10), "<br>")}</div>' if a.get("p") else "")
               + (f'<div class="tr"><b>Potwierdza:</b> {e("; ".join(a["w"]))}</div>' if a.get("w") else "")
               + (f'<div class="tr"><b>Osoby:</b> ' + ", ".join(ref(pid) + f" ({e(r)})" for pid, r in who.get(aid, [])) + "</div>" if who.get(aid) else "")
               + f'<div class="sg">{e(a.get("s", ""))}{(" · " + e(a["z"])) if a.get("z") else ""}</div></div>')

out.append('<h2 id="idx">Indeks osób</h2><div class="idx">')
groups = {}
for pid in where:
    groups.setdefault(snkey(P[pid].get("sn")), []).append(pid)
for k in sorted(groups):
    sp = list(dict.fromkeys(P[x].get("sn") for x in sorted(groups[k], key=lambda x: fold(P[x].get("sn") or "")) if P[x].get("sn")))
    out.append(f'<p class="h">{e(" · ".join(sp) or "(bez nazwiska)")}</p>')
    for pid in sorted(groups[k], key=lambda x: (P[x].get("by") or "9999", fold(P[x]["n"]))):
        out.append(f"<p>{e(nm(pid))} {e(life(P[pid]))} — " + ", ".join(f'<a href="#r{a}-{b}">{a}/§{b}</a>' for a, b in where[pid]) + "</p>")
out.append("</div></body></html>")
with io.open(OUT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))
print("written", OUT, "— chapters: %d, people with an entry: %d, acts: %d" % (len(chapters), len(where), len(A)))

if not o.no_pdf:
    chrome = find_chrome()
    if not chrome: raise SystemExit("no Chrome or Chromium found: set CHROME=/path/to/chrome, or use --no-pdf and print the HTML")
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
                    "--print-to-pdf=" + PDF, "file://" + OUT], check=True, capture_output=True, timeout=300)
    print("written", PDF, "(%.1f MB)" % (os.path.getsize(PDF) / 1048576))
