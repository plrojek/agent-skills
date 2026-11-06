#!/usr/bin/env python3
# Part of pl-genealogy-tree-viewer (plugin pl-genealogy-record-search). Made by Applied AI · https://appliedai.dev · https://github.com/plrojek/agent-skills
"""Make the copy of the tree page that leaves your computer.

    python3 publish.py out/tree.html publication/                  # noindex + 11-digit numbers masked
    python3 publish.py out/tree.html publication/ --living 1926    # + people presumed living redacted
    python3 publish.py out/tree.html publication/ --living 1926 --living-names keep

Writes publication/index.html, copies the scans/ folder next to it and writes the poster configurator to
publication/poster/ (--no-posters leaves it out). Standard library only.

- Adds <meta name="robots" content="noindex,nofollow">. That only asks search engines to stay away:
  the page still needs access control on the server (references/publishing.md).
- Replaces every 11-digit number in the tree's data (names, notes, acts, everything in `const DB`) with a
  placeholder: a PESEL copied from a land register or an act into a note would otherwise go out with the
  page. Nothing else is touched: photos (base64), the Atlas 3D code and the wordmark hold digit runs that
  are not numbers, and changing them would break them.
- --living YEAR: a person with no date of death and no burial who was born in YEAR or later is presumed
  living. So is someone with no birth year whose child or spouse is presumed living. Their dates, places,
  occupation, notes, sources and photo are removed; the name becomes "Osoba żyjąca <surname>" unless
  --living-names keep, also where the name labels a grandparent's line. Relationships stay, so the tree
  keeps its shape. The list of redacted people is printed: read it, the rule is a heuristic.
  The line labels (LINES in tree_data.py) are your own text and are not rewritten: a line whose anchor is
  presumed living is printed, so you can relabel it for the public copy if the label names that person.
- The family book is a PDF and can't be filtered afterwards: build it from the published page
  (`build_book.py publication/index.html`), never copy one made from the unredacted page.
- Posters: publication/poster/ is the poster configurator (a tree illustration with the ancestors on
  cartouches, PDF and SVG made in the browser) reading poster/people.json: name, surname, years and
  parents of everyone, taken from the published data, so people presumed living stay redacted there too.
  The tree page's "Plakaty do druku" link and the "Ułóż plakat" button appear only when poster/ is written.

Part of pl-genealogy-tree-viewer. Made by Applied AI (https://appliedai.dev),
https://github.com/plrojek/agent-skills
"""
import argparse
import json
import os
import re
import shutil
import sys

PESEL = re.compile(r"\b\d{11}\b")
MASK = "[numer usunięty w wersji publicznej]"
CREDIT = "pl-genealogy-tree-viewer · Made by Applied AI (https://appliedai.dev) · https://github.com/plrojek/agent-skills"
SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTER = os.path.join(SKILL, "templates", "poster")
BRAND = os.path.join(SKILL, "templates", "brand")
ROBOTS = '<meta name="robots" content="noindex,nofollow">'
WIPE = ("bd", "bp", "by", "dd", "dp", "dy", "bu", "oc", "re", "mn")


def split_page(text):
    lines = text.split("\n")
    i_db = next(i for i, l in enumerate(lines) if l.startswith("const DB = "))
    i_img = next(i for i, l in enumerate(lines) if l.startswith("const IMG = "))
    db = json.loads(lines[i_db][len("const DB = "):].rstrip().rstrip(";"))
    img = json.loads(lines[i_img][len("const IMG = "):].rstrip().rstrip(";"))
    return lines, i_db, i_img, db, img


def mask_numbers(value):
    """Every string inside the tree's data, recursively: (masked copy, how many numbers)."""
    n = 0
    def visit(v):
        nonlocal n
        if isinstance(v, str):
            out, k = PESEL.subn(MASK, v); n += k; return out
        if isinstance(v, dict): return {k: visit(x) for k, x in v.items()}
        if isinstance(v, list): return [visit(x) for x in v]
        return v
    return visit(value), n


def poster_people(db):
    """What the poster configurator reads: name, surname, birth and death year, parents (walls left out)."""
    people, fams = db["people"], db["fams"]
    year = lambda v: (re.search(r"\d{4}", str(v or "")) or [""])[0]
    out = {}
    for pid, p in people.items():
        if p.get("t") == "luka": continue
        fam = next((fams[f] for f in p.get("fc") or [] if f in fams and (fams[f].get("h") or fams[f].get("w"))), {})
        out[pid] = {"name": str(p.get("n") or ""), "surname": str(p.get("sn") or ""),
                    "born": year(p.get("by")), "died": year(p.get("dy")),
                    "parents": [None if not x or (people.get(x) or {}).get("t") == "luka" else x
                                for x in (fam.get("h"), fam.get("w"))]}
    return out


def write_posters(db, outdir):
    """publication/poster/: the configurator, its illustrations, the wordmark for its footer, people.json."""
    dst = os.path.join(outdir, "poster")
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(POSTER, dst)
    shutil.copytree(BRAND, os.path.join(dst, "brand"), ignore=shutil.ignore_patterns("*.md"))
    page_path = os.path.join(dst, "index.html")
    with open(page_path, encoding="utf-8") as f:
        page = f.read()
    if db.get("root"):
        page = page.replace('<meta name="poster-static" content="1">',
                            '<meta name="poster-static" content="1">\n  <meta name="poster-root" content="'
                            + db["root"].replace('"', "") + '">', 1)
    with open(page_path, "w", encoding="utf-8") as f:
        f.write(page)
    people = poster_people(db)
    with open(os.path.join(dst, "people.json"), "w", encoding="utf-8") as f:
        json.dump(people, f, ensure_ascii=False, separators=(",", ":"))
    return len(people)


def presumed_living(P, F, year):
    def alive_by_dates(p):
        return (p.get("t") != "luka" and not (p.get("dd") or p.get("dy") or p.get("bu"))
                and p.get("by", "").isdigit() and int(p["by"]) >= year)
    living = {pid for pid, p in P.items() if alive_by_dates(p)}
    changed = True
    while changed:                       # no birth year and no death: follow living children and spouses
        changed = False
        for pid, p in P.items():
            if pid in living or p.get("t") == "luka" or p.get("by") or p.get("dd") or p.get("dy") or p.get("bu"):
                continue
            near = set()
            for fid in p.get("fs", []):
                f = F.get(fid) or {}
                near.update(f.get("c", [])); near.update(x for x in (f.get("h"), f.get("w")) if x and x != pid)
            if near & living:
                living.add(pid); changed = True
    return living


def redact(db, img, year, keep_names=False):
    P, F = db["people"], db["fams"]
    living = presumed_living(P, F, year)
    for pid in living:
        p = P[pid]
        for k in WIPE: p[k] = ""
        for k in ("no",): p[k] = []
        for k in ("sd", "ev", "cf", "hy", "hw"): p.pop(k, None)
        if not keep_names:
            p["n"] = ("Osoba żyjąca " + p.get("sn", "")).strip()
            if pid in db.get("lnd", {}): db["lnd"][pid][0] = p["n"]      # the label "linia: <name>"
        for k in ("t", "b"): img.get(k, {}).pop(pid, None)
    return sorted(living, key=lambda x: (P[x].get("sn", ""), x))


def publish(page, outdir, living=None, keep_names=False, quiet=False, posters=True):
    say = (lambda *a: None) if quiet else print
    with open(page, encoding="utf-8") as f:
        text = f.read()
    lines, i_db, i_img, db, img = split_page(text)
    redacted, warned = [], []
    if living:
        before = {pid: p["n"] for pid, p in db["people"].items()}
        redacted = redact(db, img, living, keep_names)
        say(f"presumed living (born {living} or later, no death): {len(redacted)}")
        for pid in redacted: say("   ", before[pid])
        for lab, (anchor, _short) in db.get("lines", {}).items():
            if anchor in redacted:
                warned.append(lab)
                say(f"!! line {lab!r}: its anchor is presumed living; the label is kept as written in LINES")
    j = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    db, n = mask_numbers(db)
    lines[i_db] = "const DB = " + j(db) + ";"
    lines[i_img] = "const IMG = " + j(img) + ";"
    out = "\n".join(lines)
    if ROBOTS not in out:
        out = out.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n' + ROBOTS, 1)
    if 'name="generator"' not in out:
        out = out.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<meta name="generator" content="' + CREDIT + '">', 1)
    n_posters = 0
    if posters:
        n_posters = write_posters(db, outdir) if os.path.isdir(POSTER) else 0
        if n_posters: out = out.replace('id="poster-link" href="poster/" hidden', 'id="poster-link" href="poster/"', 1)
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "index.html"), "w", encoding="utf-8") as f:
        f.write(out)
    scans = os.path.join(os.path.dirname(os.path.abspath(page)), "scans")
    if os.path.isdir(scans):
        shutil.copytree(scans, os.path.join(outdir, "scans"), dirs_exist_ok=True)
    say(f"{os.path.join(outdir, 'index.html')}: {n} eleven-digit numbers masked, scans/ copied"
        + (f", poster/ with {n_posters} people" if n_posters else ""))
    return {"masked": n, "redacted": redacted, "line_labels": warned, "posters": n_posters}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page")
    ap.add_argument("outdir")
    ap.add_argument("--living", type=int, metavar="YEAR", help="redact people presumed living (born YEAR or later, no death)")
    ap.add_argument("--living-names", choices=["hide", "keep"], default="hide")
    ap.add_argument("--no-posters", action="store_true", help="no poster/ configurator (about 14 MB of illustrations)")
    o = ap.parse_args(argv)
    publish(o.page, o.outdir, o.living, o.living_names == "keep", posters=not o.no_posters)
    return 0


if __name__ == "__main__":
    sys.exit(main())
