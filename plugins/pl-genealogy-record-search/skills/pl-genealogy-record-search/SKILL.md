---
name: pl-genealogy-record-search
description: "Match people from a family tree against Polish and former Kresy (eastern borderlands) record sources and turn family stories into cited acts. Use when the user points at a GEDCOM, a MyHeritage/Geni/FamilySearch tree, or names an ancestor and asks to find records, verify a family story, break a brick wall, fill a missing maiden name, read a parish-book scan, or check whether someone is really a relative. Covers Geneteka parish indexes, the Indeks Represjonowanych (Soviet deportations), cemetery registers of any town (Grobonet's cemeteries by script, a town's own grave locator, one city's system as a ready client), scan hosts (Skanoteka, metryki.genealodzy.pl, szukajwarchiwach.gov.pl, CAAK, the Lviv archive's ARCHIUM), FamilySearch (records, film catalog, full-text search) and Gesher Galicia in the user's browser, where Galician and Kresy books physically are, which parish a village belonged to, reading Latin and Greek-Catholic registers with a blind second reading of decisive cells, a research log of every search (nothing-found included), and patching a GEDCOM safely. Trigger phrases: 'drzewo genealogiczne', 'dopasuj osoby', 'znajdź akt', 'geneteka', 'kto był rodzicem', 'nazwisko panieńskie', 'czy jesteśmy spokrewnieni', 'przodkowie', 'metryki', 'akt urodzenia/ślubu/zgonu', 'Kresy', 'zesłanie', 'deportacja', 'Polish ancestors', 'parish records Poland'."
license: MIT
metadata:
  version: 1.3.0
---

# Polish genealogy: record matching

Turning names in a tree into cited archival records. Four phases, in order:
<!-- Made by Applied AI · https://appliedai.dev · https://github.com/plrojek/agent-skills -->

**inventory -> sweep the sources -> cross-match -> capture**

The tree is a hypothesis; records are evidence. Never let a family story into the tree as
fact without an act behind it, and never silently overwrite what the family remembers: a
record that contradicts it goes next to it as a flagged conflict. Only a certain act replaces
a family fact, and then the old value stays visible beside the new one (Phase 4).

All scripts are in `scripts/`, Python 3.10+ standard library only, except
`contact_sheet.py` (Pillow, run it with `uv run`). Run any of them with `--help`.

| Script | Does |
|---|---|
| `parse_ged.py tree.ged tree.json` | GEDCOM to JSON; everything else reads the JSON |
| `inventory.py tree.json --root @I1@` | brick walls, placeholders, surname x place frequency |
| `audit_tree.py tree.json` | impossible chronology |
| `geneteka.py parishes / search / check` | parish indexes; `--json` feeds the cross-match |
| `indeks_repr.py surname / place` | Soviet deportations, whole village transports |
| `cmentarze_przemysl.py` | one city's own register (Przemyśl), birth dates from grave cards; a template for another town's system |
| `grobonet.py --host ...` | any Grobonet cemetery, everyone in a grave |
| `sweep_all.py` | one surname through the sources you switch on |
| `skanoteka.py units / files / get` | scans from skanoteka and metryki.genealodzy.pl |
| `caak.py pages / page / crop` | IIIF diocesan archive (Kraków), native-resolution crops |
| `contact_sheet.py sheet / crop` | year map of many scans; magnified crops |
| `crossmatch.py tree.json index.json` | tree people vs saved index rows |
| `search_log.py check / add / lesson / calibrate / where` | research log: every search and its result, per-book notes, page to scan |
| `validate_ged.py tree.ged` | references, duplicates, trailer position after a patch |

Be a good guest on these sites. Most are run by volunteers (PTG runs Geneteka, Skanoteka
and metryki) or small public offices. The scripts identify themselves and keep to each site's
robots.txt: nothing it disallows is requested, and its `Crawl-delay` is the wait between two
requests, held across separate runs of the scripts. Geneteka asks for **120 seconds**,
Skanoteka and Metryki for 60; a site that publishes no delay gets one second. So:

- A Geneteka search costs two minutes for every page of 50 rows after the first, and **one
  command can outlast a shell tool's default timeout**. Run Geneteka and sweep commands with
  a long timeout (ten minutes) or in the background; a sweep of several surnames and record
  types runs for hours.
- The scripts print how long they will wait. Don't kill and restart them: the wait carries
  over to the next run anyway.
- Cached Geneteka answers (`~/.cache/pl-genealogy-record-search`, 30 days) cost nothing.

Query narrowly (a parish, a surname, a year range) instead of sweeping whole provinces, and
never work around a block, a captcha or bot protection.

---

## Phase 0: read what is already known, agree the scope

If the project keeps a research log (its CLAUDE.md or the user will say where), read it
before re-deriving anything: parish coverage, acts already found, rejected leads. Sweeps
are slow and the indexes change little from month to month; extend, don't repeat.

**The research log.** Set `GENEALOGY_LOG` to a file next to the research notes (otherwise
it is `~/.local/share/pl-genealogy-record-search/searches.jsonl`; every write prints the path).
`geneteka.py search` and `sweep_all.py` write every answer to it on their own. Everything
searched another way (a book read page by page, a search in the user's browser) goes in by
hand, with exactly what was covered, **nothing found included**:

```
python3 scripts/search_log.py add --source skanoteka --where "AP 35/1234 sy 12, births 1870-1885" \
    --surname Kowal --years 1870-1885 --pages 40-69 --result negative --note "index pages read too"
```

Before any search, check it: the most expensive mistake in this work is searching the same
book twice.

```
python3 scripts/search_log.py check --surname Kowal --years 1860-1880
```

`check` also says what a logged zero does not cover: a Geneteka zero covers only that index's
years and that spelling, a zero older than six months may be out of date, and an
`inconclusive` answer (the pooled fallback, a site that was down) counts as not searched.

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
2. **Your IP address blocked** after heavy automated use. The block is per public IP
   address: every query from that connection gets the pooled answer, from a script and from a
   normal browser alike, while the site itself loads fine. In one case it followed weeks of
   province-wide sweeps. Connecting the computer through a phone's mobile hotspot (a
   different public IP) gave real answers again at once, which is how the cause was
   confirmed; a VPN or tailnet that keeps the same public exit address changes nothing. The
   block on the home address lifted on its own within two months.

`search` checks every answer (`sanity_reasons`: over 3000 rows, the surname in no row, and
for a parish query also no parish named or the wrong parish), refuses to cache or page
through a bad one, and says so. A whole-province search never names a parish, even when its
rows are real, so an empty parish list counts only on a parish query.
To tell the causes apart, run a **control query** whose answer you already know:
`geneteka.py check <woj> <B|S|D> <rid> <surname> <expected_total>`. If the control is also
pooled, the address is blocked: stop all Geneteka queries on that connection and tell the
user, including that another connection (a phone hotspot) worked before. Switching networks
is the user's decision, not yours. Don't retry in a loop; that is what makes it worse. On any
connection, run the control query first and keep searches narrow: a parish rid, a surname,
a year range, not whole provinces. Cached answers from a bad day can be poisoned too: purge
the cache if in doubt.

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

- Province-wide search: leave out `--rid`. The API returns 50 rows per call; the script pages,
  two minutes a page, up to `--max-rows` (default 250), and says before it starts how long that
  will take. Narrow the query rather than raise the limit.
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
  href=...>`). `search --links` prints those links; the formatted rows lose them. For parishes
  now in Ukraine a link often reads `.../file-viewer/<unit>#file-<image id>`: the image id is the
  scan of that very act in the Lviv archive's ARCHIUM. Jump to it instead of paging a 500-image
  volume (`references/scans.md`).
- **The parish an index is labelled with is not always the book the act is in.** An index
  labelled with one parish quoted the signatures of other volumes, one of them a neighbouring
  parish's; the act was in the labelled parish's own book, a unit the index didn't name. Before
  trusting a label or a quoted signature, read the title page of the volume (or the unit's title
  in the archive's inventory).
- **A zero in the right parish's index can still be a gap.** An index can cover only some of the
  parish's villages or years. One family, every member present in the parish book, returned zero
  in all three record types of that parish's index. Look at the village column of the rows the
  index does return: if your village never appears, log the zero as `inconclusive`, not `negative`.
- **The given-name filter matches anyone in the row**, not only the child: `--name Jan` also
  returns children whose father is Jan. Read the role before counting a hit.
- **Pair search**: `--surname2` (and `--name2`) ask for a second person in the same row, the
  other spouse of a marriage. It also matches that person's parents, so one pair query on the
  parents' surnames (`S Kowal --surname2 Lis`) lists the marriages of all their children, with
  house numbers.
- **In a richly indexed parish one query rebuilds a family.** Where rows carry both sets of
  grandparents and the house, ask for the surname with the father's given name over a long span
  (`B Kowal --name Piotr --from 1850 --to 1905`): his own birth and every child's appear, and the
  villages of the children's births show where the family moved. When the parents' marriage is
  not in the husband's parish, look up the wife's own birth row: her village names the parish
  where the marriage most likely is.
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

Cemetery registers are administrative records and usually beat family memory on dates. For
anyone who died after the parish indexes stop (about 1914-1935 depending on the parish)
this is often the only thing online, and it is free and instant: check it before writing to
an archive. They exist for most of Poland, in three kinds; check all that apply to the town
where the person lived and died:

1. **The town's own grave locator.** Every voivodeship city and many towns run one for their
   municipal cemeteries (Kraków's Zarząd Cmentarzy Komunalnych, Wrocław, Gdańsk, Łódź, Poznań,
   Warsaw, …). Search the web for `<town> wyszukiwarka grobów` or `lokalizator grobów`, or the
   town's cemetery administration (`zarząd cmentarzy komunalnych`). Use it in the browser
   (Claude in Chrome) unless a script exists for that system; the rules below apply to all of them.
2. **Grobonet**, some 1,300 municipal and parish cemeteries across the country, each under its own
   `<name>.grobonet.com`: `scripts/grobonet.py --host <name>.grobonet.com`. Results show
   sector/row/grave; `--grave <id>` lists **everyone in that grave**. Grobonet's own site and the
   national search pages in `references/sources.md` find which instance holds a town.
3. **Nothing online**: many parish cemeteries in villages. The parish office keeps the burial book
   and the grave fees; write or call, and ask for the grave's other names too.

What every register hides, whichever kind it is:

- The list is not the data. Results are paged, and the **birth date and the grave-fee date are
  often only on the grave card**. Read every page and open every card.
- Women are filed under the female form of the husband's surname, sometimes with the maiden
  name appended (`KOWAL Z NOWAKÓW`, `HELENA Z D. LIS`), and sometimes the maiden name is in
  the given-name field. A surname filter that matches from the start of the field finds none of
  them by the maiden name: search the married name, and put the maiden name where the system
  allows wildcards.
- **Search by birth date** when the date is known from elsewhere and the married name isn't.
- The grave-fee date shows whether someone still pays for the grave: decades ahead means a
  living relative.
- Coverage is the cemeteries that register holds; "nobody of that name here" means "not buried
  there", not "not from here". A parish cemetery of the next village is often in none of them.
- **A card's birth date can be the baptism day, and the year can be a year off.** A card read
  8 February of one year; the baptism in a village next to the cemetery was born 1 February,
  baptised 8 February, the year before. Treat such a match as a candidate and look for an act
  that ties the next generation (the person's own death act names birthplace and parents:
  `references/sources.md`, "Civil registry offices") before attaching anyone.

`scripts/cmentarze_przemysl.py` is a ready client for one town's own system (Przemyśl's five
municipal cemeteries), and a template for another town: find the list request and the grave-card
page in the browser's network tab, page through every result, read every card, and send the
requests through `_net.py` so the town's `robots.txt` and delays are kept. Its options show what
to look for: `--maiden` (the surname matched anywhere: `%NAME`), `<Married> --first "%MAIDEN%"`
(the maiden name in the given-name field) and `--born 1901-05-17`.

**A shared grave is a family unit** and often the strongest evidence available: father and
son in one grave can confirm a parentage the indexes cannot. Graves in the same row are
often relatives too.

🔴 **Don't attach anyone from a cemetery register to a person who may be alive.** A tree
person with no death date, born less than about 95 years ago, is presumed living; a register
of the dead cannot contain them, so any "hit" is a namesake. This mistake was made twice in
one project, a month apart, both times with a matching name and birth year. Ask the user.

### Several sources at once

`scripts/sweep_all.py <Surname> [...]` with the sources switched on by flag
(`--grobonet HOST`, `--repressions`, `--geneteka WOJ`, and `--przemysl` for that one town's system). It adds female forms,
keeps going when one source fails, stops Geneteka at the first answer that is not real, and
writes every answer to the research log. With Geneteka switched on it runs for hours: run
`search_log.py check` for the surnames first, then start it in the background.

### Scans before letters to archives

Before writing "order a query from the archive", check whether the book is online. This cost
one project four sessions: a volume written up again and again as "needs an archive query"
had been free on Skanoteka for weeks, and three pages of it closed five walls in an afternoon.
Check, in this order: `szukajwarchiwach.gov.pl` (the unit page shows a scan count),
`skanoteka.genealodzy.pl` (new fonds weekly; the front page lists them),
`metryki.genealodzy.pl`, diocesan archives (`caak.upjp2.edu.pl` for Kraków), for Eastern
Galicia the Lviv archive's ARCHIUM (`archium.tsdial.archives.gov.ua`), and the FamilySearch
catalog, which also tells you in which archive the books were filmed (many
Polish films open only at a FamilySearch Center: check before promising a scan).
A negative from six months ago is worthless.

How to download from each host, how to find a year in a 400-scan volume in minutes, and how
to read the hands and the Latin: **`references/scans.md`**. Read it before opening a book.

What one book teaches you goes into the log under the book's signature, so the next session
opening it starts from there: measured page-to-scan pairs (`search_log.py calibrate --book
<signature> --page 112 --scan 57`, then `where --book <signature> --page 130`), and quirks such
as two years per page or a hand that writes 7 like 1 (`search_log.py lesson add --book
<signature> "..."`). Run `search_log.py lesson list --book <signature>` before opening a book.

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

### Marriages are in the bride's parish

A marriage is normally recorded where the bride lived. When the groom's parish has no marriage,
open the book of the parish the bride came from (her children's baptisms often name it) before
anything else: a wedding the groom's parish didn't have was in the bride's parish book.

The rite makes this easy to miss. A Greek-Catholic groom marrying a Roman-Catholic bride in
Galicia is recorded in **her** parish's book, not his. Every query that follows the groom's rite
misses it; this cost one wall three sessions. Signals: the shape of the surname, the **siblings'
marriages** (sisters married in one rite's church, their brother in the other's because of his
bride), and plain absence from the rite you have been searching.

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
- **The Lviv archive's metrical books are largely online.** TsDIAL's e-resource ARCHIUM shows the
  scans of fond 618 (Roman-Catholic) and fond 201 op. 4a (Greek-Catholic, including the
  consistory's copies) free, without a login, up to the 1940s for many parishes. Three walls
  written up as "only in Lviv, needs a query" fell in one day once the books were checked
  there. How to list a whole inventory and find a parish in it: `references/sources.md`;
  reading the viewer: `references/scans.md`.

| What is missing | What it means | Where to go |
|---|---|---|
| death after the index's last year | coverage gap | cemetery register, then the civil registry (death acts name parents and birthplace) |
| Kresy family, no deportation record | resettled, not deported | PUR records in the regional AP |
| Kresy parish after 1900 | *księgi zabużańskie* | USC Warszawa-Śródmieście |
| Kresy parish before 1900 | | AGAD fond 301; CDIAL Lviv fond 618 and 201 op. 4a, much of it online in ARCHIUM |
| Anders' Army soldier in no index | no complete public index exists | WBH-CAW (card with photo), Sikorski Institute, TNA `WO 315`, UdSKiOR |

### Which parish a village belonged to

Search the parish the village belonged to **at the time**, never the one its municipality
(gmina) has today. Villages moved between parishes, a hamlet's acts are in a neighbouring
village's book, and in the east the Greek-Catholic church of a village often stood in another
village than its Roman-Catholic parish. A wrong parish doesn't fail loudly: it returns a clean
zero. One family's village was noted under a neighbouring town's parish, taken from an index;
nothing turned up there, and the wall was written up as needing the diocesan archive. The
children's acts named the right parish, and that parish's book, with scans online, had every
member of the family. Settle the parish before you trust any negative.

1. **Słownik geograficzny Królestwa Polskiego** (1880-1914; the whole former Commonwealth,
   Galicia and the Kresy included). An entry names the parishes (`par. rz.-kat. w ...`,
   `gr.-kat. w ...`), the district and the number of houses and people. Full-text search:
   `https://dir.icm.edu.pl/?find_in=fulltext&volume_id=1&find_text=<name>&search_volume=all`.
   Hits "in the index" are the village's own entry pages (`/Slownik_geograficzny/Tom_XIII/319`);
   hits "in the text" are mentions in other entries, often the parish's own entry listing its
   villages. The abbreviations are explained at the start of volume I. In November 2026 the site
   put a bot check in front of its pages: open it in the user's browser, never around the check.
2. **Diocesan schematisms**, the yearly lists of a diocese's parishes with the villages of
   each, give the answer for one year. Look for them in the digital libraries listed in
   `references/sources.md`.
3. **PRNG** (`prng.geoportal.gov.pl`), the state register of geographic names: today's
   official names of villages and their parts, with other names in use. It tells same-named
   villages apart and places a hamlet; it says nothing about parishes.

A place read uncertainly off a scan is a lead, not a place: don't open another parish's
books on it until the gazetteer or a second reading settles it.

Addresses, endpoints and what each source needs, including how to search FamilySearch and
Gesher Galicia in the user's browser: `references/sources.md`.

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
  about the person is gold. Names alone don't prove identity, exact dates do: two independent
  exact matches settle it, such as a child's birth date known in the family and the mother's
  birth date printed in her marriage act, both equal to the act. Marriage acts from about 1900 on
  often print both spouses' birth dates, and a grave card gives the birth date of the dead, so
  look for that pair. A grave card or a family date can still be off by days or weeks from the
  act (a date misremembered, the baptism taken for the birth): a near miss is a lead to check
  against the act, not a contradiction and not a match.
- **Probable**: right parish, name and timing, nothing contradicts. Enter it, flagged as
  probable in the note and in the GEDCOM `NOTE`.
- **Hypothesis**: plausible, one link missing. Don't enter it. Write down which act would settle it.
- **Rejected**: say why, in the note. A ruled-out lead stops the next session re-chasing it.

### A second, blind reading of the cell that decides

Old handwriting is read by the strongest model available, never a faster, cheaper pass: a
misread surname sends the search to the wrong village. A conclusion that rests on **one
hard-to-read cell** (a maiden name, a house number, an age, a first name) gets a second,
independent reading before it is graded confirmed or written into the tree as from an act:

1. Crop the cell at full resolution (`contact_sheet.py crop`, or `caak.py crop` at the host's
   native resolution). One cell, not the whole page again. Name the file neutrally
   (`blind-01.jpg`): a file name with the surname tells the reader what to expect.
2. Give the crop to a reader that knows nothing of the research: a **fresh subagent** where the
   agent can start one (`general-purpose`, the same model, no cheaper override), never a fork,
   which inherits the whole conversation and isn't blind. Its prompt is the image path and one
   neutral question: *"Transcribe exactly what is written here. Mark letters you cannot read
   with [?]. Do not guess."* Never the expected value, the name hoped for, the place or why it
   matters. Without subagents the user reads the crop, or a second session with no context.
3. The readings agree: grade on the evidence and say in the note that two readers agreed.
   They differ: look again at exactly that spot. If it stays open, record **both readings** as a
   conflict in the note and in the GEDCOM `NOTE`, and don't pick one. "Illegible" beats a guess.

A transcription the user made is never overwritten: read the cell blind yourself and record
the agreement or the conflict next to it.

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
the row again costs more than saving it now. Transcribe every column the first time you open
the entry (ages, house number, godparents, witnesses, midwife, margin notes): opening the page
again later costs more than writing it down now. Searches that found nothing go into the
research log as they happen, every ten scans or each finished year, not all at the end.

**Audit the scans against the acts** after any long reading session. List every downloaded book
and every fact the notes say came from a scan, then check each against the transcribed acts the
tree holds (with the tree viewer: `ACTS`). One such audit found eight acts whose facts were already
in the tree, a death date, a baptism, two weddings, with no transcription, crop or signature behind
them; the facts were right, but nothing showed why. Each one found gets its crop, transcription and
role list then, and a note citing the wrong scan number gets corrected the same way.

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
- 🔴 **Before adding a person from an act, look for them in the parsed tree** by given name and
  dates (and the parents' or spouse's names). A child already in the tree was added a second time
  from her death act.
- Where a record contradicts the tree, add a `NOTE` and leave the tree value alone: one index row,
  one hard-to-read cell or one late source is a conflict, not a correction. Where kinship is
  unresolved, add the person **unattached** with a note listing the hypotheses. Guessing a parent
  writes a permanent falsehood.
- **When a certain act contradicts family tradition, the tree follows the act, visibly.** Certain
  means read twice (the blind second reading) and, for a parent's name, best confirmed by a second
  act, e.g. the marriage act and a child's baptism agreeing. Then change the value in the GEDCOM,
  keep the old one as a conflict marked as resolved by the acts (the family's version, each act and
  its value), and give the person a `NOTE` beginning `🔁 ZMIANA <date> według aktów:` that says what
  it was, what it is now and which acts decided it. Never silently: a relative who remembers the old
  name must find why it changed. Ask the user first when the tradition came from a living relative.

**MyHeritage** cannot take a GEDCOM back: a web import always creates a new tree, and Family
Tree Builder's "merge into project" matches heuristically, not by XREF. The patched file is a
reference and a backup; the changes are keyed in by hand. Give the user an **entry-order
worklist**: placeholders and dates first, then parents, then children, then deletions.
A plain GEDCOM export has no `OBJE` records. An export with the **photo album option** does,
but its `FILE` lines are signed CDN links that expire after about a week: download the
photos immediately and rewrite the paths. `_POSITION x y w h` is the face rectangle.

**Privacy**: a tree contains living people. Keep GEDCOMs, scans of recent acts, the research
log and research notes out of public repositories and public pages; publish only people who are dead, and
never addresses or the details of anyone living.

---

## References

- `references/sources.md`: endpoints and parameters, province codes, archive addresses,
  what each source needs, Wikipedia checks.
- `references/scans.md`: downloading from every scan host, mapping a volume, reading
  the registers (layout, Latin, numbering traps).
