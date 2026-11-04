#!/usr/bin/env python3
"""Make the copy of the tree page that leaves your computer.

    python3 publish.py out/tree.html publication/                  # noindex + 11-digit numbers masked
    python3 publish.py out/tree.html publication/ --living 1926    # + people presumed living redacted
    python3 publish.py out/tree.html publication/ --living 1926 --living-names keep

Writes publication/index.html and copies the scans/ folder next to it. Standard library only.

- Adds <meta name="robots" content="noindex,nofollow">. That only asks search engines to stay away:
  the page still needs access control on the server (references/publishing.md).
- Replaces every 11-digit number with a placeholder: a PESEL copied from a land register or an act
  into a note would otherwise go out with the page. The photo line (`const IMG`) is left alone: a run of
  digits inside base64 is not a number, and changing it would break a photo.
- --living YEAR: a person with no date of death and no burial who was born in YEAR or later is presumed
  living. So is someone with no birth year whose child or spouse is presumed living. Their dates, places,
  occupation, notes, sources and photo are removed; the name becomes "Osoba żyjąca <surname>" unless
  --living-names keep, also where the name labels a grandparent's line. Relationships stay, so the tree
  keeps its shape. The list of redacted people is printed: read it, the rule is a heuristic.
  The line labels (LINES in tree_data.py) are your own text and are not rewritten: a line whose anchor is
  presumed living is printed, so you can relabel it for the public copy if the label names that person.
- The family book is a PDF and can't be filtered afterwards: build it from the published page
  (`build_book.py publication/index.html`), never copy one made from the unredacted page.
"""
import argparse
import json
import os
import re
import shutil
import sys

PESEL = re.compile(r"\b\d{11}\b")
ROBOTS = '<meta name="robots" content="noindex,nofollow">'
WIPE = ("bd", "bp", "by", "dd", "dp", "dy", "bu", "oc", "re", "mn")


def split_page(text):
    lines = text.split("\n")
    i_db = next(i for i, l in enumerate(lines) if l.startswith("const DB = "))
    i_img = next(i for i, l in enumerate(lines) if l.startswith("const IMG = "))
    db = json.loads(lines[i_db][len("const DB = "):].rstrip().rstrip(";"))
    img = json.loads(lines[i_img][len("const IMG = "):].rstrip().rstrip(";"))
    return lines, i_db, i_img, db, img


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


def publish(page, outdir, living=None, keep_names=False, quiet=False):
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
    lines[i_db] = "const DB = " + j(db) + ";"
    n = 0
    for i, line in enumerate(lines):
        if i != i_img:
            lines[i], k = PESEL.subn("[numer usunięty w wersji publicznej]", line)
            n += k
    lines[i_img] = "const IMG = " + j(img) + ";"
    out = "\n".join(lines)
    if ROBOTS not in out:
        out = out.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n' + ROBOTS, 1)
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "index.html"), "w", encoding="utf-8") as f:
        f.write(out)
    scans = os.path.join(os.path.dirname(os.path.abspath(page)), "scans")
    if os.path.isdir(scans):
        shutil.copytree(scans, os.path.join(outdir, "scans"), dirs_exist_ok=True)
    say(f"{os.path.join(outdir, 'index.html')}: {n} eleven-digit numbers masked, scans/ copied")
    return {"masked": n, "redacted": redacted, "line_labels": warned}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page")
    ap.add_argument("outdir")
    ap.add_argument("--living", type=int, metavar="YEAR", help="redact people presumed living (born YEAR or later, no death)")
    ap.add_argument("--living-names", choices=["hide", "keep"], default="hide")
    o = ap.parse_args(argv)
    publish(o.page, o.outdir, o.living, o.living_names == "keep")
    return 0


if __name__ == "__main__":
    sys.exit(main())
