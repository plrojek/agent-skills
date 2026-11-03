# Data model: tree_data.py and what the viewer reads

The GEDCOM holds people and families. `tree_data.py`, a plain Python file next to it, holds the
research the GEDCOM has no place for. `build_tree.py` joins the two into one `const DB` line in the
page, and the photos into `const IMG`. `templates/example/tree_data.py` uses every table below.

## Keys

| Names | Form | Notes |
|---|---|---|
| a person | `"Given Surname\|1890"`, `"Given Surname"`, or `"@I12@"` | The name as the GEDCOM has it (`parse_ged.py` prints it). Add the birth year when the name repeats. Use an xref only when two people share name and year, and look it up right before typing it. |
| a family | `"@F21@"` | `UNMARRIED`, `HYPOTHESIS_LINKS` |

A key that matches no one, or more than one person, is printed with `!!` and skipped; the build exits 1.
Never key anything by an xref remembered from earlier: a guessed xref silently attaches a description
to the wrong person.

## Tables in tree_data.py

| Name | Shape | What it does |
|---|---|---|
| `TITLE` | str | page title, header, start screen |
| `SUBTITLE` | str, optional | the family-names line; default: `plural(surname)` of each line anchor |
| `GEDCOM`, `OUTPUT` | paths, relative to tree_data.py | input and the page to write; `scans/` goes next to the page |
| `PHOTOS` | folder | `<xref without @>.jpg` (`I30.jpg`); 128 px square thumb + 480 px picture, embedded |
| `PHOTO_FILES` | `{person: path}` | photos named some other way |
| `BOOK` | str | file name of the family book PDF; shows the link on the welcome card |
| `LINES` | `[(person, label, short)]` | one branch per anchor. The anchor is the person at the **bottom** of the branch (a parent of the people the tree is for). `label` = `"przodkowie Jana Kowala"`, `short` = `"Jana Kowala"` (genitive: the header asks "whose ancestors?"). |
| `TIER_OVERRIDE` | `{person: "akt"\|"praw"\|"hip"\|""}` | tier by hand |
| `AUTO_TIER_FROM_CITATIONS` | bool, default False | a note citing `sygn.`, `akt 12/1890`, `skan`, `karta grobu` counts as `akt` |
| `WALLS` | `{person: (title, next step)}` | the box above an ancestor with no parents; ancestors without an entry get a generic box and are listed after the build |
| `WALLS_BY_ID` | same, keyed by xref | for a name that repeats |
| `HYPOTHESIS_LINKS` | `{child: (family, "praw"\|"hip", why)}` | attaches a candidate family with a dashed line and a "why this is a hypothesis" box |
| `EXTRA_PEOPLE` | `[dict(id="@X1@", name, sex, surname, child, tier, dashed, note, unknown_spouse=(label, next step))]` | people known only from the family: in the tree, not in the GEDCOM. `dashed=False` when the link itself is certain. |
| `UNMARRIED` | `{family: note}` | parents of a shared child: "Dziecko z" on the card, a dotted grey line, kinship counted by blood |
| `VARIANTS` | `[["Kowal", "Kowall", …]]` | spellings of one family **proven in the records**; the first is the group's name. Diacritics and -ska/-ski are joined without this. |
| `CONFLICTS` | `[dict(who, fact, versions=[(source, value)], status)]` | two sources, two values, side by side. `status` says what the evidence decided (`"rozstrzygnięta: …"`) or `"otwarta: …"`. Never changes the tier or the value in the tree. |
| `HYPOTHESES` | `[dict(who, question, variants=[dict(text, status, notes)], resolves)]` | `status` is `przyjęty`, `otwarty` or `wykluczony`; excluded variants stay visible as excluded |
| `ACTS` | list of dicts, below | transcribed acts with scans |

### ACTS

```python
dict(id="olszyny-u-1890-17",                  # file-name safe; scans/<id>.jpg and scans/<id>-line.jpg
     title="Olszyny, księga urodzeń 1890, akt 17",   # the words in it decide the act's kind (below)
     date="14 lutego 1890", ref="AP …, zespół …, sygn. …, skan 41", source="where the scan is online",
     text="""the entry as written, line by line""", translation="Polish translation",
     people={"Szymon Kowal|1890": "dziecko — to jego akt chrztu", "@I51@": "babka dziecka"},
     page="pages/olszyny-u-1890-17.jpg",        # optional: the whole scan; needs Pillow
     crop=(0.04, 0.30, 0.96, 0.62),             # the entry: fractions of the page, or pixels
     autocontrast=False,                        # True for faded microfilm
     proves=None)                               # optional: your own "what it proves" lines
```

Without `page`, put `scans/<id>.jpg` and `scans/<id>-line.jpg` there yourself. Everyone named in an act
gets tier `akt`, so tier and sources can't drift apart.

## Roles: what an act proves

The builder reads each role's **first part** (up to the first `—`, `,`, `(`, `;` or `:`). Then, for
every pair of people named in family roles, a parent–child or marriage link **that the tree already
has** is marked as backed by that act. It never adds a link.

| Act kind (from the title) | Role starts with | Gives |
|---|---|---|
| birth: `urodze`, `chrzt`, `ochrzcz`, `birth`, `baptism` | `dziecko`, `child` | the person's birth (unless their parents hang on a hypothesis) |
| death: `zgon`, `zmarł`, `pochow`, `death`, `burial` | `zmarł…`, `deceased` | the person's death |
| marriage: `ślub`, `małżeń`, `zapowied`, `marriage`, `banns` | `pan młody`, `panna młoda`, `groom`, `bride` | the wedding of the two |
| any | any family role: `ojciec`, `matka`, `dziad`, `babka`, `mąż zmarłej`, `ojciec panny młodej`, … | parent–child and marriage links between named people |
| — | `świadek`, `chrzestny/-a`, `zgłaszający`, `wymieniony…`, `właściciel`, `witness`, `godparent`, `informant`, `mentioned`, `owner` | nothing: not a family role |

A role like `"ojciec dziecka, zgłaszający"` is a father (first part). A link drawn on a hypothesis
(a `HYPOTHESIS_LINKS` family) is never marked as backed: the act may name a child of that name, but
whether that child is this person is exactly the open question. Acts whose title fits no kind (land
registers, address books) list each named person with their role instead.

## Tiers

| Tier | Badge | Comes from |
|---|---|---|
| `akt` | green edge, "AKT" | named in a transcribed act, `TIER: AKT` in a note, or `TIER_OVERRIDE` |
| `praw` | amber edge, (?) | `TIER: PRAWDOPODOBNE` (or `PROBABLE`), a `HYPOTHESIS_LINKS` tier, `TIER_OVERRIDE` |
| `hip` | blue edge, (?) | `TIER: HIPOTEZA` (or `HYPOTHESIS`), a `HYPOTHESIS_LINKS` tier, `TIER_OVERRIDE` |
| `""` | none | everything else, including `TIER: PEWNE` (`CERTAIN`): what the family knows is not doubt |
| `luka` | dashed box | walls, made by the builder |

## DB (the page's `const DB`)

| Key | Content |
|---|---|
| `people[xref]` | `n` name, `s` sex, `sn` surname, `mn` married name, `bd`/`bp`/`by` birth date/place/year, `dd`/`dp`/`dy` death, `bu` burial, `oc` occupation, `re` residence, `no` notes, `fc`/`fs` families as child/spouse, `t` tier, `br` line label; optional `hp`, `hpt`, `hw` (hypothetical parents), `sd` `[[act, role]]`, `ev` evidence, `cf` conflicts, `hy` hypotheses; walls also `w` next step, `wf` the person below, `wn`, `wg` generation |
| `fams[xref]` | `h`, `w`, `c` children, `md`/`mp` marriage date/place; optional `um` unmarried, `hp` hypothetical |
| `acts[id]` | `t` title, `d` date, `s` signature, `z` source, `x` transcription, `p` translation, `i` page scan, `c` crop, `w` what it proves |
| `ev` | `ur`, `zm`: lists of act ids; `rd`, `dz`, `sl`, `zw`: `{person: [acts]}` for parents, children, wedding, marriage |
| `lines` | `{label: [anchor xref, short]}` |
| `var` | `VARIANTS` |
| `meta` | `title`, optional `subtitle`, `book` |

`const IMG = {"t": {xref: data-uri}, "b": {xref: data-uri}}` — thumbnails and larger pictures.
