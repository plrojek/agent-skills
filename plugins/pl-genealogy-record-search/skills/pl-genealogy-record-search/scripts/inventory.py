#!/usr/bin/env python3
"""Phase 1 inventory of a parsed tree. Usage: inventory.py tree.json [--root @I1@]

Prints three lists, in the order to work them:
  1. brick walls: ancestors of --root (or, without --root, everyone) with no parents
  2. placeholders: no given name, no surname, a woman whose surname equals her husband's
     (often copied from him instead of her maiden name), no birth year at all
  3. surname x place frequency: which parishes to open first
"""
import argparse
import collections
import json
import re
import sys


def _year(ev):
    m = re.search(r"(1[4-9]\d\d|20\d\d)", (ev or [""])[0] or "")
    return int(m.group(1)) if m else None


def ancestors(P, F, root):
    seen, todo = {}, [(root, 0)]
    while todo:
        i, gen = todo.pop()
        if i in seen or i not in P:
            continue
        seen[i] = gen
        for fid in P[i]["famc"]:
            f = F.get(fid)
            if f:
                todo += [(x, gen + 1) for x in (f["husb"], f["wife"]) if x]
    return seen


def inventory(tree, root=None):
    P, F = tree["people"], tree["fams"]
    scope = ancestors(P, F, root) if root else {i: None for i in P}

    def parents(i):
        return [x for fid in P[i]["famc"] if fid in F for x in (F[fid]["husb"], F[fid]["wife"]) if x]

    walls = []
    for i, gen in scope.items():
        par = parents(i)
        if len(par) < 2:
            walls.append((gen, i, "no parents" if not par else "one parent missing"))
    walls.sort(key=lambda w: (-(w[0] or 0), P[w[1]]["name"] or ""))

    holes = []
    for i, p in P.items():
        if not (p.get("givn") or "").strip():
            holes.append((i, "no given name"))
        if not (p.get("surn") or "").strip():
            holes.append((i, "no surname"))
        if p.get("sex") == "F" and p.get("surn"):
            for fid in p["fams"]:
                h = F.get(fid, {}).get("husb")
                if h in P and (P[h].get("surn") or "").lower() == p["surn"].lower():
                    holes.append((i, "surname equals the husband's: maiden name missing?"))
        if not _year(p.get("birt")) and not _year(p.get("deat")):
            holes.append((i, "no birth or death year"))

    freq = collections.Counter()
    for p in P.values():
        sn = (p.get("surn") or "").strip()
        for ev in (p.get("birt"), p.get("deat"), p.get("buri")):
            if sn and ev and ev[1]:
                freq[(sn, ev[1].split(",")[0].strip())] += 1
    return walls, holes, freq


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tree")
    ap.add_argument("--root", help="XREF of the person whose ancestors are the target")
    ap.add_argument("--top", type=int, default=40)
    o = ap.parse_args(argv)
    with open(o.tree, encoding="utf-8") as f:
        tree = json.load(f)
    P = tree["people"]
    if o.root and o.root not in P:
        sys.exit(f"{o.root} is not in the tree")
    walls, holes, freq = inventory(tree, o.root)
    print(f"## 1. Brick walls ({len(walls)})")
    for gen, i, why in walls:
        g = f"gen {gen}" if gen is not None else ""
        print(f"  {g:<7}{P[i]['name'] or '(no name)':<34} b.{(P[i]['birt'] or [''])[0] or '?':<14} {why}  {i}")
    print(f"\n## 2. Placeholders and gaps ({len(holes)})")
    for i, why in holes:
        print(f"  {P[i]['name'] or '(no name)':<40} {why}  {i}")
    print(f"\n## 3. Surname x place (top {o.top})")
    for (sn, pl), n in freq.most_common(o.top):
        print(f"  {n:>4}  {sn:<24} {pl}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
