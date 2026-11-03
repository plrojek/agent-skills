#!/usr/bin/env python3
"""Build the family-tree page from a GEDCOM and the research tables in tree_data.py.

    python3 build_tree.py path/to/tree_data.py [--template tree.html] [--out tree.html]
    uv run --with pillow==11.3.0 python3 build_tree.py tree_data.py     # when there are photos or scan pages

tree_data.py is plain Python next to the GEDCOM: the title, the lines (one anchor person per
branch), tiers, walls, hypotheses, acts with transcriptions, variants, conflicts. Every key that
names a person is "Given Surname|birth-year", "Given Surname" or an xref like "@I12@" looked up
right before it was typed; a key that matches no one or several people is printed, never guessed.
The format is in references/data-model.md; templates/example/tree_data.py uses all of it.

The page is written from the template each time. Edits to the viewer go into a copy of
templates/viewer/tree.html passed with --template, not into the output.
Writes: the page, scans/ next to it (from ACTS pages and crops) and nothing else.
"""
import argparse
import html
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from parse_ged import parse  # noqa: E402

SKILL = os.path.dirname(HERE)
TEMPLATE = os.path.join(SKILL, "templates", "viewer", "tree.html")

# ---------------------------------------------------------------- tiers
# Explicit markers in a GEDCOM NOTE decide the tier. A note without a marker is NOT a reason to
# doubt a person: facts the family gives are certain unless someone says otherwise.
RE_TIER = [
    (re.compile(r"TIER:\s*(PEWNE|CERTAIN)", re.I), ""),
    (re.compile(r"TIER:\s*(AKT|DOCUMENT|PROVEN)", re.I), "akt"),
    (re.compile(r"TIER:\s*(PRAWDOPODOBNE|PROBABLE)", re.I), "praw"),
    (re.compile(r"TIER:\s*(HIPOTEZA|HYPOTHESIS)", re.I), "hip"),
]
# Optional (AUTO_TIER_FROM_CITATIONS = True): a note citing an act or a signature counts as "akt".
RE_CITATION = re.compile(r"sygn\.|akt \d+\s*/\s*\d+|akt nr \d|skan \d|z aktu |ze skanu|karta grobu", re.I)

# ---------------------------------------------------------------- roles in an act (evidence)
# Judged by the FIRST part of the role ("ojciec dziecka, zgłaszający" = father).
NOT_FAMILY = re.compile(r"^(świadek|swiadek|pierwszy świadek|drugi świadek|chrzestn|zgłaszając|zglaszajac|wymienion|"
                        r"właściciel|wlasciciel|dłużnicz|dluznicz|witness|godparent|godfather|godmother|informant|"
                        r"mentioned|owner)", re.I)
BIRTH_ROLE = re.compile(r"^(dziecko|child)", re.I)
DEATH_ROLE = re.compile(r"^(zmarł|zmarl|deceased)", re.I)
COUPLE_ROLE = re.compile(r"^(pan młody|panna młoda|pan mlody|panna mloda|groom|bride)", re.I)


def act_kind(title):
    t = title.lower()
    if re.search(r"urodze|chrzt|ochrzcz|birth|baptism|christening", t): return "U"
    if re.search(r"ślub|slub|małżeń|malzen|zapowied|marriage|banns", t): return "S"
    if re.search(r"zgon|zmarł|zmarl|pochow|death|burial", t): return "Z"
    return ""


def family_role(role):
    return not NOT_FAMILY.search(re.split(r"\s*[—,(;:]", role.strip())[0])


# ---------------------------------------------------------------- dates
MON = dict(JAN="01", FEB="02", MAR="03", APR="04", MAY="05", JUN="06", JUL="07", AUG="08", SEP="09",
           OCT="10", NOV="11", DEC="12")


def dm(t):
    """GEDCOM DATE -> (Polish display text, year)."""
    if not t: return "", ""
    t = t.strip()
    pre = ""
    for k, v in (("ABT", "ok. "), ("BEF", "przed "), ("AFT", "po "), ("EST", "ok. "), ("CAL", "ok. ")):
        if t.upper().startswith(k + " "): pre, t = v, t[4:].strip()
    if t.upper().startswith("BET "):
        ys = [y.group(0) for y in (re.search(r"\d{4}", x) for x in re.split(r"\s+AND\s+", t[4:], flags=re.I)) if y]
        return ("między " + " a ".join(ys)) if ys else "", (ys[0] if ys else "")
    m = re.match(r"^(\d{1,2}) ([A-Z]{3}) (\d{4})$", t.upper())
    if m: return pre + "%02d.%s.%s" % (int(m.group(1)), MON.get(m.group(2), "??"), m.group(3)), m.group(3)
    m = re.match(r"^([A-Z]{3}) (\d{4})$", t.upper())
    if m: return pre + MON.get(m.group(1), "??") + "." + m.group(2), m.group(2)
    if re.match(r"^\d{4}$", t): return pre + t, t
    y = re.search(r"\d{4}", t)
    return pre + t, (y.group(0) if y else "")


def load_config(path):
    spec = importlib.util.spec_from_file_location("tree_data", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build(cfg_path, template=None, out=None, quiet=False):
    say = (lambda *a: None) if quiet else print
    cfg = load_config(cfg_path)
    base = os.path.dirname(os.path.abspath(cfg_path))
    get = lambda name, default: getattr(cfg, name, default)
    rel = lambda p: p if os.path.isabs(p) else os.path.join(base, p)
    out = os.path.abspath(out or rel(get("OUTPUT", "tree.html")))
    outdir = os.path.dirname(out)
    os.makedirs(outdir, exist_ok=True)
    problems = []

    d = parse(rel(get("GEDCOM", "tree.ged")))
    GP, GF = d["people"], d["fams"]

    # ---------------------------------------------------------- people and families
    people, fams = {}, {}
    for pid, p in GP.items():
        b, dd, bu = p["birt"] or (None, None), p["deat"] or (None, None), p["buri"] or (None, None)
        bd, by = dm(b[0]); ded, dy = dm(dd[0])
        people[pid] = {"id": pid, "n": p["name"] or "(bez imienia)", "s": p["sex"] or "U",
                       "sn": p["surn"] or "", "mn": p["marnm"] or "",
                       "bd": bd, "bp": b[1] or "", "by": by, "dd": ded, "dp": dd[1] or "", "dy": dy,
                       "bu": " · ".join(x for x in (dm(bu[0])[0], bu[1]) if x),
                       "oc": p["occu"] or "", "re": p["resi"] or "", "no": p["notes"],
                       "fc": list(p["famc"]), "fs": list(p["fams"]), "t": ""}
    for fid, f in GF.items():
        md, _ = dm((f["marr"] or (None, None))[0])
        fams[fid] = {"id": fid, "h": f["husb"], "w": f["wife"], "c": list(f["chil"]),
                     "md": md, "mp": (f["marr"] or (None, None))[1] or ""}

    by_key = {}
    for pid, pp in people.items():
        by_key.setdefault(pp["n"], []).append(pid)
        if pp["by"]: by_key.setdefault(pp["n"] + "|" + pp["by"], []).append(pid)

    def one(key, table):
        hit = ([key] if key in people else []) if key.startswith("@") else (by_key.get(key) or [])
        if len(hit) != 1:
            problems.append(f"{table}: key {key!r} matches {len(hit)} people")
            return None
        return hit[0]

    # ---------------------------------------------------------- tiers
    override = {}
    for k, v in get("TIER_OVERRIDE", {}).items():
        pid = one(k, "TIER_OVERRIDE")
        if pid: override[pid] = v
    auto = get("AUTO_TIER_FROM_CITATIONS", False)
    for pid, pp in people.items():
        if pid in override:
            pp["t"] = override[pid]; continue
        notes = " \n".join(pp["no"])
        for rx, tier in RE_TIER:
            if rx.search(notes):
                pp["t"] = tier; break
        else:
            if auto and RE_CITATION.search(notes): pp["t"] = "akt"

    # ---------------------------------------------------------- couples without a marriage
    for fid, note in get("UNMARRIED", {}).items():
        if fid in fams: fams[fid]["um"] = 1
        else: problems.append(f"UNMARRIED: no family {fid}")

    # ---------------------------------------------------------- people only in the tree (no document)
    for e in get("EXTRA_PEOPLE", []):
        child = one(e["child"], "EXTRA_PEOPLE")
        if not child: continue
        xid = e["id"]; fid = "@XF" + xid.strip("@") + "@"
        people[xid] = {"id": xid, "n": e["name"], "s": e.get("sex", "U"), "sn": e.get("surname", ""), "mn": "",
                       "bd": "", "bp": "", "by": "", "dd": "", "dp": "", "dy": "", "bu": "", "oc": "", "re": "",
                       "no": [e["note"]] if e.get("note") else [], "fc": [], "fs": [fid], "t": e.get("tier", "")}
        dashed = 1 if e.get("dashed", True) else 0
        fams[fid] = {"id": fid, "h": xid if e.get("sex", "M") != "F" else None, "w": xid if e.get("sex") == "F" else None,
                     "c": [child], "md": "", "mp": "", "hp": dashed}
        people[child]["fc"].append(fid)
        if dashed: people[child]["hp"] = 1
        if e.get("unknown_spouse"):
            lab, step = e["unknown_spouse"]
            wid = "@XW" + xid.strip("@") + "@"
            people[wid] = {"id": wid, "n": "❓ " + lab, "s": "U", "sn": "— ŚCIANA —", "mn": "", "bd": "", "bp": "",
                           "by": "", "dd": "", "dp": "", "dy": "", "bu": "", "oc": "", "re": "", "no": [], "fc": [],
                           "fs": [fid], "t": "luka", "w": step, "wf": child, "br": "", "wn": people[child]["n"], "wg": 0}
            fams[fid]["w" if fams[fid]["h"] else "h"] = wid

    # ---------------------------------------------------------- branches attached on a hypothesis
    for ckey, (fid, tier, why) in get("HYPOTHESIS_LINKS", {}).items():
        kid = one(ckey, "HYPOTHESIS_LINKS")
        if not kid: continue
        if fid not in fams:
            problems.append(f"HYPOTHESIS_LINKS: no family {fid}"); continue
        fams[fid]["hp"] = 1
        if kid not in fams[fid]["c"]: fams[fid]["c"].append(kid)
        if fid not in people[kid]["fc"]: people[kid]["fc"].insert(0, fid)
        people[kid].update(hp=1, hpt=tier, hw=why)
        for x in (fams[fid]["h"], fams[fid]["w"]):
            if x and people.get(x) and people[x]["t"] != "akt": people[x]["t"] = tier

    # ---------------------------------------------------------- lines (one anchor per branch)
    BR = []
    for a, lab, short in get("LINES", []):
        pid = one(a, "LINES")
        if pid: BR.append((pid, lab, short))
    DEFBR, DEFSHORT = "poza znanymi gałęziami", "pozostali"

    def parents(pid):
        fc = people[pid]["fc"]
        if not fc: return None, None
        f = fams.get(fc[0]) or {}
        return f.get("h"), f.get("w")

    def ancestors(start):
        seen, q, walls = {start: 0}, [(start, 0)], []
        while q:
            x, g = q.pop(0)
            a, b = parents(x)
            if not a and not b:
                walls.append((g, x)); continue
            for y in (a, b):
                if y and y not in seen:
                    seen[y] = g + 1; q.append((y, g + 1))
        return seen, walls

    def blood(anchor):
        up, _ = ancestors(anchor)
        grp, fr, i = set(up), list(up), 0
        while i < len(fr):
            x = fr[i]; i += 1
            for fid in people[x]["fs"]:
                for y in (fams.get(fid) or {}).get("c") or []:
                    if y and y not in grp: grp.add(y); fr.append(y)
        return grp

    branch = {}
    for a, lab, _ in BR:
        for x in blood(a): branch.setdefault(x, lab)

    def spouse_pass():
        ch = True
        while ch:
            ch = False
            for f in fams.values():
                h, w = f.get("h"), f.get("w")
                if not (h and w): continue
                if h in branch and w not in branch: branch[w] = branch[h]; ch = True
                elif w in branch and h not in branch: branch[h] = branch[w]; ch = True

    # the married-in spouse's own family follows them into the branch, cascading until nothing changes
    done = set(branch)
    while True:
        spouse_pass()
        fresh = [k for k in branch if k not in done]
        if not fresh: break
        done.update(fresh)
        for x in sorted(fresh):
            for y in blood(x): branch.setdefault(y, branch[x])
    for x in people: branch.setdefault(x, DEFBR)
    for x, lab in branch.items():
        if x in people and not people[x].get("br"): people[x]["br"] = lab
    counts = {}
    for x, pp in people.items():
        if pp["t"] != "luka": counts[pp["br"]] = counts.get(pp["br"], 0) + 1
    LINES = {lab: [a, sh] for a, lab, sh in BR}
    if counts.get(DEFBR): LINES[DEFBR] = [None, DEFSHORT]

    # ---------------------------------------------------------- walls above every ancestor without parents
    walls_by_id = {}
    for k, v in get("WALLS_BY_ID", {}).items():
        pid = one(k, "WALLS_BY_ID")
        if pid: walls_by_id[pid] = v
    WALLS = get("WALLS", {})
    allwalls, seen_w = [], set()
    for a, _, _ in BR:
        for g, x in ancestors(a)[1]:
            if x not in seen_w and people[x]["t"] != "luka":
                seen_w.add(x); allwalls.append((g, x))
    nw, missing = 0, []
    for g, x in sorted(allwalls):
        p = people[x]
        what, how = walls_by_id.get(x) or WALLS.get(p["n"] + "|" + p["by"]) or WALLS.get(p["n"]) or (None, None)
        if what is None:
            missing.append(p["n"])
            what, how = "Rodzice — " + p["n"], "Brak tropu. Tu kończy się ta gałąź w obecnym stanie wiedzy."
        nw += 1
        wid, wfid = "@L%d@" % nw, "@LF%d@" % nw
        people[wid] = {"id": wid, "n": "❓ " + what, "s": "U", "sn": "— ŚCIANA —", "mn": "", "bd": "", "bp": "",
                       "by": "", "dd": "", "dp": "", "dy": "", "bu": "", "oc": "", "re": "", "no": [], "fc": [],
                       "fs": [wfid], "t": "luka", "w": how, "wf": x, "br": branch.get(x, DEFBR), "wn": p["n"], "wg": g}
        fams[wfid] = {"id": wfid, "h": wid, "w": None, "c": [x], "md": "", "mp": ""}
        people[x]["fc"].append(wfid)
    for pp in people.values():
        if pp["t"] == "luka" and not pp.get("br"): pp["br"] = branch.get(pp.get("wf"), DEFBR)

    # ---------------------------------------------------------- acts, scans
    scans = os.path.join(outdir, "scans")
    acts, named = {}, {}
    need_pil = any(a.get("page") for a in get("ACTS", []))
    Image = ImageOps = None
    if need_pil:
        try:
            from PIL import Image, ImageOps
        except ImportError:
            raise SystemExit("ACTS have scan pages: run with Pillow, e.g. `uv run --with pillow==11.3.0 python3 build_tree.py ...`")
        os.makedirs(scans, exist_ok=True)
    for a in get("ACTS", []):
        aid = a["id"]
        page, line = os.path.join(scans, aid + ".jpg"), os.path.join(scans, aid + "-line.jpg")
        if a.get("page"):
            src = rel(a["page"])
            if not os.path.exists(src):
                problems.append(f"ACTS {aid}: no page file {a['page']}")
            elif not (os.path.exists(line) and os.path.getmtime(line) >= max(os.path.getmtime(src), os.path.getmtime(cfg_path))):
                im = Image.open(src).convert("L" if a.get("autocontrast") else "RGB")
                if a.get("autocontrast"): im = ImageOps.autocontrast(im, cutoff=1)
                box = a.get("crop")
                if box:
                    if all(0 <= v <= 1 for v in box):
                        box = (box[0] * im.width, box[1] * im.height, box[2] * im.width, box[3] * im.height)
                    im.crop(tuple(int(v) for v in box)).save(line, quality=84)
                whole = im.copy(); whole.thumbnail((1800, 1800)); whole.save(page, quality=70)
        if not os.path.exists(page): problems.append(f"ACTS {aid}: no scans/{aid}.jpg")
        acts[aid] = {"t": a["title"], "d": a.get("date", ""), "s": a.get("ref", ""), "z": a.get("source", ""),
                     "x": a.get("text", ""), "p": a.get("translation", ""),
                     "i": "scans/%s.jpg" % aid, "c": "scans/%s-line.jpg" % aid if (a.get("crop") or os.path.exists(line)) else ""}
        for key, role in a.get("people", {}).items():
            pid = one(key, "ACTS " + aid)
            if not pid: continue
            people[pid].setdefault("sd", []).append([aid, role])
            named.setdefault(aid, {})[pid] = role
    # whoever is named in a transcribed act has tier "akt" — otherwise tier and sources drift apart
    raised = [x for x, pp in people.items() if pp.get("sd") and pp["t"] != "akt"]
    for x in raised: people[x]["t"] = "akt"

    # ---------------------------------------------------------- evidence: what each act proves
    def parents_fid(child, parent):
        for fid in people[child]["fc"]:
            f = fams.get(fid) or {}
            if not f.get("hp") and parent in (f.get("h"), f.get("w")): return fid
        return None

    def couple_fid(a, b):
        for fid in people[a]["fs"]:
            f = fams.get(fid) or {}
            if {f.get("h"), f.get("w")} == {a, b}: return fid
        return None

    def ev(pid): return people[pid].setdefault("ev", {})

    def add(dct, k, aid):
        lst = dct.setdefault(k, [])
        if aid not in lst: lst.append(aid)

    tally = dict(ur=0, zm=0, sl=0, rd=0, zw=0)
    for a in get("ACTS", []):
        aid, kind = a["id"], act_kind(a["title"])
        nm = {pid: r for pid, r in named.get(aid, {}).items() if family_role(r)}
        w, par_of = [], {}
        for pid, r in nm.items():
            if kind == "U" and BIRTH_ROLE.search(r.strip()) and not people[pid].get("hp"):
                ev(pid).setdefault("ur", []).append(aid); tally["ur"] += 1; w.append("urodzenie: " + people[pid]["n"])
            if kind == "Z" and DEATH_ROLE.search(r.strip()):
                ev(pid).setdefault("zm", []).append(aid); tally["zm"] += 1; w.append("zgon: " + people[pid]["n"])
        for x in nm:
            for y in nm:
                if x == y: continue
                if parents_fid(x, y):
                    add(ev(x).setdefault("rd", {}), y, aid); add(ev(y).setdefault("dz", {}), x, aid)
                    par_of.setdefault(x, []).append(y); tally["rd"] += 1
                if x < y and couple_fid(x, y):
                    wed = kind == "S" and COUPLE_ROLE.search(nm[x].strip()) and COUPLE_ROLE.search(nm[y].strip())
                    for p1, p2 in ((x, y), (y, x)): add(ev(p1).setdefault("sl" if wed else "zw", {}), p2, aid)
                    tally["sl" if wed else "zw"] += 1
                    w.append(("ślub: " if wed else "małżeństwo: ") + people[x]["n"] + " i " + people[y]["n"])
        for ch, ps in par_of.items():
            w.append("rodzice: " + people[ch]["n"] + " — " + " i ".join(people[q]["n"] for q in ps))
        if a.get("proves"):
            w = list(a["proves"]) if isinstance(a["proves"], (list, tuple)) else [a["proves"]]
        elif not kind:
            w = [people[pid]["n"] + ": " + r for pid, r in named.get(aid, {}).items()]
        acts[aid]["w"] = w

    # ---------------------------------------------------------- conflicts and hypotheses
    for c in get("CONFLICTS", []):
        pid = one(c["who"], "CONFLICTS")
        if pid: people[pid].setdefault("cf", []).append({"f": c["fact"], "v": [list(x) for x in c["versions"]], "s": c["status"]})
    for h in get("HYPOTHESES", []):
        pid = one(h["who"], "HYPOTHESES")
        if pid: people[pid].setdefault("hy", []).append({"q": h["question"], "r": h.get("resolves", ""),
            "v": [{"o": v["text"], "s": v["status"], "u": v.get("notes", "")} for v in h["variants"]]})

    # ---------------------------------------------------------- photos
    img = {"t": {}, "b": {}}
    files = {}
    pdir = get("PHOTOS", "")
    if pdir and os.path.isdir(rel(pdir)):
        for fn in sorted(os.listdir(rel(pdir))):
            m = re.match(r"^(I\w+)\.(jpe?g|png|webp)$", fn, re.I)
            if m and "@" + m.group(1) + "@" in people: files["@" + m.group(1) + "@"] = os.path.join(rel(pdir), fn)
    for k, fn in get("PHOTO_FILES", {}).items():
        pid = one(k, "PHOTO_FILES")
        if pid: files[pid] = rel(fn)
    if files:
        try:
            from PIL import Image as PImage
        except ImportError:
            raise SystemExit("photos found: run with Pillow, e.g. `uv run --with pillow==11.3.0 python3 build_tree.py ...`")
        import base64, io
        for pid, fn in files.items():
            im = PImage.open(fn).convert("RGB")
            s = min(im.size); left = (im.width - s) // 2; top = int((im.height - s) * 0.2)   # faces sit high
            th = im.crop((left, top, left + s, top + s)).resize((128, 128))
            big = im.copy(); big.thumbnail((480, 480))
            for key, pic, q in (("t", th, 78), ("b", big, 80)):
                buf = io.BytesIO(); pic.save(buf, "JPEG", quality=q)
                img[key][pid] = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

    # ---------------------------------------------------------- write
    title = get("TITLE", "Drzewo rodzinne")
    meta = {"title": title}
    if get("SUBTITLE", ""): meta["subtitle"] = get("SUBTITLE", "")
    if get("BOOK", ""): meta["book"] = get("BOOK", "")
    db = {"people": people, "fams": fams, "acts": acts, "lines": LINES, "var": get("VARIANTS", []), "meta": meta}
    j = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = open(template or TEMPLATE, encoding="utf-8").read()
    for ph in ("__DB__", "__IMG__", "__TITLE__", "__H1__"):
        if page.count(ph) != 1: raise SystemExit(f"template: {ph} must occur exactly once")
    page = (page.replace("const DB = __DB__;", "const DB = " + j(db) + ";")
                .replace("const IMG = __IMG__;", "const IMG = " + j(img) + ";")
                .replace("__TITLE__", html.escape(title)).replace("__H1__", html.escape(title)))
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)

    real = [p for p in people.values() if p["t"] != "luka"]
    tiers = {}
    for p in real: tiers[p["t"] or "-"] = tiers.get(p["t"] or "-", 0) + 1
    say(f"{out}: {len(real)} people, {len(fams)} families, {nw} walls, {len(acts)} acts, {len(img['t'])} photos")
    say("lines:", ", ".join(f"{lab} {counts.get(lab, 0)}" for lab in LINES))
    say("tiers:", tiers, "| raised to akt by an act:", len(raised))
    say("evidence: births %(ur)d, deaths %(zm)d, weddings %(sl)d, parent-child %(rd)d, marriages %(zw)d" % tally)
    if missing: say(f"!! {len(missing)} walls without a description in WALLS:", ", ".join(missing[:12]) + (" …" if len(missing) > 12 else ""))
    for pr in problems: say("!!", pr)
    return {"out": out, "people": len(real), "walls": nw, "acts": len(acts), "problems": problems,
            "missing_walls": missing, "evidence": tally, "db": db}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config", help="tree_data.py")
    ap.add_argument("--template", help="your copy of templates/viewer/tree.html")
    ap.add_argument("--out", help="output page (default: OUTPUT in tree_data.py)")
    o = ap.parse_args(argv)
    r = build(o.config, o.template, o.out)
    return 1 if r["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
