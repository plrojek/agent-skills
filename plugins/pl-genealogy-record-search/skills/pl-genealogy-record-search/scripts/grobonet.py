#!/usr/bin/env python3
"""Grobonet cemetery search. Many Polish parishes and towns run an instance at
<name>.grobonet.com; find the one for your cemetery on grobonet.com first.

  grobonet.py --host <name>.grobonet.com <Surname> [Surname2 ...] [--first NAME]
  grobonet.py --host <name>.grobonet.com --grave <person-id>
      everyone buried in that person's grave, with dates

Results are paged 12 at a time (&ppstrona=N); the script reads every page.
Dates can be partial: a birth year with no day, or "data nieznana" (unknown).
The results list already shows sector / row / grave number, so people in one grave are
grouped below. Use --grave for a grave's other occupants, whatever their surname:
a shared grave is the strongest family evidence this source gives.
"""
import argparse
import html
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _net  # noqa: E402

MAX_PAGES = 60


def _clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?is)<[^>]+>", " ", s))).strip()


def _items(h):
    out = []
    for li in re.findall(r"(?is)<li>(.*?)</li>", h):
        m = re.search(r"/osoba/(\d+)", li)
        name = re.search(r'(?is)class="sp">\s*śp\.\s*<span>(.*?)</span>', li)
        if not (m and name):
            continue
        txt = _clean(li)
        born = re.search(r"ur\.\s*([0-9]{4}(?:-[0-9]{2}){0,2})", txt)
        died = re.search(r"zm\.\s*([0-9]{4}(?:-[0-9]{2}){0,2})", txt)
        loc = {k: (re.search(k + r":\s*(\S+)", txt) or [None, ""])[1]
               for k in ("Sektor", "Rząd", "Nr grobu")}
        cem = re.search(r'(?is)<p><span class="szary">(.*?)</span></p>', li)
        out.append({"id": m.group(1), "name": _clean(name.group(1)),
                    "born": born.group(1) if born else "", "died": died.group(1) if died else "",
                    "cemetery": _clean(cem.group(1)) if cem else "",
                    "sector": loc["Sektor"], "row": loc["Rząd"], "grave": loc["Nr grobu"]})
    return out


def search(host, surname, first=""):
    q = {"nazwisko": surname}
    if first:
        q["imie"] = first
    base = f"https://{host}/wyszukiwarka/wyniki?"
    h = _net.get(base + urllib.parse.urlencode(q), timeout=40)
    m = re.search(r"znaleziono\s*<strong>\s*(\d+)", h)
    total = int(m.group(1)) if m else 0
    rows = _items(h)
    pages = sorted({int(x) for x in re.findall(r"ppstrona=(\d+)", h)})
    last = max(pages) if pages else 1
    for p in range(2, min(last, MAX_PAGES) + 1):
        rows += _items(_net.get(base + urllib.parse.urlencode(dict(q, ppstrona=p)), timeout=40))
    seen = set()
    rows = [r for r in rows if not (r["id"] in seen or seen.add(r["id"]))]
    return total, rows


def grave(host, person_id):
    """Everyone in the grave: [(name, born, died)]."""
    h = _net.get(f"https://{host}/osoba/{person_id}?inni=1", timeout=40)
    i = h.find("Wszyscy pochowani w tym grobie")
    if i < 0:
        return []
    out = []
    for tr in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", h[i:i + 20000]):
        cells = [_clean(c) for c in re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", tr)]
        if len(cells) >= 3 and cells[0] and cells[0] != "Imię":
            name = " ".join(x for x in cells[:2] if x)
            out.append((name, cells[2] if len(cells) > 3 else "", cells[3] if len(cells) > 3 else cells[2]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", required=True, help="<town>.grobonet.com, as shown on grobonet.com")
    ap.add_argument("--grave", help="person id from a result row")
    ap.add_argument("--first", default="")
    ap.add_argument("surnames", nargs="*")
    o = ap.parse_args(argv)
    if o.grave:
        for name, born, died in grave(o.host, o.grave):
            print(f"  {name:<34} b. {born or '?':<12} d. {died or '?'}")
        return 0
    if not o.surnames:
        ap.error("give a surname or --grave")
    for sn in o.surnames:
        total, rows = search(o.host, sn, o.first)
        print(f"\n=== {sn} -> {total} in the database, read {len(rows)} ===")
        rows.sort(key=lambda r: (r["cemetery"], r["sector"], r["row"], r["grave"], r["born"] or "9999"))
        last = None
        for r in rows:
            g = (r["cemetery"], r["sector"], r["row"], r["grave"])
            if g != last:
                print(f"  -- {r['cemetery']} sector {r['sector']} row {r['row']} grave {r['grave']}")
                last = g
            print(f"     {r['name']:<32} b. {r['born'] or '?':<11} d. {r['died'] or '?':<11} id={r['id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
