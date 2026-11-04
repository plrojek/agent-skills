# -*- coding: utf-8 -*-
"""Research tables for the example tree. Everything here is invented.

Build:  uv run --with pillow==11.3.0 python3 ../../scripts/build_tree.py tree_data.py
Every table is optional. Keys that name a person: "Given Surname|birth-year", "Given Surname",
or an xref ("@I12@") looked up in the parsed GEDCOM right before typing it. Family keys
(UNMARRIED, HYPOTHESIS_LINKS) are FAM xrefs. The format: references/data-model.md.
"""

TITLE = "Drzewo rodzinne — przykład"        # <title> and the header; the start screen uses it too
# SUBTITLE = "Jaworscy · Kosowie · …"     # default: the family names of the LINES anchors
GEDCOM = "example.ged"
OUTPUT = "out/tree.html"                     # scans/ is written next to it
PHOTOS = "photos"                            # <xref without @>.jpg, e.g. photos/I30.jpg
BOOK = ""                                    # "Ksiega-rodzinna.pdf" once build_book.py has made it

# One anchor per branch: the person at the BOTTOM of the branch (the family view unfolds upwards
# from there). Label = "przodkowie <genitive>", short = the genitive alone (the header list asks
# "whose ancestors?").
LINES = [
    ("Andrzej Jaworski|1955", "przodkowie Andrzeja Jaworskiego", "Andrzeja Jaworskiego"),
    ("Teresa Kos|1958", "przodkowie Teresy Kos", "Teresy Kos"),
    ("Krzysztof Lis|1960", "przodkowie Krzysztofa Lisa", "Krzysztofa Lisa"),
    ("Dorota Dudziak|1962", "przodkowie Doroty Dudziak", "Doroty Dudziak"),
]

# The person the tree is for: the path bar at the top starts here (route to the person in the centre,
# with the kinship term) until a reader marks someone else "to ja" on their own device.
ME = "Tomasz Jaworski|1985"

# Each line splits into the lines of its anchor's father and mother, each on its own background
# (family view, map, fan, minimap, path bar). Hues per LINES entry, in order:
# ((father's line, mother's line), the line's own side). Leave it out for the default palette;
# GRANDPARENT_LINES = False switches the backgrounds off.
# LINE_HUES = [((195, 160), 178), ((8, 52), 30), ((250, 290), 270), ((105, 68), 86)]

# Tier set by hand where the GEDCOM notes can't say it: akt / praw / hip / "" (certain, no badge).
# Notes can carry "TIER: AKT | PEWNE | PRAWDOPODOBNE | HIPOTEZA" themselves (see Feliks Lis).
TIER_OVERRIDE = {
    "Ludwik Kmieć|1915": "praw",
}

# Text of the wall above an ancestor whose parents are unknown: (title, next step).
# Keyed by name, never by a guessed xref. Ancestors with no entry get a generic wall and are listed.
WALLS = {
    "Józef Jaworski|1858": ("Rodzice Józefa Jaworskiego (ur. ok. 1858)",
        "Akt ślubu 1885 podaje tylko wiek. Następny krok: księga urodzeń parafii Olszyny 1855–1860."),
    "Feliks Lis|1898": ("Rodzice Feliksa Lisa",
        "Indeks parafii Lipnik nie ma urodzeń sprzed 1900; księga jest w archiwum diecezjalnym."),
    "Tadeusz Dudziak|1935": ("Rodzice Tadeusza Dudziaka",
        "Rodzina zna tylko imię ojca, Jan. Następny krok: odpis zupełny aktu urodzenia, USC Zalesie."),
}

# A family hung on a lead, drawn with a dashed line: child -> (FAM xref, tier, why).
HYPOTHESIS_LINKS = {
    "Helena Gołąb|1929": ("@F11@", "hip",
        "Jedyna para Gołębi z dzieckiem urodzonym ok. 1929 w okolicy. Nazwisko i wiek się zgadzają; "
        "żaden akt nie łączy Heleny z Franciszkiem i Julianną. Rozstrzygnie akt urodzenia Heleny."),
}

# People known only from the family, with no document: kept out of the GEDCOM, shown in the tree.
EXTRA_PEOPLE = [
    dict(id="@X1@", name="Ignacy Kos", sex="M", surname="Kos", child="Leon Kos|1930", tier="", dashed=False,
         note="Z relacji rodziny: ojciec Leona, kowal w Woli Brzozowej.",
         unknown_spouse=("Żona Ignacego Kosa", "Imienia nie znamy. Rozstrzygnie akt urodzenia Leona (1930).")),
]

# Parents of a shared child who were not married: "Dziecko z" on the card, dotted grey line.
UNMARRIED = {
    "@F21@": "Rozalia Kmieć i Antoni Wrona — wspólny syn Ludwik (1915), bez ślubu.",
}

# Spellings of one family proven in the records (the first is the group's name).
VARIANTS = [
    ["Jaworski", "Jaworzski"],
]

# Two sources, two values. The status is what the evidence decided, or "otwarta".
# When certain acts replace what the family tree said, the tree gets the act's value, the old value
# stays here as a conflict "rozstrzygnięta według aktów" (shown green), and the person gets a GEDCOM
# NOTE "🔁 ZMIANA według aktów: …" naming the acts (see Maciej Sowa in example.ged). Never silently.
CONFLICTS = [
    dict(who="Grzegorz Pająk|1900", fact="rok urodzenia",
         versions=[("drzewo rodzinne", "1900"), ("rejestr cmentarza, Wola Brzozowa", "12.03.1899")],
         status="otwarta: w drzewie zostaje 1900; rozstrzygnie akt urodzenia"),
    dict(who="Maciej Sowa", fact="imię ojca Marianny Sowy",
         versions=[("drzewo rodzinne, przed poprawką", "Gerwazy"),
                   ("akt ślubu, Olszyny 1885 nr 3", "Matthias (Maciej)"),
                   ("akt chrztu wnuka Szymona, Olszyny 1890 nr 17", "Matthias (Maciej)")],
         status="rozstrzygnięta według aktów: dwa akty zgodne, w drzewie jest już Maciej"),
]

# A question with several answers; status przyjęty / otwarty / wykluczony.
HYPOTHESES = [
    dict(who="Apolonia Kalita|1902", question="Która Apolonia Kalita wyszła za Feliksa Lisa?",
         variants=[dict(text="córka Hilarego i Bogumiły, ur. 1902 w Lipniku", status="otwarty",
                        notes="wiek zgodny z aktem zgonu 1979"),
                   dict(text="córka Jana i Marii, ur. 1904 w Zalesiu", status="wykluczony",
                        notes="zmarła w 1905")],
         resolves="akt ślubu Feliksa i Apolonii, parafia Lipnik, ok. 1925"),
]

# Transcribed acts. people = {key: role}; the FIRST word of the role decides what the act proves
# (references/data-model.md). page = the whole scan; crop = the entry, in pixels or fractions.
ACTS = [
    dict(id="olszyny-u-1890-17", title="Olszyny, księga urodzeń 1890, akt 17", date="14 lutego 1890",
         ref="Archiwum przykładowe, zespół 1/2, sygn. 3, skan 41", source="skany udostępnione online (przykład)",
         text="""17 | 14 Februarii | Dębina 12 | Simon | cath. · m · legitimus
PATER: Josephus Jaworzski, agricola.
MATER: Marianna, filia Matthiae Sowa et Catharinae, agricol.
Patrini: Anna Cisek, virgo.""",
         translation="Urodzony i ochrzczony 14 lutego 1890, Dębina nr 12. Szymon, syn z prawego łoża. "
                     "Ojciec: Józef Jaworzski, rolnik. Matka: Marianna, córka Macieja Sowy i Katarzyny. "
                     "Chrzestna: Anna Cisek, panna.",
         people={"Szymon Jaworski|1890": "dziecko — to jego akt chrztu",
                 "Józef Jaworski|1858": "ojciec dziecka",
                 "Marianna Sowa|1862": "matka dziecka",
                 "Maciej Sowa": "dziad dziecka — wymieniony jako ojciec matki",
                 "@I51@": "babka dziecka — wymieniona jako żona Macieja",
                 "Anna Cisek|1870": "chrzestna"},
         page="pages/olszyny-u-1890-17.jpg", crop=(0.04, 0.30, 0.96, 0.62)),
    dict(id="olszyny-s-1885-3", title="Olszyny, księga ślubów 1885, akt 3", date="7 lutego 1885",
         ref="Archiwum przykładowe, zespół 1/2, sygn. 7, skan 12", source="skany udostępnione online (przykład)",
         text="""3 | 7 Februarii | Dębina 12
SPONSUS: Josephus Jaworzski, annorum 27, caelebs.
SPONSA: Marianna, filia Matthiae Sowa et Catharinae, annorum 23, virgo.""",
         translation="Ślub 7 lutego 1885. Pan młody: Józef Jaworzski, 27 lat, kawaler. "
                     "Panna młoda: Marianna, córka Macieja Sowy i Katarzyny, 23 lata, panna.",
         people={"Józef Jaworski|1858": "pan młody",
                 "Marianna Sowa|1862": "panna młoda",
                 "Maciej Sowa": "ojciec panny młodej",
                 "@I51@": "matka panny młodej"},
         page="pages/olszyny-s-1885-3.jpg", crop=(0.04, 0.30, 0.96, 0.58)),
    dict(id="debina-z-1895-21", title="Dębina, księga zgonów 1895, akt 21", date="2 kwietnia 1895",
         ref="Archiwum przykładowe, zespół 1/2, sygn. 9, skan 77", source="skany udostępnione online (przykład)",
         text="""21 | 2 Aprilis | Dębina 12
Marianna Jaworzska, uxor Josephi, annorum 33.""",
         translation="Zmarła 2 kwietnia 1895 w Dębinie nr 12: Marianna Jaworzska, żona Józefa, 33 lata.",
         people={"Marianna Sowa|1862": "zmarła",
                 "Józef Jaworski|1858": "mąż zmarłej"},
         page="pages/debina-z-1895-21.jpg", crop=(0.04, 0.30, 0.96, 0.56), autocontrast=True),
]
