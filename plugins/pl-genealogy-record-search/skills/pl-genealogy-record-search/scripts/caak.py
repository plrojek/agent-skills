#!/usr/bin/env python3
"""Pages from IIIF-based diocesan archives; written for CAAK, the Kraków archdiocese
archive (caak.upjp2.edu.pl). Geneteka records sometimes link straight into it.

  caak.py pages <record-id>                          list of pages (index, name)
  caak.py page  <record-id> <out-dir> <i> [<i> ...]  whole page (at most ~2578x3882)
  caak.py crop  <record-id> <out-dir> <i> x y w h    a REGION at full resolution

The server caps an image at 10 million pixels, so a whole page comes down at about a
quarter of its real size (originals run ~9434x14204). Small handwriting can only be read
from a region: `crop` asks for /x,y,w,h/max/, which returns that area at native size.
The year is printed in the table header of every page, so a contact sheet of the top
strips of a dozen pages finds a year faster than paging through the viewer.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _net  # noqa: E402

HOST = "https://caak.upjp2.edu.pl"
MAX_AREA = 10_000_000


def record(recid):
    """Metadata and page list from the Next.js __NEXT_DATA__ blob."""
    t = _net.get(f"{HOST}/j/{recid}/s/0/f")
    m = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', t, re.S)
    if not m:
        raise SystemExit("no __NEXT_DATA__ on the page: the site has changed")
    return json.loads(m.group(1))["props"]["pageProps"]["record"]


def fetch(path, region, size, out, name):
    url = f"{HOST}/iiif/3/{path}/{region}/{size}/0/default.jpg"
    d = _net.get(url, headers={"Referer": HOST + "/"}, timeout=120, raw=True)
    fn = os.path.join(out, name)
    with open(fn, "wb") as f:
        f.write(d)
    return fn, len(d)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["pages", "page", "crop"])
    ap.add_argument("recid")
    ap.add_argument("rest", nargs="*")
    o = ap.parse_args(argv)
    r = record(o.recid)
    pg = r["pages"]
    if o.cmd == "pages":
        print(f"{r.get('tytul', '?')} | {(r.get('lokalizacja') or {}).get('name', '?')} | {len(pg)} pages")
        for i, p in enumerate(pg):
            print(f"{i:4d}  {p['name']}")
        return 0
    if not o.rest:
        ap.error("missing <out-dir>")
    out = o.rest[0]
    os.makedirs(out, exist_ok=True)
    if o.cmd == "page":
        for a in o.rest[1:]:
            i = int(a)
            fn, n = fetch(pg[i]["path"], "full", "2359,", out, f"{i:03d}_{pg[i]['name']}")
            print(f"{i:3d} {pg[i]['name']:<26} {n:>8} B")
        return 0
    if len(o.rest) != 6:
        ap.error("crop <record-id> <out-dir> <i> x y w h")
    i, x, y, w, h = (int(v) for v in o.rest[1:6])
    if w * h > MAX_AREA:
        ap.error(f"region {w}x{h} = {w * h / 1e6:.1f} M px, over the server's 10 M px cap")
    fn, n = fetch(pg[i]["path"], f"{x},{y},{w},{h}", "max", out, f"{i:03d}_{x}-{y}-{w}-{h}.jpg")
    print(f"{fn}  {n} B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
