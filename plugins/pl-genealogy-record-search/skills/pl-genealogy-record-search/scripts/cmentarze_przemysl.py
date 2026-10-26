#!/usr/bin/env python3
"""Municipal cemeteries of Przemyśl (cmentarzeprzemysl.pl): Główny, Zasanie, Wojskowy,
Przekopana, Kruhel Mały. Reads every result page and every grave card, because the
birth date is only on the card.

  cmentarze_przemysl.py <Surname> [Surname2 ...] [--first NAME]
  cmentarze_przemysl.py <Surname> --maiden     match the surname anywhere in the field
  cmentarze_przemysl.py --born 1901-05-17      by birth date, no surname needed
  cmentarze_przemysl.py --died 1975 --surname-from 1930 ...

What has to be right, or you get nothing or half an answer:
  * the endpoint is pages/find2.php and it needs search=Szukaj
  * results are paged (page=N); reading page 1 alone silently truncates
  * the birth date and the grave-fee date are only on pages/mapa.php?c=<cemetery>&id=<id>
  * the surname filter is LIKE '<input>%', so it matches from the START of the field.
    A married woman is often "HUSBAND'S-SURNAME Z D. MAIDEN" or "... Z <MAIDEN>ÓW";
    --maiden prefixes % so "%MAIDEN" finds her. Expect substring noise.
    The maiden name is sometimes in the GIVEN-name field instead ("JÓZEFA Z D. X").
    That field takes wildcards too, but only together with a surname:
    `<MarriedSurname> --first "%X%"`.
  * women are filed under the female form of the husband's surname: ask for both forms.

The site's TLS certificate is issued for another host name, so this script (and only for
this host) skips certificate verification. Nothing is sent but the search terms.
"""
import argparse
import os
import re
import sys
import urllib.parse
import html

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _net  # noqa: E402

B = "https://cmentarzeprzemysl.pl/pages/"
CEMETERY = {"1": "Główny", "2": "Zasanie", "3": "Wojskowy", "4": "Przekopana", "5": "Kruhel Mały"}
MAX_PAGES = 40


def _get(url):
    return _net.get(url, timeout=45, verify=False)


def _lines(h):
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h)
    t = re.sub(r"(?is)<[^>]+>", "\n", t)
    return [x for x in (re.sub(r"\s+", " ", html.unescape(y)).strip() for y in t.split("\n")) if x]


def ids(surname="", first="", born="", died="", year_from="", year_to=""):
    """All (cemetery, id) pairs for a query, across every result page."""
    out, page = [], 1
    while page <= MAX_PAGES:
        q = urllib.parse.urlencode({"nazwisko": surname, "imie": first, "data_ur": born,
                                    "data_zg": died, "rok_od": year_from, "rok_do": year_to,
                                    "search": "Szukaj", "page": page, "c": ""})
        h = _get(B + "find2.php?" + q)
        found = re.findall(r"mapa\.php\?c=(\d+)&(?:amp;)?id=(\d+)", h)
        new = [x for x in dict.fromkeys(found) if x not in out]
        if not new:
            break
        out += new
        if f"page={page + 1}" not in h.replace("&amp;", "&"):
            break
        page += 1
    return out


def grave(c, i):
    lines = _lines(_get(f"{B}mapa.php?c={c}&id={i}"))
    labels = {"Nazwisko", "Imię", "Kwatera", "Rząd", "Nr grobu", "Data urodzenia",
              "Data zgonu", "Opłata grobu"}

    def after(label):
        try:
            v = lines[lines.index(label) + 1]
        except (ValueError, IndexError):
            return ""
        return "" if v in labels else v     # empty field: the next label follows directly
    return {"surname": after("Nazwisko"), "given": after("Imię"), "section": after("Kwatera"),
            "row": after("Rząd"), "grave": after("Nr grobu"), "born": after("Data urodzenia"),
            "died": after("Data zgonu"), "fee_until": after("Opłata grobu"),
            "cemetery": CEMETERY.get(c, c), "url": f"{B}mapa.php?c={c}&id={i}"}


def people(surnames, **kw):
    pairs = []
    for s in surnames or [""]:
        pairs += ids(s, **kw)
    return [g for g in (grave(c, i) for c, i in dict.fromkeys(pairs)) if g["surname"]]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("surnames", nargs="*")
    ap.add_argument("--first", default="")
    ap.add_argument("--maiden", action="store_true", help="match the surname anywhere (prefix %%)")
    ap.add_argument("--born", default="", help="YYYY-MM-DD")
    ap.add_argument("--died", default="", help="YYYY-MM-DD")
    ap.add_argument("--year-from", default="")
    ap.add_argument("--year-to", default="")
    o = ap.parse_args(argv)
    if not (o.surnames or o.born or o.died):
        ap.error("give a surname, --born or --died")
    names = ["%" + s for s in o.surnames] if o.maiden else o.surnames
    rs = people(names, first=o.first, born=o.born, died=o.died,
                year_from=o.year_from, year_to=o.year_to)
    for r in sorted(rs, key=lambda x: (x["cemetery"], x["section"], x["row"], x["grave"], x["born"] or "9999")):
        print(f"  {r['given']:<22}{r['surname']:<26} b. {r['born'] or '?':<11} d. {r['died'] or '?':<11} "
              f"{r['cemetery']} {r['section']}/{r['row']}/{r['grave']}  fee to {r['fee_until'] or '?'}")
    print(f"\n{len(rs)} burials. Same cemetery/section/row/grave = one grave, usually one family.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
