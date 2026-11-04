#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Family book (printable HTML + PDF) built from the tree page.

    python3 build_book.py publication/index.html               # every line, HTML + PDF next to the page
    python3 build_book.py publication/index.html --no-pdf      # HTML only
    python3 build_book.py publication/index.html --with-notes  # research notes too (a working copy)

One family's book, for its readers, with a fan of all their known ancestors at the front:

    python3 build_book.py publication/index.html --lines "Andrzeja Jaworskiego,Teresy Kos" \\
        --title "Księga rodzinna Tomasza" --out publication/Ksiega-rodzinna-Tomasz.html \\
        --reader "Jaworskiego,Kos=Tomasza" --fan "Tomasz"

The print edition of the same book (margins for binding, page numbers instead of links):

    uv run --with pillow==11.3.0 --with pypdf==6.20.1 python3 build_book.py … --print

Reads `const DB` and `const IMG` from the page build_tree.py wrote. Build the book from the page you
are going to share: after `publish.py --living`, run it on the published page, so the PDF holds only
what that page holds. A chapter per line (DB.lines anchors) with the fan of its ancestors, pedigree
numbering (anchor = 1, the father of n = 2n, the mother = 2n+1), evidence marks D1…Dn, walls,
hypotheses, conflicts; an appendix with every act (scan crop, transcription, translation, what it
proves) and an index of people.

--lines FRAGMENTS   only the lines whose label contains one of the comma-separated fragments; the
                    appendix keeps the acts that name someone in them, the index their people.
--reader F,…=GEN    chapters of the lines matching F are read by a child of their anchor (normally the
                    anchors are the parents of the people the book is for): the generation headers say
                    what each generation is to that reader. GEN is the genitive: "Tomasza", "Tomasza i Ewy".
                    Repeat it for a couple's book (his lines for him, hers for her).
--fan [WHO=]LABEL   a fan of ALL known ancestors at the front of the book. WHO is an xref or
                    "Given Surname|year"; left out, it is the nearest person descending from every
                    chapter's anchor (a child of the couple). LABEL goes in the centre. Repeatable.
--print             the print edition: <name>-druk.html/.pdf, inner margin for binding, page numbers in
                    the contents, the index and every cross-reference (2-3 passes through Chrome; needs
                    pypdf), the front fans on landscape pages.

The PDF is printed by Chrome without a window: CHROME=/path/to/chrome, or Google Chrome / Chromium on the
usual paths. The text of the book is Polish, like the viewer.
"""
import argparse, datetime, html, io, json, math, os, re, shutil, subprocess, sys, unicodedata

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("page", help="the tree page (build_tree.py output, or the published index.html)")
ap.add_argument("--out", help="book HTML (default: Ksiega-rodzinna.html next to the page)")
ap.add_argument("--no-pdf", action="store_true")
ap.add_argument("--with-notes", action="store_true", help="include the research notes")
ap.add_argument("--generations", type=int, default=12)
ap.add_argument("--title", default="Księga rodzinna")
ap.add_argument("--lines", default="", help="comma-separated fragments of line labels: only those chapters")
ap.add_argument("--reader", action="append", default=[], metavar="FRAGMENTS=GENITIVE")
ap.add_argument("--fan", action="append", default=[], metavar="[WHO=]LABEL")
ap.add_argument("--print", dest="print_edition", action="store_true", help="print edition with page numbers")
ap.add_argument("--pages", help="JSON {id: page} from an earlier print run (--print finds them itself)")
o = ap.parse_args()
SRC = os.path.abspath(o.page)
HERE = os.path.dirname(SRC)
OUT = os.path.abspath(o.out) if o.out else os.path.join(HERE, "Ksiega-rodzinna.html")
PRINT = o.print_edition
if PRINT:
    stem, ext = os.path.splitext(OUT)
    if not stem.endswith("-druk"): OUT = stem + "-druk" + (ext or ".html")
PDF = os.path.splitext(OUT)[0] + ".pdf"
OUTDIR = os.path.dirname(OUT)
MAX_POKOLEN = o.generations
NOTATKI = o.with_notes
PG = {}                                                     # element id -> page number (print edition)
if o.pages:
    with io.open(o.pages, encoding="utf-8") as fh: PG.update(json.load(fh))
if PRINT and not o.no_pdf:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise SystemExit("--print reads the page numbers back with pypdf: "
                         "uv run --with pillow==11.3.0 --with pypdf==6.20.1 python3 build_book.py … --print")


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

def pl(n, one, few, many):
    """Polish plural: 1 pokolenie, 2-4 pokolenia, 5 pokoleń (12-14 pokoleń)."""
    if n == 1: return one
    return few if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else many

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
    old = a[:4].isdigit() and int(a[:4]) < datetime.date.today().year - 100      # long dead, date unknown
    return (a or "?") + "–" + (b or ("?" if p.get("dd") or p.get("bu") or old else ""))

def nm(pid): return P[pid]["n"].replace("❓ ", "")

def par(pid):
    """(father, mother, fid) from the first family with parents — like par() in the viewer."""
    for fid in P[pid]["fc"]:
        f = F.get(fid) or {}
        if f.get("h") or f.get("w"): return f.get("h"), f.get("w"), fid
    return None, None, None

def known_parents(pid):
    f, m, fid = par(pid)
    return [x for x in (f, m) if x and P[x]["t"] != "luka"], bool(fid and F[fid].get("hp"))

def spouses(pid):
    out = []
    for fid in P[pid]["fs"]:
        f = F.get(fid) or {}
        o_ = f.get("w") if f.get("h") == pid else f.get("h")
        if o_ and P.get(o_) and P[o_]["t"] != "luka": out.append((o_, f))
    return out

def plural(sn):
    sn = (sn or "").strip()
    for a, b in (("ska", "scy"), ("cka", "ccy"), ("ski", "scy"), ("cki", "ccy"), ("io", "iowie"), ("ek", "kowie"), ("a", "owie")):
        if sn.endswith(a): return sn[: -len(a)] + b
    return sn + "owie" if sn else "Rodzina"

def place(x):
    """Place names exported by tree sites carry litter: "---, ", a postcode, "X / X Voivodeship, Poland"."""
    x = re.sub(r"^(-+\s*,\s*)+", "", x or "")
    x = re.sub(r"^\d{2}-\d{3},\s*", "", x)
    x = re.sub(r"\b([\wąćęłńóśźżĄĆĘŁŃÓŚŹŻ ]+) / \1 Voivodeship, Poland", r"\1", x)
    x = re.sub(r",\s*Poland$", "", x)
    return x.strip(" ,")

def by_sex(pid, m, f, u):
    return {"M": m, "F": f}.get(P[pid].get("s"), u)

def find_person(key, what):
    """An xref, "Given Surname|year" or "Given Surname" -> one xref; nothing or several -> refuse."""
    if key in P: return key
    name, _, year = key.partition("|")
    hits = [pid for pid, p in P.items() if p["t"] != "luka" and nm(pid) == name.strip() and (not year or p.get("by") == year.strip())]
    if len(hits) != 1:
        raise SystemExit(f"{what} {key!r}: {len(hits)} people match" + (": " + "; ".join(f"{h} {nm(h)} {life(P[h])}" for h in hits[:8]) if hits else
                         " (on a page published with --living, use the xref: names and years of the living are gone)"))
    return hits[0]

# ---------------------------------------------------------------- scan crops: smaller copies when Pillow is there
CROP = {}
for aid, a in A.items():
    c = a.get("c", "")
    CROP[aid] = os.path.relpath(os.path.join(HERE, c), OUTDIR) if c and os.path.exists(os.path.join(HERE, c)) else ""
try:
    from PIL import Image
    small = os.path.join(OUTDIR, "book-scans")
    os.makedirs(small, exist_ok=True)
    for aid, a in A.items():
        srcf = os.path.join(HERE, a.get("c", "")) if a.get("c") else ""
        if not srcf or not os.path.exists(srcf): continue
        dst = os.path.join(small, aid + "-line.jpg")
        if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(srcf):
            im = Image.open(srcf); im.thumbnail((1200, 1200)); im.convert("RGB").save(dst, quality=72, optimize=True)
        CROP[aid] = os.path.relpath(dst, OUTDIR)
except ImportError:
    print("  (no Pillow: scan crops at full size — the PDF will be large)")

# ---------------------------------------------------------------- chapters and numbering
ch_list = [(lab, a, short) for lab, (a, short) in LINES.items() if a and a in P]
FRAGS = [x.strip() for x in o.lines.split(",") if x.strip()]
if FRAGS:
    for g in FRAGS:
        if not any(g.lower() in c[0].lower() for c in ch_list):
            raise SystemExit(f"--lines: no line label contains {g!r}; the lines are: " + "; ".join(LINES))
    ch_list = [c for c in ch_list if any(g.lower() in c[0].lower() for g in FRAGS)]
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

WHO_IN = {}                                                  # act -> [(person, role)]
for pid, p in P.items():
    for aid, rola in p.get("sd", []): WHO_IN.setdefault(aid, []).append((pid, rola))
if FRAGS:                                                    # one family's book: only the acts naming its people
    A = {aid: a for aid, a in A.items() if {x for x, _ in WHO_IN.get(aid, [])} & set(where)}
DN = {aid: i + 1 for i, aid in enumerate(A)}                 # act -> D1, D2 …

READER = {}                                                  # chapter -> genitive of its reader
for spec in o.reader:
    frags, sep, gen = spec.rpartition("=")
    if not sep or not gen.strip(): raise SystemExit(f"--reader {spec!r}: expected FRAGMENTS=GENITIVE, e.g. \"Jaworskiego,Kos=Tomasza\"")
    for g in [x.strip() for x in frags.split(",") if x.strip()]:
        hit = [ci for ci, ch in enumerate(chapters, 1) if g.lower() in ch["lab"].lower()]
        if not hit: raise SystemExit(f"--reader: no chapter's label contains {g!r}; the chapters are: " + "; ".join(c["lab"] for c in chapters))
        for ci in hit: READER[ci] = gen.strip()

def sn_(i):
    """", s. 12" — the page of the element with that id (print edition, once the pages are known)."""
    return f", s. {PG[i]}" if PRINT and i in PG else ""

def ref(pid, ci=None, txt=None):
    """Name with a link to the entry (the same chapter first)."""
    w = where.get(pid) or []
    best = next((x for x in w if x[0] == ci), w[0] if w else None)
    lab = e(txt or nm(pid))
    if not best: return lab
    other = "" if best[0] == ci else " r." + str(best[0]) + sn_(f"r{best[0]}-{best[1]}")
    return f'<a href="#r{best[0]}-{best[1]}">{lab}</a> <span class="nr">§{best[1]}{other}</span>'

def dref(ids):
    """Act marks, at most three; the rest as +N (all of them are in the act's own list of people)."""
    ids = [a for a in dict.fromkeys(ids) if a in DN]
    more = len(ids) - 3
    return " ".join(f'<a class="ak" href="#d{DN[a]}">D{DN[a]}</a>' for a in ids[:3]) + (f' <span class="akm">+{more}</span>' if more > 0 else "")

TIER = {"akt": "akt", "praw": "prawdopodobne", "hip": "hipoteza"}
POK = {1: "Rodzice", 2: "Dziadkowie", 3: "Pradziadkowie", 4: "Prapradziadkowie"}
REL = {1: "rodzice", 2: "dziadkowie", 3: "pradziadkowie", 4: "prapradziadkowie", 5: "praprapradziadkowie"}

def anchor_to_reader(ci):
    who = READER.get(ci)
    return f"{by_sex(chapters[ci - 1]['anchor'], 'ojciec', 'matka', 'rodzic')} {who}" if who else ""

def gen_header(g, ci):
    base = "Osoba, od której liczy się rozdział" if g == 0 else POK.get(g, f"{g}. pokolenie wstecz")
    if ci not in READER: return base
    if g == 0: return base + " — " + anchor_to_reader(ci)
    return base + f" · dla {READER[ci]}: " + REL.get(g + 1, f"{g + 1}. pokolenie wstecz")

def no_given_name(pid):
    n = nm(pid).strip()
    return n == "(bez imienia)" or n == (P[pid].get("sn") or "").strip()

def entry(pid, n, ci):
    p, ev = P[pid], P[pid].get("ev", {})
    h = [f'<section class="os" id="r{ci}-{n}">']
    if IMG["t"].get(pid): h.append(f'<img class="ph" src="{IMG["t"][pid]}" alt="">')
    t = TIER.get(p["t"], "")
    h.append(f'<h4><span class="nr">§{n}</span> {e(nm(pid))} <span class="ly">{e(life(p))}</span>'
             + (f' <span class="t {p["t"]}">{t}</span>' if t else "") + "</h4>")
    fk = []
    if p.get("bd") or p.get("bp"): fk.append("ur. " + e(" · ".join(x for x in (p.get("bd"), place(p.get("bp"))) if x)) + (" " + dref(ev.get("ur", [])) if ev.get("ur") else ""))
    if p.get("dd") or p.get("dp"): fk.append("zm. " + e(" · ".join(x for x in (p.get("dd"), place(p.get("dp"))) if x)) + (" " + dref(ev.get("zm", [])) if ev.get("zm") else ""))
    if p.get("bu"): fk.append(by_sex(pid, "pochowany: ", "pochowana: ", "pochowany(-a): ") + e(place(p["bu"])))
    if p.get("oc"): fk.append("zawód: " + e(p["oc"]))
    if p.get("re"): fk.append(by_sex(pid, "mieszkał: ", "mieszkała: ", "mieszkał(a): ") + e(place(p["re"])))
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
        for o_, fam in sp:
            ids = (ev.get("sl", {}).get(o_) or ev.get("zw", {}).get(o_) or [])
            parts.append(("dziecko z: " if fam.get("um") else "") + ref(o_, ci) + (f' — ślub {e(fam["md"])}' if fam.get("md") else "")
                         + (f', {e(place(fam["mp"]))}' if fam.get("mp") else "") + (" " + dref(ids) if ids else ""))
        h.append(f'<p><b>{"Małżonkowie" if len(sp) > 1 else "Małżonek"}:</b> ' + "; ".join(parts) + "</p>")
    kids = [c for fid2 in p["fs"] for c in (F.get(fid2) or {}).get("c", []) if P.get(c) and P[c]["t"] != "luka"]
    unnamed = [c for c in kids if no_given_name(c)]            # a child known only from a count: one phrase, not "Kowal, Kowal"
    kids = [c for c in kids if c not in unnamed]
    if kids or unnamed:
        dz = ev.get("dz", {})
        rest = ("dziecko o nieznanym imieniu" if len(unnamed) == 1 else f"{len(unnamed)} dzieci o nieznanych imionach") if unnamed else ""
        h.append("<p><b>Dzieci:</b> " + ", ".join(
            [(ref(c, ci) if c in chapters[ci - 1]["seen"] else e(nm(c))) + (f" ({e(life(P[c]))})" if life(P[c]) else "")
             + (" " + dref(dz[c]) if c in dz else "") for c in kids] + ([rest] if rest else [])) + "</p>")
    for hy in p.get("hy", []):
        h.append(f'<div class="box hyp"><b>{e(hy["q"])}</b><ul>' + "".join(
            f'<li><span class="st">{e(v["s"])}</span> {e(v["o"])}{(" — " + e(v["u"])) if v.get("u") else ""}</li>' for v in hy["v"])
            + "</ul>" + (f'<div class="r">Rozstrzygnie: {e(hy["r"])}</div>' if hy.get("r") else "") + "</div>")
    for c in p.get("cf", []):
        h.append(f'<div class="box cf"><b>Źródła podają różnie: {e(c["f"])}</b><table>' + "".join(
            f"<tr><td>{e(s)}</td><td>{e(v)}</td></tr>" for s, v in c["v"]) + f'</table><div class="r">{e(c["s"])}</div></div>')
    other = [x for x in where.get(pid, []) if x[0] != ci]
    if other: h.append('<p class="also">Także: ' + ", ".join(f'<a href="#r{a}-{b}">rozdz. {a} §{b}{sn_(f"r{a}-{b}")}</a>' for a, b in other) + "</p>")
    if NOTATKI and p.get("no"):
        h.append('<div class="notes">' + "".join(f"<p>{e(x)}</p>" for x in p["no"]) + "</div>")
    h.append("</section>")
    return "\n".join(h)

# ---------------------------------------------------------------- fan of all known ancestors (SVG)
KOLOR = ["#d3e1f2", "#f5dccd", "#d7ebcf", "#eadcf2"]   # grandparents' lines: father's father, father's mother, mother's father, mother's mother

def given(pid):
    n, sn = nm(pid), (P[pid].get("sn") or "")
    g = n[: -len(sn)].strip() if sn and n.endswith(sn) else n
    if g.startswith("Osoba żyjąca"): return "Osoba żyjąca", sn   # publish.py --living
    return (g.split() or [""])[0], sn

def fit(t, size, room):
    room_chars = max(2, int(room / (0.53 * size)))
    return t if len(t) <= room_chars else t[: room_chars - 1] + "…"

def fan_svg(root, label=""):
    """Every known ancestor of root. Only a known ancestor gets an angle, as much as their name needs (along
    the arc in the inner rings, along the radius further out); a branch with no further ancestors simply
    ends, so no space goes to empty fields. Fits in a half circle: a half circle; otherwise a full circle
    (the father's lines on the left, the mother's on the right). Links that are a hypothesis are dashed.
    Returns (svg, generations, distinct ancestors, full circle?)."""
    kids, hyp = {}, {}                              # pid -> its known parents; pid -> link to them is a hypothesis
    def walk(pid, g, seen):
        if pid in seen: kids[pid] = []; return g
        seen = seen | {pid}
        kids[pid], hyp[pid] = known_parents(pid)
        return max([g] + [walk(x, g + 1, seen) for x in kids[pid]])
    G = max(walk(root, 0, frozenset()), 1)
    R0, RMAX = 46, 492                              # the centre + G rings; outer rings wider (text along the radius needs length)
    wts = [0] + [1.0 if g <= 2 else 1.2 if g == 3 else 1.45 for g in range(1, G + 1)]
    unit = (RMAX - R0) / sum(wts)
    R = [0, R0]
    for g in range(1, G + 1): R.append(R[-1] + wts[g] * unit)
    TANG = 3 if G <= 7 else 2                       # rings with the text along the arc
    fs_t = lambda g: max(9.5, 14.5 - 1.6 * g)
    fs_r = lambda g: 10.5 if G <= 7 else 9.5
    def need(pid, g):                               # angle (radians) the person's own text needs
        rm = (R[g] + R[g + 1]) / 2
        gv, sn = given(pid)
        if g <= TANG: return (max(len(gv), len(sn)) * .53 * fs_t(g) + 10) / rm
        return (2 * fs_r(g) * 1.15 + 3) / rm
    NEED = {}
    def tot(pid, g, seen):
        if pid in seen: NEED[(pid, g)] = need(pid, g); return NEED[(pid, g)]
        NEED[(pid, g)] = max(need(pid, g), sum(tot(x, g + 1, seen | {pid}) for x in kids[pid]))
        return NEED[(pid, g)]
    total = sum(tot(x, 1, frozenset({root})) for x in kids[root])
    full = total > math.radians(200)
    span = math.radians(360 if full else 180)
    scale = span / total if total else 1
    K = min(1.25, max(.7, scale))                   # tight: smaller letters instead of cut names; loose: larger
    W = 1000
    H = 1000 if full else int(R[-1] + 24)
    cx, cy = 500, (500 if full else R[-1] + 10)
    def pt(r, a): return cx + r * math.cos(a), cy - r * math.sin(a)
    o_ = [f'<svg class="fan" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="Iowan Old Style,Palatino,Georgia,serif">']
    drawn, dashed_any = set(), [False]
    def draw(pid, g, a0, da, q, seen, dashed):
        drawn.add(pid)
        a1 = a0 - da
        r0, r1 = R[g], R[g + 1]
        x0, y0 = pt(r0, a0); x1, y1 = pt(r1, a0); x2, y2 = pt(r1, a1); x3, y3 = pt(r0, a1)
        large = 1 if da > math.pi else 0
        fill = "#ece8df" if g == 1 else KOLOR[q]
        stroke = 'stroke="#3f6ea8" stroke-width="1.3" stroke-dasharray="5 3"' if dashed else 'stroke="#fff" stroke-width="1.2"'
        dashed_any[0] |= dashed
        o_.append(f'<path d="M{x0:.1f},{y0:.1f} L{x1:.1f},{y1:.1f} A{r1:.1f},{r1:.1f} 0 {large} 1 {x2:.1f},{y2:.1f} L{x3:.1f},{y3:.1f} '
                  f'A{r0:.1f},{r0:.1f} 0 {large} 0 {x0:.1f},{y0:.1f} Z" fill="{fill}" {stroke}/>')
        gv, sn = given(pid); yrs = life(P[pid])
        am = a0 - da / 2; rm = (r0 + r1) / 2
        deg = math.degrees(am) % 360
        if g <= TANG:
            size = fs_t(g) * K; room = da * rm - 6
            lines = [(fit(gv, size, room), size, 600), (fit(sn, size, room), size, 400)]
            if (r1 - r0) > size * 3.3: lines.append((fit(yrs, size * .8, room), size * .8, 400))
            rot = (90 - deg) if deg <= 180 else (270 - deg)
        else:
            size = fs_r(g) * K; room = (r1 - r0) - 6; h_room = da * rm
            if h_room > size * 3.5:
                lines = [(fit(gv, size, room), size, 600), (fit(sn, size, room), size, 400), (fit(yrs, size * .85, room), size * .85, 400)]
            elif h_room > size * 2.3:
                lines = [(fit(gv, size, room), size, 600), (fit(sn, size, room), size, 400)]
            else:
                s1 = max(5.5, min(size, h_room / 1.25))
                lines = [(fit(gv + " " + sn, s1, room), s1, 600)]
            rot = -deg if (deg <= 90 or deg >= 270) else 180 - deg
        tx, ty = pt(rm, am)
        lh = [ln[1] * 1.15 for ln in lines]
        y = -sum(lh) / 2 + lh[0] * .8
        o_.append(f'<g transform="translate({tx:.1f},{ty:.1f}) rotate({rot:.1f})">')
        for (t, sz, wt), hh in zip(lines, lh):
            if t: o_.append(f'<text y="{y:.1f}" text-anchor="middle" font-size="{sz:.1f}" font-weight="{wt}" fill="#222">{e(t)}</text>')
            y += hh
        o_.append("</g>")
        ks = kids[pid] if pid not in seen else []
        sub = sum(NEED[(x, g + 1)] for x in ks) or 1
        a = a0
        for x in ks:
            d = da * NEED[(x, g + 1)] / sub
            qq = (q + (0 if x == par(pid)[0] else 1)) if g == 1 else q
            draw(x, g + 1, a, d, qq, seen | {pid}, dashed or hyp.get(pid, False))
            a -= d
    a = math.radians(270 if full else 180)
    f0 = par(root)[0]
    for x in kids[root]:
        d = NEED[(x, 1)] * scale
        draw(x, 1, a, d, 0 if x == f0 else 2, frozenset({root}), hyp.get(root, False))
        a -= d
    if full:
        o_.append(f'<circle cx="{cx}" cy="{cy}" r="{R0}" fill="#f3efe6" stroke="#fff" stroke-width="1.6"/>')
        ty0 = cy - 4
    else:
        o_.append(f'<path d="M{cx - R0},{cy} A{R0},{R0} 0 0 1 {cx + R0},{cy} Z" fill="#f3efe6" stroke="#fff" stroke-width="1.6"/>')
        ty0 = cy - 24
    if label and " i " in label:                    # "Tomasz i Ewa": two lines, the second starting "i"
        a_, b_ = label.split(" i ", 1); two = (a_, "i " + b_)
    else:
        two = (label, "") if label else given(root)
    for i, t in enumerate(two):
        if t: o_.append(f'<text x="{cx}" y="{ty0 + i * 13:.0f}" text-anchor="middle" font-size="{11 if i == 0 else 10}" '
                        f'font-weight="{600 if (i == 0 or label) else 400}">{e(fit(t, 11, 2 * R0 - 6))}</text>')
    o_.append("</svg>")
    return "".join(o_), G, len(drawn), full, dashed_any[0]

FANS = []                                                    # (label, generations, ancestors, full) for the summary
def fan_block(root, label, title):
    svg, G, n, full, dashed = fan_svg(root, label)
    FANS.append((label or nm(root), G, n, full))
    sw = lambda i: f'<span class="sw" style="background:{KOLOR[i]}"></span>'
    return (f'<div class="fanbox{" full" if full else ""}">' + (f'<h3 class="fanh">{e(title)}</h3>' if title else "") + svg +
            f'<p class="fancap">Wszyscy znani przodkowie w linii prostej: {n} {pl(n, "osoba", "osoby", "osób")}, {G} {pl(G, "pokolenie", "pokolenia", "pokoleń")}. '
            f'Kolory: {sw(0)} ojciec ojca · {sw(1)} matka ojca · {sw(2)} ojciec matki · {sw(3)} matka matki (licząc od środka). '
            'Gdzie gałąź się kończy, dalsi przodkowie są nieznani.'
            + (' Przerywana ramka: powiązanie z rodzicami to hipoteza.' if dashed else "") + '</p></div>')

def common_descendant():
    """The person nearest to every chapter's anchor among those descending from all of them (ME first on a tie)."""
    anchors = [ch["anchor"] for ch in chapters]
    depth = {}
    def up(pid):                                             # ancestor -> generations above pid (pid itself at 0)
        if pid in depth: return depth[pid]
        depth[pid] = {}
        d, q = {pid: 0}, [pid]
        while q:
            x = q.pop(0)
            for y in known_parents(x)[0]:
                if y not in d: d[y] = d[x] + 1; q.append(y)
        depth[pid] = d
        return d
    best = None
    for pid in sorted(P, key=lambda x: x != DB.get("root")):
        if P[pid]["t"] == "luka": continue
        d = up(pid)
        if all(a in d for a in anchors):
            score = sum(d[a] for a in anchors)
            if best is None or score < best[0]: best = (score, pid)
    return best[1] if best else None

FRONT_FANS = []
for spec in o.fan:
    who, sep, label = spec.partition("=") if "=" in spec else ("", "", spec)
    root = find_person(who.strip(), "--fan") if who.strip() else common_descendant()
    if not root: raise SystemExit("--fan: nobody in the tree descends from every chapter's anchor; name the person: --fan \"Given Surname|year=Label\"")
    FRONT_FANS.append((root, label.strip()))

# ---------------------------------------------------------------- the book's style
CSS = """
@page { size: A4; margin: 16mm 15mm 18mm 15mm;
  @bottom-center { content: counter(page); font: 8.5pt Georgia, serif; color: #888; } }
@page :first { @bottom-center { content: none; } }
* { box-sizing: border-box; }
body { font-family: "Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif; font-size: 10pt; line-height: 1.45; color: #1a1a1a; margin: 0; }
a { color: inherit; text-decoration: none; border-bottom: 1px dotted #999; }
.title { height: 255mm; display: flex; flex-direction: column; justify-content: center; text-align: center; }
.title h1 { font-size: 34pt; margin: 0 0 6mm; letter-spacing: -.5px; font-weight: 600; }
.title .rody { font-size: 13pt; color: #444; margin-bottom: 14mm; }
.title .stan { font-size: 10pt; color: #777; }
h2 { font-size: 18pt; margin: 0 0 3mm; break-before: page; font-weight: 600; }
h2 + .lead { margin-bottom: 7mm; }
h3 { font-size: 9pt; text-transform: uppercase; letter-spacing: 1.2px; color: #8a7f66; margin: 7mm 0 3mm; border-bottom: 1px solid #d8d0c0; padding-bottom: 1mm; break-after: avoid; }
.lead { color: #444; font-size: 9.6pt; border-left: 3px solid #c8c8c8; padding-left: 4mm; }
.os { break-inside: avoid; margin: 0 0 4.5mm; padding-left: 4mm; border-left: 2.5px solid #d8d0c0; overflow: hidden; }
.os h4 { font-size: 11pt; margin: 0 0 1mm; }
.os p { margin: 0 0 1mm; }
.nr { color: #8a7f66; font-weight: 400; font-size: 8.5pt; }
.ly { color: #555; font-weight: 400; }
.akm { font-size: 7.5pt; color: #777; }
.fanbox { break-inside: avoid; margin: 2mm 0 6mm; }
.fanbox svg { width: 100%; height: auto; max-height: 172mm; display: block; margin: 0 auto; }
.fanh { margin-top: 2mm; }
.fancap { font-size: 8.2pt; color: #555; margin: 1.5mm 0 0; }
.sw { display: inline-block; width: 3.2mm; height: 3.2mm; border-radius: 1px; vertical-align: -.4mm; border: 1px solid #ccc; }
.toc p { margin: 0 0 1.4mm; }
.tp { float: right; color: #555; }
.fk { color: #333; }
.ph { float: right; width: 17mm; height: 17mm; object-fit: cover; border-radius: 2mm; margin: 0 0 1mm 3mm; }
.t { font-size: 7.5pt; font-weight: 700; letter-spacing: .6px; text-transform: uppercase; border: 1px solid; border-radius: 9px; padding: 0 2mm; vertical-align: 1px; }
.t.akt { color: #2f7d3a; } .t.praw { color: #a9761d; } .t.hip { color: #3f6ea8; }
.ak { font-size: 8pt; font-weight: 700; color: #2f7d3a; border: 1px solid #2f7d3a; border-radius: 8px; padding: 0 1.4mm; }
.box { font-size: 9pt; border-left: 3px solid #a9761d; background: #faf7f0; padding: 1.5mm 3mm; margin: 1.5mm 0; break-inside: avoid; }
.box.hyp { border-left-color: #3f6ea8; background: #f3f6fa; }
.box.wall { border-left-color: #8a8378; background: #f5f4f1; }
.box ul { margin: 1mm 0; padding-left: 5mm; }
.box .st { font-size: 7.5pt; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; color: #555; }
.box .r { color: #555; font-size: 8.8pt; }
.box table { border-collapse: collapse; width: 100%; margin: 1mm 0; }
.box td { border-top: 1px solid #e3ddd0; padding: .8mm 2mm .8mm 0; vertical-align: top; }
.box td:last-child { font-weight: 700; width: 38%; }
.also { font-size: 8.5pt; color: #666; }
.notes { font-size: 8.3pt; color: #555; white-space: pre-wrap; }
.doc { margin: 0 0 7mm; }
.doc .dh { break-inside: avoid; }
.doc h4 { font-size: 10.5pt; margin: 0 0 1mm; break-after: avoid; }
.doc img { width: 100%; max-height: 70mm; object-fit: contain; object-position: left; border: 1px solid #ddd; margin: 1mm 0; }
.doc .tr, .doc .sg { break-inside: avoid; }
.doc pre { font-family: inherit; font-size: 8.8pt; white-space: pre-wrap; background: #f6f5f1; padding: 2mm 3mm; margin: 1mm 0; }
.doc .sg, .doc .tr { font-size: 8.8pt; color: #444; }
.idx { columns: 2; column-gap: 8mm; font-size: 9pt; }
.idx p { margin: 0 0 .6mm; break-inside: avoid; }
.idx .h { font-weight: 700; margin-top: 2.5mm; }
.legend p { margin: 0 0 2mm; }
"""
# print edition: the wider margin on the binding side, landscape pages for the front fans, no link underlines
CSS_PRINT = """
@page :left { margin: 16mm 22mm 18mm 13mm; }
@page :right { margin: 16mm 13mm 18mm 22mm; }
@page fan { size: A4 landscape; margin: 11mm 13mm 12mm 13mm; }
.fanpage { page: fan; break-before: page; }
.fanpage h2 { break-before: auto; }
.fanpage .fanbox svg { max-height: 150mm; }
a { border-bottom: none; }
.toc p { max-width: 150mm; }
"""

# ---------------------------------------------------------------- assembly
if FRAGS:
    n_people = len(where)
    n_fams = sum(1 for f in F.values() if f.get("h") in where or f.get("w") in where)
    rody = " · ".join(dict.fromkeys(plural(P[a]["sn"]) for _, a, _ in ch_list))
else:
    n_people = sum(1 for p in P.values() if p["t"] != "luka")
    n_fams = len(F)
    rody = DB.get("meta", {}).get("subtitle") or " · ".join(dict.fromkeys(plural(P[a]["sn"]) for _, a, _ in ch_list))
ROBOTS = '<meta name="robots" content="noindex,nofollow">' if 'name="robots"' in PAGE[:4000] else ""
today = datetime.date.today()
MIES = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września", "października", "listopada", "grudnia"]
dzis = f"{today.day} {MIES[today.month - 1]} {today.year}"

def tp(i):
    return f'<span class="tp">{PG[i]}</span>' if PRINT and i in PG else ""

def render():
    FANS.clear()
    out = [f'<!doctype html><html lang="pl"><head><meta charset="utf-8">{ROBOTS}<title>{e(o.title)}</title><style>'
           + CSS + (CSS_PRINT if PRINT else "") + "</style></head><body>",
           f'<div class="title"><h1>{e(o.title)}</h1><div class="rody">{e(rody)}</div>'
           f'<div class="stan">{n_people} {pl(n_people, "osoba", "osoby", "osób")} · {n_fams} {pl(n_fams, "rodzina", "rodziny", "rodzin")} · '
           f'{len(A)} {pl(len(A), "akt", "akty", "aktów")} z transkrypcją<br>stan na {dzis}</div></div>',
           """<h2 style="break-before:page">Jak czytać tę księgę</h2>
<div class="legend"><p>Każdy rozdział to przodkowie jednej osoby, pokolenie po pokoleniu. Osoby mają numery: osoba, od której
liczy się rozdział, to §1, jej ojciec §2, matka §3, a ogólnie ojciec osoby §n to §2n, a matka §2n+1. Numer z dopiskiem
„r.” odsyła do innego rozdziału.</p>
<p><span class="t akt">akt</span> <span class="t praw">prawdopodobne</span> <span class="t hip">hipoteza</span> — na czym opiera się
wpis: akt z sygnaturą, mocna poszlaka (indeks, rejestr, przekaz) albo trop do sprawdzenia. Osoba bez tego znaku
pochodzi z drzewa rodzinnego albo z relacji rodziny.</p>
<p><span class="ak">D12</span> przy dacie, rodzicach, małżonku albo dziecku — przepisany akt, który to potwierdza
(aneks „Dokumenty”, z wycinkiem skanu i transkrypcją).</p>
<p>Ramki: <b>ściana</b> — rodzice nieznani i co byłoby następnym krokiem; <b>hipoteza</b> — możliwe odpowiedzi, każda ze
stanem; <b>źródła podają różnie</b> — dwie wersje obok siebie.</p>
<p><b>Wachlarz</b> na początku """ + ("księgi i " if FRONT_FANS else "") + """każdego rozdziału pokazuje przodków na jednym obrazku: w środku osoba,
wyżej jej rodzice, dziadkowie i dalsze pokolenia; kolor mówi, z której linii dziadków ktoś pochodzi.</p>"""
           + ("<p>Przy odsyłaczu do innego rozdziału i w indeksie stoi numer strony.</p>" if PRINT else "") + "</div>"]
    toc = ['<h3>Rozdziały</h3><div class="toc">']
    for ci, ch in enumerate(chapters, 1):
        nums = [k for k, v in ch["num"].items() if not isinstance(v, tuple)]
        rel = anchor_to_reader(ci)
        k, deep = len(nums) - 1, max(nums).bit_length() - 1
        toc.append(f'<p><a href="#r{ci}">{ci}. {e(ch["lab"][0].upper() + ch["lab"][1:])}</a>{e(" — " + rel) if rel else ""} · '
                   f'{k} {pl(k, "przodek", "przodków", "przodków")}, {deep} {pl(deep, "pokolenie", "pokolenia", "pokoleń")}{tp("r" + str(ci))}</p>')
    toc.append(f'<p><a href="#dok">Dokumenty</a> · {len(A)} {pl(len(A), "akt", "akty", "aktów")}{tp("dok")}</p>'
               f'<p><a href="#idx">Indeks osób</a>{tp("idx")}</p></div>')
    out[-1] += "".join(toc)
    for root, label in FRONT_FANS:
        out.append(('<div class="fanpage">' if PRINT else "") + f'<h2>Wachlarz przodków — {e(label or nm(root))}</h2>'
                   + fan_block(root, label, "") + ("</div>" if PRINT else ""))
    for ci, ch in enumerate(chapters, 1):
        nums = sorted(k for k, v in ch["num"].items() if not isinstance(v, tuple))
        akt = sum(1 for k in nums if P[ch["num"][k]]["t"] == "akt")
        walls = sum(1 for k in nums for x in par(ch["num"][k])[:2] if x and P[x]["t"] == "luka")
        deep = max(nums).bit_length() - 1
        k = len(nums) - 1
        out.append(f'<h2 id="r{ci}">{ci}. {e(ch["lab"][0].upper() + ch["lab"][1:])}</h2>'
                   f'<p class="lead">{k} {pl(k, "przodek", "przodków", "przodków")} w {deep} {pl(deep, "pokoleniu", "pokoleniach", "pokoleniach")} '
                   f'wstecz od: {e(nm(ch["anchor"]))} · {akt} z aktem · ścian: {walls}</p>')
        if k: out.append(fan_block(ch["anchor"], "", "Wachlarz rozdziału"))
        g = -1
        for n in nums:
            gn = n.bit_length() - 1
            if gn != g:
                g = gn
                out.append("<h3>" + e(gen_header(g, ci)) + "</h3>")
            out.append(entry(ch["num"][n], n, ci))
        dup = sorted(k for k, v in ch["num"].items() if isinstance(v, tuple))
        if dup: out.append('<p class="also">Zbieg przodków: ' + ", ".join(f"§{k} = §{ch['num'][k][1]}" for k in dup) + "</p>")

    out.append('<h2 id="dok">Dokumenty</h2><p class="lead">Akty przepisane w całości, w kolejności jak w drzewie. Przy każdym: wycinek skanu, '
               'transkrypcja oryginału, tłumaczenie, sygnatura i to, co akt potwierdza.</p>')
    for aid, a in A.items():
        img = CROP.get(aid, "")
        # header and scan stay together; the rest may break: "avoid" on the whole act put one act per page
        out.append(f'<div class="doc" id="d{DN[aid]}"><div class="dh"><h4><span class="ak">D{DN[aid]}</span> {e(a["t"])}</h4>'
                   + (f'<div class="sg">{e(a.get("d", ""))}</div>' if a.get("d") else "")
                   + (f'<img src="{e(img)}" alt="">' if img and os.path.exists(os.path.join(OUTDIR, img)) else "") + "</div>"
                   + f'<pre>{e(a.get("x", ""))}</pre>'
                   + (f'<div class="tr"><b>Tłumaczenie.</b> {e(a["p"]).replace(chr(10), "<br>")}</div>' if a.get("p") else "")
                   + (f'<div class="tr"><b>Potwierdza:</b> {e("; ".join(a["w"]))}</div>' if a.get("w") else "")
                   + (f'<div class="tr"><b>Osoby:</b> ' + ", ".join(ref(pid) + f" ({e(r)})" for pid, r in WHO_IN.get(aid, [])) + "</div>" if WHO_IN.get(aid) else "")
                   + f'<div class="sg">{e(a.get("s", ""))}{(" · " + e(a["z"])) if a.get("z") else ""}</div></div>')

    out.append('<h2 id="idx">Indeks osób</h2><div class="idx">')
    groups = {}
    for pid in where:
        groups.setdefault(snkey(P[pid].get("sn")), []).append(pid)
    for k in sorted(groups):
        sp = list(dict.fromkeys(P[x].get("sn") for x in sorted(groups[k], key=lambda x: fold(P[x].get("sn") or "")) if P[x].get("sn")))
        out.append(f'<p class="h">{e(" · ".join(sp) or "(bez nazwiska)")}</p>')
        for pid in sorted(groups[k], key=lambda x: (P[x].get("by") or "9999", fold(P[x]["n"]))):
            out.append(f"<p>{e(nm(pid))} {e(life(P[pid]))} — " + ", ".join(
                f'<a href="#r{a}-{b}">{a}/§{b}{(" s." + chr(160) + str(PG[f"r{a}-{b}"])) if PRINT and f"r{a}-{b}" in PG else ""}</a>'
                for a, b in where[pid]) + "</p>")
    out.append("</div></body></html>")
    return "\n".join(out)

def write_html():
    with io.open(OUT, "w", encoding="utf-8") as fh:
        fh.write(render())

def print_pdf(chrome):
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
                    "--print-to-pdf=" + PDF, "file://" + OUT], check=True, capture_output=True, timeout=600)

def pages_in_pdf():
    """Chrome turns every link target (id) into a named destination: id -> page number."""
    r = PdfReader(PDF)
    return {k.lstrip("/"): r.get_destination_page_number(v) + 1 for k, v in r.named_destinations.items()}

write_html()
print("written", OUT, "— chapters: %d, people with an entry: %d, acts: %d" % (len(chapters), len(where), len(A)))
for label, G, n, full in FANS:
    print(f"   fan {label}: {n} ancestors, {G} generation{'s' if G != 1 else ''}, {'full circle' if full else 'half circle'}")
if not o.no_pdf:
    chrome = find_chrome()
    if not chrome: raise SystemExit("no Chrome or Chromium found: set CHROME=/path/to/chrome, or use --no-pdf and print the HTML")
    print_pdf(chrome)
    if PRINT:                                                # numbers change the text, the text can move the pages
        for run in range(2, 5):
            now = pages_in_pdf()
            if now == PG:
                print(f"  page numbers stable after {run - 1} passes"); break
            PG.clear(); PG.update(now)
            print(f"  pass {run}: page numbers in")
            write_html(); print_pdf(chrome)
        else:
            if pages_in_pdf() != PG:
                print("!! page numbers still moving after 4 passes: check the contents and a few cross-references by hand")
    print("written", PDF, "(%.1f MB)" % (os.path.getsize(PDF) / 1048576))
