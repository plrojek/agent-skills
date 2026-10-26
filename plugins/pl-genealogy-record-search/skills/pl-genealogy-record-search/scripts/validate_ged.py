#!/usr/bin/env python3
"""Check a GEDCOM after patching it. Usage: validate_ged.py tree.ged   (exit 1 on errors)

Checks:
  * FAMC/FAMS <-> CHIL/HUSB/WIFE close both ways and point at existing records
  * no duplicate XREFs
  * every line starts with a level number
  * 0 TRLR exists and is the LAST record. Records appended after the trailer are
    silently dropped by strict readers, so everything added that way vanishes on import.
"""
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_ged import parse, read_text  # noqa: E402


def check(path):
    d = parse(path)
    P, F = d["people"], d["fams"]
    err = []
    for i, p in P.items():
        for f in p["famc"]:
            if f not in F:
                err.append(f"{i}: FAMC {f} does not exist")
            elif i not in F[f]["chil"]:
                err.append(f"{i}: FAMC {f} has no matching CHIL")
        for f in p["fams"]:
            if f not in F:
                err.append(f"{i}: FAMS {f} does not exist")
            elif i not in (F[f]["husb"], F[f]["wife"]):
                err.append(f"{i}: FAMS {f} but not its HUSB/WIFE")
    for fid, f in F.items():
        for role in ("husb", "wife"):
            x = f[role]
            if x and x not in P:
                err.append(f"{fid}: {role.upper()} {x} does not exist")
            elif x and fid not in P[x]["fams"]:
                err.append(f"{fid}: {role.upper()} {x} has no matching FAMS")
        for c in f["chil"]:
            if c not in P:
                err.append(f"{fid}: CHIL {c} does not exist")
            elif fid not in P[c]["famc"]:
                err.append(f"{fid}: CHIL {c} has no matching FAMC")

    lines = read_text(path).split("\n")
    ids = [ln.split()[1] for ln in lines if re.match(r"^0 @[^@]+@ ", ln)]
    dup = [k for k, v in collections.Counter(ids).items() if v > 1]
    bad = [n for n, ln in enumerate(lines, 1) if ln.strip() and not re.match(r"^\s*\d+ ", ln)]
    level0 = [(n, ln.strip()) for n, ln in enumerate(lines, 1) if re.match(r"^0 ", ln)]
    trlr = [n for n, ln in level0 if ln == "0 TRLR"]
    if not trlr:
        err.append("no 0 TRLR record")
    elif level0[-1][1] != "0 TRLR":
        after = [ln for n, ln in level0 if n > trlr[-1]]
        err.append(f"0 TRLR is on line {trlr[-1]} but {len(after)} record(s) follow it "
                   f"(first: {after[0][:40]}); move the trailer to the end")
    if len(trlr) > 1:
        err.append(f"{len(trlr)} TRLR records")
    return len(P), len(F), err, dup, bad


def main(path):
    n_p, n_f, err, dup, bad = check(path)
    print(f"INDI={n_p} FAM={n_f}")
    print(f"errors: {len(err)}")
    for e in err[:30]:
        print("  x", e)
    print(f"duplicate XREFs: {dup or 'none'}")
    print(f"lines without a level number: {bad[:10] or 'none'}")
    return 1 if (err or dup or bad) else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
