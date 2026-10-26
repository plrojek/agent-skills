#!/usr/bin/env python3
"""Indeks Represjonowanych (indeksrepresjonowanych.pl): Poles repressed by the USSR,
mostly the 1940-41 deportations, with their later fate (Anders' Army, return, death).

  indeks_repr.py surname <Surname> [Given] [--max 300] [--no-cards]
  indeks_repr.py place <Village>   [--max 300] [--no-cards]
      the useful mode: the WHOLE transport from one village

`place` searches search[repression_place] with exact_repression_place=1, which on this
site means "contains the text", not "exactly". It brings up relatives whose surname you
don't know yet, and the neighbours who explain later marriages.

On each card read the questionnaire number (IR/<n>/<position>) when present. Positions in
one questionnaire are one household: father, mother, then children oldest first. GAPS in
the numbering are family members who were not published, often the answer you need.
Originals are in Archiwum IPN; cite the signature on the card when you order them.
"""
import argparse
import html
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _net  # noqa: E402

B = "https://indeksrepresjonowanych.pl"


def _text_lines(s):
    s = re.sub(r"(?is)<(script|style|nav|header|footer|form)\b.*?</\1>", "", s)
    lines = [re.sub(r"\s+", " ", y).strip()
             for y in html.unescape(re.sub(r"(?is)<[^>]+>", "\n", s)).split("\n")]
    return [y for y in lines if y]


def query(max_rows=300, **fields):
    """Returns (total, [(uuid, row_text)]). Pages through search[start]=1,2,..."""
    p = {f"search[{k}]": v for k, v in fields.items() if v}
    p["search[limit]"] = "100"
    rows, total, page = [], None, 1
    while len(rows) < max_rows:
        p["search[start]"] = str(page)
        s = _net.get(B + "/wyniki?" + urllib.parse.urlencode(p), timeout=45)
        if total is None:
            m = re.search(r"Liczba wyszukanych rekordów:\s*(\d+)", html.unescape(s))
            total = int(m.group(1)) if m else 0
        new = []
        for tr in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", s):
            uid = re.findall(r"szczegoly/([0-9a-f-]{20,})", tr)
            if uid:
                t = re.sub(r"\s+", " ", html.unescape(re.sub(r"(?is)<[^>]+>", " ", tr))).strip()
                new.append((uid[0], t))
        new = [r for r in new if r[0] not in {x[0] for x in rows}]
        if not new:
            break
        rows += new
        if len(rows) >= total:
            break
        page += 1
    return total or 0, rows[:max_rows]


def card(uid):
    """The card as text from the name down to the source signatures."""
    lines = _text_lines(_net.get(f"{B}/szczegoly/{uid}", timeout=45))
    try:
        i = lines.index("Imię:")
    except ValueError:
        return ""
    end = next((j for j in range(i, len(lines)) if lines[j] in ("Wstecz", "Drukuj")), len(lines))
    return " | ".join(lines[max(0, i - 1):end])


def summary(card_text):
    fates = list(dict.fromkeys(re.findall(
        r"(Deportacja|Zesłanie|Aresztowanie|Więzienie|Łagier|Armia Polska[^|]*|Anders[^|]*|"
        r"Repatriacja|Zwolnienie|Śmierć|Zgon)", card_text)))
    q = re.search(r"IR/\s*/?\s*(\d+)(?:\s*/\s*(\d+))?", card_text)
    return fates, (q.group(0).replace(" ", "") if q else "")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["surname", "place"])
    ap.add_argument("value")
    ap.add_argument("given", nargs="?", default="")
    ap.add_argument("--max", type=int, default=300)
    ap.add_argument("--no-cards", action="store_true", help="list only, skip opening each card")
    o = ap.parse_args(argv)
    if o.mode == "surname":
        total, rows = query(o.max, last_name=o.value, exact_last_name="1", name=o.given)
    else:
        total, rows = query(o.max, repression_place=o.value, exact_repression_place="1")
    print(f"### {o.mode} {o.value} {o.given} -> {total}" +
          (f" (showing {len(rows)})" if len(rows) < total else "") + "\n")
    for uid, t in rows:
        print(f"* {t[:90]}")
        if not o.no_cards:
            c = card(uid)
            fates, q = summary(c)
            print(f"    questionnaire: {q or '-'}   fate: {', '.join(fates) or '-'}")
            print(f"    {c[:400]}")
        print(f"    {B}/szczegoly/{uid}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
