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

A key with a year breaks when the year changes: correct a birth date in the GEDCOM and every
`"Given Surname|old year"` in `ACTS`, `WALLS` and the other tables stops matching. After any change of a
birth date, rebuild and read the `!!` lines; switch such keys to the xref (looked up then) or the new year.

### Grandparents' lines

Each line splits into its anchor's father's line and mother's line. A person in the blood (ancestors
and all their descendants) of exactly one of those grandparents belongs to that grandparent's line; in
both grandparents' blood of one anchor (the anchor, their siblings and their children), to the anchor's
side; in two different anchors' lines (the people the tree is for, their children), to none. A spouse
who married in takes the partner's line. The wall above a person takes that person's line.

## Tables in tree_data.py

| Name | Shape | What it does |
|---|---|---|
| `TITLE` | str | page title, header, start screen |
| `SUBTITLE` | str, optional | the family-names line; default: `plural(surname)` of each line anchor |
| `GEDCOM`, `OUTPUT` | paths, relative to tree_data.py | input and the page to write; `scans/` goes next to the page |
| `PHOTOS` | folder | `<xref without @>.jpg` (`I30.jpg`); 128 px square thumb + 480 px picture, embedded |
| `PHOTO_FILES` | `{person: path}` | photos named some other way |
| `BOOK` | str | file name of the family book PDF; shows the link on the start screen, in "O drzewie" |
| `ME` | person | the person the tree is for: the path bar starts there until a reader marks someone "to ja" on their own device. Without it the bar starts at the person with the most descendants. |
| `LINES` | `[(person, label, short)]` | one branch per anchor. The anchor is the person at the **bottom** of the branch (a parent of the people the tree is for). `label` = `"przodkowie Jana Kowala"`, `short` = `"Jana Kowala"` (genitive: the header asks "whose ancestors?"). |
| `LINE_HUES` | `[((father, mother), side)]`, HSL hues | one entry per `LINES` anchor, in order: the hue of the anchor's father's line, of the mother's line, and of the anchor's own side. Default: four sets, reused past the fourth line. |
| `GRANDPARENT_LINES` | bool, default True | False: no line backgrounds (no `ln`, empty `lnd`) |
| `TIER_OVERRIDE` | `{person: "akt"\|"praw"\|"hip"\|""}` | tier by hand |
| `AUTO_TIER_FROM_CITATIONS` | bool, default False | a note citing `sygn.`, `akt 12/1890`, `skan`, `karta grobu` counts as `akt` |
| `WALLS` | `{person: (title, next step)}` | the box above an ancestor with no parents; ancestors without an entry get a generic box and are listed after the build |
| `WALLS_BY_ID` | same, keyed by xref | for a name that repeats |
| `HYPOTHESIS_LINKS` | `{child: (family, "praw"\|"hip", why)}` | attaches a candidate family with a dashed line and a "why this is a hypothesis" box |
| `EXTRA_PEOPLE` | `[dict(id="@X1@", name, sex, surname, child, tier, dashed, note, unknown_spouse=(label, next step))]` | people known only from the family: in the tree, not in the GEDCOM. `dashed=False` when the link itself is certain. |
| `UNMARRIED` | `{family: note}` | parents of a shared child: "Dziecko z" on the card, a dotted grey line, kinship counted by blood |
| `VARIANTS` | `[["Kowal", "Kowall", …]]` | spellings of one family **proven in the records**; the first is the group's name. Diacritics and -ska/-ski are joined without this. |
| `CONFLICTS` | `[dict(who, fact, versions=[(source, value)], status)]` | two sources, two values, side by side. `status` says what the evidence decided (`"rozstrzygnięta: …"`, shown green) or `"otwarta: …"`. Never changes the tier or the value in the tree. |
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

### When an act replaces a family fact

The tree follows the acts, and the change stays visible. When certain acts (a blind second reading,
ideally two acts that agree) contradict what the family tree said:

1. Change the value in the GEDCOM to the act's.
2. Keep the old value as a conflict that is already decided:
   `dict(who=..., fact="imię ojca", versions=[("drzewo rodzinne, przed poprawką", "Gerwazy"),
   ("akt ślubu, Olszyny 1885 nr 3", "Maciej")], status="rozstrzygnięta według aktów: …")`.
3. Add a GEDCOM `NOTE` to the person: `🔁 ZMIANA <date> według aktów: <what it was>; <which acts say
   what>. <what was changed>.` It shows on the card with the other notes.

One index row or one hard-to-read cell is not enough: that stays an open conflict, and the tree value
stays.

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

A role with **`KANDYDAT`** or **`CANDIDATE`** in capitals (`"dziecko — KANDYDAT (czy to Jan z grobu?)"`)
is an act that may be about this person but does not show it. It does not raise the person's tier,
and the book prints that act with a "hipoteza" badge and a note that it does not prove the identity.

## Tiers

| Tier | Badge | Comes from |
|---|---|---|
| `akt` | green edge, "AKT" | named in a transcribed act (not as a `KANDYDAT`/`CANDIDATE`), `TIER: AKT` in a note, or `TIER_OVERRIDE` |
| `praw` | amber edge, (?) | `TIER: PRAWDOPODOBNE` (or `PROBABLE`), a `HYPOTHESIS_LINKS` tier, `TIER_OVERRIDE` |
| `hip` | blue edge, (?) | `TIER: HIPOTEZA` (or `HYPOTHESIS`), a `HYPOTHESIS_LINKS` tier, `TIER_OVERRIDE` |
| `""` | none | everything else, including `TIER: PEWNE` (`CERTAIN`): what the family knows is not doubt |
| `luka` | dashed box | walls, made by the builder |

## DB (the page's `const DB`)

| Key | Content |
|---|---|
| `people[xref]` | `n` name, `s` sex, `sn` surname, `mn` married name, `bd`/`bp`/`by` birth date/place/year, `dd`/`dp`/`dy` death, `bu` burial, `oc` occupation, `re` residence, `no` notes, `fc`/`fs` families as child/spouse, `t` tier, `br` line label; optional `ln` (the key of the person's grandparent's line in `lnd`), `hp`, `hpt`, `hw` (hypothetical parents), `sd` `[[act, role]]`, `ev` evidence, `cf` conflicts, `hy` hypotheses; walls also `w` next step, `wf` the person below, `wn`, `wg` generation |
| `fams[xref]` | `h`, `w`, `c` children, `md`/`mp` marriage date/place; optional `um` unmarried, `hp` hypothetical |
| `acts[id]` | `t` title, `d` date, `s` signature, `z` source, `x` transcription, `p` translation, `i` page scan, `c` crop, `w` what it proves |
| `ev` | `ur`, `zm`: lists of act ids; `rd`, `dz`, `sl`, `zw`: `{person: [acts]}` for parents, children, wedding, marriage |
| `lines` | `{label: [anchor xref, short]}` |
| `lnd` | `{xref: [name, hue, 1 or 0]}`: the lines of each anchor's father and mother (1, labelled "linia: name") and each anchor's own side (0, a band without a label) |
| `root` | the xref of `ME`, where the path bar starts |
| `var` | `VARIANTS` |
| `meta` | `title`, `generator` (who made the page: Applied AI and the repository), optional `subtitle`, `book` |

`const IMG = {"t": {xref: data-uri}, "b": {xref: data-uri}, "brand": {"light": data-uri, "dark": data-uri}}` —
thumbnails and larger pictures, and the Applied AI wordmark (the footer has its own copy; `build_book.py`
takes this one for the book's last page).

A death in the GEDCOM with no date and no place (`1 DEAT Y`, as tree sites export "deceased") becomes
`dd = "data nieznana"`: the card says "Zm. data nieznana", the life span ends in "?", and `publish.py
--living` does not take the person for living.
