#!/usr/bin/env python3
"""Download parish-book scans from PTG's two scan hosts:
skanoteka.genealodzy.pl (whole archive fonds) and metryki.genealodzy.pl.

  skanoteka.py units <fond-id>                               (skanoteka only)
      the volumes (units) of a fond: number, signature, title, scan count, link
  skanoteka.py files <id> <sy> [--kt N] [--site metryki]
      file names in a volume
  skanoteka.py get <id> <sy> <out-dir> <file> [<file> ...] [--kt N] [--site metryki]
      download; <file> is a number (7 -> 007.jpg) or a name as listed (031-032)

`id`, `sy` and `kt` come from the viewer URL: .../id<ID>-sy<SY>-kt<KT>. On metryki,
kt1 = births, kt2 = marriages, kt3 = deaths, and each kt has its own image credentials.

The image URL is not in an <img src>: the viewer page builds it in JavaScript as
https://metbox<N>.genealodzy.pl/metryka_get.php?dir=<dir>&znak=<znak>&plik=NNN.jpg
`dir` and `znak` are constant for one volume (and one kt), so they are read once.
On metryki the FILE NAME often encodes ACT numbers, not pages: 026.jpg can be act 26,
031-032.jpg a page with acts 31-32. Download one from the middle and count before guessing.
The image host throws 502s and truncates downloads; every file is retried.
"""
import argparse
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _net  # noqa: E402

SITES = {"skanoteka": "https://skanoteka.genealodzy.pl", "metryki": "https://metryki.genealodzy.pl"}
MIN_JPEG = 30_000      # placeholders and error pages are smaller than any real scan


def units(fond):
    t = _net.get(f"{SITES['skanoteka']}/id{fond}")
    out = []
    for r in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", t):
        cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
                 for c in re.findall(r"(?is)<td[^>]*>(.*?)</td>", r)]
        m = re.search(r'href="?(id\d+-sy\d+[^"\s>]*)"?', r)
        if m and len(cells) >= 3:
            out.append(tuple(cells[:4]) + (m.group(1),))
    return out


def files(site, idz, sy, kt=1):
    base = SITES[site]
    t = _net.get(f"{base}/id{idz}-sy{sy}-kt{kt}")
    return list(dict.fromkeys(re.findall(r"plik=([0-9][0-9\-]*)\.jpg", t)))


def creds(site, idz, sy, kt=1, first=None):
    """(host, dir, znak) for one volume and kt. Tries the first listed file, then 000, 001."""
    base = SITES[site]
    tried = [first] if first else []
    tried += [x for x in ("000", "001") if x not in tried]
    for plik in tried:
        u = f"{base}/index.php?op=pg&id={idz}&sy={sy}&kt={kt}&plik={plik}.jpg"
        try:
            t = _net.get(u, headers={"Referer": f"{base}/id{idz}-sy{sy}-kt{kt}"}, tries=4)
        except Exception:
            continue
        m = re.search(r"(metbox\d*\.genealodzy\.pl)/metryka_get\.php"
                      r"\?dir=([^&]+)&(?:amp;)?znak=([^&]+)&", t)
        if m:
            return m.group(1), html.unescape(m.group(2)), html.unescape(m.group(3))
    raise SystemExit("could not read dir/znak from the viewer page; open it in a browser to check")


def grab(site, host, dirv, znak, name, out):
    fn = os.path.join(out, name + ".jpg")
    if os.path.exists(fn) and os.path.getsize(fn) > MIN_JPEG:
        return fn, os.path.getsize(fn)
    src = f"https://{host}/metryka_get.php?dir={dirv}&znak={znak}&plik={name}.jpg"
    for _ in range(3):
        try:
            d = _net.get(src, headers={"Referer": SITES[site] + "/"}, timeout=180, tries=3, raw=True)
        except Exception:
            continue
        if len(d) > MIN_JPEG and d[:3] == b"\xff\xd8\xff":
            with open(fn, "wb") as f:
                f.write(d)
            return fn, len(d)
    return None, 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["units", "files", "get"])
    ap.add_argument("args", nargs="+")
    ap.add_argument("--kt", type=int, default=1)
    ap.add_argument("--site", choices=list(SITES), default="skanoteka")
    o = ap.parse_args(argv)
    if o.cmd == "units":
        for row in units(o.args[0]):
            print(" | ".join(str(x) for x in row))
        return 0
    if o.cmd == "files":
        print(" ".join(files(o.site, o.args[0], o.args[1], o.kt)))
        return 0
    if len(o.args) < 4:
        ap.error("get <id> <sy> <out-dir> <file> [...]")
    idz, sy, out, wanted = o.args[0], o.args[1], o.args[2], o.args[3:]
    os.makedirs(out, exist_ok=True)
    names = [f"{int(w):03d}" if w.isdigit() else w for w in wanted]
    host, dirv, znak = creds(o.site, idz, sy, o.kt, names[0])
    bad = []
    for n in names:
        fn, size = grab(o.site, host, dirv, znak, n, out)
        print(f"{n}.jpg  {size:>9} B" if fn else f"{n}.jpg  FAILED")
        if not fn:
            bad.append(n)
    if bad:
        listed = files(o.site, idz, sy, o.kt)
        missing = [n for n in bad if n not in listed]
        if missing and listed:
            print(f"\n{', '.join(missing)} not in this volume. Its files are named: "
                  f"{' '.join(sorted(listed)[:12])} ... (run `files`)", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
