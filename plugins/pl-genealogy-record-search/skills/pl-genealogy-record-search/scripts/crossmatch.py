#!/usr/bin/env python3
"""Match people in the tree against index rows saved by `geneteka.py search ... --json`.

  crossmatch.py tree.json index1.json [index2.json ...] [--years 15]

Matches on given name + surname with diacritics folded, trying both the birth surname
and the married one (_MARNM): women are indexed under either. For marriage files both the
groom and the bride columns are matched. --years drops candidates whose act year is far
from the person's own dates.

The output is CANDIDATES, not matches. Grade each by hand: the strongest single
confirmation is the spouse's given name in the remarks column, then the parents' names.
"""
import argparse
import json
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _net import norm  # noqa: E402

# (given, surname, parents/remarks columns shown) per record type
PEOPLE_COLS = {"B": [(2, 3, (4, 5, 6))], "D": [(2, 3, (4, 5, 6))],
               "S": [(2, 3, (4, 5, 6, 7)), (5, 6, (2, 3, 4, 7))]}


def key(s):
    return re.sub(r"[^a-z]", "", norm(s))


def _year(v):
    m = re.search(r"(1[4-9]\d\d|20\d\d)", v or "")
    return int(m.group(1)) if m else None


def load_index(paths):
    idx = {}
    for path in paths:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        bdm = d.get("bdm", "B")
        for r in d["rows"]:
            for g, s, extra in PEOPLE_COLS.get(bdm, PEOPLE_COLS["B"]):
                if len(r) > max(g, s):
                    for given in (r[g] or "").split():   # double given names: try each
                        idx.setdefault((key(given), key(r[s])), []).append((bdm, r, extra))
    return idx


def crossmatch(tree, idx, years=None):
    P, F = tree["people"], tree["fams"]

    def spouses(i):
        out = []
        for fid in P[i].get("fams", []):
            f = F.get(fid)
            o = f and (f["wife"] if f["husb"] == i else f["husb"])
            if o and o in P:
                out.append(P[o]["name"])
        return "; ".join(out)
    results = []
    for i, p in sorted(P.items(), key=lambda kv: kv[1]["name"] or ""):
        own = [y for y in (_year((p["birt"] or [None])[0]), _year((p["deat"] or [None])[0])) if y]
        cands = []
        for given in (p.get("givn") or "").split()[:2]:
            for sn in filter(None, {p.get("surn"), p.get("marnm")}):
                for bdm, r, extra in idx.get((key(given), key(sn)), []):
                    ay = _year(r[0])
                    if years and own and ay and min(abs(ay - y) for y in own) > years:
                        continue
                    if (bdm, r) not in [(c[0], c[1]) for c in cands]:
                        cands.append((bdm, r, extra))
        if cands:
            results.append((i, spouses(i), cands))
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tree")
    ap.add_argument("index", nargs="+")
    ap.add_argument("--years", type=int, default=0, help="max distance between act year and own dates")
    o = ap.parse_args(argv)
    with open(o.tree, encoding="utf-8") as f:
        tree = json.load(f)
    res = crossmatch(tree, load_index(o.index), o.years or None)
    P = tree["people"]
    for i, sp, cands in res:
        p = P[i]
        b = (p["birt"] or ["?"])[0] or "?"
        d = (p["deat"] or ["?"])[0] or "?"
        print(f"\n* TREE  {p['name']:<32} b.{b:<12} d.{d:<12} spouse: {sp[:40]}  {i}")
        for bdm, r, extra in cands:
            ctx = " / ".join(r[k] for k in extra if k < len(r) and r[k])
            print(f"    {bdm} {r[0]} act {r[1]:>4}  {' '.join(r[2:4]):<28} {ctx[:110]}")
    print(f"\n{len(res)} people with candidates. Grade by hand: spouse's name in remarks, then parents.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
