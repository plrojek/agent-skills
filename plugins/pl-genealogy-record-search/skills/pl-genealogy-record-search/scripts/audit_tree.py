#!/usr/bin/env python3
"""Chronology check of a parsed tree. Usage: audit_tree.py tree.json

Flags: parent younger than 15 at a child's birth, mother older than 55, child born after
the mother's death or more than a year after the father's, death before birth, age over 105.
These are structural errors worth reporting even when they have nothing to do with records.
"""
import json
import re
import sys


def year(ev):
    if not ev or not ev[0]:
        return None
    m = re.search(r"(1[4-9]\d\d|20\d\d)", ev[0])
    return int(m.group(1)) if m else None


def audit(tree):
    P, F = tree["people"], tree["fams"]

    def label(i):
        p = P[i]
        b, d = year(p["birt"]), year(p["deat"])
        return (p["name"] or "(no name)") + (f" b.{b}" if b else "") + (f" d.{d}" if d else "") + f" {i}"
    out = []
    for f in F.values():
        for role in ("husb", "wife"):
            par = f[role]
            if not par or par not in P:
                continue
            pb, pd = year(P[par]["birt"]), year(P[par]["deat"])
            for c in f["chil"]:
                cb = year(P[c]["birt"]) if c in P else None
                if not cb:
                    continue
                if pb is not None:
                    gap = cb - pb
                    if gap < 15:
                        out.append(f"parent too young ({gap}): {label(par)} -> {label(c)}")
                    elif gap > 55 and role == "wife":
                        out.append(f"mother too old ({gap}): {label(par)} -> {label(c)}")
                if pd is not None:
                    if role == "wife" and cb > pd:
                        out.append(f"born after the mother's death: {label(par)} -> {label(c)}")
                    if role == "husb" and cb > pd + 1:
                        out.append(f"born over a year after the father's death: {label(par)} -> {label(c)}")
    for i, p in P.items():
        b, d = year(p["birt"]), year(p["deat"])
        if b and d and d < b:
            out.append(f"death before birth: {label(i)}")
        if b and d and d - b > 105:
            out.append(f"age over 105: {label(i)}")
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as f:
        found = audit(json.load(f))
    for x in found:
        print("  x " + x)
    print(f"\nanomalies: {len(found)}")
