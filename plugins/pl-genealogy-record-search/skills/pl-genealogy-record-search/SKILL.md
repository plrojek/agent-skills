---
name: pl-genealogy-record-search
description: "Match people from a family tree against Polish and former Kresy (eastern borderlands) record sources and turn family stories into cited acts. Use when the user points at a GEDCOM, a MyHeritage/Geni/FamilySearch tree, or names an ancestor and asks to find records, verify a family story, break a brick wall, fill a missing maiden name, read a parish-book scan, or check whether someone is really a relative. Covers Geneteka parish indexes, the Indeks Represjonowanych (Soviet deportations), cemetery registers (Przemyśl, Grobonet), scan hosts (Skanoteka, metryki.genealodzy.pl, szukajwarchiwach.gov.pl, CAAK), where Galician and Kresy books physically are, reading Latin and Greek-Catholic registers, and patching a GEDCOM safely. Trigger phrases: 'drzewo genealogiczne', 'dopasuj osoby', 'znajdź akt', 'geneteka', 'kto był rodzicem', 'nazwisko panieńskie', 'czy jesteśmy spokrewnieni', 'przodkowie', 'metryki', 'akt urodzenia/ślubu/zgonu', 'Kresy', 'zesłanie', 'deportacja', 'Polish ancestors', 'parish records Poland'."
license: MIT
metadata:
  version: 1.0.0
---

# Polish genealogy: record matching

Turning names in a tree into cited archival records. Four phases, in order:

**inventory -> sweep the sources -> cross-match -> capture**

The tree is a hypothesis; records are evidence. Never let a family story into the tree as
fact without an act behind it, and never silently overwrite what the family remembers:
put the record next to it and flag the conflict.

All scripts are in `scripts/`, Python 3.10+ standard library only, except
`contact_sheet.py` (Pillow, run it with `uv run`). Run any of them with `--help`.

| Script | Does |
|---|---|
| `parse_ged.py tree.ged tree.json` | GEDCOM to JSON; everything else reads the JSON |
| `inventory.py tree.json --root @I1@` | brick walls, placeholders, surname x place frequency |
| `audit_tree.py tree.json` | impossible chronology |
| `geneteka.py parishes / search / check` | parish indexes; `--json` feeds the cross-match |
| `indeks_repr.py surname / place` | Soviet deportations, whole village transports |
| `cmentarze_przemysl.py` | Przemyśl municipal cemeteries, birth dates from grave cards |
| `grobonet.py --host ...` | any Grobonet cemetery, everyone in a grave |
| `sweep_all.py` | one surname through the sources you switch on |
| `skanoteka.py units / files / get` | scans from skanoteka and metryki.genealodzy.pl |
| `caak.py pages / page / crop` | IIIF diocesan archive (Kraków), native-resolution crops |
| `contact_sheet.py sheet / crop` | year map of many scans; magnified crops |
| `crossmatch.py tree.json index.json` | tree people vs saved index rows |
| `validate_ged.py tree.ged` | references, duplicates, trailer position after a patch |

Be a good guest on these sites. Most are run by volunteers (PTG runs Geneteka, Skanoteka
and metryki) or small public offices. The scripts identify themselves, wait a second between
requests to a host, and cache Geneteka answers in `~/.cache/pl-genealogy-record-search`.
Query narrowly (a parish, a surname, a year range) instead of sweeping whole provinces, and
never work around a block, a captcha or bot protection.

---

## Phase 0: read what is already known, agree the scope

If the project keeps a research log (its CLAUDE.md or the user will say where), read it
before re-deriving anything: parish coverage, acts already found, rejected leads. Sweeps
are slow and the indexes change little from month to month; extend, don't repeat.

Ask whose ancestors are the target (the `--root` person, or a couple's children, who carry
all four lines) and how far sideways to go. Default: direct ancestors first; their siblings
and first cousins as "close family"; anything further only when it settles a wall on the
direct line (a cousin's act that names the shared grandparents). Side branches eat sessions.

---

## Phase 1: inventory the tree

Parse the GEDCOM first; never grep a GEDCOM by hand.

```
python3 scripts/parse_ged.py tree.ged tree.json
python3 scripts/inventory.py tree.json --root @I1@
python3 scripts/audit_tree.py tree.json
```

`inventory.py` gives three lists, in the order to work them:

1. **Brick walls**: ancestors with no parents recorded. These are the targets.
2. **Placeholders**: blank given names, missing surnames, a wife whose surname equals her
   husband's (usually copied from him instead of her maiden name). The cheapest wins: one
   marriage act often fills three of them.
3. **Surname x place frequency**: which parishes to open. A surname twenty times in one
   village is a parish to sweep in full; a surname twice is noise.

`audit_tree.py` flags a parent under 15, a mother over 55, a child born after the mother's
death, death before birth. Report these even when they have nothing to do with records.

---

## Phase 2: sweep the sources

### Geneteka: parish indexes

`scripts/geneteka.py`; don't hand-roll the URL.

```
python3 scripts/geneteka.py parishes 09pk --grep Rzeszów       # rids and indexed years
python3 scripts/geneteka.py search 09pk B Kowal --rid 1234 --json kowal-B.json
```

**Every record type of a parish has its own rid.** The parish list carries `data-b`,
`data-s`, `data-d` and the indexed years. Passing the birth rid with `D` does not fail: it
returns the birth table under death headers, and you will read it as deaths. Take the rid
from `parishes`. And **query all three before declaring a negative**: it is easy to work
for days on a parish's marriage and death indexes while its birth index, under a third
rid, was never asked. A dash in `parishes` means no index; an unused rid means no answer.

**The pooled "Archiwum" answer.** Geneteka sometimes answers with tens of thousands of rows
from unrelated parishes, every filter ignored, and an empty `parishes` list. It looks like
real index rows. Two causes are known:

1. A defective rid for one parish while its sibling rids work.
2. **Your network address flagged** after heavy automated use. Then every query returns it,
   and so does a normal browser on the same network. In one case it followed weeks of
   province-wide sweeps and lifted on its own within two months.

`search` checks every answer (`sanity_reasons`: over 3000 rows, no parish named, the wrong
parish, the surname in no row), refuses to cache or page through a bad one, and says so.
To tell the causes apart, run a **control query** whose answer you already know:
`geneteka.py check <woj> <B|S|D> <rid> <surname> <expected_total>`. If the control is also
pooled, stop all Geneteka work for the session. Do not retry in a loop and do not try to get
around the flag; keep later use manual and narrow. Older cached answers from a bad day can be
poisoned too: purge the cache if in doubt.

**A zero is more often a spelling problem than a gap.** A family searched as `Kostur`
returned nothing in all three record types in its home parish; the priest had written
`Kastur`, and that returned dozens of births, marriages and deaths, including a marriage act
that had been read off the scan by hand the session before. Before writing "not indexed",
spend one query on each obvious variant: vowel swaps, `-ski/-ska`, `-cki/-cka`, dropped
diacritics, `ó/o/u/i`, `rz/ż`, Latin and Ruthenian forms (`Szewczyk/Szewczuk`). The fastest
test: search the **spouse's or mother's surname** instead, and read the target family's
spelling off the row. In Greek-Catholic books one family can be spelled two ways for the
same couple's children two years apart; parents' names and the village decide, not the spelling.

Other mechanics:

- Province-wide search: leave out `--rid`. The API returns 50 rows per call; the script pages.
- The remarks are in the **last** column, often only in `title=` tooltips; `strip()` reads
  them. They carry `mąż/żona/wdowa po ...` and the exact date: the most valuable field.
- Some parishes are **bare indexes**: year, act number, name, village, no parents in any row.
  Parents cannot come out of Geneteka there; you need the book.
- Indexes carry **systematic errors**. In one city parish every `Angela` was indexed as
  `Agnieszka`, and a similar surname was folded into a more common one, so part of the hits
  for that surname belonged to a different family. Search with the index, prove with the original.
- An index may be built from the **date the act was written**, not the event. In Russian
  Poland the act gives Julian and Gregorian dates (`pierwszego /: trzynastego :/ lutego`);
  the tree gets the Gregorian event date.
- **Geneteka often links straight to the scan, but only in the raw JSON** (`<a class="gt"
  href=...>`). `search --links` prints those links; the formatted rows lose them.
- `geneszukacz.genealodzy.pl?op=se` counts surname occurrences per province: use it to
  decide whether to dig. It returns no records.

### Indeks Represjonowanych: deportations and Soviet repression

`scripts/indeks_repr.py surname <Surname>` or `place <Village>`.

**Search by place, not surname.** `repression_place` with the `exact_` flag (which on this
site means "contains") returns **the whole transport from one village**: relatives whose
surname you don't know yet, and neighbours who explain later marriages. In one family a
surname search found a third of the people the place search did.

Read the questionnaire number `IR/<n>/<position>` where a card has one. Positions in one
questionnaire are one household: father, mother, children oldest first. **Gaps in the
positions are unpublished family members**, often the answer to the question asked. The
originals are in Archiwum IPN and can be ordered with the signature from the card
(`references/sources.md`).

A Kresy family with **no** record here was probably resettled in 1944-46, not deported:
look for PUR (repatriation office) records instead.

### Cemetery registers: the best source for the 20th century

Municipal registers are administrative records and usually beat family memory on dates. For
anyone who died after the parish indexes stop (about 1914-1935 depending on the parish)
this is often the only thing online, and it is free and instant: check it before writing to
an archive.

`scripts/cmentarze_przemysl.py` (five municipal cemeteries of Przemyśl):

- The list is not the data. Results are paged, and the **birth date and the grave-fee date
  are only on the grave card**. The script reads every page and every card.
- Women are filed under the female form of the husband's surname, sometimes with the maiden
  name appended (`KOWAL Z NOWAKÓW`, `HELENA Z D. LIS`), and sometimes the maiden name is in
  the given-name field. The surname filter matches from the start of the field, so a plain
  maiden-name query finds none of them: use `--maiden` (searches `%NAME`), and
  `<Married> --first "%MAIDEN%"` for the given-name field.
- **Search by birth date** (`--born 1901-05-17`) when the date is known from elsewhere and
  the married name isn't.
- The grave-fee date (`fee to`) shows whether someone still pays for the grave: decades
  ahead means a living relative.
- Coverage is the five municipal cemeteries only; parish cemeteries of surrounding villages
  are absent. "Nobody of that name here" means "not buried in town", not "not from here".

`scripts/grobonet.py --host <name>.grobonet.com` covers the many parish and town cemeteries on
Grobonet. Results show sector/row/grave; `--grave <id>` lists **everyone in that grave**.

**A shared grave is a family unit** and often the strongest evidence available: father and
son in one grave can confirm a parentage the indexes cannot. Graves in the same row are
often relatives too.

🔴 **Don't attach anyone from a cemetery register to a person who may be alive.** A tree
person with no death date, born less than about 95 years ago, is presumed living; a register
of the dead cannot contain them, so any "hit" is a namesake. This mistake was made twice in
one project, a month apart, both times with a matching name and birth year. Ask the user.

### Several sources at once

`scripts/sweep_all.py <Surname> [...]` with the sources switched on by flag
(`--przemysl`, `--grobonet HOST`, `--repressions`, `--geneteka WOJ`). It adds female forms,
keeps going when one source fails, and stops Geneteka at the first answer that is not real.

### Scans before letters to archives

Before writing "order a query from the archive", check whether the book is online. This cost
one project four sessions: a volume written up again and again as "needs an archive query"
had been free on Skanoteka for weeks, and three pages of it closed five walls in an afternoon.
Check, in this order: `szukajwarchiwach.gov.pl` (the unit page shows a scan count),
`skanoteka.genealodzy.pl` (new fonds weekly; the front page lists them),
`metryki.genealodzy.pl`, diocesan archives (`caak.upjp2.edu.pl` for Kraków), FamilySearch.
A negative from six months ago is worthless.

How to download from each host, how to find a year in a 400-scan volume in minutes, and how
to read the hands and the Latin: **`references/scans.md`**. Read it before opening a book.

What one act gives, so you budget for it:

- A 19th-century **Latin** register names the child's parents and the mother's own father
  (*"Ursula, filia Joannis ... et Mariae"*); a marriage act gives both spouses' parents,
  ages (so birth years) and birthplaces. Expect four new people per act.
- A **Galician Greek-Catholic birth register names the grandparents** on both sides and the
  mother's home village. At a Greek-Catholic wall, the child's birth act is worth more than
  the parents' marriage act, and easier to find.
- **Witnesses and godparents are kin**: a witness at a bride's wedding is usually her brother
  or brother-in-law. When a link will not appear in the direct records, read the witness and
  godparent columns of the suspected relatives' acts. That is how one man was finally tied to
  his wife's family: his name, with his occupation, in the `Testes` column of her sister's wedding.
- **Ages in the children's marriage acts order a multiply-widowed parent's marriages.**
  Three wives indexed against one man's name looked like index confusion until the
  children's ages put the marriages in sequence.
- Margins matter: Russian-partition birth acts carry later notes of the person's marriage;
  Galician entries carry USC notes from 1949-53 with the spouse's death date and act number.

### Mixed-rite marriages are in the bride's parish

A Greek-Catholic groom marrying a Roman-Catholic bride in Galicia is recorded in **her**
parish's book, not his. Every query that follows the groom's rite misses it; this cost one
wall three sessions. Signals: the shape of the surname, the **siblings' marriages** (sisters
married in one rite's church, their brother in the other's because of his bride), and plain
absence from the rite you have been searching.

### Where the book physically is

- **State archives (AP)** hold Roman-Catholic civil-registry duplicates from roughly 1890
  onward in Galicia; earlier volumes of the same parish are usually not there.
- **Diocesan archives** keep the older books. A signature like `21/T. 10` (a plain volume
  number, not `56/nnnn/0/-/n`) means a diocesan archive; writing to the AP gets nothing.
- `vacat - przekazane do USC` in an AP inventory: the volume went to a civil registry office
  because it was still too recent for the archive (also where many Greek-Catholic books went
  after 1947).
- **Kresy**: before ~1900 AGAD fond 301 and the Lviv archive (CDIAL fond 618); after ~1900
  the Warsaw-Śródmieście registry office (*księgi zabużańskie*).

| What is missing | What it means | Where to go |
|---|---|---|
| death after the index's last year | coverage gap | cemetery register, then the civil registry (death acts name parents and birthplace) |
| Kresy family, no deportation record | resettled, not deported | PUR records in the regional AP |
| Kresy parish after 1900 | *księgi zabużańskie* | USC Warszawa-Śródmieście |
| Kresy parish before 1900 | | AGAD fond 301, CDIAL Lviv fond 618 |
| Anders' Army soldier in no index | no complete public index exists | WBH-CAW (card with photo), Sikorski Institute, TNA `WO 315`, UdSKiOR |

Addresses, endpoints and what each source needs: `references/sources.md`.

---

## Phase 3: cross-match, and be honest about confidence

```
python3 scripts/geneteka.py search 09pk S Kowal --rid 1235 --json kowal-S.json
python3 scripts/crossmatch.py tree.json kowal-B.json kowal-S.json --years 15
```

`crossmatch.py` matches on given name + surname with diacritics folded, both the birth and
the married surname, both spouses in marriage rows. It gives candidates. Grade each by hand:

- **Confirmed**: a second independent field agrees. The spouse's given name in the remarks
  is the strongest single corroborator; the parents' names next. An indexer's free-text note
  about the person is gold.
- **Probable**: right parish, name and timing, nothing contradicts. Enter it, flagged as
  probable in the note and in the GEDCOM `NOTE`.
- **Hypothesis**: plausible, one link missing. Don't enter it. Write down which act would settle it.
- **Rejected**: say why, in the note. A ruled-out lead stops the next session re-chasing it.

Index rows without parents (a death entry with no parents, say) are verified on the scan
before they are used. One such row looked like a founding couple's infant daughter and would
have overturned the family story; the scan showed a married adult from another family.

Traps seen repeatedly:

- **Two men of one name in one parish at one time.** Find the discriminator (house number,
  a sibling pair, the wife) before merging. The house number is usually fastest.
- **One name, three wives.** Either one twice-widowed man or three men. In a village where a
  rare surname is dense, given names recycle every generation: a name pair identifies nothing.
- **An index attractor couple**: the same parents across a 40-year span of children is two
  couples sharing names, or index conflation. Stop the line there.
- **Common surnames** need a parish filter or the results are worthless; rare ones can be
  swept province-wide.

### Testing a family story

Family claims ("X is our cousin", "he was with Anders") are worth testing and are often
partly true. Split the claim and test each part: "the famous person was born in our
village" can be false while "her mother came from our village" is true. Conflating them
produced a wrong verdict that had to be retracted.

Before relying on a Wikipedia sentence, check that it has a citation and who added it:
`?action=raw` and the revision history (`references/sources.md`). An unsourced birthplace
claim added in one edit, years after the article was written, was simply wrong.

---

## Phase 4: capture

**Research note**, one per line of inquiry, wherever the user keeps them. It holds: the
parish coverage table (rids and year ranges, or the next session re-checks empty indexes),
every act as *year / act number / parish* with the archive signature and scan number, the
confidence grade of each finding, the rejected leads with reasons, and a prioritised list of
what to order from which archive. Cite institutions with signatures, not just names. Save
the scan crop of an act **when you find it**, not in a later "transcription round": locating
the row again costs more than saving it now.

Family-facing documents are written in the third person ("X's great-grandfather"); don't
guess how the user addresses their relatives, and check the direction of every kinship term.

**GEDCOM**: patch a **copy**, never the original export.

- 🔴 **Resolve every XREF by lookup right before patching** and re-parse afterwards to see the
  data landed on the intended person. Ids typed from memory put a birth act on two people
  from an unrelated branch.
- 🔴 **`0 TRLR` must stay the last line.** Three sessions once appended ~350 lines of new
  people after the trailer; a strict reader stops at `TRLR`, so all of them would have
  vanished on import. Remove the trailer, append, re-add it. `validate_ged.py` checks this,
  plus two-way FAMC/FAMS links and duplicate ids.
- Every touched record gets a `NOTE` with the act citation, so the file documents itself.
  The house number goes in as `1 RESI / 2 PLAC <village> <no.>`, not inside a note.
- Where a record contradicts the tree, add a `NOTE` and leave the tree value alone. Where
  kinship is unresolved, add the person **unattached** with a note listing the hypotheses.
  Guessing a parent writes a permanent falsehood.

**MyHeritage** cannot take a GEDCOM back: a web import always creates a new tree, and Family
Tree Builder's "merge into project" matches heuristically, not by XREF. The patched file is a
reference and a backup; the changes are keyed in by hand. Give the user an **entry-order
worklist**: placeholders and dates first, then parents, then children, then deletions.
A plain GEDCOM export has no `OBJE` records. An export with the **photo album option** does,
but its `FILE` lines are signed CDN links that expire after about a week: download the
photos immediately and rewrite the paths. `_POSITION x y w h` is the face rectangle.

**Privacy**: a tree contains living people. Keep GEDCOMs, scans of recent acts and research
notes out of public repositories and public pages; publish only people who are dead, and
never addresses or the details of anyone living.

---

## References

- `references/sources.md`: endpoints and parameters, province codes, archive addresses,
  what each source needs, Wikipedia checks.
- `references/scans.md`: downloading from every scan host, mapping a volume, reading
  the registers (layout, Latin, numbering traps).
