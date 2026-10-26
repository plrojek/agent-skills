#!/usr/bin/env python3
"""One surname (or several) through every script-accessible source you switch on.

  sweep_all.py <Surname> [<Surname> ...] [--przemysl] [--grobonet HOST[,HOST]]
               [--repressions] [--geneteka WOJ[,WOJ]] [--types BSD]

Nothing runs unless you name it, because every source is a real site and most are run
by volunteers. Pick the ones that fit the family:
  --przemysl       municipal cemeteries of Przemyśl (birth dates from grave cards)
  --grobonet H     a Grobonet cemetery instance, <town>.grobonet.com
  --repressions    Indeks Represjonowanych (deportations, Soviet repression)
  --geneteka W     Geneteka parish indexes, province-wide, for the provinces given

Female forms are asked for too (-ski/-cki/-dzki -> -ska/-cka/-dzka and back).
A source that fails does not stop the others. If Geneteka gives an answer that is not
real (see geneteka.sanity_reasons), the rows are dropped and Geneteka is skipped for the
rest of the run: repeating requests is what gets a network flagged.
"""
import argparse
import os
import re
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def variants(surname):
    out = [surname]
    if surname.endswith("ki"):
        out.append(surname[:-1] + "a")
    elif surname.endswith("ka") and re.search(r"(s|c|dz)ka$", surname):
        out.append(surname[:-1] + "i")
    return out


def header(t):
    print("\n" + "=" * 72 + f"\n  {t}\n" + "=" * 72)


def przemysl(names):
    import cmentarze_przemysl as C
    header("PRZEMYŚL MUNICIPAL CEMETERIES - birth dates from grave cards")
    rs = C.people(names)
    for r in sorted(rs, key=lambda x: (x["surname"], x["born"] or "9999")):
        print(f"  {r['given']:<24}{r['surname']:<24} b. {r['born'] or '?':<11} d. {r['died'] or '?':<11} "
              f"{r['cemetery']} {r['section']}/{r['row']}/{r['grave']}")
    print(f"  -> {len(rs)}")


def grobonet(names, hosts):
    import grobonet as G
    for host in hosts:
        header(f"GROBONET - {host}")
        for sn in names:
            total, rows = G.search(host, sn)
            if not total:
                continue
            print(f"  -- {sn} -> {total}")
            for r in sorted(rows, key=lambda x: (x["sector"], x["row"], x["grave"])):
                print(f"     {r['name']:<30} b. {r['born'] or '?':<11} d. {r['died'] or '?':<11} "
                      f"{r['sector']}/{r['row']}/{r['grave']} id={r['id']}")


def repressions(names):
    import indeks_repr as I
    header("INDEKS REPRESJONOWANYCH - deportations and repression")
    for sn in names:
        total, rows = I.query(100, last_name=sn, exact_last_name="1")
        print(f"  -- {sn} -> {total}" + (f" (first {len(rows)}; narrow it with indeks_repr.py)" if total > len(rows) else ""))
        for uid, t in rows:
            print(f"     {t[:80]}  {I.B}/szczegoly/{uid}")


def geneteka(names, wojs, types):
    import geneteka as G
    header("GENETEKA - parish indexes")
    for w in wojs:
        for sn in names:
            for bdm in types:
                try:
                    total, rows, _, problems = G.search(w, bdm, sn, max_rows=200)
                except Exception as e:
                    print(f"  {w} {sn} [{bdm}] error: {e!r}"[:120])
                    continue
                if problems:
                    print(f"  {w} {sn} [{bdm}] DROPPED, not a real answer: {'; '.join(problems)}")
                    print("  Stopping Geneteka for this run. Check with `geneteka.py check` later.")
                    return
                if not total:
                    print(f"  -- {G.WOJ.get(w, w)} {sn} [{bdm}] -> 0")
                    continue
                print(f"  -- {G.WOJ.get(w, w)} {sn} [{bdm}] -> {total}" +
                      (f" (showing 25 of {len(rows)} read)" if len(rows) > 25 else ""))
                for r in rows[:25]:
                    print("     " + " | ".join(x for x in r if x)[:190])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("surnames", nargs="+")
    ap.add_argument("--przemysl", action="store_true")
    ap.add_argument("--grobonet", default="")
    ap.add_argument("--repressions", action="store_true")
    ap.add_argument("--geneteka", default="", help="province codes, e.g. 06mp,09pk")
    ap.add_argument("--types", default="BSD", help="Geneteka record types, subset of BSD")
    o = ap.parse_args(argv)
    names = list(dict.fromkeys(v for s in o.surnames for v in variants(s)))
    jobs = []
    if o.przemysl:
        jobs.append(("przemysl", przemysl, (names,)))
    if o.grobonet:
        jobs.append(("grobonet", grobonet, (names, [h for h in o.grobonet.split(",") if h])))
    if o.repressions:
        jobs.append(("repressions", repressions, (names,)))
    if o.geneteka:
        types = [t for t in o.types.upper() if t in "BSD"]
        jobs.append(("geneteka", geneteka, (names, [w for w in o.geneteka.split(",") if w], types)))
    if not jobs:
        ap.error("switch on at least one source: --przemysl, --grobonet, --repressions, --geneteka")
    print("surnames: " + ", ".join(names))
    for name, fn, args in jobs:
        try:
            fn(*args)
        except Exception:
            print(f"\n  ! {name}: source unavailable")
            traceback.print_exc(limit=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
