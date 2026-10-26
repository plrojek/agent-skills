#!/usr/bin/env python3
"""Geneteka client (geneteka.genealodzy.pl, run by PTG volunteers).

  geneteka.py parishes <woj> [--grep TEXT]
      rid per record type and indexed years for every parish in a province
  geneteka.py search <woj> <B|S|D> <surname> [--name X] [--rid N] [--from Y] [--to Y]
                     [--max-rows 1000] [--json out.json] [--links] [--no-cache]
  geneteka.py check <woj> <B|S|D> <rid> <surname> <expected_total>
      control query: run a search whose answer you already know

B = births, S = marriages, D = deaths. Province codes: see references/sources.md.

Every record type of a parish has its OWN rid (data-b / data-s / data-d). A wrong rid does
not fail: it returns another table under misleading headers. Take rids from `parishes`.
Without --rid the search covers the whole province.

The API returns at most 50 rows per call; the script pages through, one call per second.
If the answer looks like Geneteka's pooled "Archiwum" fallback (see sanity()), the script
stops paging, does not cache it, and prints why the rows must be discarded.
"""
import argparse
import html
import json
import re
import sys
import urllib.parse
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _net  # noqa: E402

BASE = "https://geneteka.genealodzy.pl"
POOLED_TOTAL = 3000   # no sensible single-parish or rare-surname query has more

WOJ = {"01ds": "dolnośląskie", "02kp": "kujawsko-pomorskie", "03lb": "lubelskie",
       "04ls": "lubuskie", "05ld": "łódzkie", "06mp": "małopolskie", "07mz": "mazowieckie",
       "71wa": "Warszawa", "08op": "opolskie", "09pk": "podkarpackie", "10pl": "podlaskie",
       "11pm": "pomorskie", "12sl": "śląskie", "13sk": "świętokrzyskie",
       "14wm": "warmińsko-mazurskie", "15wp": "wielkopolskie", "16zp": "zachodniopomorskie",
       "21uk": "Ukraine", "22br": "Belarus", "23lt": "Lithuania", "25po": "other"}

# Column meaning per record type. The remarks are in the LAST column, not the 9th:
# spouse, widowhood and the exact date live there. Index-only parishes leave most empty.
COLS = {
    "B": ["year", "act", "given", "surname", "father", "mother", "mother_surname",
          "parish", "place", "remarks"],
    "S": ["year", "act", "groom_given", "groom_surname", "groom_parents",
          "bride_given", "bride_surname", "bride_parents", "parish", "remarks"],
    "D": ["year", "act", "given", "surname", "father", "mother", "mother_or_spouse_surname",
          "parish", "place", "remarks"],
}
_SKIP_TIPS = ("Indeks dodał", "Miejsce przechowywania", "Zgłoś")


def strip(cell):
    """Visible text of a cell; when empty, the joined title= tooltips (that is where
    the remarks are). Tooltips about the indexer, the archive and the fix link are dropped."""
    if cell is None:
        return ""
    s = cell if isinstance(cell, str) else str(cell)
    tips = re.findall(r'title="([^"]*)"', s)
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"(?is)<[^>]+>", " ", s))).strip()
    if not t and tips:
        t = " ~ ".join(html.unescape(x).replace("&#013;", " ").strip() for x in tips
                       if x and not any(k in html.unescape(x) for k in _SKIP_TIPS))
        t = re.sub(r"\s+", " ", t).strip()
    return t


def links(raw_row):
    """Links to scans hidden in the raw cells. strip() deletes them with the tags,
    so look here when a record matters."""
    out = []
    for c in raw_row:
        for href in re.findall(r'href="([^"]+)"', str(c)):
            href = html.unescape(href)
            if "user.php" in href or "fix.php" in href or href.startswith("mailto:"):
                continue                       # indexer profile, "report a fix"
            u = urllib.parse.urlsplit(href)
            if u.netloc and u.path in ("", "/"):
                continue                       # an archive's home page
            out.append(href)
    return list(dict.fromkeys(out))


def parishes(woj):
    s = _net.get(f"{BASE}/index.php?op=gt&lang=pol&bdm=B&w={woj}&rid=B")
    out = {}
    for m in re.finditer(r'<option\s+value="(\d+)"\s+data-b="([^"]*)"\s+data-s="([^"]*)"'
                         r'\s+data-d="([^"]*)"\s+data-years="([^"]*)"\s*>([^<]*)', s):
        _, b, sr, dr, yrs, name = m.groups()
        out[html.unescape(name).strip()] = {"B": b or None, "S": sr or None, "D": dr or None,
                                            "years": html.unescape(yrs).strip()}
    return out


def _fetch(params, use_cache=True):
    url = BASE + "/api/getAct.php?" + urllib.parse.urlencode(params)
    if use_cache:
        hit = _net.cache_get(url)
        if hit is not None:
            return hit
    d = json.loads(_net.get(url, headers={"X-Requested-With": "XMLHttpRequest",
                                          "Referer": BASE + "/index.php"}))
    if use_cache and not sanity_reasons(d, params.get("search_lastname", ""), params.get("rid")):
        _net.cache_put(url, d)
    return d


def search(woj, bdm, lastname="", name="", rid=None, frm="", to="", exact=True,
           max_rows=1000, use_cache=True):
    """Returns (total, rows, raw_rows, problems). rows are stripped text cells."""
    rid = rid or bdm
    raw, start, total, problems = [], 0, 0, []
    while True:
        p = {"op": "gt", "lang": "pol", "bdm": bdm, "w": woj, "rid": rid,
             "search_lastname": lastname, "search_name": name,
             "search_lastname2": "", "search_name2": "",
             "from_date": frm, "to_date": to, "draw": 1, "start": start, "length": 50}
        if exact:
            p["exac"] = 1
        d = _fetch(p, use_cache)
        batch = d.get("data") or []
        total = int(d.get("recordsTotal") or 0)
        if start == 0:
            problems = sanity_reasons(d, lastname, rid)
            if problems:
                raw = batch
                break
        if not batch:
            break
        raw += batch
        start += len(batch)
        if start >= total or len(raw) >= max_rows:
            break
    return total, [[strip(c) for c in r] for r in raw], raw, problems


def sanity_reasons(d, lastname, rid=None):
    """Why this answer is NOT a real result. Empty list = looks real.

    Geneteka answers some requests with a pooled "Archiwum" dataset: tens of thousands
    of rows from unrelated parishes, filters ignored, and an empty "parishes" list.
    Two known causes: a defective rid for one parish, or your network address being
    flagged after heavy automated use (then even a browser on that network gets it).
    """
    reasons = []
    rows = d.get("data") or []
    total = int(d.get("recordsTotal") or 0)
    if total > POOLED_TOTAL:
        reasons.append(f"{total} rows: more than any real query returns")
    if rows and not d.get("parishes"):
        reasons.append("the answer names no parish")
    if rid and str(rid).isdigit() and d.get("parishes"):
        ids = {str(p[0]) for v in d["parishes"].values() for p in v} if isinstance(
            d["parishes"], dict) else set()
        if ids and str(rid) not in ids:
            reasons.append(f"the answer is for parish ids {sorted(ids)[:5]}, not {rid}")
    if lastname and rows:
        want = _net.norm(lastname)[:5]
        if not any(want in _net.norm(strip(c)) for r in rows[:60] for c in r):
            reasons.append(f"no row contains the surname '{lastname}'")
    return reasons


def warn(problems):
    if problems:
        print("\n  DISCARD THESE ROWS - this is not a real answer:", file=sys.stderr)
        for p in problems:
            print("   - " + p, file=sys.stderr)
        print("  Re-run a control query (`check`). If that is also bad, your network is likely\n"
              "  flagged: stop, try another network or another day. Do not retry in a loop.\n",
              file=sys.stderr)


def show(total, rows, bdm, label=""):
    print(f"\n### {label}  [{bdm}] -> {total}" + (f" (showing {len(rows)})" if len(rows) < total else ""))
    cols = COLS.get(bdm, [])
    for r in rows:
        print("  - " + " | ".join(f"{cols[i] if i < len(cols) else i}={c}"
                                  for i, c in enumerate(r) if c))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("parishes")
    a.add_argument("woj")
    a.add_argument("--grep", default="")
    s = sub.add_parser("search")
    s.add_argument("woj")
    s.add_argument("bdm", choices=["B", "S", "D"])
    s.add_argument("surname")
    s.add_argument("--name", default="")
    s.add_argument("--rid")
    s.add_argument("--from", dest="frm", default="")
    s.add_argument("--to", default="")
    s.add_argument("--loose", action="store_true", help="drop the exact-match flag")
    s.add_argument("--max-rows", type=int, default=1000)
    s.add_argument("--json", help="also write the rows to this file (input for crossmatch.py)")
    s.add_argument("--links", action="store_true", help="print scan links found in raw cells")
    s.add_argument("--no-cache", action="store_true")
    c = sub.add_parser("check")
    for k in ("woj", "bdm", "rid", "surname"):
        c.add_argument(k)
    c.add_argument("expected", type=int)
    o = ap.parse_args(argv)

    if o.cmd == "parishes":
        for nm, v in sorted(parishes(o.woj).items()):
            if o.grep.lower() in nm.lower():
                print(f"{nm:52s} B={v['B'] or '-':>6} S={v['S'] or '-':>6} D={v['D'] or '-':>6}  {v['years']}")
        return 0

    if o.cmd == "check":
        total, rows, _, problems = search(o.woj, o.bdm, o.surname, rid=o.rid, max_rows=50,
                                          use_cache=False)
        ok = not problems and total == o.expected
        print(f"control query: expected {o.expected}, got {total} -> {'OK' if ok else 'NOT OK'}")
        warn(problems)
        return 0 if ok else 1

    total, rows, raw, problems = search(o.woj, o.bdm, o.surname, o.name, o.rid, o.frm, o.to,
                                        not o.loose, o.max_rows, not o.no_cache)
    warn(problems)
    if problems:
        return 2
    show(total, rows, o.bdm, f"{o.surname} {o.name} in {WOJ.get(o.woj, o.woj)}".replace("  ", " "))
    if o.links:
        for r, rr in zip(rows, raw):
            for href in links(rr):
                print(f"  scan: {r[0]} act {r[1]} {r[2]} {r[3]} -> {href}")
    if o.json:
        with open(o.json, "w", encoding="utf-8") as f:
            json.dump({"woj": o.woj, "bdm": o.bdm, "rid": o.rid, "surname": o.surname,
                       "total": total, "columns": COLS[o.bdm], "rows": rows,
                       "links": [links(rr) for rr in raw]}, f, ensure_ascii=False, indent=1)
        print(f"\nwrote {len(rows)} rows to {o.json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
