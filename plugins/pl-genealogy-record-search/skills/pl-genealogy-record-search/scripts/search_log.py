#!/usr/bin/env python3
"""Research log: every search with its result, nothing-found included, and per-book notes.

  search_log.py check [--source S] [--where W] [--surname X] [--years A-B]
      earlier searches that overlap this one; run it before searching
  search_log.py add --source S --where W --surname X --result R
                    [--type B|S|D|...] [--given G] [--years A-B] [--pages P] [--count N]
                    [--note TEXT] [--ref SIGNATURE-OR-URL]
      record a search done by hand: a book read page by page, a browser search
  search_log.py list [--last N] [--source S]
  search_log.py lesson add --book B TEXT      a quirk of one book (calibration, two years
  search_log.py lesson list [--book B]        per page, a hand that writes 7 like 1)
  search_log.py calibrate --book B --page P --scan N
      a measured page -> scan pair (read off the image, never guessed)
  search_log.py where --book B --page P
      which scan a page is on, from the measured pairs

R is one of: found, negative, partial, inconclusive. "negative" means the search ran and
covered what it says and nothing matched; an answer that can't be trusted (Geneteka's
pooled fallback, a site that was down) is "inconclusive", never "negative".

The log is one JSON object per line. Location: GENEALOGY_LOG, else
~/.local/share/pl-genealogy-record-search/searches.jsonl. Keep it next to the research
notes (set GENEALOGY_LOG), and out of public repositories: it holds the surnames searched.
geneteka.py and sweep_all.py append to it on their own; every write prints the path.
"""
import argparse
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _net  # noqa: E402

RESULTS = ("found", "negative", "partial", "inconclusive")
STALE_DAYS = 180


def log_path():
    p = os.environ.get("GENEALOGY_LOG")
    if p:
        return os.path.abspath(os.path.expanduser(p))
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, "pl-genealogy-record-search", "searches.jsonl")


def _today():
    return datetime.date.today().isoformat()


def append(entry, quiet=False):
    """Append one entry; returns the log path."""
    p = log_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    entry = {"date": _today(), **entry}
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    if not quiet:
        print(f"  logged to {p}", file=sys.stderr)
    return p


def record(source, where, surname, result, rtype="", given="", years="", pages="",
           count=None, note="", ref="", query=None, by=None, quiet=False):
    if result not in RESULTS:
        raise ValueError(f"result must be one of {', '.join(RESULTS)}")
    e = {"kind": "search", "source": source, "where": where, "type": rtype,
         "surname": surname, "given": given, "years": years, "pages": pages,
         "result": result, "count": count, "note": note, "ref": ref}
    if query:
        e["query"] = query
    if by:
        e["by"] = by
    return append({k: v for k, v in e.items() if v not in ("", None)}, quiet=quiet)


def entries(kind=None):
    p = log_path()
    if not os.path.exists(p):
        return []
    out = []
    with open(p, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except ValueError:
                print(f"  ! {p}:{i} is not JSON, skipped", file=sys.stderr)
                continue
            if kind is None or e.get("kind") == kind:
                out.append(e)
    return out


def years_range(s):
    """'1850-1870' -> (1850, 1870); '1850' -> (1850, 1850); '' -> None."""
    ys = [int(y) for y in re.findall(r"\d{4}", s or "")]
    return (min(ys), max(ys)) if ys else None


def _overlap(a, b):
    ra, rb = years_range(a), years_range(b)
    return ra is None or rb is None or (ra[0] <= rb[1] and rb[0] <= ra[1])


def _has(hay, needle):
    return not needle or _net.norm(needle) in _net.norm(hay or "")


def matching(source=None, where=None, surname=None, years=None):
    return [e for e in entries("search")
            if _has(e.get("source"), source) and _has(e.get("where"), where)
            and _has(e.get("surname"), surname) and _overlap(e.get("years"), years)]


def _age_days(e):
    try:
        return (datetime.date.today() - datetime.date.fromisoformat(e["date"][:10])).days
    except (KeyError, ValueError):
        return 0


def describe(e):
    bits = [e.get("date", "?"), e.get("source", "?"), e.get("where", "")]
    if e.get("type"):
        bits.append(f"[{e['type']}]")
    bits.append(" ".join(x for x in (e.get("given"), e.get("surname")) if x))
    if e.get("years"):
        bits.append(e["years"])
    if e.get("pages"):
        bits.append(f"pages {e['pages']}")
    res = e.get("result", "?") + (f" ({e['count']})" if e.get("count") is not None else "")
    return "  ".join(b for b in bits if b) + "  -> " + res


def check_report(source=None, where=None, surname=None, years=None):
    hits = matching(source, where, surname, years)
    if not hits:
        return "no earlier search in the log overlaps this one (" + log_path() + ")"
    lines = [f"{len(hits)} earlier search(es) overlap this one:"]
    for e in sorted(hits, key=lambda x: x.get("date", "")):
        lines.append("  " + describe(e))
        if e.get("note"):
            lines.append("      note: " + e["note"])
        if e.get("result") == "negative":
            if e.get("source") == "geneteka":
                lines.append("      a Geneteka zero covers only the years that index has "
                             "(geneteka.py parishes) and only this spelling")
            if _age_days(e) > STALE_DAYS:
                lines.append(f"      older than {STALE_DAYS} days: the source may have grown since")
        if e.get("result") == "inconclusive":
            lines.append("      inconclusive: this does not count as searched")
    return "\n".join(lines)


def _book_key(b):
    return re.sub(r"\s+", " ", _net.norm(b)).strip()


def lessons(book=None):
    return [e for e in entries("lesson") if not book or _book_key(book) in _book_key(e.get("book", ""))]


def calibration(book):
    pts = {}
    for e in entries("calib"):
        if _book_key(e.get("book", "")) == _book_key(book):
            pts[int(e["page"])] = int(e["scan"])      # a later measurement of a page wins
    return sorted(pts.items())


def where_is(book, page):
    """(scan, how) for a page of a book, from the measured page -> scan pairs."""
    pts = calibration(book)
    if not pts:
        return None, "no measured page -> scan pair for this book; measure one (calibrate)"
    for p, s in pts:
        if p == page:
            return s, "measured"
    if len(pts) == 1:
        p, s = pts[0]
        return s + (page - p), f"one measured pair (page {p} = scan {s}); assumes one page per scan"
    below = [x for x in pts if x[0] < page]
    above = [x for x in pts if x[0] > page]
    a, b = (below[-1], above[0]) if below and above else (pts[-2], pts[-1]) if below else (pts[0], pts[1])
    slope = (b[1] - a[1]) / (b[0] - a[0])
    return round(a[1] + (page - a[0]) * slope), (f"between measured pairs {a[0]}={a[1]} and {b[0]}={b[1]}"
                                                 f" ({slope:g} scans per page); check one scan either side")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    a = sub.add_parser("add")
    for p in (c, a):
        p.add_argument("--source")
        p.add_argument("--where")
        p.add_argument("--surname")
        p.add_argument("--years")
    a.add_argument("--result", required=True, choices=RESULTS)
    a.add_argument("--type", default="")
    a.add_argument("--given", default="")
    a.add_argument("--pages", default="")
    a.add_argument("--count", type=int)
    a.add_argument("--note", default="")
    a.add_argument("--ref", default="")
    li = sub.add_parser("list")
    li.add_argument("--last", type=int, default=30)
    li.add_argument("--source")
    le = sub.add_parser("lesson")
    le.add_argument("action", choices=["add", "list"])
    le.add_argument("text", nargs="*")
    le.add_argument("--book")
    ca = sub.add_parser("calibrate")
    ca.add_argument("--book", required=True)
    ca.add_argument("--page", type=int, required=True)
    ca.add_argument("--scan", type=int, required=True)
    wh = sub.add_parser("where")
    wh.add_argument("--book", required=True)
    wh.add_argument("--page", type=int, required=True)
    o = ap.parse_args(argv)

    if o.cmd == "check":
        print(check_report(o.source, o.where, o.surname, o.years))
    elif o.cmd == "add":
        for k in ("source", "where", "surname"):
            if not getattr(o, k):
                ap.error(f"add needs --{k}")
        record(o.source, o.where, o.surname, o.result, o.type, o.given, o.years or "", o.pages,
               o.count, o.note, o.ref, by="hand")
    elif o.cmd == "list":
        es = [e for e in entries("search") if _has(e.get("source"), o.source)]
        for e in es[-o.last:]:
            print(describe(e))
        print(f"({len(es)} searches in {log_path()})", file=sys.stderr)
    elif o.cmd == "lesson":
        if o.action == "add":
            if not o.book or not o.text:
                ap.error("lesson add --book B TEXT")
            append({"kind": "lesson", "book": o.book, "text": " ".join(o.text)})
        else:
            for e in lessons(o.book):
                print(f"{e.get('date', '?')}  {e.get('book')}\n    {e.get('text')}")
            for e in ([] if not o.book else calibration(o.book)):
                print(f"    calibration: page {e[0]} = scan {e[1]}")
    elif o.cmd == "calibrate":
        append({"kind": "calib", "book": o.book, "page": o.page, "scan": o.scan})
    elif o.cmd == "where":
        scan, how = where_is(o.book, o.page)
        print(f"page {o.page}: " + (f"scan {scan}  ({how})" if scan is not None else how))
        return 0 if scan is not None else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
