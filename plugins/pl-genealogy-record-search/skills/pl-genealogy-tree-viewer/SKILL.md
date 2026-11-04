---
name: pl-genealogy-tree-viewer
description: "Turn a GEDCOM and the research behind it into a private family-tree website and a printable family book: a family view with couples side by side, each grandparent's line on its own background, a whole-tree map, an ancestor fan, a timeline, a list, kinship between any two people and a path bar from the reader to whoever is in the centre, search by every spelling of a surname, by place and by years, the evidence for each fact (a transcribed act with its scan crop next to a date or a parent), walls with the next step, hypotheses and conflicting sources side by side, a downloadable ancestor picture (fan or tree, PNG/JPG/SVG), a living-people filter and a book PDF. Static files, no server code; works offline and on phones. Add-on to pl-genealogy-record-search: use it when the user has a tree (GEDCOM, research notes, acts) and wants to show it to family, put it on a private page, print it, or asks for a tree 'like a website'. Trigger phrases: 'drzewo na stronę', 'drzewo genealogiczne online', 'pokaż drzewo rodzinie', 'strona z drzewem', 'księga rodzinna', 'wydrukuj drzewo', 'wachlarz przodków', 'oś czasu przodków', 'obraz przodków', 'family tree website', 'family book PDF', 'ancestor chart picture', 'publish my family tree privately'."
license: MIT
metadata:
  version: 1.1.0
---

# Family tree page and family book

Builds a private family-tree website and a printable book from a GEDCOM plus the research the
GEDCOM can't hold: which act proves what, where the knowledge ends, what is only a hypothesis.

Paths in this file (`scripts/`, `templates/`, `references/`) are relative to the folder holding this
`SKILL.md`. It pairs with `pl-genealogy-record-search`, which finds and grades the records; this skill
shows them. The interface and the book are in Polish.

```
tree.ged  +  tree_data.py (me, lines, tiers, walls, acts, hypotheses, conflicts, variants)
        │  scripts/build_tree.py      (Pillow only for scan pages and photos)
        ▼
out/tree.html + out/scans/             one page, data and photos inside, scans beside it
        │  scripts/check_tree.py      (headless Chrome: every card, every layout)
        │  scripts/publish.py         (noindex, 11-digit numbers masked, --living YEAR)
        ▼
publication/index.html + scans/   →  scripts/build_book.py  →  Ksiega-rodzinna.pdf
```

## What the page does

| Part | What it shows |
|---|---|
| Start screen | one card per line (the ancestors of one person), with photos and counts |
| Rodzina | the person in the centre with all partners, children under each couple, every partner's ancestors above; side relatives on request; the direct line drawn thicker; a hint when parents are off screen |
| Line backgrounds | each line splits into its anchor's father's and mother's lines, each on its own colour band with a "linia: …" label; the same colours in the map, the fan, the minimap and the path bar |
| Path bar | under the header: the route from "to ja" (by default `ME`, the person the tree is for) to the person in the centre, each step in its line's colour and clickable, with the kinship term at the end |
| Mapa całości | everyone at once, with level of detail: dots with as many names as fit → names → tiles |
| Wachlarz | the centre person's ancestors on a half circle, up to 7 generations; walls and hypotheses dashed |
| Oś czasu | lives as bars on a year axis for the centre person's line, or for search results |
| Lista | everyone by family; spellings of one family under one heading |
| Card | dates, places, parents, partners ("Dziecko z" for unmarried parents), children, siblings; **akt** marks next to facts an act proves; walls with the next step; hypotheses with variants; conflicting sources side by side (green once the acts settled them); the transcribed acts with scan crops; notes, including change notes. On a computer a wide panel on the right (✕ or Esc closes it), on a phone a bottom sheet |
| Search | name in every spelling, place, a year or years; "show all" highlights the hits in the tree |
| Kinship | between any two people, and "this is me" for every card |
| Obraz przodków | a picture of one person's ancestors to download or share: fan or tree, 1–7 generations, dates, places, photos, empty fields for unknown ancestors, certainty colours, light, print or dark theme, PNG/JPG (2000–4000 px) or SVG; no dates or places of people presumed living by default |
| Tiers | the left edge of a tile: act, probable, hypothesis; (?) after the surname only for research-level doubt |
| Phone | bottom sheet, tab bar, pinch zoom, back gesture through the browser history |
| Book | a chapter per line in pedigree numbering, act marks, walls, hypotheses, an appendix of acts, an index |

## Phase 0: what to collect

- The GEDCOM (the record-search skill's patched copy, or an export from MyHeritage, Geni, Ancestry).
  `python3 scripts/parse_ged.py tree.ged` shows names and xrefs as the builder will see them.
- The research notes: which acts are transcribed, where each wall stands and what would break it,
  which links are hypotheses and why, which sources disagree.
- Scans of the transcribed acts (whole page; the entry is cropped by the builder).
- Photos, named by xref (`I30.jpg`).
- Who the tree is for: each line is the ancestors of one person, normally the parents of the people the
  tree is made for (four lines for a couple: both of each one's parents). That person goes into `ME`,
  where the path bar starts.
- Anything a certain act has replaced (a parent's name, a date): the old value and the acts that
  decided it, for a resolved conflict and a change note (Phase 1).

Ask the user before putting anything in: what they give as fact is certain. Only what they call
uncertain gets a tier below `akt` (`TIER: PRAWDOPODOBNE` / `HIPOTEZA` in a note, or `TIER_OVERRIDE`).

## Phase 1: tree_data.py

Copy `templates/example/` and replace its contents; the example uses every table. The tables, the
key format and the role vocabulary that drives the evidence marks are in
**`references/data-model.md`**: read it before writing `ACTS`.

Rules that matter most:

- Every person key is `"Given Surname|year"`, `"Given Surname"` or an xref looked up right then. The
  build prints every key that matches nobody or several people; fix them before going on.
- `LINES` anchors stand at the **bottom** of their branch. Their parents' lines get the background
  colours on their own; `LINE_HUES` only when the defaults clash with something.
- `VARIANTS` only for spellings proven in the records.
- `CONFLICTS` and `HYPOTHESES` copy values from the notes word for word, with the status the evidence
  reached. They never change a tier or a value in the tree.
- When certain acts replace a family fact, change the GEDCOM to the act's value **and** keep the old
  one visible: a `CONFLICTS` entry whose status starts `rozstrzygnięta według aktów` (shown green) and a
  GEDCOM `NOTE` on the person starting `🔁 ZMIANA <date> według aktów:` that says what it was, what
  it is now and which acts decided it. Never silently. The example does this for one name.

## Phase 2: build and check

```
uv run --with pillow==11.3.0 python3 scripts/build_tree.py path/to/tree_data.py
python3 scripts/check_tree.py path/to/out/tree.html
```

Read the build summary: people, walls (and walls without a description, listed), acts, evidence
counts, the grandparents' lines and where the path bar starts, and `!!` lines. `check_tree.py` opens
the page in headless Chrome, at a computer's and at a phone's window size, and renders every card, the family
layout with every person in the centre (side relatives off and on), the map with its far-zoom labels, the
fan, the timeline, the list, the path bar and the ancestor picture; any script error, overlap or
duplicate fails it. Then open the page yourself and look at one card with an act, one wall, one
hypothesis and one resolved conflict.

Changing the viewer: copy `templates/viewer/tree.html`, edit the copy, pass `--template`, and run
`check_tree.py` after every change to the layout. The output is rewritten on every build.

## Phase 3: publish

```
python3 scripts/publish.py out/tree.html publication/ --living 1926
uv run --with pillow==11.3.0 python3 scripts/build_book.py publication/index.html
```

`publish.py` adds noindex, masks every 11-digit number (a PESEL copied into a note) and, with
`--living`, redacts people presumed living (it prints them, and any line whose label you may want to
change; read the list). Build the book from the
published page: a PDF can't be filtered afterwards. Set `BOOK = "Ksiega-rodzinna.pdf"` in
`tree_data.py` to put the link on the welcome card. Hosting it privately (access control, caching,
checks): **`references/publishing.md`**.

## Phase 4: keep it current

| Change | Where |
|---|---|
| a new act | `ACTS` entry + the page scan; people named in it rise to `akt`, evidence marks follow |
| a wall broken | the parents go into the GEDCOM; the wall disappears on the next build |
| a new wall text | `WALLS` |
| a hypothesis decided | the variant's `status`; if confirmed, a normal family in the GEDCOM and the `HYPOTHESIS_LINKS` entry removed |
| a new spelling | `VARIANTS`, only with the act that shows it |
| an act replaces a family fact | the GEDCOM value, a `CONFLICTS` entry "rozstrzygnięta według aktów", a `🔁 ZMIANA` note naming the acts |

Rebuild, check, publish, book, in that order, every time.

## What not to do

- Don't key anything by a remembered xref, and don't hand-edit the output page.
- Don't show a tier for doubt nobody expressed, and don't read an unmarked fact as uncertain.
- Don't mark a hypothetical link as backed by an act.
- Don't replace a family fact without leaving the old value and the deciding acts on the card.
- Don't publish without access control, or with living people the family hasn't agreed to show.

The reasons behind each of these, and the layout and phone rules the viewer follows:
**`references/lessons.md`**.

## Requirements

Python 3.10+. Pillow only for scan pages and photos (`uv run --with pillow==11.3.0 …`). Google Chrome or
Chromium for `check_tree.py` and the book PDF (`CHROME=/path` if it isn't on the usual paths; inside a
Linux container Chrome may also need `--no-sandbox`, which the scripts don't add for you). The
page itself needs nothing: no server code, no external requests, no fonts or scripts from the web.
