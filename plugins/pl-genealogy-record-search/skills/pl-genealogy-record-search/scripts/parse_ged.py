#!/usr/bin/env python3
"""GEDCOM -> JSON: {people, fams}. Usage: parse_ged.py tree.ged [out.json]

Reads UTF-8 (with or without BOM), then falls back to cp1250 and latin-1. ANSEL files
(old exports, "1 CHAR ANSEL") are read as latin-1 with a warning: re-export as UTF-8.
Multi-line NOTEs are joined from their CONT/CONC lines.
"""
import json
import re
import sys

LINE = re.compile(r"^\s*(\d+) (?:(@[^@]+@) )?(\w+)(?: (.*))?$")


def read_text(path):
    with open(path, "rb") as f:
        data = f.read()
    for enc in ("utf-8-sig", "cp1250", "latin-1"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if re.search(r"^1 CHAR ANSEL", text, re.M):
        print("warning: ANSEL encoding, letters with diacritics may be wrong; "
              "re-export the tree as UTF-8", file=sys.stderr)
    return text.replace("\r\n", "\n").replace("\r", "\n")


def records(text):
    """Level-0 records as nested {tag, val, xref, sub} nodes."""
    roots, stack = [], []
    for ln in text.split("\n"):
        m = LINE.match(ln)
        if not m:
            continue
        lvl, xref, tag, val = int(m.group(1)), m.group(2), m.group(3), m.group(4) or ""
        node = {"tag": tag, "val": val, "xref": xref, "sub": []}
        if lvl == 0:
            roots.append(node)
            stack = [node]
        elif stack:
            del stack[lvl:]
            stack[-1]["sub"].append(node)
            stack.append(node)
    return roots


def _get(n, t):
    return next((s for s in n["sub"] if s["tag"] == t), None) if n else None


def _all(n, t):
    return [s for s in n["sub"] if s["tag"] == t] if n else []


def _val(n, *tags):
    for t in tags:
        n = _get(n, t)
        if n is None:
            return None
    return n["val"]


def _flat(n):
    out = n["val"]
    for s in n["sub"]:
        if s["tag"] == "CONT":
            out += "\n" + s["val"]
        elif s["tag"] == "CONC":
            out += s["val"]
    return out


def _event(n):
    return [_val(n, "DATE"), _val(n, "PLAC")] if n else None


def parse(path):
    people, fams = {}, {}
    for r in records(read_text(path)):
        if r["tag"] == "INDI":
            nm = _get(r, "NAME")
            res = _get(r, "RESI")
            people[r["xref"]] = {
                "id": r["xref"],
                "name": (nm["val"].replace("/", " ") if nm else "").strip().replace("  ", " "),
                "givn": _val(nm, "GIVN") if nm else None,
                "surn": _val(nm, "SURN") if nm else None,
                "marnm": _val(nm, "_MARNM") if nm else None,
                "sex": _val(r, "SEX"),
                "birt": _event(_get(r, "BIRT")) or _event(_get(r, "CHR")),
                "deat": _event(_get(r, "DEAT")),
                "buri": _event(_get(r, "BURI")),
                "occu": _val(r, "OCCU"),
                "resi": (_val(res, "PLAC") or _val(res, "ADDR")) if res else None,
                "famc": [x["val"] for x in _all(r, "FAMC")],
                "fams": [x["val"] for x in _all(r, "FAMS")],
                "notes": [_flat(x) for x in _all(r, "NOTE")],
            }
            p = people[r["xref"]]
            if nm and not p["surn"]:          # no SURN line: take it from /Surname/
                m = re.search(r"/([^/]*)/", nm["val"])
                p["surn"] = m.group(1).strip() if m else None
            if nm and not p["givn"]:
                p["givn"] = nm["val"].split("/")[0].strip() or None
        elif r["tag"] == "FAM":
            fams[r["xref"]] = {
                "id": r["xref"], "husb": _val(r, "HUSB"), "wife": _val(r, "WIFE"),
                "chil": [x["val"] for x in _all(r, "CHIL")],
                "marr": _event(_get(r, "MARR")),
            }
    return {"people": people, "fams": fams}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    d = parse(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else "tree.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    print(f"INDI: {len(d['people'])}  FAM: {len(d['fams'])}  -> {out}", file=sys.stderr)
